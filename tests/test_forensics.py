"""Inline byte fixtures for the five pure family adapters."""

from dataclasses import replace

import pytest
from tools import forensics as f

FAMILIES = (
    "claude_code_jsonl",
    "atif_normalized",
    "openhands_events",
    "cybergym_usage",
    "openhands_native_metrics",
)
COMPACT = (
    b'{"type":"system","subtype":"compact_boundary",'
    b'"compact_metadata":{"trigger":"auto","pre_tokens":168780}}\n'
)
ZERO = b'{"agent_result":{"metadata":{"summarization_count":0,"enable_summarize":false}}}'
CLEAN_LOG = b'{"type":"system","subtype":"init","index":0}\n{"type":"result","index":1}\n'
MARKER = b"This session is being continued from a previous conversation that ran out of context"


def bundle(family: str, files: dict[str, bytes]) -> f.TraceBundle:
    assert hasattr(f, "TraceBundle"), "Task 14 must expose the frozen TraceBundle adapter input"
    return f.TraceBundle(
        family=family,
        harness_version="2.1.158" if family in {"claude_code_jsonl", "cybergym_usage"} else "1.8",
        files=files,
    )


def compaction(result: f.RolloutFidelity) -> f.SignalFinding:
    return next(x for x in result.findings if x.signal is f.SignalClass.COMPACTION)


class TestAdapters:
    def test_claude_code_detects_compact_boundary(self) -> None:
        # Given: the incident's literal native record, with synthetic rollout identity.
        trace = bundle("claude_code_jsonl", {"agent/agent.jsonl": COMPACT})
        # When: inspect without compaction authorization.
        result = f.analyze_trace(trace)
        # Then: the pointer carries the scalar observation, never the event payload.
        finding = compaction(result)
        assert finding.outcome is f.FidelityOutcome.VIOLATION
        assert "168780" in finding.evidence_pointer
        assert "compact_metadata" not in finding.evidence_pointer

    def test_claude_code_authorized_compaction_is_clean(self) -> None:
        # Given: the same event with bound authorization.
        trace = replace(
            bundle("claude_code_jsonl", {"agent.jsonl": COMPACT}),
            authorization=f.Authorization(compaction=True),
        )
        # When: classify the transformation.
        result = f.analyze_trace(trace)
        # Then: approved compaction is conforming, not a violation.
        assert compaction(result).outcome is f.FidelityOutcome.COVERED_CLEAN

    def test_claude_code_refuses_unsupported_version(self) -> None:
        # Given: a version outside the reviewed vocabulary.
        trace = replace(
            bundle("claude_code_jsonl", {"agent.jsonl": CLEAN_LOG}), harness_version="unknown"
        )
        # When / Then: absence of markers cannot establish coverage.
        result = f.analyze_trace(trace)
        assert compaction(result).refusal is f.FidelityRefusal.FIDELITY_VERSION_UNSUPPORTED

    def test_atif_marker_present_is_violation(self) -> None:
        # Given: a converted trajectory retaining positive evidence.
        trace = bundle(
            "atif_normalized",
            {"agent/trajectory.json": b'{"steps":[{"message":"' + MARKER + b'"}]}'},
        )
        # When / Then: the conversion ceiling never hides a positive observation.
        assert f.analyze_trace(trace).overall is f.FidelityOutcome.VIOLATION

    def test_atif_marker_absent_hits_the_declared_ceiling(self) -> None:
        # Given: marker-free conversion bytes.
        trace = bundle("atif_normalized", {"agent/trajectory.json": b'{"steps":[]}'})
        # When: classify negative evidence.
        result = f.analyze_trace(trace)
        # Then: exactly the single-source conversion ceiling.
        expected = f.strongest_supported_outcome("atif_normalized", frozenset())
        assert (result.overall, compaction(result).refusal) == expected
        assert expected == (
            f.FidelityOutcome.INSUFFICIENT_EVIDENCE,
            f.FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY,
        )

    def test_accompanied_atif_dispatches_and_lifts_ceiling(self) -> None:
        # Given: ATIF is an index alongside an explicitly named native source.
        trace = replace(
            bundle(
                "atif_normalized",
                {
                    "agent/trajectory.json": (
                        b'{"steps":[],"agent":{"model_name":"synthetic","version":"2.1.158"},'
                        b'"continued_trajectory_ref":"agent.jsonl"}'
                    ),
                    "agent.jsonl": CLEAN_LOG,
                },
            ),
            accompaniment=frozenset({"claude_code_jsonl", "raw_agent_jsonl"}),
        )
        # When: dispatch the accompanied pair.
        result = f.analyze_trace(trace)
        # Then: native evidence, native identity, native ceiling; no conversion refusal.
        assert result.family == "claude_code_jsonl"
        assert compaction(result).outcome is f.FidelityOutcome.COVERED_CLEAN
        assert f.strongest_supported_outcome(trace.family, trace.accompaniment) == (
            f.FidelityOutcome.COVERED_CLEAN,
            None,
        )

    @pytest.mark.parametrize("family", FAMILIES)
    def test_no_adapter_exceeds_its_ceiling(self, family: str) -> None:
        # Given: clean native records or clean conversion-only records.
        files = {
            "claude_code_jsonl": {"agent.jsonl": CLEAN_LOG},
            "atif_normalized": {"agent/trajectory.json": b'{"steps":[]}'},
            "openhands_events": {
                "events.jsonl": b'{"id":0,"type":"Action"}\n',
                "run-metadata.json": b'{"condenser_config":{"type":"noop"}}',
            },
            "cybergym_usage": {"usage.json": b'{"turns":1,"tokens":10}', "agent.jsonl": CLEAN_LOG},
            "openhands_native_metrics": {
                "run-metadata.json": (
                    b'{"llm_config":{"num_retries":0},"condenser_config":{"type":"noop"}}'
                ),
                "metrics.json": b"{}",
            },
        }
        trace = bundle(family, files[family])
        # When: call the registry adapter directly, bypassing dispatch.
        result = f.FIDELITY_FAMILIES[family](trace)
        ceiling, refusal = f.strongest_supported_outcome(family, trace.accompaniment)
        # Then: a non-native ceiling can never yield covered clean.
        if refusal is not None:
            assert result.overall is ceiling
        assert result.overall is not f.FidelityOutcome.VIOLATION

    def test_openhands_condensation_event(self) -> None:
        # Given: a native condensation, not an inferred summary counter.
        trace = bundle(
            "openhands_events",
            {
                "events.jsonl": (
                    b'{"type":"Condensation","forgotten_event_ids":[1,2],'
                    b'"summary":"synthetic","summary_offset":0}\n'
                )
            },
        )
        # When / Then: unauthorized transformation is observed.
        assert compaction(f.analyze_trace(trace)).outcome is f.FidelityOutcome.VIOLATION

    def test_openhands_noncontiguous_forgotten_ids(self) -> None:
        # Given: an authorized transformation whose source span has a hole.
        trace = replace(
            bundle(
                "openhands_events",
                {
                    "events.jsonl": (
                        b'{"type":"Condensation","forgotten_event_ids":[1,3],'
                        b'"summary":"synthetic","summary_offset":0}\n'
                    )
                },
            ),
            authorization=f.Authorization(compaction=True),
        )
        # When / Then: authorization cannot repair missing events.
        assert (
            compaction(f.analyze_trace(trace)).refusal
            is f.FidelityRefusal.FIDELITY_SEQUENCE_INCOMPLETE
        )

    def test_cybergym_usage_without_raw_log_is_self_reported(self) -> None:
        # Given: usage accounting with no native observation.
        trace = bundle("cybergym_usage", {"usage.json": b'{"turns":1,"tokens":10}'})
        # When / Then: usage does not prove absence of compaction.
        assert (
            compaction(f.analyze_trace(trace)).refusal
            is f.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY
        )

    def test_native_metrics_maps_max_message_chars(self) -> None:
        # Given: an undeclared per-message truncation configuration.
        trace = bundle(
            "openhands_native_metrics",
            {
                "run-metadata.json": b'{"llm_config":{"max_message_chars":30000}}',
                "metrics.json": b"{}",
            },
        )
        # When / Then: truncation is not mistaken for compaction.
        result = f.analyze_trace(trace)
        assert any(
            x.signal is f.SignalClass.OBSERVATION_TRUNCATION
            and x.outcome is f.FidelityOutcome.VIOLATION
            for x in result.findings
        )

    def test_native_metrics_retries_without_records_is_self_reported(self) -> None:
        # Given: four retries, no per-attempt capture.
        trace = bundle(
            "openhands_native_metrics",
            {"run-metadata.json": b'{"llm_config":{"num_retries":4}}', "metrics.json": b"{}"},
        )
        # When / Then: retry configuration cannot demonstrate provider health.
        result = f.analyze_trace(trace)
        assert any(
            x.signal is f.SignalClass.PROVIDER_ERROR
            and x.refusal is f.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY
            for x in result.findings
        )

    @pytest.mark.parametrize("family", FAMILIES)
    def test_summarization_count_zero_never_yields_clean_compaction(self, family: str) -> None:
        # Given: the incident counter is the only supplied evidence.
        trace = bundle(family, {"result.json": ZERO})
        # When: every adapter passes through the common guard.
        finding = compaction(f.FIDELITY_FAMILIES[family](trace))
        # Then: self-report alone is always insufficient, including conversion families.
        assert (finding.outcome, finding.refusal) == (
            f.FidelityOutcome.INSUFFICIENT_EVIDENCE,
            f.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY,
        )

    def test_unrecognized_family_refuses(self) -> None:
        # Given: a family outside the closed registry.
        trace = bundle("synthetic_unknown", {})
        # When / Then: dispatch refuses rather than guessing a parser.
        assert (
            compaction(f.analyze_trace(trace)).refusal
            is f.FidelityRefusal.FIDELITY_FAMILY_UNRECOGNIZED
        )

    @pytest.mark.parametrize("family", FAMILIES)
    def test_adapters_refuse_oversized_trace(self, family: str) -> None:
        # Given: a supplied artifact beyond the shared byte cap.
        trace = bundle(family, {"agent.jsonl": b"x" * (f.MAX_TRACE_BYTES + 1)})
        # When / Then: direct registry calls cannot bypass bounded reads.
        assert (
            compaction(f.FIDELITY_FAMILIES[family](trace)).refusal
            is f.FidelityRefusal.FIDELITY_TRACE_UNREADABLE
        )
