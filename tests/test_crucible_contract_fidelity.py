"""CRUCIBLE.md execution-fidelity clauses: the G-FID family and the grown vocabularies.

The contract prose is the product, so these assertions pin the exact tokens the
auditor contract must spell and the exact arity of the two closed vocabularies
step 8q fixes. A silently shrunk list is a silently weakened coverage ledger.
"""

import re
from pathlib import Path

import pytest

CONTRACT = Path(__file__).resolve().parents[1] / "CRUCIBLE.md"

THREAT_PREFIX = "each naming the boundary at which the reward claim first becomes false: "
CHANNEL_PREFIX = "scorer-influence channels: "

EXPECTED_THREATS = 29
EXPECTED_CHANNELS = 9

REQUIRED_TOKENS: tuple[str, ...] = (
    "G-FID",
    "G-FID-CONFIG",
    "G-FID-TRACE",
    "G-FID-POPULATION",
    "G-FID-HANDOFF",
    ".audit/fidelity.yaml",
    "trinity.execution/v2",
    "trinity.trial-conformance/v1",
    "execution_fidelity",
    "fidelity_coverage",
    "reward-claim model version 2",
    "capability vocabulary version 2",
)

ADDED_THREATS: tuple[str, ...] = (
    "approved-but-inadequate configuration",
    "solver-input or tool-interface corruption",
    "submission or scoring handoff failure",
    "execution-state contamination",
    "effective service degradation",
    "population or scheduling manipulation",
    "post-solver measurement suppression",
)

PARTITIONED_BOUNDARIES: tuple[str, ...] = (
    "input, whether the scorer received the intended task state and exactly the "
    "solver-produced deliverable set, including submission transport and scoring handoff",
    "population, whether the committed rollout and group membership equals the precommitted "
    "measurement universe, including admission, replacement, and outcome-dependent selection",
    "and execution, whether the solver received the intended task and service under an approved "
    "configuration adequate for the declared horizon",
    "submission transport belongs to input, population membership belongs to population, and "
    "evidence capture and custody belong to evidence",
)

ORDERED_REASONS: tuple[str, ...] = (
    "config-unpinned for a missing, unbound, or unapproved configuration",
    "config-drift for an attested effective configuration contradicting the binding",
    "config-inadequate for missing adequacy approval or demonstrated inadequacy",
    "handoff-unverified for a failed or unprovable submission handoff",
    "context-uncovered for insufficient context-handling evidence",
    "fidelity-unverified for every remaining observed suppressing violation",
)


def contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def clause(opening: str) -> str:
    """Return the single line whose paragraph opens with this text."""
    matches = [line for line in contract_text().split("\n") if line.startswith(opening)]
    assert len(matches) == 1, f"expected exactly one clause opening {opening!r}, got {len(matches)}"
    return matches[0]


def enumerated(line: str, prefix: str) -> list[str]:
    """Parse the comma-separated closed list that follows prefix on this line."""
    assert prefix in line, f"clause does not carry the list prefix {prefix!r}"
    tail = line.split(prefix, 1)[1]
    body = re.split(r"\.\s", tail, maxsplit=1)[0].rstrip(".")
    return [re.sub(r"^and\s+", "", item.strip()) for item in body.split(", ")]


@pytest.mark.parametrize("token", REQUIRED_TOKENS)
def test_contract_names_the_fidelity_token(token: str) -> None:
    assert token in contract_text(), f"CRUCIBLE.md never names {token!r}"


def test_threat_vocabulary_enumerates_twenty_nine_entries() -> None:
    line = clause("8q. ")
    threats = enumerated(line, THREAT_PREFIX)
    assert len(threats) == EXPECTED_THREATS, threats
    assert len(set(threats)) == EXPECTED_THREATS, "threat vocabulary repeats an entry"
    assert "twenty-nine" in line, "clause does not declare the closure at twenty-nine"


@pytest.mark.parametrize("threat", ADDED_THREATS)
def test_threat_vocabulary_carries_the_added_class(threat: str) -> None:
    assert threat in enumerated(clause("8q. "), THREAT_PREFIX)


def test_capability_vocabulary_enumerates_nine_channels() -> None:
    line = clause("8q. ")
    channels = enumerated(line, CHANNEL_PREFIX)
    assert len(channels) == EXPECTED_CHANNELS, channels
    assert channels[-1] == "context", channels
    assert "nine" in line, "clause does not declare the closure at nine channels"


def test_execution_is_the_eighth_causal_boundary() -> None:
    line = clause("8q. ")
    assert "eight causal boundaries" in line, line
    assert "and execution, whether the solver received the intended task and service" in line


@pytest.mark.parametrize("definition", PARTITIONED_BOUNDARIES)
def test_boundary_definitions_partition_the_execution_boundary(definition: str) -> None:
    assert definition in clause("8q. "), definition


def test_boundary_ownership_is_one_atomic_obligation() -> None:
    line = clause("8q. ")
    assert "Boundary ownership attaches to an atomic violated obligation" in line
    assert "not to an incident, instrument family, capability channel, or downstream" in line
    assert "each finding has exactly one owning boundary" in line


def test_added_threat_classes_carry_their_owning_boundary() -> None:
    line = clause("8q. ")
    assert "respectively, execution, execution, input, execution, execution, population, " in line
    assert "and evidence" in line
    assert "ordering that instead changes a solver's execution state belongs to" in line
    assert "not omission of rollout or group membership, which belongs to population" in line


@pytest.mark.parametrize("reason", ORDERED_REASONS)
def test_step_8u_orders_the_suppression_reasons(reason: str) -> None:
    assert reason in clause("8u. "), reason


def test_step_8u_closes_the_reason_order_and_caps() -> None:
    line = clause("8u. ")
    assert "Retain every finding privately" in line
    assert "with no suppression reason" in line
    assert "Earlier matches exclude later reasons" in line
    assert "Other governing `BLOCK` conditions retain precedence" in line
    assert "operator-versus-derived status disagreement caps at `HOLD`" in line
    assert "Missing adequacy approval caps at `HOLD` independently of configuration" in line


def test_rollout_integrity_establishes_custody_and_never_execution_validity() -> None:
    line = clause("8o. ")
    assert "establishes custody and never execution validity" in line
    assert "G-FID" in line


def test_execution_attestation_ingest_binds_the_harness_config() -> None:
    line = clause("8p. ")
    assert "trinity.execution/v2" in line
    assert "harness-config digest" in line
    assert "effective-configuration reconciliation" in line
    assert "observation capture precedes operator editing" in line


def test_step_8u_builds_the_four_fidelity_instruments() -> None:
    line = clause("8u. ")
    for instrument in ("G-FID-CONFIG", "G-FID-TRACE", "G-FID-POPULATION", "G-FID-HANDOFF"):
        assert instrument in line, instrument
    assert "EXECUTION-FIDELITY" in line
    assert "pure Bucket D" in line
    assert ".audit/fidelity.yaml" in line
    assert "stripped from every projection by name" in line


def test_detector_standing_principle_is_three_valued() -> None:
    line = clause("8. Detector standing is three-valued")
    values = (
        "an observed violation, demonstrated coverage with no violation, or insufficient evidence"
    )
    assert values in line
    for condition in (
        "missing marker",
        "unsupported harness version",
        "conversion-only trace",
        "self-reported zero",
    ):
        assert condition in line, condition
    assert "never resolve as clean" in line
    assert "absence of a record is not a record of absence" in line


def test_class_seventeen_is_execution_fidelity() -> None:
    line = clause("17. Execution fidelity")
    assert "step 8u" in line


def test_phase_r_states_the_content_addressed_stem() -> None:
    text = contract_text()
    assert "<source-class>/<canonical-id>-<slug>" in text
    assert "the SHA-256 of the retained bytes rather than the stem" in text
    assert "<arxiv-id>-<slug>" not in text
