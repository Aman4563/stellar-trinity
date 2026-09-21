"""Disk-backed both-halves contracts, including format ceilings and native dispatch."""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest
from tools import forensics as f
from tools.forensics.reading import Json, boolean, child, document, integer, log_records, text

from tests.fidelity_fixtures import load_fixture

ROOT: Final = Path(__file__).parent / "fixtures" / "fidelity"
NATIVE: Final = tuple(f.COVERAGE_CONTRACTS)
CLEAN: Final = sorted(
    set(f.FIDELITY_FAMILIES)
    | {"atif_normalized_with_native", "cybergym_usage_no_raw_log"}
    | {path.name for path in (ROOT / "clean").glob("*") if path.is_dir()}
)


def _load(relative: str) -> f.TraceBundle:
    assert (ROOT / relative / "bundle.json").is_file(), f"missing fixture: {relative}"
    return load_fixture(relative)


def _matrix() -> Mapping[str, Json]:
    path = ROOT / "reachability.json"
    assert path.is_file(), "missing reachability.json"
    return document(path.read_bytes())


@pytest.mark.parametrize("name", CLEAN)
def test_clean_fixtures_resolve_declared_strongest_outcome(name: str) -> None:
    # Given: the directory's declaration, including conditional family ceilings.
    bundle = _load(f"clean/{name}")
    declared = child(child(_matrix(), "families"), bundle.family)
    if name.endswith("_with_native"):
        declared = child(declared, "when_accompanied_by_native")
    if name.endswith("_no_raw_log"):
        declared = child(declared, "without_requires")
    # When: the actual public adapter consumes disk bytes.
    result = f.analyze_trace(bundle)
    # Then: the exact ceiling, never a uniform clean assumption.
    assert result.overall.value == text(declared, "strongest_outcome")
    refusal = text(declared, "ceiling_refusal") if declared["ceiling_refusal"] else None
    if refusal:
        assert f.FidelityRefusal(refusal) in {item.refusal for item in result.findings}
    else:
        assert all(item.refusal is None for item in result.findings)


def test_atif_alone_can_never_reach_covered_clean() -> None:
    # Given: normalized conversion without native evidence.
    trace = _load("clean/atif_normalized")
    # When: classify without promotion from absence of a marker.
    result = f.analyze_trace(trace)
    # Then: conversion-only evidence stays indeterminate.
    assert not trace.accompaniment
    assert result.overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert f.FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY in {
        item.refusal for item in result.findings
    }


def test_accompanied_atif_dispatches_to_native() -> None:
    # Given: a normalized index with its original native source.
    trace = _load("clean/atif_normalized_with_native")
    # When: the public dispatcher chooses the evidence-bearing adapter.
    result = f.analyze_trace(trace)
    # Then: native identity is observable, not merely inferred from a clean verdict.
    assert trace.family == "atif_normalized"
    assert (result.family, result.overall) == ("claude_code_jsonl", f.FidelityOutcome.COVERED_CLEAN)


def test_cybergym_without_raw_log_is_self_reported() -> None:
    # Given: usage accounting without native capture.
    trace = _load("clean/cybergym_usage_no_raw_log")
    # When: analyze its actual artifacts.
    result = f.analyze_trace(trace)
    # Then: usage cannot establish raw-log coverage.
    assert not {"agent.jsonl", "agent/agent.jsonl"} & trace.files.keys()
    assert result.overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    assert f.FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY in {
        item.refusal for item in result.findings
    }


@pytest.mark.parametrize("family", NATIVE)
def test_approved_limits_stay_clean_in_native_families(family: str) -> None:
    # Given: both limits actually fired, rather than merely being configured.
    trace = _load(f"clean/{family}")
    path = f.COVERAGE_CONTRACTS[family][f.SignalClass.TIMEOUT].native_paths[0]
    terminal = log_records(trace.files[path])[-1]
    assert boolean(terminal, "timed_out") is True
    assert (
        integer(terminal, "turns")
        == integer(terminal, "max_turns")
        == (trace.authorization.max_turns)
    )
    assert integer(terminal, "timeout_seconds") == trace.authorization.timeout_seconds
    # When: assess approved limit enforcement independently of solver success.
    result = f.analyze_trace(trace)
    # Then: all eight signals are covered and no violation is manufactured.
    assert result.overall is f.FidelityOutcome.COVERED_CLEAN
    assert {item.signal for item in result.findings} == set(f.SignalClass)
    assert all(item.outcome is f.FidelityOutcome.COVERED_CLEAN for item in result.findings)


def test_strongest_outcome_declared_for_every_family() -> None:
    # Given / When: the checked-in family declarations.
    families = child(_matrix(), "families")
    # Then: closed registry, real enum members, and explicit conditional ceilings.
    assert set(families) == set(f.FIDELITY_FAMILIES)
    for family in families:
        row = child(families, family)
        assert boolean(row, "native") == (family in NATIVE)
        outcome = text(row, "strongest_outcome")
        assert outcome in f.FidelityOutcome.__members__
        refusal = text(row, "ceiling_refusal") if row["ceiling_refusal"] is not None else None
        assert refusal is None or refusal in f.FidelityRefusal.__members__
        assert row["dispatch_to"] is None
        if family not in NATIVE:
            assert refusal is not None
            assert outcome == f.FidelityOutcome.INSUFFICIENT_EVIDENCE.value
    usage = child(families, "cybergym_usage")
    assert usage["requires"] == ["raw_agent_jsonl"]
    assert child(usage, "without_requires") == {
        "strongest_outcome": "INSUFFICIENT_EVIDENCE",
        "ceiling_refusal": "FIDELITY_SELF_REPORTED_ONLY",
        "dispatch_to": None,
    }
    assert child(child(families, "atif_normalized"), "when_accompanied_by_native") == {
        "strongest_outcome": "COVERED_CLEAN",
        "ceiling_refusal": None,
        "dispatch_to": "native_source_family",
    }


def test_reachability_matrix_is_complete() -> None:
    # Given: native contract rows plus the normalized adapter's positive marker path.
    pairs = child(_matrix(), "pairs")
    assert set(pairs) == set(f.FIDELITY_FAMILIES)
    expected: set[str] = set()
    # When: enumerate every declared pair and classify each reachable planted trace.
    for family in pairs:
        rows = child(pairs, family)
        assert set(rows) == {signal.value for signal in f.SignalClass}
        for signal in f.SignalClass:
            row = child(rows, signal.value)
            reachable = boolean(row, "reachable")
            contract_reachable = (
                signal in f.COVERAGE_CONTRACTS[family]
                if family in NATIVE
                else family == "atif_normalized" and signal is f.SignalClass.COMPACTION
            )
            assert reachable is contract_reachable, (family, signal, row)
            relative = f"planted/{family}/{signal.value.lower()}"
            if reachable:
                expected.add(relative)
                result = f.analyze_trace(_load(relative))
                assert result.overall is f.FidelityOutcome.VIOLATION
                assert {
                    item.signal
                    for item in result.findings
                    if item.outcome is f.FidelityOutcome.VIOLATION
                } == {signal}
                assert text(row, "reason")
            else:
                assert text(row, "reason")
                assert not (ROOT / relative).exists()
    # Then: no undeclared directory or missing fixture can silently escape the sweep.
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "planted").glob("*/*")
        if path.is_dir()
    }
    assert actual == expected


def test_fixture_tree_carries_no_client_content() -> None:
    # Given: every file, including any later adversarial fixtures.
    paths = tuple(path for path in ROOT.rglob("*") if path.is_file())
    assert paths, "missing fidelity fixture tree"
    forbidden = re.compile(
        r"cc-bridge-internal|argos|teresa|deku|anubis|yuji|kakashi|kanao|thanatos|levi|envora"
        r"|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.I,
    )
    # When / Then: scan bytes and paths; identifiers are synthetic, never client UUIDs.
    for path in paths:
        assert not forbidden.search(path.relative_to(ROOT).as_posix()), path
        assert not forbidden.search(path.read_text(encoding="utf-8")), path
