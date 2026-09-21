"""Read-only static probe for affirmative sentinel evidence in untrusted repository bytes.

The probe never imports or executes candidate Python, shell, workflow, generator, or hook code. It
uses bounded no-follow reads and Python's parser only. Its deliberately narrow result is suitable
for a trusted observer; absence of findings is not a general integrity verdict.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.project_paths import (
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
else:
    try:
        from tools.project_paths import (
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from project_paths import (
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )

SCHEMA = "trinity.static-incident-probe/v1"
MAX_FILE_BYTES = 1_000_000
MAX_FILES = 2_000
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
# Mirrors the liveness vocabulary of tools/sabotage.py; this module stays import-free of it so
# the observer runs the probe with nothing but the parser and project_paths.
_INSTRUMENT_PREFIXES = ("g_", "check_", "inst_", "instrument_")
_SANDBOX_NAMES = frozenset({"sandbox_state", "sandbox_available", "hermetic"})
_GAP_CALLEES = frozenset({"gap", "coverage_gap", "_gap"})
_LIVE_MARKERS = ("finding", "fire")
GATE_INVOCATIONS = (
    "integrity.py",
    "sentinel.py",
    "incident_probe.py",
    "release.py",
    "sabotage.py",
    "gate.py",
    "pipeline.py",
    "harbor.py",
    "parent-sanity",
)
_STEP_START = re.compile(r"^([ \t]*)-[ \t]")
_BYPASS = (
    re.compile(r"^[ \t]*set[ \t]+\+e(?:[ \t]|$)"),
    re.compile(r"\|\|[ \t]*true(?:[ \t]|$)"),
    re.compile(r"(?i)^[ \t]*continue-on-error:[ \t]*true[ \t]*$"),
)
_SHIP = re.compile(r"(?m)^##\s+Disposition\s*$\n+(?:\s*\n)*[^\n]*\bSHIP(?::INFERRED)?\b")


@dataclass(frozen=True, slots=True)
class Evidence:
    code: str
    path: str
    line: int | None


def _inside(root: Path, path: Path) -> Path:
    absolute_root = Path(os.path.abspath(root))  # noqa: PTH100 - lexical, never follow symlinks
    absolute_path = Path(os.path.abspath(path))  # noqa: PTH100 - lexical, never follow symlinks
    try:
        return absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise ValueError("probe path escapes candidate root") from exc


def _read_regular(root: Path, path: Path) -> bytes:
    relative = _inside(root, path)
    current = Path(os.path.abspath(root))  # noqa: PTH100 - lexical, never follow symlinks
    ancestor = Path(current.anchor)
    for part in current.parts[1:]:
        ancestor /= part
        if stat.S_ISLNK(os.lstat(ancestor).st_mode):
            raise ValueError("candidate root component is symbolic")
    root_meta = os.lstat(current)
    if stat.S_ISLNK(root_meta.st_mode) or not stat.S_ISDIR(root_meta.st_mode):
        raise ValueError("candidate root must be a real directory")
    for part in relative.parts:
        current /= part
        metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"probe refuses symbolic path {relative}")
    metadata = os.lstat(path)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_FILE_BYTES:
        raise ValueError(f"probe refuses non-regular or oversized file {relative}")
    descriptor = os.open(path, os.O_RDONLY | _NOFOLLOW)
    try:
        document = os.read(descriptor, MAX_FILE_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(document) > MAX_FILE_BYTES:
        raise ValueError(f"probe file grew beyond its bound {relative}")
    return document


def _callee(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _own_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    nodes: list[ast.AST] = []
    stack: list[ast.AST] = list(function.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef):
            continue
        nodes.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return nodes


def _inert_return(value: ast.expr | None) -> bool:
    if value is None or isinstance(value, ast.Constant):
        return True
    if isinstance(value, ast.List | ast.Tuple | ast.Set):
        return not value.elts
    if isinstance(value, ast.Dict):
        return not [item for item in value.values if item is not None]
    if isinstance(value, ast.Call):
        return _callee(value.func) in _GAP_CALLEES
    return False


def _false_literal(value: ast.expr | None) -> bool:
    if isinstance(value, ast.Constant):
        return value.value is False
    if isinstance(value, ast.Dict):
        return any(_false_literal(item) for item in value.values if item is not None)
    return False


def _mentions_live_marker(function: ast.AST) -> bool:
    for child in ast.walk(function):
        name = child.id if isinstance(child, ast.Name) else None
        if isinstance(child, ast.Attribute):
            name = child.attr
        if name is not None and any(marker in name.lower() for marker in _LIVE_MARKERS):
            return True
    return False


def _exercises_a_decision(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in _own_nodes(function):
        if isinstance(node, ast.Raise | ast.Assert):
            return True
        if isinstance(node, ast.Call) and _callee(node.func) not in _GAP_CALLEES:
            return True
    return False


def _inert(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    returns = [item for item in _own_nodes(node) if isinstance(item, ast.Return)]
    if node.name in _SANDBOX_NAMES:
        has_call = any(isinstance(child, ast.Call) for child in ast.walk(node))
        return any(_false_literal(item.value) for item in returns) and not has_call
    if not node.name.startswith(_INSTRUMENT_PREFIXES) or not returns:
        return False
    return (
        all(_inert_return(item.value) for item in returns)
        and not _mentions_live_marker(node)
        and not _exercises_a_decision(node)
    )


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _enclosing_block(lines: list[str], index: int) -> str:
    """The YAML block a line belongs to: its own list item, or its nearest less-indented parent."""
    owner = index
    if _STEP_START.match(lines[index]) is None:
        depth = _indent(lines[index])
        owner = next(
            (
                position
                for position in range(index - 1, -1, -1)
                if lines[position].strip() and _indent(lines[position]) < depth
            ),
            0,
        )
    depth = _indent(lines[owner])
    stop = next(
        (
            position
            for position in range(owner + 1, len(lines))
            if lines[position].strip() and _indent(lines[position]) <= depth
        ),
        len(lines),
    )
    return "\n".join(lines[owner:stop])


def bypasses_a_gate(text: str) -> bool:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not any(pattern.search(line) for pattern in _BYPASS):
            continue
        block = _enclosing_block(lines, index)
        if any(token in block for token in GATE_INVOCATIONS):
            return True
    return False


def _regular_files(base: Path, suffix: str) -> list[Path]:
    if not base.exists() or base.is_symlink():
        return []
    files: list[Path] = []
    for directory, names, filenames in os.walk(base, followlinks=False):
        names[:] = sorted(name for name in names if not Path(directory, name).is_symlink())
        for name in sorted(filenames):
            path = Path(directory, name)
            if path.suffix == suffix:
                files.append(path)
                if len(files) > MAX_FILES:
                    raise ValueError("probe file count exceeds its bound")
    return files


def probe(root: Path, changed_paths: tuple[str, ...] = ()) -> list[Evidence]:
    findings: list[Evidence] = []
    for harness in (root / ".audit", root / ".seed"):
        for path in _regular_files(harness, ".py"):
            relative = _inside(root, path).as_posix()
            try:
                tree = ast.parse(_read_regular(root, path), filename=relative)
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _inert(node):
                    findings.append(Evidence("SAB_INERT_INSTRUMENT", relative, node.lineno))
    for raw in sorted(set(changed_paths)):
        normalized = raw.strip().removeprefix("./")
        if not normalized.startswith(".github/workflows/"):
            continue
        path = root / normalized
        try:
            text = _read_regular(root, path).decode("utf-8")
        except (FileNotFoundError, UnicodeDecodeError, ValueError):
            continue
        if bypasses_a_gate(text):
            findings.append(Evidence("SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS", normalized, None))
    if findings:
        for name in ("VERDICT.md", "EDICT.md", "DIRECTIVE.md"):
            path = root / name
            try:
                text = _read_regular(root, path).decode("utf-8")
            except (FileNotFoundError, UnicodeDecodeError, ValueError):
                continue
            if _SHIP.search(text):
                findings.append(Evidence("SAB_DISPOSITION_FORGED", name, None))
    return sorted(set(findings), key=lambda item: (item.code, item.path, item.line or 0))


def render(findings: list[Evidence]) -> bytes:
    evidence = [{"code": item.code, "line": item.line, "path": item.path} for item in findings]
    evidence_bytes = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    payload = {
        "codes": sorted({item.code for item in findings}),
        "evidence_digest": hashlib.sha256(evidence_bytes).hexdigest(),
        "schema": SCHEMA,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--changed-paths")
    args = parser.parse_args(argv)
    try:
        project_root = invocation_root()
        candidate_root = resolve_project_path(
            str(args.root),
            project_root=project_root,
            description="candidate root",
            must_exist=True,
        )
        changed_path = (
            None
            if args.changed_paths is None
            else resolve_project_path(
                str(args.changed_paths),
                project_root=project_root,
                description="changed-path input",
                must_exist=True,
            )
        )
        changed: tuple[str, ...] = ()
        if changed_path is not None:
            document = changed_path.read_text(encoding="utf-8")
            if len(document.encode()) > MAX_FILE_BYTES:
                raise ValueError("changed-path input exceeds its bound")
            changed = tuple(document.splitlines())
        sys.stdout.buffer.write(render(probe(candidate_root, changed)))
    except (OSError, ValueError) as exc:
        root = locals().get("project_root")
        message = (
            str(exc)
            if not isinstance(root, Path)
            else redact_project_root(str(exc), project_root=root)
        )
        print(f"incident probe refused: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
