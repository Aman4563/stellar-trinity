"""Pure validation of feedback documents, using the integrity verifier's byte grammar."""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from tools import _findings
from tools.attest import canonical

if TYPE_CHECKING:
    from tools import integrity
else:
    sys.modules.setdefault("_findings", _findings)
    from tools import integrity

__all__ = ["BROKEN", "ROLLED_BACK", "FeedbackError", "Head", "integrity", "walk_documents"]

BROKEN: Final = "FEEDBACK_CHAIN_BROKEN"
ROLLED_BACK: Final = "FEEDBACK_HEAD_ROLLED_BACK"


class FeedbackError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Head:
    seq: int
    entry_hash: str
    chain: str
    ledger: str


def walk_documents(chain: str, ledger: str | None, log: str) -> Head:
    """Walk a chain, its ledger, and its checkpoint log to the head they agree on.

    ``ledger`` is ``None`` only for a frozen pre-namespace chain at a harness root, whose
    ledger was hand-written before the one-record-per-line grammar existed and whose record
    digests therefore cannot be re-derived. The gate never re-derives them for any chain, so
    holding that chain to the gate's own rule is compatibility rather than grandfathering.
    """

    findings, head = integrity.walk_chain_document(Path(integrity.FEEDBACK_CHAIN), chain.encode())
    if findings or head is None:
        raise FeedbackError(BROKEN, "feedback chain failed the verifier walk")
    entries = [canonical.parse_json(line) for line in chain.splitlines() if line.strip()]
    records = [] if ledger is None else ledger.splitlines()
    if ledger is not None and len(records) != len(entries):
        raise FeedbackError(BROKEN, "ledger and chain lengths differ")
    for row, entry in zip(records, entries, strict=ledger is not None):
        record = canonical.parse_json(row.removeprefix("- "))
        if not isinstance(record, dict) or not isinstance(entry, dict):
            raise FeedbackError(BROKEN, "ledger record is not an object")
        verbatim = record.get("verbatim")
        if (
            not isinstance(verbatim, str)
            or canonical.canonical_sha256(record) != entry["record_sha256"]
            or hashlib.sha256(verbatim.encode()).hexdigest() != entry["verbatim_sha256"]
            or record.get("feedback_id") != entry["feedback_id"]
            or record.get("chain_seq") != entry["seq"]
        ):
            raise FeedbackError(BROKEN, "ledger bytes do not match their chain record")
    roots = [
        line.partition(":")[2].strip()
        for line in log.splitlines()
        if line.strip().startswith("- root:")
    ]
    hashes = [entry["entry_hash"] for entry in entries if isinstance(entry, dict)]
    if roots and roots[-1] not in hashes:
        raise FeedbackError(ROLLED_BACK, "latest published checkpoint is outside this chain")
    return Head(*head, chain, ledger or "")
