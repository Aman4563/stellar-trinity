"""Root reports and the executive tracker rendered from per-run reports.

Under many concurrent runners every instrument run writes only its own
``<harness>/runs/<run>/report.md``. The root reports ``DIRECTIVE.md``, ``EDICT.md``,
``VERDICT.md`` and the tracker ``TRACKING.md`` are pure functions of those run reports,
rendered at the merge by ``pipeline.py reconcile`` and never hand-edited, so two
runners never conflict on a shared file and a root report never becomes a channel
between instruments. The root ``## Disposition`` is the worst run disposition and is
never ``SHIP``: a release is signed against a frozen candidate, not aggregated.

``tools.dashboard`` owns every tracker byte, so this module only asks it for them. Every
report including the tracker is compared exactly, with no exempt line, and a parent-shaped
tree renders its dashboard even before its first run while a bare directory renders nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import runs
    from tools._findings import Finding, Severity
else:
    try:
        from tools import runs
        from tools._findings import Finding, Severity
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        import runs
        from _findings import Finding, Severity

GENERATED_BANNER: Final = "GENERATED SECTION. DO NOT HAND-EDIT."
REPORT_SECTIONS: Final = (
    "Executive summary",
    "Disposition",
    "Findings",
    "Coverage gaps",
    "Escalations",
    "Flag legend",
)
ROOT_REPORTS: Final[dict[str, str]] = {
    "ENGRAM": "DIRECTIVE.md",
    "FORGE": "EDICT.md",
    "CRUCIBLE": "VERDICT.md",
}
TRACKER: Final = "TRACKING.md"
SAMPLE_CEILING: Final = 30
RANK: Final[dict[str, int]] = {"BLOCK": 0, "HOLD": 1, "SHIP_ELIGIBLE": 2, "SHIP": 2}
FLAG_LEGEND: Final = (
    "| Flag | Meaning |\n"
    "| --- | --- |\n"
    "| SHIP_ELIGIBLE | every gate passed; release still needs the signed disposition |\n"
    "| HOLD | a named gate or gap is open |\n"
    "| BLOCK | a refusal that no later work lifts without a new candidate |"
)
_H2 = re.compile(r"^## (.+?)\s*$")
_PROGRESS_LINE = re.compile(r"^([a-z_]+):\s*(.*?)\s*$")


@dataclass(frozen=True, slots=True)
class RunSummary:
    instrument: str
    run_id: str
    principal: str
    started_at: str
    disposition: str
    phase: str
    phases_done: int
    phases_total: int
    gates_done: int
    gates_total: int
    open_gates: tuple[str, ...]
    gaps: int
    sections: dict[str, str]


def _sections(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        match = _H2.match(line)
        if match:
            if current is not None:
                out[current] = "\n".join(body).strip()
            current, body = match[1], []
        elif current is not None:
            body.append(line)
    if current is not None:
        out[current] = "\n".join(body).strip()
    return out


def _int(value: str) -> int:
    try:
        return max(int(value), 0)
    except ValueError:
        return 0


def _progress(directory: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    try:
        lines = (directory / "progress.yaml").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return fields
    for line in lines:
        match = _PROGRESS_LINE.fullmatch(line)
        if match:
            fields[match[1]] = match[2]
    return fields


def _disposition(sections: dict[str, str]) -> str:
    stated = sections.get("Disposition", "").splitlines()
    token = stated[0].strip() if stated else "HOLD"
    token = re.sub(r"[^A-Z_:]", "", token.split()[0]) if token.split() else "HOLD"
    if token.startswith("SHIP"):
        return "SHIP_ELIGIBLE"
    return token or "HOLD"


def _summaries(root: Path, instrument: str) -> list[RunSummary]:
    out: list[RunSummary] = []
    for run in runs.list_runs(root, instrument):
        directory = runs.run_dir(root, instrument, run.run_id)
        try:
            text = (directory / "report.md").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        sections = _sections(text)
        progress = _progress(directory)
        gates = progress.get("open_gates", "").strip("[] ")
        out.append(
            RunSummary(
                instrument=instrument,
                run_id=run.run_id,
                principal=run.principal,
                started_at=run.started_at,
                disposition=_disposition(sections),
                phase=progress.get("phase", "unknown"),
                phases_done=_int(progress.get("phases_done", "0")),
                phases_total=_int(progress.get("phases_total", "0")),
                gates_done=_int(progress.get("gates_done", "0")),
                gates_total=_int(progress.get("gates_total", "0")),
                open_gates=tuple(g.strip() for g in gates.split(",") if g.strip()),
                gaps=_int(progress.get("gaps", "0")),
                sections=sections,
            )
        )
    return out


def _worst(summaries: list[RunSummary]) -> str:
    ranked = sorted(summaries, key=lambda item: RANK.get(item.disposition.split(":")[0], 1))
    return ranked[0].disposition if ranked else "HOLD"


def _ratio(done: int, total: int) -> str:
    percent = int(done * 100 / total) if total else 0
    return f"{done} of {total} ({percent}%)"


def render_root_report(instrument: str, summaries: list[RunSummary]) -> str:
    harness = runs.HARNESS[instrument]
    lines = [GENERATED_BANNER, "", f"# {ROOT_REPORTS[instrument]}", ""]
    lines += ["## Executive summary", ""]
    lines += ["| run | principal | disposition | phase |", "| --- | --- | --- | --- |"]
    for item in summaries:
        lines.append(
            f"| `{harness}/runs/{item.run_id}/report.md` | {item.principal} | "
            f"{item.disposition} | {item.phase} |"
        )
    lines += ["", "## Disposition", "", _worst(summaries), ""]
    for name in ("Findings", "Coverage gaps", "Escalations"):
        lines += [f"## {name}", ""]
        for item in summaries:
            body = item.sections.get(name, "").strip() or "none recorded"
            lines += [f"### {item.run_id}", "", body, ""]
    lines += ["## Flag legend", "", FLAG_LEGEND, ""]
    return "\n".join(lines)


def render_tracker(root: Path, *, persist: bool = True) -> str:
    """The founder dashboard, whose every byte ``tools.dashboard`` owns."""
    if TYPE_CHECKING:
        from tools import dashboard, tracker_cache, tracker_snapshot  # noqa: PLC0415
    else:
        try:
            from tools import dashboard, tracker_cache, tracker_snapshot  # noqa: PLC0415
        except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
            import dashboard  # noqa: PLC0415
            import tracker_cache  # noqa: PLC0415
            import tracker_snapshot  # noqa: PLC0415

    return dashboard.render_dashboard(
        tracker_snapshot.load_snapshot(
            root, cache=tracker_cache.cache_location(root, persist=persist), persist=persist
        )
    )


def is_parent(root: Path) -> bool:
    """A tree the dashboard belongs in: an instrument harness, or a tracker already there."""
    return (
        any((root / runs.HARNESS[name]).is_dir() for name in ROOT_REPORTS)
        or (root / TRACKER).exists()
    )


def rendered_root_reports(root: Path, *, persist: bool = False) -> dict[str, str]:
    """Every root report the tree on disk determines, keyed by root file name."""
    out: dict[str, str] = {}
    for instrument, name in ROOT_REPORTS.items():
        summaries = _summaries(root, instrument)
        if summaries:
            out[name] = render_root_report(instrument, summaries)
    if is_parent(root):
        out[TRACKER] = render_tracker(root, persist=persist)
    return out


def _differs(path: Path, rendered: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") != rendered
    except (OSError, UnicodeDecodeError):
        return True


def render_root_reports(root: Path) -> list[str]:
    """Write every root report that differs from its rendering; return the names written."""
    written: list[str] = []
    for name, rendered in rendered_root_reports(root, persist=True).items():
        path = root / name
        if _differs(path, rendered):
            path.write_text(rendered, encoding="utf-8")
            written.append(name)
    return written


def check_root_reports(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """A root report must equal its rendering, and every tracker card must be readable."""
    if TYPE_CHECKING:
        from tools import tracker  # noqa: PLC0415 - tracker imports reports
    else:
        try:
            from tools import tracker  # noqa: PLC0415 - tracker imports reports
        except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
            import tracker  # noqa: PLC0415

    root_path = Path(root)
    out: list[Finding] = []
    for name, rendered in rendered_root_reports(root_path, persist=False).items():
        if _differs(root_path / name, rendered):
            out.append(
                Finding(
                    "REPORT_NOT_RENDERED",
                    Severity.ERROR,
                    str(root_path / name),
                    None,
                    f"{name} is not rendered from its run reports",
                )
            )
    return out + tracker.check_tracker_cards(root)
