"""The subject closure one run's qualification binds, instead of the whole repository.

Under many concurrent runners, a disposition that binds ``HEAD`` dies the moment anyone
else's commit lands. A run's qualification therefore binds a closure: every byte in the
run's own namespace that is input rather than output, every bundle the run sealed or
judged at its full sealed digest, the human inputs under ``requirements/`` and
``touchstones/``, the projection the instrument reads, and the ``trinity/`` gitlink. A
foreign commit outside that closure leaves the qualification current; a change inside
it invalidates the qualification, whoever made it.

The verifier computes the closure from disk; candidate metadata never chooses it.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import pipeline, runs
else:
    try:
        from tools import pipeline, runs
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        import pipeline
        import runs

SCHEMA: Final = "trinity.subject-closure/v1"
INPUT_ROOTS: Final = ("requirements", "touchstones")
VIEWS: Final[dict[str, str]] = {
    "FORGE": ".memory/forge_view.yaml",
    "CRUCIBLE": ".memory/crucible_view.yaml",
}
OUTPUT_NAMES: Final = frozenset(
    {"disposition.json", "report.md", "progress.yaml", "TODO.md", "tracker.json"}
)
OUTPUT_DIRS: Final = frozenset({"gate-receipts"})
TRINITY_DIR: Final = "trinity"
GIT_SHA_LENGTH: Final = 40


class SubjectError(ValueError):
    """The closure cannot be computed safely."""


@dataclass(frozen=True, slots=True)
class Entry:
    kind: str
    path: str
    mode: str
    size: int
    sha256: str


def _file_entry(kind: str, logical: str, path: Path) -> Entry:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        raise SubjectError(f"{logical} is a symlink; the closure holds regular files only")
    if not stat.S_ISREG(info.st_mode):
        raise SubjectError(f"{logical} is not a regular file")
    mode = "0755" if info.st_mode & stat.S_IXUSR else "0644"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Entry(kind, logical, mode, info.st_size, digest)


def _walk(kind: str, root: Path, base: Path, *, skip: Path | None = None) -> list[Entry]:
    out: list[Entry] = []
    if not base.exists():
        return out
    if base.is_symlink():
        raise SubjectError(f"{base.relative_to(root).as_posix()} is a symlink")
    for directory, names, files in os.walk(base):
        here = Path(directory)
        if here == skip:
            names[:] = []
            continue
        names[:] = sorted(name for name in names if not (here == base and name in OUTPUT_DIRS))
        for name in sorted(files):
            if here == base and name in OUTPUT_NAMES and kind == "run":
                continue
            path = here / name
            out.append(_file_entry(kind, path.relative_to(root).as_posix(), path))
    return out


def _trinity_commit(root: Path) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "rev-parse", f"HEAD:{TRINITY_DIR}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = done.stdout.strip()
    return value if done.returncode == 0 and len(value) == GIT_SHA_LENGTH else None


def _bundles(root: Path, instrument: str, run_id: str) -> list[Entry]:
    out: list[Entry] = []
    try:
        latest = pipeline.sealed_records(root)
    except pipeline.PipelineError as exc:
        raise SubjectError(f"sealed queue is unreadable: {exc}") from exc
    for uuid, record in sorted(latest.items()):
        digest = str(record["bundle_digest"])
        if instrument == "FORGE" and record["stream"] == run_id:
            out.append(Entry("bundle", uuid, "sealed", 0, digest))
        if instrument == "CRUCIBLE":
            verdict = pipeline.verdict_records(root, uuid).get(digest)
            if verdict is not None and verdict.get("consumer_run_id") == run_id:
                out.append(Entry("bundle", uuid, "judged", 0, digest))
    return out


def subject_manifest(root: Path, instrument: str, run_id: str) -> list[Entry]:
    """Every entry of the run's closure, sorted by kind then path."""
    directory = runs.run_dir(root, instrument, run_id)
    if not (directory / "run.json").is_file():
        raise SubjectError(f"no run {run_id} under {directory.parent.relative_to(root)}")
    entries = _walk("run", root, directory)
    entries += _bundles(root, instrument, run_id)
    for name in INPUT_ROOTS:
        entries += _walk("input", root, root / name)
    view = VIEWS.get(instrument)
    if view is not None and (root / view).exists():
        entries.append(_file_entry("view", view, root / view))
    trinity = _trinity_commit(root)
    if trinity is not None:
        entries.append(Entry("trinity", TRINITY_DIR, "gitlink", 0, trinity))
    return sorted(entries, key=lambda item: (item.kind, item.path))


def render_manifest(entries: list[Entry]) -> str:
    lines = [
        f"{item.kind}\t{item.path}\t{item.mode}\t{item.size}\t{item.sha256}"
        for item in sorted(entries, key=lambda item: (item.kind, item.path))
    ]
    return "\n".join(lines) + "\n"


def subject_digest(root: Path, instrument: str, run_id: str) -> str:
    """SHA-256 of the canonical manifest, the value a run's qualification binds."""
    body = SCHEMA + "\n" + render_manifest(subject_manifest(root, instrument, run_id))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
