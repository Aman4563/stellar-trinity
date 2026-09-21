"""Observable contracts for the pure, recorded-time dashboard."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Final

from tools import dashboard, reports
from tools.dashboard_charts import elapsed
from tools.tracker_cache import RunRecord
from tools.tracker_snapshot import EpochRecord, load_snapshot

from tests.tracker_fixtures import parent_fixture
from tests.tracker_surfaces import write_run

EXPECTED_HEADINGS: Final = (
    "## Headline",
    "## Organizational lanes",
    "## Disposition board",
    "## Decisions needed",
    "## Changed since boundary",
    "## Cycle timeline",
    "## Bundle flow",
    "## Samples occupancy",
    "## Aging work",
    "## Blockers and escalations",
    "## Sign-off log",
    "## ENGRAM",
    "## FORGE",
    "## CRUCIBLE",
    "## History",
    "## Flag legend",
)
INSTRUMENTS: Final = ("ENGRAM", "FORGE", "CRUCIBLE")
FIELDS: Final = ("status", "phase", "progress", "pending")


def section(text: str, heading: str) -> str:
    return text.split(heading + "\n", 1)[1].split("\n## ", 1)[0].strip()


def digest(text: str, instrument: str) -> list[str]:
    """The four labelled bullets of one instrument section, past its plain-words intro."""
    lines = section(text, f"## {instrument}").splitlines()
    return lines[2:6]


def test_section_order_is_exact(tmp_path: Path) -> None:
    # Given a populated parent.
    fixture = parent_fixture(tmp_path)
    # When the dashboard is rendered.
    text = dashboard.render_tracker(fixture.root)
    # Then the public heading contract and opening structure are exact.
    assert tuple(re.findall(r"^## .+$", text, re.MULTILINE)) == EXPECTED_HEADINGS
    assert dashboard.HEADINGS == EXPECTED_HEADINGS
    assert text.startswith(f"# TRACKING.md\n\n> **{reports.GENERATED_BANNER}**\n")
    assert text.count(reports.GENERATED_BANNER) == 1
    assert "\n\nAs of " in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_zero_run_parent_renders_every_section(tmp_path: Path) -> None:
    # Given a parent with no recorded activity.
    fixture = parent_fixture(tmp_path, zero_runs=True)
    # When rendered.
    text = dashboard.render_tracker(fixture.root)
    # Then all sections remain, and only the empty pie/gantt are omitted.
    assert tuple(re.findall(r"^## .+$", text, re.MULTILINE)) == EXPECTED_HEADINGS
    assert "As of no recorded activity;" in text
    assert "pie showData" not in text and "gantt" not in text
    assert "bar [0, 0, 0, 0, 0]" in text
    assert "`" + "░" * 30 + "`" in text
    assert len(section(text, "## History").splitlines()) == 4
    assert section(text, "## Headline").count("no run") == 5
    # Then the three instrument sections are identical in shape and say "no run" the same way.
    assert all(
        digest(text, name) == [f"- {field}: no run" for field in FIELDS] for name in INSTRUMENTS
    )


def test_research_and_engineering_lanes_render_before_any_operations_run(tmp_path: Path) -> None:
    # Given no operations runs, but a published epoch and known harness revision.
    fixture = parent_fixture(tmp_path, zero_runs=True)
    snapshot = replace(
        load_snapshot(fixture.root),
        current_epoch=2,
        harness_revision="a" * 40,
        epochs=(EpochRecord(2, "2026-09-17T12:00:00Z", "research-owner", 0),),
    )
    # When rendered.
    lanes = section(dashboard.render_dashboard(snapshot), "## Organizational lanes")
    # Then independent lanes are visible without inventing an operations sign-off.
    assert "| Research | epoch 2" in lanes and "research-owner" in lanes
    assert "| Engineering | harness gitlink aaaaaaaaaaaa" in lanes
    assert "| Operations | no run | unknown |" in lanes


def test_history_inserts_a_late_arriving_run_in_order(tmp_path: Path) -> None:
    # Given a run created last with an earlier start time.
    fixture = parent_fixture(tmp_path, late_run=True)
    # When the history is regenerated.
    rows = dashboard.history_rows(load_snapshot(fixture.root))
    # Then history inserts chronologically rather than appending the arrival.
    assert "engram-fixture-late-run" in rows[2]
    assert [r.split(" | ")[0] for r in rows[2:]] == sorted(r.split(" | ")[0] for r in rows[2:])
    assert len(rows) == len(fixture.runs) + 2


def test_occupancy_and_placements_are_separate_rows(tmp_path: Path) -> None:
    # Given an anchor graduated to delivery.
    fixture = parent_fixture(tmp_path, graduated_anchor=True)
    # When rendered.
    body = section(dashboard.render_tracker(fixture.root), "## Samples occupancy")
    # Then graduation frees occupancy without losing the placement.
    assert "occupancy: 1 of 30 (3%)" in body.splitlines()
    assert "cumulative placements: 2" in body.splitlines()
    assert "`" + "█" + "░" * 29 + "`" in body


def test_malformed_card_renders_closure_unknown(tmp_path: Path) -> None:
    # Given an unreadable CRUCIBLE close card.
    fixture = parent_fixture(tmp_path, malformed_card=True)
    # When rendered.
    body = section(dashboard.render_tracker(fixture.root), "## CRUCIBLE")
    # Then neither a close instant nor an elapsed duration is invented.
    assert "| unknown | unknown | BLOCK:INVALID_TASK | Phase 2 | closure unknown |" in body


def test_gantt_disables_today_marker(tmp_path: Path) -> None:
    # Given recorded runs that close on their starting dates.
    fixture = parent_fixture(tmp_path)
    # When rendered.
    body = section(dashboard.render_tracker(fixture.root), "## Cycle timeline")
    # Then dates are stable and zero-length bars use Mermaid's one-day duration.
    assert "todayMarker off" in body
    assert "dateFormat YYYY-MM-DD" in body and "axisFormat %Y-%m-%d" in body
    assert body.count(", 1d") == 3


def test_labels_escape_colons_and_quotes(tmp_path: Path) -> None:
    # Given a live gate label with Mermaid syntax characters.
    fixture = parent_fixture(tmp_path, malformed_card=True)
    (fixture.runs[-1].directory / "progress.yaml").write_text(
        'phase: Phase 2\nopen_gates: [ask:"yes"#1]\n', encoding="utf-8"
    )
    # When rendered.
    body = section(dashboard.render_tracker(fixture.root), "## Decisions needed")
    # Then the label is quoted and escaped once, not interpreted as chart syntax.
    assert '"ask#58;#quot;yes#quot;#35;1 CRUCIBLE"' in body


def test_ratios_carry_both_counts(tmp_path: Path) -> None:
    # Given three runs with half their phases and gates complete.
    fixture = parent_fixture(tmp_path)
    # When rendered.
    text = dashboard.render_tracker(fixture.root)
    # Then each percentage is attached to both counts.
    assert text.count("phases 3 of 6 (50%), gates 1 of 2 (50%)") == 3
    percentages = re.findall(r"\d+%", text)
    assert len(re.findall(r"\d+ of \d+ \(\d+%\)", text)) == len(percentages)


def test_render_is_deterministic(tmp_path: Path) -> None:
    # Given cached and uncached inventories of identical evidence.
    fixture = parent_fixture(tmp_path / "parent", late_run=True, graduated_anchor=True)
    snapshot = load_snapshot(fixture.root)
    cached = load_snapshot(fixture.root, cache=tmp_path / "cache")
    warm = load_snapshot(fixture.root, cache=tmp_path / "cache")
    # When all snapshots are rendered.
    outputs = [dashboard.render_dashboard(s) for s in (snapshot, snapshot, cached, warm)]
    # Then cache metadata and repeated execution cannot affect output bytes.
    assert len(set(outputs)) == 1
    assert warm.parsed_runs == 0


def test_instrument_digest_aggregates_every_run_of_its_instrument(tmp_path: Path) -> None:
    # Given two ENGRAM runs and one run each for the other two instruments.
    fixture = parent_fixture(tmp_path, late_run=True)
    # When the dashboard renders those runs.
    text = dashboard.render_tracker(fixture.root)
    # Then each section opens with the four-line digest summed over its own runs alone.
    assert digest(text, "ENGRAM") == [
        "- status: SHIP_ELIGIBLE (every local check passed, release still needs a signed "
        "disposition)",
        "- phase: Phase 2",
        "- progress: phases 6 of 12 (50%), gates 2 of 4 (50%)",
        "- pending: 2 open gates (design, design), 2 gaps",
    ]
    assert digest(text, "FORGE") == [
        "- status: HOLD:PILOT_REQUIRED (waiting for an outside signed test run)",
        "- phase: Phase 2",
        "- progress: phases 3 of 6 (50%), gates 1 of 2 (50%)",
        "- pending: 1 open gate (design), 1 gap",
    ]
    assert digest(text, "CRUCIBLE")[0].startswith("- status: BLOCK:INVALID_TASK (")
    # Then every instrument section carries the same labels in the same order.
    for instrument in INSTRUMENTS:
        assert [line.split(":")[0] for line in digest(text, instrument)] == [
            f"- {field}" for field in FIELDS
        ]


def test_open_runs_and_chart_caps(tmp_path: Path) -> None:
    # Given thirteen live runs, all pending one gate.
    fixture = parent_fixture(tmp_path, zero_runs=True)
    for index in range(13):
        run = write_run(
            fixture.root,
            "FORGE",
            f"forge-live-run-{index:02d}",
            principal="author",
            started_at="2026-09-01T12:00:00Z",
            disposition="HOLD",
            malformed_card=False,
        )
        (run.directory / "tracker.json").unlink()
    snapshot = replace(load_snapshot(fixture.root), as_of="2026-09-17T12:00:00Z")
    # When rendered.
    text = dashboard.render_dashboard(snapshot)
    # Then open ages, bounds and active bars reflect the recorded instant.
    assert "and 1 more open runs" in section(text, "## Aging work")
    assert section(text, "## Aging work").count("| 16 |") == 12
    assert "bar [" + ", ".join(["16"] * 10) + "]" in text
    assert section(text, "## Cycle timeline").count(":active,") == 13


def test_boundary_and_overlapping_operations(tmp_path: Path) -> None:
    # Given a previous epoch and overlapping FORGE/CRUCIBLE intervals.
    fixture = parent_fixture(tmp_path)
    snapshot = load_snapshot(fixture.root)
    snapshot = replace(
        snapshot,
        boundary="epoch-1",
        current_epoch=2,
        runs=tuple(replace(r, closed_at="2026-09-17T16:00:00Z") for r in snapshot.runs),
    )
    # When rendered.
    text = dashboard.render_dashboard(snapshot)
    # Then boundary comparisons are strictly after, and overlaps are concurrent.
    assert "Boundary: epoch-1" in text
    assert "| runs started after | 2 |" in text
    assert "concurrent" in section(text, "## Organizational lanes")


def test_plain_text_cells_only_replace_pipes_and_newlines(tmp_path: Path) -> None:
    # Given an identity with markup, a link, a line break and an emoji shortcode.
    fixture = parent_fixture(tmp_path)
    snapshot = load_snapshot(fixture.root)
    injected = "<b>[owner](https://example.test)</b>\n| :smile: ` █"
    snapshot = replace(snapshot, runs=(replace(snapshot.runs[0], principal=injected),))
    # When rendered.
    text = dashboard.render_dashboard(snapshot)
    # Then cell separators and newlines are sanitized, but all other text stays raw.
    assert injected.replace("\n", " ").replace("|", "/") in section(text, "## History")
    assert "&#" not in text


def test_tables_carry_raw_timestamps_without_entities(tmp_path: Path) -> None:
    # Given persisted run timestamps and disposition tokens.
    fixture = parent_fixture(tmp_path)
    # When rendered.
    text = dashboard.render_tracker(fixture.root)
    # Then Markdown tables retain raw timestamps without entity encodings.
    assert "&#" not in text
    assert "| 2026-09-17T12:00:00Z |" in section(text, "## History")
    assert "| HOLD:PILOT_REQUIRED |" in section(text, "## FORGE")


def test_gantt_and_pie_titles_are_unquoted(tmp_path: Path) -> None:
    # Given a populated parent and a title carrying Mermaid punctuation.
    snapshot = load_snapshot(parent_fixture(tmp_path, late_run=True).root)
    snapshot = replace(
        snapshot, runs=(replace(snapshot.runs[0], run_id='run:"quoted"#1'), *snapshot.runs[1:])
    )
    # When rendered.
    text = dashboard.render_dashboard(snapshot)
    # Then free-text syntax stays unquoted while literal punctuation is escaped.
    gantt = section(text, "## Cycle timeline")
    assert "    section ENGRAM\n" in gantt
    assert "    engram-fixture-run-01 :done, r1," in gantt
    assert "    run#58;#quot;quoted#quot;#35;1 :done, r0," in gantt
    assert '"' not in gantt
    assert "    title Dispositions\n" in section(text, "## Disposition board")
    assert 'RES0["' in section(text, "## Organizational lanes")


def test_decision_categories_are_distinct_and_bounded(tmp_path: Path) -> None:
    # Given repeated gates, including names that collide after truncation.
    snapshot = load_snapshot(parent_fixture(tmp_path, late_run=True).root)
    gates = ("design", "long-gate-name-sharing-a-prefix-one", "long-gate-name-sharing-a-prefix-two")
    snapshot = replace(snapshot, runs=tuple(replace(r, open_gates=gates) for r in snapshot.runs))
    # When the decision chart is rendered.
    body = section(dashboard.render_dashboard(snapshot), "## Decisions needed")
    axis = next(line for line in body.splitlines() if "x-axis" in line)
    labels = re.findall(r'"([^"]*)"', axis)
    # Then labels identify the instrument, remain distinct and obey both limits.
    assert "design CRUCIBLE" in labels and "design ENGRAM" in labels
    assert len(labels) == len(set(labels)) == 10
    assert all(len(label) <= 24 for label in labels)


def test_digest_preserves_existing_run_order_for_tied_dispositions(tmp_path: Path) -> None:
    # Given lexical run order opposite chronological order, with distinct HOLD reasons.
    fixture = parent_fixture(tmp_path, zero_runs=True)
    for name, stamp, disposition in (
        ("alpha", "2026-09-17T12:00:00Z", "HOLD:ALPHA"),
        ("bravo", "2026-09-16T12:00:00Z", "HOLD:BRAVO"),
    ):
        write_run(
            fixture.root,
            "FORGE",
            f"forge-{name}-run",
            principal="author",
            started_at=stamp,
            disposition=disposition,
            malformed_card=False,
        )
    # When the renderer projects that evidence.
    text = dashboard.render_tracker(fixture.root)
    # Then the digest breaks the tie lexically while history stays chronological.
    assert digest(text, "FORGE")[0] == "- status: HOLD:ALPHA (alpha)"
    assert [row.split(" | ")[2] for row in section(text, "## History").splitlines()[4:]] == [
        "forge-bravo-run",
        "forge-alpha-run",
    ]


def test_backward_closure_renders_unknown_elapsed() -> None:
    # Given a card whose closed_at precedes started_at (clock skew or a hand-supplied instant)
    run = RunRecord(
        instrument="FORGE",
        run_id="forge-skew-1",
        principal="ada",
        started_at="2026-09-20T07:00:00Z",
        disposition="HOLD",
        phase="Phase 2",
        phases_done=1,
        phases_total=2,
        gates_done=0,
        gates_total=1,
        open_gates=(),
        gap_count=0,
        closed_at="2026-09-19T15:00:00Z",
        closure="closed",
        has_escalations=False,
    )
    # Then the elapsed value is unknown rather than a negative interval.
    assert elapsed(run) == "unknown"
