"""The protected records one accepted commit carries, read straight from git.

An accepted state is whatever a named commit holds under the protected prefixes: the sealed
queue streams, the audit claims and verdicts, the sentinel ledgers, the memory epochs, and the
run markers that bind a namespace to a principal. Every read here goes through ``git ls-tree``
and ``git cat-file`` against an explicit ref, never through the working tree, because the
working tree is the candidate operator's to shape and the accepted state is not.

Blob object ids are the identity used for immutability: two paths carry the same bytes exactly
when git recorded the same object id, so an unchanged record costs one tree listing rather than
a file read. Bytes are fetched only for the records a rule must parse.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

QUEUE_PREFIX: Final = ".podium/queue"
LEGACY_QUEUE: Final = ".podium/queue.jsonl"
CLAIMS_PREFIX: Final = ".audit/queue.claims"
VERDICTS_PREFIX: Final = ".audit/verdicts"
SENTINEL_PREFIX: Final = ".sentinel"
EPOCHS_PREFIX: Final = ".memory/epochs"
CURRENT_PATH: Final = ".memory/current.json"
TRUST_POLICY_PATH: Final = ".memory/roots.yaml"
RUN_PREFIXES: Final = (".memory/runs", ".seed/runs", ".audit/runs")
_TIMEOUT: Final = 15.0
_LS_TREE_FIELDS: Final = ("objecttype", "objectname", "path")


class Protected(StrEnum):
    """The kind of accepted record a protected path holds."""

    STREAM = "stream"
    CLAIM = "claim"
    VERDICT = "verdict"
    SENTINEL = "sentinel"
    EPOCH = "epoch"
    RUN = "run"


def classify(path: str) -> Protected | None:
    """The record kind ``path`` holds, or None when the path is outside protected state."""
    if path == LEGACY_QUEUE or path.startswith(f"{QUEUE_PREFIX}/"):
        return Protected.STREAM
    if path.startswith(f"{CLAIMS_PREFIX}/"):
        return Protected.CLAIM
    if path.startswith(f"{VERDICTS_PREFIX}/"):
        return Protected.VERDICT
    if path.startswith(f"{SENTINEL_PREFIX}/"):
        return Protected.SENTINEL
    if path.startswith(f"{EPOCHS_PREFIX}/"):
        return Protected.EPOCH
    if any(path.startswith(f"{prefix}/") for prefix in RUN_PREFIXES):
        return Protected.RUN
    return None


def run_namespace(path: str) -> str | None:
    """The run id owning ``path``, for any path inside a run namespace."""
    for prefix in RUN_PREFIXES:
        if path.startswith(f"{prefix}/"):
            tail = path[len(prefix) + 1 :].split("/", 1)[0]
            return tail or None
    return None


def _git(root: Path, argv: list[str]) -> tuple[int, bytes]:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *argv],
            capture_output=True,
            check=False,
            timeout=_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, b""
    return done.returncode, done.stdout


def resolve(root: Path, ref: str) -> str | None:
    """The commit id ``ref`` names, or None when it does not resolve to a commit."""
    status, out = _git(root, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    if status != 0:
        return None
    text = out.decode("utf-8", "replace").strip()
    return text or None


def parents(root: Path, commit: str) -> list[str]:
    """The parent commit ids of ``commit`` in recorded order, empty when it has none."""
    status, out = _git(root, ["rev-list", "--parents", "-n", "1", commit])
    if status != 0:
        return []
    return out.decode("utf-8", "replace").split()[1:]


@dataclass(frozen=True, slots=True)
class AcceptedState:
    """One commit's protected records, keyed by path and identified by blob object id."""

    commit: str
    blobs: dict[str, str]

    def kind(self, kind: Protected) -> dict[str, str]:
        return {path: oid for path, oid in self.blobs.items() if classify(path) is kind}

    def holds(self, path: str) -> bool:
        return path in self.blobs


def read_state(root: Path, commit: str) -> AcceptedState:
    """Every protected path ``commit`` carries, mapped to its blob object id."""
    listing = ["ls-tree", "-r", "-z", "--format=%(objecttype) %(objectname) %(path)", commit]
    status, out = _git(root, listing)
    blobs: dict[str, str] = {}
    if status != 0:
        return AcceptedState(commit, blobs)
    for record in out.decode("utf-8", "replace").split("\0"):
        parts = record.split(" ", 2)
        if len(parts) != len(_LS_TREE_FIELDS) or parts[0] != "blob":
            continue
        _, oid, path = parts
        if classify(path) is not None or path in (CURRENT_PATH, TRUST_POLICY_PATH):
            blobs[path] = oid
    return AcceptedState(commit, blobs)


def read_blob(root: Path, commit: str, path: str) -> bytes | None:
    """The bytes ``commit`` holds at ``path``, or None when it holds nothing there."""
    status, out = _git(root, ["cat-file", "blob", f"{commit}:{path}"])
    return out if status == 0 else None


def read_object(root: Path, oid: str) -> bytes | None:
    """The bytes of one blob object id, so an unchanged path is never re-resolved by path."""
    status, out = _git(root, ["cat-file", "blob", oid])
    return out if status == 0 else None


def json_object(data: bytes | None) -> dict[str, object]:
    """One accepted record parsed as a JSON object; an unreadable record is an empty one."""
    if data is None:
        return {}
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def text_field(body: dict[str, object], key: str) -> str:
    """One string field of a parsed record, empty when absent or of another type."""
    value = body.get(key)
    return value if isinstance(value, str) else ""
