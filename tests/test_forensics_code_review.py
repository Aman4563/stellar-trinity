"""Public-entry-point regressions for the F2 measurement review."""

import json
from dataclasses import replace

import pytest
from tools import forensics as f
from tools import harness_config as hc
from tools.forensics.atif_normalized import CONTINUATION_MARKER

from tests.test_forensics_contracts import complete_bundle, native_records, signal_outcome
from tests.test_forensics_family import Inputs

pytest_plugins = ("tests.test_forensics_family",)


@pytest.mark.parametrize(
    ("iterations", "expected"),
    [
        (150, f.FidelityOutcome.COVERED_CLEAN),
        (250, f.FidelityOutcome.VIOLATION),
        (None, f.FidelityOutcome.INSUFFICIENT_EVIDENCE),
    ],
)
def test_iteration_limit_uses_its_own_authorization(
    inputs: Inputs, iterations: int | None, expected: f.FidelityOutcome
) -> None:
    # Given: independently approved turn and iteration budgets and native counters.
    original, config, roster = inputs
    raw = json.dumps(
        json.loads(config.effective or b"{}") | {"maxTurns": 300, "maxIterations": 200}
    ).encode()
    config.source.write_bytes(raw)
    digest = hc.harness_config_digest(raw)
    config = replace(config, mirror=raw, effective=raw, bound_digest=digest, approved_digest=digest)
    records = native_records("claude_code_jsonl")
    records[-1].update({"max_turns": 300, "turns": 150, "max_iterations": 200})
    if iterations is not None:
        records[-1]["iterations"] = iterations
    trace = complete_bundle("claude_code_jsonl", records)
    root = original.parent / "independent-limits"
    for identity in roster.groups[0]:
        for name, content in trace.files.items():
            path = root / identity / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    # When: the public family entry point derives authorization from the bound config.
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # Then: iteration coverage never borrows the turns counter or its budget.
    assert signal_outcome(ledger.rows[0].trace, f.SignalClass.TURN_CAP) is expected


@pytest.mark.parametrize("path", ["result.json", "submission.json", "metrics.json"])
def test_native_violation_survives_malformed_collateral(path: str) -> None:
    # Given: a positive native marker and an independently damaged source.
    records = native_records("claude_code_jsonl")
    records[3]["isCompactSummary"] = True
    trace = complete_bundle("claude_code_jsonl", records)
    trace = replace(trace, files={**trace.files, path: b"{"})
    # When: classify through the public identity-reconciling entry point.
    result = f.analyze_trace(trace)
    # Then: unreadable collateral is recorded without erasing the native violation.
    assert result.overall is f.FidelityOutcome.VIOLATION
    assert signal_outcome(result, f.SignalClass.COMPACTION) is f.FidelityOutcome.VIOLATION
    assert any(
        item.refusal is f.FidelityRefusal.FIDELITY_TRACE_UNREADABLE
        and item.evidence_pointer == f"./{path}:1"
        for item in result.findings
    )


def test_positive_record_survives_malformed_independent_field() -> None:
    # Given: compaction precedes a malformed field in a later native record.
    records = native_records("claude_code_jsonl")
    records[3]["isCompactSummary"] = True
    records[-1]["turns"] = "invalid"
    trace = complete_bundle("claude_code_jsonl", records)
    # When: a later adapter read raises after the positive observation.
    result = f.analyze_trace(trace)
    # Then: the accumulated positive survives alongside the unreadability finding.
    assert result.overall is f.FidelityOutcome.VIOLATION
    assert any(x.refusal is f.FidelityRefusal.FIDELITY_TRACE_UNREADABLE for x in result.findings)


@pytest.mark.parametrize("authorized", [False, True])
@pytest.mark.parametrize("accompanied", [False, True])
def test_atif_marker_respects_authorization(authorized: bool, accompanied: bool) -> None:
    # Given: a normalized marker with independently supplied authorization and native coverage.
    native = complete_bundle("claude_code_jsonl")
    files = dict(native.files) if accompanied else {}
    files["agent/trajectory.json"] = json.dumps(
        {
            "agent": {"version": native.harness_version, "model_name": "synthetic"},
            "steps": [{"message": CONTINUATION_MARKER}],
        }
    ).encode()
    trace = replace(
        native,
        family="atif_normalized",
        harness_version="1.8",
        files=files,
        accompaniment=frozenset({native.family}) if accompanied else frozenset(),
        authorization=replace(native.authorization, compaction=authorized),
    )
    # When: classify the marker through the public entry point.
    result = f.analyze_trace(trace)
    # Then: authorization excuses transformation, but never supplies native coverage.
    expected = f.FidelityOutcome.VIOLATION
    if authorized:
        expected = (
            f.FidelityOutcome.COVERED_CLEAN
            if accompanied
            else f.FidelityOutcome.INSUFFICIENT_EVIDENCE
        )
    assert signal_outcome(result, f.SignalClass.COMPACTION) is expected
    assert result.overall is expected
    if authorized and not accompanied:
        assert any(
            x.refusal is f.FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY for x in result.findings
        )
