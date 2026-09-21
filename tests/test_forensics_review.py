"""Wave 3 bypass regressions using synthetic native evidence only."""

import json
from dataclasses import replace

import pytest
from tools import forensics as f
from tools.forensics.atif_normalized import CONTINUATION_MARKER
from tools.forensics.family_models import PrivateReason

from tests.test_forensics_contracts import NATIVE, complete_bundle, native_records, signal_outcome
from tests.test_forensics_family import Inputs

pytest_plugins = ("tests.test_forensics_family",)


@pytest.mark.parametrize("family", NATIVE)
def test_accompanied_atif_marker_survives_native_delegation(family: str) -> None:
    # Given: clean native coverage accompanied by contradictory normalized evidence.
    native = complete_bundle(family)
    trace = replace(
        native,
        family="atif_normalized",
        harness_version="1.8",
        accompaniment=frozenset({family}),
        files={
            **native.files,
            "agent/trajectory.json": json.dumps(
                {
                    "agent": {"version": native.harness_version, "model_name": "synthetic"},
                    "steps": [{"message": CONTINUATION_MARKER}],
                }
            ).encode(),
        },
    )
    # When: delegate to the evidence-bearing native family.
    result = f.analyze_trace(trace)
    # Then: native identity survives, but its coverage cannot erase a positive.
    assert signal_outcome(result, f.SignalClass.COMPACTION) is f.FidelityOutcome.VIOLATION
    assert result.family == family
    assert f.map_trial_status(result) == "nonconforming"
    assert all(
        x.refusal is not f.FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY for x in result.findings
    )


@pytest.mark.parametrize("family", NATIVE)
def test_missing_turn_count_is_not_covered(family: str) -> None:
    # Given: an authorized cap without the observed count.
    records = native_records(family)
    del records[-1]["turns"]
    # When: classify otherwise complete native evidence.
    result = f.analyze_trace(complete_bundle(family, records))
    # Then: policy declarations do not prove count coverage.
    assert signal_outcome(result, f.SignalClass.TURN_CAP) is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert result.overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("family", NATIVE)
@pytest.mark.parametrize("elapsed", [1, 58])
def test_early_fired_timeout_is_violation(family: str, elapsed: int) -> None:
    # Given: an approved 60-second timer fired before the horizon, beyond tolerance.
    records = native_records(family)
    records[-1].update({"timed_out": True, "elapsed_seconds": elapsed})
    # When: classify the observed early termination.
    result = f.analyze_trace(complete_bundle(family, records))
    # Then: approval of the configured timer cannot excuse budget starvation.
    assert signal_outcome(result, f.SignalClass.TIMEOUT) is f.FidelityOutcome.VIOLATION
    assert f.map_trial_status(result) == "nonconforming"


@pytest.mark.parametrize("family", NATIVE)
def test_fired_timeout_without_elapsed_is_insufficient(family: str) -> None:
    # Given: an approved fired timer without any captured duration.
    records = native_records(family)
    records[-1]["timed_out"] = True
    del records[-1]["elapsed_seconds"]
    # When: classify the supplied record.
    result = f.analyze_trace(complete_bundle(family, records))
    # Then: the actual horizon remains unknown.
    assert signal_outcome(result, f.SignalClass.TIMEOUT) is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert result.overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("elapsed", [59, 60, 61])
def test_fired_timeout_within_tolerance_stays_clean(elapsed: int) -> None:
    # Given: integer-second capture within the one-second early tolerance or later.
    records = native_records("claude_code_jsonl")
    records[-1].update({"timed_out": True, "elapsed_seconds": elapsed})
    # When: classify faithful enforcement of the approved horizon.
    result = f.analyze_trace(complete_bundle("claude_code_jsonl", records))
    # Then: timestamp granularity and late delivery do not imply starvation.
    assert result.overall is f.FidelityOutcome.COVERED_CLEAN


@pytest.mark.parametrize("field", ["max_turns", "timeout_seconds"])
def test_unapproved_limit_without_observation_remains_violation(field: str) -> None:
    # Given: an unauthorized limit, without the count or duration needed for clean coverage.
    records = native_records("claude_code_jsonl")
    records[-1].update({field: 1, "timed_out": True})
    del records[-1]["turns"]
    del records[-1]["elapsed_seconds"]
    # When: classify the surviving positive evidence.
    result = f.analyze_trace(complete_bundle("claude_code_jsonl", records))
    # Then: missing observations cannot suppress an unauthorized-limit violation.
    signal = f.SignalClass.TURN_CAP if field == "max_turns" else f.SignalClass.TIMEOUT
    assert signal_outcome(result, signal) is f.FidelityOutcome.VIOLATION


@pytest.mark.parametrize(
    "statuses", [("nonconforming",), ("indeterminate",), ("conforming", "conforming")]
)
def test_projection_refuses_operator_status_disagreement(
    inputs: Inputs, statuses: tuple[str, ...]
) -> None:
    # Given: clean derived evidence and a disagreeing declaration or duplicate sentinel.
    root, config, roster = inputs
    roster = replace(roster, operator_statuses=tuple(("run_0", status) for status in statuses))
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    assert ledger.rows[0].trial_status == "conforming"
    assert ledger.selected_reason is PrivateReason.FIDELITY_UNVERIFIED
    # When: attempting to cross the private/public projection boundary.
    with pytest.raises(f.FidelityProjectionError) as error:
        f.project_for_pilot(ledger)
    # Then: the named exception contains no private diagnostic or evidence payload.
    assert type(error.value).__name__ == "FidelityProjectionError"
    exposed = str(error.value) + repr(error.value) + repr(vars(error.value))
    assert error.value.args == ()
    assert not any(
        token.value in exposed for token in (*PrivateReason, *f.FidelityRefusal, *f.SignalClass)
    )
    assert not any(
        finding.evidence_pointer in exposed for row in ledger.rows for finding in row.trace.findings
    )
    assert ledger.rows[0].trial_status == "conforming"


def test_projection_accepts_agreeing_statuses(inputs: Inputs) -> None:
    # Given: independently derived clean evidence with agreeing operator declarations.
    root, config, roster = inputs
    roster = replace(
        roster, operator_statuses=tuple((identity, "conforming") for identity in roster.groups[0])
    )
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # When: projecting reconciled rows.
    projection = f.project_for_pilot(ledger)
    # Then: all declared identities retain the truthful derived classification.
    assert {identity: projection[identity] for identity in roster.groups[0]} == dict(
        roster.operator_statuses
    )
    assert ledger.selected_reason is None
