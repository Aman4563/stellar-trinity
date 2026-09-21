"""Sabotage sentinel: a hash-chained ledger of intent-class gate refusals and their alerts.

The parent gate (``integrity.py json parent``) already refuses ninety-odd conditions. Most of
them are sloppiness. A few carry evidence of intent: a self-signed approval, a disposition line
that says SHIP while the machine says BLOCK, an instrument that cannot fire by construction, a
ledger head that moved backwards. This module maps that subset onto a closed ``SAB_``
vocabulary, appends every occurrence to ``.sentinel/attempts.jsonl`` under the parent root as a
canonical-JSON hash chain, and, when attempts repeat inside the rolling window, appends an alert
to ``.sentinel/alerts.jsonl`` on a chain of its own. An uncleared alert is the gate refusal
``SAB_REPEATED_ATTEMPT``, which caps the disposition at BLOCK until a principal distinct from
the actor signs a clearance under ``.sentinel/clearances/<alert entry hash>.json.dsse``.

Every ``gate.py`` moment appends here, the pre-push hook's ``--check`` pass included: check
mode writes no receipt and mints no disposition record, but a sabotage-class refusal it
observes is the same observation the report moment would make and lands in the ledger under
the same per-commit attempt identity, so one commit is one attempt however many moments run
against it.

The local ledger is deletable by the operator it watches. The record that counts is the one
continuous integration re-derives on an org-owned runner from the pushed bytes; see
``templates/SENTINEL.md`` for the trust boundary.

An alert is a claim about the attempts ledger, never a fact of its own. Every reader re-derives
it under the repeat rule in force: an alert that is uncleared and still supported *stands* and
caps the disposition, an alert the ledger no longer supports is *superseded* history that caps
nothing, and a *cleared* alert is closed. A standing refusal names the runs it counted and who
can clear it, or why nobody can, so the refusal carries its own arithmetic and its own way out.

Usage::

    python3 tools/sentinel.py record <root> [--findings findings.json] [--run-id X] [--ci]
                                            [--changed-paths file]
    python3 tools/sentinel.py verify <root>
    python3 tools/sentinel.py clear <root> --alert <entry-hash> --key ./private-key
                                           [--reason TEXT] [--stream RUN]
    python3 tools/sentinel.py status <root>

Exit codes: ``record`` returns 3 when any sabotage-class refusal was recorded; ``verify`` and
``status`` return 1 on a broken or rolled-back chain or a standing alert, and 0 when every
alert is cleared or superseded, exactly as the gate decides; ``clear`` returns 1 when the
clearance is refused.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Literal, cast


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING:
    from tools._findings import Finding, FindingJson, Severity
    from tools.attest import canonical as attest_canonical
    from tools.attest import dsse as attest_dsse
    from tools.attest import trustroot as attest_trustroot
    from tools.attest.backend import SignatureBackend, SignatureBackendError
    from tools.attest.backend_ssh import SshKeygenBackend
    from tools.incident_probe import GATE_INVOCATIONS
    from tools.layout import (
        PARENT_LAYOUT_BOUNDARY_LEAK,
        PARENT_LAYOUT_PARENT_TRACKS_BUNDLE,
        PARENT_LAYOUT_SHARED_REMOTE,
        PARENT_LAYOUT_SYMLINK,
        PARENT_LAYOUT_UNKNOWN_SUBMODULE,
    )
    from tools.project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
    from tools.sabotage import SAB_SENTINEL_CLEARANCE_UNSIGNED, inert_functions
else:
    try:
        from tools._findings import Finding, FindingJson, Severity
        from tools.attest import canonical as attest_canonical
        from tools.attest import dsse as attest_dsse
        from tools.attest import trustroot as attest_trustroot
        from tools.attest.backend import SignatureBackend, SignatureBackendError
        from tools.attest.backend_ssh import SshKeygenBackend
        from tools.incident_probe import GATE_INVOCATIONS
        from tools.layout import (
            PARENT_LAYOUT_BOUNDARY_LEAK,
            PARENT_LAYOUT_PARENT_TRACKS_BUNDLE,
            PARENT_LAYOUT_SHARED_REMOTE,
            PARENT_LAYOUT_SYMLINK,
            PARENT_LAYOUT_UNKNOWN_SUBMODULE,
        )
        from tools.project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
        from tools.sabotage import SAB_SENTINEL_CLEARANCE_UNSIGNED, inert_functions
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from _findings import Finding, FindingJson, Severity
        from attest import canonical as attest_canonical
        from attest import dsse as attest_dsse
        from attest import trustroot as attest_trustroot
        from attest.backend import SignatureBackend, SignatureBackendError
        from attest.backend_ssh import SshKeygenBackend
        from incident_probe import GATE_INVOCATIONS
        from layout import (
            PARENT_LAYOUT_BOUNDARY_LEAK,
            PARENT_LAYOUT_PARENT_TRACKS_BUNDLE,
            PARENT_LAYOUT_SHARED_REMOTE,
            PARENT_LAYOUT_SYMLINK,
            PARENT_LAYOUT_UNKNOWN_SUBMODULE,
        )
        from project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
        from sabotage import SAB_SENTINEL_CLEARANCE_UNSIGNED, inert_functions

ATTEMPT_SCHEMA_V1 = "trinity.sentinel-attempt/v1"
ATTEMPT_SCHEMA_V2 = "trinity.sentinel-attempt/v2"
SCHEMA = ATTEMPT_SCHEMA_V2
ACCEPTED_ATTEMPT_SCHEMAS = frozenset({ATTEMPT_SCHEMA_V1, ATTEMPT_SCHEMA_V2})
ALERT_SCHEMA_V2 = "trinity.sentinel-alert/v2"
SENTINEL_DIRECTORY = Path(".sentinel")
LEDGER_PATH = SENTINEL_DIRECTORY / "attempts.jsonl"
HEAD_PATH = SENTINEL_DIRECTORY / "head.json"
ALERTS_PATH = SENTINEL_DIRECTORY / "alerts.jsonl"
ALERTS_HEAD_PATH = SENTINEL_DIRECTORY / "alerts-head.json"
CLEARANCES_DIR = SENTINEL_DIRECTORY / "clearances"
CHAIN_GENESIS = "0" * 64
DEFAULT_WINDOW_DAYS = 30
DEFAULT_THRESHOLD = 5
GIT_TIMEOUT_SECONDS = 10.0
GIT_SSH_NAMESPACE = "git"
ALLOWED_SIGNERS_PATH = ".memory/allowed_signers"
TRUST_ROOT_PATH = ".memory/roots.yaml"
TRUSTED_ROOT_VERSION_PATH = ".memory/trusted-root-version"
STATUS_TAIL = 10
EXIT_RECORDED = 3
EXIT_REFUSED = 1
LOCK_PATH = SENTINEL_DIRECTORY / "ledger.lock"
QUARANTINE_DIRECTORY = SENTINEL_DIRECTORY / "quarantine"
STREAMS_DIRECTORY = SENTINEL_DIRECTORY / "streams"
_STREAM_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")


@dataclass(frozen=True, slots=True)
class Layout:
    """Where one sentinel stream keeps its ledgers, heads, clearances, and quarantine.

    The legacy stream is ``.sentinel/`` itself; a run stream is ``.sentinel/streams/<run>/``
    with the same file names, so every clone appends to its own chain and a merge is a
    union of streams rather than a broken chain.
    """

    directory: Path
    ledger: Path
    head: Path
    alerts: Path
    alerts_head: Path
    clearances: Path
    lock: Path
    quarantine: Path


def layout(root: Path, stream: str | None = None) -> Layout:
    if stream is None:
        directory = root / SENTINEL_DIRECTORY
    else:
        if _STREAM_NAME.fullmatch(stream) is None or ".." in stream:
            raise ValueError(f"stream name {stream!r} is outside the closed stream grammar")
        directory = root / STREAMS_DIRECTORY / stream
    return Layout(
        directory=directory,
        ledger=directory / LEDGER_PATH.name,
        head=directory / HEAD_PATH.name,
        alerts=directory / ALERTS_PATH.name,
        alerts_head=directory / ALERTS_HEAD_PATH.name,
        clearances=directory / CLEARANCES_DIR.name,
        lock=directory / LOCK_PATH.name,
        quarantine=directory / QUARANTINE_DIRECTORY.name,
    )


def stream_names(root: Path) -> list[str]:
    """Every run stream on disk, sorted; the legacy stream is never listed."""
    directory = root / STREAMS_DIRECTORY
    if not directory.is_dir():
        return []
    return sorted(
        path.name
        for path in directory.iterdir()
        if path.is_dir() and not path.is_symlink() and _STREAM_NAME.fullmatch(path.name)
    )


def all_attempts(root: Path) -> list[Attempt]:
    """The union of every readable stream's attempts in capture order, for repeat detection."""
    out: list[Attempt] = []
    for stream in (None, *stream_names(root)):
        attempts, defect = read_ledger(layout(root, stream).ledger)
        if defect is None:
            out += attempts
    return sorted(out, key=lambda item: (item.captured_at, item.seq))


_flock: Callable[[int, int], None] | None
_lock_exclusive: int | None
try:
    from fcntl import LOCK_EX as _PLATFORM_LOCK_EXCLUSIVE
    from fcntl import flock as _platform_flock
except ImportError:  # pragma: no cover - the trusted workflow requires Unix
    _flock = None
    _lock_exclusive = None
else:
    _flock = _platform_flock
    _lock_exclusive = _PLATFORM_LOCK_EXCLUSIVE

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
# A headline claims a disposition only when the disposition word opens it, after any emoji,
# bold markers, or code ticks. "SHIP is unreachable" inside a HOLD line is not a claim.
_SHIP_TOKEN = re.compile(r"^[^A-Za-z0-9]*SHIP(?::INFERRED)?(?![A-Z_:])")
_CURRENT_TOKEN = re.compile(r"^[^A-Za-z0-9]*CURRENT(?![A-Z_:])")
_H2 = re.compile(r"^##\s+(.+?)\s*$")
_WORKFLOW_ROOT = ".github/workflows/"
_OWNERSHIP_SURFACES = (".github/CODEOWNERS", "CODEOWNERS")
_HARNESS_ROOTS = (".audit", ".seed")
_REPORT_TOKENS: dict[str, re.Pattern[str]] = {
    "VERDICT.md": _SHIP_TOKEN,
    "EDICT.md": _SHIP_TOKEN,
    "DIRECTIVE.md": _CURRENT_TOKEN,
}


class SabotageCode(StrEnum):
    """Closed vocabulary of intent-class refusals."""

    SAB_SELF_APPROVAL = "SAB_SELF_APPROVAL"
    SAB_STALE_DIGEST_REUSE = "SAB_STALE_DIGEST_REUSE"
    SAB_DISPOSITION_FORGED = "SAB_DISPOSITION_FORGED"
    SAB_INERT_INSTRUMENT = "SAB_INERT_INSTRUMENT"
    SAB_DIRTY_TREE_CLAIMED_CLEAN = "SAB_DIRTY_TREE_CLAIMED_CLEAN"
    SAB_SUBMODULE_TAMPERED = "SAB_SUBMODULE_TAMPERED"
    SAB_AGENT_WROTE_HUMAN_ROOT = "SAB_AGENT_WROTE_HUMAN_ROOT"
    SAB_BUNDLE_MUTATED_AFTER_AUDIT = "SAB_BUNDLE_MUTATED_AFTER_AUDIT"
    SAB_EXPORT_WITHOUT_RECEIPT = "SAB_EXPORT_WITHOUT_RECEIPT"
    SAB_LEDGER_ROLLBACK = "SAB_LEDGER_ROLLBACK"
    SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS = "SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS"
    SAB_AUTHOR_SPOOF = "SAB_AUTHOR_SPOOF"
    SAB_REPEATED_ATTEMPT = "SAB_REPEATED_ATTEMPT"


class SentinelFailureReason(StrEnum):
    """Closed failure vocabulary of the sentinel itself."""

    SENTINEL_CHAIN_BROKEN = "SENTINEL_CHAIN_BROKEN"
    SENTINEL_CHAIN_ROLLBACK = "SENTINEL_CHAIN_ROLLBACK"


WEIGHTS: dict[SabotageCode, int] = {
    SabotageCode.SAB_SELF_APPROVAL: 3,
    SabotageCode.SAB_STALE_DIGEST_REUSE: 3,
    SabotageCode.SAB_DISPOSITION_FORGED: 3,
    SabotageCode.SAB_INERT_INSTRUMENT: 2,
    SabotageCode.SAB_DIRTY_TREE_CLAIMED_CLEAN: 2,
    SabotageCode.SAB_SUBMODULE_TAMPERED: 3,
    SabotageCode.SAB_AGENT_WROTE_HUMAN_ROOT: 2,
    SabotageCode.SAB_BUNDLE_MUTATED_AFTER_AUDIT: 3,
    SabotageCode.SAB_EXPORT_WITHOUT_RECEIPT: 3,
    SabotageCode.SAB_LEDGER_ROLLBACK: 3,
    SabotageCode.SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS: 3,
    SabotageCode.SAB_AUTHOR_SPOOF: 2,
    # The highest weight: an uncleared alert is the ledger speaking for itself.
    SabotageCode.SAB_REPEATED_ATTEMPT: 4,
}

# Codes that describe a state of the tree rather than an act of the operator. An inert
# instrument is re-observed by every gate run until someone builds it, so counting each
# observation as a fresh attempt turned an unfinished scaffold into a block that finishing the
# work could not lift and its sole operator could not clear. These still reach the ledger and
# still refuse the gate on their own; they never feed the repeat counter.
STATE_CODES: frozenset[SabotageCode] = frozenset({SabotageCode.SAB_INERT_INSTRUMENT})

# Existing gate refusal codes that carry evidence of intent, mapped to the SAB vocabulary.
# Sloppiness codes (missing, unreadable, malformed) are deliberately absent and never count.
FINDING_CODE_MAP: dict[str, SabotageCode] = {
    "APPROVAL_PRODUCER_IS_APPROVER": SabotageCode.SAB_SELF_APPROVAL,
    "APPROVAL_SIGNER_UNAUTHORIZED": SabotageCode.SAB_SELF_APPROVAL,
    "APPROVAL_SIGNER_REVOKED": SabotageCode.SAB_SELF_APPROVAL,
    "APPROVAL_DIGEST_MISMATCH": SabotageCode.SAB_STALE_DIGEST_REUSE,
    "WORK_DIFFERENTIAL_DIGEST_MISMATCH": SabotageCode.SAB_DIRTY_TREE_CLAIMED_CLEAN,
    "HUMAN_ONLY_INPUT_WORKTREE_UNATTRIBUTED": SabotageCode.SAB_DIRTY_TREE_CLAIMED_CLEAN,
    "TRINITY_FRESHNESS_DIVERGED": SabotageCode.SAB_SUBMODULE_TAMPERED,
    "TRINITY_FRESHNESS_LOCALLY_MODIFIED": SabotageCode.SAB_SUBMODULE_TAMPERED,
    "TRINITY_SUBMODULE_REMOTE_CHANGED": SabotageCode.SAB_SUBMODULE_TAMPERED,
    PARENT_LAYOUT_UNKNOWN_SUBMODULE: SabotageCode.SAB_SUBMODULE_TAMPERED,
    PARENT_LAYOUT_SHARED_REMOTE: SabotageCode.SAB_SUBMODULE_TAMPERED,
    PARENT_LAYOUT_PARENT_TRACKS_BUNDLE: SabotageCode.SAB_SUBMODULE_TAMPERED,
    PARENT_LAYOUT_BOUNDARY_LEAK: SabotageCode.SAB_SUBMODULE_TAMPERED,
    PARENT_LAYOUT_SYMLINK: SabotageCode.SAB_SUBMODULE_TAMPERED,
    # Only a crossed or collapsed layout boundary counts. The seven sloppiness layout codes
    # are deliberately absent: an incomplete or retired registration is the unfinished
    # scaffold every parent carries until genesis completes, and an absence is never
    # evidence of intent.
    "HUMAN_ONLY_INPUT_AGENT_COMMIT": SabotageCode.SAB_AGENT_WROTE_HUMAN_ROOT,
    "BUNDLE_TRUTH_REGEN_MISMATCH": SabotageCode.SAB_BUNDLE_MUTATED_AFTER_AUDIT,
    "BUNDLE_MANIFEST_SIGNATURE_INVALID": SabotageCode.SAB_BUNDLE_MUTATED_AFTER_AUDIT,
    "RELEASE_EXPORT_MISMATCH": SabotageCode.SAB_BUNDLE_MUTATED_AFTER_AUDIT,
    "RELEASE_ORACLE_RECEIPT_MISSING": SabotageCode.SAB_EXPORT_WITHOUT_RECEIPT,
    "RELEASE_ORACLE_RECEIPT_INVALID": SabotageCode.SAB_EXPORT_WITHOUT_RECEIPT,
    "RELEASE_DISPOSITION_UNBOUND": SabotageCode.SAB_EXPORT_WITHOUT_RECEIPT,
    "CHECKPOINT_HEAD_ROLLED_BACK": SabotageCode.SAB_LEDGER_ROLLBACK,
    # LEDGER_CHECKPOINT_CHAIN_INVALID is deliberately absent: it covers a missing, empty, or
    # malformed checkpoint log, which every project carries until checkpoint signing lands,
    # and an absence is never evidence of a rollback. Only CHECKPOINT_HEAD_ROLLED_BACK, a
    # head that moved backwards against a recorded one, counts.
    "SENTINEL_CHAIN_BROKEN": SabotageCode.SAB_LEDGER_ROLLBACK,
    "SENTINEL_CHAIN_ROLLBACK": SabotageCode.SAB_LEDGER_ROLLBACK,
    "AUTHOR_SPOOF": SabotageCode.SAB_AUTHOR_SPOOF,
    # Codes emitted by tools/sabotage.py and tools/pipeline.py, folded onto the
    # closed vocabulary so a refusal from either module reaches the ledger.
    "SAB_DISPOSITION_UNBOUND": SabotageCode.SAB_DISPOSITION_FORGED,
    "SAB_DISPOSITION_FORGED": SabotageCode.SAB_DISPOSITION_FORGED,
    "SAB_INERT_INSTRUMENT": SabotageCode.SAB_INERT_INSTRUMENT,
    "SAB_AUDIT_UNCOMMITTED": SabotageCode.SAB_DIRTY_TREE_CLAIMED_CLEAN,
    "SAB_DIRTY_TREE": SabotageCode.SAB_DIRTY_TREE_CLAIMED_CLEAN,
    "SAB_SUBMODULE_REMOTE": SabotageCode.SAB_SUBMODULE_TAMPERED,
    "SAB_SUBMODULE_OFF_MAIN": SabotageCode.SAB_SUBMODULE_TAMPERED,
    "SAB_TYPED_SIGNOFF": SabotageCode.SAB_SELF_APPROVAL,
    # D2: vocabulary and weights stay closed; a typed clearance is self-approval class.
    SAB_SENTINEL_CLEARANCE_UNSIGNED: SabotageCode.SAB_SELF_APPROVAL,
    "SAB_WORKFLOW_TAMPER": SabotageCode.SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS,
    # SAB_WORKFLOW_TAMPER_SUSPECT is deliberately absent: a co-edit with no bypass and no
    # forged SHIP is a HOLD the actor closes with split commits, never intent evidence.
    "PIPELINE_SEALED_MUTATED": SabotageCode.SAB_BUNDLE_MUTATED_AFTER_AUDIT,
    "PIPELINE_UNSEALED_AUDIT": SabotageCode.SAB_BUNDLE_MUTATED_AFTER_AUDIT,
    # Emitted by this module from an uncleared alert. It maps onto itself so the vocabulary
    # stays closed, and ``record`` never re-enters it, because an alert is derived from the
    # ledger and must not feed the ledger that raised it.
    "SAB_REPEATED_ATTEMPT": SabotageCode.SAB_REPEATED_ATTEMPT,
}

RECORD_FIELDS = frozenset(
    {
        "actor",
        "captured_at",
        "code",
        "entry_hash",
        "evidence_digest",
        "findings",
        "git_sha",
        "previous_hash",
        "repo",
        "run_id",
        "schema_version",
        "seq",
        "weight",
    }
)
ACTOR_FIELDS_V1 = frozenset({"git_author", "github_login", "source"})
ACTOR_FIELDS_V2 = ACTOR_FIELDS_V1 | {"identity", "principal"}
ALERT_FIELDS_V1 = frozenset(
    {
        "actor",
        "codes",
        "entry_hash",
        "first_seq",
        "last_seq",
        "previous_hash",
        "raised_at",
        "seq",
        "threshold",
        "window_days",
    }
)
ALERT_FIELDS_V2 = ALERT_FIELDS_V1 | {"schema_version", "repo", "attempts"}
ALERT_FIELDS = ALERT_FIELDS_V2
CLEARANCE_PAYLOAD_TYPE = "application/vnd.trinity.sentinel-clearance+json"
CLEARANCE_SCHEMA = "trinity.sentinel-clearance/v1"
SENTINEL_CLEARER_ROLE = "sentinel_clearer"
CLEARANCE_FIELDS = frozenset(
    {"alert_entry_hash", "attempts", "cleared_at", "reason", "repo", "schema", "stream"}
)

ActorSource = Literal["ci", "local"]
ActorIdentity = Literal["verified", "claimed", "ci"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Actor:
    git_author: str
    github_login: str | None
    source: ActorSource
    identity: ActorIdentity
    principal: str | None

    @classmethod
    def verified(cls, *, git_author: str, github_login: str | None, principal: str) -> Actor:
        return cls(
            git_author=git_author,
            github_login=github_login,
            source="local",
            identity="verified",
            principal=principal,
        )

    @classmethod
    def claimed(cls, *, git_author: str, github_login: str | None) -> Actor:
        return cls(
            git_author=git_author,
            github_login=github_login,
            source="local",
            identity="claimed",
            principal=f"unverified:{git_author}",
        )

    @classmethod
    def for_ci(cls, *, git_author: str, github_login: str | None) -> Actor:
        if not github_login:
            return replace(
                cls.claimed(git_author=git_author, github_login=github_login), source="ci"
            )
        return cls(
            git_author=git_author,
            github_login=github_login,
            source="ci",
            identity="ci",
            principal=f"github:{github_login}",
        )

    def shares_identity(self, other: Actor) -> bool:
        return self.identity == other.identity and (
            (self.principal is not None and self.principal == other.principal)
            or (
                self.identity == "ci"
                and self.github_login is not None
                and self.github_login == other.github_login
            )
        )


@dataclass(frozen=True, slots=True)
class Attempt:
    seq: int
    code: SabotageCode
    weight: int
    actor: Actor
    captured_at: datetime
    git_sha: str
    repo: str
    run_id: str
    evidence_digest: str
    findings: tuple[FindingJson, ...]
    previous_hash: str
    entry_hash: str
    schema_version: str


@dataclass(frozen=True, slots=True)
class Classified:
    code: SabotageCode
    findings: tuple[FindingJson, ...]


@dataclass(frozen=True, slots=True)
class Alert:
    """One repeat inside the rolling window, raised once per actor until cleared."""

    seq: int
    actor: Actor
    codes: tuple[str, ...]
    window_days: int
    threshold: int
    first_seq: int
    last_seq: int
    raised_at: datetime
    previous_hash: str
    entry_hash: str
    repo: str | None
    attempts: tuple[str, ...]
    schema_version: str = ALERT_SCHEMA_V2


def format_time(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp is not an RFC 3339 UTC instant")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def canonical_line(value: attest_canonical.JSONValue) -> str:
    return attest_canonical.canonicalize(value).decode("utf-8").removesuffix("\n")


def evidence_digest(findings: Sequence[FindingJson]) -> str:
    payload: list[attest_canonical.JSONValue] = [
        {
            "code": item["code"],
            "line": item["line"],
            "message": item["message"],
            "path": item["path"],
            "severity": item["severity"],
        }
        for item in findings
    ]
    return hashlib.sha256(attest_canonical.canonicalize(payload)).hexdigest()


def _record_body(attempt: Attempt) -> dict[str, attest_canonical.JSONValue]:
    findings: list[attest_canonical.JSONValue] = [
        {
            "code": item["code"],
            "line": item["line"],
            "message": item["message"],
            "path": item["path"],
            "severity": item["severity"],
        }
        for item in attempt.findings
    ]
    actor: dict[str, attest_canonical.JSONValue] = {
        "git_author": attempt.actor.git_author,
        "github_login": attempt.actor.github_login,
        "source": attempt.actor.source,
    }
    if attempt.schema_version != ATTEMPT_SCHEMA_V1:
        actor.update(identity=attempt.actor.identity, principal=attempt.actor.principal)
    return {
        "actor": actor,
        "captured_at": format_time(attempt.captured_at),
        "code": str(attempt.code),
        "evidence_digest": attempt.evidence_digest,
        "findings": findings,
        "git_sha": attempt.git_sha,
        "previous_hash": attempt.previous_hash,
        "repo": attempt.repo,
        "run_id": attempt.run_id,
        "schema_version": attempt.schema_version,
        "seq": attempt.seq,
        "weight": attempt.weight,
    }


def entry_hash_for(body: dict[str, attest_canonical.JSONValue]) -> str:
    """Digest a record body that carries every field except ``entry_hash``.

    The body already carries ``previous_hash``, so the chain links exactly as the feedback
    chain does: ``sha256(canonical(record minus entry_hash))``.
    """
    return hashlib.sha256(attest_canonical.canonicalize(body)).hexdigest()


def render_record(attempt: Attempt) -> str:
    body = _record_body(attempt)
    body["entry_hash"] = attempt.entry_hash
    return canonical_line(body)


def _finding_json(item: object) -> FindingJson | None:
    if not isinstance(item, dict):
        return None
    code = item.get("code")
    severity = item.get("severity")
    path = item.get("path")
    line = item.get("line")
    message = item.get("message")
    if not isinstance(code, str) or not isinstance(severity, str) or not isinstance(path, str):
        return None
    if not isinstance(message, str):
        return None
    if line is not None and (isinstance(line, bool) or not isinstance(line, int)):
        return None
    return {"code": code, "severity": severity, "path": path, "line": line, "message": message}


def parse_findings_document(document: str | bytes) -> list[FindingJson]:
    """Parse the JSON array ``integrity.py json parent`` emits."""
    parsed = json.loads(document)
    if not isinstance(parsed, list):
        raise ValueError("findings document is not a JSON array")
    out: list[FindingJson] = []
    for index, item in enumerate(parsed):
        shaped = _finding_json(item)
        if shaped is None:
            raise ValueError(f"findings entry {index} is not a finding object")
        out.append(shaped)
    return out


# ---- classification ------------------------------------------------------------------------


def _disposition_line(text: str) -> str | None:
    lines = text.split("\n")
    for index, line in enumerate(lines):
        match = _H2.match(line)
        if match is None or match.group(1) != "Disposition":
            continue
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped:
                continue
            if _H2.match(candidate):
                return None
            return stripped
    return None


def forged_dispositions(root: Path, findings: Sequence[FindingJson]) -> list[Classified]:
    """A root report headline that claims SHIP or CURRENT while the machine gate refuses."""
    errors = tuple(item for item in findings if item["severity"] == "error")
    if not errors:
        return []
    out: list[Classified] = []
    for report, token in _REPORT_TOKENS.items():
        path = root / report
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        line = _disposition_line(text)
        if line is None or token.search(line) is None:
            continue
        witness: FindingJson = {
            "code": "DISPOSITION_CONTRADICTS_GATE",
            "severity": "error",
            "path": display_project_path(path, project_root=root),
            "line": None,
            "message": (
                f"disposition reads {line!r} while the parent gate returns "
                f"{len(errors)} error finding(s)"
            ),
        }
        out.append(Classified(SabotageCode.SAB_DISPOSITION_FORGED, (witness, *errors)))
    return out


def inert_instruments(root: Path) -> list[Classified]:
    """Instruments under the harness roots whose every return is a constant or a coverage gap."""
    witnesses: list[FindingJson] = []
    for harness in _HARNESS_ROOTS:
        base = root / harness
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue
            for name, line, reason in inert_functions(tree):
                witnesses.append(
                    {
                        "code": "INSTRUMENT_INERT",
                        "severity": "error",
                        "path": display_project_path(path, project_root=root),
                        "line": line,
                        "message": f"{name}() {reason}, so it can certify clean without testing",
                    }
                )
    if not witnesses:
        return []
    return [Classified(SabotageCode.SAB_INERT_INSTRUMENT, tuple(witnesses))]


def _invokes_a_gate(root: Path, path: str) -> bool:
    try:
        text = (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return any(token in text for token in GATE_INVOCATIONS)


def _touches_gate_surface(root: Path, changed_paths: Iterable[str]) -> list[str]:
    """Changed paths that guard the gate: its ownership rules, or a workflow that invokes it."""
    hits: list[str] = []
    for raw in changed_paths:
        path = raw.strip().removeprefix("./")
        if not path:
            continue
        if path in _OWNERSHIP_SURFACES or (
            path.startswith(_WORKFLOW_ROOT) and _invokes_a_gate(root, path)
        ):
            hits.append(path)
    return hits


def classify(
    findings: Sequence[FindingJson],
    *,
    root: Path,
    changed_paths: Sequence[str] = (),
    ci: bool = False,
) -> list[Classified]:
    """Map gate findings plus the sentinel's own predicates onto SAB codes."""
    del ci
    grouped: dict[SabotageCode, list[FindingJson]] = {}
    for item in findings:
        code = FINDING_CODE_MAP.get(item["code"])
        if code is None or code is SabotageCode.SAB_REPEATED_ATTEMPT:
            continue
        grouped.setdefault(code, []).append(item)
    out = [Classified(code, tuple(items)) for code, items in grouped.items()]
    out += forged_dispositions(root, findings)
    out += inert_instruments(root)
    hits = _touches_gate_surface(root, changed_paths)
    if out and hits:
        witness: FindingJson = {
            "code": "GATE_SURFACE_EDITED",
            "severity": "error",
            "path": hits[0],
            "line": None,
            "message": (
                "the same push edits a gate surface ("
                + ", ".join(hits)
                + ") and produces "
                + ", ".join(sorted({str(item.code) for item in out}))
            ),
        }
        out.append(Classified(SabotageCode.SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS, (witness,)))
    return out


# ---- git and actor ---------------------------------------------------------------------------


def _git(root: Path, *argv: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *argv],
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _git_bytes(root: Path, *argv: str) -> bytes | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *argv],
            capture_output=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _head_commit_object(root: Path) -> bytes | None:
    head = _git(root, "rev-parse", "HEAD")
    body = _git_bytes(root, "cat-file", "commit", "HEAD")
    if head is None or body is None:
        return None
    digest = hashlib.sha1(
        b"commit " + str(len(body)).encode() + b"\0" + body, usedforsecurity=False
    ).hexdigest()
    return body if digest == head else None


def _split_gpgsig(body: bytes) -> tuple[bytes, bytes] | None:
    headers, separator, message = body.partition(b"\n\n")
    if not separator:
        return None
    lines = headers.split(b"\n")
    positions = [index for index, line in enumerate(lines) if line.startswith(b"gpgsig ")]
    if len(positions) != 1:
        return None
    start = positions[0]
    signature = [lines[start].removeprefix(b"gpgsig ")]
    end = start + 1
    while end < len(lines) and lines[end].startswith(b" "):
        signature.append(lines[end][1:])
        end += 1
    payload = b"\n".join(lines[:start] + lines[end:]) + separator + message
    return payload, b"\n".join(signature)


def verify_head_principal(
    root: Path,
    *,
    evaluation_time: datetime,
    backend: SignatureBackend | None = None,
    allowed_signers: Path | None = None,
) -> str | None:
    signers_path = root / ALLOWED_SIGNERS_PATH if allowed_signers is None else allowed_signers
    if not signers_path.is_file():
        return None
    body = _head_commit_object(root)
    if body is None:
        return None
    split = _split_gpgsig(body)
    if split is None:
        return None
    payload, signature = split
    verifier = SshKeygenBackend(namespace=GIT_SSH_NAMESPACE) if backend is None else backend
    try:
        with tempfile.TemporaryDirectory(prefix="trinity-sentinel-") as temporary:
            signature_path = Path(temporary) / "commit.sig"
            signature_path.write_bytes(signature)
            result = verifier.verify(
                payload,
                signature_path=signature_path,
                allowed_signers_path=signers_path,
                evaluation_time=evaluation_time,
            )
    except (OSError, SignatureBackendError):
        return None
    return result.principal if result.verified and result.principal else None


def resolve_actor(
    root: Path,
    *,
    ci: bool,
    environ: Mapping[str, str] | None = None,
    evaluation_time: datetime | None = None,
    backend: SignatureBackend | None = None,
) -> Actor:
    env = os.environ if environ is None else environ
    author = _git(root, "log", "-1", "--format=%an <%ae>") or "unknown <unknown>"
    login = env.get("GITHUB_ACTOR") or None
    if ci:
        return Actor.for_ci(git_author=author, github_login=login)
    principal = verify_head_principal(
        root, evaluation_time=evaluation_time or datetime.now(UTC), backend=backend
    )
    if principal is not None:
        return Actor.verified(git_author=author, github_login=login, principal=principal)
    return Actor.claimed(git_author=author, github_login=login)


def resolve_git_sha(root: Path) -> str:
    sha = _git(root, "rev-parse", "HEAD")
    return sha if sha is not None and _HEX40.fullmatch(sha) else "0" * 40


def resolve_repo(root: Path, environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    repository = env.get("GITHUB_REPOSITORY")
    if repository:
        return repository
    return root.resolve().name


# ---- ledger ----------------------------------------------------------------------------------


def _parse_actor(value: object, *, version: str) -> Actor | None:
    if version not in (ATTEMPT_SCHEMA_V1, ATTEMPT_SCHEMA_V2, "", ALERT_SCHEMA_V2):
        return None
    legacy = version in (ATTEMPT_SCHEMA_V1, "")
    fields = ACTOR_FIELDS_V1 if legacy else ACTOR_FIELDS_V2
    if not isinstance(value, dict) or set(value) != fields:
        return None
    author = value["git_author"]
    login = value["github_login"]
    source = value["source"]
    if not isinstance(author, str) or not author:
        return None
    if login is not None and (not isinstance(login, str) or not login):
        return None
    if source not in ("ci", "local"):
        return None
    if legacy:
        return replace(Actor.claimed(git_author=author, github_login=login), source=source)
    identity = value["identity"]
    principal = value["principal"]
    if identity not in ("verified", "claimed", "ci"):
        return None
    if principal is not None and (not isinstance(principal, str) or not principal):
        return None
    return Actor(
        git_author=author,
        github_login=login,
        source=source,
        identity=identity,
        principal=principal,
    )


def _parse_attempt(entry: dict[str, object]) -> Attempt | str:
    fields = set(entry)
    if fields != RECORD_FIELDS:
        missing = sorted(RECORD_FIELDS - fields)
        unknown = sorted(fields - RECORD_FIELDS)
        return f"record fields differ from the closed schema: missing {missing}, unknown {unknown}"
    version = entry["schema_version"]
    if not isinstance(version, str) or version not in ACCEPTED_ATTEMPT_SCHEMAS:
        return f"schema_version is {version!r}, expected one of {sorted(ACCEPTED_ATTEMPT_SCHEMAS)}"
    seq = entry["seq"]
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
        return "seq is not a positive integer"
    code_raw = entry["code"]
    if not isinstance(code_raw, str) or code_raw not in SabotageCode.__members__:
        return f"code {code_raw!r} is outside the closed SAB vocabulary"
    code = SabotageCode(code_raw)
    weight = entry["weight"]
    if isinstance(weight, bool) or not isinstance(weight, int) or weight != WEIGHTS[code]:
        return f"weight for {code} must be {WEIGHTS[code]}"
    actor = _parse_actor(entry["actor"], version=version)
    if actor is None:
        return "actor is malformed"
    captured_raw = entry["captured_at"]
    if not isinstance(captured_raw, str):
        return "captured_at is not a string"
    try:
        captured_at = parse_time(captured_raw)
    except ValueError:
        return "captured_at is not an RFC 3339 UTC instant"
    for name in ("evidence_digest", "previous_hash", "entry_hash"):
        value = entry[name]
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            return f"{name} is not a lowercase hex sha-256 digest"
    git_sha = entry["git_sha"]
    if not isinstance(git_sha, str) or _HEX40.fullmatch(git_sha) is None:
        return "git_sha is not a 40-hex commit id"
    repo = entry["repo"]
    run_id = entry["run_id"]
    if not isinstance(repo, str) or not repo or not isinstance(run_id, str) or not run_id:
        return "repo and run_id must be non-empty strings"
    raw_findings = entry["findings"]
    if not isinstance(raw_findings, list):
        return "findings is not a list"
    findings: list[FindingJson] = []
    for item in raw_findings:
        shaped = _finding_json(item)
        if shaped is None:
            return "findings carries a malformed entry"
        findings.append(shaped)
    if evidence_digest(findings) != entry["evidence_digest"]:
        return "evidence_digest does not cover the recorded findings"
    return Attempt(
        seq=seq,
        code=code,
        weight=weight,
        actor=actor,
        captured_at=captured_at,
        git_sha=git_sha,
        repo=repo,
        run_id=run_id,
        evidence_digest=str(entry["evidence_digest"]),
        findings=tuple(findings),
        previous_hash=str(entry["previous_hash"]),
        entry_hash=str(entry["entry_hash"]),
        schema_version=version,
    )


def read_ledger_document(document: bytes) -> tuple[list[Attempt], str | None]:
    """Walk the chain. Returns the attempts read and the first defect, if any."""
    try:
        text = document.decode("utf-8")
    except UnicodeDecodeError:
        return [], "ledger is not UTF-8"
    attempts: list[Attempt] = []
    previous = CHAIN_GENESIS
    seq = 1
    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            parsed = attest_canonical.parse_json(raw)
        except attest_canonical.CanonicalizationError:
            return attempts, f"line {number} is not canonical JSON"
        if not isinstance(parsed, dict) or canonical_line(parsed) != raw:
            return attempts, f"line {number} is not canonical JSON"
        entry: dict[str, object] = dict(parsed)
        attempt = _parse_attempt(entry)
        if isinstance(attempt, str):
            return attempts, f"line {number}: {attempt}"
        if attempt.seq != seq:
            return attempts, f"line {number}: seq is {attempt.seq} where the chain expects {seq}"
        if attempt.previous_hash != previous:
            return attempts, f"line {number}: previous_hash does not link to the preceding line"
        body = _record_body(attempt)
        if entry_hash_for(body) != attempt.entry_hash:
            return attempts, f"line {number}: entry_hash does not cover this line"
        attempts.append(attempt)
        previous = attempt.entry_hash
        seq += 1
    return attempts, None


def read_ledger(path: Path) -> tuple[list[Attempt], str | None]:
    if not os.path.lexists(path):
        return [], None
    try:
        document = _safe_read_state_file(path)
    except (OSError, ValueError) as exc:
        return [], f"ledger is unreadable: {exc.__class__.__name__}"
    return read_ledger_document(document)


def read_head(path: Path) -> tuple[int, str] | str | None:
    """The last head this sentinel wrote, used to detect truncation between runs."""
    if not os.path.lexists(path):
        return None
    try:
        parsed = json.loads(_safe_read_state_file(path))
    except (OSError, UnicodeDecodeError, ValueError):
        return "head is unreadable or malformed"
    if not isinstance(parsed, dict) or set(parsed) != {"entry_hash", "seq"}:
        return "head fields differ from the closed schema"
    seq = parsed.get("seq")
    head = parsed.get("entry_hash")
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
        return "head seq is not a positive integer"
    if not isinstance(head, str) or _HEX64.fullmatch(head) is None:
        return "head entry_hash is not a lowercase SHA-256 digest"
    return seq, head


def write_head(path: Path, seq: int, head: str) -> None:
    _ensure_state_directory(_sentinel_root_for(path), path.parent)
    payload: attest_canonical.JSONValue = {"entry_hash": head, "seq": seq}
    _safe_write_state_file(path, attest_canonical.canonicalize(payload))


def rollback_defect(attempts: Sequence[Attempt], head: tuple[int, str] | None) -> str | None:
    if head is None:
        return None
    seq, entry_hash = head
    if seq < 1:
        return None
    if len(attempts) < seq:
        return f"ledger holds {len(attempts)} records but the recorded head is seq {seq}"
    if attempts[seq - 1].entry_hash != entry_hash:
        return f"record at seq {seq} no longer matches the recorded head"
    return None


def verify_chain(root: Path, stream: str | None = None) -> list[Finding]:
    """Refuse a broken or rolled-back attempt ledger or alert ledger of one stream."""
    paths = layout(root, stream)
    ledger = paths.ledger
    attempts, defect = read_ledger(ledger)
    if defect is not None:
        return [_chain_finding(SentinelFailureReason.SENTINEL_CHAIN_BROKEN, ledger, defect)]
    head = read_head(paths.head)
    if isinstance(head, str):
        return [_chain_finding(SentinelFailureReason.SENTINEL_CHAIN_BROKEN, ledger, head)]
    rollback = rollback_defect(attempts, head)
    if rollback is not None:
        return [_chain_finding(SentinelFailureReason.SENTINEL_CHAIN_ROLLBACK, ledger, rollback)]
    alerts_path = paths.alerts
    alerts, alert_defect = read_alerts(alerts_path)
    if alert_defect is not None:
        return [
            _chain_finding(SentinelFailureReason.SENTINEL_CHAIN_BROKEN, alerts_path, alert_defect)
        ]
    alert_head = read_head(paths.alerts_head)
    if isinstance(alert_head, str):
        return [
            _chain_finding(SentinelFailureReason.SENTINEL_CHAIN_BROKEN, alerts_path, alert_head)
        ]
    alert_rollback = alert_rollback_defect(alerts, alert_head)
    if alert_rollback is not None:
        return [
            _chain_finding(
                SentinelFailureReason.SENTINEL_CHAIN_ROLLBACK, alerts_path, alert_rollback
            )
        ]
    return []


def _chain_finding(reason: SentinelFailureReason, path: Path, detail: str) -> Finding:
    return Finding(
        reason,
        Severity.ERROR,
        display_project_path(path, project_root=_sentinel_root_for(path)),
        None,
        detail,
    )


def alert_stands(
    ledger: Sequence[Attempt],
    alert: Alert,
    *,
    window: timedelta = timedelta(days=DEFAULT_WINDOW_DAYS),
    threshold: int = DEFAULT_THRESHOLD,
) -> bool:
    """Re-derive ``alert`` from the attempts ledger under the current repeat rule.

    The attempts ledger is the source of truth and the alert is a claim about it. An alert
    raised under a superseded rule, one that related attempts by shared author or fired at a
    lower threshold, is re-derived against the same attempts it names, and it stands only
    when at least one of them is a repeat under the rule in force now. An alert the ledger
    no longer supports is history, never a live refusal, and needs no clearance.
    """
    named = alert_attempts(ledger, alert)
    return any(is_repeat(ledger, item, window=window, threshold=threshold) for item in named)


def alert_attempts(ledger: Sequence[Attempt], alert: Alert) -> list[Attempt]:
    """The attempts ``alert`` names that the ledger holds, in ledger order."""
    return [
        item
        for item in ledger
        if alert.first_seq <= item.seq <= alert.last_seq
        and str(item.code) in alert.codes
        and item.actor.shares_identity(alert.actor)
    ]


@dataclass(frozen=True, slots=True)
class AlertStanding:
    """One alert read against the ledger, the clearances, and the trust root at one instant.

    ``stands`` is true only for an alert that is uncleared and that the attempts ledger still
    supports under the rule in force; it is the one state that caps the disposition. A
    cleared alert and a superseded alert are both history. ``counted`` is the distinct run
    identities the repeat rule counted, so a reader can check the arithmetic against the
    ledger, and ``remedy`` names who can clear a standing alert or why nobody can.
    """

    alert: Alert
    status: ClearanceStatus
    stands: bool
    counted: tuple[str, ...]
    remedy: str

    @property
    def superseded(self) -> bool:
        return not self.status.cleared and not self.stands

    def summary(self) -> str:
        return (
            f"alert seq {self.alert.seq} by {self.alert.actor.git_author} over "
            f"{', '.join(self.alert.codes)} (attempts {self.alert.first_seq} to "
            f"{self.alert.last_seq} inside {self.alert.window_days} days)"
        )

    def evidence(self) -> str:
        return (
            f"counted {len(self.counted)} distinct runs at threshold {self.alert.threshold}: "
            + ", ".join(self.counted)
        )


def alert_standings(
    root: Path, stream: str | None = None, *, evaluation_time: datetime | None = None
) -> list[AlertStanding]:
    """Read every alert in ``stream`` and decide its standing; an unreadable stream is none."""
    alerts, defect = read_alerts(layout(root, stream).alerts)
    if defect is not None:
        return []
    ledger = all_attempts(root)
    instant = evaluation_time if evaluation_time is not None else datetime.now(UTC)
    out: list[AlertStanding] = []
    for alert in alerts:
        status = clearance_status(root, alert, evaluation_time=instant, stream=stream)
        stands = not status.cleared and alert_stands(ledger, alert)
        named = alert_attempts(ledger, alert)
        counted = tuple(
            f"{run_id}@{sha[:12]}" if sha else run_id
            for run_id, sha in sorted({(item.run_id, item.git_sha) for item in named})
        )
        remedy = clearer_remedy(root, alert, evaluation_time=instant) if stands else ""
        out.append(AlertStanding(alert, status, stands, counted, remedy))
    return out


def standing_alerts(
    root: Path, stream: str | None = None, *, evaluation_time: datetime | None = None
) -> list[AlertStanding]:
    """Only the alerts that cap the disposition now: uncleared and still supported."""
    return [
        item
        for item in alert_standings(root, stream, evaluation_time=evaluation_time)
        if item.stands
    ]


def repeated_attempt_findings(
    root: Path, stream: str | None = None, *, evaluation_time: datetime | None = None
) -> list[Finding]:
    """One ERROR per standing alert that no distinct principal has cleared.

    The ERROR names the runs the repeat rule counted and who can clear it, or why nobody
    can, so the refusal carries its own arithmetic and its own way out. An uncleared alert
    the attempts ledger no longer supports surfaces as an ADVISORY naming it superseded, so
    the record stays append-only while the refusal is re-derived rather than restated.
    """
    paths = layout(root, stream)
    out: list[Finding] = []
    for standing in alert_standings(root, stream, evaluation_time=evaluation_time):
        alert, status = standing.alert, standing.status
        if status.unsigned:
            typed_path = display_project_path(
                legacy_clearance_path(root, alert, stream), project_root=root
            )
            signed_path = display_project_path(
                clearance_path(root, alert, stream), project_root=root
            )
            out.append(
                Finding(
                    SAB_SENTINEL_CLEARANCE_UNSIGNED,
                    Severity.ERROR,
                    typed_path,
                    None,
                    f"alert seq {alert.seq} {alert.entry_hash}: {typed_path}: {status.detail}; "
                    f"replace it with an authorized signed clearance at {signed_path}",
                )
            )
        if status.cleared:
            continue
        if standing.superseded:
            out.append(
                Finding(
                    SabotageCode.SAB_REPEATED_ATTEMPT,
                    Severity.ADVISORY,
                    display_project_path(paths.alerts, project_root=root),
                    None,
                    f"{standing.summary()} was raised under a superseded repeat rule; "
                    "re-derived from the attempts ledger it is no repeat at threshold "
                    f"{DEFAULT_THRESHOLD} and no longer caps the disposition; it stays in the "
                    "ledger as history and needs no clearance",
                )
            )
            continue
        out.append(
            Finding(
                SabotageCode.SAB_REPEATED_ATTEMPT,
                Severity.ERROR,
                display_project_path(paths.alerts, project_root=root),
                None,
                f"{standing.summary()} stands uncleared: {status.detail}; "
                f"{standing.evidence()}; {standing.remedy}",
            )
        )
    return out


def check_sentinel_chain(root: str, evaluation_time: datetime | None = None) -> list[Finding]:
    """Parent-gate entry point: the ledgers must verify and every alert must be cleared."""
    root_path = Path(root)
    instant = evaluation_time if evaluation_time is not None else datetime.now(UTC)
    out: list[Finding] = []
    for stream in (None, *stream_names(root_path)):
        paths = layout(root_path, stream)
        present = any(
            os.path.lexists(path)
            for path in (paths.ledger, paths.head, paths.alerts, paths.alerts_head)
        )
        if not present:
            continue
        out += verify_chain(root_path, stream) + repeated_attempt_findings(
            root_path, stream, evaluation_time=instant
        )
    return out


CHECKS: list[tuple[str, Callable[[str, datetime | None], list[Finding]]]] = [
    ("check_sentinel_chain", check_sentinel_chain),
]


def append(path: Path, attempts: Sequence[Attempt]) -> None:
    _ensure_state_directory(_sentinel_root_for(path), path.parent)
    with _safe_open_state_file(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, "ab") as handle:
        for attempt in attempts:
            handle.write(render_record(attempt).encode("utf-8") + b"\n")


def _sentinel_root_for(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))  # noqa: PTH100 - lexical, never follow symlinks
    indices = [
        index for index, part in enumerate(absolute.parts) if part == SENTINEL_DIRECTORY.name
    ]
    if not indices:
        raise ValueError("sentinel state path is outside .sentinel")
    index = indices[-1]
    return Path(*absolute.parts[:index])


def _relative_state_path(root: Path, path: Path) -> tuple[Path, Path]:
    absolute_root = Path(os.path.abspath(root))  # noqa: PTH100 - lexical, never follow symlinks
    absolute_path = Path(os.path.abspath(path))  # noqa: PTH100 - lexical, never follow symlinks
    try:
        relative = absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise ValueError("sentinel state path escapes its root") from exc
    if not relative.parts or relative.parts[0] != SENTINEL_DIRECTORY.name:
        raise ValueError("sentinel state path is outside .sentinel")
    current = Path(absolute_root.anchor)
    for part in absolute_root.parts[1:]:
        current /= part
        metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"sentinel root component is a symbolic link: {current}")
    return absolute_root, relative


def _inspect_state_components(root: Path, path: Path, *, leaf_directory: bool = False) -> None:
    absolute_root, relative = _relative_state_path(root, path)
    try:
        root_metadata = os.lstat(absolute_root)
    except FileNotFoundError as exc:
        raise ValueError("sentinel root does not exist") from exc
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError("sentinel root is not a real directory")
    current = absolute_root
    for index, part in enumerate(relative.parts):
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError(f"sentinel state component is a symbolic link: {current}")
        is_leaf = index == len(relative.parts) - 1
        if is_leaf and not leaf_directory and not stat.S_ISREG(metadata.st_mode):
            raise ValueError(f"sentinel state file is not regular: {current}")
        if (not is_leaf or leaf_directory) and not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"sentinel state component is not a directory: {current}")


def _ensure_state_directory(root: Path, directory: Path) -> None:
    absolute_root, relative = _relative_state_path(root, directory)
    root_metadata = os.lstat(absolute_root)
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError("sentinel root is not a real directory")
    current = absolute_root
    for part in relative.parts:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            metadata = os.lstat(current)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ValueError(f"sentinel state directory is unsafe: {current}")


@contextlib.contextmanager
def _safe_open_state_file(path: Path, flags: int, mode: str) -> Iterator[BinaryIO]:
    root = _sentinel_root_for(path)
    _inspect_state_components(root, path)
    descriptor = os.open(path, flags | _NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, mode) as handle:
            descriptor = -1
            yield cast(BinaryIO, handle)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _safe_read_state_file(path: Path) -> bytes:
    with _safe_open_state_file(path, os.O_RDONLY, "rb") as handle:
        return handle.read()


def _safe_write_state_file(path: Path, document: bytes) -> None:
    with _safe_open_state_file(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, "wb") as handle:
        handle.write(document)


@contextlib.contextmanager
def ledger_lock(root: Path, stream: str | None = None) -> Iterator[None]:
    """Hold the Unix advisory lock for the complete ledger read-modify-write operation."""
    if _flock is None or _lock_exclusive is None:
        raise RuntimeError("sentinel ledger mutation requires Unix fcntl.flock")
    path = layout(root, stream).lock
    _ensure_state_directory(root, path.parent)
    with _safe_open_state_file(path, os.O_RDWR | os.O_CREAT, "a+b") as handle:
        _flock(handle.fileno(), _lock_exclusive)
        yield


def quarantine_files(root: Path, *paths: Path, stream: str | None = None) -> list[Path]:
    """Move corrupt forensic bytes aside without replacing or deleting them."""
    directory = layout(root, stream).quarantine
    _ensure_state_directory(root, directory)
    moved: list[Path] = []
    marker = uuid.uuid4().hex
    for path in paths:
        if not os.path.lexists(path):
            continue
        _inspect_state_components(root, path)
        destination = directory / f"{path.name}.{marker}.corrupt"
        _inspect_state_components(root, destination)
        path.replace(destination)
        moved.append(destination)
    return moved


def _merge_classified(items: Sequence[Classified]) -> list[Classified]:
    grouped: dict[SabotageCode, list[FindingJson]] = {}
    for item in items:
        grouped.setdefault(item.code, []).extend(item.findings)
    return [Classified(code, tuple(findings)) for code, findings in grouped.items()]


def record(
    root: Path,
    findings: Sequence[FindingJson],
    *,
    actor: Actor,
    run_id: str,
    git_sha: str,
    repo: str,
    now: datetime | None = None,
    changed_paths: Sequence[str] = (),
    ci: bool = False,
    stream: str | None = None,
) -> tuple[list[Attempt], list[Finding]]:
    """Classify the gate output and append one chained record per sabotage code.

    A broken or rolled-back ledger is itself recorded as ``SAB_LEDGER_ROLLBACK`` on a fresh
    chain segment, because the operator who truncated the ledger must not gain a clean start.
    ``stream`` names the run's own chain; repeats are still counted across every stream.
    """
    captured_at = now if now is not None else datetime.now(UTC)
    paths = layout(root, stream)
    ledger = paths.ledger
    with ledger_lock(root, stream):
        attempts, defect = read_ledger(ledger)
        chain_findings = verify_chain(root, stream)
        current_head = read_head(paths.head)
        if isinstance(current_head, str) or (
            isinstance(current_head, tuple) and not os.path.lexists(ledger)
        ):
            quarantine_files(root, paths.head, stream=stream)
        classified = classify(findings, root=root, changed_paths=changed_paths, ci=ci)
        if chain_findings:
            witnesses: list[FindingJson] = [
                {
                    "code": item.code,
                    "severity": "error",
                    "path": item.path,
                    "line": item.line,
                    "message": item.message,
                }
                for item in chain_findings
            ]
            classified.append(Classified(SabotageCode.SAB_LEDGER_ROLLBACK, tuple(witnesses)))
        classified = _merge_classified(classified)
        seen = {(item.repo, item.run_id, item.code) for item in attempts}
        classified = [item for item in classified if (repo, run_id, item.code) not in seen]
        if not classified:
            return [], chain_findings
        if defect is not None:
            quarantine_files(root, ledger, paths.head, stream=stream)
            attempts = []
        previous = attempts[-1].entry_hash if attempts else CHAIN_GENESIS
        seq = attempts[-1].seq + 1 if attempts else 1
        new: list[Attempt] = []
        for item in classified:
            digest = evidence_digest(item.findings)
            draft = Attempt(
                seq=seq,
                code=item.code,
                weight=WEIGHTS[item.code],
                actor=actor,
                captured_at=captured_at,
                git_sha=git_sha,
                repo=repo,
                run_id=run_id,
                evidence_digest=digest,
                findings=item.findings,
                previous_hash=previous,
                entry_hash="",
                schema_version=ATTEMPT_SCHEMA_V2,
            )
            entry_hash = entry_hash_for(_record_body(draft))
            attempt = replace(draft, entry_hash=entry_hash)
            new.append(attempt)
            previous = entry_hash
            seq += 1
        append(ledger, new)
        write_head(paths.head, new[-1].seq, new[-1].entry_hash)
        others = [
            item
            for item in all_attempts(root)
            if item.entry_hash not in {n.entry_hash for n in new}
        ]
        universe = sorted([*others, *new], key=lambda item: (item.captured_at, item.seq))
        raise_alerts(root, universe, new, now=captured_at, stream=stream)
        return new, chain_findings


# ---- repeat detection ------------------------------------------------------------------------


def is_repeat(
    ledger: Sequence[Attempt],
    new: Attempt,
    *,
    window: timedelta = timedelta(days=DEFAULT_WINDOW_DAYS),
    threshold: int = DEFAULT_THRESHOLD,
) -> bool:
    """True when ``new`` is the ``threshold``-th attempt carrying its SAB code in the window.

    Only the code relates attempts. Sharing an author is not evidence of intent, and relating
    on it turned two unrelated refusals by one person into a block nobody on a small team could
    clear. Distinct ``(repo, run_id)`` identities are counted, so retries, preflight/report
    passes, and multiple codes emitted by one run are one attempt for repetition purposes. A
    ``STATE_CODES`` member is never a repeat: it is one condition of the tree re-observed by
    every run, not an act repeated by an operator.
    """
    if new.code in STATE_CODES:
        return False
    start = new.captured_at - window
    in_window = [
        item
        for item in ledger
        if start <= item.captured_at <= new.captured_at
        and (item.repo, item.run_id) != (new.repo, new.run_id)
    ]
    related_runs = {(item.repo, item.run_id) for item in in_window if item.code == new.code}
    return len(related_runs) + 1 >= threshold


def repeats(
    ledger: Sequence[Attempt],
    *,
    now: datetime,
    window: timedelta,
    threshold: int,
) -> list[Attempt]:
    """Every attempt in the window that is part of a repeat, newest first."""
    start = now - window
    recent = [item for item in ledger if start <= item.captured_at <= now]
    flagged = [
        item for item in recent if is_repeat(ledger, item, window=window, threshold=threshold)
    ]
    if not flagged:
        return []
    related: dict[str, Attempt] = {}
    for anchor in flagged:
        for item in recent:
            if item.code == anchor.code:
                related[item.entry_hash] = item
    return sorted(related.values(), key=lambda item: item.seq, reverse=True)


# ---- alerts and clearances ---------------------------------------------------------------


def _alert_body(alert: Alert) -> dict[str, attest_canonical.JSONValue]:
    actor: dict[str, attest_canonical.JSONValue] = {
        "git_author": alert.actor.git_author,
        "github_login": alert.actor.github_login,
        "source": alert.actor.source,
    }
    body: dict[str, attest_canonical.JSONValue] = {
        "actor": actor,
        "codes": list(alert.codes),
        "first_seq": alert.first_seq,
        "last_seq": alert.last_seq,
        "previous_hash": alert.previous_hash,
        "raised_at": format_time(alert.raised_at),
        "seq": alert.seq,
        "threshold": alert.threshold,
        "window_days": alert.window_days,
    }
    if alert.schema_version == ALERT_SCHEMA_V2:
        actor.update(identity=alert.actor.identity, principal=alert.actor.principal)
        body["schema_version"] = alert.schema_version
        body["repo"] = alert.repo
        body["attempts"] = list(alert.attempts)
    return body


def render_alert(alert: Alert) -> str:
    body = _alert_body(alert)
    body["entry_hash"] = alert.entry_hash
    return canonical_line(body)


def _parse_alert(entry: dict[str, object]) -> Alert | str:
    fields = set(entry)
    version = entry.get("schema_version", "")
    expected = ALERT_FIELDS_V2 if "schema_version" in entry else ALERT_FIELDS_V1
    if fields != expected:
        missing = sorted(expected - fields)
        unknown = sorted(fields - expected)
        return f"alert fields differ from the closed schema: missing {missing}, unknown {unknown}"
    if not isinstance(version, str) or ("schema_version" in entry and version != ALERT_SCHEMA_V2):
        return f"schema_version is {version!r}, expected {ALERT_SCHEMA_V2}"
    for name in ("seq", "first_seq", "last_seq", "threshold", "window_days"):
        value = entry[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            return f"{name} is not a positive integer"
    actor = _parse_actor(entry["actor"], version=version)
    if actor is None:
        return "actor is malformed"
    codes_raw = entry["codes"]
    if not isinstance(codes_raw, list) or not codes_raw:
        return "codes is not a non-empty list"
    codes: list[str] = []
    for code in codes_raw:
        if not isinstance(code, str) or code not in SabotageCode.__members__:
            return f"code {code!r} is outside the closed SAB vocabulary"
        codes.append(code)
    raised_raw = entry["raised_at"]
    if not isinstance(raised_raw, str):
        return "raised_at is not a string"
    try:
        raised_at = parse_time(raised_raw)
    except ValueError:
        return "raised_at is not an RFC 3339 UTC instant"
    for name in ("previous_hash", "entry_hash"):
        value = entry[name]
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            return f"{name} is not a lowercase hex sha-256 digest"
    first_seq = int(str(entry["first_seq"]))
    last_seq = int(str(entry["last_seq"]))
    if first_seq > last_seq:
        return "first_seq exceeds last_seq"
    repo: str | None = None
    attempts: list[str] = []
    if version == ALERT_SCHEMA_V2:
        repo_raw = entry["repo"]
        if not isinstance(repo_raw, str) or not repo_raw:
            return "repo is not a non-empty string"
        repo = repo_raw
        attempts_raw = entry["attempts"]
        if not isinstance(attempts_raw, list) or not attempts_raw:
            return "attempts is not a non-empty list"
        for digest in attempts_raw:
            if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
                return "attempts contains an invalid lowercase hex sha-256 digest"
            attempts.append(digest)
        if attempts != sorted(attempts):
            return "attempts is not sorted"
    return Alert(
        seq=int(str(entry["seq"])),
        actor=actor,
        codes=tuple(codes),
        window_days=int(str(entry["window_days"])),
        threshold=int(str(entry["threshold"])),
        first_seq=first_seq,
        last_seq=last_seq,
        raised_at=raised_at,
        previous_hash=str(entry["previous_hash"]),
        entry_hash=str(entry["entry_hash"]),
        schema_version=version,
        repo=repo,
        attempts=tuple(attempts),
    )


def read_alerts_document(document: bytes) -> tuple[list[Alert], str | None]:
    """Walk the alert chain. Returns the alerts read and the first defect, if any."""
    try:
        text = document.decode("utf-8")
    except UnicodeDecodeError:
        return [], "alert ledger is not UTF-8"
    alerts: list[Alert] = []
    previous = CHAIN_GENESIS
    seq = 1
    for number, raw in enumerate(text.split("\n"), start=1):
        if not raw.strip():
            continue
        try:
            parsed = attest_canonical.parse_json(raw)
        except attest_canonical.CanonicalizationError:
            return alerts, f"line {number} is not canonical JSON"
        if not isinstance(parsed, dict) or canonical_line(parsed) != raw:
            return alerts, f"line {number} is not canonical JSON"
        alert = _parse_alert(dict(parsed))
        if isinstance(alert, str):
            return alerts, f"line {number}: {alert}"
        if alert.seq != seq:
            return alerts, f"line {number}: seq is {alert.seq} where the chain expects {seq}"
        if alert.previous_hash != previous:
            return alerts, f"line {number}: previous_hash does not link to the preceding line"
        if entry_hash_for(_alert_body(alert)) != alert.entry_hash:
            return alerts, f"line {number}: entry_hash does not cover this line"
        alerts.append(alert)
        previous = alert.entry_hash
        seq += 1
    return alerts, None


def read_alerts(path: Path) -> tuple[list[Alert], str | None]:
    if not os.path.lexists(path):
        return [], None
    try:
        document = _safe_read_state_file(path)
    except (OSError, ValueError) as exc:
        return [], f"alert ledger is unreadable: {exc.__class__.__name__}"
    return read_alerts_document(document)


def alert_rollback_defect(alerts: Sequence[Alert], head: tuple[int, str] | None) -> str | None:
    if head is None:
        return None
    seq, entry_hash = head
    if seq < 1:
        return None
    if len(alerts) < seq:
        return f"alert ledger holds {len(alerts)} records but the recorded head is seq {seq}"
    if alerts[seq - 1].entry_hash != entry_hash:
        return f"alert at seq {seq} no longer matches the recorded head"
    return None


@dataclass(frozen=True, slots=True)
class ClearanceStatus:
    cleared: bool
    detail: str
    principals: tuple[str, ...]
    unsigned: bool


def alert_excluded_principals(alert: Alert) -> tuple[str, ...]:
    if alert.actor.identity in {"verified", "ci"} and alert.actor.principal is not None:
        return (alert.actor.principal,)
    return ()


ROTATION_REMEDY = (
    "a trust-root rotation ceremony (trinity/docs/trust-root.md) that enrols a distinct "
    f"{SENTINEL_CLEARER_ROLE} is the only remedy"
)


def clearer_remedy(root: Path, alert: Alert, *, evaluation_time: datetime) -> str:
    """Say who could sign a clearance for ``alert`` now, or why nobody can.

    The gate already refuses an uncleared alert; this names the way out. It asks the trust
    root the same question a clearance verification would, with every principal the root
    binds to ``sentinel_clearer`` offered as if verified and the alerted actor excluded, so
    the answer is the set a real signature could produce and never a wider one. A root that
    defines the role but binds nobody eligible to it is a policy nothing can meet, and the
    remedy for that is organisational, so the sentence says so instead of leaving the
    operator to loop.
    """
    if not (root / ALLOWED_SIGNERS_PATH).is_file():
        return f"nobody can clear it: {ALLOWED_SIGNERS_PATH} is absent; {ROTATION_REMEDY}"
    try:
        trust_root = attest_trustroot.TrustRoot.from_path(root / TRUST_ROOT_PATH)
    except FileNotFoundError:
        return f"nobody can clear it: {TRUST_ROOT_PATH} is absent; {ROTATION_REMEDY}"
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return f"nobody can clear it: {TRUST_ROOT_PATH} is unreadable ({exc}); {ROTATION_REMEDY}"
    try:
        trusted_version = int(
            (root / TRUSTED_ROOT_VERSION_PATH).read_text(encoding="utf-8").strip()
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return (
            f"nobody can clear it: {TRUSTED_ROOT_VERSION_PATH} is unreadable or malformed "
            f"({exc}); {ROTATION_REMEDY}"
        )
    role = next((item for item in trust_root.roles if item.name == SENTINEL_CLEARER_ROLE), None)
    excluded = alert_excluded_principals(alert)
    bound = sorted(role.principals) if role is not None else []
    distinct = [name for name in bound if name not in excluded]
    if bound and not distinct:
        return (
            f"nobody can clear it under {TRUST_ROOT_PATH} version {trust_root.version}: the "
            f"only principals bound to {SENTINEL_CLEARER_ROLE} are the alerted actor "
            f"({', '.join(bound)}), and self-clearance is refused; {ROTATION_REMEDY}"
        )
    outcome = trust_root.authorize(
        role_name=SENTINEL_CLEARER_ROLE,
        verified_principals=distinct,
        evaluation_time=evaluation_time,
        trusted_version=trusted_version,
        excluded_principals=excluded,
    )
    if outcome.accepted and role is not None:
        return (
            f"clearable now by a signed clearance from {role.threshold} of the "
            f"{len(outcome.principals)} eligible {SENTINEL_CLEARER_ROLE} principals in "
            f"{TRUST_ROOT_PATH} version {trust_root.version}: " + ", ".join(outcome.principals)
        )
    return (
        f"nobody can clear it under {TRUST_ROOT_PATH} version {trust_root.version} "
        f"({outcome.reason_value}: {outcome.detail}); {ROTATION_REMEDY}"
    )


def clearance_path(root: Path, alert: Alert, stream: str | None = None) -> Path:
    return layout(root, stream).clearances / f"{alert.entry_hash}.json.dsse"


def legacy_clearance_path(root: Path, alert: Alert, stream: str | None = None) -> Path:
    return layout(root, stream).clearances / f"{alert.entry_hash}.json"


def alert_evidence(
    root: Path, alert: Alert, stream: str | None
) -> tuple[str, tuple[str, ...]] | None:
    if alert.repo is not None and alert.attempts:
        return alert.repo, alert.attempts
    paths = layout(root, stream)
    ledger, defect = read_ledger(paths.ledger)
    if defect is not None or not 1 <= alert.first_seq <= alert.last_seq <= len(ledger):
        return None
    head = read_head(paths.head)
    if isinstance(head, str) or rollback_defect(ledger, head) is not None:
        return None
    related = [
        item
        for item in ledger
        if alert.first_seq <= item.seq <= alert.last_seq and str(item.code) in alert.codes
    ]
    if not related or related[0].seq != alert.first_seq or related[-1].seq != alert.last_seq:
        return None
    return related[-1].repo, tuple(sorted(item.entry_hash for item in related))


def clearance_status(
    root: Path,
    alert: Alert,
    *,
    evaluation_time: datetime,
    stream: str | None = None,
    backend: SignatureBackend | None = None,
) -> ClearanceStatus:
    if os.path.lexists(legacy_clearance_path(root, alert, stream)):
        return ClearanceStatus(
            False, "clearance is typed rather than signed; a name is not a signature", (), True
        )
    path = clearance_path(root, alert, stream)
    if not os.path.lexists(path):
        return ClearanceStatus(False, "no signed clearance recorded", (), False)
    try:
        document = _safe_read_state_file(path)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return ClearanceStatus(False, f"clearance is unreadable: {exc}", (), False)
    return _verify_clearance_document(
        root, alert, document, evaluation_time=evaluation_time, stream=stream, backend=backend
    )


def _verify_clearance_document(
    root: Path,
    alert: Alert,
    document: bytes,
    *,
    evaluation_time: datetime,
    stream: str | None,
    backend: SignatureBackend | None,
) -> ClearanceStatus:
    result = attest_dsse.parse_envelope(document)
    if result.envelope is None:
        return ClearanceStatus(False, result.detail, (), False)
    envelope = result.envelope
    allowed_signers = root / ALLOWED_SIGNERS_PATH
    if not allowed_signers.is_file():
        return ClearanceStatus(
            False,
            ".memory/allowed_signers is absent, so no clearance signer can be verified; "
            "enrol the clearer's public key under the trust-root rotation ceremony and re-run",
            (),
            False,
        )
    outcome = attest_dsse.verify_envelope(
        backend if backend is not None else SshKeygenBackend(),
        envelope,
        expected_payload_type=CLEARANCE_PAYLOAD_TYPE,
        allowed_signers_path=allowed_signers,
        evaluation_time=evaluation_time,
    )
    if not outcome.accepted:
        return ClearanceStatus(False, outcome.detail, (), False)
    try:
        parsed = attest_canonical.parse_json(envelope.payload)
    except attest_canonical.CanonicalizationError as exc:
        return ClearanceStatus(False, str(exc), (), False)
    if not isinstance(parsed, dict) or set(parsed) != CLEARANCE_FIELDS:
        return ClearanceStatus(False, "clearance fields differ from the closed schema", (), False)
    if parsed["schema"] != CLEARANCE_SCHEMA:
        return ClearanceStatus(False, "clearance schema is unsupported", (), False)
    if parsed["alert_entry_hash"] != alert.entry_hash:
        return ClearanceStatus(False, "clearance names a different alert", (), False)
    if parsed["stream"] != stream:
        return ClearanceStatus(False, "clearance names a different stream", (), False)
    evidence = alert_evidence(root, alert, stream)
    if evidence is None:
        return ClearanceStatus(
            False, "alert evidence unavailable: attempt ledger cannot cover the alert", (), False
        )
    repo, attempts = evidence
    if parsed["repo"] != repo:
        return ClearanceStatus(False, "clearance names a different repo", (), False)
    if parsed["attempts"] != list(attempts):
        return ClearanceStatus(False, "clearance names different attempts", (), False)
    cleared_at = parsed["cleared_at"]
    if not isinstance(cleared_at, str):
        return ClearanceStatus(False, "cleared_at is not an RFC 3339 UTC instant", (), False)
    try:
        parse_time(cleared_at)
    except ValueError:
        return ClearanceStatus(False, "cleared_at is not an RFC 3339 UTC instant", (), False)
    reason = parsed["reason"]
    if not isinstance(reason, str) or not reason.strip():
        return ClearanceStatus(False, "clearance carries no reason", (), False)
    try:
        trusted_version = int(
            (root / TRUSTED_ROOT_VERSION_PATH).read_text(encoding="utf-8").strip()
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return ClearanceStatus(
            False, f"trusted root version is unreadable or malformed: {exc}", (), False
        )
    if trusted_version < 0:
        return ClearanceStatus(False, "trusted root version must be non-negative", (), False)
    authorized = attest_trustroot.authorize(
        root / TRUST_ROOT_PATH,
        role_name=SENTINEL_CLEARER_ROLE,
        verified_principals=outcome.principals,
        evaluation_time=evaluation_time,
        trusted_version=trusted_version,
        excluded_principals=alert_excluded_principals(alert),
    )
    if not authorized.accepted:
        return ClearanceStatus(
            False,
            f"clearance signer is not authorized ({authorized.reason_value}): {authorized.detail}",
            (),
            False,
        )
    return ClearanceStatus(True, "", authorized.principals, False)


def write_clearance(
    root: Path,
    alert: Alert,
    *,
    key_path: Path,
    reason: str,
    evaluation_time: datetime | None = None,
    now: datetime | None = None,
    stream: str | None = None,
    backend: SignatureBackend | None = None,
) -> Path:
    path, _status = _write_verified_clearance(
        root,
        alert,
        key_path=key_path,
        reason=reason,
        evaluation_time=evaluation_time,
        now=now,
        stream=stream,
        backend=backend,
    )
    return path


def _write_verified_clearance(
    root: Path,
    alert: Alert,
    *,
    key_path: Path,
    reason: str,
    evaluation_time: datetime | None = None,
    now: datetime | None = None,
    stream: str | None = None,
    backend: SignatureBackend | None = None,
) -> tuple[Path, ClearanceStatus]:
    if not reason.strip():
        raise ValueError("a clearance needs a reason")
    if os.path.lexists(legacy_clearance_path(root, alert, stream)):
        raise ValueError("clearance is typed rather than signed; a name is not a signature")
    evidence = alert_evidence(root, alert, stream)
    if evidence is None:
        raise ValueError("alert evidence unavailable: attempt ledger cannot cover the alert")
    repo, attempts = evidence
    instant = evaluation_time if evaluation_time is not None else datetime.now(UTC)
    signer = backend if backend is not None else SshKeygenBackend()
    path = clearance_path(root, alert, stream)
    payload: attest_canonical.JSONValue = {
        "alert_entry_hash": alert.entry_hash,
        "repo": repo,
        "attempts": list(attempts),
        "cleared_at": format_time(now if now is not None else instant),
        "reason": reason.strip(),
        "schema": CLEARANCE_SCHEMA,
        "stream": stream,
    }
    try:
        envelope = attest_dsse.sign_envelope(
            signer,
            CLEARANCE_PAYLOAD_TYPE,
            attest_canonical.canonicalize(payload),
            key_path=key_path,
        )
    except SignatureBackendError as exc:
        raise ValueError(exc.detail) from exc
    document = envelope.to_json()
    status = _verify_clearance_document(
        root, alert, document, evaluation_time=instant, stream=stream, backend=signer
    )
    if not status.cleared:
        raise ValueError(status.detail)
    _inspect_state_components(root, path)
    _ensure_state_directory(root, path.parent)
    _safe_write_state_file(path, document)
    return path, status


def append_alerts(path: Path, alerts: Sequence[Alert]) -> None:
    _ensure_state_directory(_sentinel_root_for(path), path.parent)
    with _safe_open_state_file(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, "ab") as handle:
        for alert in alerts:
            handle.write(render_alert(alert).encode("utf-8") + b"\n")


def raise_alerts(
    root: Path,
    ledger: Sequence[Attempt],
    new: Sequence[Attempt],
    *,
    now: datetime,
    evaluation_time: datetime | None = None,
    window_days: int = DEFAULT_WINDOW_DAYS,
    threshold: int = DEFAULT_THRESHOLD,
    stream: str | None = None,
) -> list[Alert]:
    """Append one alert per actor whose new attempt repeats inside the window.

    An actor with an uncleared alert already standing folds into it: the refusal is already
    live, and a second alert would only lengthen the ledger. A cleared alert never folds, so
    a repeat after clearance raises a fresh one.
    """
    paths = layout(root, stream)
    alerts_path = paths.alerts
    alerts, defect = read_alerts(alerts_path)
    alert_head = read_head(paths.alerts_head)
    if isinstance(alert_head, str) or (
        isinstance(alert_head, tuple) and not os.path.lexists(alerts_path)
    ):
        quarantine_files(root, paths.alerts_head, stream=stream)
    if defect is not None:
        quarantine_files(root, alerts_path, paths.alerts_head, stream=stream)
        alerts = []
    instant = evaluation_time if evaluation_time is not None else datetime.now(UTC)
    standing = [
        alert
        for alert in alerts
        if not clearance_status(root, alert, evaluation_time=instant, stream=stream).cleared
        and alert_stands(ledger, alert, window=timedelta(days=window_days), threshold=threshold)
    ]
    window = timedelta(days=window_days)
    previous = alerts[-1].entry_hash if alerts else CHAIN_GENESIS
    seq = alerts[-1].seq + 1 if alerts else 1
    raised: list[Alert] = []
    for attempt in new:
        if attempt.code is SabotageCode.SAB_REPEATED_ATTEMPT:
            continue
        if not is_repeat(ledger, attempt, window=window, threshold=threshold):
            continue
        if any(alert.actor.shares_identity(attempt.actor) for alert in (*standing, *raised)):
            continue
        start = attempt.captured_at - window
        related = [
            item
            for item in ledger
            if start <= item.captured_at <= attempt.captured_at and item.code == attempt.code
        ]
        draft = Alert(
            seq=seq,
            actor=attempt.actor,
            codes=tuple(sorted({str(item.code) for item in related})),
            window_days=window_days,
            threshold=threshold,
            first_seq=min(item.seq for item in related),
            last_seq=attempt.seq,
            raised_at=now,
            previous_hash=previous,
            entry_hash="",
            schema_version=ALERT_SCHEMA_V2,
            repo=attempt.repo,
            attempts=tuple(sorted(item.entry_hash for item in related)),
        )
        alert = replace(draft, entry_hash=entry_hash_for(_alert_body(draft)))
        raised.append(alert)
        previous = alert.entry_hash
        seq += 1
    if raised:
        append_alerts(alerts_path, raised)
        write_head(paths.alerts_head, raised[-1].seq, raised[-1].entry_hash)
    return raised


# ---- CLI ----------------------------------------------------------------------------------


def _run_gate(root: Path, project_root: Path) -> list[FindingJson]:
    integrity = Path(__file__).with_name("integrity.py")
    completed = subprocess.run(
        [
            sys.executable,
            str(integrity),
            "json",
            "parent",
            display_project_path(root, project_root=project_root),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return parse_findings_document(completed.stdout or "[]")


def _read_changed_paths(path: Path | None) -> list[str]:
    if path is None:
        return []
    try:
        return path.read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeDecodeError):
        return []


def _cmd_record(args: argparse.Namespace) -> int:
    root: Path = args.root
    if args.findings is not None:
        findings = parse_findings_document(args.findings.read_bytes())
    else:
        findings = _run_gate(root, args.project_root)
    actor = resolve_actor(root, ci=args.ci)
    run_id = args.run_id or os.environ.get("GITHUB_RUN_ID") or f"local-{uuid.uuid4()}"
    new, chain_findings = record(
        root,
        findings,
        actor=actor,
        run_id=run_id,
        git_sha=resolve_git_sha(root),
        repo=resolve_repo(root),
        changed_paths=_read_changed_paths(args.changed_paths),
        ci=args.ci,
        stream=args.stream,
    )
    for item in chain_findings:
        print(f"{item.code}: {item.message}")
    for attempt in new:
        print(f"{attempt.code} seq {attempt.seq} weight {attempt.weight} {attempt.evidence_digest}")
    for standing in standing_alerts(root, args.stream):
        print(
            f"{SabotageCode.SAB_REPEATED_ATTEMPT} alert seq {standing.alert.seq} "
            f"{standing.alert.entry_hash} by {standing.alert.actor.git_author}: "
            f"{standing.status.detail}; {standing.evidence()}; {standing.remedy}"
        )
    return EXIT_RECORDED if new else 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Refuse on exactly what the gate refuses: a broken chain or a standing alert.

    A superseded alert is printed as the advisory the gate emits and refuses nothing, so
    this command's exit code never disagrees with the disposition ceiling.
    """
    root: Path = args.root
    instant = datetime.now(UTC)
    findings = check_sentinel_chain(str(root), instant)
    for item in findings:
        print(f"{item.severity.name.lower()} {item.code}: {item.path}: {item.message}")
    if any(item.severity is Severity.ERROR for item in findings):
        return EXIT_REFUSED
    for stream in (None, *stream_names(root)):
        for standing in alert_standings(root, stream, evaluation_time=instant):
            if standing.status.cleared:
                print(
                    f"alert seq {standing.alert.seq} {standing.alert.entry_hash}: cleared by "
                    f"{', '.join(standing.status.principals)}"
                )
    print("sentinel: chain verified, no standing alert")
    return 0


def _cmd_clear(args: argparse.Namespace) -> int:
    root: Path = args.root
    alerts, defect = read_alerts(layout(root, args.stream).alerts)
    if defect is not None:
        print(f"{SentinelFailureReason.SENTINEL_CHAIN_BROKEN}: {defect}", file=sys.stderr)
        return EXIT_REFUSED
    match = [alert for alert in alerts if alert.entry_hash == args.alert]
    if not match:
        print(f"clear refused: no alert with entry hash {args.alert}", file=sys.stderr)
        return EXIT_REFUSED
    try:
        path, status = _write_verified_clearance(
            root, match[0], key_path=args.key, reason=args.reason, stream=args.stream
        )
    except ValueError as exc:
        print(f"clear refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(
        f"cleared alert seq {match[0].seq} under {', '.join(status.principals)}: "
        f"{display_project_path(path, project_root=args.project_root)}"
    )
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    root: Path = args.root
    paths = layout(root, args.stream)
    attempts, defect = read_ledger(paths.ledger)
    head = read_head(paths.head)
    if isinstance(head, str):
        head_text = f"broken {head}"
    elif head is None:
        head_text = f"0 {CHAIN_GENESIS}"
    else:
        head_text = f"{head[0]} {head[1]}"
    print(f"records: {len(attempts)}")
    print(f"head: {head_text}")
    print(f"chain: {'broken: ' + defect if defect else 'ok'}")
    for attempt in attempts[-STATUS_TAIL:]:
        print(
            f"  seq {attempt.seq} {format_time(attempt.captured_at)} {attempt.code} "
            f"{attempt.actor.identity}:{attempt.actor.principal}"
        )
    alerts, alert_defect = read_alerts(paths.alerts)
    standings = alert_standings(root, args.stream)
    standing = [item for item in standings if item.stands]
    superseded = [item for item in standings if item.superseded]
    cleared = [item for item in standings if item.status.cleared]
    print(
        f"alerts: {len(alerts)} raised, {len(standing)} standing, "
        f"{len(superseded)} superseded, {len(cleared)} cleared"
    )
    for item in standing:
        print(
            f"  standing alert seq {item.alert.seq} {item.alert.entry_hash} "
            f"{item.alert.actor.git_author}: {item.status.detail}; {item.evidence()}; "
            f"{item.remedy}"
        )
    for item in superseded:
        print(
            f"  superseded alert seq {item.alert.seq} {item.alert.entry_hash} "
            f"{item.alert.actor.git_author}: raised under a superseded repeat rule, "
            "history only, caps nothing, needs no clearance"
        )
    for item in cleared:
        print(
            f"  cleared alert seq {item.alert.seq} {item.alert.entry_hash}: cleared by "
            f"{', '.join(item.status.principals)}"
        )
    broken = defect or alert_defect or verify_chain(root, args.stream) or standing
    return EXIT_REFUSED if broken else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    rec = commands.add_parser("record", help="classify gate findings and append SAB records")
    rec.add_argument("root")
    rec.add_argument("--findings", help="JSON findings file; default runs integrity.py")
    rec.add_argument("--run-id")
    rec.add_argument("--ci", action="store_true")
    rec.add_argument("--changed-paths", help="file listing paths changed by this push")
    rec.add_argument("--stream", help="the run stream under .sentinel/streams/ to append to")
    rec.set_defaults(func=_cmd_record)
    ver = commands.add_parser("verify", help="walk the sentinel chain")
    ver.add_argument("root")
    ver.set_defaults(func=_cmd_verify)
    clr = commands.add_parser("clear", help="record a clearance for one alert")
    clr.add_argument("root")
    clr.add_argument("--alert", required=True, help="entry hash of the alert to clear")
    clr.add_argument(
        "--key", required=True, help="software SSH private key of a sentinel_clearer principal"
    )
    clr.add_argument("--reason", default="cleared after review")
    clr.add_argument("--stream", help="the run stream holding the alert")
    clr.set_defaults(func=_cmd_clear)
    sta = commands.add_parser(
        "status", help="print the ledger tail and every alert as standing, superseded, or cleared"
    )
    sta.add_argument("root")
    sta.add_argument("--stream", help="the run stream to print")
    sta.set_defaults(func=_cmd_status)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        project_root = invocation_root()
        args.project_root = project_root
        args.root = resolve_project_path(
            str(args.root),
            project_root=project_root,
            description="parent root",
            must_exist=True,
        )
        if getattr(args, "findings", None) is not None:
            args.findings = resolve_project_path(
                str(args.findings),
                project_root=project_root,
                description="findings input",
                must_exist=True,
            )
        if getattr(args, "changed_paths", None) is not None:
            args.changed_paths = resolve_project_path(
                str(args.changed_paths),
                project_root=project_root,
                description="changed-path input",
                must_exist=True,
            )
        if getattr(args, "key", None) is not None:
            args.key = resolve_project_path(
                str(args.key),
                project_root=project_root,
                description="clearance signing key",
                must_exist=True,
            )
        return int(args.func(args))
    except (OSError, ProjectPathError, ValueError) as exc:
        root = locals().get("project_root")
        message = (
            str(exc)
            if not isinstance(root, Path)
            else redact_project_root(str(exc), project_root=root)
        )
        print(f"sentinel refused: {message}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
