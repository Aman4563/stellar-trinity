"""Executable backing for the measurement-fidelity bite rows.

Every row registered here claims `CI: yes` in `tests/bite/`, so each one has to
resolve to a scenario running code actually refuses rather than to a reading of
the contract. The pilot rows drive `tools/pilot.py` and `tools/stats.py`, the
configuration row drives the planted `check_harness_config` fixtures, the ledger
rows parse the closed vocabularies step 8q fixes, and the firewall row drives the
same closure checker its `shared.md` sibling rows use.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from tools import forensics, pilot, stats

from tests.bite_shared.registration import bite
from tests.harness_imports import integrity
from tests.test_crucible_contract_fidelity import (
    CHANNEL_PREFIX,
    EXPECTED_CHANNELS,
    EXPECTED_THREATS,
    THREAT_PREFIX,
    clause,
    enumerated,
)
from tests.test_pilot import (
    accounting_attempt,
    canonical,
    evaluate_attempt_registry,
    parsed_policy,
    registry_document,
    v2_attempt_value,
    v2_policy_value,
)

FAMILYWISE_CONFIDENCE = 0.95
RETIRED_GROUP_FLOOR = 8
COMPARISON_FAMILY = 8
TRIAL_VOCABULARY = frozenset({"conforming", "nonconforming", "indeterminate"})
HARNESS_CONFIG_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "harness_config"


def refusal(value: dict[str, object]) -> pilot.PilotEvaluationOutcome:
    return pilot.parse_pilot_policy(canonical(value)).outcome


@bite("forge.md:F68")
def test_hardcoded_eight_group_floor_is_refused_as_infeasible() -> None:
    # Given: a policy declaring the retired hardcoded floor of eight groups.
    value = v2_policy_value()
    value["groupCount"] = RETIRED_GROUP_FLOOR
    # When: parsing it before any outcome exists.
    outcome = refusal(value)
    # Then: the computed floor refuses it and names the count the arithmetic needs.
    required = stats.minimum_groups(
        pilot.MEASURED_PASS_CEILING_MAX, FAMILYWISE_CONFIDENCE, COMPARISON_FAMILY
    )
    assert outcome.reason == "PILOT_INFEASIBLE_GROUP_COUNT"
    assert required > RETIRED_GROUP_FLOOR
    assert str(required) in outcome.detail


@bite("forge.md:F69")
def test_worst_case_indicator_counts_a_suppressed_trial_against_release() -> None:
    # Given: one group whose members all failed, one of them not conforming.
    suppressed = [(False, "conforming")] * 7 + [(False, "nonconforming")]
    clean = [(False, "conforming")] * 8
    # When: reducing each group to its release indicator.
    # Then: uncertainty scores as a success, so suppression raises the bound.
    assert stats.group_indicator(suppressed) == 1
    assert stats.group_indicator(clean) == 0
    assert stats.worst_case_group_successes([clean, suppressed, clean]) == (1, 3)


@bite("forge.md:F70")
def test_fixed_group_count_refuses_a_shrunk_or_padded_population() -> None:
    # Given: a policy that fixed ten groups before any outcome was observed.
    policy = parsed_policy(budget=1)
    for realized in (9, 11):
        # When: submitting a population of a different size.
        result = evaluate_attempt_registry(policy, accounting_attempt(count=realized))
        # Then: the refusal names the realized and the declared count.
        assert result.reason == "PILOT_GROUP_POPULATION_MUTATED"
        assert str(realized) in result.detail
        assert "10" in result.detail


@bite("forge.md:F71")
def test_feasibility_precheck_refuses_a_group_count_that_cannot_reach_the_ceiling() -> None:
    # Given: the Bonferroni-corrected confidence for the declared comparison family.
    confidence = stats.bonferroni_confidence(FAMILYWISE_CONFIDENCE, COMPARISON_FAMILY)
    ceiling = pilot.MEASURED_PASS_CEILING_MAX
    required = stats.minimum_groups(ceiling, FAMILYWISE_CONFIDENCE, COMPARISON_FAMILY)
    # When: evaluating the zero-success bound at the infeasible and the required count.
    # Then: the precheck separates the two before a single rollout runs.
    assert stats.group_upper_bound(0, required - 1, confidence) >= ceiling
    assert stats.group_upper_bound(0, required, confidence) < ceiling


@bite("forge.md:F72")
def test_unproven_fidelity_and_unprovable_population_carry_their_own_dispositions() -> None:
    # Given: a population with zero raw successes and two groups carrying a suppressed trial.
    policy = replace(
        parsed_policy(budget=1, measured_ceiling=pilot.MEASURED_PASS_CEILING_MAX),
        max_affected_group_fraction=Fraction(3, 10),
    )
    # When: evaluating it at the release ceiling.
    result = evaluate_attempt_registry(policy, accounting_attempt(affected=2))
    # Then: suppression breaches the headroom instead of buying it.
    assert result.reason == "PILOT_MEASURED_HEADROOM_BREACH"
    assert "HOLD:SUPPRESSED_MEASUREMENT" in integrity.DISPOSITIONS
    assert "BLOCK:INVALID_PILOT" in integrity.DISPOSITIONS


@bite("forge.md:F73")
def test_unbound_or_drifted_harness_configuration_is_refused() -> None:
    # Given: a policy whose configuration digest is absent.
    value = v2_policy_value()
    del value["harnessConfigDigest"]
    # When: parsing the policy, and qualifying a parent whose mirror drifted.
    outcome = refusal(value)
    drifted = integrity.check_harness_config(str(HARNESS_CONFIG_FIXTURES / "planted" / "drifted"))
    # Then: the pin is refused by name and the drift is refused without naming a value.
    assert outcome.reason == "PILOT_HARNESS_CONFIG_UNBOUND"
    assert "harnessConfigDigest" in outcome.detail
    assert [item.code for item in drifted] == ["HARNESS_CONFIG_DRIFT"]


@bite("forge.md:F74")
def test_trial_conformance_vocabulary_admits_no_fourth_token_and_no_reason() -> None:
    # Given: a registry carrying an unofficial status, and one carrying a reason code.
    unknown = v2_attempt_value()
    groups = unknown["solverGroups"]
    assert isinstance(groups, list)
    rollouts = groups[0]["rollouts"]
    assert isinstance(rollouts, list)
    rollouts[0]["trialStatus"] = "valid"
    reasoned = v2_attempt_value()
    reasoned["reasonCode"] = "private"
    # When: parsing each registry.
    unknown_outcome = pilot.parse_attempt_registry(registry_document([unknown])).outcome
    reasoned_outcome = pilot.parse_attempt_registry(registry_document([reasoned])).outcome
    # Then: neither an alias nor a reason reaches the author's registry.
    assert unknown_outcome.reason == "PILOT_TRIAL_STATUS_UNKNOWN"
    assert reasoned_outcome.reason == "PILOT_ATTEMPT_REGISTRY_MALFORMED"
    assert "forbidden" in reasoned_outcome.detail
    assert forensics.TRIAL_STATUSES == TRIAL_VOCABULARY


@bite("crucible.md:FD1")
def test_reward_claim_model_closes_at_eight_partitioned_boundaries() -> None:
    # Given: the step 8q clause that fixes the reward-claim model.
    line = clause("8q. ")
    # When: reading the boundary count and the partition sentence.
    # Then: execution is the eighth boundary and submission transport stays with input.
    assert "eight causal boundaries" in line
    assert "and execution, whether the solver received the intended task and service" in line
    assert "submission transport belongs to input" in line
    assert "each finding has exactly one owning boundary" in line


@bite("crucible.md:FD2")
def test_threat_vocabulary_closes_at_twenty_nine_distinct_entries() -> None:
    # Given: the closed threat list step 8q enumerates.
    line = clause("8q. ")
    threats = enumerated(line, THREAT_PREFIX)
    # When: counting its entries and locating the declared closure.
    # Then: the list is twenty-nine distinct entries with the added classes owned.
    assert len(threats) == EXPECTED_THREATS
    assert len(set(threats)) == EXPECTED_THREATS
    assert "twenty-nine" in line
    assert "respectively, execution, execution, input, execution, execution, population, " in line


@bite("crucible.md:FD3")
def test_capability_vocabulary_closes_at_nine_channels_ending_in_context() -> None:
    # Given: the closed capability list step 8q enumerates.
    line = clause("8q. ")
    channels = enumerated(line, CHANNEL_PREFIX)
    # When: counting its entries and reading the undeclared-transformation rule.
    # Then: context is the ninth channel and an undeclared one is never a pass.
    assert len(channels) == EXPECTED_CHANNELS
    assert channels[-1] == "context"
    assert "nine" in line
    assert "is an undeclared influence channel" in line


@bite("crucible.md:FD4")
def test_execution_validity_needs_the_four_fidelity_instruments() -> None:
    # Given: the custody clause and the clause building the fidelity family.
    custody = clause("8o. ")
    family = clause("8u. ")
    # When: reading what a clean custody result establishes and what the family adds.
    # Then: custody is never execution validity and all four instruments are required.
    assert "establishes custody and never execution validity" in custody
    assert "never accepted in its place" in custody
    for instrument in ("G-FID-CONFIG", "G-FID-TRACE", "G-FID-POPULATION", "G-FID-HANDOFF"):
        assert instrument in family
    assert "no live instrument in this family is `D-COVERAGE-GAP` capping at `HOLD`" in family


@bite("crucible.md:FD5")
def test_detector_standing_never_reads_an_absent_record_as_clean() -> None:
    # Given: a rollout whose only signal class demonstrating coverage is one of eight.
    finding = forensics.SignalFinding(
        signal=forensics.SignalClass.TIMEOUT,
        outcome=forensics.FidelityOutcome.COVERED_CLEAN,
        refusal=None,
        evidence_pointer="trace.jsonl:1",
    )
    partial = forensics.RolloutFidelity("r-1", "openhands", (finding,))
    covered = forensics.RolloutFidelity(
        "r-2",
        "openhands",
        tuple(replace(finding, signal=signal_class) for signal_class in forensics.SignalClass),
    )
    # When: reducing each rollout to its standing and its trial status.
    # Then: seven absent classes are insufficient evidence rather than a clean pass.
    assert partial.overall is forensics.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert forensics.map_trial_status(partial) == "indeterminate"
    assert covered.overall is forensics.FidelityOutcome.COVERED_CLEAN
    assert forensics.map_trial_status(covered) == "conforming"


@bite("shared.md:W10")
def test_forge_rejects_fidelity_detector_vocabulary() -> None:
    # Given: an author contract sentence naming a detector term outside a prohibition.
    planted = "Read the detector outcome from the fidelity ledger before sealing."
    # When: running the firewall closure the auditor's vocabulary is held to.
    findings = integrity.check_fidelity_closure("FORGE.md", planted)
    # Then: the term is refused in FORGE and left alone in the peer contracts.
    assert any("fidelity-detector term" in item.message for item in findings)
    assert integrity.check_fidelity_closure("CRUCIBLE.md", planted) == []
