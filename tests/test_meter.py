"""The external consumption harness: a session export in, a token and wall-clock fold out.

Every expectation below is derived from a source the harness does not read the same way.
The harness folds per-message ``tokens``; these tests compare that fold against the
session-level ``info.tokens`` the same export records separately, so a parser that
mis-reads one of the two shapes is caught rather than confirmed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests import parent_fixtures

ROOT = Path(__file__).parents[1]
METER = ROOT / "tools" / "meter.py"
HARNESS_ROOTS = (".memory", ".seed", ".audit", ".trial", ".podium")
DEFERRED_ROW = "Per-lane consumption metering"


def run_meter(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Invoke the harness the way its documented interface invokes it: by path."""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, str(METER), *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def place_fixture(cwd: Path) -> str:
    """Copy the captured three-node export beside the working directory under test."""
    target = cwd / "export.json"
    target.write_bytes(parent_fixtures.METER_EXPORT.read_bytes())
    return "./export.json"


def fixture_documents() -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = json.loads(parent_fixtures.METER_EXPORT.read_text("utf-8"))
    return loaded


def recorded_totals(documents: list[dict[str, Any]]) -> dict[str, int]:
    """Fold the session-level token record, which the harness never reads."""
    totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for document in documents:
        tokens = document["info"]["tokens"]
        totals["input"] += tokens["input"]
        totals["output"] += tokens["output"]
        totals["cache_read"] += tokens["cache"]["read"]
        totals["cache_write"] += tokens["cache"]["write"]
    return totals


def counts_of(entry: dict[str, Any]) -> dict[str, int]:
    return {name: entry[name] for name in ("input", "output", "cache_read", "cache_write")}


def tree_snapshot(root: Path) -> list[str]:
    return sorted(str(item.relative_to(root)) for item in root.rglob("*"))


def payload_of(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.returncode == 0, result.stderr
    loaded: dict[str, Any] = json.loads(result.stdout)
    return loaded


def session_entry(payload: dict[str, Any], session_id: str) -> dict[str, Any]:
    for entry in payload["sessions"]:
        found: dict[str, Any] = entry
        if found["session"] == session_id:
            return found
    raise AssertionError(f"session {session_id} is absent from the emitted fold")


def test_subtree_totals_sum_every_descendant(tmp_path: Path) -> None:
    documents = fixture_documents()
    export = place_fixture(tmp_path)

    payload = payload_of(run_meter(tmp_path, "sessions", "--export", export, "--json"))

    assert payload["schema"] == "trinity.meter/v1"
    for document in documents:
        entry = session_entry(payload, document["info"]["id"])
        assert counts_of(entry["self"]) == recorded_totals([document])
        assert entry["self"]["messages"] == len(document["messages"])
    root = session_entry(payload, parent_fixtures.METER_ROOT)
    assert counts_of(root["subtree"]) == recorded_totals(documents)
    assert root["subtree"]["messages"] == sum(len(item["messages"]) for item in documents)
    assert counts_of(payload["totals"]) == recorded_totals(documents)


def test_root_filter_excludes_sibling_trees(tmp_path: Path) -> None:
    export = parent_fixtures.write_meter_export(
        tmp_path,
        sessions=(("ses_alpha", None), ("ses_alpha_lane", "ses_alpha"), ("ses_beta", None)),
    )
    documents = json.loads(export.read_text("utf-8"))
    selected = [item for item in documents if item["info"]["id"] != "ses_beta"]

    payload = payload_of(
        run_meter(
            tmp_path, "sessions", "--export", f"./{export.name}", "--root", "ses_alpha", "--json"
        )
    )

    assert [entry["session"] for entry in payload["sessions"]] == ["ses_alpha", "ses_alpha_lane"]
    assert payload["roots"] == ["ses_alpha"]
    assert counts_of(payload["totals"]) == recorded_totals(selected)
    assert "ses_beta" not in json.dumps(payload)


def test_unrecognized_export_is_refused_not_zeroed(tmp_path: Path) -> None:
    (tmp_path / "export.json").write_text(
        json.dumps({"sessions": [{"id": "ses_alpha", "usage": {"prompt": 10}}]}), encoding="utf-8"
    )

    result = run_meter(tmp_path, "sessions", "--export", "./export.json", "--json")

    assert result.returncode == 3
    assert "METER_EXPORT_UNRECOGNIZED" in result.stderr
    assert "trinity.meter/v1" not in result.stdout
    assert "totals" not in result.stdout


@pytest.mark.parametrize("harness", HARNESS_ROOTS)
def test_out_path_inside_a_harness_is_refused(tmp_path: Path, harness: str) -> None:
    export = place_fixture(tmp_path)
    (tmp_path / harness).mkdir()
    out = tmp_path / harness / "meter.json"

    result = run_meter(
        tmp_path, "sessions", "--export", export, "--out", f"./{harness}/meter.json", "--json"
    )

    assert result.returncode == 3
    assert "METER_PATH_IN_HARNESS" in result.stderr
    assert not out.exists()


def test_no_output_is_written_without_out(tmp_path: Path) -> None:
    export = place_fixture(tmp_path)
    before = tree_snapshot(tmp_path)

    result = run_meter(tmp_path, "sessions", "--export", export, "--json")

    assert result.returncode == 0
    assert tree_snapshot(tmp_path) == before


def test_wall_clock_is_derived_from_recorded_instants_not_the_clock(tmp_path: Path) -> None:
    documents = fixture_documents()
    instants = [
        value
        for document in documents
        for value in (document["info"]["time"]["created"], document["info"]["time"]["updated"])
    ]
    export = place_fixture(tmp_path)

    first = run_meter(tmp_path, "sessions", "--export", export, "--json")
    second = run_meter(tmp_path, "sessions", "--export", export, "--json")

    assert first.stdout == second.stdout
    payload = payload_of(first)
    assert payload["totals"]["wall_clock_seconds"] == (max(instants) - min(instants)) / 1000
    root = session_entry(payload, parent_fixtures.METER_ROOT)
    assert root["self"]["wall_clock_seconds"] < root["subtree"]["wall_clock_seconds"]


def test_deferred_row_99_names_the_harness() -> None:
    rows = [
        line
        for line in (ROOT / "DEFERRED.md").read_text("utf-8").splitlines()
        if line.startswith(f"| {DEFERRED_ROW} |")
    ]

    assert len(rows) == 1
    assert "meter.py" in rows[0]
