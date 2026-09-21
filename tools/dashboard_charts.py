"""Plain-text presentation primitives; no evidence access or clock reads."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Final, assert_never

from tools import reports
from tools.tracker_cache import RunRecord
from tools.tracker_snapshot import Snapshot

INSTRUMENTS: Final = ("ENGRAM", "FORGE", "CRUCIBLE")
CHART_LIMIT: Final = 10
LABEL_LIMIT: Final = 24
NO_RUN: Final = "no run"
BASES: Final[dict[str, str]] = {
    "SHIP": "released",
    "SHIP_ELIGIBLE": "every local check passed, release still needs a signed disposition",
    "HOLD": "waiting on a person or an open gap",
    "BLOCK": "refused until a new candidate is built",
}
REASONS: Final[dict[str, str]] = {
    "PILOT_REQUIRED": "waiting for an outside signed test run",
    "INVALID_TASK": "the task itself is malformed and has to be rebuilt",
    "INVALID_PILOT": "the test run cannot be proved against what was promised",
    "SUPPRESSED_MEASUREMENT": "a measurement was weakened or its coverage was never shown",
}


def plain(value: str) -> str:
    """Preserve raw Markdown text, replacing only cell separators and newlines."""
    return " ".join(value.splitlines()).replace("|", "/")


def row(values: Iterable[str | int]) -> str:
    return "| " + " | ".join(plain(str(value)) for value in values) + " |"


def table(columns: str, rows: Iterable[Sequence[str | int]]) -> list[str]:
    names = columns.split(" | ")
    return ["| " + columns + " |", row("---" for _ in names), *(row(r) for r in rows)]


def mermaid_text(value: str) -> str:
    text = " ".join(value.split())
    text = text.replace("#", "#35;").replace('"', "#quot;").replace(":", "#58;")
    return text.translate({ord(c): f"#{ord(c)};" for c in "<>`|[]\\█░"})


def label(value: str) -> str:
    return f'"{mermaid_text(value)}"'


def fence(lines: Iterable[str]) -> list[str]:
    return ["```mermaid", *lines, "```"]


def bars(values: Sequence[tuple[str, int]]) -> list[str]:
    selected = values[:CHART_LIMIT]
    if not selected:
        return []
    return fence(
        [
            "xychart-beta",
            "    x-axis [" + ", ".join(label(name) for name, _ in selected) + "]",
            f"    y-axis 0 --> {max(1, *(count for _, count in selected))}",
            "    bar [" + ", ".join(str(count) for _, count in selected) + "]",
        ]
    )


def counted_bars(values: Sequence[tuple[str, int]]) -> list[str]:
    """A bar chart under a blank line, or nothing when there is no count to draw."""
    drawn = bars(values)
    return ["", *drawn] if drawn else []


def age(started: str, as_of: str | None) -> int | None:
    if as_of is None or started == "unknown":
        return None
    return (datetime.fromisoformat(as_of) - datetime.fromisoformat(started)).days


def decision_labels(values: Sequence[tuple[str, int]]) -> list[tuple[str, int]]:
    """Bounded, de-duplicated chart categories; two runs never collapse into one bar."""
    selected: list[tuple[str, int]] = []
    used: set[str] = set()
    for name, days in values[:CHART_LIMIT]:
        base = " ".join(name.split())[:LABEL_LIMIT]
        category = base
        occurrence = 1
        while category in used:
            occurrence += 1
            suffix = f" {occurrence}"
            category = base[: LABEL_LIMIT - len(suffix)] + suffix
        used.add(category)
        selected.append((category, days))
    return selected


def decision_bars(values: Sequence[tuple[str, int]]) -> list[str]:
    return bars(decision_labels(values))


def worst(items: Sequence[RunRecord]) -> str:
    if not items:
        return NO_RUN
    return min(items, key=lambda r: reports.RANK.get(r.disposition.split(":")[0], 1)).disposition


def explain(token: str) -> str:
    """The token unchanged, followed by its plain meaning in brackets for a lay reader."""
    if token == NO_RUN:
        return token
    base, _, reason = token.partition(":")
    meaning = REASONS.get(reason, reason.lower().replace("_", " ")) if reason else BASES.get(base)
    return f"{token} ({meaning})" if meaning else token


def elapsed(run: RunRecord) -> str:
    match run.closure:
        case "open":
            return "open"
        case "unknown":
            return "unknown"
        case "closed":
            if run.closed_at is None or run.started_at == "unknown":
                return "unknown"
            delta = datetime.fromisoformat(run.closed_at) - datetime.fromisoformat(run.started_at)
            if delta.days < 0:
                return "unknown"
            minutes = delta.seconds // 60
            return f"{delta.days}d {minutes // 60:02d}:{minutes % 60:02d}"
        case unreachable:
            assert_never(unreachable)


def closure(run: RunRecord) -> str:
    match run.closure:
        case "unknown":
            return "closure unknown"
        case "closed" | "open":
            return run.closure
        case unreachable:
            assert_never(unreachable)


def timeline(snapshot: Snapshot) -> list[str]:
    if not snapshot.runs:
        return ["no run"]
    lines = ["gantt", "    dateFormat YYYY-MM-DD", "    axisFormat %Y-%m-%d", "    todayMarker off"]
    for instrument in INSTRUMENTS:
        members = [(i, r) for i, r in enumerate(snapshot.runs) if r.instrument == instrument]
        if not members:
            continue
        lines.append(f"    section {mermaid_text(instrument)}")
        for index, run in members:
            start = run.started_at[:10]
            match run.closure:
                case "closed":
                    tag, end = "done", (run.closed_at or "unknown")[:10]
                case "open":
                    tag, end = "active", (snapshot.as_of or "unknown")[:10]
                case "unknown":
                    tag, end = "milestone", "0d"
                case unreachable:
                    assert_never(unreachable)
            duration = "1d" if end == start else end
            lines.append(f"    {mermaid_text(run.run_id)} :{tag}, r{index}, {start}, {duration}")
    return fence(lines)


def occupancy(snapshot: Snapshot) -> list[str]:
    occupied = min(snapshot.samples_resident, reports.SAMPLE_CEILING)
    bar = "█" * occupied + "░" * (reports.SAMPLE_CEILING - occupied)
    placements = len({r.uuid for r in snapshot.residents})
    return [
        f"occupancy: {reports._ratio(snapshot.samples_resident, reports.SAMPLE_CEILING)}",
        "",
        f"`{bar}`",
        "",
        f"cumulative placements: {placements}",
        "",
        "Occupancy counts what is on the shelf right now rather than everything ever placed, so "
        "it can fall as well as rise: a starter task leaves the shelf once it has taught the "
        "project what its techniques cost, and the next task takes its place.",
    ]
