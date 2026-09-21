"""Deterministic TRACKING.md rendering from a recorded-activity snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from tools import dashboard_sections as sections
from tools import reports
from tools.dashboard_charts import (
    BASES,
    INSTRUMENTS,
    REASONS,
    closure,
    counted_bars,
    elapsed,
    explain,
    occupancy,
    plain,
    table,
    timeline,
    worst,
)
from tools.tracker_snapshot import Snapshot, cache_location, load_snapshot

HEADINGS: Final[tuple[str, ...]] = (
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
BANNER: Final[tuple[str, ...]] = (
    f"> **{reports.GENERATED_BANNER}**",
    ">",
    "> Every byte below is rendered by `trinity/tools/pipeline.py render-reports` from the run "
    "reports and per-run tracker cards already on disk. Anything typed into this file is erased "
    "by the next render, so change the work this page reports rather than the page.",
)
ORIENTATION: Final = (
    "Three instruments do the work. ENGRAM remembers what earlier tasks cost and tells the other "
    "two where to aim, FORGE writes new tasks, and CRUCIBLE inspects finished tasks for defects. "
    "A run is one sitting of one instrument. A gate is a stop that waits for a person to sign. A "
    "gap is required work that nothing has covered yet. Every section below counts runs, gates, "
    "and gaps and charts what it counts, and the last section gives the plain meaning of every "
    "status word on this page."
)
TIMELINE_INTRO: Final = (
    "When each run started and finished, one lane per instrument. A bar that never closes is a "
    "run still waiting."
)
OCCUPANCY_INTRO: Final = (
    "How full the public shelf is. It holds thirty tasks at a time, and a starter task leaves the "
    "shelf once it has taught the project what its techniques cost."
)
HISTORY_INTRO: Final = (
    "Every run ever recorded, in the order it started. A run that arrives late is inserted in "
    "order rather than appended."
)
INTRO: Final[dict[str, str]] = {
    "ENGRAM": "ENGRAM is the memory. It remembers what earlier tasks cost, expires evidence that "
    "has gone stale, and is the only instrument that talks to the other two.",
    "FORGE": "FORGE is the author. It writes new tasks in batches, proves each one against its "
    "own checks, and hands the sealed batch on to be inspected.",
    "CRUCIBLE": "CRUCIBLE is the inspector. It audits finished work against recorded evidence and "
    "never sees the difficulty targets FORGE was aiming at.",
}


def _count(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _instrument(snapshot: Snapshot, instrument: str) -> list[str]:
    items = sorted((r for r in snapshot.runs if r.instrument == instrument), key=lambda r: r.run_id)
    gates = [gate for r in items for gate in r.open_gates]
    names = f" ({', '.join(gates)})" if gates else ""
    gaps = sum(r.gaps for r in items)
    phases_done, phases_total = (
        sum(r.phases_done for r in items),
        sum(r.phases_total for r in items),
    )
    gates_done, gates_total = sum(r.gates_done for r in items), sum(r.gates_total for r in items)
    digest = (
        [
            "- status: " + plain(explain(worst(items))),
            "- phase: " + plain("; ".join(sorted({r.phase for r in items}))),
            f"- progress: phases {reports._ratio(phases_done, phases_total)}, "
            f"gates {reports._ratio(gates_done, gates_total)}",
            "- pending: "
            + plain(f"{_count(len(gates), 'open gate')}{names}, {_count(gaps, 'gap')}"),
        ]
        if items
        else [f"- {name}: no run" for name in ("status", "phase", "progress", "pending")]
    )
    rows = [
        (
            r.run_id,
            r.principal,
            r.started_at,
            r.closed_at or "unknown",
            elapsed(r),
            r.disposition,
            r.phase,
            closure(r),
        )
        for r in items
    ]
    return [
        INTRO[instrument],
        "",
        *digest,
        *counted_bars(
            [
                ("phases done", phases_done),
                ("phases left", max(phases_total - phases_done, 0)),
                ("gates done", gates_done),
                ("gates left", max(gates_total - gates_done, 0)),
                ("open gates", len(gates)),
                ("gaps", gaps),
            ]
            if items
            else []
        ),
        "",
        *table(
            "run | principal | started | closed | run elapsed, including waits | "
            "disposition | phase | closure",
            rows or [("no run",) * 8],
        ),
    ]


GLOSSARY: Final[tuple[tuple[str, str], ...]] = (
    ("run", "one sitting of one instrument, from the moment it opens to the moment it closes"),
    ("gate", "a stop that waits for a person to sign before the work may continue"),
    ("gap", "required work that nothing has covered yet"),
    ("phase", "a numbered step inside a run"),
    ("bundle", "one finished task, packaged so it can be run by an outside grader"),
    ("staged", "written but not yet frozen"),
    ("sealed", "frozen, so its bytes can no longer change"),
    ("claimed", "picked up by the inspector"),
    ("audited", "inspected, with a verdict recorded"),
    ("placed", "moved onto the public shelf or into the private corpus"),
    ("epoch", "a published, frozen version of the memory"),
    ("escalation", "a problem a run raised for someone above it to settle"),
)


def legend_rows() -> list[str]:
    """The three outcome flags with their reasons, then the plain meaning of every term."""
    return [
        "The three outcomes any run can reach, worst first.",
        "",
        *table(
            "flag | plain meaning",
            [
                ("BLOCK", BASES["BLOCK"]),
                ("HOLD", BASES["HOLD"]),
                ("SHIP_ELIGIBLE", BASES["SHIP_ELIGIBLE"]),
            ],
        ),
        "",
        "A flag may carry a reason after a colon, such as `HOLD:PILOT_REQUIRED`. Every reason "
        "this page prints is spelled out in brackets beside the flag it qualifies.",
        "",
        *table("reason | plain meaning", sorted(REASONS.items())),
        "",
        "The words this page uses for the work itself.",
        "",
        *table("term | plain meaning", GLOSSARY),
    ]


def history_rows(snapshot: Snapshot) -> list[str]:
    """History table lines in recorded chronological order, including closure."""
    return table(
        "started | instrument | run | principal | disposition | phase | closed | closure",
        [
            (
                r.started_at,
                r.instrument,
                r.run_id,
                r.principal,
                r.disposition,
                r.phase,
                r.closed_at or "unknown",
                closure(r),
            )
            for r in sorted(snapshot.runs, key=lambda r: (r.started_at, r.instrument, r.run_id))
        ],
    )


def render_dashboard(snapshot: Snapshot) -> str:
    """Return plain Markdown; equal snapshots produce identical bytes without I/O."""
    as_of = (
        f"As of {snapshot.as_of} UTC, derived from recorded activity; every age and interval "
        "below is relative to that instant and no wall clock is read."
        if snapshot.as_of is not None
        else "As of no recorded activity; this parent has published no epoch, opened no run, "
        "and sealed no bundle."
    )
    bodies = [
        sections.headline(snapshot),
        sections.lanes(snapshot),
        sections.dispositions(snapshot),
        sections.decisions(snapshot),
        sections.changes(snapshot),
        [TIMELINE_INTRO, "", *timeline(snapshot)],
        sections.flow(snapshot),
        [OCCUPANCY_INTRO, "", *occupancy(snapshot)],
        sections.aging(snapshot),
        sections.blockers(snapshot),
        sections.signoffs(snapshot),
        *(_instrument(snapshot, name) for name in INSTRUMENTS),
        [HISTORY_INTRO, "", *history_rows(snapshot)],
        legend_rows(),
    ]
    lines = ["# TRACKING.md", "", *BANNER, "", as_of, "", ORIENTATION]
    for heading, body in zip(HEADINGS, bodies, strict=True):
        lines += ["", heading, "", *body]
    return "\n".join(lines) + "\n"


def render_tracker(root: Path) -> str:
    """Load the existing cached inventory and render it without changing evidence."""
    return render_dashboard(load_snapshot(root, cache=cache_location(root)))
