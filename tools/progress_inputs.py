"""Safe byte manifests and the four-component phase fingerprint."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from pathlib import Path

from tools import _phases
from tools.attest.canonical import canonical_sha256
from tools.progress_types import Entry, Evidence, Fingerprint, Target
from tools.project_paths import ProjectPathError, resolve_project_path


def gitlinks(root: Path) -> dict[str, str]:
    if not (root / ".git").exists():
        return {}
    done = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-s", "-z"],
        capture_output=True,
        check=True,
        timeout=15,
    )
    links: dict[str, str] = {}
    for record in done.stdout.decode().split("\0"):
        if record.startswith("160000 "):
            metadata, path = record.split("\t", 1)
            links[path] = metadata.split()[1]
    return links


def submodule_clean(root: Path, name: str) -> bool:
    checkout = resolve_project_path(f"./{name}", project_root=root)
    if not (checkout / ".git").exists():
        return False
    done = subprocess.run(
        ["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        check=False,
        timeout=15,
    )
    return done.returncode == 0 and not done.stdout and not done.stderr


def file_entry(root: Path, name: str) -> Entry:
    try:
        path = resolve_project_path(name, project_root=root)
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            return Entry(path=name, mode="0000", sha256=None, state="unreadable")
        return Entry(
            path=name,
            mode=f"{stat.S_IMODE(metadata.st_mode):04o}",
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            state="present",
        )
    except FileNotFoundError:
        return Entry(path=name, mode="0000", sha256=None, state="missing")
    except (OSError, ProjectPathError):
        return Entry(path=name, mode="0000", sha256=None, state="unreadable")


def expand(root: Path, pattern: str) -> list[str]:
    base = pattern.split("*", 1)[0].rstrip("/") or "./"
    resolve_project_path(base, project_root=root)
    if "*" not in pattern:
        return [pattern]
    names: set[str] = set()
    for match in root.glob(pattern[2:]):
        if match.is_dir() and not match.is_symlink():
            for directory, dirs, files in os.walk(match, followlinks=False):
                dirs[:] = sorted(d for d in dirs if d != ".git")
                names.update(
                    f"./{(Path(directory) / f).relative_to(root).as_posix()}" for f in files
                )
                names.update(
                    f"./{(Path(directory) / d).relative_to(root).as_posix()}"
                    for d in dirs
                    if (Path(directory) / d).is_symlink()
                )
        else:
            names.add(f"./{match.relative_to(root).as_posix()}")
    return sorted(names) or [pattern]


def manifest(
    root: Path, patterns: tuple[str, ...], *, binding: bool = False
) -> tuple[list[Entry], bool]:
    links = gitlinks(root) if binding else {}
    result: dict[str, Entry] = {}
    dirty = False
    for pattern in patterns:
        link = next(
            (name for name in links if pattern[2:] == name or pattern[2:].startswith(name + "/")),
            None,
        )
        if link is not None:
            clean = submodule_clean(root, link)
            dirty |= not clean
            name = f"./{link}"
            result[name] = Entry(
                path=name,
                mode="160000",
                sha256=links[link] if clean else None,
                state="present" if clean else "unreadable",
            )
            continue
        try:
            paths = expand(root, pattern)
        except (OSError, ProjectPathError):
            paths = [pattern]
        for name in paths:
            result[name] = file_entry(root, name)
    return [result[name] for name in sorted(result)], dirty


def snapshot(target: Target, row: _phases.Phase) -> Evidence:
    reads, dirty = manifest(target.root, row.reads, binding=True)
    reconciles, reconcile_dirty = manifest(target.root, row.reconciles, binding=True)
    artifacts, _ = manifest(target.root, row.artifacts)
    contract = file_entry(target.root, _phases.CONTRACT[target.instrument])
    links = gitlinks(target.root)
    if "trinity" in links:
        dirty |= not submodule_clean(target.root, "trinity")
    approval = None
    bound = None
    if row.approval_file and row.approval_binds:
        bound = file_entry(target.root, row.approval_binds)["sha256"]
        try:
            approval = (
                resolve_project_path(row.approval_file, project_root=target.root)
                .read_text()
                .strip()
            )
        except (OSError, UnicodeError, ProjectPathError):
            approval = None
    combined = {item["path"]: item for item in reads + reconciles}
    fp = Fingerprint(
        schema="trinity.phase-fingerprint/v1",
        phase=row.id,
        inputs=[combined[key] for key in sorted(combined)],
        approval_digest=approval,
        contract_sha256=contract["sha256"],
        trinity_gitlink=links.get("trinity"),
    )
    problem = None
    if dirty or reconcile_dirty:
        problem = "submodule_dirty"
    elif any(item["state"] == "unreadable" for item in reads + reconciles):
        problem = "input_unreadable"
    elif contract["state"] == "unreadable":
        problem = "contract_unreadable"
    return Evidence(
        fingerprint=fp,
        inputs_fp=canonical_sha256(fp),
        reads=reads,
        reconciles=reconciles,
        artifacts=artifacts,
        approval_digest=approval,
        bound_digest=bound,
        codes=[],
        problem=problem,
        opened_contract=fp["contract_sha256"],
        opened_gitlink=fp["trinity_gitlink"],
    )
