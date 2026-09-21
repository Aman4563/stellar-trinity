from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tools import runs

NOW = datetime(2026, 9, 17, 12, 0, 5, tzinfo=UTC)


def test_new_run_id_is_instrument_principal_stamp_and_entropy() -> None:
    run_id = runs.new_run_id("FORGE", "Ada Lovelace", NOW)

    assert run_id.startswith("forge-ada-lovelace-20260917t120005z-")
    assert runs.RUN_ID.fullmatch(run_id)
    assert runs.new_run_id("FORGE", "Ada Lovelace", NOW) != run_id


@pytest.mark.parametrize(
    "run_id",
    ["forge-ada-20260917t120005z-0a1b2c", "crucible-x-1", "a" * 80, "engram.1.2.3"],
)
def test_run_id_grammar_accepts_lowercase_dotted_dashed(run_id: str) -> None:
    assert runs.parse_run_id(run_id) == run_id


@pytest.mark.parametrize(
    "run_id", ["FORGE-ada", "-forge", "forge ada", "ab", "a" * 81, "forge/ada", "..", ""]
)
def test_run_id_grammar_refuses_shapes_that_escape_or_collide(run_id: str) -> None:
    with pytest.raises(runs.RunError) as refused:
        runs.parse_run_id(run_id)
    assert refused.value.code == "invalid-run-id"


def test_open_run_writes_run_json_once(tmp_path: Path) -> None:
    run_id = runs.new_run_id("FORGE", "ada", NOW)

    first = runs.open_run(tmp_path, "FORGE", run_id, principal="ada", now=NOW)
    again = runs.open_run(tmp_path, "FORGE", run_id, principal="ada", now=NOW)

    assert first == again == tmp_path / ".seed" / "runs" / run_id
    assert json.loads((first / "run.json").read_text(encoding="utf-8")) == {
        "schema": "trinity.run/v1",
        "instrument": "FORGE",
        "run_id": run_id,
        "principal": "ada",
        "started_at": "2026-09-17T12:00:05Z",
    }


def test_open_run_refuses_a_run_owned_by_another_instrument_or_principal(tmp_path: Path) -> None:
    run_id = runs.new_run_id("FORGE", "ada", NOW)
    runs.open_run(tmp_path, "FORGE", run_id, principal="ada", now=NOW)

    with pytest.raises(runs.RunError) as wrong_principal:
        runs.open_run(tmp_path, "FORGE", run_id, principal="bob", now=NOW)
    with pytest.raises(runs.RunError) as wrong_instrument:
        runs.open_run(tmp_path, "CRUCIBLE", run_id, principal="ada", now=NOW)

    assert wrong_principal.value.code == "run-owned"
    assert wrong_instrument.value.code == "run-owned"


def test_run_dir_maps_each_instrument_to_its_harness(tmp_path: Path) -> None:
    assert runs.run_dir(tmp_path, "FORGE", "forge-ada-1") == tmp_path / ".seed/runs/forge-ada-1"
    assert runs.run_dir(tmp_path, "CRUCIBLE", "crucible-1") == tmp_path / ".audit/runs/crucible-1"
    assert runs.run_dir(tmp_path, "ENGRAM", "engram-1-2") == tmp_path / ".memory/runs/engram-1-2"
    with pytest.raises(runs.RunError) as no_harness:
        runs.run_dir(tmp_path, "MAESTRO", "maestro-1-2")
    assert no_harness.value.code == "invalid-instrument"
    with pytest.raises(runs.RunError) as foreign:
        runs.run_dir(tmp_path, "CRUCIBLE", "forge-ada-1")
    assert foreign.value.code == "run-owned"


def test_list_runs_returns_only_valid_run_json_owners(tmp_path: Path) -> None:
    a = runs.new_run_id("FORGE", "ada", NOW)
    b = runs.new_run_id("FORGE", "bob", NOW)
    runs.open_run(tmp_path, "FORGE", a, principal="ada", now=NOW)
    runs.open_run(tmp_path, "FORGE", b, principal="bob", now=NOW)
    (tmp_path / ".seed/runs/stray").mkdir()
    (tmp_path / ".seed/runs/README.md").write_text("x", encoding="utf-8")

    listed = runs.list_runs(tmp_path, "FORGE")

    assert [item.run_id for item in listed] == sorted([a, b])
    assert {item.principal for item in listed} == {"ada", "bob"}
