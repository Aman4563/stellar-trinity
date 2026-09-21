from __future__ import annotations

import json
import re
from dataclasses import FrozenInstanceError, asdict, fields, replace
from graphlib import TopologicalSorter
from pathlib import Path
from typing import Final

import pytest
import tools._phases as phases
from tools.attest import canonical

ROOT: Final = Path(__file__).resolve().parents[1]
INSTRUMENTS: Final = ("ENGRAM", "FORGE", "CRUCIBLE")


def paths(row: phases.Phase) -> tuple[str, ...]:
    return (
        row.reads
        + row.reconciles
        + row.artifacts
        + tuple(path for path in (row.approval_file, row.approval_binds) if path is not None)
    )


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_every_table_path_is_named_in_its_contract_section(instrument: str) -> None:
    # Given the authoritative contract, not a fixture repeating the table.
    text = (ROOT / Path(phases.CONTRACT[instrument]).name).read_text(encoding="utf-8")
    for row in phases.TABLE[instrument]:
        # When resolving the exact heading's own slice, never a neighbouring phase.
        section = text.split(row.contract_heading + "\n", 1)[1].split("\n### ", 1)[0]
        # Then every static path prefix is present, including approval bindings.
        for path in paths(row):
            stem = re.split(r"[*?\[]", path.removeprefix("./"), maxsplit=1)[0]
            assert stem and stem in section, (instrument, row.id, path)


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_every_contract_heading_exists_verbatim(instrument: str) -> None:
    # Given the contract's structural routing tokens.
    lines = (ROOT / Path(phases.CONTRACT[instrument]).name).read_text().splitlines()
    # When collecting the table's anchors.
    headings = {row.contract_heading for row in phases.TABLE[instrument]}
    # Then every anchor is a literal H3 line, not a paraphrase of prose.
    assert headings <= {line for line in lines if line.startswith("### ")}


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_depends_on_is_acyclic_and_closed(instrument: str) -> None:
    # Given all branches of an instrument, including its internal human stops.
    rows = phases.TABLE[instrument]
    graph = {row.id: row.depends_on for row in rows}
    # When topologically sorting the dependency graph.
    ordered = tuple(TopologicalSorter(graph).static_order())
    # Then no cycle, duplicate id, dangling dependency, or self-dependency survives.
    assert len(graph) == len(rows)
    assert set(ordered) == set(graph)
    for row in rows:
        assert row.id not in row.depends_on
        assert all(ordered.index(dep) < ordered.index(row.id) for dep in row.depends_on)


def test_kinds_and_branches_are_closed() -> None:
    # Given the closed vocabulary and the default flow fixed by the contracts.
    expected = {
        "ENGRAM": ("0", "0.5", "1", "2", "S", "commit", "report"),
        "FORGE": ("place_reconcile", "R", "0", "0.5", "1", "2", "3", "4", "4.5"),
        "CRUCIBLE": ("R", "0", "0.5", "1", "2"),
    }
    # When selecting each default or explicitly invoked branch.
    selected = {name: phases.phases(name) for name in INSTRUMENTS}
    # Then selection preserves table order and lookups do not silently fall back.
    assert phases.KINDS == ("work", "gate", "always", "barrier")
    assert phases.BRANCHES == ("default", "G", "H", "N", "S")
    assert {name: tuple(row.id for row in rows) for name, rows in selected.items()} == expected
    for name, rows in phases.TABLE.items():
        for row in rows:
            assert row.instrument == name
            assert row.kind in phases.KINDS
            assert row.branches and set(row.branches) <= set(phases.BRANCHES)
            assert phases.phase(name, row.id) == row
        for branch in phases.BRANCHES:
            assert phases.phases(name, branch) == tuple(
                row for row in rows if branch in row.branches
            )
    for operation in (
        lambda: phases.phases("unknown"),
        lambda: phases.phases("ENGRAM", "unknown"),
        lambda: phases.phase("ENGRAM", "unknown"),
        lambda: phases.phase("unknown", "0"),
        lambda: phases.never_skip("unknown"),
    ):
        with pytest.raises(phases.PhaseError) as refusal:
            operation()
        assert refusal.value.code
        assert str(refusal.value).startswith(refusal.value.code + ": ")
    for field in fields(phases.Phase):
        with pytest.raises(FrozenInstanceError):
            setattr(selected["ENGRAM"][0], field.name, None)


def test_gate_rows_carry_both_approval_fields() -> None:
    # Given the single-artifact approval pairs actually named in their sections.
    expected = {
        ("ENGRAM", "0.5"): ("./.memory/approval", "./.memory/scope.yaml"),
        ("ENGRAM", "G.0.5"): ("./.memory/genesis.approval", "./.memory/genesis.yaml"),
        ("FORGE", "0.5"): ("./.seed/contract.approved", "./.seed/contract.yaml"),
        ("CRUCIBLE", "0.5"): ("./.audit/scope.approved", "./.audit/scope.yaml"),
    }
    # When projecting the gate bindings.
    actual = {
        (name, row.id): (row.approval_file, row.approval_binds)
        for name, rows in phases.TABLE.items()
        for row in rows
        if row.kind == "gate"
    }
    # Then only supported digest pairs are gates; release-set approval stays a barrier.
    assert actual == expected
    for rows in phases.TABLE.values():
        for row in rows:
            if row.kind != "gate":
                assert (row.approval_file, row.approval_binds) == (None, None)
    assert phases.phase("FORGE", "4.5").kind == "barrier"
    assert "./.seed/release.approved" in phases.phase("FORGE", "4.5").reads
    for phase_id in ("commit", "report", "G.election", "H.adjudication"):
        assert phases.phase("ENGRAM", phase_id).kind == "barrier"


@pytest.mark.parametrize("instrument", INSTRUMENTS)
def test_never_skip_includes_phase_two_for_every_instrument(instrument: str) -> None:
    # Given the per-invocation deterministic phase.
    assert phases.phase(instrument, "2").kind == "always"
    # When requesting the never-skip roster.
    checks = phases.never_skip(instrument)
    # Then phase two is present even when branch selection would omit it.
    assert "2" in checks
    assert checks == tuple(row.id for row in phases.TABLE[instrument] if row.kind == "always")


def test_never_skip_includes_place_reconcile_for_forge_only() -> None:
    # Given the three separate instrument rosters.
    # When projecting placement obligations.
    owners = tuple(name for name in INSTRUMENTS if "place_reconcile" in phases.never_skip(name))
    # Then FORGE alone repeats placement before research, with no peer input channel.
    assert owners == ("FORGE",)
    assert phases.phase("FORGE", "R").depends_on == ("place_reconcile",)
    assert not any(
        path.startswith(("./.memory/", "./HARDNESS.md"))
        for row in phases.TABLE["CRUCIBLE"]
        for path in paths(row)
    )


def test_table_digest_is_stable_and_content_sensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given an independently serialized copy of every row and every field.
    body = {
        name: [json.loads(json.dumps(asdict(row))) for row in rows]
        for name, rows in phases.TABLE.items()
    }
    expected = canonical.canonical_sha256(body)
    # When hashing the registry repeatedly and then changing just one field in a copy.
    first = phases.table_digest()
    second = phases.table_digest()
    row = phases.TABLE["ENGRAM"][0]
    variants = (
        replace(row, id="changed"),
        replace(row, instrument="FORGE"),
        replace(row, kind="always"),
        replace(row, contract_heading="### Changed"),
        replace(row, branches=("G",)),
        replace(row, reads=("./changed",)),
        replace(row, reconciles=("./changed",)),
        replace(row, artifacts=("./changed",)),
        replace(row, approval_file="./changed"),
        replace(row, approval_binds="./changed"),
        replace(row, depends_on=("changed",)),
    )
    # Then hashes use ADR 0003 bytes and bind all fields, never a cached constant.
    assert first == second == expected
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    for changed in variants:
        monkeypatch.setitem(phases.TABLE, "ENGRAM", (changed, *phases.TABLE["ENGRAM"][1:]))
        assert phases.table_digest() != first


def test_paths_start_at_dot_slash() -> None:
    # Given all authored path fields and contract paths.
    authored = tuple(phases.CONTRACT.values()) + tuple(
        path for rows in phases.TABLE.values() for row in rows for path in paths(row)
    )
    # When checking their project-relative spelling.
    invalid = tuple(
        path for path in authored if not path.startswith("./") or ".." in Path(path).parts
    )
    # Then no absolute or parent-escaping path is published.
    assert invalid == ()
