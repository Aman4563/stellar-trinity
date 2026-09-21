from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from tools import dashboard, reports, runs, tracker_cache

from tests.bite_shared.registration import bite

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)


def test_check_root_reports_writes_nothing(tmp_path: Path) -> None:
    # Given a parent repository with a run but no tracker cache.
    run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD")
    assert tracker_cache.git_output(tmp_path, ("init", "-q")) is not None
    cache = tracker_cache.git_output(tmp_path, ("rev-parse", "--git-path", "trinity/tracker-cache"))
    assert cache is not None
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    # When checking generated reports, then no file or directory is created.
    reports.check_root_reports(str(tmp_path))
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} == before
    assert not (tmp_path / cache).exists()
    assert list((tmp_path / ".git/trinity").rglob("*")) == []


def test_render_persists_cache_but_check_does_not(tmp_path: Path) -> None:
    # Given persisted cache entries with one source changed since rendering.
    directory = run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD")
    assert tracker_cache.git_output(tmp_path, ("init", "-q")) is not None
    reports.render_root_reports(tmp_path)
    cache = tmp_path / ".git/trinity/tracker-cache"
    before = {p: p.read_bytes() for p in cache.rglob("*") if p.is_file()}
    assert before
    path = directory.parent / "progress.yaml"
    path.write_bytes(path.read_bytes() + b"\n")
    # When a check encounters a miss, then it leaves the existing cache untouched.
    reports.check_root_reports(str(tmp_path))
    assert {p: p.read_bytes() for p in cache.rglob("*") if p.is_file()} == before


def section(text: str, heading: str) -> str:
    return text.split(heading + "\n", 1)[1].split("\n## ", 1)[0].strip()


def run_report(
    root: Path, instrument: str, run_id: str, disposition: str, *, principal: str = "ada"
) -> Path:
    directory = runs.open_run(root, instrument, run_id, principal=principal, now=NOW)
    body = (
        "## Executive summary\n\nsummary of the run\n\n"
        f"## Disposition\n\n{disposition}\n\n"
        "## Findings\n\n- one finding\n\n"
        "## Coverage gaps\n\n- one gap\n\n"
        "## Escalations\n\nnone\n\n"
        "## Flag legend\n\nlegend\n"
    )
    (directory / "report.md").write_text(body, encoding="utf-8")
    (directory / "progress.yaml").write_text(
        "phase: Phase 2\nphases_done: 3\nphases_total: 6\ngates_done: 1\ngates_total: 2\n"
        "open_gates: [design]\ngaps: 1\n",
        encoding="utf-8",
    )
    (directory / "disposition.json").write_text(
        json.dumps(
            {
                "schema": "trinity.qualification/v2",
                "instrument": instrument,
                "run_id": run_id,
                "disposition": disposition,
                "subject_digest": "a" * 64,
                "trinity_commit": "b" * 40,
                "generated_at": "2026-09-17T12:00:00Z",
                "producer": principal,
                "approver": "unsigned",
            }
        ),
        encoding="utf-8",
    )
    return directory / "report.md"


@bite("shared.md:A60")
def test_root_report_is_rendered_from_every_run_and_states_the_worst_disposition(
    tmp_path: Path,
) -> None:
    run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD:PILOT_REQUIRED")
    run_report(tmp_path, "FORGE", "forge-bob-1", "BLOCK:INVALID_TASK", principal="bob")
    run_report(tmp_path, "FORGE", "forge-cat-1", "SHIP_ELIGIBLE", principal="cat")

    written = reports.render_root_reports(tmp_path)

    assert written == ["EDICT.md", "TRACKING.md"]
    text = (tmp_path / "EDICT.md").read_text(encoding="utf-8")
    assert text.startswith(reports.GENERATED_BANNER)
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    assert headings == [f"## {name}" for name in reports.REPORT_SECTIONS]
    assert "\n## Disposition\n\nBLOCK:INVALID_TASK\n" in text
    for run_id in ("forge-ada-1", "forge-bob-1", "forge-cat-1"):
        assert f".seed/runs/{run_id}/report.md" in text
    assert reports.render_root_reports(tmp_path) == []


def test_root_report_never_states_ship_from_runs_alone(tmp_path: Path) -> None:
    run_report(tmp_path, "CRUCIBLE", "crucible-ada-1", "SHIP")

    reports.render_root_reports(tmp_path)

    text = (tmp_path / "VERDICT.md").read_text(encoding="utf-8")
    assert "\n## Disposition\n\nSHIP_ELIGIBLE\n" in text


def test_instrument_sections_open_with_the_four_line_digest(tmp_path: Path) -> None:
    # Given two FORGE runs and three resident sample bundles.
    run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD:PILOT_REQUIRED")
    run_report(tmp_path, "FORGE", "forge-bob-1", "HOLD:PILOT_REQUIRED", principal="bob")
    (tmp_path / "samples").mkdir()
    for index in range(3):
        (tmp_path / "samples" / f"{index:08x}-0000-5000-8000-{index:012x}").mkdir()

    # When the root reports are rendered.
    reports.render_root_reports(tmp_path)

    # Then the digest opens each instrument section and the ratio moves to the headline.
    text = (tmp_path / reports.TRACKER).read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# TRACKING.md"
    assert text.splitlines()[2] == f"> **{reports.GENERATED_BANNER}**"
    assert text.count(reports.GENERATED_BANNER) == 1
    assert "| samples occupancy | 3 of 30 (10%) |" in section(text, "## Headline")
    assert section(text, "## FORGE").splitlines()[2:6] == [
        "- status: HOLD:PILOT_REQUIRED (waiting for an outside signed test run)",
        "- phase: Phase 2",
        "- progress: phases 6 of 12 (50%), gates 2 of 4 (50%)",
        "- pending: 2 open gates (design, design), 2 gaps",
    ]
    assert section(text, "## ENGRAM").splitlines()[2:6] == [
        "- status: no run",
        "- phase: no run",
        "- progress: no run",
        "- pending: no run",
    ]


def test_tracker_history_keeps_every_earlier_run(tmp_path: Path) -> None:
    # Given one FORGE run rendered into the tracker.
    run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD:PILOT_REQUIRED")
    reports.render_root_reports(tmp_path)
    first = (tmp_path / reports.TRACKER).read_text(encoding="utf-8")
    assert "## History" in first
    assert first.count("| FORGE | forge-ada-1 | ada | HOLD:PILOT_REQUIRED | Phase 2 |") == 1

    # When a later CRUCIBLE run lands and the tracker is rendered again.
    later = runs.open_run(
        tmp_path,
        "CRUCIBLE",
        "crucible-bob-1",
        principal="bob",
        now=NOW.replace(hour=13),
    )
    run_report(tmp_path, "CRUCIBLE", "crucible-bob-1", "BLOCK:INVALID_TASK", principal="bob")
    assert later.is_dir()
    assert reports.render_root_reports(tmp_path) == ["VERDICT.md", reports.TRACKER]

    # Then the earlier row survives, oldest first, under the full section skeleton.
    second = (tmp_path / reports.TRACKER).read_text(encoding="utf-8")
    history = section(second, "## History").splitlines()
    rows = [line for line in history if line.startswith("| 2026-")]
    assert rows == [
        "| 2026-09-17T12:00:00Z | FORGE | forge-ada-1 | ada | HOLD:PILOT_REQUIRED | Phase 2 "
        "| unknown | open |",
        "| 2026-09-17T13:00:00Z | CRUCIBLE | crucible-bob-1 | bob | BLOCK:INVALID_TASK | Phase 2 "
        "| unknown | open |",
    ]
    headings = [line for line in second.splitlines() if line.startswith("## ")]
    assert headings == list(dashboard.HEADINGS)
    assert reports.check_root_reports(str(tmp_path)) == []


def test_render_leaves_hand_written_root_reports_alone(tmp_path: Path) -> None:
    # Given a parent-shaped tree with no run and a hand-written root report.
    (tmp_path / ".seed").mkdir()
    (tmp_path / "EDICT.md").write_text("hand written\n", encoding="utf-8")

    # When the root reports are rendered.
    written = reports.render_root_reports(tmp_path)

    # Then the dashboard is rendered and the hand-written report keeps its bytes.
    assert written == [reports.TRACKER]
    assert (tmp_path / "EDICT.md").read_text(encoding="utf-8") == "hand written\n"


def test_render_is_a_no_op_outside_a_parent(tmp_path: Path) -> None:
    # Given a bare directory that carries no harness and no tracker.

    # When the root reports are rendered.
    written = reports.render_root_reports(tmp_path)

    # Then nothing at all is emitted into a tree that is not parent-shaped.
    assert written == []
    assert list(tmp_path.iterdir()) == []


def test_check_root_reports_refuses_a_hand_edited_tracker(tmp_path: Path) -> None:
    # Given a rendered tracker with exactly one character changed by hand.
    run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD:PILOT_REQUIRED")
    reports.render_root_reports(tmp_path)
    path = tmp_path / reports.TRACKER
    original = path.read_text(encoding="utf-8")
    edited = original.replace("As of ", "As on ", 1)
    assert sum(a != b for a, b in zip(original, edited, strict=True)) == 1
    path.write_text(edited, encoding="utf-8")

    # When the report check runs.
    findings = reports.check_root_reports(str(tmp_path))

    # Then the exact comparison names the drift rather than exempting the instant line.
    assert [(item.code, item.message) for item in findings] == [
        ("REPORT_NOT_RENDERED", "TRACKING.md is not rendered from its run reports")
    ]


def test_check_root_reports_reports_a_malformed_card(tmp_path: Path) -> None:
    # Given a rendered parent whose only tracker card is unreadable.
    directory = run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD:PILOT_REQUIRED").parent
    (directory / "tracker.json").write_text("{ not a card", encoding="utf-8")
    reports.render_root_reports(tmp_path)

    # When the report check runs.
    findings = reports.check_root_reports(str(tmp_path))

    # Then the card is named as a finding instead of silently reading as closure.
    assert [item.code for item in findings] == ["TRACKER_CARD_MALFORMED"]


def test_check_reports_drift(tmp_path: Path) -> None:
    run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD:PILOT_REQUIRED")
    assert [item.message for item in reports.check_root_reports(str(tmp_path))] == [
        "EDICT.md is not rendered from its run reports",
        "TRACKING.md is not rendered from its run reports",
    ]
    reports.render_root_reports(tmp_path)
    assert reports.check_root_reports(str(tmp_path)) == []
