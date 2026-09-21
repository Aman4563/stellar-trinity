"""Fail-closed pilot-attempt registry parsing and familywise bound evaluation.

The statistic is a worst-case CP-derived upper bound on faithful pass@8 under
independence and common-distribution assumptions, not an exact CP bound on the
augmented indicator. Rollout IDs identify single executions globally, including
across solvers; reusing one never creates another independent observation.

Each attempt's groupCommitmentDigest binds its realized membership, not proof
that the commitment predates outcomes. Authenticated admission and look schedules
remain deferred under DEFERRED.md's "Precommitted population roster reconciled
against realized groups" row. Only a single final look is implemented here.
"""

# allow: SIZE_OK - Keep this scoped security fix in the existing closed-schema module.

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, Self, TypeGuard

if TYPE_CHECKING:
    from tools._bounded_json import BoundedJsonError, load_bounded_json
    from tools._findings import Finding, Severity
    from tools.attest import intoto, trustroot
    from tools.forensics import TRIAL_STATUSES
    from tools.forensics.filesystem import read_regular
    from tools.forensics.ledger import (
        FidelityLedgerReadError,
        FidelityProjectionError,
        project_for_pilot,
        read_fidelity_ledger,
    )
    from tools.forensics.reading import TraceReadError
    from tools.stats import (
        affected_group_fraction,
        bonferroni_confidence,
        group_upper_bound,
        minimum_groups,
        worst_case_group_successes,
    )
else:
    try:
        from tools._bounded_json import BoundedJsonError, load_bounded_json
        from tools._findings import Finding, Severity
        from tools.attest import intoto, trustroot
        from tools.forensics import TRIAL_STATUSES
        from tools.forensics.filesystem import read_regular
        from tools.forensics.ledger import (
            FidelityLedgerReadError,
            FidelityProjectionError,
            project_for_pilot,
            read_fidelity_ledger,
        )
        from tools.forensics.reading import TraceReadError
        from tools.stats import (
            affected_group_fraction,
            bonferroni_confidence,
            group_upper_bound,
            minimum_groups,
            worst_case_group_successes,
        )
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from _bounded_json import BoundedJsonError, load_bounded_json
        from _findings import Finding, Severity
        from attest import intoto, trustroot
        from forensics import TRIAL_STATUSES
        from forensics.filesystem import read_regular
        from forensics.ledger import (
            FidelityLedgerReadError,
            FidelityProjectionError,
            project_for_pilot,
            read_fidelity_ledger,
        )
        from forensics.reading import TraceReadError
        from stats import (
            affected_group_fraction,
            bonferroni_confidence,
            group_upper_bound,
            minimum_groups,
            worst_case_group_successes,
        )

POLICY_SCHEMA = "trinity.pilot-policy/v2"
ATTEMPT_SCHEMA = "trinity.pilot-attempt/v2"
STOPPING_RULE = "fixed_attempt_budget"
MEASURED_PASS_CEILING_MAX = 0.40
GENESIS_DIGEST = "0" * 64
POLICY_PATH = Path(".seed/pilot-policy.json")
REGISTRY_PATH = Path(".seed/pilot-attempts.jsonl")
MAX_POLICY_BYTES: Final = 1024 * 1024
MAX_REGISTRY_BYTES: Final = 16 * 1024 * 1024
MAX_REPORT_BYTES: Final = 4 * 1024 * 1024
MAX_REGISTRY_RECORDS: Final = 10000

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\Z")
_GROUP_SIZE = 8
_FRACTION_COMPONENT_COUNT = 2
_POLICY_FIELDS = frozenset(
    {
        "schemaVersion",
        "pilotId",
        "taskHash",
        "solverRegistryDigest",
        "familywiseConfidence",
        "attemptBudget",
        "primarySolverIds",
        "stoppingRule",
        "groupSize",
        "groupCount",
        "comparisonFamily",
        "permittedLooks",
        "maxAffectedGroupFraction",
        "harnessConfigDigest",
        "executionFidelityRequired",
    }
)
_FORBIDDEN_POLICY_FIELDS = frozenset(
    {"reasonCode", "reason", "suppressionReason", "fidelityDetail"}
)
_POLICY_CLAIM_FIELD = "correctedTaskBound"
_POLICY_CEILING_FIELD = "measuredPassCeiling"
_ATTEMPT_FIELDS = frozenset(
    {
        "schemaVersion",
        "sequence",
        "pilotId",
        "attemptId",
        "taskHash",
        "solverRegistryDigest",
        "startedAt",
        "endedAt",
        "solverGroups",
        "harnessConfigDigest",
        "groupCommitmentDigest",
        "fidelityLedgerDigest",
        "executionAttestationDigest",
        "previousRecordDigest",
        "recordDigest",
    }
)
_SOLVER_GROUP_FIELDS = frozenset({"solverId", "groupId", "rollouts"})
_ROLLOUT_FIELDS = frozenset({"rolloutId", "outcome", "trialStatus"})
TRIAL_OUTCOMES = frozenset({"success", "failure"})
_FORBIDDEN_ATTEMPT_FIELDS = frozenset(
    {"reasonCode", "reason", "suppressionReason", "fidelityDetail"}
)


class PilotFailureReason(StrEnum):
    """Closed failure vocabulary for pilot registry evaluation."""

    PILOT_ATTEMPT_REGISTRY_MISSING = "PILOT_ATTEMPT_REGISTRY_MISSING"
    PILOT_ATTEMPT_REGISTRY_MALFORMED = "PILOT_ATTEMPT_REGISTRY_MALFORMED"
    PILOT_ATTEMPT_CHAIN_INVALID = "PILOT_ATTEMPT_CHAIN_INVALID"
    PILOT_ATTEMPT_SET_INCOMPLETE = "PILOT_ATTEMPT_SET_INCOMPLETE"
    PILOT_ATTEMPT_BUDGET_EXCEEDED = "PILOT_ATTEMPT_BUDGET_EXCEEDED"
    PILOT_CORRECTION_INVALID = "PILOT_CORRECTION_INVALID"
    PILOT_CORRECTED_BOUND_MISMATCH = "PILOT_CORRECTED_BOUND_MISMATCH"
    PILOT_ATTEMPT_ATTESTATION_MISMATCH = "PILOT_ATTEMPT_ATTESTATION_MISMATCH"
    PILOT_MEASURED_CEILING_INVALID = "PILOT_MEASURED_CEILING_INVALID"
    PILOT_MEASURED_HEADROOM_BREACH = "PILOT_MEASURED_HEADROOM_BREACH"
    PILOT_SCHEMA_VERSION_UNSUPPORTED = "PILOT_SCHEMA_VERSION_UNSUPPORTED"
    PILOT_GROUP_STRUCTURE_INVALID = "PILOT_GROUP_STRUCTURE_INVALID"
    PILOT_INFEASIBLE_GROUP_COUNT = "PILOT_INFEASIBLE_GROUP_COUNT"
    PILOT_HARNESS_CONFIG_UNBOUND = "PILOT_HARNESS_CONFIG_UNBOUND"
    PILOT_OPERATOR_SELF_ASSERTED = "PILOT_OPERATOR_SELF_ASSERTED"
    PILOT_TRIAL_STATUS_UNKNOWN = "PILOT_TRIAL_STATUS_UNKNOWN"
    PILOT_FIDELITY_UNBOUND = "PILOT_FIDELITY_UNBOUND"
    PILOT_TRIAL_STATUS_DISAGREES = "PILOT_TRIAL_STATUS_DISAGREES"
    PILOT_GROUP_POPULATION_MUTATED = "PILOT_GROUP_POPULATION_MUTATED"
    PILOT_SUPPRESSION_FRACTION_EXCEEDED = "PILOT_SUPPRESSION_FRACTION_EXCEEDED"


@dataclass(frozen=True, slots=True)
class PilotPolicy:
    schema_version: str
    pilot_id: str
    task_hash: str
    solver_registry_digest: str
    familywise_confidence: float
    attempt_budget: int
    primary_solver_ids: tuple[str, ...]
    stopping_rule: str
    group_size: int
    group_count: int
    comparison_family: int
    permitted_looks: int
    max_affected_group_fraction: Fraction
    harness_config_digest: str
    execution_fidelity_required: Literal[True]
    corrected_task_bound: float | None = None
    measured_pass_ceiling: float = MEASURED_PASS_CEILING_MAX


@dataclass(frozen=True, slots=True)
class RolloutRecord:
    rollout_id: str
    outcome: str
    trial_status: str


@dataclass(frozen=True, slots=True)
class SolverGroup:
    solver_id: str
    group_id: str
    rollouts: tuple[RolloutRecord, ...]


@dataclass(frozen=True, slots=True)
class PilotAttempt:
    schema_version: str
    sequence: int
    pilot_id: str
    attempt_id: str
    task_hash: str
    solver_registry_digest: str
    started_at: datetime
    ended_at: datetime
    solver_groups: tuple[SolverGroup, ...]
    harness_config_digest: str
    group_commitment_digest: str
    fidelity_ledger_digest: str
    execution_attestation_digest: str
    previous_record_digest: str
    record_digest: str


@dataclass(frozen=True, slots=True)
class SolverBound:
    solver_id: str
    cumulative_successes: int
    cumulative_trials: int
    group_successes: int
    group_count: int
    confidence: float

    @property
    def upper_bound(self) -> float:
        """Release arithmetic accepts group counts only, never descriptive rollout tallies."""
        return group_upper_bound(self.group_successes, self.group_count, self.confidence)


@dataclass(frozen=True, slots=True)
class PilotEvaluationOutcome:
    accepted: bool
    reason: PilotFailureReason | None
    detail: str
    provisional: bool
    comparisons: int
    per_comparison_confidence: float | None
    solver_bounds: tuple[SolverBound, ...]
    corrected_task_bound: float | None

    @classmethod
    def accept(
        cls,
        *,
        provisional: bool,
        comparisons: int,
        per_comparison_confidence: float,
        solver_bounds: tuple[SolverBound, ...],
        corrected_task_bound: float,
    ) -> Self:
        return cls(
            True,
            None,
            "",
            provisional,
            comparisons,
            per_comparison_confidence,
            solver_bounds,
            corrected_task_bound,
        )

    @classmethod
    def refuse(cls, reason: PilotFailureReason, detail: str) -> Self:
        return cls(False, reason, detail, False, 0, None, (), None)


@dataclass(frozen=True, slots=True)
class PolicyParseResult:
    policy: PilotPolicy | None
    outcome: PilotEvaluationOutcome


@dataclass(frozen=True, slots=True)
class RegistryParseResult:
    attempts: tuple[PilotAttempt, ...] | None
    outcome: PilotEvaluationOutcome


def _is_object(value: object) -> TypeGuard[dict[str, object]]:
    return type(value) is dict and all(isinstance(key, str) for key in value)


def _canonical_json(value: object) -> bytes:
    rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return rendered.encode()


def _digest_record(record: dict[str, object]) -> str:
    body = {key: value for key, value in record.items() if key != "recordDigest"}
    return hashlib.sha256(_canonical_json(body)).hexdigest()


def derive_attempt_id(
    pilot_id: str,
    task_hash: str,
    sequence: int,
    solver_registry_digest: str,
) -> str:
    """Derive an attempt id as SHA-256(pilotId + taskHash + decimal sequence + registry digest)."""
    material = f"{pilot_id}{task_hash}{sequence}{solver_registry_digest}".encode()
    return hashlib.sha256(material).hexdigest()


def _refusal(reason: PilotFailureReason, detail: str) -> PilotEvaluationOutcome:
    return PilotEvaluationOutcome.refuse(reason, detail)


def _parse_json_object(document: str | bytes) -> tuple[dict[str, object] | None, str]:
    try:
        raw = document.encode("utf-8") if isinstance(document, str) else document
        value = load_bounded_json(raw)
    except UnicodeError:
        return None, "document must be UTF-8"
    except BoundedJsonError as error:
        return None, f"invalid JSON: {error}"
    if not _is_object(value):
        return None, "document must be a JSON object"
    return value, ""


def _closed_fields(value: dict[str, object], expected: frozenset[str]) -> str:
    missing = sorted(expected - value.keys())
    unknown = sorted(value.keys() - expected)
    if missing:
        return f"missing fields: {', '.join(missing)}"
    if unknown:
        return f"unknown fields: {', '.join(unknown)}"
    return ""


def _is_nonempty_string(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and bool(value)


def _is_hex_digest(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def parse_pilot_policy(document: str | bytes) -> PolicyParseResult:
    """Parse the closed v2 pilot policy, returning a refusal instead of raising."""
    value, error = _parse_json_object(document)
    malformed = PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    if value is None:
        return PolicyParseResult(None, _refusal(malformed, error))
    version = value.get("schemaVersion")
    if version != POLICY_SCHEMA:
        detail = f"unsupported schemaVersion {version!r}; required {POLICY_SCHEMA!r}"
        return PolicyParseResult(
            None, _refusal(PilotFailureReason.PILOT_SCHEMA_VERSION_UNSUPPORTED, detail)
        )
    group_size = value.get("groupSize")
    if type(group_size) is not int or group_size != _GROUP_SIZE:
        return PolicyParseResult(
            None,
            _refusal(
                PilotFailureReason.PILOT_GROUP_STRUCTURE_INVALID, "groupSize must be exactly 8"
            ),
        )
    fields = frozenset(value)
    binding_fields = frozenset({"harnessConfigDigest", "executionFidelityRequired"})
    if not _POLICY_FIELDS - binding_fields <= fields:
        error = _closed_fields(value, _POLICY_FIELDS - binding_fields)
        return PolicyParseResult(None, _refusal(malformed, error))
    pilot_id = value["pilotId"]
    task_hash = value["taskHash"]
    registry_digest = value["solverRegistryDigest"]
    confidence = value["familywiseConfidence"]
    budget = value["attemptBudget"]
    solver_ids = value["primarySolverIds"]
    stopping_rule = value["stoppingRule"]
    corrected_bound = value.get(_POLICY_CLAIM_FIELD)
    measured_ceiling = value.get(_POLICY_CEILING_FIELD, MEASURED_PASS_CEILING_MAX)
    if not _is_nonempty_string(pilot_id):
        return PolicyParseResult(None, _refusal(malformed, "pilotId must be a non-empty string"))
    if not _is_hex_digest(task_hash):
        detail = "taskHash must be 64 lowercase hex characters"
        return PolicyParseResult(None, _refusal(malformed, detail))
    if not _is_hex_digest(registry_digest):
        return PolicyParseResult(
            None, _refusal(malformed, "solverRegistryDigest must be 64 lowercase hex characters")
        )
    if type(confidence) is not float or not math.isfinite(confidence) or not 0.0 < confidence < 1.0:
        detail = "familywiseConfidence must be a float inside (0, 1)"
        return PolicyParseResult(
            None,
            _refusal(PilotFailureReason.PILOT_CORRECTION_INVALID, detail),
        )
    if type(budget) is not int or budget < 1:
        detail = "attemptBudget must be an integer at least 1"
        return PolicyParseResult(
            None,
            _refusal(PilotFailureReason.PILOT_CORRECTION_INVALID, detail),
        )
    if type(solver_ids) is not list or not solver_ids:
        detail = "primarySolverIds must be a non-empty list"
        return PolicyParseResult(None, _refusal(malformed, detail))
    if not all(_is_nonempty_string(item) for item in solver_ids):
        detail = "primarySolverIds must contain non-empty strings"
        return PolicyParseResult(None, _refusal(malformed, detail))
    primary_solver_ids = tuple(solver_ids)
    if len(set(primary_solver_ids)) != len(primary_solver_ids):
        return PolicyParseResult(None, _refusal(malformed, "primarySolverIds must be unique"))
    comparison_family = value["comparisonFamily"]
    if type(comparison_family) is not int or comparison_family != budget * len(primary_solver_ids):
        detail = "comparisonFamily must equal attemptBudget times the number of primarySolverIds"
        return PolicyParseResult(
            None, _refusal(PilotFailureReason.PILOT_CORRECTION_INVALID, detail)
        )
    if stopping_rule != STOPPING_RULE:
        detail = f"stoppingRule must be {STOPPING_RULE!r}"
        return PolicyParseResult(None, _refusal(malformed, detail))
    if corrected_bound is not None and (
        type(corrected_bound) is not float
        or not math.isfinite(corrected_bound)
        or not 0.0 <= corrected_bound <= 1.0
    ):
        return PolicyParseResult(
            None,
            _refusal(
                PilotFailureReason.PILOT_CORRECTED_BOUND_MISMATCH,
                "correctedTaskBound must be a float inside [0, 1]",
            ),
        )
    if (
        type(measured_ceiling) is not float
        or not math.isfinite(measured_ceiling)
        or not 0.0 < measured_ceiling <= MEASURED_PASS_CEILING_MAX
    ):
        return PolicyParseResult(
            None,
            _refusal(
                PilotFailureReason.PILOT_MEASURED_CEILING_INVALID,
                f"measuredPassCeiling must be a float inside (0, {MEASURED_PASS_CEILING_MAX}]",
            ),
        )
    group_count = value["groupCount"]
    if type(group_count) is not int:
        return PolicyParseResult(
            None,
            _refusal(
                PilotFailureReason.PILOT_GROUP_STRUCTURE_INVALID, "groupCount must be an integer"
            ),
        )
    try:
        required_groups = max(8, minimum_groups(measured_ceiling, confidence, comparison_family))
    except (ValueError, OverflowError) as error:
        return PolicyParseResult(
            None, _refusal(PilotFailureReason.PILOT_MEASURED_CEILING_INVALID, str(error))
        )
    if group_count < required_groups:
        detail = f"declared groupCount {group_count}; required at least {required_groups}"
        return PolicyParseResult(
            None, _refusal(PilotFailureReason.PILOT_INFEASIBLE_GROUP_COUNT, detail)
        )
    harness_digest = value.get("harnessConfigDigest")
    if not _is_hex_digest(harness_digest):
        return PolicyParseResult(
            None,
            _refusal(
                PilotFailureReason.PILOT_HARNESS_CONFIG_UNBOUND,
                "harnessConfigDigest must be 64 lowercase hex characters",
            ),
        )
    if value.get("executionFidelityRequired") is not True:
        return PolicyParseResult(
            None,
            _refusal(
                PilotFailureReason.PILOT_HARNESS_CONFIG_UNBOUND,
                "executionFidelityRequired must be boolean true",
            ),
        )
    if forbidden := sorted(fields & _FORBIDDEN_POLICY_FIELDS):
        return PolicyParseResult(
            None, _refusal(malformed, f"forbidden policy fields: {', '.join(forbidden)}")
        )
    optional_fields = frozenset({_POLICY_CLAIM_FIELD, _POLICY_CEILING_FIELD})
    if not fields <= _POLICY_FIELDS | optional_fields:
        return PolicyParseResult(
            None,
            _refusal(malformed, _closed_fields(value, _POLICY_FIELDS | (fields & optional_fields))),
        )
    permitted_looks = value["permittedLooks"]
    if type(permitted_looks) is not int or permitted_looks != 1:
        return PolicyParseResult(
            None, _refusal(malformed, "permittedLooks must be exactly 1 (single final look)")
        )
    affected_fraction = value["maxAffectedGroupFraction"]
    if (
        type(affected_fraction) is not list
        or len(affected_fraction) != _FRACTION_COMPONENT_COUNT
        or type(affected_fraction[0]) is not int
        or type(affected_fraction[1]) is not int
        or affected_fraction[1] <= 0
        or not 0 <= affected_fraction[0] <= affected_fraction[1]
    ):
        detail = (
            "maxAffectedGroupFraction must be an integer [numerator, denominator] inside [0, 1]"
        )
        return PolicyParseResult(None, _refusal(malformed, detail))
    policy = PilotPolicy(
        POLICY_SCHEMA,
        pilot_id,
        task_hash,
        registry_digest,
        confidence,
        budget,
        primary_solver_ids,
        STOPPING_RULE,
        group_size,
        group_count,
        comparison_family,
        permitted_looks,
        Fraction(affected_fraction[0], affected_fraction[1]),
        harness_digest,
        True,
        corrected_bound,
        measured_ceiling,
    )
    accepted = PilotEvaluationOutcome(True, None, "", False, 0, None, (), None)
    return PolicyParseResult(policy, accepted)


def _parse_timestamp(value: object, field: str) -> tuple[datetime | None, str]:
    if not isinstance(value, str) or _UTC_TIMESTAMP.fullmatch(value) is None:
        return None, f"{field} must be an RFC 3339 UTC timestamp"
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError:
        return None, f"{field} must be an RFC 3339 UTC timestamp"
    return parsed, ""


def _attempt_fields(value: dict[str, object], fields: frozenset[str], depth: str) -> str:
    if forbidden := _FORBIDDEN_ATTEMPT_FIELDS & value.keys():
        return f"forbidden key at {depth} depth: {', '.join(sorted(forbidden))}"
    return _closed_fields(value, fields)


def _parse_rollout(value: object) -> RolloutRecord | PilotEvaluationOutcome:
    malformed = PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    if not _is_object(value):
        return _refusal(malformed, "rollout must be an object")
    if error := _attempt_fields(value, _ROLLOUT_FIELDS, "rollout"):
        return _refusal(malformed, error)
    rollout_id, outcome, status = value["rolloutId"], value["outcome"], value["trialStatus"]
    if not _is_nonempty_string(rollout_id):
        return _refusal(malformed, "rolloutId must be a non-empty string")
    if not isinstance(outcome, str) or outcome not in TRIAL_OUTCOMES:
        return _refusal(PilotFailureReason.PILOT_TRIAL_STATUS_UNKNOWN, "unknown outcome token")
    if not isinstance(status, str) or status not in TRIAL_STATUSES:
        return _refusal(PilotFailureReason.PILOT_TRIAL_STATUS_UNKNOWN, "unknown trialStatus token")
    return RolloutRecord(rollout_id, outcome, status)


def _parse_solver_groups(
    value: object, group_size: int
) -> tuple[SolverGroup, ...] | PilotEvaluationOutcome:
    malformed = PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    structure = PilotFailureReason.PILOT_GROUP_STRUCTURE_INVALID
    if type(value) is not list or not value:
        return _refusal(malformed, "solverGroups must be a non-empty list")
    groups: list[SolverGroup] = []
    group_ids: set[tuple[str, str]] = set()
    rollout_groups: dict[str, tuple[str, str]] = {}
    for item in value:
        if not _is_object(item):
            return _refusal(malformed, "group must be an object")
        if error := _attempt_fields(item, _SOLVER_GROUP_FIELDS, "group"):
            return _refusal(malformed, error)
        solver_id, group_id = item["solverId"], item["groupId"]
        if not _is_nonempty_string(solver_id) or not _is_nonempty_string(group_id):
            return _refusal(malformed, "solverId and groupId must be non-empty strings")
        identity = (solver_id, group_id)
        if identity in group_ids:
            return _refusal(
                structure, f"duplicate groupId {group_id!r} within solver {solver_id!r}"
            )
        group_ids.add(identity)
        raw_rollouts = item["rollouts"]
        if type(raw_rollouts) is not list:
            return _refusal(structure, f"group {group_id!r} rollouts must be a list")
        if len(raw_rollouts) != group_size:
            return _refusal(
                structure,
                f"group {group_id!r} has {len(raw_rollouts)} rollouts; required {group_size}",
            )
        rollouts: list[RolloutRecord] = []
        for raw_rollout in raw_rollouts:
            rollout = _parse_rollout(raw_rollout)
            if isinstance(rollout, PilotEvaluationOutcome):
                return rollout
            prior = rollout_groups.get(rollout.rollout_id)
            if prior == identity:
                return _refusal(
                    structure,
                    f"duplicate rolloutId {rollout.rollout_id!r} within group {group_id!r}",
                )
            if prior is not None:
                return _refusal(
                    structure,
                    f"rolloutId {rollout.rollout_id!r} shared across groups"
                    f" {prior[1]!r} (solver {prior[0]!r}) and {group_id!r} (solver {solver_id!r})",
                )
            rollout_groups[rollout.rollout_id] = identity
            rollouts.append(rollout)
        groups.append(SolverGroup(solver_id, group_id, tuple(rollouts)))
    return tuple(groups)


def _parse_attempt(
    value: dict[str, object], policy: PilotPolicy | None
) -> PilotAttempt | PilotEvaluationOutcome:
    malformed = PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    version = value.get("schemaVersion")
    if version != ATTEMPT_SCHEMA:
        return _refusal(
            PilotFailureReason.PILOT_SCHEMA_VERSION_UNSUPPORTED,
            f"unsupported schemaVersion {version!r}; required {ATTEMPT_SCHEMA!r}",
        )
    if error := _attempt_fields(value, _ATTEMPT_FIELDS, "top level"):
        return _refusal(malformed, error)
    sequence = value["sequence"]
    if type(sequence) is not int or sequence < 1:
        return _refusal(malformed, "sequence must be an integer at least 1")
    string_fields = ("pilotId", "attemptId")
    if any(not _is_nonempty_string(value[field]) for field in string_fields):
        return _refusal(malformed, "pilotId and attemptId must be non-empty strings")
    digest_fields = (
        "taskHash",
        "solverRegistryDigest",
        "executionAttestationDigest",
        "previousRecordDigest",
        "recordDigest",
        "groupCommitmentDigest",
        "fidelityLedgerDigest",
    )
    if any(not _is_hex_digest(value[field]) for field in digest_fields):
        return _refusal(malformed, "digest fields must be 64 lowercase hex characters")
    harness_digest = value["harnessConfigDigest"]
    if not _is_hex_digest(harness_digest) or (
        policy is not None and harness_digest != policy.harness_config_digest
    ):
        return _refusal(
            PilotFailureReason.PILOT_HARNESS_CONFIG_UNBOUND,
            "harnessConfigDigest must bind the policy's configuration",
        )
    started_at, error = _parse_timestamp(value["startedAt"], "startedAt")
    if started_at is None:
        return _refusal(malformed, error)
    ended_at, error = _parse_timestamp(value["endedAt"], "endedAt")
    if ended_at is None:
        return _refusal(malformed, error)
    if started_at >= ended_at:
        return _refusal(malformed, "startedAt must be earlier than endedAt")
    groups = _parse_solver_groups(
        value["solverGroups"], policy.group_size if policy is not None else _GROUP_SIZE
    )
    if isinstance(groups, PilotEvaluationOutcome):
        return groups
    pilot_id = value["pilotId"]
    attempt_id = value["attemptId"]
    task_hash = value["taskHash"]
    registry_digest = value["solverRegistryDigest"]
    attestation_digest = value["executionAttestationDigest"]
    previous_digest = value["previousRecordDigest"]
    record_digest = value["recordDigest"]
    commitment_digest = value["groupCommitmentDigest"]
    fidelity_digest = value["fidelityLedgerDigest"]
    assert isinstance(pilot_id, str)
    assert isinstance(attempt_id, str)
    assert isinstance(task_hash, str)
    assert isinstance(registry_digest, str)
    assert isinstance(attestation_digest, str)
    assert isinstance(previous_digest, str)
    assert isinstance(record_digest, str)
    assert isinstance(commitment_digest, str)
    assert isinstance(fidelity_digest, str)
    expected_attempt_id = derive_attempt_id(pilot_id, task_hash, sequence, registry_digest)
    if attempt_id != expected_attempt_id:
        return _refusal(malformed, "attemptId does not match its derived value")
    if record_digest != _digest_record(value):
        return _refusal(
            PilotFailureReason.PILOT_ATTEMPT_CHAIN_INVALID,
            "recordDigest does not match canonical record bytes",
        )
    return PilotAttempt(
        ATTEMPT_SCHEMA,
        sequence,
        pilot_id,
        attempt_id,
        task_hash,
        registry_digest,
        started_at,
        ended_at,
        groups,
        harness_digest,
        commitment_digest,
        fidelity_digest,
        attestation_digest,
        previous_digest,
        record_digest,
    )


def parse_attempt_registry(
    document: str | bytes, policy: PilotPolicy | None = None
) -> RegistryParseResult:
    """Parse closed v2 JSONL; bind configuration and group size when policy is supplied."""
    try:
        raw = document.encode("utf-8") if isinstance(document, str) else document
        if len(raw) > MAX_REGISTRY_BYTES or raw.count(b"\n") > MAX_REGISTRY_RECORDS:
            return RegistryParseResult(
                None,
                _refusal(
                    PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED,
                    "registry exceeds MAX_REGISTRY_BYTES or MAX_REGISTRY_RECORDS",
                ),
            )
        text = raw.decode("utf-8")
    except UnicodeError:
        return RegistryParseResult(
            None,
            _refusal(PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED, "registry must be UTF-8"),
        )
    if not text or not text.endswith("\n"):
        detail = "registry must end with LF"
        return RegistryParseResult(
            None,
            _refusal(PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED, detail),
        )
    attempts: list[PilotAttempt] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            detail = f"line {line_number} is empty"
            return RegistryParseResult(
                None,
                _refusal(PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED, detail),
            )
        value, error = _parse_json_object(line)
        if value is None:
            detail = f"line {line_number}: {error}"
            return RegistryParseResult(
                None,
                _refusal(PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED, detail),
            )
        attempt = _parse_attempt(value, policy)
        if isinstance(attempt, PilotEvaluationOutcome):
            assert attempt.reason is not None
            return RegistryParseResult(
                None, _refusal(attempt.reason, f"line {line_number}: {attempt.detail}")
            )
        if line.encode() != _canonical_json(value):
            detail = f"line {line_number} is not canonical JSON"
            return RegistryParseResult(
                None,
                _refusal(PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED, detail),
            )
        attempts.append(attempt)
    return RegistryParseResult(
        tuple(attempts), PilotEvaluationOutcome(True, None, "", False, 0, None, (), None)
    )


def evaluate_attempt_registry(
    policy: PilotPolicy,
    attempts: tuple[PilotAttempt, ...] | list[PilotAttempt],
    resolve_operator: Callable[[str], tuple[str, frozenset[str]] | None] | None = None,
    *,
    ledger_projection: Mapping[str, str] | None = None,
    ledger_digest: str | None = None,
) -> PilotEvaluationOutcome:
    """Evaluate fixed groups; the parent check supplies attestation/operator resolution.

    Without resolution this is arithmetic only, not independent execution verification.
    """
    if ledger_projection is None or not _is_hex_digest(ledger_digest):
        return _refusal(PilotFailureReason.PILOT_FIDELITY_UNBOUND, "fidelity ledger unavailable")
    projection = dict(ledger_projection)
    comparisons = policy.comparison_family
    if comparisons != policy.attempt_budget * len(policy.primary_solver_ids):
        return _refusal(PilotFailureReason.PILOT_CORRECTION_INVALID, "comparisonFamily mismatch")
    if policy.permitted_looks != 1:
        return _refusal(
            PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED,
            "permittedLooks must be exactly 1 (single final look)",
        )
    try:
        confidence = bonferroni_confidence(policy.familywise_confidence, comparisons)
        required_groups = max(
            8,
            minimum_groups(policy.measured_pass_ceiling, policy.familywise_confidence, comparisons),
        )
    except (ValueError, OverflowError) as error:
        return _refusal(PilotFailureReason.PILOT_CORRECTION_INVALID, str(error))
    if policy.group_count < required_groups:
        return _refusal(
            PilotFailureReason.PILOT_INFEASIBLE_GROUP_COUNT,
            f"declared groupCount {policy.group_count}; required at least {required_groups}",
        )
    if not attempts:
        return _refusal(
            PilotFailureReason.PILOT_ATTEMPT_SET_INCOMPLETE,
            "registry contains no pilot attempts",
        )
    if len(attempts) > policy.attempt_budget:
        return _refusal(
            PilotFailureReason.PILOT_ATTEMPT_BUDGET_EXCEEDED,
            f"registry has {len(attempts)} attempts but budget is {policy.attempt_budget}",
        )
    previous = GENESIS_DIGEST
    attestation_digests: set[str] = set()
    populations: dict[str, list[SolverGroup]] = {
        solver_id: [] for solver_id in policy.primary_solver_ids
    }
    group_ids: set[tuple[str, str]] = set()
    rollout_groups: dict[str, tuple[str, str]] = {}
    expected_solver_ids = set(policy.primary_solver_ids)
    for expected_sequence, attempt in enumerate(attempts, start=1):
        if attempt.fidelity_ledger_digest != ledger_digest:
            return _refusal(
                PilotFailureReason.PILOT_FIDELITY_UNBOUND,
                f"{attempt.fidelity_ledger_digest} != {ledger_digest}",
            )
        if attempt.sequence != expected_sequence:
            return _refusal(
                PilotFailureReason.PILOT_ATTEMPT_CHAIN_INVALID,
                f"expected sequence {expected_sequence}, got {attempt.sequence}",
            )
        if attempt.previous_record_digest != previous:
            return _refusal(
                PilotFailureReason.PILOT_ATTEMPT_CHAIN_INVALID,
                f"attempt {attempt.sequence} does not name the preceding record digest",
            )
        previous = attempt.record_digest
        if (
            attempt.pilot_id != policy.pilot_id
            or attempt.task_hash != policy.task_hash
            or attempt.solver_registry_digest != policy.solver_registry_digest
        ):
            return _refusal(
                PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED,
                f"attempt {attempt.sequence} digest identity does not match policy",
            )
        if attempt.execution_attestation_digest in attestation_digests:
            return _refusal(
                PilotFailureReason.PILOT_ATTEMPT_ATTESTATION_MISMATCH,
                f"attempt {attempt.sequence} reuses an execution attestation digest",
            )
        attestation_digests.add(attempt.execution_attestation_digest)
        if attempt.harness_config_digest != policy.harness_config_digest:
            return _refusal(
                PilotFailureReason.PILOT_HARNESS_CONFIG_UNBOUND,
                f"attempt {attempt.sequence} harnessConfigDigest does not match policy",
            )
        actual_solver_ids = {group.solver_id for group in attempt.solver_groups}
        if actual_solver_ids != expected_solver_ids:
            return _refusal(
                PilotFailureReason.PILOT_ATTEMPT_SET_INCOMPLETE,
                f"attempt {attempt.sequence} must contain every primary solver",
            )
        for group in attempt.solver_groups:
            identity = (group.solver_id, group.group_id)
            if identity in group_ids:
                return _refusal(
                    PilotFailureReason.PILOT_GROUP_STRUCTURE_INVALID,
                    f"duplicate groupId {group.group_id!r} for solver {group.solver_id!r}",
                )
            group_ids.add(identity)
            for rollout in group.rollouts:
                status = projection.get(rollout.rollout_id)
                if status not in TRIAL_STATUSES or rollout.trial_status != status:
                    return _refusal(
                        PilotFailureReason.PILOT_TRIAL_STATUS_DISAGREES,
                        rollout.rollout_id,
                    )
                if rollout.rollout_id in rollout_groups:
                    prior = rollout_groups[rollout.rollout_id]
                    return _refusal(
                        PilotFailureReason.PILOT_GROUP_STRUCTURE_INVALID,
                        f"rolloutId {rollout.rollout_id!r} shared across groups"
                        f" {prior[1]!r} (solver {prior[0]!r}) and"
                        f" {group.group_id!r} (solver {group.solver_id!r})",
                    )
                rollout_groups[rollout.rollout_id] = identity
            populations[group.solver_id].append(group)
    for attempt in attempts:
        membership = sorted(
            (group.solver_id, group.group_id, sorted(r.rollout_id for r in group.rollouts))
            for group in attempt.solver_groups
        )
        realized_digest = hashlib.sha256(_canonical_json(membership)).hexdigest()
        if attempt.group_commitment_digest != realized_digest:
            return _refusal(
                PilotFailureReason.PILOT_GROUP_POPULATION_MUTATED,
                f"attempt {attempt.sequence} groupCommitmentDigest does not match realized"
                f" membership: recorded {attempt.group_commitment_digest},"
                f" computed {realized_digest}",
            )
    bounds_list: list[SolverBound] = []
    for solver_id, population in populations.items():
        if len(population) != policy.group_count:
            return _refusal(
                PilotFailureReason.PILOT_GROUP_POPULATION_MUTATED,
                f"solver {solver_id!r} realized {len(population)} groups;"
                f" policy groupCount {policy.group_count}",
            )
        groups = tuple(
            tuple(
                (rollout.outcome == "success", projection[rollout.rollout_id])
                for rollout in group.rollouts
            )
            for group in population
        )
        try:
            x_star, n = worst_case_group_successes(groups)
            affected = affected_group_fraction(groups)
        except ValueError as error:
            return _refusal(PilotFailureReason.PILOT_GROUP_STRUCTURE_INVALID, str(error))
        if affected > policy.max_affected_group_fraction:
            return _refusal(
                PilotFailureReason.PILOT_SUPPRESSION_FRACTION_EXCEEDED,
                f"solver {solver_id!r} affected {affected * n}/{n} ({affected});"
                f" maximum {policy.max_affected_group_fraction}",
            )
        bounds_list.append(
            SolverBound(
                solver_id,
                sum(success for group in groups for success, _ in group),
                sum(len(group) for group in groups),
                x_star,
                n,
                confidence,
            )
        )
    bounds = tuple(bounds_list)
    corrected_bound = max(bound.upper_bound for bound in bounds)
    if policy.corrected_task_bound is not None:
        declared = Fraction(*policy.corrected_task_bound.as_integer_ratio())
        computed = Fraction(*corrected_bound.as_integer_ratio())
        if declared != computed:
            return _refusal(
                PilotFailureReason.PILOT_CORRECTED_BOUND_MISMATCH,
                "declared corrected task bound does not match the cumulative Bonferroni bound",
            )
    if corrected_bound >= policy.measured_pass_ceiling:
        return _refusal(
            PilotFailureReason.PILOT_MEASURED_HEADROOM_BREACH,
            f"corrected task bound {corrected_bound:.6f} sits at or above the"
            f" measured pass ceiling {policy.measured_pass_ceiling}",
        )
    if resolve_operator is not None:
        for attempt in attempts:
            resolution = resolve_operator(attempt.execution_attestation_digest)
            if resolution is None:
                return _refusal(
                    PilotFailureReason.PILOT_ATTEMPT_ATTESTATION_MISMATCH,
                    f"attempt {attempt.sequence} execution operator or repository signers"
                    " unresolved",
                )
            operator, repository_signers = resolution
            if operator in repository_signers:
                return _refusal(
                    PilotFailureReason.PILOT_OPERATOR_SELF_ASSERTED,
                    f"attempt {attempt.sequence} operator {operator!r} is a repository signer",
                )
    return PilotEvaluationOutcome.accept(
        provisional=len(attempts) < policy.attempt_budget,
        comparisons=comparisons,
        per_comparison_confidence=confidence,
        solver_bounds=bounds,
        corrected_task_bound=corrected_bound,
    )


def _finding(path: Path, reason: PilotFailureReason, detail: str) -> Finding:
    return Finding(reason.value, Severity.ERROR, str(path), 0, detail)


def _read(path: Path, root: Path, budget: tuple[str, int]) -> tuple[bytes | None, str]:
    try:
        return read_regular(path, project_root=root, max_bytes=budget[1]), ""
    except FileNotFoundError:
        return None, ""
    except (OSError, TraceReadError):
        return None, f"cannot read {path}: regular confined file within {budget[0]} required"


def _resolve_operator(root: Path, digest: str) -> tuple[str, frozenset[str]] | None:
    """Reuse execution-gate parsing and trust resolution, imported late to avoid its pilot cycle.

    This rejects local self-assertions; signature authorization remains the separately
    registered check_execution_attestations check, not a claim made by this parser.
    """
    if TYPE_CHECKING:
        from tools import integrity  # noqa: PLC0415 - integrity imports pilot
    else:
        try:
            from tools import integrity  # noqa: PLC0415 - integrity imports pilot
        except ModuleNotFoundError:  # pragma: no cover - direct tools/ execution
            import integrity  # noqa: PLC0415

    name = f"{integrity.EXECUTION_ATTESTATIONS_PATH}/{digest}.dsse"
    path, document, failure = integrity._parent_resource(root, name)
    if failure is not None or path is None or document is None:
        return None
    if integrity._first_symlink_component(root, path) is not None:
        return None
    if hashlib.sha256(document).hexdigest() != digest:
        return None
    statement, failure = integrity._execution_statement(path, document)
    if failure is not None or statement is None:
        return None
    trust, trust_failure = trustroot._load_root(root / integrity.TRUST_ROOT_PATH)
    if trust_failure is not None or trust is None:
        return None
    match statement.predicate:
        case intoto.ExecutionPredicateV2(operator_identity=operator):
            return operator, frozenset(principal.name for principal in trust.principals)
        case _:
            return None


def check_pilot_attempt_registry(
    root: str, evaluation_time: datetime | None = None
) -> list[Finding]:
    """Check a parent project's predeclared pilot policy and attempt registry."""
    del evaluation_time
    root_path = Path(root)
    policy_path = root_path / POLICY_PATH
    registry_path = root_path / REGISTRY_PATH
    policy_document, error = _read(policy_path, root_path, ("MAX_POLICY_BYTES", MAX_POLICY_BYTES))
    malformed = PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    if error:
        return [_finding(policy_path, malformed, error)]
    registry_document, error = _read(
        registry_path, root_path, ("MAX_REGISTRY_BYTES", MAX_REGISTRY_BYTES)
    )
    if error:
        return [_finding(registry_path, malformed, error)]
    if policy_document is None and registry_document is None:
        for report in ("EDICT.md", "VERDICT.md", "DIRECTIVE.md"):
            report_path = root_path / report
            document, error = _read(report_path, root_path, ("MAX_REPORT_BYTES", MAX_REPORT_BYTES))
            if error:
                return [_finding(report_path, malformed, error)]
            if document is None:
                continue
            if re.search(
                rb"executionAttestationDigest|correctedTaskBound|pilotId|"
                rb"pilot-attempts\.jsonl|\bpilot\s+evidence\s*:",
                document,
                re.IGNORECASE,
            ):
                break
        else:
            return []
    if policy_document is None:
        reason = PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MISSING
        return [_finding(policy_path, reason, "pilot evidence is declared without a policy")]
    if registry_document is None:
        reason = PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MISSING
        detail = "pilot policy exists but attempt registry is missing"
        return [_finding(registry_path, reason, detail)]
    parsed_policy = parse_pilot_policy(policy_document)
    if parsed_policy.policy is None:
        outcome = parsed_policy.outcome
        assert outcome.reason is not None
        return [_finding(policy_path, outcome.reason, outcome.detail)]
    parsed_registry = parse_attempt_registry(registry_document, parsed_policy.policy)
    if parsed_registry.attempts is None:
        outcome = parsed_registry.outcome
        assert outcome.reason is not None
        return [_finding(registry_path, outcome.reason, outcome.detail)]
    try:
        projection = project_for_pilot(read_fidelity_ledger(root_path / ".audit"))
    except (FidelityLedgerReadError, FidelityProjectionError):
        return [
            _finding(
                registry_path,
                PilotFailureReason.PILOT_FIDELITY_UNBOUND,
                "fidelity ledger unavailable",
            )
        ]
    evaluated = evaluate_attempt_registry(
        parsed_policy.policy,
        parsed_registry.attempts,
        lambda digest: _resolve_operator(root_path, digest),
        ledger_projection=projection,
        ledger_digest=projection["fidelityLedgerDigest"],
    )
    if not evaluated.accepted:
        assert evaluated.reason is not None
        return [_finding(registry_path, evaluated.reason, evaluated.detail)]
    if evaluated.provisional:
        return [
            _finding(
                registry_path,
                PilotFailureReason.PILOT_ATTEMPT_SET_INCOMPLETE,
                "provisional outcome cannot authorize qualification; attempt budget incomplete",
            )
        ]
    return []
