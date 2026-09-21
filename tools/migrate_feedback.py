"""Rewrite a legacy harness-root feedback chain into the closed line schema.

Chains written before ``github_id`` joined ``CHAIN_FIELDS`` carry no login and a ``writer``
that is either a bare string or an object naming runtime, model lineage, and git sha. The
walker refuses the first such line, so every parent that captured feedback before the
schema closed halts before Phase R and nothing on disk can lift it. This module decides,
over bytes alone, whether a chain is that legacy shape and what its closed-shape
replacement is; ``migrate.py`` owns the backup, the journal, and the write.

Every line is recomputed from the first line onward, because ``entry_hash`` covers the
whole record and ``prev_hash`` covers its predecessor. That is only lawful while no signed
checkpoint names a legacy head: a checkpoint is the human's published anchor, and rewriting
the bytes beneath it is the rollback the checkpoint exists to expose. A chain whose own
legacy links do not verify is never laundered into one that does. The login itself is the
operator's assertion, supplied at the command line and recorded in the journal, and it is
no weaker than the capture path that reads the same value from the invoking session.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import _findings
from tools.attest import canonical
from tools.feedback import LOGIN

if TYPE_CHECKING:
    from tools import integrity
else:
    sys.modules.setdefault("_findings", _findings)
    from tools import integrity

__all__ = [
    "CHAIN_PATHS",
    "CHECKPOINT_PATHS",
    "checkpointed_roots",
    "legacy_heads",
    "rewrite_legacy_chain",
    "valid_login",
]

CHAIN_PATHS: Final = tuple(
    f"./{integrity.HARNESS_ROOTS[harness]}/{integrity.FEEDBACK_CHAIN}"
    for harness in integrity.HARNESS_DIRS
)
CHECKPOINT_PATHS: Final = {
    chain: f"./{integrity.HARNESS_ROOTS[harness]}/{integrity.FEEDBACK_CHECKPOINTS[harness]}"
    for chain, harness in zip(CHAIN_PATHS, integrity.HARNESS_DIRS, strict=True)
}
WRITER_OBJECT_FIELDS: Final = frozenset({"git_sha", "model_lineage", "runtime"})
LEGACY_FIELDS: Final = integrity.CHAIN_FIELDS - {"github_id"}


def valid_login(value: str | None) -> bool:
    return value is not None and value != "unattributed" and LOGIN.fullmatch(value) is not None


def _writer(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    if (
        isinstance(value, dict)
        and set(value) == WRITER_OBJECT_FIELDS
        and all(isinstance(item, str) and item for item in value.values())
    ):
        return f"{value['runtime']}/{value['model_lineage']}@{value['git_sha']}"
    return None


def _parse(document: bytes) -> tuple[list[dict[str, object]], str | None]:
    try:
        text = document.decode("utf-8")
    except UnicodeDecodeError:
        return [], "feedback chain is not UTF-8"
    entries: list[dict[str, object]] = []
    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            parsed = canonical.parse_json(raw)
        except canonical.CanonicalizationError:
            return [], f"line {number} is not JSON"
        if not isinstance(parsed, dict):
            return [], f"line {number} is not a JSON object"
        entries.append(dict(parsed))
    return entries, None


def rewrite_legacy_chain(document: bytes, github_id: str) -> tuple[bytes | None, str | None]:
    """Return ``(replacement, None)`` for a legacy chain, ``(None, None)`` for a current one.

    A chain that is neither, or that cannot be rewritten without laundering, returns
    ``(None, reason)`` and the caller holds.
    """

    entries, failure = _parse(document)
    if failure is not None:
        return None, failure
    if not entries:
        return None, None
    legacy = [set(entry) == LEGACY_FIELDS for entry in entries]
    if not any(legacy):
        return None, None
    prev_hash = integrity.CHAIN_GENESIS
    rewritten: list[dict[str, object]] = []
    new_prev = integrity.CHAIN_GENESIS
    for number, (entry, is_legacy) in enumerate(zip(entries, legacy, strict=True), start=1):
        if not is_legacy and set(entry) != integrity.CHAIN_FIELDS:
            return (
                None,
                f"line {number} carries a field set outside the legacy and closed schemas",
            )
        if entry.get("seq") != number:
            return None, f"line {number} carries seq {entry.get('seq')!r}"
        if entry.get("prev_hash") != prev_hash or entry.get("entry_hash") != integrity.chain_digest(
            entry
        ):
            return None, f"line {number} does not link; a broken legacy chain is never rewritten"
        prev_hash = str(entry["entry_hash"])
        writer = _writer(entry.get("writer"))
        if writer is None:
            return None, f"line {number} carries a writer shape no migration recognizes"
        body = {key: value for key, value in entry.items() if key != "entry_hash"}
        body["writer"] = writer
        body["github_id"] = github_id
        body["prev_hash"] = new_prev
        body["entry_hash"] = integrity.chain_digest(body)
        new_prev = str(body["entry_hash"])
        rewritten.append(body)
    lines = [
        canonical.canonicalize(entry).decode("utf-8").removesuffix("\n") for entry in rewritten
    ]
    return ("\n".join(lines) + "\n").encode("utf-8"), None


def checkpointed_roots(log: bytes | None) -> set[str]:
    """Every chain head a checkpoint log has published."""

    if log is None:
        return set()
    try:
        text = log.decode("utf-8")
    except UnicodeDecodeError:
        return {"unreadable"}
    return {
        stripped.partition(":")[2].strip()
        for line in text.splitlines()
        if (stripped := line.strip()).startswith("- root:")
    }


def legacy_heads(document: bytes) -> set[str]:
    """Every entry hash the legacy chain carries, for matching against a checkpoint log."""

    entries, failure = _parse(document)
    if failure is not None:
        return set()
    return {
        str(entry["entry_hash"]) for entry in entries if isinstance(entry.get("entry_hash"), str)
    }
