"""Canonical, versioned identities for Trinity task-bundle file trees.

The identity binds each regular file's relative path, exact bytes, and executable bit. Symbolic
links and every other non-regular object are refused. Callers comparing repository checkouts may
exclude only explicitly named top-level VCS metadata. Bundle identities exclude only top-level
trajectories/ evidence: rollouts are recorded after the freeze and cannot move identity.

Reads use no-follow file descriptors and compare pre-read, descriptor, and post-read metadata.
This detects replacement during an ordinary verification but is not a complete defence against a
hostile filesystem. Release verification requires an immutable verifier snapshot for that threat.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

IDENTITY_VERSION = "trinity.bundle-identity/v1"
BUNDLE_EVIDENCE_DIRS: frozenset[str] = frozenset({"trajectories"})
SET_IDENTITY_VERSION = "trinity.bundle-set-identity/v1"
SNAPSHOT_IDENTITY_VERSION = "trinity.release-snapshot/v1"
ZERO_DIGEST = "0" * 64
TOP_LEVEL_METADATA_FILES = frozenset({"README.md", "reward-schema.json"})
TOP_LEVEL_METADATA_DIRS = frozenset({".github"})


class BundleIdentityError(ValueError):
    """The requested tree has no safe, stable canonical identity."""


@dataclass(frozen=True, slots=True)
class FileIdentity:
    path: str
    digest: str
    executable: bool


def _metadata(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)


def _require_unlinked_root(root: Path) -> Path:
    absolute = root.absolute()
    try:
        info = absolute.lstat()
    except OSError as exc:
        raise BundleIdentityError(f"tree root {root} is unavailable: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise BundleIdentityError(f"tree root {root} is a symbolic link")
    if not stat.S_ISDIR(info.st_mode):
        raise BundleIdentityError(f"tree root {root} is not a directory")
    try:
        resolved = absolute.resolve(strict=True)
    except OSError as exc:
        raise BundleIdentityError(f"tree root {root} cannot be resolved: {exc}") from exc
    if resolved != absolute:
        raise BundleIdentityError(f"tree root {root} reaches its location through a symbolic link")
    return absolute


def _read_regular(path: Path) -> tuple[bytes, os.stat_result]:
    try:
        before = path.lstat()
    except OSError as exc:
        raise BundleIdentityError(f"cannot inspect {path}: {exc}") from exc
    if not stat.S_ISREG(before.st_mode):
        kind = "symbolic link" if stat.S_ISLNK(before.st_mode) else "non-regular object"
        raise BundleIdentityError(f"{path} is a {kind}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BundleIdentityError(f"cannot safely open {path}: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _metadata(opened) != _metadata(before):
            raise BundleIdentityError(f"{path} changed while its identity was being read")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after_descriptor = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after_path = path.lstat()
    except OSError as exc:
        raise BundleIdentityError(f"{path} disappeared while its identity was being read") from exc
    if _metadata(before) != _metadata(after_descriptor) or _metadata(before) != _metadata(
        after_path
    ):
        raise BundleIdentityError(f"{path} changed while its identity was being read")
    return b"".join(chunks), before


def tree_manifest(
    root: Path, *, exclude_top_level: frozenset[str] = frozenset()
) -> tuple[FileIdentity, ...]:
    """Return the safe canonical manifest for ``root``.

    Exclusions match direct children of ``root`` only. They cover repository metadata during
    checkout comparison and only ``trajectories/`` evidence for task bundles, because rollouts
    are recorded after the freeze and cannot move identity.
    """

    absolute = _require_unlinked_root(root)
    root_before = absolute.stat()
    files: list[FileIdentity] = []
    stack = [absolute]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise BundleIdentityError(f"cannot enumerate {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(absolute)
            if len(relative.parts) == 1 and entry.name in exclude_top_level:
                continue
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise BundleIdentityError(f"cannot inspect {path}: {exc}") from exc
            if stat.S_ISLNK(info.st_mode):
                raise BundleIdentityError(f"{path} is a symbolic link")
            if stat.S_ISDIR(info.st_mode):
                stack.append(path)
                continue
            if not stat.S_ISREG(info.st_mode):
                raise BundleIdentityError(f"{path} is a non-regular object")
            payload, stable = _read_regular(path)
            files.append(
                FileIdentity(
                    path=relative.as_posix(),
                    digest=hashlib.sha256(payload).hexdigest(),
                    executable=bool(stable.st_mode & 0o111),
                )
            )
    root_after = absolute.stat()
    if _metadata(root_before) != _metadata(root_after):
        raise BundleIdentityError(f"tree root {root} changed while its identity was being read")
    return tuple(sorted(files, key=lambda item: item.path))


def manifest_digest(manifest: tuple[FileIdentity, ...]) -> str:
    hasher = hashlib.sha256()
    hasher.update((IDENTITY_VERSION + "\n").encode("ascii"))
    for item in manifest:
        mode = "x" if item.executable else "-"
        hasher.update(f"{item.path}\0{mode}\0{item.digest}\n".encode())
    return hasher.hexdigest()


def bundle_digest(bundle_root: Path) -> str:
    """Identify one non-empty task bundle excluding top-level rollout evidence."""

    manifest = tree_manifest(bundle_root, exclude_top_level=BUNDLE_EVIDENCE_DIRS)
    if not manifest:
        raise BundleIdentityError(f"bundle {bundle_root} contains no regular files")
    return manifest_digest(manifest)


def bundle_set_digest(samples: Path, bundle_ids: list[str], *, allow_empty: bool = False) -> str:
    """Identify a set of task bundles by sorted identifier and canonical bundle identity."""

    identifiers = sorted(bundle_ids)
    if not identifiers:
        if allow_empty:
            return ZERO_DIGEST
        raise BundleIdentityError(f"release population under {samples} is empty")
    hasher = hashlib.sha256()
    hasher.update((SET_IDENTITY_VERSION + "\n").encode("ascii"))
    for bundle_id in identifiers:
        hasher.update(f"{bundle_id}\0{bundle_digest(samples / bundle_id)}\n".encode())
    return hasher.hexdigest()


def validate_release_population(samples: Path, bundle_ids: list[str]) -> None:
    """Reject unclassified top-level content while permitting closed release metadata."""

    absolute = _require_unlinked_root(samples)
    expected = set(bundle_ids)
    for entry in os.scandir(absolute):
        if entry.name == ".git":
            continue
        info = entry.stat(follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise BundleIdentityError(f"{entry.path} is a symbolic link")
        if entry.name in expected:
            if not stat.S_ISDIR(info.st_mode):
                raise BundleIdentityError(f"task bundle {entry.path} is not a directory")
            continue
        if entry.name in TOP_LEVEL_METADATA_FILES and stat.S_ISREG(info.st_mode):
            continue
        if entry.name in TOP_LEVEL_METADATA_DIRS and stat.S_ISDIR(info.st_mode):
            continue
        raise BundleIdentityError(f"unexpected top-level release object {entry.name!r}")


def release_snapshot_digest(samples: Path, bundle_ids: list[str]) -> str:
    """Bind every release-tree byte except explicit top-level Git metadata."""

    validate_release_population(samples, bundle_ids)
    manifest = tree_manifest(samples, exclude_top_level=frozenset({".git"}))
    if not bundle_ids:
        raise BundleIdentityError(f"release population under {samples} is empty")
    hasher = hashlib.sha256()
    hasher.update((SNAPSHOT_IDENTITY_VERSION + "\n").encode("ascii"))
    for item in manifest:
        mode = "x" if item.executable else "-"
        hasher.update(f"{item.path}\0{mode}\0{item.digest}\n".encode())
    return hasher.hexdigest()
