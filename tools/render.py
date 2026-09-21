"""The augmentation backlog one run projects from its own capability block.

Every instrument regenerates ``<harness>/runs/<run_id>/TODO.md`` from
``<harness>/capabilities.yaml``, the ``bucket_d_status`` block ENGRAM alone carries, and the
coverage gaps the run recorded under ``## Coverage gaps`` in its own ``report.md``. Nothing is
authored: a field the source omits is reported unrecorded, and an absent block or report is named
absent rather than read as a project with nothing to do. ``subject.OUTPUT_NAMES`` excludes the
file, so a render moves no subject digest, ``--check`` proves the bytes on disk equal the
projection without writing one, and no instant is read, so two renders of one tree agree.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import reports, runs
    from tools._findings import Finding, Severity, render_finding, serialize_findings
    from tools.project_paths import display_project_path, invocation_root, resolve_project_path
else:
    try:
        from tools import reports, runs
        from tools._findings import Finding, Severity, render_finding, serialize_findings
        from tools.project_paths import display_project_path, invocation_root, resolve_project_path
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        import reports
        import runs
        from _findings import Finding, Severity, render_finding, serialize_findings
        from project_paths import display_project_path, invocation_root, resolve_project_path

TODO_NAME: Final = "TODO.md"
REPORT_NAME: Final = "report.md"
GAPS_SECTION: Final = "Coverage gaps"
BUCKET_D_INSTRUMENT: Final = "ENGRAM"
DECLARED: Final = "declared"
PROVEN: Final = "true"
DRIFT: Final = "TODO_DRIFT"
SOURCE_UNREADABLE: Final = "TODO_SOURCE_UNREADABLE"
EXIT_CLEAN: Final = 0
EXIT_USAGE: Final = 1
EXIT_DRIFT: Final = 2
EXIT_REFUSED: Final = 3
EMPTY_GAPS: Final = frozenset({"", "none", "none.", "none recorded", "none recorded."})
CONSEQUENCE: Final = "fail-closed consequence"
GAP_HEADINGS: Final = ("coverage gap",)
_COMMENT: Final = re.compile(r"\s*#.*")
_ROW: Final = re.compile(r"\s+-\s+([a-z_]+):\s*(.*?)\s*")
_FIELD: Final = re.compile(r"\s+([a-z_]+):\s*(.*?)\s*")


class RenderError(ValueError):
    """A backlog refusal with a closed public code."""

    code: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Target:
    """One run namespace and the principal claiming it."""

    root: Path
    instrument: str
    run_id: str
    principal: str


@dataclass(frozen=True, slots=True)
class Block:
    """One block of the capability file and the table its outstanding rows render as."""

    key: str
    title: str
    headings: tuple[str, ...]
    fields: tuple[str, str, str, str]
    outstanding: Callable[[dict[str, str]], bool]


CAPABILITIES: Final = Block(
    "capabilities",
    "Declared capabilities awaiting implementation",
    ("capability", "missing byte-level definition", "module or section", CONSEQUENCE),
    ("id", "definition", "module", "consequence"),
    lambda row: row.get("state") == DECLARED,
)
BUCKET_D: Final = Block(
    "bucket_d_status",
    "Bucket-D instruments awaiting liveness proof",
    ("instrument", "bytes present", "module to repair", CONSEQUENCE),
    ("instrument", "bytes_present", "module", "consequence"),
    lambda row: row.get("liveness_proven", "").casefold() != PROVEN,
)


def _blocks(text: str, key: str) -> list[dict[str, str]] | None:
    """Every ``- `` mapping under one top-level block key, or None when the key is absent."""
    rows: list[dict[str, str]] | None = None
    inside = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or _COMMENT.fullmatch(line):
            continue
        if not line.startswith(" "):
            inside = line == f"{key}:"
            rows = [] if inside and rows is None else rows
            continue
        if not inside or rows is None:
            continue
        item = _ROW.fullmatch(line)
        match = item or _FIELD.fullmatch(line)
        if match is None:
            continue
        value = match[2].strip().strip("'\"")
        if item is not None:
            rows.append({match[1]: value})
        elif rows:
            rows[-1].setdefault(match[1], value)
    return rows


def _cell(value: str | None) -> str:
    return " ".join((value or "").split()).replace("|", r"\|") or "not recorded"


def _table(headings: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    if not rows:
        return ["None recorded."]
    ruled = [headings, ["---"] * len(headings), *rows]
    return ["| " + " | ".join(cells) + " |" for cells in ruled]


def _section(title: str, body: Sequence[str]) -> list[str]:
    return [f"## {title}", "", *body, ""]


def _source_name(target: Target) -> str:
    return f"{runs.HARNESS[target.instrument]}/capabilities.yaml"


def _report_name(target: Target) -> str:
    harness = runs.HARNESS[target.instrument]
    return f"{harness}/{runs.RUNS_DIR}/{target.run_id}/{REPORT_NAME}"


def _todo_path(target: Target) -> Path:
    return runs.run_dir(target.root, target.instrument, target.run_id) / TODO_NAME


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _block_section(text: str, source: str, block: Block) -> list[str]:
    """One block as its own section: the outstanding rows, or why none is projected."""
    rows = _blocks(text, block.key)
    if rows is None:
        absent = f"No `{block.key}` block stands in `{source}`, so no row is projected from it."
        return _section(block.title, [absent])
    name, *rest = block.fields
    kept = [
        (f"`{_cell(row.get(name))}`", *(_cell(row.get(field)) for field in rest))
        for row in rows
        if block.outstanding(row)
    ]
    return _section(block.title, _table(block.headings, kept))


def _gap_body(target: Target, directory: Path) -> list[str]:
    """The recorded gap rows, or the one reason this run records none."""
    text = _read(directory / REPORT_NAME)
    if text is None:
        return [f"No run report stands at `{_report_name(target)}`, so no gap is recorded yet."]
    body = reports._sections(text).get(GAPS_SECTION, "")
    stated = [] if body.strip().casefold() in EMPTY_GAPS else body.splitlines()
    rows = [(_cell(line.strip().removeprefix("- ")),) for line in stated if line.strip()]
    return _table(GAP_HEADINGS, rows)


def _preamble(target: Target) -> str:
    return (
        f"This backlog is rendered from `{_source_name(target)}`, its source of truth, and from "
        f"the coverage gaps this run recorded under `## {GAPS_SECTION}` in `{_report_name(target)}`"
        ". It is never hand-maintained, and drift between this file and its source fails closed."
    )


def render_todo(target: Target) -> str:
    """The backlog this tree determines, computed in memory and never from a cache."""
    opened, source = runs.open_run, _source_name(target)
    directory = opened(target.root, target.instrument, target.run_id, principal=target.principal)
    capabilities = _read(target.root / source)
    if capabilities is None:
        raise RenderError(SOURCE_UNREADABLE, f"{source} is absent or unreadable")
    lines = [reports.GENERATED_BANNER, "", "# TODO", "", _preamble(target), ""]
    lines += _block_section(capabilities, source, CAPABILITIES)
    lines += _section(GAPS_SECTION, _gap_body(target, directory))
    if target.instrument == BUCKET_D_INSTRUMENT:
        lines += _block_section(capabilities, source, BUCKET_D)
    return "\n".join(lines)


def _atomic_write(path: Path, body: str) -> None:
    handle, name = tempfile.mkstemp(dir=str(path.parent), prefix=".render-", suffix=".md")
    scratch = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(body)
        scratch.chmod(0o644)
        scratch.replace(path)
    except OSError:
        scratch.unlink(missing_ok=True)
        raise


def write_todo(target: Target) -> bool:
    """Write the backlog when it differs. True when bytes moved, False when already current."""
    text, path = render_todo(target), _todo_path(target)
    if _read(path) == text:
        return False
    _atomic_write(path, text)
    return True


def check_todo(target: Target) -> list[Finding]:
    """Name the drift between the file on disk and its rendering, writing nothing."""
    path = _todo_path(target)
    if _read(path) == render_todo(target):
        return []
    display = display_project_path(path, project_root=target.root)
    message = f"{TODO_NAME} is not the rendering of {_source_name(target)}"
    return [Finding(DRIFT, Severity.ERROR, display, None, message)]


def _todo(target: Target, *, check: bool, as_json: bool) -> int:
    findings = check_todo(target) if check else []
    written = False if check else write_todo(target)
    display = display_project_path(_todo_path(target), project_root=target.root)
    if as_json:
        report = json.loads(serialize_findings(findings))
        payload = {"path": display, "written": written, "findings": report}
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        for item in findings:
            print(f"{item.code}: {render_finding(item)}")
    else:
        print(f"{'wrote' if written else 'current'} {display}")
    return EXIT_DRIFT if findings else EXIT_CLEAN


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 tools/render.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    todo = sub.add_parser("todo", help="render this run's augmentation backlog")
    todo.add_argument("root")
    todo.add_argument("--instrument", required=True, choices=sorted(runs.HARNESS))
    todo.add_argument("--run", required=True, dest="run_id")
    todo.add_argument("--principal", required=True)
    todo.add_argument("--check", action="store_true", help="compare byte for byte, write nothing")
    todo.add_argument("--json", action="store_true", dest="as_json", help="print one JSON object")
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
        target = Target(
            root, str(arguments.instrument), str(arguments.run_id), str(arguments.principal)
        )
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        return _todo(target, check=bool(arguments.check), as_json=bool(arguments.as_json))
    except (RenderError, runs.RunError) as exc:
        if arguments.as_json:
            print(json.dumps({"code": exc.code, "written": False}, sort_keys=True))
        else:
            print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
