from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest
from tools import preflight

from tools import gate, integrity, pipeline, runs  # isort: skip
from tools._findings import Finding, Severity
from tools.attest.canonical import JSONValue
from tools.preflight_receipt import Entry, ToolResult, invoke_json, placement

from tests.parent_fixtures import git, write_resume_parent

KEYS = {
    "schema",
    "instrument",
    "run_id",
    "freshness",
    "migration",
    "gate",
    "feedback",
    "preconditions",
    "progress",
    "never_skip",
    "meter",
}


@pytest.fixture
def parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Given a real owned namespace and Git repository; remote qualification is isolated.
    root = tmp_path / "parent"
    write_resume_parent(root, "ENGRAM", "engram-ada-1", approved=True)
    git(["init", "-q"], cwd=root)
    monkeypatch.chdir(root)
    monkeypatch.setenv("GITHUB_ACTOR", "ada")
    monkeypatch.setattr(gate, "run_gate", lambda _root: [])
    monkeypatch.setattr(integrity, "check_work_differential_digests", lambda *_args: [])
    return root


def invoke(instrument: str = "ENGRAM", *, check: bool = True) -> tuple[int, dict[str, JSONValue]]:
    argv = [
        "preflight.py",
        "./",
        "--instrument",
        instrument,
        "--run",
        f"{instrument.lower()}-ada-1",
        "--principal",
        "ada",
        "--moment",
        "report",
        "--json",
    ]
    if check:
        argv.append("--check")
    out = io.StringIO()
    with redirect_stdout(out):
        status = preflight.main(argv)
    decoded: dict[str, JSONValue] = json.loads(out.getvalue())
    return status, decoded


def test_receipt_carries_every_schema_key(parent: Path) -> None:
    # When / Then
    assert parent.is_dir()
    _, receipt = invoke()
    assert set(receipt) == KEYS
    assert receipt["schema"] == "trinity.preflight/v1"


def test_receipt_carries_no_disposition_at_any_depth(parent: Path) -> None:
    assert parent.is_dir()
    _, receipt = invoke()

    def visit(value: JSONValue) -> None:
        if isinstance(value, dict):
            assert "disposition" not in value
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(receipt)


def test_never_skip_entries_are_all_ran_never_skipped(parent: Path) -> None:
    assert parent.is_dir()
    _, receipt = invoke()
    assert isinstance(receipt["never_skip"], dict)
    assert set(receipt["never_skip"]) == {
        "freshness",
        "migrate",
        "gate",
        "feedback_walk",
        "differential_digests",
        "phase_2_instruments",
        "progress_rebuild",
    }
    assert set(receipt["never_skip"].values()) <= {"ran:pass", "ran:fail"}


def test_forge_never_skip_includes_place_then_reconcile(
    parent: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs.open_run(parent, "FORGE", "forge-ada-1", principal="ada")
    order: list[str] = []
    original = placement
    original_reconcile = pipeline.reconcile

    def place(root: Path, *, check: bool) -> bool:
        order.append("place")
        return original(root, check=check)

    def reconcile(root: Path, *, check: bool = False) -> pipeline.Reconciliation:
        order.append("reconcile")
        return original_reconcile(root, check=check)

    monkeypatch.setattr(preflight, "placement", place)
    monkeypatch.setattr(pipeline, "reconcile", reconcile)
    _, receipt = invoke("FORGE")
    assert order == ["place", "reconcile"]
    assert isinstance(receipt["never_skip"], dict)
    assert {"pipeline_place", "pipeline_reconcile"} <= receipt["never_skip"].keys()


def test_engram_never_skip_excludes_them(parent: Path) -> None:
    assert parent.is_dir()
    _, receipt = invoke()
    assert isinstance(receipt["never_skip"], dict)
    assert not {"pipeline_place", "pipeline_reconcile"} & receipt["never_skip"].keys()


@pytest.mark.parametrize("new_run", [False, True])
def test_check_mode_writes_only_the_documented_paths(
    parent: Path,
    monkeypatch: pytest.MonkeyPatch,
    new_run: bool,
) -> None:
    if new_run:
        (parent / ".memory/runs/engram-ada-1/run.json").unlink()
    monkeypatch.setattr(
        gate,
        "run_gate",
        lambda root: [
            Finding("SAB_INERT_INSTRUMENT", Severity.ERROR, str(root / ".memory"), 0, "inert")
        ],
    )
    before = {p.relative_to(parent): p.read_bytes() for p in parent.rglob("*") if p.is_file()}
    invoke()
    after = {p.relative_to(parent): p.read_bytes() for p in parent.rglob("*") if p.is_file()}
    changed = {p.as_posix() for p in after if before.get(p) != after[p]}
    expected = {
        ".sentinel/streams/engram-ada-1/attempts.jsonl",
        ".sentinel/streams/engram-ada-1/head.json",
        ".sentinel/streams/engram-ada-1/ledger.lock",
    }
    if new_run:
        expected.add(".memory/runs/engram-ada-1/run.json")
    assert changed == expected


def test_default_mode_writes_the_gate_receipt(parent: Path) -> None:
    _, receipt = invoke(check=False)
    files = list((parent / ".memory/runs/engram-ada-1/gate-receipts").glob("preflight-*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text()) == receipt


def test_absent_touchstones_yields_precondition_absent_at_hold(
    parent: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (parent / "touchstones").rmdir()
    status, receipt = invoke()
    assert status == 2
    assert isinstance(receipt["preconditions"], dict)
    assert receipt["preconditions"]["touchstones"] == "absent"
    assert "PRECONDITION_ABSENT:touchstones" in capsys.readouterr().err


def test_feedback_walk_runs_before_the_gate_call(
    parent: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert parent.is_dir()
    order: list[str] = []
    original = invoke_json

    def invoke_recorded(entry: Entry, argv: list[str]) -> ToolResult:
        order.append(argv[0])
        return original(entry, argv)

    monkeypatch.setattr(preflight, "invoke_json", invoke_recorded)
    invoke()
    assert order.index("feedback.py") < order.index("gate.py")


def test_gate_envelope_is_embedded_unmodified(parent: Path) -> None:
    assert parent.is_dir()
    _, receipt = invoke()
    assert isinstance(receipt["meter"], dict)
    output = io.StringIO()
    with redirect_stdout(output):
        gate.main(
            [
                "gate.py",
                "./",
                "--instrument",
                "ENGRAM",
                "--run",
                "engram-ada-1",
                "--moment",
                "report",
                "--check",
                "--json",
            ]
        )
    assert receipt["gate"] == json.loads(output.getvalue())


def test_preflight_decides_inside_the_budget(parent: Path) -> None:
    assert parent.is_dir()
    _, receipt = invoke()
    assert isinstance(receipt["meter"], dict)
    assert isinstance(receipt["meter"]["preflight_ms"], int)


def test_block_is_not_lowered_by_missing_preconditions(
    parent: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert parent.is_dir()
    monkeypatch.setattr(
        gate,
        "run_gate",
        lambda root: [
            Finding(
                "TRINITY_FRESHNESS_UNVERIFIABLE",
                Severity.ERROR,
                str(root / "trinity"),
                0,
                "offline",
            )
        ],
    )
    status, receipt = invoke()
    assert status == 3
    assert isinstance(receipt["never_skip"], dict)
    assert receipt["never_skip"]["freshness"] == "ran:fail"


def test_foreign_owner_refuses_before_writes(parent: Path) -> None:
    marker = parent / ".memory/runs/engram-ada-1/run.json"
    data = json.loads(marker.read_text())
    data["principal"] = "other"
    marker.write_text(json.dumps(data))
    assert (
        preflight.main(
            [
                "preflight.py",
                "./",
                "--instrument",
                "ENGRAM",
                "--run",
                "engram-ada-1",
                "--principal",
                "ada",
                "--moment",
                "report",
            ]
        )
        == 3
    )
