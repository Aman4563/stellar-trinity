"""Closed execution-fidelity carrier; parsing does not establish capture custody."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from .canonical import JSONValue
from .errors import AttestationFailureReason, AttestationOutcome

if TYPE_CHECKING:
    from .intoto import (
        ExecutionInterval,
        PreRunCommitment,
        ReplayMetadata,
        ResourceDescriptor,
        RolloutDuration,
        _PredicateParseResult,
    )

EXECUTION_PREDICATE_TYPE_V2: Final = "trinity.execution/v2"
_DESCRIPTOR_FIELDS: Final = (
    "harnessConfig",
    "effectiveConfigReconciliation",
    "populationRoster",
    "observationCapture",
)
_BASE_FIELDS: Final = frozenset(
    {
        "operatorIdentity",
        "trajectoryRoot",
        "policyManifest",
        "scorerClosure",
        "populationSequenceCommitment",
        "preRunCommitment",
        "executionInterval",
        "rolloutDurations",
        "budgetEnvelope",
        "replay",
    }
)
_FIELDS: Final = _BASE_FIELDS | set(_DESCRIPTOR_FIELDS) | {"rolloutTelemetry"}


class TerminationReason(StrEnum):
    COMPLETED = "completed"
    SUBMITTED = "submitted"
    TURN_CAP = "turn_cap"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    REFUSAL = "refusal"
    SETUP_FAILURE = "setup_failure"


@dataclass(frozen=True, slots=True)
class RolloutTelemetry:
    rollout: str
    turns: int
    context_events: int
    termination_reason: TerminationReason
    provider_error_count: int


@dataclass(frozen=True, slots=True)
class ExecutionPredicateV2:
    """Bind observation_capture as it existed BEFORE operator editing.

    No deployed operator satisfies this custody obligation today. The descriptor
    binds bytes, not proof that an independent authority captured those bytes.
    """

    operator_identity: str
    trajectory_root: ResourceDescriptor
    policy_manifest: ResourceDescriptor
    scorer_closure: ResourceDescriptor
    population_sequence_commitment: ResourceDescriptor
    pre_run_commitment: PreRunCommitment
    execution_interval: ExecutionInterval
    rollout_durations: tuple[RolloutDuration, ...]
    budget_envelope: ResourceDescriptor
    replay: ReplayMetadata
    harness_config: ResourceDescriptor
    effective_config_reconciliation: ResourceDescriptor
    rollout_telemetry: tuple[RolloutTelemetry, ...]
    population_roster: ResourceDescriptor
    observation_capture: ResourceDescriptor


def _malformed(detail: str) -> AttestationOutcome:
    return AttestationOutcome.refuse(
        AttestationFailureReason.PREDICATE_MALFORMED,
        f"{EXECUTION_PREDICATE_TYPE_V2}: {detail}",
    )


def _parse_telemetry(
    value: JSONValue,
    durations: tuple[RolloutDuration, ...],
) -> tuple[tuple[RolloutTelemetry, ...] | None, AttestationOutcome]:
    from . import intoto  # noqa: PLC0415 - Defer shared parsers to avoid the re-export cycle.

    if not intoto._is_array(value) or not value:
        return None, _malformed("rolloutTelemetry must be a non-empty array")
    fields = {"rollout", "turns", "contextEvents", "terminationReason", "providerErrorCount"}
    telemetry: list[RolloutTelemetry] = []
    rollout_ids: set[str] = set()
    for index, item in enumerate(value):
        location = f"rolloutTelemetry[{index}]"
        if not intoto._is_object(item) or item.keys() != fields:
            return None, _malformed(f"{location} fields do not match the closed telemetry schema")
        rollout = intoto._required_text(item["rollout"])
        if rollout is None:
            return None, _malformed(f"{location}.rollout must be a non-empty string")
        if rollout in rollout_ids:
            return None, _malformed(f"{location} duplicates rollout {rollout!r}")
        counts: list[int] = []
        for field in ("turns", "contextEvents", "providerErrorCount"):
            count = item[field]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                return None, _malformed(f"{location}.{field} must be a non-negative integer")
            counts.append(count)
        reason = item["terminationReason"]
        if not isinstance(reason, str):
            return None, _malformed(f"{location}.terminationReason must be a registered string")
        try:
            termination = TerminationReason(reason)
        except ValueError:
            return None, _malformed(f"{location}.terminationReason is unknown: {reason!r}")
        rollout_ids.add(rollout)
        telemetry.append(RolloutTelemetry(rollout, counts[0], counts[1], termination, counts[2]))
    duration_ids: set[str] = set()
    for duration in durations:
        if duration.rollout in duration_ids:
            return None, _malformed(f"rolloutDurations duplicates rollout {duration.rollout!r}")
        duration_ids.add(duration.rollout)
    if rollout_ids != duration_ids:
        return None, _malformed(
            "rolloutTelemetry population mismatch: "
            f"missing {sorted(duration_ids - rollout_ids)!r}; "
            f"extra {sorted(rollout_ids - duration_ids)!r}"
        )
    return tuple(telemetry), AttestationOutcome.accept(())


def parse_execution_v2(value: JSONValue) -> _PredicateParseResult:
    from . import intoto  # noqa: PLC0415 - Defer shared parsers to avoid the re-export cycle.

    if not intoto._is_object(value) or value.keys() != _FIELDS:
        return intoto._PredicateParseResult(
            None, _malformed("execution predicate fields do not match trinity.execution/v2")
        )
    base_result = intoto._parse_execution({field: value[field] for field in _BASE_FIELDS})
    base = base_result.predicate
    if base is None:
        return intoto._PredicateParseResult(None, _malformed(base_result.outcome.detail))
    assert isinstance(base, intoto.ExecutionPredicate)
    resources: list[ResourceDescriptor] = []
    for field in _DESCRIPTOR_FIELDS:
        result = intoto._parse_resource(value[field], field)
        if result.resource is None:
            return intoto._PredicateParseResult(None, _malformed(result.outcome.detail))
        resources.append(result.resource)
    telemetry, outcome = _parse_telemetry(value["rolloutTelemetry"], base.rollout_durations)
    if telemetry is None:
        return intoto._PredicateParseResult(None, outcome)
    return intoto._PredicateParseResult(
        ExecutionPredicateV2(
            operator_identity=base.operator_identity,
            trajectory_root=base.trajectory_root,
            policy_manifest=base.policy_manifest,
            scorer_closure=base.scorer_closure,
            population_sequence_commitment=base.population_sequence_commitment,
            pre_run_commitment=base.pre_run_commitment,
            execution_interval=base.execution_interval,
            rollout_durations=base.rollout_durations,
            budget_envelope=base.budget_envelope,
            replay=base.replay,
            harness_config=resources[0],
            effective_config_reconciliation=resources[1],
            rollout_telemetry=telemetry,
            population_roster=resources[2],
            observation_capture=resources[3],
        ),
        AttestationOutcome.accept(()),
    )
