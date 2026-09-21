"""The one gate entry point a pasted contract runs, and the record it mints.

Trinity is invoked by pasting ``ENGRAM.md``, ``FORGE.md``, or ``CRUCIBLE.md`` into an
agent at the parent root. A pasted contract is followed by an agent that can skip a
step, so every check under ``tools/`` is worth nothing unless one command runs all of
them at fixed moments and the artifacts the run must produce are only valid when that
command produced them. This module is that command.

Two moments. ``--moment preflight`` runs after the Trinity freshness gate and before any
phase work; ``--moment report`` runs before the root report is written. Both run every
registered parent check, append sabotage-class refusals to the sentinel ledger, and
write a receipt under ``<harness>/gate-receipts/``. The report moment also mints
``<harness>/disposition.json`` with the machine ceiling, which the root report copies
verbatim into its ``## Disposition`` line.

The ceiling is closed. An ERROR finding whose code starts with ``SAB_`` or ``RELEASE_``,
or is a Trinity freshness refusal or a layout boundary violation, is ``BLOCK``.
Any other ERROR is ``HOLD``. Only an
empty ERROR set is ``SHIP_ELIGIBLE``, never ``SHIP``: the agent cannot mint a SHIP.
``promote`` rewrites an eligible record to ``SHIP`` under a named approver who is not the
producer, and the DSSE envelope that makes that record valid is signed with a key the
operator does not hold, by ``tools.attest``.

``install`` is the third verb, and the preflight runs it before the first check. It copies
the two workflows and the pre-push hook from ``trinity/templates/`` into the parent, points
``core.hooksPath`` at ``.githooks``, writes the CODEOWNERS lines that put ``.github/``,
``trinity``, and ``.gitmodules`` under the research team, and ensures branch protection on
``main`` through the GitHub CLI for the parent and the declared submodules under
``.memory``, ``samples``, ``delivery``, ``harness``, and optional ``staging``, in roster
order. The vendored ``trinity`` repository is excluded. It records a receipt per
repository under ``.trinity-install/``. Protection already in force is read back, from
classic protection or from the rulesets an administrator applied, and receipted without a
write; only when nothing stands does install PUT classic protection, which GitHub allows
administrators alone. A
protection it can neither read back nor apply is a receipt saying so, and
``check_gates_installed`` turns that receipt into ``GATE_PROTECTION_MISSING``, a HOLD.
Trinity installs its own gates; nobody applies them by hand.

Exit codes: 0 when the ceiling is ``SHIP_ELIGIBLE``, 2 for ``HOLD``, 3 for ``BLOCK``;
``install`` exits 0 when every protection applied and 2 otherwise.

Residual, stated once: a local run can still skip the preflight, and the receipt's
timestamps are self-reported. ``check_gate_receipts`` decides from committed bytes that
a report without a receipt binding HEAD, or a report token above the minted record, is
refused; ``.githooks/pre-push`` refuses a BLOCK locally; the decision that counts is the
same command run by continuous integration on the pushed commit.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid as uuid_module
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, TypedDict


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING:
    from tools import layout
    from tools import runs as runs_module
    from tools import subject as subject_module
    from tools._findings import Finding, FindingJson, Severity, finding_to_json, render_finding
    from tools.attest import SignatureBackend
    from tools.attest.backend_ssh import SshKeygenBackend
    from tools.attest.canonical import canonicalize, parse_json
    from tools.attest.dsse import Envelope, parse_envelope, sign_envelope, verify_envelope
    from tools.bundle_identity import (
        ZERO_DIGEST,
        BundleIdentityError,
        release_snapshot_digest,
    )
    from tools.bundle_identity import (
        bundle_set_digest as canonical_bundle_set_digest,
    )
    from tools.project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
    from tools.release_evidence import (
        DISPOSITION_PAYLOAD_TYPES,
        DISPOSITION_SCHEMA,
        GROUP_APPROVER_ROLE,
        GROUP_DISPOSITION_PAYLOAD_TYPES,
        GROUP_DISPOSITION_SCHEMA,
        GROUP_PRODUCER_ROLE,
        MAX_EVIDENCE_BYTES,
        ReleaseEvidenceError,
        ReleaseTrust,
        load_release_trust,
        parse_instant,
        safe_read_bytes,
        seals_only,
    )
    from tools.safe_git import SafeGitError, SafeGitRepository
else:
    try:
        from tools import layout
        from tools import runs as runs_module
        from tools import subject as subject_module
        from tools._findings import Finding, FindingJson, Severity, finding_to_json, render_finding
        from tools.attest import SignatureBackend
        from tools.attest.backend_ssh import SshKeygenBackend
        from tools.attest.canonical import canonicalize, parse_json
        from tools.attest.dsse import Envelope, parse_envelope, sign_envelope, verify_envelope
        from tools.bundle_identity import (
            ZERO_DIGEST,
            BundleIdentityError,
            release_snapshot_digest,
        )
        from tools.bundle_identity import (
            bundle_set_digest as canonical_bundle_set_digest,
        )
        from tools.project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
        from tools.release_evidence import (
            DISPOSITION_PAYLOAD_TYPES,
            DISPOSITION_SCHEMA,
            GROUP_APPROVER_ROLE,
            GROUP_DISPOSITION_PAYLOAD_TYPES,
            GROUP_DISPOSITION_SCHEMA,
            GROUP_PRODUCER_ROLE,
            MAX_EVIDENCE_BYTES,
            ReleaseEvidenceError,
            ReleaseTrust,
            load_release_trust,
            parse_instant,
            safe_read_bytes,
            seals_only,
        )
        from tools.safe_git import SafeGitError, SafeGitRepository
    except ModuleNotFoundError:
        import layout
        import runs as runs_module
        import subject as subject_module
        from _findings import Finding, FindingJson, Severity, finding_to_json, render_finding
        from attest import SignatureBackend
        from attest.backend_ssh import SshKeygenBackend
        from attest.canonical import canonicalize, parse_json
        from attest.dsse import Envelope, parse_envelope, sign_envelope, verify_envelope
        from bundle_identity import (
            ZERO_DIGEST,
            BundleIdentityError,
            release_snapshot_digest,
        )
        from bundle_identity import (
            bundle_set_digest as canonical_bundle_set_digest,
        )
        from project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
        from release_evidence import (
            DISPOSITION_PAYLOAD_TYPES,
            DISPOSITION_SCHEMA,
            GROUP_APPROVER_ROLE,
            GROUP_DISPOSITION_PAYLOAD_TYPES,
            GROUP_DISPOSITION_SCHEMA,
            GROUP_PRODUCER_ROLE,
            MAX_EVIDENCE_BYTES,
            ReleaseEvidenceError,
            ReleaseTrust,
            load_release_trust,
            parse_instant,
            safe_read_bytes,
            seals_only,
        )
        from safe_git import SafeGitError, SafeGitRepository

# ---- closed vocabularies -------------------------------------------------------

INSTRUMENT_HARNESS: dict[str, str] = {
    "ENGRAM": ".memory",
    "FORGE": ".seed",
    "CRUCIBLE": ".audit",
}
INSTRUMENT_REPORT: dict[str, str] = {
    "ENGRAM": "DIRECTIVE.md",
    "FORGE": "EDICT.md",
    "CRUCIBLE": "VERDICT.md",
}
MOMENTS: tuple[str, ...] = ("preflight", "report")

BLOCK = "BLOCK"
HOLD = "HOLD"
SHIP_ELIGIBLE = "SHIP_ELIGIBLE"
SHIP = "SHIP"
CEILINGS: tuple[str, ...] = (BLOCK, HOLD, SHIP_ELIGIBLE)
BLOCK_PREFIXES: tuple[str, ...] = ("SAB_", "RELEASE_", "TRINITY_FRESHNESS_")
# Suspicion without a bypass or a forged SHIP holds rather than blocks.
HOLD_EXCEPTIONS: frozenset[str] = frozenset({"SAB_WORKFLOW_TAMPER_SUSPECT"})
BLOCK_CODES: frozenset[str] = layout.BLOCKING_CODES

# Rank of a disposition token as a root report may spell it. Higher is more permissive.
# A record token is always one of the three ceilings or a promoted SHIP.
TOKEN_RANK: dict[str, int] = {
    "BLOCK": 0,
    "BROKEN": 0,
    "HOLD": 1,
    "STALE": 1,
    "SHIP_ELIGIBLE": 2,
    "SHIP": 3,
    "SHIP:INFERRED": 3,
    "CURRENT": 3,
}

RECEIPT_DIR = "gate-receipts"
RECEIPT_SCHEMA = "trinity.gate-receipt/v1"
RECEIPT_FIELDS: frozenset[str] = frozenset(
    {
        "schema_version",
        "instrument",
        "moment",
        "run_id",
        "tree_sha",
        "trinity_commit",
        "ceiling",
        "codes",
        "error_count",
        "generated_at",
    }
)
RUN_RECEIPT_SCHEMA = "trinity.gate-receipt/v2"
RUN_RECEIPT_FIELDS: frozenset[str] = RECEIPT_FIELDS | {"subject_digest"}
QUALIFICATION_SCHEMA = "trinity.qualification/v2"
QUALIFICATION_FIELDS: frozenset[str] = frozenset(
    {
        "schema",
        "instrument",
        "run_id",
        "disposition",
        "subject_digest",
        "trinity_commit",
        "generated_at",
        "producer",
        "approver",
    }
)
GATE_SUBJECT_UNBOUND = "GATE_SUBJECT_UNBOUND"
RELEASES_DIR = "releases"
RELEASE_ID = re.compile(r"[a-z0-9][a-z0-9.-]{2,63}\Z")
GENERATED_BANNER = "GENERATED SECTION. DO NOT HAND-EDIT."
DISPOSITION_RECORD = "disposition.json"
DISPOSITION_ENVELOPE = "disposition.json.dsse"
DISPOSITION_PAYLOAD_TYPE = "application/vnd.trinity.disposition+json"
DISPOSITION_FIELDS: frozenset[str] = frozenset(
    {
        "disposition",
        "tree_sha",
        "trinity_commit",
        "bundle_digest",
        "generated_at",
        "producer",
        "approver",
    }
)
FINAL_DISPOSITION_FIELDS: frozenset[str] = frozenset(
    {
        "schema",
        "instrument",
        "disposition",
        "project_id",
        "repository_id",
        "snapshot_digest",
        "bundle_set_digest",
        "candidate_commit",
        "verifier_sha",
        "issued_at",
        "expires_at",
        "producer",
        "approver",
    }
)
GROUP_DISPOSITION_FIELDS: frozenset[str] = frozenset(
    (FINAL_DISPOSITION_FIELDS - {"producer", "approver"}) | {"producer_role", "approver_role"}
)
UNSIGNED_APPROVER = "unsigned"
HOOK_PATH = ".githooks/pre-push"
HOOK_MARKER = "tools/gate.py"
TRINITY_DIR = "trinity"
SAMPLES_DIR = "samples"
SHA40_ZERO = "0" * 40
SHA64_ZERO = ZERO_DIGEST
UUID = re.compile(r"\A[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
H2_DISPOSITION = re.compile(r"^##\s+Disposition\s*$")
DISPOSITION_TOKEN = re.compile(r"[A-Z][A-Z_:]{2,}")

GATE_PREFLIGHT_MISSING = "GATE_PREFLIGHT_MISSING"
GATE_DISPOSITION_MISMATCH = "GATE_DISPOSITION_MISMATCH"
GATE_HOOK_MISSING = "GATE_HOOK_MISSING"
GATE_ATTRIBUTES_MISSING = "GATE_ATTRIBUTES_MISSING"
GATE_MERGE_DRIVER_MISSING = "GATE_MERGE_DRIVER_MISSING"
GATE_WORKFLOW_MISSING = "GATE_WORKFLOW_MISSING"
GATE_CODEOWNERS_MISSING = "GATE_CODEOWNERS_MISSING"
GATE_PROTECTION_UNVERIFIED = "GATE_PROTECTION_UNVERIFIED"
GATE_PROTECTION_MISSING = "GATE_PROTECTION_MISSING"
PROJECT_MIGRATION_HOLD = "PROJECT_MIGRATION_HOLD"

# ---- install surfaces ------------------------------------------------------------
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
WORKFLOWS_DIR = ".github/workflows"
WORKFLOW_TEMPLATES: tuple[str, ...] = ("sentinel.yaml",)
HOOK_TEMPLATE = "pre-push"
HOOK_TEMPLATES: tuple[str, ...] = (
    "pre-commit",
    "pre-merge-commit",
    "post-checkout",
    "post-merge",
    "post-rewrite",
    "pre-push",
)
HOOK_DIR = ".githooks"
ATTRIBUTES_PATH = ".gitattributes"
MERGE_DRIVER = "trinity-generated"
MERGE_DRIVER_NAME = "Trinity generated report; keep ours and re-render"
DOOR_TEMPLATES_DIR = TEMPLATES_DIR / "doors"
COMMAND_DOOR_DIR = ".opencode/commands"
SKILL_DOOR_DIR = ".agents/skills"
CODEOWNERS_PATH = ".github/CODEOWNERS"
CODEOWNED_PATHS: tuple[str, ...] = ("/.github/", "/trinity", "/.gitmodules")
DEFAULT_CODEOWNERS_TEAM = "@Aman4563"
CODEOWNERS_TEAM_ENV = "TRINITY_CODEOWNERS_TEAM"
INSTALL_DIR = ".trinity-install"
PROTECTION_DIR = "protection"
PROTECTION_SCHEMA = "trinity.branch-protection/v1"
PROTECTED_BRANCH = "main"
# The job names the two workflows expose as status contexts.
REQUIRED_CHECKS: tuple[str, ...] = ("gate",)
GATED_SUBMODULES: tuple[str, ...] = layout.PROTECTED_ROOTS
GH_TIMEOUT_SECONDS = 60.0
GITHUB_REMOTE = re.compile(r"github\.com[:/](?P<owner>[^/\s]+)/(?P<name>[^/\s]+?)(?:\.git)?/?\Z")
EXIT_INSTALL_INCOMPLETE = 2

EXIT_CLEAN = 0
EXIT_USAGE = 1
EXIT_HOLD = 2
EXIT_BLOCK = 3
EXIT_FOR_CEILING: dict[str, int] = {SHIP_ELIGIBLE: EXIT_CLEAN, HOLD: EXIT_HOLD, BLOCK: EXIT_BLOCK}

GIT_TIMEOUT_SECONDS = 30.0
GITLINK_MODE = "160000"
GITLINK_FIELDS = 3
PORCELAIN_STATUS_PREFIX = 3


class GateError(ValueError):
    """A refusal raised by ``promote`` or by malformed inputs."""


class RoleProgress(TypedDict):
    role: str
    threshold: int
    principals: list[str]
    missing: int
    complete: bool


# ---- git ------------------------------------------------------------------------


def _git(root: Path, *argv: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *argv],
            capture_output=True,
            check=False,
            shell=False,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_head(root: Path) -> str | None:
    return _git(root, "rev-parse", "--verify", "HEAD^{commit}")


def git_head_author_email(root: Path) -> str | None:
    return _git(root, "log", "-1", "--format=%ae", "HEAD")


def git_gitlink(root: Path, name: str) -> str | None:
    listing = _git(root, "ls-files", "--stage", "--", name)
    if not listing:
        return None
    parts = listing.split()
    if len(parts) < GITLINK_FIELDS or parts[0] != GITLINK_MODE:
        return None
    return parts[1]


def binds_head(root: Path, tree_sha: str, head: str) -> bool:
    """``tree_sha`` is ``head`` or an ancestor reached only through sealing commits.

    A record or receipt cannot name the commit that contains it, and each external signer
    lands their envelope in a commit of their own, so the chain from the bound commit to
    HEAD may be any length provided every commit in it touches sealing artifacts alone.
    """
    if tree_sha == head:
        return True
    if not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
        return False
    if _git(root, "merge-base", "--is-ancestor", tree_sha, head) is None:
        return False
    changed = _git(root, "diff", "--name-only", f"{tree_sha}..{head}")
    if changed is None:
        return False
    return seals_only(line for line in changed.splitlines() if line)


# ---- ceiling --------------------------------------------------------------------


def is_block_code(code: str) -> bool:
    return code in BLOCK_CODES or (code.startswith(BLOCK_PREFIXES) and code not in HOLD_EXCEPTIONS)


def ceiling(findings: Iterable[Finding]) -> str:
    """The closed rule that turns gate findings into a disposition ceiling."""

    worst = SHIP_ELIGIBLE
    for item in findings:
        if item.severity != Severity.ERROR:
            continue
        if is_block_code(item.code):
            return BLOCK
        worst = HOLD
    return worst


def error_codes(findings: Iterable[Finding]) -> list[str]:
    return sorted({item.code for item in findings if item.severity == Severity.ERROR})


# ---- running the parent gate ------------------------------------------------------


def _harness_module(name: str) -> ModuleType:
    """Import a sibling harness module lazily; ``integrity`` imports this module at load."""

    try:
        return importlib.import_module(f"tools.{name}")
    except ModuleNotFoundError:
        return importlib.import_module(name)


def run_gate(root: Path) -> list[Finding]:
    """Run substantive qualification checks without final release prerequisites."""

    integrity = _harness_module("integrity")
    return list(integrity.run_qualification(str(root)))


def _principal(root: Path) -> str:
    """The human this invocation runs under: CI actor, then git identity, then unknown."""
    actor = os.environ.get("GITHUB_ACTOR", "").strip()
    if actor:
        return actor
    configured = _git(root, "config", "user.email") or _git(root, "config", "user.name")
    return configured or "unknown"


def local_run_id(root: Path) -> str:
    """One attempt identity per commit outside CI, as GITHUB_RUN_ID is one per workflow run.

    The preflight, the report, and the pre-push hook of one authoring pass all run against
    the same HEAD; a fresh identity per moment made one pass count as two or three attempts
    and trip the repeat threshold against itself.
    """
    head = git_head(root)
    return f"local-{head}" if head else f"local-{uuid_module.uuid4()}"


def record_sentinel(
    root: Path,
    findings: Sequence[Finding],
    *,
    run_id: str,
    ci: bool,
    stream: str | None = None,
) -> list[str]:
    """Append sabotage-class refusals to the sentinel ledger; return the codes recorded.

    A run-scoped invocation appends to its own stream so two clones never fork one chain;
    repeat detection still reads every stream.
    """

    sentinel = _harness_module("sentinel")
    integrity = _harness_module("integrity")
    documents: list[FindingJson] = [
        finding_to_json(item)
        for item in integrity.public_findings(list(findings), project_root=root)
    ]
    attempts, _chain = sentinel.record(
        root,
        documents,
        actor=sentinel.resolve_actor(root, ci=ci),
        run_id=run_id,
        git_sha=sentinel.resolve_git_sha(root),
        repo=sentinel.resolve_repo(root),
        ci=ci,
        stream=stream,
    )
    return sorted({str(attempt.code) for attempt in attempts})


# ---- receipts and records ---------------------------------------------------------


def _now_iso(now: datetime | None) -> str:
    instant = datetime.now(UTC) if now is None else now
    return instant.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bundle_set_digest(root: Path) -> str:
    """Digest ``samples/`` with the shared identity, or 64 zeros when empty."""

    samples = root / SAMPLES_DIR
    if not samples.is_dir():
        return SHA64_ZERO
    uuids = sorted(
        entry.name for entry in samples.iterdir() if entry.is_dir() and UUID.match(entry.name)
    )
    if not uuids:
        return SHA64_ZERO
    try:
        return canonical_bundle_set_digest(samples, uuids)
    except BundleIdentityError as exc:
        raise GateError(f"samples/ has no canonical bundle identity: {exc}") from exc


@dataclass(frozen=True, slots=True)
class Receipt:
    instrument: str
    moment: str
    run_id: str
    tree_sha: str
    trinity_commit: str
    ceiling: str
    codes: tuple[str, ...]
    error_count: int
    generated_at: str

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": RECEIPT_SCHEMA,
            "instrument": self.instrument,
            "moment": self.moment,
            "run_id": self.run_id,
            "tree_sha": self.tree_sha,
            "trinity_commit": self.trinity_commit,
            "ceiling": self.ceiling,
            "codes": list(self.codes),
            "error_count": self.error_count,
            "generated_at": self.generated_at,
        }


def _safe_run_id(run_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", run_id).strip("._")
    return cleaned or "run"


def write_receipt(
    root: Path,
    *,
    instrument: str,
    moment: str,
    findings: Sequence[Finding],
    run_id: str,
    now: datetime | None = None,
    run: str | None = None,
) -> Path:
    head = git_head(root) or SHA40_ZERO
    receipt = Receipt(
        instrument=instrument,
        moment=moment,
        run_id=run_id,
        tree_sha=head,
        trinity_commit=git_gitlink(root, TRINITY_DIR) or SHA40_ZERO,
        ceiling=ceiling(findings),
        codes=tuple(error_codes(findings)),
        error_count=sum(1 for item in findings if item.severity == Severity.ERROR),
        generated_at=_now_iso(now),
    )
    if run is not None:
        directory = runs_module.run_dir(root, instrument, run) / RECEIPT_DIR
        directory.mkdir(parents=True, exist_ok=True)
        attempt = sum(1 for _ in directory.glob(f"{moment}-*.json")) + 1
        body = {
            **receipt.to_json(),
            "schema_version": RUN_RECEIPT_SCHEMA,
            "subject_digest": subject_module.subject_digest(root, instrument, run),
        }
        path = directory / f"{moment}-{attempt:04d}.json"
        path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", "utf-8")
        return path
    directory = root / INSTRUMENT_HARNESS[instrument] / RECEIPT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_run_id(run_id)}.json"
    path.write_text(json.dumps(receipt.to_json(), indent=2, sort_keys=True) + "\n", "utf-8")
    return path


def mint_record(
    root: Path,
    *,
    instrument: str,
    findings: Sequence[Finding],
    now: datetime | None = None,
    run: str | None = None,
) -> Path:
    """Write the unsigned disposition record for ``instrument`` at the machine ceiling.

    Bytes already on disk are left alone while they still describe HEAD: a rerun of the
    report moment must not rewrite a record that external principals have signed or are
    signing, or every collected envelope dies with the ``generated_at`` it covered.
    """

    if run is not None:
        return mint_qualification(root, instrument=instrument, findings=findings, now=now, run=run)
    record = {
        "disposition": ceiling(findings),
        "tree_sha": git_head(root) or SHA40_ZERO,
        "trinity_commit": git_gitlink(root, TRINITY_DIR) or SHA40_ZERO,
        "bundle_digest": bundle_set_digest(root),
        "generated_at": _now_iso(now),
        "producer": git_head_author_email(root) or "unknown",
        "approver": UNSIGNED_APPROVER,
    }
    directory = root / INSTRUMENT_HARNESS[instrument]
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / DISPOSITION_RECORD
    if _record_still_current(root, path, minted=record, now=now):
        return path
    path.write_bytes(json.dumps(record, sort_keys=True).encode("utf-8"))
    return path


def mint_qualification(
    root: Path,
    *,
    instrument: str,
    findings: Sequence[Finding],
    now: datetime | None,
    run: str,
) -> Path:
    """Write the run-scoped qualification record binding the subject closure, not HEAD.

    Another runner's commit outside the closure leaves the record current; bytes already
    on disk are kept while they describe the same closure and ceiling.
    """
    record = {
        "schema": QUALIFICATION_SCHEMA,
        "instrument": instrument,
        "run_id": run,
        "disposition": ceiling(findings),
        "subject_digest": subject_module.subject_digest(root, instrument, run),
        "trinity_commit": git_gitlink(root, TRINITY_DIR) or SHA40_ZERO,
        "generated_at": _now_iso(now),
        "producer": git_head_author_email(root) or "unknown",
        "approver": UNSIGNED_APPROVER,
    }
    path = runs_module.run_dir(root, instrument, run) / DISPOSITION_RECORD
    existing = load_qualification(path)
    if existing is not None and all(
        existing[name] == record[name]
        for name in ("disposition", "subject_digest", "trinity_commit", "instrument", "run_id")
    ):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(record, sort_keys=True).encode("utf-8"))
    return path


def load_qualification(path: Path) -> dict[str, str] | None:
    """The closed v2 qualification record at ``path``, or None when absent or malformed."""
    try:
        value = json.loads(path.read_text("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != QUALIFICATION_FIELDS:
        return None
    if not all(isinstance(item, str) and item for item in value.values()):
        return None
    if value["schema"] != QUALIFICATION_SCHEMA:
        return None
    return {key: str(item) for key, item in value.items()}


def _record_still_current(
    root: Path, path: Path, *, minted: dict[str, str], now: datetime | None
) -> bool:
    try:
        value = json.loads(path.read_text("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    if not isinstance(value, dict) or not all(
        isinstance(item, str) and item for item in value.values()
    ):
        return False
    existing = {str(key): str(item) for key, item in value.items()}
    head = minted["tree_sha"]
    if head == SHA40_ZERO:
        return False
    fields = set(existing)
    if fields == DISPOSITION_FIELDS:
        return (
            existing["disposition"] == minted["disposition"]
            and existing["trinity_commit"] == minted["trinity_commit"]
            and existing["bundle_digest"] == minted["bundle_digest"]
            and binds_head(root, existing["tree_sha"], head)
        )
    if fields in (FINAL_DISPOSITION_FIELDS, GROUP_DISPOSITION_FIELDS):
        try:
            expires = parse_instant(existing["expires_at"], "expires_at")
        except ReleaseEvidenceError:
            return False
        instant = datetime.now(UTC) if now is None else now.astimezone(UTC)
        return (
            minted["disposition"] == SHIP_ELIGIBLE
            and existing["bundle_set_digest"] == minted["bundle_digest"]
            and instant < expires
            and binds_head(root, existing["candidate_commit"], head)
        )
    return False


def load_record(path: Path) -> dict[str, str]:
    try:
        value = json.loads(path.read_text("utf-8"))
    except FileNotFoundError as exc:
        raise GateError(f"no disposition record at {path}") from exc
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise GateError(f"disposition record at {path} is unreadable: {exc}") from exc
    if not isinstance(value, dict) or set(value) != DISPOSITION_FIELDS:
        raise GateError(f"disposition record at {path} does not carry the closed field set")
    if not all(isinstance(item, str) and item for item in value.values()):
        raise GateError(f"disposition record at {path} carries an empty field")
    return {key: str(item) for key, item in value.items()}


def load_qualified_record(root: Path, path: Path) -> dict[str, str]:
    """The unsigned record, or an already promoted one read back as its own qualified source."""
    try:
        return load_record(path)
    except GateError as unsigned_error:
        try:
            value = json.loads(path.read_text("utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            raise unsigned_error from None
        if not isinstance(value, dict) or set(value) not in (
            FINAL_DISPOSITION_FIELDS,
            GROUP_DISPOSITION_FIELDS,
        ):
            raise unsigned_error from None
        final = {str(key): str(item) for key, item in value.items()}
        return {
            "disposition": SHIP_ELIGIBLE if final["disposition"] == SHIP else final["disposition"],
            "tree_sha": final["candidate_commit"],
            "trinity_commit": git_gitlink(root, TRINITY_DIR) or SHA40_ZERO,
            "bundle_digest": final["bundle_set_digest"],
            "generated_at": final["issued_at"],
            "producer": final.get("producer") or git_head_author_email(root) or "unknown",
            "approver": final.get("approver", UNSIGNED_APPROVER),
        }


def promote(
    root: Path,
    *,
    instrument: str,
    approver: str | None = None,
    now: datetime | None = None,
    trust_dir: str | Path | None = None,
    release: str | None = None,
) -> Path:
    """Turn a qualified record into a domain-separated final release record.

    With ``release`` the final record lands under ``<harness>/releases/<id>/`` as a frozen
    candidate; the qualified source record still binds HEAD, which becomes that candidate.
    """

    if instrument not in DISPOSITION_PAYLOAD_TYPES:
        raise GateError(f"instrument {instrument!r} has no final release disposition domain")
    source = root / INSTRUMENT_HARNESS[instrument] / DISPOSITION_RECORD
    path = release_dir(root, instrument, release) / DISPOSITION_RECORD
    record = load_qualified_record(root, source if release is not None else path)
    if record["disposition"] != SHIP_ELIGIBLE:
        raise GateError(
            f"record is {record['disposition']}, not {SHIP_ELIGIBLE}; only an eligible record "
            "can be promoted"
        )
    named_approver = approver.strip() if approver is not None else None
    if named_approver is not None:
        if not named_approver or named_approver == UNSIGNED_APPROVER:
            raise GateError("promote needs a named approver")
        if named_approver == record["producer"]:
            raise GateError("approver equals producer; a disposition is never self-approved")
        head_author = git_head_author_email(root)
        if head_author is not None and named_approver == head_author:
            raise GateError(f"approver equals the HEAD author {head_author}")
    head = git_head(root)
    if head is None:
        raise GateError("HEAD cannot be resolved, so the record cannot bind a tree")
    if not binds_head(root, record["tree_sha"], head):
        raise GateError("qualified record does not bind HEAD through gate-sealing commits")
    if bundle_set_digest(root) != record["bundle_digest"]:
        raise GateError("samples/ bytes moved since the record was minted; run the gate again")
    try:
        trust = load_release_trust(root, trust_dir)
        samples = root / SAMPLES_DIR
        uuids = sorted(
            entry.name for entry in samples.iterdir() if entry.is_dir() and UUID.match(entry.name)
        )
        snapshot = release_snapshot_digest(samples, uuids)
    except (OSError, BundleIdentityError, ValueError) as exc:
        raise GateError(f"final release policy cannot be loaded or bound: {exc}") from exc
    issued = datetime.now(UTC) if now is None else now.astimezone(UTC)
    expires = issued + timedelta(seconds=trust.disposition_max_age_seconds)
    common = {
        "instrument": instrument,
        "disposition": SHIP,
        "project_id": trust.project_id,
        "repository_id": trust.repository_id,
        "snapshot_digest": snapshot,
        "bundle_set_digest": bundle_set_digest(root),
        "candidate_commit": head,
        "verifier_sha": trust.verifier_sha,
        "issued_at": _now_iso(issued),
        "expires_at": _now_iso(expires),
    }
    if named_approver is None:
        role_names = {role.name for role in trust.root.roles}
        required = {GROUP_PRODUCER_ROLE, GROUP_APPROVER_ROLE}
        if not required <= role_names:
            missing = ", ".join(sorted(required - role_names))
            raise GateError(f"group promotion requires external governance roles: {missing}")
        promoted = {
            "schema": GROUP_DISPOSITION_SCHEMA,
            **common,
            "producer_role": GROUP_PRODUCER_ROLE,
            "approver_role": GROUP_APPROVER_ROLE,
        }
    else:
        promoted = {
            "schema": DISPOSITION_SCHEMA,
            **common,
            "producer": record["producer"],
            "approver": named_approver,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonicalize(promoted))
    return path


def release_dir(root: Path, instrument: str, release: str | None) -> Path:
    """Where an instrument's final record lives: the harness, or a frozen release candidate.

    A release candidate ``<harness>/releases/<id>/`` binds one candidate commit and export
    snapshot forever; later movement of ``main`` neither invalidates nor extends it.
    """
    harness = root / INSTRUMENT_HARNESS[instrument]
    if release is None:
        return harness
    if RELEASE_ID.fullmatch(release) is None or ".." in release:
        raise GateError(f"release id {release!r} is outside [a-z0-9][a-z0-9.-]{{2,63}}")
    return harness / RELEASES_DIR / release


def signing_instruction(_root: Path, instrument: str, release: str | None = None) -> str:
    harness = INSTRUMENT_HARNESS[instrument]
    if release is not None:
        harness = f"{harness}/{RELEASES_DIR}/{release}"
    record = f"./candidate-data/{harness}/{DISPOSITION_RECORD}"
    envelope = f"./candidate-data/{harness}/{DISPOSITION_ENVELOPE}"
    release_flag = "" if release is None else f" --release {release}"
    return (
        "a signer administrator must independently obtain, review, pin, and mount a read-only "
        "Trinity signer checkout outside the candidate. The producer and approver each use only "
        "that checkout with their own external key; the candidate is data and is never executed:\n"
        "  TRUSTED_SIGNER_CODE_DIR=./trusted-signer\n"
        "  TRUSTED_RELEASE_TRUST_DIR=./release-trust\n"
        "  CANDIDATE_ROOT=./candidate-data\n"
        "  PRIVATE_KEY=./.secrets/approver-key\n"
        "  mkdir -p ./.trinity-runtime && chmod 700 ./.trinity-runtime\n"
        '  python3 -I "./trusted-signer/tools/gate.py" sign-partial '
        '"--root=$CANDIDATE_ROOT" '
        f'--instrument {instrument}{release_flag} --trust-dir "$TRUSTED_RELEASE_TRUST_DIR" '
        '--key "$PRIVATE_KEY" --output ./.trinity-runtime/producer-or-approver.dsse\n'
        "Transfer only their DSSE envelopes, then combine them without either private key:\n"
        '  python3 -I "./trusted-signer/tools/gate.py" cosign-assemble '
        '"--root=$CANDIDATE_ROOT" '
        f"--instrument {instrument}{release_flag} --envelope ./.trinity-runtime/signer-1.dsse "
        f"--envelope ./.trinity-runtime/signer-2.dsse --output {envelope}\n"
        f'  git -C "$CANDIDATE_ROOT" add {record} {envelope} && '
        f"git -C \"$CANDIDATE_ROOT\" commit -m 'seal {instrument} disposition'"
    )


def _trusted_signer_root(candidate_root: Path) -> tuple[Path, Path]:
    try:
        candidate = candidate_root.absolute().resolve(strict=True)
        signer = Path(__file__).resolve(strict=True).parent.parent
    except OSError as exc:
        raise GateError(f"signer or candidate root cannot be resolved: {exc}") from exc
    if signer == candidate or candidate in signer.parents:
        raise GateError("trusted signer code directory must live outside the candidate tree")
    return candidate, signer


def _candidate_commit_is_sealed(root: Path, candidate_commit: str) -> bool:
    if re.fullmatch(r"[0-9a-f]{40}", candidate_commit) is None:
        return False
    try:
        with SafeGitRepository(root) as repository:
            head = repository.head
            if not repository.is_ancestor(candidate_commit, head):
                return False
            changed = repository.changed_paths(candidate_commit, head)
            if changed is None or (changed and not seals_only(changed)):
                return False
            status = repository.status_porcelain()
    except SafeGitError:
        return False
    if status is None:
        return False
    dirty = {
        line[PORCELAIN_STATUS_PREFIX:]
        for line in status.splitlines()
        if len(line) > PORCELAIN_STATUS_PREFIX
    }
    return not dirty or seals_only(dirty)


def _validated_signing_payload(
    root: Path,
    *,
    instrument: str,
    trust_dir: str | Path,
    now: datetime | None,
    release: str | None = None,
) -> tuple[Path, bytes]:
    candidate, _signer = _trusted_signer_root(root)
    if instrument not in DISPOSITION_PAYLOAD_TYPES:
        raise GateError(f"instrument {instrument!r} has no final release disposition domain")
    record_path = release_dir(candidate, instrument, release) / DISPOSITION_RECORD
    try:
        payload = safe_read_bytes(record_path, maximum=MAX_EVIDENCE_BYTES)
        value = parse_json(payload)
        if not isinstance(value, dict):
            raise GateError("final disposition is not an object")
        schema = value.get("schema")
        expected_fields = (
            FINAL_DISPOSITION_FIELDS
            if schema == DISPOSITION_SCHEMA
            else GROUP_DISPOSITION_FIELDS
            if schema == GROUP_DISPOSITION_SCHEMA
            else frozenset()
        )
        if set(value) != expected_fields:
            raise GateError(
                "final disposition does not carry a closed v2 field set or v3 field set"
            )
        if any(not isinstance(item, str) or not item for item in value.values()):
            raise GateError("final disposition carries an empty or non-string field")
        record = {str(key): str(item) for key, item in value.items()}
        if canonicalize(value) != payload:
            raise GateError("final disposition is not canonical JSON")
        trust = load_release_trust(candidate, trust_dir)
        if record["instrument"] != instrument or record["disposition"] != SHIP:
            raise GateError("final disposition schema, instrument, or SHIP domain is invalid")
        if (
            record["project_id"] != trust.project_id
            or record["repository_id"] != trust.repository_id
            or record["verifier_sha"] != trust.verifier_sha
        ):
            raise GateError("final disposition does not match external release trust")
        samples = candidate / SAMPLES_DIR
        uuids = sorted(
            entry.name for entry in samples.iterdir() if entry.is_dir() and UUID.match(entry.name)
        )
        snapshot = release_snapshot_digest(samples, uuids)
        bundle_digest = canonical_bundle_set_digest(samples, uuids)
        if record["snapshot_digest"] != snapshot or record["bundle_set_digest"] != bundle_digest:
            raise GateError("final disposition does not bind the complete candidate snapshot")
        if not _candidate_commit_is_sealed(candidate, record["candidate_commit"]):
            raise GateError("final disposition candidate commit is not the sealed snapshot")
        evaluation_time = datetime.now(UTC) if now is None else now.astimezone(UTC)
        issued = parse_instant(record["issued_at"], f"{instrument} issued_at")
        expires = parse_instant(record["expires_at"], f"{instrument} expires_at")
        if not issued <= evaluation_time < expires:
            raise GateError("final disposition time window is invalid")
        if evaluation_time - issued > timedelta(seconds=trust.disposition_max_age_seconds):
            raise GateError("final disposition is older than external policy permits")
        if expires - issued > timedelta(seconds=trust.disposition_max_age_seconds):
            raise GateError("final disposition expiry exceeds external policy")
        if schema == DISPOSITION_SCHEMA:
            if record["producer"] == record["approver"]:
                raise GateError("final disposition producer and approver must be distinct")
        elif (
            record["producer_role"] != GROUP_PRODUCER_ROLE
            or record["approver_role"] != GROUP_APPROVER_ROLE
        ):
            raise GateError("final disposition group roles are not the pinned gate roles")
    except (OSError, BundleIdentityError, ReleaseEvidenceError) as exc:
        raise GateError(f"final disposition validation failed: {exc}") from exc
    return candidate, payload


def _require_external_key(candidate: Path, key_path: Path) -> None:
    try:
        key = key_path.absolute().resolve(strict=True)
    except OSError as exc:
        raise GateError(f"private key is unavailable: {exc}") from exc
    if key == candidate or candidate in key.parents:
        raise GateError("private key must live outside the candidate tree")


def sign_partial_envelope(
    root: Path,
    *,
    instrument: str,
    trust_dir: str | Path,
    key_path: Path,
    output: Path,
    backend: SignatureBackend | None = None,
    now: datetime | None = None,
    release: str | None = None,
) -> Path:
    """Validate then sign one exact disposition using only this trusted checkout's code."""

    candidate, payload = _validated_signing_payload(
        root,
        instrument=instrument,
        trust_dir=trust_dir,
        release=release,
        now=now,
    )
    _require_external_key(candidate, key_path)
    envelope = sign_envelope(
        backend or SshKeygenBackend(),
        _payload_type_for_record(payload, instrument),
        payload,
        key_path=key_path,
    )
    output.write_bytes(envelope.to_json())
    return output


def _payload_type_for_record(payload: bytes, instrument: str) -> str:
    value = parse_json(payload)
    if not isinstance(value, dict):
        raise GateError("final disposition is not an object")
    if value.get("schema") == DISPOSITION_SCHEMA:
        return DISPOSITION_PAYLOAD_TYPES[instrument]
    if value.get("schema") == GROUP_DISPOSITION_SCHEMA:
        return GROUP_DISPOSITION_PAYLOAD_TYPES[instrument]
    # Assembly remains backwards compatible with pre-schema-test callers. The trusted signer and
    # release verifier still reject any such record before key access or authorization.
    return DISPOSITION_PAYLOAD_TYPES[instrument]


def _matching_envelope(path: Path, *, payload_type: str, payload: bytes) -> Envelope:
    parsed = parse_envelope(safe_read_bytes(path, maximum=MAX_EVIDENCE_BYTES))
    if parsed.envelope is None:
        raise GateError(f"cannot parse partial envelope {path}: {parsed.detail}")
    if parsed.envelope.payload_type != payload_type or parsed.envelope.payload != payload:
        raise GateError(f"partial envelope {path} does not sign this instrument record")
    return parsed.envelope


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def assemble_cosigned_envelope(
    root: Path,
    *,
    instrument: str,
    output: Path,
    envelope_paths: Sequence[Path] = (),
    producer_envelope: Path | None = None,
    approver_envelope: Path | None = None,
    release: str | None = None,
) -> Path:
    """Combine two independently generated signatures without reading private keys."""

    payload = (release_dir(root, instrument, release) / DISPOSITION_RECORD).read_bytes()
    expected_type = _payload_type_for_record(payload, instrument)
    envelopes: list[Envelope] = []
    sources = list(envelope_paths)
    sources += [path for path in (producer_envelope, approver_envelope) if path is not None]
    if output.is_file() and output not in sources:
        sources.insert(0, output)
    if not sources:
        raise GateError("cosign assembly requires at least one partial or existing envelope")
    for path in sources:
        envelopes.append(_matching_envelope(path, payload_type=expected_type, payload=payload))
    signatures = tuple(signature for item in envelopes for signature in item.signatures)
    if len({(signature.keyid, signature.sig) for signature in signatures}) != len(signatures):
        raise GateError("partial envelopes contain duplicate signatures")
    _atomic_write(output, Envelope(expected_type, payload, signatures).to_json())
    return output


def signing_status(
    root: Path,
    *,
    instrument: str,
    trust_dir: str | Path,
    envelope_paths: Sequence[Path],
    complete_envelope: Path | None = None,
    backend: SignatureBackend | None = None,
    now: datetime | None = None,
    release: str | None = None,
) -> dict[str, object]:
    """Authenticate persisted v3 partials and report role quorum without reading a key."""

    candidate, payload = _validated_signing_payload(
        root, instrument=instrument, trust_dir=trust_dir, now=now, release=release
    )
    value = parse_json(payload)
    if not isinstance(value, dict) or value.get("schema") != GROUP_DISPOSITION_SCHEMA:
        raise GateError("signing-status is available only for group disposition v3")
    trust = load_release_trust(candidate, trust_dir)
    payload_type = GROUP_DISPOSITION_PAYLOAD_TYPES[instrument]
    sources = list(envelope_paths)
    if complete_envelope is not None:
        sources.append(complete_envelope)
    signatures = tuple(
        signature
        for path in sources
        for signature in _matching_envelope(
            path, payload_type=payload_type, payload=payload
        ).signatures
    )
    principals: tuple[str, ...] = ()
    if signatures:
        verified = verify_envelope(
            backend or SshKeygenBackend(),
            Envelope(payload_type, payload, signatures),
            expected_payload_type=payload_type,
            allowed_signers_path=trust.allowed_signers,
            evaluation_time=datetime.now(UTC) if now is None else now.astimezone(UTC),
        )
        if not verified.accepted:
            reason = verified.reason_value
            detail = verified.detail
            raise GateError(f"signature authentication refused: {reason}: {detail}")
        principals = verified.principals
    evaluation_time = datetime.now(UTC) if now is None else now.astimezone(UTC)
    producer = _role_progress(trust, GROUP_PRODUCER_ROLE, principals, evaluation_time, ())
    producer_principals = tuple(str(item) for item in producer["principals"])
    approver = _role_progress(
        trust, GROUP_APPROVER_ROLE, principals, evaluation_time, producer_principals
    )
    return {
        "schema": "trinity.signing-status/v1",
        "instrument": instrument,
        "disposition_schema": GROUP_DISPOSITION_SCHEMA,
        "payload_type": payload_type,
        "authenticated_principals": list(principals),
        "roles": {GROUP_PRODUCER_ROLE: producer, GROUP_APPROVER_ROLE: approver},
        "complete": bool(producer["complete"] and approver["complete"]),
    }


def _role_progress(
    trust: ReleaseTrust,
    role_name: str,
    principals: tuple[str, ...],
    evaluation_time: datetime,
    excluded: tuple[str, ...],
) -> RoleProgress:
    root = trust.root
    role = next((item for item in root.roles if item.name == role_name), None)
    if role is None:
        raise GateError(f"external governance does not define role {role_name}")
    expiry = {item.name: item.expires_at for item in root.principals}
    revoked = {item.principal for item in root.revocations if evaluation_time >= item.revoked_at}
    expired: set[str] = set()
    for principal in role.principals:
        expires_at = expiry[principal]
        if expires_at is not None and evaluation_time >= expires_at:
            expired.add(principal)
    eligible = sorted(
        set(principals).intersection(role.principals) - set(excluded) - revoked - expired
    )
    return {
        "role": role_name,
        "threshold": role.threshold,
        "principals": eligible,
        "missing": max(0, role.threshold - len(eligible)),
        "complete": len(eligible) >= role.threshold,
    }


# ---- the parent check -------------------------------------------------------------


def finding(path: object, line: int, message: str, code: str) -> Finding:
    return Finding(code, Severity.ERROR, str(path), line, message)


def report_token(text: str) -> str | None:
    """The first uppercase token on the first non-empty line under ``## Disposition``."""

    in_section = False
    for line in text.split("\n"):
        if line.startswith("## "):
            in_section = H2_DISPOSITION.match(line) is not None
            continue
        if not in_section or not line.strip():
            continue
        match = DISPOSITION_TOKEN.search(line)
        return match.group(0).rstrip(":") if match is not None else None
    return None


def token_rank(token: str) -> int | None:
    if token in TOKEN_RANK:
        return TOKEN_RANK[token]
    head = token.split(":", 1)[0]
    return TOKEN_RANK.get(head)


def _load_receipts(directory: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text("utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if isinstance(value, dict) and set(value) == RECEIPT_FIELDS:
            out.append(value)
    return out


def _run_receipt_findings(root_path: Path) -> list[Finding]:
    """Every run report needs a report receipt binding the run's current subject closure."""
    out: list[Finding] = []
    for instrument in INSTRUMENT_HARNESS:
        for run in runs_module.list_runs(root_path, instrument):
            directory = runs_module.run_dir(root_path, instrument, run.run_id)
            report_path = directory / "report.md"
            if not report_path.is_file():
                continue
            try:
                expected = subject_module.subject_digest(root_path, instrument, run.run_id)
            except subject_module.SubjectError as exc:
                out.append(
                    finding(
                        directory, 0, f"subject closure is unreadable: {exc}", GATE_SUBJECT_UNBOUND
                    )
                )
                continue
            bound = [
                receipt
                for receipt in _load_run_receipts(directory / RECEIPT_DIR)
                if receipt.get("moment") == "report"
                and receipt.get("instrument") == instrument
                and receipt.get("subject_digest") == expected
            ]
            if not bound:
                out.append(
                    finding(
                        report_path,
                        0,
                        f"run report exists with no report-moment receipt binding its subject "
                        f"closure {expected[:12]}; run trinity/tools/gate.py --moment report "
                        f"--run {run.run_id} before writing the report",
                        GATE_PREFLIGHT_MISSING,
                    )
                )
                continue
            try:
                token = report_token(report_path.read_text("utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
            record = load_qualification(directory / DISPOSITION_RECORD)
            minted_token = (
                record["disposition"] if record is not None else str(bound[-1].get("ceiling", ""))
            )
            stated = token_rank(token) if token is not None else None
            minted = token_rank(minted_token)
            if stated is not None and minted is not None and stated > minted:
                out.append(
                    finding(
                        report_path,
                        0,
                        f"run report states {token} above the minted record {minted_token}; "
                        "the disposition line is copied from the record, never raised",
                        GATE_DISPOSITION_MISMATCH,
                    )
                )
    return out


def _load_run_receipts(directory: Path) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text("utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if isinstance(value, dict) and set(value) == RUN_RECEIPT_FIELDS:
            out.append(value)
    return out


def check_gate_receipts(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """A root report needs a report receipt binding HEAD and a token at or below its record."""

    root_path = Path(root)
    head = git_head(root_path)
    if head is None:
        return []
    out: list[Finding] = []
    out += _run_receipt_findings(root_path)
    for instrument, report in INSTRUMENT_REPORT.items():
        report_path = root_path / report
        if not report_path.is_file():
            continue
        try:
            rendered = report_path.read_text("utf-8").startswith(GENERATED_BANNER)
        except (OSError, UnicodeDecodeError):
            rendered = False
        if rendered:
            continue
        harness = root_path / INSTRUMENT_HARNESS[instrument]
        receipts = [
            receipt
            for receipt in _load_receipts(harness / RECEIPT_DIR)
            if receipt.get("moment") == "report"
            and receipt.get("instrument") == instrument
            and isinstance(receipt.get("tree_sha"), str)
            and binds_head(root_path, str(receipt["tree_sha"]), head)
        ]
        if not receipts:
            out.append(
                finding(
                    report_path,
                    0,
                    f"{report} exists with no report-moment gate receipt under "
                    f"{INSTRUMENT_HARNESS[instrument]}/{RECEIPT_DIR}/ binding HEAD {head[:12]}; "
                    "run trinity/tools/gate.py --moment report before writing the report",
                    GATE_PREFLIGHT_MISSING,
                )
            )
            continue
        try:
            text = report_path.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        token = report_token(text)
        if token is None:
            continue
        try:
            record = load_record(harness / DISPOSITION_RECORD)
        except GateError:
            record = {"disposition": str(receipts[-1].get("ceiling", ""))}
        stated = token_rank(token)
        minted = token_rank(record["disposition"])
        if stated is not None and minted is not None and stated > minted:
            out.append(
                finding(
                    report_path,
                    0,
                    f"{report} states {token} above the minted record {record['disposition']}; "
                    "the disposition line is copied from the record, never raised",
                    GATE_DISPOSITION_MISMATCH,
                )
            )
    hook = root_path / HOOK_PATH
    try:
        hook_text = hook.read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        hook_text = None
    if hook_text is None or HOOK_MARKER not in hook_text:
        out.append(
            finding(
                hook,
                0,
                f"{HOOK_PATH} is absent or does not invoke {HOOK_MARKER}; scaffold it from "
                "trinity/templates/pre-push and set core.hooksPath to .githooks",
                GATE_HOOK_MISSING,
            )
        )
    return out


# ---- install ------------------------------------------------------------------------


def codeowners_team() -> str:
    return os.environ.get(CODEOWNERS_TEAM_ENV, "").strip() or DEFAULT_CODEOWNERS_TEAM


def codeowners_lines() -> list[str]:
    team = codeowners_team()
    return [f"{path} {team}" for path in CODEOWNED_PATHS]


def parse_github_repo(url: str) -> str | None:
    """``owner/name`` from any GitHub remote spelling, including ``org-NNN@`` deploy hosts."""

    match = GITHUB_REMOTE.search(url.strip())
    if match is None:
        return None
    return f"{match.group('owner')}/{match.group('name')}"


def parent_repo(root: Path) -> str | None:
    url = _git(root, "remote", "get-url", "origin")
    return parse_github_repo(url) if url else None


def gated_submodule_repos(root: Path) -> list[str]:
    """Declared repositories under the five protected roots, in roster order.

    Protect ``.memory``, ``samples``, ``delivery``, ``harness``, and optional ``staging``;
    exclude the vendored ``trinity`` repository.
    """

    try:
        text = (root / ".gitmodules").read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    sections, _malformed = layout.parse_gitmodules(text)
    repos: list[str] = []
    for name in GATED_SUBMODULES:
        for section in sections:
            if section.path.strip("/").split("/", 1)[0] != name:
                continue
            repo = parse_github_repo(section.url)
            if repo is not None and repo not in repos:
                repos.append(repo)
    return repos


def protection_body() -> dict[str, object]:
    return {
        "required_status_checks": {"strict": True, "contexts": list(REQUIRED_CHECKS)},
        "enforce_admins": True,
        # Direct pushes to main are lawful: many runners push their reconciled trees
        # straight to main and the required status check on the pushed commit is the
        # admission. No pull request review is required.
        "required_pull_request_reviews": None,
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_linear_history": True,
    }


@dataclass(frozen=True, slots=True)
class GhResult:
    ok: bool
    stdout: str
    stderr: str


def _gh(*argv: str, stdin: str | None = None) -> GhResult | None:
    """Run the GitHub CLI; ``None`` when it is not installed."""

    executable = shutil.which("gh")
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [executable, *argv],
            capture_output=True,
            check=False,
            input=stdin,
            shell=False,
            text=True,
            timeout=GH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GhResult(False, "", f"{exc.__class__.__name__}: {exc}")
    return GhResult(completed.returncode == 0, completed.stdout, completed.stderr)


def _protection_readback_ok(readback: object) -> tuple[bool, str]:
    if not isinstance(readback, dict):
        return False, "read-back is not a JSON object"
    checks = readback.get("required_status_checks")
    contexts = checks.get("contexts") if isinstance(checks, dict) else None
    if not isinstance(contexts, list):
        return False, "read-back carries no required status checks"
    missing = sorted(set(REQUIRED_CHECKS) - {str(item) for item in contexts})
    if missing:
        return False, f"read-back lacks required checks {', '.join(missing)}"
    admins = readback.get("enforce_admins")
    if not (isinstance(admins, dict) and admins.get("enabled") is True):
        return False, "read-back does not enforce the rules for administrators"
    force = readback.get("allow_force_pushes")
    if isinstance(force, dict) and force.get("enabled") is True:
        return False, "read-back allows force pushes"
    return True, ""


def _receipt_path(root: Path, repo: str) -> Path:
    return root / INSTALL_DIR / PROTECTION_DIR / (repo.replace("/", "-") + ".json")


def _receipt_unchanged(path: Path, receipt: dict[str, object]) -> bool:
    """True when the receipt on disk differs only by its ``applied_at`` stamp.

    A preflight that read the same protection back must not rewrite the receipt, or every
    gate run dirties the tree it is about to grade.
    """
    try:
        existing = json.loads(path.read_text("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    if not isinstance(existing, dict):
        return False
    return {key: value for key, value in existing.items() if key != "applied_at"} == {
        key: value for key, value in receipt.items() if key != "applied_at"
    }


def _write_protection_receipt(
    root: Path,
    repo: str,
    *,
    applied: bool,
    reason: str,
    contexts: Sequence[str],
    now: datetime | None,
) -> Path:
    path = _receipt_path(root, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": PROTECTION_SCHEMA,
        "repo": repo,
        "branch": PROTECTED_BRANCH,
        "applied": applied,
        "reason": reason,
        "required_checks": list(REQUIRED_CHECKS),
        "read_back_contexts": list(contexts),
        "applied_at": _now_iso(now),
    }
    if _receipt_unchanged(path, receipt):
        return path
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", "utf-8")
    return path


def _gh_json(*argv: str) -> object | None:
    result = _gh("api", *argv)
    if result is None or not result.ok:
        return None
    try:
        parsed: object = json.loads(result.stdout)
    except ValueError:
        return None
    return parsed


def _readback_contexts(readback: object) -> list[str]:
    if not isinstance(readback, dict):
        return []
    checks = readback.get("required_status_checks")
    if isinstance(checks, dict) and isinstance(checks.get("contexts"), list):
        return [str(item) for item in checks["contexts"]]
    return []


def _ruleset_bypass_ok(repo: str, rule: dict[str, object]) -> tuple[bool, str]:
    """A ruleset enforces its rules for administrators only when nobody may bypass it."""
    ruleset_id = rule.get("ruleset_id")
    source_type = str(rule.get("ruleset_source_type", ""))
    if not isinstance(ruleset_id, int) or isinstance(ruleset_id, bool):
        return False, "ruleset rule names no ruleset id"
    if source_type == "Organization":
        endpoint = f"orgs/{repo.split('/', 1)[0]}/rulesets/{ruleset_id}"
    else:
        endpoint = f"repos/{repo}/rulesets/{ruleset_id}"
    ruleset = _gh_json(endpoint)
    if not isinstance(ruleset, dict):
        return False, f"ruleset {ruleset_id} is unreadable, so its bypass actors are unverified"
    if ruleset.get("enforcement") != "active":
        return False, f"ruleset {ruleset_id} is not actively enforced"
    actors = ruleset.get("bypass_actors")
    if isinstance(actors, list) and actors:
        return False, f"ruleset {ruleset_id} lets {len(actors)} actor(s) bypass it"
    return True, ""


def _ruleset_rules_ok(repo: str, rules: object) -> tuple[bool, str, list[str]]:
    """Evaluate the effective branch rules GitHub reports from rulesets on ``main``."""
    if not isinstance(rules, list):
        return False, "branch rules are not a JSON array", []
    by_type: dict[str, dict[str, object]] = {}
    for rule in rules:
        if isinstance(rule, dict) and isinstance(rule.get("type"), str):
            by_type[rule["type"]] = rule
    checks = by_type.get("required_status_checks")
    parameters = checks.get("parameters") if checks is not None else None
    required = parameters.get("required_status_checks") if isinstance(parameters, dict) else None
    if not isinstance(required, list):
        return False, "rulesets require no status checks", []
    contexts = [
        str(item.get("context"))
        for item in required
        if isinstance(item, dict) and "context" in item
    ]
    missing = sorted(set(REQUIRED_CHECKS) - set(contexts))
    if missing:
        return False, f"rulesets lack required checks {', '.join(missing)}", contexts
    if "non_fast_forward" not in by_type:
        return False, "rulesets allow force pushes", contexts
    for rule_type in ("required_status_checks", "non_fast_forward"):
        ok, why = _ruleset_bypass_ok(repo, by_type[rule_type])
        if not ok:
            return False, why, contexts
    return True, "", contexts


def read_protection(repo: str) -> tuple[bool, str, list[str], str]:
    """What protects ``main`` of ``repo`` now: classic protection first, then rulesets.

    Returns ``(in_force, reason, read_back_contexts, mechanism)``. Classic protection is read
    back through the branch protection endpoint; when that endpoint refuses or reports a gap,
    the effective rules endpoint is read, because a ruleset applied by an administrator
    protects the branch without populating classic protection.
    """
    classic = _gh_json(f"repos/{repo}/branches/{PROTECTED_BRANCH}/protection")
    ok, why = _protection_readback_ok(classic)
    if ok:
        return (
            True,
            "in force: classic protection read back",
            _readback_contexts(classic),
            "classic",
        )
    classic_reason = why if classic is not None else "classic protection is absent or unreadable"
    rules = _gh_json(f"repos/{repo}/rules/branches/{PROTECTED_BRANCH}")
    ruleset_ok, ruleset_why, contexts = _ruleset_rules_ok(repo, rules)
    if ruleset_ok:
        return True, "in force: rulesets read back", contexts, "ruleset"
    if rules is None:
        ruleset_why = "branch rules are unreadable"
    return False, f"{classic_reason}; {ruleset_why}", contexts, "none"


def apply_protection(root: Path, repo: str, *, now: datetime | None = None) -> tuple[bool, str]:
    """Ensure branch protection on ``main`` of ``repo`` and write the receipt.

    Protection already in force, through classic protection or through rulesets, is read back
    and receipted without a write, so a principal without administrative rights passes when an
    administrator has already protected the branch. Only when nothing stands does install PUT
    classic protection, which GitHub allows administrators alone.
    """

    auth = _gh("auth", "status")
    if auth is None:
        reason = "gh-absent: the GitHub CLI is not installed"
        _write_protection_receipt(root, repo, applied=False, reason=reason, contexts=(), now=now)
        return False, reason
    if not auth.ok:
        reason = "gh-unauthenticated: run gh auth login as a principal that can read the repo"
        _write_protection_receipt(root, repo, applied=False, reason=reason, contexts=(), now=now)
        return False, reason
    in_force, reason, contexts, _mechanism = read_protection(repo)
    if in_force:
        _write_protection_receipt(
            root, repo, applied=True, reason=reason, contexts=contexts, now=now
        )
        return True, reason
    standing = reason
    endpoint = f"repos/{repo}/branches/{PROTECTED_BRANCH}/protection"
    put = _gh("api", "-X", "PUT", endpoint, "--input", "-", stdin=json.dumps(protection_body()))
    if put is None or not put.ok:
        detail = (put.stderr if put is not None else "").strip().splitlines()
        reason = (
            "gh-refused: "
            + (detail[-1] if detail else "the API refused the request")
            + f"; nothing already in force ({standing}); an administrator applies classic "
            "protection or an active ruleset with no bypass actors, and the next preflight "
            "reads it back"
        )
        _write_protection_receipt(root, repo, applied=False, reason=reason, contexts=(), now=now)
        return False, reason
    in_force, reason, contexts, _mechanism = read_protection(repo)
    reason = "applied and read back" if in_force else f"read-back-mismatch: {reason}"
    _write_protection_receipt(
        root, repo, applied=in_force, reason=reason, contexts=contexts, now=now
    )
    return in_force, reason


@dataclass(frozen=True, slots=True)
class InstallReport:
    written: tuple[str, ...]
    unchanged: tuple[str, ...]
    hooks_path_set: bool
    repos: tuple[str, ...]
    protected: tuple[str, ...]
    unprotected: tuple[tuple[str, str], ...]

    @property
    def complete(self) -> bool:
        return not self.unprotected and bool(self.repos)


def _install_file(
    root: Path, relative: str, content: bytes, *, executable: bool, dry_run: bool
) -> bool:
    """Write ``content`` at ``relative`` when it differs. Returns True when written."""

    target = root / relative
    current = target.read_bytes() if target.is_file() else None
    if current == content:
        if executable and not dry_run and not os.access(target, os.X_OK):
            target.chmod(target.stat().st_mode | 0o111)
        return False
    if dry_run:
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    if executable:
        target.chmod(target.stat().st_mode | 0o111)
    return True


def door_templates() -> list[tuple[str, Path]]:
    """Every front door the preflight writes, as ``(parent-relative path, template)``."""

    doors: list[tuple[str, Path]] = []
    for template in sorted(DOOR_TEMPLATES_DIR.glob("commands/*.md")):
        doors.append((f"{COMMAND_DOOR_DIR}/{template.name}", template))
    for template in sorted(DOOR_TEMPLATES_DIR.glob("skills/*/SKILL.md")):
        doors.append((f"{SKILL_DOOR_DIR}/{template.parent.name}/SKILL.md", template))
    return doors


def hook_templates() -> list[tuple[str, Path]]:
    """Installed parent-relative paths paired with their canonical hook templates."""
    return [(f"{HOOK_DIR}/{name}", TEMPLATES_DIR / name) for name in HOOK_TEMPLATES]


def _merge_lines(target: Path, required: list[str], *, dry_run: bool) -> bool:
    existing = target.read_text("utf-8") if target.is_file() else ""
    present = {line.strip() for line in existing.splitlines()}
    missing = [line for line in required if line not in present]
    if not missing:
        return False
    if dry_run:
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    body = existing if not existing or existing.endswith("\n") else existing + "\n"
    target.write_text(body + "\n".join(missing) + "\n", "utf-8")
    return True


def _merge_codeowners(root: Path, *, dry_run: bool) -> bool:
    return _merge_lines(root / CODEOWNERS_PATH, codeowners_lines(), dry_run=dry_run)


def _overridden_report_attributes(root: Path) -> list[str]:
    names = [
        line.split()[0]
        for line in (TEMPLATES_DIR / "gitattributes").read_text("utf-8").splitlines()
    ]
    resolved = _git(root, "check-attr", "merge", "--", *names)
    effective = set(resolved.splitlines()) if resolved is not None else set()
    return [name for name in names if f"{name}: merge: {MERGE_DRIVER}" not in effective]


def install(
    root: Path, *, repo: str | None = None, dry_run: bool = False, now: datetime | None = None
) -> InstallReport:
    """Install the parent's gates and front doors; idempotent, a second run changes nothing."""

    written: list[str] = []
    unchanged: list[str] = []
    for name in WORKFLOW_TEMPLATES:
        relative = f"{WORKFLOWS_DIR}/{name}"
        content = (TEMPLATES_DIR / name).read_bytes()
        (
            written
            if _install_file(root, relative, content, executable=False, dry_run=dry_run)
            else unchanged
        ).append(relative)
    for relative, template in hook_templates():
        (
            written
            if _install_file(
                root, relative, template.read_bytes(), executable=True, dry_run=dry_run
            )
            else unchanged
        ).append(relative)
    required_attributes = (TEMPLATES_DIR / "gitattributes").read_text("utf-8").splitlines()
    attributes = root / ATTRIBUTES_PATH
    attributes_changed = _merge_lines(attributes, required_attributes, dry_run=dry_run)
    if _git(root, "rev-parse", "--is-inside-work-tree") == "true" and _overridden_report_attributes(
        root
    ):
        attributes_changed = True
        if not dry_run:
            existing = attributes.read_text("utf-8")
            body = existing if existing.endswith("\n") else existing + "\n"
            attributes.write_text(body + "\n".join(required_attributes) + "\n", "utf-8")
            if overridden := _overridden_report_attributes(root):
                raise GateError(
                    f"{ATTRIBUTES_PATH} cannot select {MERGE_DRIVER} for {', '.join(overridden)}"
                )
    (written if attributes_changed else unchanged).append(ATTRIBUTES_PATH)
    (written if _merge_codeowners(root, dry_run=dry_run) else unchanged).append(CODEOWNERS_PATH)
    for relative, template in door_templates():
        content = template.read_bytes()
        (
            written
            if _install_file(root, relative, content, executable=False, dry_run=dry_run)
            else unchanged
        ).append(relative)
    hooks_path_set = False
    if not dry_run and _git(root, "rev-parse", "--is-inside-work-tree") == "true":
        hooks_path_set = _git(root, "config", "core.hooksPath", HOOK_DIR) is not None
        _git(root, "config", f"merge.{MERGE_DRIVER}.name", MERGE_DRIVER_NAME)
        _git(root, "config", f"merge.{MERGE_DRIVER}.driver", "true")
    repos: list[str] = []
    resolved = repo or parent_repo(root)
    if resolved is not None:
        repos.append(resolved)
    repos += [item for item in gated_submodule_repos(root) if item not in repos]
    protected: list[str] = []
    unprotected: list[tuple[str, str]] = []
    if not repos:
        unprotected.append(("(unresolved)", "no GitHub remote to protect; pass --repo owner/name"))
        if not dry_run:
            _write_protection_receipt(
                root,
                "unresolved",
                applied=False,
                reason=unprotected[0][1],
                contexts=(),
                now=now,
            )
    for item in repos:
        if dry_run:
            unprotected.append((item, "dry run"))
            continue
        ok, reason = apply_protection(root, item, now=now)
        if ok:
            protected.append(item)
        else:
            unprotected.append((item, reason))
    return InstallReport(
        written=tuple(written),
        unchanged=tuple(unchanged),
        hooks_path_set=hooks_path_set,
        repos=tuple(repos),
        protected=tuple(protected),
        unprotected=tuple(unprotected),
    )


def _load_protection_receipts(root: Path) -> list[dict[str, object]]:
    directory = root / INSTALL_DIR / PROTECTION_DIR
    out: list[dict[str, object]] = []
    if not directory.is_dir():
        return out
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text("utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        if isinstance(value, dict) and value.get("schema_version") == PROTECTION_SCHEMA:
            out.append(value)
    return out


def check_gates_installed(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """The workflows, CODEOWNERS, and branch protection the preflight installs must stand."""

    root_path = Path(root)
    if git_head(root_path) is None:
        return []
    out: list[Finding] = []
    for name in WORKFLOW_TEMPLATES:
        relative = f"{WORKFLOWS_DIR}/{name}"
        target = root_path / relative
        expected = (TEMPLATES_DIR / name).read_bytes()
        current = target.read_bytes() if target.is_file() else None
        if current != expected:
            state = "absent" if current is None else "differs from trinity/templates"
            out.append(
                finding(
                    target,
                    0,
                    f"{relative} is {state}; run trinity/tools/gate.py install",
                    GATE_WORKFLOW_MISSING,
                )
            )
    for relative, template in hook_templates():
        target = root_path / relative
        current = target.read_bytes() if target.is_file() else None
        if current != template.read_bytes():
            state = "absent" if current is None else "differs from trinity/templates"
            out.append(
                finding(
                    target,
                    0,
                    f"{relative} is {state}; run trinity/tools/gate.py install",
                    GATE_HOOK_MISSING,
                )
            )
    attributes = root_path / ATTRIBUTES_PATH
    try:
        present_attributes = {line.strip() for line in attributes.read_text("utf-8").splitlines()}
    except (OSError, UnicodeDecodeError):
        present_attributes = set()
    required_attributes = (TEMPLATES_DIR / "gitattributes").read_text("utf-8").splitlines()
    missing_attributes = [line for line in required_attributes if line not in present_attributes]
    overridden = _overridden_report_attributes(root_path)
    if missing_attributes or overridden:
        out.append(
            finding(
                attributes,
                0,
                f"{ATTRIBUTES_PATH} lacks required rules or effective {MERGE_DRIVER} for "
                f"{', '.join(overridden or missing_attributes)}; "
                "run trinity/tools/gate.py install",
                GATE_ATTRIBUTES_MISSING,
            )
        )
    if (
        _git(root_path, "config", "--get", f"merge.{MERGE_DRIVER}.driver") != "true"
        or _git(root_path, "config", "--get", f"merge.{MERGE_DRIVER}.name") != MERGE_DRIVER_NAME
    ):
        out.append(
            finding(
                root_path,
                0,
                f"merge.{MERGE_DRIVER} is absent or drifted; run trinity/tools/gate.py install",
                GATE_MERGE_DRIVER_MISSING,
            )
        )
    codeowners = root_path / CODEOWNERS_PATH
    try:
        present = {line.strip() for line in codeowners.read_text("utf-8").splitlines()}
    except (OSError, UnicodeDecodeError):
        present = set()
    missing = [line for line in codeowners_lines() if line not in present]
    if missing:
        out.append(
            finding(
                codeowners,
                0,
                f"{CODEOWNERS_PATH} lacks {', '.join(missing)}; run trinity/tools/gate.py install",
                GATE_CODEOWNERS_MISSING,
            )
        )
    receipts = _load_protection_receipts(root_path)
    if not receipts:
        out.append(
            Finding(
                GATE_PROTECTION_UNVERIFIED,
                Severity.ADVISORY,
                str(root_path / INSTALL_DIR / PROTECTION_DIR),
                None,
                "no branch-protection receipt exists; the preflight has not run install here",
            )
        )
        return out
    for receipt in receipts:
        repo = str(receipt.get("repo", "?"))
        contexts = receipt.get("read_back_contexts")
        contexts_set = {str(item) for item in contexts} if isinstance(contexts, list) else set()
        lacking = sorted(set(REQUIRED_CHECKS) - contexts_set)
        if receipt.get("applied") is not True or lacking:
            detail = (
                str(receipt.get("reason", ""))
                if receipt.get("applied") is not True
                else (f"read-back lacks required checks {', '.join(lacking)}")
            )
            out.append(
                finding(
                    _receipt_path(root_path, repo) if repo != "?" else root_path,
                    0,
                    f"branch protection on {repo} is not in force: {detail}",
                    GATE_PROTECTION_MISSING,
                )
            )
    return out


CHECKS: list[tuple[str, Callable[[str, datetime | None], list[Finding]]]] = [
    ("check_gate_receipts", check_gate_receipts),
    ("check_gates_installed", check_gates_installed),
]


# ---- CLI ------------------------------------------------------------------------------


def _run(args: argparse.Namespace) -> int:
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            args.root,
            project_root=project_root,
            description="parent root",
            must_exist=True,
        )
    except ProjectPathError as exc:
        print(f"gate refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not root.is_dir():
        print("parent root is not a directory", file=sys.stderr)
        return EXIT_USAGE
    run_id = args.run_id or args.run or os.environ.get("GITHUB_RUN_ID") or local_run_id(root)
    if args.run is not None:
        try:
            runs_module.open_run(root, args.instrument, args.run, principal=_principal(root))
        except runs_module.RunError as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return EXIT_USAGE
    installed: InstallReport | None = None
    migration_report: Any | None = None
    migration_findings: list[Finding] = []
    if args.moment == "preflight":
        migrator = _harness_module("migrate")
        report: Any = migrator.compatibility_check(root, apply=not args.check)
        migration_report = report
        migration_status = str(report.status)
        migration_revalidation = tuple(report.needs_revalidation)
        migration_blocked = tuple(report.blocked)
        if migration_status == "hold" or migration_revalidation:
            details = (
                migration_blocked
                or migration_revalidation
                or (
                    "safe migration is pending; run an authoring preflight or "
                    "tools/migrate.py --apply",
                )
            )
            migration_findings.append(
                finding(
                    root / ".trinity" / "migrations",
                    0,
                    "project migration requires action: " + "; ".join(details),
                    PROJECT_MIGRATION_HOLD,
                )
            )
    if args.moment == "preflight" and not args.check and not migration_findings:
        installed = install(root, repo=args.repo)
    findings = migration_findings + run_gate(root)
    if installed is not None and not installed.complete:
        existing = {item.code for item in findings}
        findings += [item for item in check_gates_installed(str(root)) if item.code not in existing]
    recorded = record_sentinel(root, findings, run_id=run_id, ci=args.ci, stream=args.run)
    level = ceiling(findings)
    receipt: Path | None = None
    record: Path | None = None
    if not args.check:
        receipt = write_receipt(
            root,
            instrument=args.instrument,
            moment=args.moment,
            findings=findings,
            run_id=run_id,
            run=args.run,
        )
        if args.moment == "report":
            record = mint_record(root, instrument=args.instrument, findings=findings, run=args.run)
    public_findings = [
        Finding(
            item.code,
            item.severity,
            display_project_path(item.path, project_root=project_root),
            item.line,
            redact_project_root(item.message, project_root=project_root),
        )
        for item in findings
    ]
    if args.json:
        print(
            json.dumps(
                {
                    "instrument": args.instrument,
                    "moment": args.moment,
                    "run_id": run_id,
                    "ceiling": level,
                    "codes": error_codes(findings),
                    "sabotage_recorded": recorded,
                    "receipt": None
                    if receipt is None
                    else display_project_path(receipt, project_root=project_root),
                    "record": None
                    if record is None
                    else display_project_path(record, project_root=project_root),
                    "install": None if installed is None else _install_json(installed),
                    "migration": None if migration_report is None else migration_report.to_json(),
                    "findings": [finding_to_json(item) for item in public_findings],
                },
                indent=2,
            )
        )
    else:
        if installed is not None:
            _print_install(installed)
        if migration_report is not None:
            print(f"migration: {migration_report.status}")
        for item in public_findings:
            print(render_finding(item))
        print(f"gate {args.instrument} {args.moment}: ceiling {level}")
        if recorded:
            print(f"sentinel recorded: {', '.join(recorded)}")
        if receipt is not None:
            print(f"receipt: {display_project_path(receipt, project_root=project_root)}")
        if record is not None:
            print(f"record: {display_project_path(record, project_root=project_root)}")
    return EXIT_FOR_CEILING[level]


def _install_json(report: InstallReport) -> dict[str, object]:
    return {
        "written": list(report.written),
        "unchanged": list(report.unchanged),
        "hooks_path_set": report.hooks_path_set,
        "repos": list(report.repos),
        "protected": list(report.protected),
        "unprotected": [{"repo": repo, "reason": reason} for repo, reason in report.unprotected],
    }


def _print_install(report: InstallReport) -> None:
    for relative in report.written:
        print(f"install: wrote {relative}")
    for relative in report.unchanged:
        print(f"install: unchanged {relative}")
    if report.hooks_path_set:
        print(f"install: core.hooksPath -> {HOOK_PATH.rsplit('/', 1)[0]}")
    for repo in report.protected:
        print(f"install: branch protection in force on {repo}")
    for repo, reason in report.unprotected:
        print(f"install: branch protection NOT in force on {repo}: {reason}")
    if report.written:
        print(
            "install: commit .github/, .githooks/, .opencode/commands/, and .agents/skills/ "
            "alone, before any report or harness change, so the gate surfaces never share a "
            "commit with their subject"
        )


def _install_cmd(args: argparse.Namespace) -> int:
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            args.root,
            project_root=project_root,
            description="parent root",
            must_exist=True,
        )
    except ProjectPathError as exc:
        print(f"install refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if not root.is_dir():
        print("parent root is not a directory", file=sys.stderr)
        return EXIT_USAGE
    report = install(root, repo=args.repo, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(_install_json(report), indent=2))
    else:
        _print_install(report)
    return EXIT_CLEAN if report.complete else EXIT_INSTALL_INCOMPLETE


def _promote(args: argparse.Namespace) -> int:
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            args.root,
            project_root=project_root,
            description="candidate root",
            must_exist=True,
        )
        trust_dir = (
            None
            if args.trust_dir is None
            else resolve_project_path(
                args.trust_dir,
                project_root=project_root,
                description="release trust directory",
                must_exist=True,
            )
        )
    except ProjectPathError as exc:
        print(f"promote refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        path = promote(
            root,
            instrument=args.instrument,
            approver=args.approver,
            trust_dir=trust_dir,
            release=args.release,
        )
    except GateError as exc:
        print(
            f"promote refused: {redact_project_root(str(exc), project_root=project_root)}",
            file=sys.stderr,
        )
        return EXIT_BLOCK
    authority = (
        f"named approver {args.approver}"
        if args.approver is not None
        else f"roles {GROUP_PRODUCER_ROLE} and {GROUP_APPROVER_ROLE}"
    )
    print(
        f"promoted {display_project_path(path, project_root=project_root)} to {SHIP} "
        f"under {authority}"
    )
    print(signing_instruction(root, args.instrument, args.release))
    return EXIT_CLEAN


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gate.py", description=(__doc__ or "Trinity gate").split("\n\n")[0]
    )
    parser.add_argument("root")
    parser.add_argument("--instrument", required=True, choices=sorted(INSTRUMENT_HARNESS))
    parser.add_argument("--moment", required=True, choices=MOMENTS)
    parser.add_argument("--run-id")
    parser.add_argument(
        "--run", help="the run namespace this invocation owns under <harness>/runs/<run>/"
    )
    parser.add_argument("--repo", help="owner/name of the parent when origin is not GitHub")
    parser.add_argument("--ci", action="store_true", help="resolve the actor from CI variables")
    parser.add_argument(
        "--check", action="store_true", help="run and record only; write no receipt or record"
    )
    parser.add_argument("--json", action="store_true")
    return parser


def build_promote_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gate.py promote")
    parser.add_argument("root")
    parser.add_argument("--instrument", required=True, choices=sorted(DISPOSITION_PAYLOAD_TYPES))
    parser.add_argument("--release", help="frozen release candidate id under <harness>/releases/")
    parser.add_argument(
        "--approver",
        help="named v2 approver; omit to mint default group-authorized v3",
    )
    parser.add_argument("--trust-dir")
    return parser


def build_cosign_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gate.py cosign-assemble")
    parser.add_argument("--root", required=True)
    parser.add_argument("--instrument", required=True, choices=("FORGE", "CRUCIBLE"))
    parser.add_argument("--release", help="frozen release candidate id under <harness>/releases/")
    parser.add_argument("--envelope", action="append", default=[])
    parser.add_argument("--producer-envelope")
    parser.add_argument("--approver-envelope")
    parser.add_argument("--output", required=True)
    return parser


def build_partial_sign_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gate.py sign-partial")
    parser.add_argument("--root", required=True)
    parser.add_argument("--instrument", required=True, choices=("FORGE", "CRUCIBLE"))
    parser.add_argument("--release", help="frozen release candidate id under <harness>/releases/")
    parser.add_argument("--trust-dir", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--output", required=True)
    return parser


def build_signing_status_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gate.py signing-status")
    parser.add_argument("--root", required=True)
    parser.add_argument("--instrument", required=True, choices=("FORGE", "CRUCIBLE"))
    parser.add_argument("--release", help="frozen release candidate id under <harness>/releases/")
    parser.add_argument("--trust-dir", required=True)
    parser.add_argument("--envelope", action="append", default=[])
    parser.add_argument("--complete-envelope")
    return parser


def _sign_partial(args: argparse.Namespace) -> int:
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            args.root,
            project_root=project_root,
            description="candidate root",
            must_exist=True,
        )
        trust_dir = resolve_project_path(
            args.trust_dir,
            project_root=project_root,
            description="release trust directory",
            must_exist=True,
        )
        key_path = resolve_project_path(
            args.key,
            project_root=project_root,
            description="private key",
            must_exist=True,
        )
        output = resolve_project_path(
            args.output,
            project_root=project_root,
            description="partial envelope output",
        )
    except ProjectPathError as exc:
        print(f"partial signing refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        path = sign_partial_envelope(
            root,
            instrument=args.instrument,
            trust_dir=trust_dir,
            key_path=key_path,
            output=output,
            release=args.release,
        )
    except (OSError, ValueError) as exc:
        print(
            f"partial signing refused: {redact_project_root(str(exc), project_root=project_root)}",
            file=sys.stderr,
        )
        return EXIT_BLOCK
    print(display_project_path(path, project_root=project_root))
    return EXIT_CLEAN


def _cosign(args: argparse.Namespace) -> int:
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            args.root,
            project_root=project_root,
            description="candidate root",
            must_exist=True,
        )
        envelopes = [
            resolve_project_path(
                value,
                project_root=project_root,
                description="partial envelope",
                must_exist=True,
            )
            for value in args.envelope
        ]
        producer = (
            None
            if args.producer_envelope is None
            else resolve_project_path(
                args.producer_envelope,
                project_root=project_root,
                description="producer envelope",
                must_exist=True,
            )
        )
        approver = (
            None
            if args.approver_envelope is None
            else resolve_project_path(
                args.approver_envelope,
                project_root=project_root,
                description="approver envelope",
                must_exist=True,
            )
        )
        output = resolve_project_path(
            args.output,
            project_root=project_root,
            description="cosigned envelope output",
        )
    except ProjectPathError as exc:
        print(f"cosign assembly refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        path = assemble_cosigned_envelope(
            root,
            instrument=args.instrument,
            envelope_paths=envelopes,
            producer_envelope=producer,
            approver_envelope=approver,
            output=output,
            release=args.release,
        )
    except (GateError, OSError) as exc:
        print(
            f"cosign assembly refused: {redact_project_root(str(exc), project_root=project_root)}",
            file=sys.stderr,
        )
        return EXIT_BLOCK
    print(display_project_path(path, project_root=project_root))
    return EXIT_CLEAN


def _signing_status(args: argparse.Namespace) -> int:
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            args.root,
            project_root=project_root,
            description="candidate root",
            must_exist=True,
        )
        trust_dir = resolve_project_path(
            args.trust_dir,
            project_root=project_root,
            description="release trust directory",
            must_exist=True,
        )
        envelopes = [
            resolve_project_path(
                value,
                project_root=project_root,
                description="partial envelope",
                must_exist=True,
            )
            for value in args.envelope
        ]
        complete = (
            None
            if args.complete_envelope is None
            else resolve_project_path(
                args.complete_envelope,
                project_root=project_root,
                description="complete envelope",
                must_exist=True,
            )
        )
    except ProjectPathError as exc:
        print(f"signing status refused: {exc}", file=sys.stderr)
        return EXIT_USAGE
    try:
        status = signing_status(
            root,
            instrument=args.instrument,
            trust_dir=trust_dir,
            envelope_paths=envelopes,
            complete_envelope=complete,
            release=args.release,
        )
    except (OSError, ValueError) as exc:
        print(
            f"signing status refused: {redact_project_root(str(exc), project_root=project_root)}",
            file=sys.stderr,
        )
        return EXIT_BLOCK
    print(json.dumps(status, indent=2, sort_keys=True))
    return EXIT_CLEAN


def build_install_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gate.py install")
    parser.add_argument("root")
    parser.add_argument("--repo", help="owner/name of the parent when origin is not GitHub")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str]) -> int:
    arguments = list(argv[1:])
    if arguments and arguments[0] == "promote":
        return _promote(build_promote_parser().parse_args(arguments[1:]))
    if arguments and arguments[0] == "sign-partial":
        return _sign_partial(build_partial_sign_parser().parse_args(arguments[1:]))
    if arguments and arguments[0] == "cosign-assemble":
        return _cosign(build_cosign_parser().parse_args(arguments[1:]))
    if arguments and arguments[0] == "signing-status":
        return _signing_status(build_signing_status_parser().parse_args(arguments[1:]))
    if arguments and arguments[0] == "install":
        return _install_cmd(build_install_parser().parse_args(arguments[1:]))
    return _run(build_parser().parse_args(arguments))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
