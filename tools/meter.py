#!/usr/bin/env python3
"""External consumption harness: fold an ``opencode export`` session tree into token totals.

This tool measures and never governs. It reads a session export, walks the ``parentID`` tree
from one named root or from every root, and emits ``trinity.meter/v1`` with, per session and
summed over the subtree, input tokens, output tokens, cache-read tokens, cache-write tokens,
a message count, the first and last instants the export recorded, and the wall-clock seconds
between them. Every instant comes from the export, so two runs over one export agree byte for
byte and a slow reader never inflates a lane's recorded duration. ``tools/meter_fold.py`` owns
the decoding and the fold; this module owns the paths, the refusals, and the envelope.

Per ``docs/adr/0005-run-lifecycle-closure.md`` decision 5, measurement never lands inside a
harness namespace. Nothing is written without ``--out``, and an ``--out`` resolving inside
``.memory/``, ``.seed/``, ``.audit/``, ``.trial/``, or ``.podium/`` is refused with
``METER_PATH_IN_HARNESS`` before anything is read, whether that path was authored relative to
the working directory or absolute, and whether or not a symbolic link leads there.

Usage:
  meter.py sessions --export FILE [--root SESSION] [--out FILE] [--json]

Exit codes:
  0  the fold was emitted
  1  usage, an unreadable input, or a path outside the project path rules
  3  a refusal: METER_EXPORT_UNRECOGNIZED or METER_PATH_IN_HARNESS
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools._bounded_json import Json
    from tools.meter_fold import Counts, Fold, MeterError, fold, read_export, roots_of
    from tools.project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
else:
    from _bounded_json import Json
    from meter_fold import Counts, Fold, MeterError, fold, read_export, roots_of
    from project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )

SCHEMA: Final = "trinity.meter/v1"
PATH_IN_HARNESS: Final = "METER_PATH_IN_HARNESS"
HARNESS_ROOTS: Final = frozenset({".memory", ".seed", ".audit", ".trial", ".podium"})
MILLISECONDS: Final = 1000
SECONDS_PLACES: Final = 3


def refuse_harness_path(value: str, *, project_root: Path) -> None:
    """Refuse a path resolving inside a harness namespace, named outright or through a link."""
    authored = Path(value)
    absolute = authored if authored.is_absolute() else project_root / authored
    for candidate in {Path(os.path.normpath(absolute)), Path(os.path.realpath(absolute))}:
        inside = sorted(HARNESS_ROOTS.intersection(candidate.parts))
        if inside:
            raise MeterError(
                PATH_IN_HARNESS,
                f"an output path inside {inside[0]}/ would let measurement alter the measured run",
            )


def _resolve(value: str, *, project_root: Path, description: str, must_exist: bool) -> Path:
    authored = value if value.startswith("./") or Path(value).is_absolute() else f"./{value}"
    return resolve_project_path(
        authored, project_root=project_root, description=description, must_exist=must_exist
    )


def _seconds(counts: Counts) -> float:
    if counts.first is None or counts.last is None:
        return 0.0
    return round((counts.last - counts.first) / MILLISECONDS, SECONDS_PLACES)


def _instant(value: int | None) -> str | None:
    if value is None:
        return None
    moment = datetime.fromtimestamp(value // MILLISECONDS, UTC)
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%S')}.{value % MILLISECONDS:03d}Z"


def _view(counts: Counts) -> dict[str, Json]:
    return {
        "input": counts.input_tokens,
        "output": counts.output_tokens,
        "cache_read": counts.cache_read,
        "cache_write": counts.cache_write,
        "messages": counts.messages,
        "first": _instant(counts.first),
        "last": _instant(counts.last),
        "wall_clock_seconds": _seconds(counts),
    }


def envelope(folded: Fold) -> dict[str, Json]:
    """Render one fold as the ``trinity.meter/v1`` document."""
    return {
        "schema": SCHEMA,
        "roots": list(folded.roots),
        "sessions": [
            {
                "session": entry.session_id,
                "parent": entry.parent,
                "depth": entry.depth,
                "self": _view(entry.own),
                "subtree": _view(entry.subtree),
            }
            for entry in folded.entries
        ],
        "totals": _view(folded.totals),
    }


def _render(folded: Fold) -> str:
    return "\n".join(
        f"{'  ' * entry.depth}{entry.session_id} in={entry.subtree.input_tokens} "
        f"out={entry.subtree.output_tokens} cache_read={entry.subtree.cache_read} "
        f"cache_write={entry.subtree.cache_write} messages={entry.subtree.messages} "
        f"seconds={_seconds(entry.subtree)}"
        for entry in folded.entries
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meter.py", description="fold a session export")
    commands = parser.add_subparsers(dest="command", required=True)
    sessions = commands.add_parser("sessions", help="fold one export into per-session totals")
    sessions.add_argument("--export", required=True, help="path to an opencode session export")
    sessions.add_argument("--root", help="fold only this session and its descendants")
    sessions.add_argument("--out", help="write the envelope here, outside every harness root")
    sessions.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _refused(exc: Exception, *, project_root: Path) -> None:
    print(f"refused: {redact_project_root(str(exc), project_root=project_root)}", file=sys.stderr)


def main(argv: list[str]) -> int:
    """Run the harness by path and return a process exit status."""
    arguments = _parser().parse_args(argv[1:])
    project_root = invocation_root()
    try:
        out: Path | None = None
        if arguments.out is not None:
            refuse_harness_path(arguments.out, project_root=project_root)
            out = _resolve(
                arguments.out, project_root=project_root, description="out", must_exist=False
            )
        export = _resolve(
            arguments.export, project_root=project_root, description="export", must_exist=True
        )
        sessions = read_export(export.read_bytes())
        folded = fold(sessions, roots_of(sessions, arguments.root))
    except MeterError as exc:
        _refused(exc, project_root=project_root)
        if arguments.as_json:
            print(json.dumps({"code": exc.code, "written": False}, sort_keys=True))
        return 3
    except (ProjectPathError, OSError, ValueError) as exc:
        _refused(exc, project_root=project_root)
        return 1
    body = json.dumps(envelope(folded), indent=2, sort_keys=True) + "\n"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        print(f"wrote {display_project_path(out, project_root=project_root)}", file=sys.stderr)
    sys.stdout.write(body if arguments.as_json else _render(folded) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
