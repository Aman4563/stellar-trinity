"""Evidence destruction must not turn absence of evidence into native coverage."""

import re
from dataclasses import replace
from typing import Final

import pytest
from tools import forensics as f
from tools.forensics.capture import capture
from tools.forensics.reading import boolean, child, document, integer, log_records, text

from tests.fidelity_fixtures import FIDELITY_ROOT, load_adversarial_fixture

ROOT: Final = FIDELITY_ROOT / "adversarial"
CASES: Final = (
    ("deleted_event", f.FidelityRefusal.FIDELITY_SEQUENCE_INCOMPLETE),
    ("silent_compaction", f.FidelityRefusal.FIDELITY_VERSION_UNSUPPORTED),
    ("truncated_stream", f.FidelityRefusal.FIDELITY_TRACE_UNREADABLE),
    ("normalization_loss", f.FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY),
    ("marker_stripped", f.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY),
    ("foreign_execution", f.FidelityRefusal.FIDELITY_TRACE_UNREADABLE),
    ("self_reported_clean", f.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY),
)
EXPECTED: Final = {
    **dict.fromkeys((name for name, _ in CASES), f.FidelityOutcome.INSUFFICIENT_EVIDENCE),
    "contradictory_native_normalized": f.FidelityOutcome.VIOLATION,
}


def _load(name: str) -> f.TraceBundle:
    assert (ROOT / name / "bundle.json").is_file(), f"missing adversarial fixture: {name}"
    return load_adversarial_fixture(name)


def test_adversarial_fixtures_are_never_clean() -> None:
    # Given: enumerate directories, not a fixed list that future cases could escape.
    directories = tuple(path for path in ROOT.glob("*") if path.is_dir())
    assert len(directories) >= 7, "missing seven adversarial fixture directories"
    assert {path.name for path in directories} == set(EXPECTED)
    # When / Then: every on-disk case is classified through the public dispatcher.
    for directory in directories:
        result = f.analyze_trace(_load(directory.name))
        assert result.overall is not f.FidelityOutcome.COVERED_CLEAN, directory.name
        assert result.overall is EXPECTED[directory.name], directory.name


@pytest.mark.parametrize(("name", "refusal"), CASES)
def test_adversarial_fixtures_name_expected_refusal(name: str, refusal: f.FidelityRefusal) -> None:
    # Given: one minimal, named evidence-destruction case.
    bundle = _load(name)
    # When: consume the original fixture bytes.
    result = f.analyze_trace(bundle)
    # Then: the intended refusal, not merely any non-clean verdict.
    assert result.overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert refusal in {finding.refusal for finding in result.findings}


def test_foreign_execution_is_refused_despite_being_well_formed() -> None:
    # Given: complete native capture, independently clean under its recorded identity.
    bundle = _load("foreign_execution")
    records = log_records(bundle.files["agent.jsonl"])
    stream = capture(records, "agent.jsonl")
    recorded = text(stream.start, "rollout_id")
    assert stream.complete and recorded and recorded != bundle.rollout_id
    assert f.analyze_trace(replace(bundle, rollout_id=recorded)).overall is (
        f.FidelityOutcome.COVERED_CLEAN
    )
    # When: request a different rollout without changing a single captured byte.
    result = f.analyze_trace(bundle)
    # Then: provenance, not structural parsing, refuses this otherwise perfect trace.
    assert result.overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert all(
        finding.refusal is f.FidelityRefusal.FIDELITY_TRACE_UNREADABLE
        and "rollout_identity_mismatch" in finding.evidence_pointer
        for finding in result.findings
    )


def test_normalization_loss_pair_diverges() -> None:
    # Given: side-by-side native evidence and a derivative that dropped the boundary.
    bundle = _load("normalization_loss")
    records = log_records(bundle.files["agent.jsonl"])
    assert any(text(event, "subtype") == "compact_boundary" for event in records)
    normalized = replace(
        bundle, files={"agent/trajectory.json": bundle.files["agent/trajectory.json"]}
    )
    native = replace(bundle, family="claude_code_jsonl", harness_version="2.1.158")
    # When: analyze both sides independently and then their declared accompaniment.
    results = tuple(
        f.analyze_trace(trace)
        for trace in (
            native,
            normalized,
            replace(bundle, accompaniment=frozenset({"claude_code_jsonl"})),
        )
    )
    # Then: native evidence survives dispatch; the derivative cannot claim absence.
    assert tuple(result.overall for result in results) == (
        f.FidelityOutcome.VIOLATION,
        f.FidelityOutcome.INSUFFICIENT_EVIDENCE,
        f.FidelityOutcome.VIOLATION,
    )
    assert f.FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY in {
        finding.refusal for finding in results[1].findings
    }


def test_self_reported_clean_reproduces_the_incident() -> None:
    # Given: the exact false-negative counter/config combination, no native bytes.
    bundle = _load("self_reported_clean")
    assert set(bundle.files) == {"result.json"}
    report = document(bundle.files["result.json"])
    metadata = child(child(report, "agent_result"), "metadata")
    assert integer(metadata, "summarization_count") == 0
    assert boolean(metadata, "enable_summarize") is False
    # When: classify the self-report through the real adapter.
    result = f.analyze_trace(bundle)
    # Then: no zero counter supplies native coverage.
    assert result.overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert {finding.refusal for finding in result.findings} == {
        f.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY
    }


def test_adversarial_tree_carries_no_client_content() -> None:
    # Given: all payloads and names, including future cases and malformed JSONL.
    paths = tuple(path for path in ROOT.rglob("*") if path.is_file())
    assert paths, "missing adversarial fixture tree"
    forbidden = re.compile(
        r"cc-bridge-internal|argos|teresa|deku|anubis|yuji|kakashi|kanao|thanatos|levi|envora"
        r"|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        r"|/Users/|/home/|https?://|[\w.+-]+@[\w.-]+",
        re.I,
    )
    # When / Then: scan bytes and paths, never requiring the damaged logs to parse.
    for path in paths:
        assert not forbidden.search(path.relative_to(ROOT).as_posix()), path
        assert not forbidden.search(path.read_text(encoding="utf-8")), path
