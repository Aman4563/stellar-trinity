"""The commit-time comparison between the rendered root reports and the git index.

``pipeline.py render-reports ./ --check --staged`` is what a commit hook runs, so the
commit publishes reports rendered from the very bytes that commit carries. This module
answers that one question. It reads git and never writes it: no ``add``, no ``commit``,
no ``push``, no ``checkout``, no ``stash``. Its only write is the expected report bytes
into the working tree, so a human reads them and stages them deliberately.

Finding codes: ``REPORT_STAGED_UNAVAILABLE`` when the root is no git repository,
``REPORT_INPUTS_UNSTAGED`` when a dashboard input differs between the index and the
working tree, and ``REPORT_NOT_STAGED`` when a report's index bytes are not its
rendering.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import reports
    from tools._findings import Finding, Severity
else:
    try:
        from tools import reports
        from tools._findings import Finding, Severity
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        import reports
        from _findings import Finding, Severity

INPUT_DIRS: Final[tuple[str, ...]] = (
    ".memory",
    ".seed",
    ".audit",
    ".podium",
    ".trial",
    "staging",
    "samples",
    "delivery",
)
UNTRACKED_INPUT_ROOTS: Final[tuple[str, ...]] = (
    ".memory/",
    ".seed/",
    ".audit/",
    ".podium/",
    ".trial/",
    "staging/",
    "samples/",
    "delivery/",
)
_UNSTAGED_WORKTREE_STATES: Final = frozenset("MD")
_STATUS_PATH_OFFSET: Final = 3
_NAMED_PATH_CEILING: Final = 5
_GIT_TIMEOUT_SECONDS: Final = 30.0


@dataclass(frozen=True, slots=True)
class StagedReports:
    written: tuple[str, ...]
    findings: tuple[Finding, ...]


def _finding(path: Path, code: str, message: str) -> Finding:
    return Finding(code, Severity.ERROR, str(path), None, message)


def _git(root: Path, *arguments: str) -> bytes | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def _status_entries(root: Path, paths: Sequence[str]) -> list[tuple[str, str]] | None:
    """Every ``git status`` entry under ``paths`` as its two state letters and its path."""
    raw = _git(root, "status", "--porcelain", "-z", "--", *paths)
    if raw is None:
        return None
    fields = raw.decode("utf-8", "replace").split("\0")
    out: list[tuple[str, str]] = []
    cursor = 0
    while cursor < len(fields):
        entry = fields[cursor]
        cursor += 1
        if len(entry) <= _STATUS_PATH_OFFSET:
            continue
        if entry[0] in {"R", "C"}:
            cursor += 1
        out.append((entry[:2], entry[_STATUS_PATH_OFFSET:]))
    return out


def _is_unstaged(state: str, path: str) -> bool:
    if state == "??":
        return path in INPUT_DIRS or path.startswith(UNTRACKED_INPUT_ROOTS)
    return state[1] in _UNSTAGED_WORKTREE_STATES


def _unstaged_input_findings(root: Path, names: Sequence[str]) -> list[Finding]:
    entries = _status_entries(root, [*INPUT_DIRS, *names])
    if entries is None:
        return [
            _finding(
                root, "REPORT_STAGED_UNAVAILABLE", "git status could not inventory report inputs"
            )
        ]
    unstaged = sorted(path for state, path in entries if _is_unstaged(state, path))
    if not unstaged:
        return []
    remainder = len(unstaged) - _NAMED_PATH_CEILING
    tail = f" and {remainder} more" if remainder > 0 else ""
    named = ", ".join(unstaged[:_NAMED_PATH_CEILING])
    return [
        _finding(
            root,
            "REPORT_INPUTS_UNSTAGED",
            "a dashboard input is not staged, so this commit would publish a report rendered "
            f"from bytes it does not carry: {named}{tail}",
        )
    ]


def staged_reports(root: Path) -> StagedReports:
    """Refuse an index whose reports are not its rendering, leaving the bytes to stage."""
    if _git(root, "rev-parse", "--git-dir") is None:
        message = "--staged needs a git repository at the parent root"
        return StagedReports((), (_finding(root, "REPORT_STAGED_UNAVAILABLE", message),))
    expected = reports.rendered_root_reports(root)
    findings = _unstaged_input_findings(root, sorted(expected))
    written: list[str] = []
    for name, rendered in expected.items():
        if _git(root, "show", f":{name}") == rendered.encode("utf-8"):
            continue
        (root / name).write_text(rendered, encoding="utf-8")
        written.append(name)
        findings.append(
            _finding(
                root / name,
                "REPORT_NOT_STAGED",
                f"{name} in the index is not its rendering; the expected bytes are now in the "
                "working tree, so review them and git add them",
            )
        )
    return StagedReports(tuple(written), tuple(findings))
