"""The frozen closure card one run contributes to the founder dashboard.

A run's card at ``<harness>/runs/<run_id>/tracker.json`` states the closure the dashboard
reads instead of re-deriving every run's state on every render. Every field is derived from
the run's own validated inputs and none is supplied: the card binds run identity together
with the SHA-256 of ``run.json``, ``report.md``, and ``progress.yaml``, so a card is a
statement about exactly those bytes. Closure is terminal, so ``closed_at`` is write-once. A
second emission over identical bytes changes nothing, and a second emission over changed
bytes is a refusal a human resolves by opening a new run, never a rewrite this tool
performs. ``check_tracker_cards`` names a card the renderer cannot read as an error, so it
reports closure as unknown instead of guessing silently, and names a card whose run lawfully
continued after closure, so that only ``report.md`` or ``progress.yaml`` moved while
``run.json`` still binds, as the advisory ``TRACKER_CARD_SUPERSEDED``: the card stays an
honest statement about what was true at ``closed_at`` and never blocks a push.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import runs, tracker_card
    from tools._findings import Finding, Severity
    from tools.project_paths import display_project_path, invocation_root, resolve_project_path
    from tools.reports import _disposition, _int, _progress, _sections
else:
    try:
        from tools import runs, tracker_card
        from tools._findings import Finding, Severity
        from tools.project_paths import display_project_path, invocation_root, resolve_project_path
        from tools.reports import _disposition, _int, _progress, _sections
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        import runs
        import tracker_card
        from _findings import Finding, Severity
        from project_paths import display_project_path, invocation_root, resolve_project_path
        from reports import _disposition, _int, _progress, _sections

SCHEMA: Final = tracker_card.SCHEMA
CARD_NAME: Final = "tracker.json"
PARSER_VERSION: Final = tracker_card.PARSER_VERSION
SOURCE_NAMES: Final = tracker_card.SOURCE_NAMES
COUNT_NAMES: Final = tracker_card.COUNT_NAMES
CARD_KEYS: Final = tracker_card.CARD_KEYS
CONFLICT: Final = "TRACKER_CARD_CONFLICT"
INPUT_MISSING: Final = tracker_card.INPUT_MISSING
IDENTITY_MISMATCH: Final = tracker_card.IDENTITY_MISMATCH
MALFORMED: Final = tracker_card.MALFORMED
SUPERSEDED: Final = tracker_card.SUPERSEDED
EXIT_CLEAN: Final = 0
EXIT_USAGE: Final = 1
EXIT_REFUSED: Final = 3
_INSTANT: Final = tracker_card.INSTANT
_STAMP: Final = tracker_card.STAMP
_UNPROVABLE: Final = tracker_card.Refusal(
    MALFORMED, "the run namespace carries no readable run.json, so card identity is unprovable"
)


class TrackerError(ValueError):
    """A card refusal with a closed public code."""

    code: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Target:
    """One run namespace: the parent root, the instrument that owns it, and the run id."""

    root: Path
    instrument: str
    run_id: str

    def __post_init__(self) -> None:
        if self.instrument not in runs.HARNESS:
            raise TrackerError(IDENTITY_MISMATCH, f"{self.instrument} owns no run namespace")


def card_path(target: Target) -> Path:
    """Where the card lives; pure path math that never checks run ownership."""
    harness = runs.HARNESS[target.instrument]
    return target.root / harness / runs.RUNS_DIR / target.run_id / CARD_NAME


def _namespace(target: Target) -> Path:
    try:
        return runs.run_dir(target.root, target.instrument, target.run_id)
    except runs.RunError as exc:
        raise TrackerError(IDENTITY_MISMATCH, str(exc)) from exc


def _source_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TrackerError(INPUT_MISSING, f"{path.name} is absent or unreadable") from exc


def _report_text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TrackerError(INPUT_MISSING, "report.md is not valid UTF-8") from exc


def _identity(directory: Path, target: Target) -> runs.Run:
    """The ownership ``run.json`` binds to this namespace, parsed by ``runs`` alone."""
    run = runs._read_run(directory / "run.json")
    if run is None:
        raise TrackerError(INPUT_MISSING, "run.json is absent, unreadable, or not a run record")
    if run.instrument != target.instrument or run.run_id != target.run_id:
        raise TrackerError(IDENTITY_MISMATCH, f"run.json names {run.instrument} run {run.run_id}")
    return run


def _derive(target: Target, run: runs.Run, directory: Path) -> dict[str, object]:
    """Every card field except the write-once ``closed_at``."""
    source = {name: _source_bytes(directory / name) for name in SOURCE_NAMES}
    progress = _progress(directory)
    gates = progress.get("open_gates", "").strip("[] ")
    return {
        "schema": SCHEMA,
        "instrument": target.instrument,
        "run_id": target.run_id,
        "principal": run.principal,
        "started_at": run.started_at,
        "disposition": _disposition(_sections(_report_text(source["report.md"]))),
        "phase": progress.get("phase") or "unknown",
        "open_gates": sorted(item.strip() for item in gates.split(",") if item.strip()),
        "sources": {name: hashlib.sha256(source[name]).hexdigest() for name in SOURCE_NAMES},
        "parser_version": PARSER_VERSION,
        **{name: _int(progress.get(name, "0")) for name in COUNT_NAMES},
    }


def _read_card(path: Path, run: runs.Run) -> dict[str, object] | tracker_card.Refusal:
    """The card on disk, or the one refusal that says why it is not a trusted ``v1`` statement."""
    return tracker_card.read_card(path, run)


def _atomic_write(path: Path, body: str) -> None:
    handle, name = tempfile.mkstemp(dir=str(path.parent), prefix=".tracker-", suffix=".json")
    scratch = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(body)
        scratch.chmod(0o644)
        scratch.replace(path)
    except OSError:
        scratch.unlink(missing_ok=True)
        raise


def write_card(target: Target, *, closed_at: str | None = None) -> bool:
    """Freeze this run's closure once. True when bytes were written, False when unchanged."""
    directory = _namespace(target)
    run = _identity(directory, target)
    path = card_path(target)
    if os.path.lexists(path):
        frozen = _read_card(path, run)
        if isinstance(frozen, tracker_card.Refusal):
            code = CONFLICT if frozen.code in (SUPERSEDED, MALFORMED) else frozen.code
            raise TrackerError(code, f"{frozen.reason}, and a frozen card is never repaired")
        derived = _derive(target, run, directory)
        if {**derived, "closed_at": frozen["closed_at"]} != frozen:
            raise TrackerError(CONFLICT, f"{CARD_NAME} was frozen over different bytes")
        return False
    derived = _derive(target, run, directory)
    derived["closed_at"] = closed_at or datetime.now(UTC).strftime(_STAMP)
    _atomic_write(path, json.dumps(derived, sort_keys=True, indent=2, ensure_ascii=True) + "\n")
    return True


def _finding(path: Path, root: Path, refusal: tracker_card.Refusal) -> Finding:
    display = display_project_path(path, project_root=root)
    if refusal.code == SUPERSEDED:
        return Finding(SUPERSEDED, Severity.ADVISORY, display, None, refusal.reason)
    code = MALFORMED if refusal.code == IDENTITY_MISMATCH else refusal.code
    return Finding(code, Severity.ERROR, display, None, refusal.reason)


def check_tracker_cards(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """A tracker card the dashboard cannot read is named, never repaired."""
    root_path = Path(root)
    out: list[Finding] = []
    for instrument in sorted(runs.HARNESS):
        base = root_path / runs.HARNESS[instrument] / runs.RUNS_DIR
        if not base.is_dir():
            continue
        owned = {run.run_id: run for run in runs.list_runs(root_path, instrument)}
        for directory in sorted(base.iterdir()):
            path = directory / CARD_NAME
            if not os.path.lexists(path):
                continue
            run = owned.get(directory.name)
            card = _UNPROVABLE if run is None else _read_card(path, run)
            if isinstance(card, tracker_card.Refusal):
                out.append(_finding(path, root_path, card))
    return out


def _closed_at(value: str | None) -> str | None:
    if value is None:
        return None
    if _INSTANT.fullmatch(value) is None:
        raise ValueError("--closed-at must be YYYY-MM-DDTHH:MM:SSZ")
    datetime.strptime(value, _STAMP).replace(tzinfo=UTC)
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 tools/tracker.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    card = sub.add_parser("card", help="freeze this run's closure card, once")
    card.add_argument("root")
    card.add_argument("--instrument", required=True, choices=sorted(runs.HARNESS))
    card.add_argument("--run-id", required=True)
    card.add_argument("--closed-at", help="closure instant as YYYY-MM-DDTHH:MM:SSZ")
    card.add_argument("--json", action="store_true", dest="as_json", help="print one JSON object")
    return parser


def main(argv: list[str]) -> int:
    arguments = _parser().parse_args(argv[1:])
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            str(arguments.root),
            project_root=project_root,
            description="parent root",
            must_exist=True,
        )
        closed_at = _closed_at(arguments.closed_at)
        target = Target(root, str(arguments.instrument), str(arguments.run_id))
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    display = display_project_path(card_path(target), project_root=project_root)
    try:
        written = write_card(target, closed_at=closed_at)
    except TrackerError as exc:
        if arguments.as_json:
            print(json.dumps({"code": exc.code, "path": display, "written": False}, sort_keys=True))
        else:
            print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    if arguments.as_json:
        print(json.dumps({"path": display, "written": written}, sort_keys=True))
    else:
        print(f"{'wrote' if written else 'unchanged'} {display}")
    return EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
