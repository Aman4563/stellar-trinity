from __future__ import annotations

# allow: SIZE_OK - Existing pilot regression corpus stays together for this scoped fix.
import base64
import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest
from tools import pilot
from tools.pilot import (
    ATTEMPT_SCHEMA,
    GENESIS_DIGEST,
    POLICY_SCHEMA,
    PilotAttempt,
    PilotFailureReason,
    PilotPolicy,
    check_pilot_attempt_registry,
    derive_attempt_id,
    parse_attempt_registry,
    parse_pilot_policy,
)

from tests.fidelity_binding_fixtures import bind_registry_ledger
from tests.harness_imports import integrity
from tests.test_attest_intoto import valid_execution_v2

TASK_HASH = "a" * 64
REGISTRY_DIGEST = "b" * 64
PILOT_ID = "pilot-alpha"
SOLVERS = ("solver-a", "solver-b")


def matching_projection(attempts: tuple[PilotAttempt, ...]) -> dict[str, str]:
    return {
        rollout.rollout_id: rollout.trial_status
        for attempt in attempts
        for group in attempt.solver_groups
        for rollout in group.rollouts
    }


def evaluate_attempt_registry(
    policy: PilotPolicy,
    attempts: tuple[PilotAttempt, ...],
    resolve_operator: Callable[[str], tuple[str, frozenset[str]] | None] | None = None,
) -> pilot.PilotEvaluationOutcome:
    """Legacy arithmetic fixtures explicitly supply their matching auditor projection."""
    return pilot.evaluate_attempt_registry(
        policy,
        attempts,
        resolve_operator,
        ledger_projection=matching_projection(attempts),
        ledger_digest="e" * 64,
    )


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def commitment_digest(groups: list[dict[str, object]]) -> str:
    """Test-side membership encoding, independent of the evaluator implementation."""
    membership = sorted(
        (
            str(group["solverId"]),
            str(group["groupId"]),
            sorted(str(rollout["rolloutId"]) for rollout in group_rollouts(group)),
        )
        for group in groups
    )
    return hashlib.sha256(canonical(membership)).hexdigest()


def policy_document(
    *,
    budget: int = 2,
    corrected_bound: float | None = None,
    measured_ceiling: float | None = None,
) -> bytes:
    value: dict[str, object] = {
        "schemaVersion": POLICY_SCHEMA,
        "pilotId": PILOT_ID,
        "taskHash": TASK_HASH,
        "solverRegistryDigest": REGISTRY_DIGEST,
        "familywiseConfidence": 0.95,
        "attemptBudget": budget,
        "primarySolverIds": list(SOLVERS),
        "stoppingRule": "fixed_attempt_budget",
        "groupSize": 8,
        "groupCount": 10,
        "comparisonFamily": budget * len(SOLVERS),
        "permittedLooks": 1,
        "maxAffectedGroupFraction": [1, 10],
        "harnessConfigDigest": "c" * 64,
        "executionFidelityRequired": True,
    }
    if corrected_bound is not None:
        value["correctedTaskBound"] = corrected_bound
    if measured_ceiling is not None:
        value["measuredPassCeiling"] = measured_ceiling
    return canonical(value)


def test_policy_tiny_ceiling_is_refused_quickly() -> None:
    # Given: a syntactically valid policy with an unsupported tiny ceiling.
    document = policy_document(measured_ceiling=1e-20)
    code = (
        "from tools.pilot import parse_pilot_policy\n"
        f"result = parse_pilot_policy({document!r})\n"
        "assert result.policy is None\n"
        "assert result.outcome.reason.value == 'PILOT_MEASURED_CEILING_INVALID', result\n"
    )
    # When: invoke the public parser under a hard wall-clock limit.
    result = subprocess.run(
        [sys.executable, "-c", code], timeout=2, capture_output=True, check=False
    )
    # Then: the ceiling receives its own refusal, without hanging.
    assert result.returncode == 0, result.stderr.decode()


def attempt_record(
    sequence: int,
    previous_digest: str,
    *,
    groups: list[dict[str, object]] | None = None,
    task_hash: str = TASK_HASH,
    registry_digest: str = REGISTRY_DIGEST,
) -> dict[str, object]:
    record: dict[str, object] = {
        "schemaVersion": ATTEMPT_SCHEMA,
        "sequence": sequence,
        "pilotId": PILOT_ID,
        "attemptId": derive_attempt_id(PILOT_ID, task_hash, sequence, registry_digest),
        "taskHash": task_hash,
        "solverRegistryDigest": registry_digest,
        "startedAt": f"2026-09-0{sequence}T00:00:00Z",
        "endedAt": f"2026-09-0{sequence}T00:01:00Z",
        "solverGroups": groups
        if groups is not None
        else solver_groups("solver-a") + solver_groups("solver-b"),
        "harnessConfigDigest": "c" * 64,
        "groupCommitmentDigest": commitment_digest(
            groups if groups is not None else solver_groups("solver-a") + solver_groups("solver-b")
        ),
        "fidelityLedgerDigest": "e" * 64,
        "executionAttestationDigest": f"{sequence}" * 64,
        "previousRecordDigest": previous_digest,
    }
    record["recordDigest"] = hashlib.sha256(canonical(record)).hexdigest()
    return record


def registry_records(count: int = 2) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    previous = GENESIS_DIGEST
    for sequence in range(1, count + 1):
        groups = [
            group
            for solver in SOLVERS
            for index, group in enumerate(solver_groups(solver))
            if index % count == sequence - 1
        ]
        record = attempt_record(sequence, previous, groups=groups)
        records.append(record)
        previous = str(record["recordDigest"])
    return records


def registry_document(records: list[dict[str, object]]) -> bytes:
    return b"".join(canonical(record) + b"\n" for record in records)


def parsed_policy(
    *,
    budget: int = 2,
    corrected_bound: float | None = None,
    measured_ceiling: float | None = None,
) -> PilotPolicy:
    result = parse_pilot_policy(
        policy_document(
            budget=budget, corrected_bound=corrected_bound, measured_ceiling=measured_ceiling
        )
    )
    assert result.policy is not None
    return result.policy


def breaching_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    previous = GENESIS_DIGEST
    for sequence in (1, 2):
        record = attempt_record(
            sequence,
            previous,
            groups=[
                group
                for solver in SOLVERS
                for index, group in enumerate(
                    solver_groups(solver, successes=40 if solver == "solver-a" else 0)
                )
                if index % 2 == sequence - 1
            ],
        )
        records.append(record)
        previous = str(record["recordDigest"])
    return records


def parsed_attempts(records: list[dict[str, object]]) -> tuple[PilotAttempt, ...]:
    result = parse_attempt_registry(registry_document(records))
    assert result.attempts is not None
    return result.attempts


def redigest(record: dict[str, object]) -> None:
    body = {key: value for key, value in record.items() if key != "recordDigest"}
    record["recordDigest"] = hashlib.sha256(canonical(body)).hexdigest()


def test_clean_two_attempt_two_solver_registry_uses_hand_computed_corrected_bound() -> None:
    outcome = evaluate_attempt_registry(parsed_policy(), parsed_attempts(registry_records()))
    # m = 2 attempts * 2 solvers = 4; C_each = 1 - (1 - .95) / 4 = .9875.
    # Each solver has X*=0, N=10; rollouts are descriptive, not binomial trials.
    expected = 1.0 - 0.0125 ** (1.0 / 10.0)
    assert outcome.accepted
    assert not outcome.provisional
    assert outcome.comparisons == 4
    assert outcome.per_comparison_confidence == 0.9875
    assert outcome.corrected_task_bound == pytest.approx(expected, abs=1e-12)


def test_declared_uncorrected_bound_is_refused() -> None:
    uncorrected = 1.0 - 0.05 ** (1.0 / 160.0)
    outcome = evaluate_attempt_registry(
        parsed_policy(corrected_bound=uncorrected), parsed_attempts(registry_records())
    )
    assert outcome.reason is PilotFailureReason.PILOT_CORRECTED_BOUND_MISMATCH


def test_omitted_primary_solver_is_refused() -> None:
    records = registry_records()
    records[1]["solverGroups"] = solver_groups("solver-a")
    redigest(records[1])
    outcome = evaluate_attempt_registry(parsed_policy(), parsed_attempts(records))
    assert outcome.reason is PilotFailureReason.PILOT_ATTEMPT_SET_INCOMPLETE


def test_sequence_gap_is_refused() -> None:
    records = registry_records()
    records[1] = attempt_record(3, str(records[0]["recordDigest"]))
    outcome = evaluate_attempt_registry(parsed_policy(), parsed_attempts(records))
    assert outcome.reason is PilotFailureReason.PILOT_ATTEMPT_CHAIN_INVALID


def test_chain_tamper_is_refused() -> None:
    records = registry_records()
    records[1]["previousRecordDigest"] = "f" * 64
    redigest(records[1])
    outcome = evaluate_attempt_registry(parsed_policy(), parsed_attempts(records))
    assert outcome.reason is PilotFailureReason.PILOT_ATTEMPT_CHAIN_INVALID


def test_record_digest_tamper_is_refused_by_parser() -> None:
    records = registry_records()
    records[0]["recordDigest"] = "f" * 64
    parsed = parse_attempt_registry(registry_document(records))
    assert parsed.outcome.reason is PilotFailureReason.PILOT_ATTEMPT_CHAIN_INVALID


def test_attempt_budget_excess_is_refused() -> None:
    outcome = evaluate_attempt_registry(parsed_policy(), parsed_attempts(registry_records(3)))
    assert outcome.reason is PilotFailureReason.PILOT_ATTEMPT_BUDGET_EXCEEDED


def test_digest_disagreement_with_policy_is_refused() -> None:
    records = registry_records()
    records[1] = attempt_record(2, str(records[0]["recordDigest"]), task_hash="c" * 64)
    outcome = evaluate_attempt_registry(parsed_policy(), parsed_attempts(records))
    assert outcome.reason is PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED


def test_unknown_attempt_field_is_refused() -> None:
    records = registry_records()
    records[0]["surprise"] = True
    parsed = parse_attempt_registry(registry_document(records))
    assert parsed.outcome.reason is PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    assert "unknown fields" in parsed.outcome.detail


def test_fewer_realized_attempts_keep_bound_provisional_and_use_full_budget() -> None:
    policy = parsed_policy(budget=3)
    outcome = evaluate_attempt_registry(policy, parsed_attempts(registry_records(1)))
    assert outcome.accepted
    assert outcome.provisional
    assert outcome.comparisons == 6
    assert outcome.per_comparison_confidence == pytest.approx(1.0 - 0.05 / 6.0)


def test_parent_check_allows_absent_unclaimed_pilot(tmp_path: Path) -> None:
    assert check_pilot_attempt_registry(str(tmp_path)) == []


def test_parent_check_flags_policy_without_registry(tmp_path: Path) -> None:
    seed = tmp_path / ".seed"
    seed.mkdir()
    (seed / "pilot-policy.json").write_bytes(policy_document())
    findings = check_pilot_attempt_registry(str(tmp_path))
    assert [finding.code for finding in findings] == ["PILOT_ATTEMPT_REGISTRY_MISSING"]


def test_parent_check_flags_declared_bound_mismatch(tmp_path: Path) -> None:
    seed = tmp_path / ".seed"
    seed.mkdir()
    uncorrected = 1.0 - 0.05 ** (1.0 / 160.0)
    (seed / "pilot-policy.json").write_bytes(policy_document(corrected_bound=uncorrected))
    records = registry_records()
    bind_registry_ledger(tmp_path, records)
    (seed / "pilot-attempts.jsonl").write_bytes(registry_document(records))
    findings = check_pilot_attempt_registry(str(tmp_path))
    assert [finding.code for finding in findings] == ["PILOT_CORRECTED_BOUND_MISMATCH"]


def test_measured_headroom_breach_is_refused() -> None:
    # Planted positive: solver-a accumulates 80/160, whose CP upper bound exceeds 0.40.
    policy = parsed_policy(measured_ceiling=0.40)
    outcome = evaluate_attempt_registry(policy, parsed_attempts(breaching_records()))
    assert not outcome.accepted
    assert outcome.reason is PilotFailureReason.PILOT_MEASURED_HEADROOM_BREACH


def test_measured_headroom_clean_bound_below_ceiling_is_accepted() -> None:
    # Clean fixture: 0/160 per solver keeps the corrected bound near 0.027, below 0.40.
    policy = parsed_policy(measured_ceiling=0.40)
    outcome = evaluate_attempt_registry(policy, parsed_attempts(registry_records()))
    assert outcome.accepted
    assert outcome.corrected_task_bound is not None
    assert outcome.corrected_task_bound < 0.40


def test_measured_headroom_breach_on_provisional_registry_is_refused() -> None:
    policy = parsed_policy(budget=3, measured_ceiling=0.40)
    outcome = evaluate_attempt_registry(policy, parsed_attempts(breaching_records()))
    assert outcome.reason is PilotFailureReason.PILOT_MEASURED_HEADROOM_BREACH


def test_policy_without_ceiling_enforces_default_headroom() -> None:
    outcome = evaluate_attempt_registry(parsed_policy(), parsed_attempts(breaching_records()))
    assert outcome.reason is PilotFailureReason.PILOT_MEASURED_HEADROOM_BREACH


@pytest.mark.parametrize("ceiling", [0.0, -0.1, 0.41, 1.0])
def test_out_of_range_measured_ceiling_is_refused(ceiling: float) -> None:
    parsed = parse_pilot_policy(policy_document(measured_ceiling=ceiling))
    assert parsed.policy is None
    assert parsed.outcome.reason is PilotFailureReason.PILOT_MEASURED_CEILING_INVALID


def test_non_float_measured_ceiling_is_refused() -> None:
    value = json.loads(policy_document())
    value["measuredPassCeiling"] = "0.4"
    parsed = parse_pilot_policy(canonical(value))
    assert parsed.policy is None
    assert parsed.outcome.reason is PilotFailureReason.PILOT_MEASURED_CEILING_INVALID


def test_parent_check_flags_measured_headroom_breach(tmp_path: Path) -> None:
    seed = tmp_path / ".seed"
    seed.mkdir()
    (seed / "pilot-policy.json").write_bytes(policy_document(measured_ceiling=0.40))
    records = breaching_records()
    bind_registry_ledger(tmp_path, records)
    (seed / "pilot-attempts.jsonl").write_bytes(registry_document(records))
    findings = check_pilot_attempt_registry(str(tmp_path))
    assert [finding.code for finding in findings] == ["PILOT_MEASURED_HEADROOM_BREACH"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update({"unknown": True}),
        lambda value: value.pop("attemptBudget"),
    ],
)
def test_policy_refuses_unknown_and_missing_fields(
    mutate: Callable[[dict[str, object]], object],
) -> None:
    value = json.loads(policy_document())
    mutate(value)
    parsed = parse_pilot_policy(canonical(value))
    assert parsed.outcome.reason is PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED


def v2_policy_value() -> dict[str, object]:
    value: dict[str, object] = json.loads(policy_document())
    value.update(
        schemaVersion="trinity.pilot-policy/v2",
        primarySolverIds=["a", "b", "c", "d"],
        groupSize=8,
        groupCount=10,
        comparisonFamily=8,
        permittedLooks=1,
        maxAffectedGroupFraction=[1, 10],
        harnessConfigDigest="c" * 64,
        executionFidelityRequired=True,
    )
    return value


def test_policy_refuses_v1_schema_version() -> None:
    # Given: the original v1 field set and version, without v2 declarations.
    value = v2_policy_value()
    for field in (
        "groupSize",
        "groupCount",
        "comparisonFamily",
        "permittedLooks",
        "maxAffectedGroupFraction",
        "harnessConfigDigest",
        "executionFidelityRequired",
    ):
        del value[field]
    value["schemaVersion"] = "trinity.pilot-policy/v1"
    value["primarySolverIds"] = list(SOLVERS)
    # When: parsing the legacy policy.
    parsed = parse_pilot_policy(canonical(value))
    # Then: the downgrade refusal names the refused version.
    assert parsed.outcome.reason == "PILOT_SCHEMA_VERSION_UNSUPPORTED"
    assert "trinity.pilot-policy/v1" in parsed.outcome.detail


def test_policy_refuses_v1_before_field_validation() -> None:
    # Given: a v1 document with missing and forbidden fields.
    value = {"schemaVersion": "trinity.pilot-policy/v1", "reasonCode": "private"}
    # When: parsing it.
    parsed = parse_pilot_policy(canonical(value))
    # Then: version refusal takes precedence over field validation.
    assert parsed.outcome.reason == "PILOT_SCHEMA_VERSION_UNSUPPORTED"
    assert "trinity.pilot-policy/v1" in parsed.outcome.detail


@pytest.mark.parametrize("group_size", [1, 4, 7, 9, 16])
def test_policy_refuses_group_size_other_than_eight(group_size: int) -> None:
    # Given: a non-eight group size.
    value = v2_policy_value()
    value["groupSize"] = group_size
    # When: parsing it.
    parsed = parse_pilot_policy(canonical(value))
    # Then: group structure is refused.
    assert parsed.outcome.reason == "PILOT_GROUP_STRUCTURE_INVALID"


def test_policy_refuses_comparison_family_mismatch() -> None:
    # Given: a declared family smaller than two attempts times four solvers.
    value = v2_policy_value()
    value["comparisonFamily"] = 4
    # When: parsing it.
    parsed = parse_pilot_policy(canonical(value))
    # Then: the correction cannot use the underdeclared family.
    assert parsed.outcome.reason is PilotFailureReason.PILOT_CORRECTION_INVALID


def test_policy_refuses_infeasible_group_count() -> None:
    # Given: eight groups at comparison family eight, with no explicit ceiling.
    value = v2_policy_value()
    value["groupCount"] = 8
    # When: parsing before any outcomes exist.
    parsed = parse_pilot_policy(canonical(value))
    # Then: the refusal names both the declared and required counts.
    assert parsed.outcome.reason == "PILOT_INFEASIBLE_GROUP_COUNT"
    assert "8" in parsed.outcome.detail
    assert "10" in parsed.outcome.detail


def test_policy_accepts_feasible_group_count() -> None:
    # Given: ten groups at comparison family eight.
    value = v2_policy_value()
    # When: parsing the predeclared policy.
    parsed = parse_pilot_policy(canonical(value))
    # Then: all new bindings survive as typed fields, including an exact fraction.
    assert parsed.outcome.accepted
    assert parsed.policy is not None
    assert parsed.policy.schema_version == "trinity.pilot-policy/v2"
    assert parsed.policy.group_size == 8
    assert parsed.policy.group_count == 10
    assert parsed.policy.comparison_family == 8
    assert parsed.policy.permitted_looks == 1
    assert parsed.policy.max_affected_group_fraction == Fraction(1, 10)
    assert parsed.policy.harness_config_digest == "c" * 64
    assert parsed.policy.execution_fidelity_required is True


@pytest.mark.parametrize("digest", [None, "abc", "A" * 64])
def test_policy_refuses_unbound_harness_config(digest: str | None) -> None:
    # Given: an absent, short, or uppercase digest.
    value = v2_policy_value()
    if digest is None:
        del value["harnessConfigDigest"]
    else:
        value["harnessConfigDigest"] = digest
    # When: parsing it.
    parsed = parse_pilot_policy(canonical(value))
    # Then: configuration binding is refused by name.
    assert parsed.outcome.reason == "PILOT_HARNESS_CONFIG_UNBOUND"
    assert "harnessConfigDigest" in parsed.outcome.detail


@pytest.mark.parametrize("required", [False, "true", None])
def test_policy_refuses_fidelity_not_required(required: bool | str | None) -> None:
    # Given: anything other than boolean true.
    value = v2_policy_value()
    if required is None:
        del value["executionFidelityRequired"]
    else:
        value["executionFidelityRequired"] = required
    # When: parsing it.
    parsed = parse_pilot_policy(canonical(value))
    # Then: the refusal names the missing fidelity requirement.
    assert parsed.outcome.reason == "PILOT_HARNESS_CONFIG_UNBOUND"
    assert "executionFidelityRequired" in parsed.outcome.detail


@pytest.mark.parametrize("field", ["reasonCode", "reason", "suppressionReason", "fidelityDetail"])
def test_policy_refuses_forbidden_reason_fields(field: str) -> None:
    # Given: a policy carrying private reason vocabulary.
    value = v2_policy_value()
    value[field] = "private"
    # When: parsing it.
    parsed = parse_pilot_policy(canonical(value))
    # Then: the malformed-policy refusal identifies the forbidden key.
    assert parsed.outcome.reason is PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    assert field in parsed.outcome.detail
    assert "forbidden" in parsed.outcome.detail


def solver_groups(solver_id: str, successes: int = 0) -> list[dict[str, object]]:
    return [
        {
            "solverId": solver_id,
            "groupId": f"{solver_id}-g-{group}",
            "rollouts": [
                {
                    "rolloutId": f"{solver_id}-r-{group * 8 + rollout:02}",
                    "outcome": "success" if group * 8 + rollout < successes else "failure",
                    "trialStatus": "conforming",
                }
                for rollout in range(8)
            ],
        }
        for group in range(10)
    ]


def v2_attempt_value() -> dict[str, object]:
    value = attempt_record(1, GENESIS_DIGEST)
    value.update(
        schemaVersion="trinity.pilot-attempt/v2",
        solverGroups=solver_groups("solver-a") + solver_groups("solver-b"),
        harnessConfigDigest="c" * 64,
        fidelityLedgerDigest="e" * 64,
    )
    redigest(value)
    return value


def attempt_groups(value: dict[str, object]) -> list[dict[str, object]]:
    groups = value["solverGroups"]
    assert isinstance(groups, list)
    return groups


def group_rollouts(group: dict[str, object]) -> list[dict[str, object]]:
    rollouts = group["rollouts"]
    assert isinstance(rollouts, list)
    return rollouts


def test_attempt_refuses_v1_schema_first() -> None:
    # Given: a legacy version on an otherwise valid v2 body.
    value = v2_attempt_value()
    value["schemaVersion"] = "trinity.pilot-attempt/v1"
    redigest(value)
    # When: parsing the legacy declaration before inspecting its fields.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: schema refusal takes precedence over the new field set.
    assert parsed.outcome.reason == "PILOT_SCHEMA_VERSION_UNSUPPORTED"


@pytest.mark.parametrize("size", [7, 9])
def test_attempt_refuses_wrong_group_size(size: int) -> None:
    # Given: a group with one missing or additional rollout.
    value = v2_attempt_value()
    rollouts = group_rollouts(attempt_groups(value)[0])
    rollouts.append({"rolloutId": "extra", "outcome": "failure", "trialStatus": "conforming"})
    del rollouts[size:]
    redigest(value)
    # When: parsing the malformed group.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: size, not outcome accounting, is refused.
    assert parsed.outcome.reason == "PILOT_GROUP_STRUCTURE_INVALID"
    assert str(size) in parsed.outcome.detail


def test_attempt_refuses_duplicate_group_id() -> None:
    # Given: two different populations claiming the same solver's group identity.
    value = v2_attempt_value()
    groups = attempt_groups(value)
    groups[1]["groupId"] = groups[0]["groupId"]
    redigest(value)
    # When: parsing duplicate group membership.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: the duplicate group is distinguished from rollout reuse.
    assert parsed.outcome.reason == "PILOT_GROUP_STRUCTURE_INVALID"
    assert "duplicate groupId" in parsed.outcome.detail
    assert str(groups[0]["groupId"]) in parsed.outcome.detail


def test_attempt_refuses_duplicate_rollout_within_group() -> None:
    # Given: one rollout counted twice within a group.
    value = v2_attempt_value()
    rollouts = group_rollouts(attempt_groups(value)[0])
    rollouts[1]["rolloutId"] = rollouts[0]["rolloutId"]
    redigest(value)
    # When: parsing the group.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: within-group duplication is identified explicitly.
    assert parsed.outcome.reason == "PILOT_GROUP_STRUCTURE_INVALID"
    assert "duplicate rolloutId" in parsed.outcome.detail
    assert "within group" in parsed.outcome.detail


def test_attempt_refuses_rollout_shared_across_groups() -> None:
    # Given: group two reuses a member of group one.
    value = v2_attempt_value()
    groups = attempt_groups(value)
    group_rollouts(groups[0])[3]["rolloutId"] = "r-03"
    group_rollouts(groups[1])[0]["rolloutId"] = "r-03"
    redigest(value)
    # When: parsing overlapping populations.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: the distinct disjointness refusal names both groups and their shared member.
    assert parsed.outcome.reason == "PILOT_GROUP_STRUCTURE_INVALID"
    assert "shared across groups" in parsed.outcome.detail
    assert "r-03" in parsed.outcome.detail
    assert all(str(group["groupId"]) in parsed.outcome.detail for group in groups[:2])


@pytest.mark.parametrize("outcome", ["pass", "error", ""])
def test_attempt_refuses_unknown_outcome(outcome: str) -> None:
    # Given: an outcome outside the two-token vocabulary.
    value = v2_attempt_value()
    group_rollouts(attempt_groups(value)[0])[0]["outcome"] = outcome
    redigest(value)
    # When: parsing, without coercing a spelling.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: the closed trial vocabulary refuses it.
    assert parsed.outcome.reason == "PILOT_TRIAL_STATUS_UNKNOWN"


@pytest.mark.parametrize("status", ["valid", "invalid", "unknown", ""])
def test_attempt_refuses_unknown_trial_status(status: str) -> None:
    # Given: an unofficial conformance token.
    value = v2_attempt_value()
    group_rollouts(attempt_groups(value)[0])[0]["trialStatus"] = status
    redigest(value)
    # When: parsing the operator's declaration.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: no alias is accepted.
    assert parsed.outcome.reason == "PILOT_TRIAL_STATUS_UNKNOWN"


@pytest.mark.parametrize("field", ["reasonCode", "reason", "suppressionReason", "fidelityDetail"])
@pytest.mark.parametrize("depth", ["top level", "group", "rollout"])
def test_attempt_refuses_forbidden_reason_field_at_every_depth(field: str, depth: str) -> None:
    # Given: private reason data at one of the three schema depths.
    value = v2_attempt_value()
    group = attempt_groups(value)[0]
    destinations = {"top level": value, "group": group, "rollout": group_rollouts(group)[0]}
    destinations[depth][field] = "private"
    redigest(value)
    # When: parsing a reason-bearing registry.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: diagnostics name the forbidden key and depth, never its private value.
    assert parsed.outcome.reason == "PILOT_ATTEMPT_REGISTRY_MALFORMED"
    assert "forbidden" in parsed.outcome.detail
    assert field in parsed.outcome.detail
    assert depth in parsed.outcome.detail
    assert "private" not in parsed.outcome.detail


def test_attempt_refuses_harness_config_digest_mismatch(tmp_path: Path) -> None:
    # Given: an attempt bound to a different valid digest than its policy.
    value = v2_attempt_value()
    value["harnessConfigDigest"] = "f" * 64
    redigest(value)
    seed = tmp_path / ".seed"
    seed.mkdir()
    (seed / "pilot-policy.json").write_bytes(policy_document())
    (seed / "pilot-attempts.jsonl").write_bytes(registry_document([value]))
    # When: the parent check parses the registry against its policy.
    findings = check_pilot_attempt_registry(str(tmp_path))
    # Then: a valid but unbound digest cannot pass.
    assert [finding.code for finding in findings] == ["PILOT_HARNESS_CONFIG_UNBOUND"]


def test_attempt_accepts_well_formed_v2_registry() -> None:
    # Given: ten disjoint groups of eight rollouts for each of two solvers.
    value = v2_attempt_value()
    # When: parsing the canonical registry.
    parsed = parse_attempt_registry(registry_document([value]))
    # Then: the complete typed population and bindings survive parsing.
    assert parsed.outcome.accepted
    assert parsed.attempts is not None
    assert parsed.attempts[0].solver_groups == tuple(
        pilot.SolverGroup(
            solver,
            f"{solver}-g-{group}",
            tuple(
                pilot.RolloutRecord(f"{solver}-r-{group * 8 + rollout:02}", "failure", "conforming")
                for rollout in range(8)
            ),
        )
        for solver in SOLVERS
        for group in range(10)
    )
    assert parsed.attempts[0].harness_config_digest == "c" * 64
    assert parsed.attempts[0].group_commitment_digest == commitment_digest(attempt_groups(value))
    assert parsed.attempts[0].fidelity_ledger_digest == "e" * 64


def accounting_attempt(*, affected: int = 0, count: int = 10) -> tuple[PilotAttempt, ...]:
    """Build one fixed population; status changes never erase a member."""
    groups = [
        pilot.SolverGroup(
            solver,
            f"{solver}-g-{index}",
            tuple(
                pilot.RolloutRecord(
                    f"{solver}-r-{index}-{member}",
                    "failure",
                    "nonconforming" if index < affected and member == 0 else "conforming",
                )
                for member in range(8)
            ),
        )
        for solver in SOLVERS
        for index in range(count)
    ]
    membership = sorted(
        (group.solver_id, group.group_id, sorted(r.rollout_id for r in group.rollouts))
        for group in groups
    )
    return (
        replace(
            parsed_attempts(registry_records(1))[0],
            solver_groups=tuple(groups),
            group_commitment_digest=hashlib.sha256(canonical(membership)).hexdigest(),
        ),
    )


def test_evaluator_uses_worst_case_group_indicator() -> None:
    # Given: group three has one indeterminate failure, all other members conform.
    attempts = accounting_attempt(count=20)
    groups = list(attempts[0].solver_groups)
    group = groups[3]
    groups[3] = replace(
        group,
        rollouts=(replace(group.rollouts[0], trial_status="indeterminate"), *group.rollouts[1:]),
    )
    # When: evaluating the whole population.
    result = evaluate_attempt_registry(
        replace(parsed_policy(budget=1), group_count=20),
        (replace(attempts[0], solver_groups=tuple(groups)),),
    )
    # Then: uncertainty contributes one worst-case group success.
    assert result.accepted
    assert result.solver_bounds[0].group_successes == 1


def test_evaluator_counts_nonconforming_against_release() -> None:
    # Given: zero raw successes, but two affected groups, within governance tolerance.
    policy = replace(
        parsed_policy(budget=1, measured_ceiling=0.40), max_affected_group_fraction=Fraction(3, 10)
    )
    # When: evaluating at the release ceiling.
    result = evaluate_attempt_registry(policy, accounting_attempt(affected=2))
    # Then: suppression raises the bound above the ceiling, reversing the incentive.
    assert result.reason == "PILOT_MEASURED_HEADROOM_BREACH"


@pytest.mark.parametrize("affected", [0, 1, 2, 10])
def test_evaluator_never_drops_invalid_groups(affected: int) -> None:
    # Given: an admitted population whose affected count varies.
    policy = replace(
        parsed_policy(budget=1), group_count=100, max_affected_group_fraction=Fraction(1)
    )
    # When: computing descriptive and group accounting.
    result = evaluate_attempt_registry(policy, accounting_attempt(count=100, affected=affected))
    # Then: all groups remain in N, and each affected group contributes to X*.
    assert result.accepted
    assert [(bound.group_successes, bound.group_count) for bound in result.solver_bounds] == [
        (affected, 100)
    ] * 2


@pytest.mark.parametrize("realized", [9, 11])
def test_evaluator_refuses_realized_group_count_mismatch(realized: int) -> None:
    # Given: the policy fixes ten groups regardless of observed outcomes.
    policy = parsed_policy(budget=1)
    # When: submitting a different population.
    result = evaluate_attempt_registry(policy, accounting_attempt(count=realized))
    # Then: refusal names both the realized and declared counts.
    assert result.reason == "PILOT_GROUP_POPULATION_MUTATED"
    assert str(realized) in result.detail and "10" in result.detail


def test_evaluator_refuses_duplicate_group_across_attempts() -> None:
    # Given: otherwise disjoint attempts reusing one solver's group identity.
    records = registry_records()
    attempt_groups(records[1])[0]["groupId"] = attempt_groups(records[0])[0]["groupId"]
    redigest(records[1])
    # When: evaluating across the attempt boundary.
    result = evaluate_attempt_registry(parsed_policy(), parsed_attempts(records))
    # Then: duplicate identity cannot create an independent observation.
    assert result.reason == "PILOT_GROUP_STRUCTURE_INVALID"


def test_evaluator_refuses_excess_affected_fraction() -> None:
    # Given: governance tolerates at most three affected groups out of ten.
    policy = replace(parsed_policy(budget=1), max_affected_group_fraction=Fraction(3, 10))
    # When: four groups are affected.
    result = evaluate_attempt_registry(policy, accounting_attempt(affected=4))
    # Then: exact rationals, including the observed population tally, name the breach.
    assert result.reason == "PILOT_SUPPRESSION_FRACTION_EXCEEDED"
    assert "4/10" in result.detail and "3/10" in result.detail


def test_affected_fraction_compared_as_exact_rational() -> None:
    # Given: three hundred groups, with an exact one-third governance maximum.
    policy = replace(
        parsed_policy(budget=1), group_count=300, max_affected_group_fraction=Fraction(1, 3)
    )
    # When: exactly one third are affected and the bound is below the effective ceiling.
    result = evaluate_attempt_registry(policy, accounting_attempt(count=300, affected=100))
    # Then: equality is accepted without floating-point drift.
    assert result.accepted
    assert result.solver_bounds[0].group_successes == 100


def test_descriptive_rate_cannot_reach_ceiling_comparison() -> None:
    # Given: one verified success per group, a descriptive rate of only 1/8.
    attempts = accounting_attempt()
    groups = tuple(
        replace(
            group, rollouts=(replace(group.rollouts[0], outcome="success"), *group.rollouts[1:])
        )
        for group in attempts[0].solver_groups
    )
    # When: evaluating against 0.40 rather than comparing the descriptive 0.125.
    result = evaluate_attempt_registry(
        parsed_policy(budget=1, measured_ceiling=0.40),
        (replace(attempts[0], solver_groups=groups),),
    )
    # Then: every group flags, so release is refused.
    assert result.reason == "PILOT_MEASURED_HEADROOM_BREACH"


@pytest.mark.parametrize("operator", ["author", "independent-runner"])
def test_evaluator_refuses_self_asserted_operator(operator: str) -> None:
    # Given: resolution is keyed by the exact attempt's attestation digest.
    attempts = accounting_attempt()
    resolutions = {
        attempts[0].execution_attestation_digest: (operator, frozenset({"author", "auditor"}))
    }
    # When: evaluating with the repository's signer resolution.
    result = evaluate_attempt_registry(parsed_policy(budget=1), attempts, resolutions.get)
    # Then: an independent operator is allowed, the repository's own signer is not.
    assert result.accepted == (operator == "independent-runner")
    if operator == "author":
        assert result.reason == "PILOT_OPERATOR_SELF_ASSERTED"


@pytest.mark.parametrize("surface", ["registry", "EDICT.md", "VERDICT.md", "DIRECTIVE.md"])
def test_registry_check_refuses_missing_policy_when_pilot_declared(
    tmp_path: Path, surface: str
) -> None:
    # Given: pilot evidence is declared with no policy.
    if surface == "registry":
        (tmp_path / ".seed").mkdir()
        (tmp_path / ".seed/pilot-attempts.jsonl").write_bytes(registry_document(registry_records()))
    else:
        (tmp_path / surface).write_text(
            "Pilot evidence: executionAttestationDigest: " + "a" * 64 + "\n"
        )
    # When: running the parent check.
    findings = check_pilot_attempt_registry(str(tmp_path))
    # Then: no policy is a missing-registry refusal, never silent acceptance.
    assert [finding.code for finding in findings] == ["PILOT_ATTEMPT_REGISTRY_MISSING"]


def test_full_bound_is_one_when_every_group_flags() -> None:
    # Given: every group's outcomes are untrustworthy, with no fraction restriction.
    policy = replace(parsed_policy(budget=1), max_affected_group_fraction=Fraction(1))
    attempts = accounting_attempt(affected=10)
    # When: obtaining the full-success boundary and applying its ceiling.
    result = evaluate_attempt_registry(policy, attempts)
    # Then: U is exactly one, and release is refused.
    assert pilot.SolverBound("solver-a", 0, 80, 10, 10, 0.975).upper_bound == 1.0
    assert result.reason == "PILOT_MEASURED_HEADROOM_BREACH"
    assert "1.000000" in result.detail


def test_evaluator_checks_minimum_groups_without_reparsing_policy() -> None:
    # Given: a typed policy with an infeasible count, not sent through the parser.
    policy = replace(parsed_policy(budget=1), group_count=2)
    # When: invoking the evaluator directly.
    result = evaluate_attempt_registry(policy, accounting_attempt(count=2))
    # Then: evaluator feasibility is independently enforced.
    assert result.reason == "PILOT_INFEASIBLE_GROUP_COUNT"


@pytest.mark.parametrize("operator", ["author", "independent-runner"])
def test_parent_check_resolves_operator_from_digest_bound_envelope(
    tmp_path: Path, operator: str
) -> None:
    # Given: a v2 execution envelope and a separate repository signer roster on disk.
    statement = valid_execution_v2()
    predicate = statement["predicate"]
    assert isinstance(predicate, dict)
    predicate["operatorIdentity"] = operator
    envelope = canonical(
        {
            "payloadType": "application/vnd.in-toto+json",
            "payload": base64.b64encode(canonical(statement)).decode(),
            "signatures": [{"sig": base64.b64encode(b"parser-only fixture").decode()}],
        }
    )
    digest = hashlib.sha256(envelope).hexdigest()
    directory = tmp_path / ".audit/attestations/execution"
    directory.mkdir(parents=True)
    (directory / f"{digest}.dsse").write_bytes(envelope)
    memory = tmp_path / ".memory"
    memory.mkdir()
    (memory / "roots.yaml").write_bytes(
        canonical(
            {
                "version": 1,
                "expires": "2030-01-01T00:00:00Z",
                "roles": [{"name": "gate_producer", "threshold": 1}],
                "principals": [{"name": "author", "roles": ["gate_producer"]}],
                "revocations": [],
            }
        )
    )
    seed = tmp_path / ".seed"
    seed.mkdir()
    record = registry_records(1)[0]
    record["executionAttestationDigest"] = digest
    redigest(record)
    bind_registry_ledger(tmp_path, [record])
    (seed / "pilot-policy.json").write_bytes(policy_document(budget=1, measured_ceiling=0.40))
    (seed / "pilot-attempts.jsonl").write_bytes(registry_document([record]))
    # When: checking the real parent surface, without replacing its resolution helper.
    findings = integrity.check_pilot_attempt_registry(str(tmp_path))
    # Then: only the local operator is refused; signature verification is a separate gate.
    assert [finding.code for finding in findings] == (
        ["PILOT_OPERATOR_SELF_ASSERTED"] if operator == "author" else []
    )


def test_solver_bound_excludes_descriptive_fields_from_upper_bound() -> None:
    # Given: an evaluated group bound with descriptive rollout totals.
    result = evaluate_attempt_registry(parsed_policy(budget=1), accounting_attempt())
    bound = result.solver_bounds[0]
    # When: descriptive totals change while the group evidence stays identical.
    changed = replace(bound, cumulative_successes=8000, cumulative_trials=8000)
    # Then: the release statistic is structurally independent of those fields.
    assert changed.upper_bound == bound.upper_bound


def test_parent_check_refuses_unresolved_execution_operator(tmp_path: Path) -> None:
    # Given: numerically clean pilot evidence but no referenced execution envelope.
    seed = tmp_path / ".seed"
    seed.mkdir()
    (seed / "pilot-policy.json").write_bytes(policy_document(budget=1))
    records = registry_records(1)
    bind_registry_ledger(tmp_path, records)
    (seed / "pilot-attempts.jsonl").write_bytes(registry_document(records))
    # When: checking the parent rather than requesting arithmetic alone.
    findings = check_pilot_attempt_registry(str(tmp_path))
    # Then: missing operator resolution is never independent evidence.
    assert [finding.code for finding in findings] == ["PILOT_ATTEMPT_ATTESTATION_MISMATCH"]


@pytest.mark.parametrize("cross_solver", [False, True])
def test_evaluator_refuses_rollout_reuse_across_attempts(cross_solver: bool) -> None:
    # Given: distinct groups reuse all forty rollouts from an earlier attempt.
    records = registry_records()
    first = attempt_groups(records[0])
    second = attempt_groups(records[1])
    for index in range(5):
        second[index]["rollouts"] = group_rollouts(first[index + (5 if cross_solver else 0)])
    records[1]["groupCommitmentDigest"] = commitment_digest(second)
    redigest(records[1])
    # When: aggregating across the attempt boundary.
    result = evaluate_attempt_registry(parsed_policy(), parsed_attempts(records))
    # Then: reusing an observation cannot increase N, even under another solver.
    assert result.reason is PilotFailureReason.PILOT_GROUP_STRUCTURE_INVALID, result
    original = first[5 if cross_solver else 0]
    assert str(group_rollouts(original)[0]["rolloutId"]) in result.detail
    assert all(str(group["groupId"]) in result.detail for group in (original, second[0]))


@pytest.mark.parametrize("budget", [1, 2])
def test_missing_ceiling_defaults_and_is_enforced(budget: int) -> None:
    # Given: all-success evidence, with no explicit ceiling, complete or provisional.
    groups = solver_groups("solver-a", 80) + solver_groups("solver-b", 80)
    records = [attempt_record(1, GENESIS_DIGEST, groups=groups)]
    policy = parsed_policy(budget=budget)
    # When: applying release arithmetic.
    result = evaluate_attempt_registry(policy, parsed_attempts(records))
    # Then: the implicit ceiling refuses U=1 just as an explicit ceiling does.
    assert result.reason is PilotFailureReason.PILOT_MEASURED_HEADROOM_BREACH, result
    assert policy.measured_pass_ceiling == 0.40


def test_provisional_outcome_never_qualifies(tmp_path: Path) -> None:
    # Given: the existing parser-only external-operator fixture clears the parent check.
    test_parent_check_resolves_operator_from_digest_bound_envelope(tmp_path, "independent-runner")
    (tmp_path / ".seed/pilot-policy.json").write_bytes(policy_document(budget=2))
    # When: the full N is present but the fixed attempt budget is incomplete.
    findings = check_pilot_attempt_registry(str(tmp_path))
    # Then: arithmetic acceptance is non-authorizing while provisional.
    assert [finding.code for finding in findings] == ["PILOT_ATTEMPT_SET_INCOMPLETE"]
    assert "provisional" in findings[0].message


@pytest.mark.parametrize("surface", ["parser", "evaluator"])
def test_group_count_below_eight_refused_even_when_feasible(surface: str) -> None:
    # Given: M=1 permits six groups arithmetically, but the contract requires eight.
    value = json.loads(policy_document(budget=1))
    value.update(primarySolverIds=["solver-a"], comparisonFamily=1, groupCount=6)
    policy = replace(
        parsed_policy(budget=1),
        primary_solver_ids=("solver-a",),
        comparison_family=1,
        group_count=6,
    )
    records = [attempt_record(1, GENESIS_DIGEST, groups=solver_groups("solver-a")[:6])]
    # When: validating either serialized or already typed policy.
    result = (
        parse_pilot_policy(canonical(value)).outcome
        if surface == "parser"
        else evaluate_attempt_registry(policy, parsed_attempts(records))
    )
    # Then: both entry points enforce the eight-group floor.
    assert result.reason is PilotFailureReason.PILOT_INFEASIBLE_GROUP_COUNT, result
    assert "8" in result.detail


@pytest.mark.parametrize("looks", [0, 2, 3, True, 1.0])
def test_permitted_looks_other_than_one_refused(looks: int | float) -> None:
    # Given: a schedule other than the implemented single final look.
    value = json.loads(policy_document())
    value["permittedLooks"] = looks
    # When: parsing the declaration.
    result = parse_pilot_policy(canonical(value))
    # Then: the unsupported field value is refused by name.
    assert result.outcome.reason is PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    assert "permittedLooks" in result.outcome.detail


@pytest.mark.parametrize("regroup", [False, True])
def test_group_commitment_digest_binds_membership(regroup: bool) -> None:
    # Given: a recorded membership commitment, not evidence of when it was made.
    records = registry_records(1)
    groups = attempt_groups(records[0])
    if regroup:
        first, second = group_rollouts(groups[0]), group_rollouts(groups[1])
        first[0], second[0] = second[0], first[0]
    groups.reverse()
    for group in groups:
        group_rollouts(group).reverse()
    redigest(records[0])
    # When: evaluating the same rollouts, possibly regrouped, under the recorded digest.
    result = evaluate_attempt_registry(parsed_policy(budget=1), parsed_attempts(records))
    # Then: order is irrelevant, but membership cannot change unnoticed.
    assert result.accepted is not regroup, result
    if regroup:
        assert result.reason is PilotFailureReason.PILOT_GROUP_POPULATION_MUTATED
        assert "groupCommitmentDigest" in result.detail


def test_evaluator_refuses_without_ledger_projection() -> None:
    # Given: otherwise qualifying operator-supplied evidence.
    attempts = parsed_attempts(registry_records())
    # When: no auditor projection is supplied.
    result = pilot.evaluate_attempt_registry(parsed_policy(), attempts)
    # Then: qualification is impossible.
    assert result.reason == "PILOT_FIDELITY_UNBOUND"


def test_evaluator_refuses_ledger_digest_mismatch() -> None:
    # Given: a projection bound to different ledger bytes.
    attempts = parsed_attempts(registry_records())
    # When: the attempt names another digest.
    result = pilot.evaluate_attempt_registry(
        parsed_policy(),
        attempts,
        ledger_projection=matching_projection(attempts),
        ledger_digest="f" * 64,
    )
    # Then: only the two digests appear in the detail.
    assert result.reason == "PILOT_FIDELITY_UNBOUND"
    assert result.detail == f"{'e' * 64} != {'f' * 64}"


@pytest.mark.parametrize("missing", [False, True])
def test_evaluator_refuses_flipped_trial_status(missing: bool) -> None:
    # Given: the auditor observed a nonconforming trial before the operator's edit.
    records = registry_records(1)
    rollout = group_rollouts(attempt_groups(records[0])[0])[0]
    rollout["trialStatus"] = "nonconforming"
    redigest(records[0])
    projection = matching_projection(parsed_attempts(records))
    identity = str(rollout["rolloutId"])
    if missing:
        del projection[identity]
    rollout["trialStatus"] = "conforming"
    redigest(records[0])
    # When: the operator submits the flipped, rehashed unsigned registry.
    result = pilot.evaluate_attempt_registry(
        parsed_policy(budget=1),
        parsed_attempts(records),
        ledger_projection=projection,
        ledger_digest="e" * 64,
    )
    # Then: no statuses or detector reasons escape in the detail.
    assert result.reason == "PILOT_TRIAL_STATUS_DISAGREES"
    assert result.detail == identity


def test_evaluator_bound_uses_projected_statuses() -> None:
    # Given: auditor-derived uncertainty affects one group per solver at fixed N.
    attempts = accounting_attempt(count=100, affected=1)
    projection = matching_projection(attempts)
    # When: evaluating a matching bound projection.
    result = pilot.evaluate_attempt_registry(
        replace(parsed_policy(budget=1), group_count=100),
        attempts,
        ledger_projection=projection,
        ledger_digest="e" * 64,
    )
    # Then: the projected affected trials count against release, without dropping groups.
    assert result.accepted
    assert [(bound.group_successes, bound.group_count) for bound in result.solver_bounds] == [
        (1, 100),
        (1, 100),
    ]


def test_registry_check_refuses_absent_ledger(tmp_path: Path) -> None:
    # Given: a complete unsigned registry with no private auditor ledger.
    seed = tmp_path / ".seed"
    seed.mkdir()
    (seed / "pilot-policy.json").write_bytes(policy_document())
    (seed / "pilot-attempts.jsonl").write_bytes(registry_document(registry_records()))
    # When: the parent gate resolves the local binding.
    findings = check_pilot_attempt_registry(str(tmp_path))
    # Then: it refuses without echoing private details.
    assert [finding.code for finding in findings] == ["PILOT_FIDELITY_UNBOUND"]


def test_registry_check_binds_ledger_from_audit_root(tmp_path: Path) -> None:
    # Given: the real parent fixture emits a ledger with emit_fidelity_ledger.
    test_parent_check_resolves_operator_from_digest_bound_envelope(tmp_path, "independent-runner")
    # When: the registered orchestrator check resolves the matching ledger.
    findings = integrity.check_pilot_attempt_registry(str(tmp_path))
    # Then: the matching auditor-derived population qualifies.
    assert findings == []


@pytest.mark.parametrize("surface", ["registry", "policy"])
@pytest.mark.parametrize(
    "raw", [b'{"x":"\\ud800"}\n', b'{"x":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}\n"]
)
def test_pilot_json_hostility_is_typed(surface: str, raw: bytes) -> None:
    # Given: hostile JSON at either public parsing boundary.
    parser = parse_attempt_registry if surface == "registry" else parse_pilot_policy
    # When: parsing the supplied bytes.
    result = parser(raw)
    # Then: decoding and canonicalization cannot escape the refusal boundary.
    assert result.outcome.reason == PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED


@pytest.mark.parametrize("surface", ["registry", "policy"])
def test_pilot_json_decoder_recursion_is_typed(
    surface: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: the decoder fails internally despite a shallow input.
    def exhausted(*_args: object, **_kwargs: object) -> None:
        raise RecursionError

    monkeypatch.setattr(json, "loads", exhausted)
    parser = parse_attempt_registry if surface == "registry" else parse_pilot_policy
    # When: using the public parser.
    result = parser(b"{}\n")
    # Then: interpreter recursion is a typed malformed outcome.
    assert result.outcome.reason == PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED


def test_pilot_json_depth_is_refused_before_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: a deeply nested registry and a decoder that must never be reached.
    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("deep input reached JSON decoder")

    monkeypatch.setattr(json, "loads", forbidden)
    # When: parsing through the public registry boundary.
    result = parse_attempt_registry(b'{"x":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}\n")
    # Then: the structural budget refuses before allocating decoded containers.
    assert result.outcome.reason == PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED


@pytest.mark.parametrize(
    ("name", "cap"),
    [
        (".seed/pilot-policy.json", "MAX_POLICY_BYTES"),
        (".seed/pilot-attempts.jsonl", "MAX_REGISTRY_BYTES"),
        ("EDICT.md", "MAX_REPORT_BYTES"),
    ],
)
def test_pilot_read_caps_before_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, cap: str
) -> None:
    # Given: a file above its cap and no permitted Path.read_bytes fallback.
    if name.startswith(".seed/"):
        (tmp_path / ".seed").mkdir()
        (tmp_path / pilot.POLICY_PATH).write_bytes(policy_document())
        (tmp_path / pilot.REGISTRY_PATH).write_bytes(registry_document(registry_records()))
    (tmp_path / name).write_bytes(b"x" * 9)
    monkeypatch.setattr(pilot, cap, 8, raising=False)

    def forbidden(path: Path) -> bytes:
        pytest.fail(f"unbounded read reached: {path}")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    # When: checking the real on-disk project.
    findings = check_pilot_attempt_registry(str(tmp_path))
    # Then: the named budget is refused through the public entry point.
    assert [item.code for item in findings] == ["PILOT_ATTEMPT_REGISTRY_MALFORMED"]
    assert cap in findings[0].message


@pytest.mark.parametrize("alias", ["policy", "registry", "ancestor", "dangling_ancestor", "report"])
def test_pilot_reads_refuse_symlinks(tmp_path: Path, alias: str) -> None:
    # Given: a leaf or ancestor alias into otherwise readable pilot inputs.
    seed = tmp_path / ".seed"
    seed.mkdir()
    policy = seed / "pilot-policy.json"
    registry = seed / "pilot-attempts.jsonl"
    policy.write_bytes(policy_document())
    registry.write_bytes(registry_document(registry_records()))
    if alias in {"ancestor", "dangling_ancestor"}:
        target = tmp_path / "elsewhere"
        seed.rename(target)
        seed.symlink_to(
            target if alias == "ancestor" else tmp_path / "absent", target_is_directory=True
        )
    elif alias == "report":
        policy.unlink()
        registry.unlink()
        (tmp_path / "report.txt").write_text("No pilot claim.\n")
        (tmp_path / "EDICT.md").symlink_to(tmp_path / "report.txt")
    else:
        path = policy if alias == "policy" else registry
        target = tmp_path / "external.json"
        path.rename(target)
        path.symlink_to(target)
    # When: inspecting the project through its trusted root.
    findings = check_pilot_attempt_registry(str(tmp_path))
    # Then: neither leaf nor ancestor aliases are admitted.
    assert [item.code for item in findings] == ["PILOT_ATTEMPT_REGISTRY_MALFORMED"]


def test_pilot_registry_record_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given: two otherwise valid records with a one-record budget.
    raw = registry_document(registry_records())
    monkeypatch.setattr(pilot, "MAX_REGISTRY_RECORDS", 1, raising=False)
    # When: parsing the registry.
    result = parse_attempt_registry(raw)
    # Then: refuse rather than silently truncate the population.
    assert result.outcome.reason == PilotFailureReason.PILOT_ATTEMPT_REGISTRY_MALFORMED
    assert "MAX_REGISTRY_RECORDS" in result.outcome.detail
