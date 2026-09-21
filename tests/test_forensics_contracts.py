"""Synthetic capture-profile fixtures, not client traces or execution attestations."""

import json
from dataclasses import replace
from typing import assert_never

import pytest
from tools import forensics as f
from tools.forensics.reading import Json

from tests.test_forensics import FAMILIES, ZERO, bundle

NATIVE = tuple(family for family in FAMILIES if family != "atif_normalized")
DIGEST = "a" * 64


def native_records(family: str) -> list[dict[str, Json]]:
    """Capture v1 adds instrumented records, not inferred stock-format guarantees."""
    claude = family in {"claude_code_jsonl", "cybergym_usage"}
    records: list[dict[str, Json]] = [
        {"type": "system" if claude else "SessionStart", "subtype": "init", "status": "success"},
        {"type": "bootstrap", "bootstrap_id": "env", "status": "success"},
        {"type": "provider_request", "request_id": "req", "status_code": 200},
        {"type": "assistant", "request_id": "req", "stop_reason": "end_turn"},
        {"type": "tool_result", "tool_result_id": "obs", "truncated": False},
        {
            "type": "result" if claude else "Terminal",
            "stop_reason": "end_turn",
            "submission_sha256": DIGEST,
            "bootstrap_ids": ["env"],
            "request_ids": ["req"],
            "tool_result_ids": ["obs"],
            "max_turns": 4,
            "turns": 2,
            "timed_out": False,
            "timeout_seconds": 60,
            "elapsed_seconds": 10,
        },
    ]
    records[0]["capture_profile"] = "trinity.native-capture/v1"
    records[0]["max_message_chars"] = 100
    for index, event in enumerate(records):
        event["index" if claude else "id"] = index
        event["session_id"] = "session"
    return records


def complete_bundle(family: str, records: list[dict[str, Json]] | None = None) -> f.TraceBundle:
    events = native_records(family) if records is None else records
    path = "agent.jsonl" if family in {"claude_code_jsonl", "cybergym_usage"} else "events.jsonl"
    files = {
        path: b"".join(json.dumps(event).encode() + b"\n" for event in events),
        "submission.json": json.dumps({"session_id": "session", "sha256": DIGEST}).encode(),
        "usage.json": b"{}",
        "run-metadata.json": b'{"condenser_config":{"type":"noop"}}',
        "metrics.json": b"{}",
    }
    return replace(
        bundle(family, files),
        authorization=f.Authorization(max_turns=4, timeout_seconds=60, max_message_chars=100),
    )


def signal_outcome(result: f.RolloutFidelity, signal: f.SignalClass) -> f.FidelityOutcome:
    outcomes = {item.outcome for item in result.findings if item.signal is signal}
    for outcome in (f.FidelityOutcome.VIOLATION, f.FidelityOutcome.INSUFFICIENT_EVIDENCE):
        if outcome in outcomes:
            return outcome
    assert outcomes == {f.FidelityOutcome.COVERED_CLEAN}
    return f.FidelityOutcome.COVERED_CLEAN


@pytest.mark.parametrize("family", NATIVE)
def test_native_family_can_reach_covered_clean(family: str) -> None:
    # Given: all positive records required by the native capture contract.
    trace = complete_bundle(family)
    # When: dispatch through the public API and its ceiling guard.
    result = f.analyze_trace(trace)
    # Then: actual whole-rollout coverage, not merely the format ceiling.
    assert result.overall is f.FidelityOutcome.COVERED_CLEAN, result.findings


@pytest.mark.parametrize("family", NATIVE)
@pytest.mark.parametrize("signal", tuple(f.SignalClass))
@pytest.mark.parametrize("planted", [False, True], ids=["missing", "violation"])
def test_each_contract_row_has_negative_and_violation(
    family: str, signal: f.SignalClass, planted: bool
) -> None:
    # Given: remove a required record/field, or plant contradictory native evidence.
    records = native_records(family)
    match signal:
        case f.SignalClass.COMPACTION:
            if planted:
                records[3].update({"isCompactSummary": True})
                if family.startswith("openhands"):
                    records[3].update(
                        {
                            "type": "Condensation",
                            "forgotten_event_ids": [0, 1],
                            "summary": "synthetic",
                            "summary_offset": 0,
                        }
                    )
            else:
                records.pop()
        case f.SignalClass.OBSERVATION_TRUNCATION:
            if planted:
                records[4].update({"truncated": True, "max_message_chars": 50})
            else:
                records.pop(4)
        case f.SignalClass.TURN_CAP:
            if planted:
                records[-1]["max_turns"] = 1
            else:
                del records[-1]["max_turns"]
        case f.SignalClass.TIMEOUT:
            if planted:
                records[-1].update({"timed_out": True, "timeout_seconds": 1})
            else:
                del records[-1]["timed_out"]
        case f.SignalClass.PROVIDER_ERROR:
            if planted:
                records[2]["status_code"] = 429
            else:
                records.pop(2)
        case f.SignalClass.REFUSAL:
            if planted:
                records[3]["stop_reason"] = "refusal"
            else:
                del records[-1]["stop_reason"]
        case f.SignalClass.SETUP_FAILURE:
            if planted:
                records[0]["status"] = "error"
            else:
                records.pop(0)
        case f.SignalClass.HANDOFF_FAILURE:
            if planted:
                records[-1]["submission_sha256"] = "b" * 64
        case unreachable:
            assert_never(unreachable)
    trace = complete_bundle(family, records)
    if signal is f.SignalClass.HANDOFF_FAILURE and not planted:
        trace = replace(
            trace, files={k: v for k, v in trace.files.items() if k != "submission.json"}
        )
    # When: classify the changed evidence, never altering authorization.
    outcome = signal_outcome(f.analyze_trace(trace), signal)
    # Then: every row has both an unknown and a positive violation route.
    expected = f.FidelityOutcome.VIOLATION if planted else f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert outcome is expected


def test_coverage_contracts_cover_all_eight_signals_per_native_family() -> None:
    # Given / When: the public, machine-readable contract registry.
    contracts = f.COVERAGE_CONTRACTS
    # Then: no family or signal can silently disappear from fixture generation.
    assert set(contracts) == set(NATIVE)
    for family in NATIVE:
        assert set(contracts[family]) == set(f.SignalClass)


def test_atif_alone_still_capped() -> None:
    # Given: normalized bytes without their native source.
    trace = bundle("atif_normalized", {"agent/trajectory.json": b'{"steps":[]}'})
    # When / Then: the unchanged ceiling rejects a clean conclusion.
    assert f.analyze_trace(trace).overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("family", FAMILIES)
def test_self_reported_zero_still_never_clean(family: str) -> None:
    # Given: the incident's self-reported zero, without native records.
    trace = bundle(family, {"result.json": ZERO})
    # When / Then: all five families remain indeterminate.
    assert f.analyze_trace(trace).overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
