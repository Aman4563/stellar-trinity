"""Task 13 pure fidelity semantics, independent of trace adapters."""

import re
from itertools import product

import pytest
from tools import forensics

SIGNALS = (
    "COMPACTION",
    "OBSERVATION_TRUNCATION",
    "TURN_CAP",
    "TIMEOUT",
    "PROVIDER_ERROR",
    "REFUSAL",
    "SETUP_FAILURE",
    "HANDOFF_FAILURE",
)
OUTCOMES = ("COVERED_CLEAN", "INSUFFICIENT_EVIDENCE", "VIOLATION")
REFUSALS = (
    "FIDELITY_FAMILY_UNRECOGNIZED",
    "FIDELITY_VERSION_UNSUPPORTED",
    "FIDELITY_TRACE_CONVERSION_ONLY",
    "FIDELITY_SEQUENCE_INCOMPLETE",
    "FIDELITY_SELF_REPORTED_ONLY",
    "FIDELITY_TRACE_UNREADABLE",
)


def test_outcome_reduction_truth_table() -> None:
    # Given: every one of the 3**8 complete outcome assignments.
    assert {member.value for member in forensics.SignalClass} == set(SIGNALS)
    assert {member.value for member in forensics.FidelityOutcome} == set(OUTCOMES)
    assert {member.value for member in forensics.FidelityRefusal} == set(REFUSALS)
    for ranks in product(range(3), repeat=8):
        findings = tuple(
            forensics.SignalFinding(
                forensics.SignalClass(signal),
                forensics.FidelityOutcome(OUTCOMES[rank]),
                None,
                "./agent/agent.jsonl:174",
            )
            for signal, rank in zip(SIGNALS, ranks, strict=True)
        )
        # When: reduce independently classified findings.
        result = forensics.RolloutFidelity("run-2", "native", findings).overall
        # Then: the independent severity rank selects the fixed precedence.
        assert result.value == OUTCOMES[max(ranks)], ranks


@pytest.mark.parametrize("omitted", SIGNALS)
@pytest.mark.parametrize("duplicate", [False, True])
def test_covered_clean_requires_all_eight_signals(omitted: str, duplicate: bool) -> None:
    # Given: seven clean classes; duplicate findings cannot fill the missing class.
    findings = tuple(
        forensics.SignalFinding(
            forensics.SignalClass(signal),
            forensics.FidelityOutcome.COVERED_CLEAN,
            None,
            "./agent/agent.jsonl:1",
        )
        for signal in SIGNALS
        if signal != omitted
    )
    if duplicate:
        findings += (findings[0],)
    # When: reduce the incomplete rollout.
    result = forensics.RolloutFidelity("run-2", "native", findings).overall
    # Then: even eight findings cannot substitute for eight covered classes.
    assert result is forensics.FidelityOutcome.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("conditions", tuple(product((False, True), repeat=5)))
def test_coverage_predicate_refusal_order(conditions: tuple[bool, ...]) -> None:
    # Given: all 32 combinations, including each single failure and all-pass.
    ordered_refusals = (REFUSALS[0], REFUSALS[1], REFUSALS[2], REFUSALS[1], REFUSALS[3])
    expected = next(
        (
            refusal
            for passed, refusal in zip(conditions, ordered_refusals, strict=True)
            if not passed
        ),
        None,
    )
    # When: evaluate the five coverage facts in their public positional order.
    covered, refusal = forensics.demonstrates_coverage(*conditions)
    # Then: the first failed fact wins, including vocabulary as a version fact.
    assert (covered, refusal) == (expected is None, expected)


def test_self_reported_zero_is_insufficient() -> None:
    # Given: summarization_count: 0 under enable_summarize: false is self-report only.
    # Adapters will classify those bytes; this core consumes the classified finding.
    finding = forensics.SignalFinding(
        forensics.SignalClass.COMPACTION,
        forensics.FidelityOutcome.INSUFFICIENT_EVIDENCE,
        forensics.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY,
        "./result.json:1",
    )
    clean = tuple(
        forensics.SignalFinding(
            forensics.SignalClass(signal),
            forensics.FidelityOutcome.COVERED_CLEAN,
            None,
            "./agent/agent.jsonl:1",
        )
        for signal in SIGNALS[1:]
    )
    # When: reduce self-report alongside coverage of every other class.
    rollout = forensics.RolloutFidelity("run-2", "native", (finding, *clean))
    # Then: a self-reported zero never supplies compaction coverage.
    assert finding.refusal is forensics.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY
    assert rollout.overall is forensics.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert forensics.map_trial_status(rollout) == "indeterminate"


def test_approved_timeout_is_conforming() -> None:
    # Given: approved timeout and turn cap fired as declared, with all classes covered.
    findings = tuple(
        forensics.SignalFinding(
            forensics.SignalClass(signal),
            forensics.FidelityOutcome.COVERED_CLEAN,
            None,
            "./agent/agent.jsonl:174",
        )
        for signal in SIGNALS
    )
    # When: map the rollout independently of whether the solver succeeded.
    rollout = forensics.RolloutFidelity("approved-timeout", "native", findings)
    status = forensics.map_trial_status(rollout)
    # Then: faithful enforcement of an approved limit remains conforming.
    assert rollout.overall is forensics.FidelityOutcome.COVERED_CLEAN
    assert status == "conforming"


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        ("VIOLATION", "nonconforming"),
        ("INSUFFICIENT_EVIDENCE", "indeterminate"),
        ("COVERED_CLEAN", "conforming"),
    ],
)
def test_map_trial_status_is_total(outcome: str, expected: str) -> None:
    # Given: each closed outcome with a complete signal roster.
    findings = tuple(
        forensics.SignalFinding(
            forensics.SignalClass(signal),
            forensics.FidelityOutcome(outcome),
            None,
            "./agent/agent.jsonl:1",
        )
        for signal in SIGNALS
    )
    # When: apply the named conformance rule.
    status = forensics.map_trial_status(forensics.RolloutFidelity("run-2", "native", findings))
    # Then: exact mapping and vocabulary closure, without depending on future pilot work.
    assert status == expected
    assert {status} <= forensics.TRIAL_STATUSES
    expected_statuses = frozenset({"conforming", "nonconforming", "indeterminate"})
    assert expected_statuses == forensics.TRIAL_STATUSES
    assert forensics.TRIAL_CONFORMANCE_RULE == "trinity.trial-conformance/v1"


@pytest.mark.parametrize(
    ("pointer", "accepted"),
    [
        ("./agent/agent.jsonl:174", True),
        ("result.json:1", True),
        ("agent.jsonl:174 secret trace", False),
        ("agent.jsonl:174\nsecret", False),
        ('{"type":"system"}:174', False),
        ("agent.jsonl:0", False),
        ("agent.jsonl:-1", False),
        (":174", False),
        ("agent.jsonl", False),
    ],
)
def test_evidence_pointer_carries_no_trace_content(pointer: str, accepted: bool) -> None:
    # Given: locators and payload-bearing or malformed counterexamples.
    if not accepted:
        # When / Then: reject at construction without reflecting trace bytes in errors.
        with pytest.raises(ValueError) as error:
            forensics.SignalFinding(
                forensics.SignalClass.COMPACTION,
                forensics.FidelityOutcome.VIOLATION,
                None,
                pointer,
            )
        assert pointer not in str(error.value)
        return
    # When: construct a pointer-only finding.
    finding = forensics.SignalFinding(
        forensics.SignalClass.COMPACTION,
        forensics.FidelityOutcome.VIOLATION,
        None,
        pointer,
    )
    # Then: retain only a path plus positive line number, never whitespace-bearing content.
    assert finding.evidence_pointer == pointer
    assert re.fullmatch(r"[^\s:]+:[1-9][0-9]*", finding.evidence_pointer)
