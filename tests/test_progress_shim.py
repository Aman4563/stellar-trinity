from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest
from tools import reports, runs, tracker, tracker_cache

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
CLOSED: Final = "2026-09-17T15:00:00Z"
INSTRUMENT: Final = "FORGE"
RUN: Final = "forge-ada-1"
PRINCIPAL: Final = "ada"
FLAT_KEYS: Final = (
    "phase",
    "phases_done",
    "phases_total",
    "gates_done",
    "gates_total",
    "open_gates",
    "gaps",
    "schema",
    "authority",
    "resume_at",
)
SHIM: Final[dict[str, str]] = {
    "phase": "Phase 2",
    "phases_done": "4",
    "phases_total": "7",
    "gates_done": "2",
    "gates_total": "5",
    "open_gates": "[scope sign-off, release evidence]",
    "gaps": "3",
    "schema": "trinity.progress/v1",
    "authority": "derived",
    "resume_at": "2",
}
COUNTS: Final[dict[str, int]] = {
    "phases_done": 4,
    "phases_total": 7,
    "gates_done": 2,
    "gates_total": 5,
    "gaps": 3,
}
GATES: Final = ["release evidence", "scope sign-off"]
NESTED: Final = 'phases:\n  "0":\n    status: complete\n'
REPORT: Final = (
    "## Executive summary\n\nsummary of the run\n\n"
    "## Disposition\n\nHOLD:PILOT_REQUIRED\n\n"
    "## Findings\n\n- one finding\n\n"
    "## Coverage gaps\n\n- one gap\n\n"
    "## Escalations\n\nnone\n\n"
    "## Flag legend\n\nlegend\n"
)


def write_run(root: Path, fields: dict[str, str], *, nested: str = "") -> Path:
    directory = runs.open_run(root, INSTRUMENT, RUN, principal=PRINCIPAL, now=NOW)
    (directory / "report.md").write_text(REPORT, encoding="utf-8")
    body = "".join(f"{name}: {fields[name]}\n" for name in FLAT_KEYS) + nested
    (directory / "progress.yaml").write_text(body, encoding="utf-8")
    return directory


def run_of(root: Path) -> runs.Run:
    return runs.list_runs(root, INSTRUMENT)[0]


def derive(root: Path, directory: Path) -> dict[str, object]:
    target = tracker.Target(root, INSTRUMENT, RUN)
    return tracker._derive(target, run_of(root), directory)


def test_flat_keys_survive_reports_progress(tmp_path: Path) -> None:
    # Given every shim key written at column zero.
    directory = write_run(tmp_path, SHIM)

    # When the flat parser reads the cache.
    parsed = reports._progress(directory)

    # Then every key survives with its authored value and nothing else appears.
    assert parsed == SHIM


def test_indented_nested_block_is_invisible_to_the_flat_parser(tmp_path: Path) -> None:
    # Given a nested phases block below the flat keys.
    directory = write_run(tmp_path, SHIM, nested=NESTED)

    # When the flat parser reads the cache.
    parsed = reports._progress(directory)

    # Then only the column-zero key is seen and no nested name leaks into it.
    assert parsed == {**SHIM, "phases": ""}
    assert "status" not in parsed
    assert '"0"' not in parsed


def test_open_gates_list_grammar_round_trips(tmp_path: Path) -> None:
    # Given two gate names inside the bracketed comma list.
    directory = write_run(tmp_path, SHIM)

    # When the tracker derives the card fields from those bytes.
    derived = derive(tmp_path, directory)

    # Then the raw line is carried verbatim and the derived list is sorted.
    assert reports._progress(directory)["open_gates"] == SHIM["open_gates"]
    assert derived["open_gates"] == GATES


def test_gate_name_with_a_comma_is_unrepresentable(tmp_path: Path) -> None:
    # Given one authored gate name that itself contains a comma.
    directory = write_run(tmp_path, {**SHIM, "open_gates": "[release, evidence]"})

    # When the tracker derives the card fields from those bytes.
    derived = derive(tmp_path, directory)

    # Then the single name splits into two entries, so the writer must refuse it.
    assert reports._progress(directory)["open_gates"] == "[release, evidence]"
    assert derived["open_gates"] == ["evidence", "release"]


def test_tracker_card_derives_every_count_from_the_shim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a run whose cache states counts and a phase that differ from every fallback.
    write_run(tmp_path, SHIM)
    monkeypatch.chdir(tmp_path)
    argv = ["tracker.py", "card", "./", "--instrument", INSTRUMENT, "--run-id", RUN]

    # When the card is frozen through the CLI.
    code = tracker.main([*argv, "--closed-at", CLOSED])

    # Then every count and the phase come from the shim rather than from zeros and unknown.
    assert code == 0
    card = json.loads(
        (runs.run_dir(tmp_path, INSTRUMENT, RUN) / "tracker.json").read_text(encoding="utf-8")
    )
    assert {name: card[name] for name in tracker.COUNT_NAMES} == COUNTS
    assert card["phase"] == SHIM["phase"]
    assert card["open_gates"] == GATES


def test_tracker_cache_reads_the_same_shim(tmp_path: Path) -> None:
    # Given one cache and both derived readers of it.
    directory = write_run(tmp_path, SHIM)
    derived = derive(tmp_path, directory)

    # When the disposable projection parses the same bytes.
    record = tracker_cache._parse_run(directory, run_of(tmp_path))

    # Then it agrees with the card on every shim field.
    assert record.phase == derived["phase"] == SHIM["phase"]
    assert list(record.open_gates) == derived["open_gates"] == GATES
    assert {name: getattr(record, name) for name in tracker.COUNT_NAMES} == COUNTS
    assert {name: derived[name] for name in tracker.COUNT_NAMES} == COUNTS


def test_progress_rebuild_output_satisfies_every_consumer(tmp_path: Path) -> None:
    # Given a run whose cache the writer owns rather than the fixture.
    progress = importlib.import_module("tools.progress")
    directory = runs.open_run(tmp_path, INSTRUMENT, RUN, principal=PRINCIPAL, now=NOW)
    (directory / "report.md").write_text(REPORT, encoding="utf-8")

    # When the writer rebuilds the projection from disk.
    progress.rebuild(tmp_path, INSTRUMENT, RUN, principal=PRINCIPAL)

    # Then all three consumers read the emitted bytes and agree on every field.
    parsed = reports._progress(directory)
    derived = derive(tmp_path, directory)
    record = tracker_cache._parse_run(directory, run_of(tmp_path))
    assert set(FLAT_KEYS) <= set(parsed)
    assert derived["phase"] == parsed["phase"] == record.phase != "unknown"
    assert list(record.open_gates) == derived["open_gates"]
    assert {name: derived[name] for name in tracker.COUNT_NAMES} == {
        name: getattr(record, name) for name in tracker.COUNT_NAMES
    }
