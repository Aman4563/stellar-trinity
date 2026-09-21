#!/usr/bin/env python3
"""Release gate: the machine check between an audited parent and a client push.

Every artifact authorization is a byte-exact DSSE envelope verified with policy supplied from
outside the candidate tree. Root-report prose is checked for consistency but cannot authorize a
release. Release waivers are categorically rejected.

Usage:
  release.py PARENT_ROOT                 gate the parent's own samples/ tree
  release.py PARENT_ROOT --export DIR    also require DIR to be byte-identical

Refusal codes, all error severity:

  RELEASE_VERDICT_NOT_SHIP        VERDICT.md disposition line is not SHIP
  RELEASE_EDICT_NOT_SHIP          EDICT.md batch or per-slot line is not SHIP
  RELEASE_DISPOSITION_UNBOUND     SHIP line carries no digest, or a stale one
  RELEASE_EXPORT_MISMATCH         samples pointer or export bytes not audited
  RELEASE_ORACLE_RECEIPT_MISSING  no stock-Harbor oracle receipt for a bundle
  RELEASE_ORACLE_RECEIPT_INVALID  receipt malformed, unbound, or short
  RELEASE_REWARD_SCHEMA_AMBIGUOUS no single authoritative reward declared
  RELEASE_TRIAL_STATUS_INVALID    vacuous rollout not tagged trial_status invalid
  RELEASE_WAIVER_INVALID          release waiver exists; release failures are never waivable
  RELEASE_TRUST_INVALID           external release trust is absent or invalid
  RELEASE_DISPOSITION_INVALID     signed FORGE/CRUCIBLE authorization is absent or invalid
  RELEASE_POPULATION_EMPTY        no task bundle exists to release
  RELEASE_DIRTY_TREE              working tree dirty at gate time

Receipt verification is idempotent: release revalidates signatures and authorization without
consuming the shared attestation replay store.
"""

from __future__ import annotations

# allow: SIZE_OK - Keep the receipt binding fix within the existing release gate.
import argparse
import math
import os
import re
import sys
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING:
    from tools._findings import Finding, Severity
    from tools.attest.backend import SignatureBackend
    from tools.attest.canonical import CanonicalizationError, parse_json
    from tools.bundle_identity import (
        BundleIdentityError,
        release_snapshot_digest,
        tree_manifest,
        validate_release_population,
    )
    from tools.bundle_identity import (
        bundle_digest as canonical_bundle_digest,
    )
    from tools.bundle_identity import (
        bundle_set_digest as canonical_bundle_set_digest,
    )
    from tools.forensics.ledger import FidelityLedgerReadError, ledger_bytes, read_fidelity_ledger
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
        ORACLE_SCHEMA,
        TRUST_ENV,
        ReleaseEvidenceError,
        ReleaseTrust,
        authenticate_signed_payload,
        authorize_authenticated_principals,
        load_release_trust,
        parse_instant,
        safe_read_bytes,
        seals_only,
        verify_oracle_receipt,
        verify_signed_payload,
    )
    from tools.safe_git import SafeGitError, SafeGitRepository
else:
    try:
        from tools._findings import Finding, Severity
        from tools.attest.backend import SignatureBackend
        from tools.attest.canonical import CanonicalizationError, parse_json
        from tools.bundle_identity import (
            BundleIdentityError,
            release_snapshot_digest,
            tree_manifest,
            validate_release_population,
        )
        from tools.bundle_identity import (
            bundle_digest as canonical_bundle_digest,
        )
        from tools.bundle_identity import (
            bundle_set_digest as canonical_bundle_set_digest,
        )
        from tools.forensics.ledger import (
            FidelityLedgerReadError,
            ledger_bytes,
            read_fidelity_ledger,
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
            ORACLE_SCHEMA,
            TRUST_ENV,
            ReleaseEvidenceError,
            ReleaseTrust,
            authenticate_signed_payload,
            authorize_authenticated_principals,
            load_release_trust,
            parse_instant,
            safe_read_bytes,
            seals_only,
            verify_oracle_receipt,
            verify_signed_payload,
        )
        from tools.safe_git import SafeGitError, SafeGitRepository
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from _findings import Finding, Severity
        from attest.backend import SignatureBackend
        from attest.canonical import CanonicalizationError, parse_json
        from bundle_identity import (
            BundleIdentityError,
            release_snapshot_digest,
            tree_manifest,
            validate_release_population,
        )
        from bundle_identity import (
            bundle_digest as canonical_bundle_digest,
        )
        from bundle_identity import (
            bundle_set_digest as canonical_bundle_set_digest,
        )
        from forensics.ledger import FidelityLedgerReadError, ledger_bytes, read_fidelity_ledger
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
            ORACLE_SCHEMA,
            TRUST_ENV,
            ReleaseEvidenceError,
            ReleaseTrust,
            authenticate_signed_payload,
            authorize_authenticated_principals,
            load_release_trust,
            parse_instant,
            safe_read_bytes,
            seals_only,
            verify_oracle_receipt,
            verify_signed_payload,
        )
        from safe_git import SafeGitError, SafeGitRepository

VERDICT_NOT_SHIP = "RELEASE_VERDICT_NOT_SHIP"
EDICT_NOT_SHIP = "RELEASE_EDICT_NOT_SHIP"
DISPOSITION_UNBOUND = "RELEASE_DISPOSITION_UNBOUND"
EXPORT_MISMATCH = "RELEASE_EXPORT_MISMATCH"
ORACLE_RECEIPT_MISSING = "RELEASE_ORACLE_RECEIPT_MISSING"
ORACLE_RECEIPT_INVALID = "RELEASE_ORACLE_RECEIPT_INVALID"
REWARD_SCHEMA_AMBIGUOUS = "RELEASE_REWARD_SCHEMA_AMBIGUOUS"
TRIAL_STATUS_INVALID = "RELEASE_TRIAL_STATUS_INVALID"
WAIVER_INVALID = "RELEASE_WAIVER_INVALID"
TRUST_INVALID = "RELEASE_TRUST_INVALID"
DISPOSITION_INVALID = "RELEASE_DISPOSITION_INVALID"
POPULATION_EMPTY = "RELEASE_POPULATION_EMPTY"
DIRTY_TREE = "RELEASE_DIRTY_TREE"

SHIP_TOKENS: frozenset[str] = frozenset({"SHIP", "SHIP:INFERRED"})
VERDICT_REPORT = "VERDICT.md"
EDICT_REPORT = "EDICT.md"
SAMPLES_DIR = "samples"
DELIVERABLES_DIR = "deliverables"
TRAJECTORIES_DIR = "trajectories"
RECEIPT_DIR = Path(".audit") / "receipts" / "oracle"
WAIVER_PATH = Path(".audit") / "release-waiver.json"
REWARD_SCHEMA_NAME = "reward-schema.json"
RECEIPT_SCHEMA = ORACLE_SCHEMA
REWARD_SCHEMA = "trinity.reward-schema/v1"
SUBMODULE_MODE = "160000"
LS_TREE_FIELDS = 3
EXPORT_VCS_EXCLUSIONS: frozenset[str] = frozenset({".git"})
MAX_LISTED_PATHS = 5
MAX_CANDIDATE_TEXT_BYTES = 4 * 1024 * 1024

UUID = re.compile(r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")
H2_DISPOSITION = re.compile(r"^##\s+Disposition\s*$")
H2 = re.compile(r"^##\s+")
RUN_DIR = re.compile(r"\Arun[_-]?\d+\Z")
DECORATION = re.compile(r"[*`~#>]")
SHIP_TOKEN = re.compile(r"(?<![A-Za-z0-9:_-])SHIP(?::INFERRED)?(?![A-Za-z0-9:_-])")

JsonObject = dict[str, Any]


def _finding(path: Path | str, code: str, message: str, line: int = 0) -> Finding:
    return Finding(code, Severity.ERROR, str(path), line, message)


def _read_text(path: Path) -> str | None:
    try:
        return safe_read_bytes(path, maximum=MAX_CANDIDATE_TEXT_BYTES).decode("utf-8")
    except (OSError, UnicodeDecodeError, ReleaseEvidenceError):
        return None


def _read_json(path: Path) -> JsonObject | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        value = parse_json(text)
    except CanonicalizationError:
        return None
    if not isinstance(value, dict):
        return None
    return value


# ---- byte identity ----


def _files(tree: Path) -> Iterator[Path]:
    if tree.is_symlink() or not tree.is_dir():
        return
    stack = [tree]
    while stack:
        current = stack.pop()
        for entry in sorted(current.iterdir(), key=lambda item: item.name):
            if entry.is_symlink():
                continue
            if entry.is_dir():
                stack.append(entry)
            elif entry.is_file():
                yield entry


def tree_digests(tree: Path) -> dict[str, str]:
    """Compatibility projection of the shared manifest, including executable-bit identity."""
    return {
        item.path: f"{'x' if item.executable else '-'}:{item.digest}"
        for item in tree_manifest(tree)
    }


def bundle_digest(bundle: Path) -> str:
    """Return the shared versioned identity for one task bundle."""
    return canonical_bundle_digest(bundle)


def bundle_set_digest(samples: Path, uuids: list[str]) -> str:
    """Return the shared versioned identity for a non-empty task-bundle population."""
    return canonical_bundle_set_digest(samples, uuids)


def exported_uuids(samples: Path) -> list[str]:
    if not samples.is_dir():
        return []
    return sorted(
        entry.name
        for entry in samples.iterdir()
        if not entry.is_symlink() and entry.is_dir() and UUID.match(entry.name)
    )


# ---- report reading ----


def disposition_line(text: str) -> str | None:
    """Return the first non-empty line under ``## Disposition``, or None when absent."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if not H2_DISPOSITION.match(line):
            continue
        for candidate in lines[index + 1 :]:
            if H2.match(candidate):
                return None
            if candidate.strip():
                return candidate.strip()
        return None
    return None


def disposition_token(line: str) -> str | None:
    """Strip decorations and emoji, then return the leading disposition token."""
    plain = DECORATION.sub(" ", line)
    plain = "".join(character if character.isascii() else " " for character in plain)
    tokens = [token.strip(".,;") for token in plain.split()]
    tokens = [token for token in tokens if token]
    return tokens[0] if tokens else None


def _digest_on_line(line: str) -> str | None:
    found = HEX64.search(line)
    return found.group(0) if found else None


# ---- predicates ----


def _check_verdict(root: Path, expected_digest: str) -> list[Finding]:
    path = root / VERDICT_REPORT
    text = _read_text(path)
    if text is None:
        return [_finding(path, VERDICT_NOT_SHIP, "VERDICT.md is absent or unreadable")]
    line = disposition_line(text)
    if line is None:
        return [_finding(path, VERDICT_NOT_SHIP, "VERDICT.md carries no disposition line")]
    token = disposition_token(line)
    if token not in SHIP_TOKENS:
        return [_finding(path, VERDICT_NOT_SHIP, f"VERDICT.md disposition is {token!r}, not SHIP")]
    digest = _digest_on_line(line)
    if digest is None:
        message = "SHIP line carries no bundle-set digest; a SHIP bound to nothing releases nothing"
        return [_finding(path, DISPOSITION_UNBOUND, message)]
    if digest != expected_digest:
        message = (
            f"SHIP line binds bundle-set digest {digest[:12]} but the exported bytes digest to "
            f"{expected_digest[:12]}; the audited bytes are not the released bytes"
        )
        return [_finding(path, DISPOSITION_UNBOUND, message)]
    return []


def _check_edict(root: Path, uuids: list[str]) -> list[Finding]:
    path = root / EDICT_REPORT
    text = _read_text(path)
    if text is None:
        return [_finding(path, EDICT_NOT_SHIP, "EDICT.md is absent or unreadable")]
    out: list[Finding] = []
    line = disposition_line(text)
    token = disposition_token(line) if line is not None else None
    if token not in SHIP_TOKENS:
        out.append(
            _finding(path, EDICT_NOT_SHIP, f"EDICT.md batch disposition is {token!r}, not SHIP")
        )
    for uuid in uuids:
        rows = [row for row in text.split("\n") if uuid in row]
        if not any(SHIP_TOKEN.search(row) for row in rows):
            message = f"EDICT.md carries no SHIP row for exported bundle {uuid}"
            out.append(_finding(path, EDICT_NOT_SHIP, message))
    return out


def _samples_pointer(repository: SafeGitRepository) -> str | None:
    stdout = repository.run("ls-tree", repository.head, SAMPLES_DIR)
    if stdout is None:
        return None
    fields = stdout.split()
    if len(fields) < LS_TREE_FIELDS or fields[0] != SUBMODULE_MODE:
        return None
    return fields[2]


def _check_export(root: Path, export: Path | None, repository: SafeGitRepository) -> list[Finding]:
    out: list[Finding] = []
    pointer = _samples_pointer(repository)
    if pointer is not None:
        text = _read_text(root / VERDICT_REPORT) or ""
        if pointer not in set(HEX40.findall(text)):
            message = (
                f"samples submodule points at {pointer[:12]} which VERDICT.md never audited; "
                "the pointer moved after the verdict"
            )
            out.append(_finding(root / VERDICT_REPORT, EXPORT_MISMATCH, message))
    if export is None:
        return out
    try:
        audited_manifest = tree_manifest(
            root / SAMPLES_DIR, exclude_top_level=EXPORT_VCS_EXCLUSIONS
        )
        shipped_manifest = tree_manifest(export, exclude_top_level=EXPORT_VCS_EXCLUSIONS)
    except BundleIdentityError as exc:
        return [_finding(export, EXPORT_MISMATCH, f"export has no safe canonical identity: {exc}")]
    audited = {item.path: (item.digest, item.executable) for item in audited_manifest}
    shipped = {item.path: (item.digest, item.executable) for item in shipped_manifest}
    differing = sorted(
        path for path in set(audited) | set(shipped) if audited.get(path) != shipped.get(path)
    )
    if differing:
        listed = ", ".join(differing[:MAX_LISTED_PATHS])
        suffix = (
            ""
            if len(differing) <= MAX_LISTED_PATHS
            else f" and {len(differing) - MAX_LISTED_PATHS} more"
        )
        message = f"export differs from the audited samples tree at {listed}{suffix}"
        out.append(_finding(export, EXPORT_MISMATCH, message))
    return out


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _is_number(value: object) -> bool:
    return _number(value) is not None


def _check_receipts(
    root: Path,
    samples: Path,
    uuids: list[str],
    *,
    trust: ReleaseTrust,
    now: datetime,
    backend: SignatureBackend | None,
) -> list[Finding]:
    out: list[Finding] = []
    for uuid in uuids:
        path = root / RECEIPT_DIR / f"{uuid}.json.dsse"
        if not path.is_file():
            message = f"no signed authorized oracle receipt for bundle {uuid}"
            out.append(_finding(path, ORACLE_RECEIPT_MISSING, message))
            continue
        try:
            verify_oracle_receipt(
                path,
                trust=trust,
                task_uuid=uuid,
                bundle_digest=bundle_digest(samples / uuid),
                evaluation_time=now,
                backend=backend,
                ledger=ledger_bytes(read_fidelity_ledger(root / ".audit")),
            )
        except (BundleIdentityError, ReleaseEvidenceError, FidelityLedgerReadError) as exc:
            out.append(_finding(path, ORACLE_RECEIPT_INVALID, str(exc)))
    return out


def _schema_declares_one(schema: JsonObject | None) -> bool:
    if schema is None or schema.get("schema") != REWARD_SCHEMA:
        return False
    authoritative = schema.get("authoritative")
    if not isinstance(authoritative, dict):
        return False
    path = authoritative.get("path")
    key = authoritative.get("key")
    return isinstance(path, str) and bool(path) and isinstance(key, str) and bool(key)


def _trajectory_roots(root: Path, uuid: str) -> list[Path]:
    candidates = [
        root / SAMPLES_DIR / uuid / TRAJECTORIES_DIR,
        root / "delivery" / uuid / TRAJECTORIES_DIR,
        root / DELIVERABLES_DIR / uuid / TRAJECTORIES_DIR,
    ]
    return [candidate for candidate in candidates if candidate.is_dir()]


def _run_directory(path: Path, stop: Path) -> Path:
    for ancestor in path.parents:
        if ancestor == stop:
            break
        if RUN_DIR.match(ancestor.name):
            return ancestor
    return path.parent


def _json_files(tree: Path) -> Iterator[tuple[Path, JsonObject | None]]:
    for path in _files(tree):
        if path.suffix != ".json":
            continue
        yield path, _read_json(path)


def _check_reward_schema(root: Path, samples: Path, uuids: list[str]) -> list[Finding]:
    out: list[Finding] = []
    shared = _schema_declares_one(_read_json(samples / REWARD_SCHEMA_NAME))
    for uuid in uuids:
        bundle_schema = samples / uuid / "tests" / REWARD_SCHEMA_NAME
        if not shared and not _schema_declares_one(_read_json(bundle_schema)):
            message = (
                f"bundle {uuid} declares no {REWARD_SCHEMA_NAME} naming exactly one authoritative "
                "reward field"
            )
            out.append(_finding(bundle_schema, REWARD_SCHEMA_AMBIGUOUS, message))
        for trajectories in _trajectory_roots(root, uuid):
            rewards: dict[Path, set[float]] = {}
            for path, value in _json_files(trajectories):
                if value is None:
                    message = "trajectory JSON is unreadable, malformed, or not an object"
                    out.append(_finding(path, REWARD_SCHEMA_AMBIGUOUS, message))
                    continue
                reward = _number(value.get("reward"))
                if reward is not None:
                    rewards.setdefault(_run_directory(path, trajectories), set()).add(reward)
            for run, values in sorted(rewards.items()):
                if len(values) > 1:
                    listed = ", ".join(str(value) for value in sorted(values))
                    message = f"run carries {len(values)} different values named reward: {listed}"
                    out.append(_finding(run, REWARD_SCHEMA_AMBIGUOUS, message))
    return out


def _vacuous(value: object) -> bool:
    if isinstance(value, dict):
        if value.get("status") == "vacuous" or value.get("targets_total") == 0:
            return True
        return any(_vacuous(child) for child in value.values())
    if isinstance(value, list):
        return any(_vacuous(child) for child in value)
    return False


def _check_trial_status(root: Path, uuids: list[str]) -> list[Finding]:
    out: list[Finding] = []
    for uuid in uuids:
        for trajectories in _trajectory_roots(root, uuid):
            for path, value in _json_files(trajectories):
                if value is None:
                    continue
                if _vacuous(value) and value.get("trial_status") != "invalid":
                    message = (
                        "rollout is vacuous or grades zero targets yet is not tagged "
                        "trial_status invalid; it would be aggregated as a model failure"
                    )
                    out.append(_finding(path, TRIAL_STATUS_INVALID, message))
    return out


def _check_waiver_absent(root: Path) -> list[Finding]:
    path = root / WAIVER_PATH
    if path.exists() or path.is_symlink():
        return [
            _finding(
                path,
                WAIVER_INVALID,
                "release waivers are forbidden; operational acceptance is not SHIP and cannot "
                "clear disposition, oracle, or reward failures",
            )
        ]
    return []


DISPOSITION_FIELDS = {
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
GROUP_DISPOSITION_FIELDS = (DISPOSITION_FIELDS - {"producer", "approver"}) | {
    "producer_role",
    "approver_role",
}


def _disposition_record(value: object, *, instrument: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ReleaseEvidenceError(f"{instrument} disposition does not carry the closed field set")
    schema = value.get("schema")
    expected = (
        DISPOSITION_FIELDS
        if schema == DISPOSITION_SCHEMA
        else GROUP_DISPOSITION_FIELDS
        if schema == GROUP_DISPOSITION_SCHEMA
        else set()
    )
    if set(value) != expected:
        raise ReleaseEvidenceError(f"{instrument} disposition does not carry the closed field set")
    if any(not isinstance(item, str) or not item for item in value.values()):
        raise ReleaseEvidenceError(f"{instrument} disposition carries an empty field")
    return {str(key): str(item) for key, item in value.items()}


RELEASE_ID = re.compile(r"[a-z0-9][a-z0-9.-]{2,63}\Z")


def _binds_candidate_snapshot(repository: SafeGitRepository, candidate_commit: str) -> bool:
    if re.fullmatch(r"[0-9a-f]{40}", candidate_commit) is None:
        return False
    if not repository.is_ancestor(candidate_commit, repository.head):
        return False
    changed = repository.changed_paths(candidate_commit, repository.head)
    return changed is not None and (not changed or seals_only(changed))


def _check_signed_dispositions(
    root: Path,
    *,
    repository: SafeGitRepository,
    bundle_set: str,
    snapshot: str,
    trust: ReleaseTrust,
    now: datetime,
    backend: SignatureBackend | None,
    release: str | None = None,
) -> list[Finding]:
    out: list[Finding] = []
    for instrument, harness in (("FORGE", ".seed"), ("CRUCIBLE", ".audit")):
        home = root / harness if release is None else root / harness / "releases" / release
        record_path = home / "disposition.json"
        envelope_path = home / "disposition.json.dsse"
        try:
            record_bytes = safe_read_bytes(record_path, maximum=1024 * 1024)
            value = parse_json(record_bytes)
            record = _disposition_record(value, instrument=instrument)
            is_group = record["schema"] == GROUP_DISPOSITION_SCHEMA
            payload_type = (
                GROUP_DISPOSITION_PAYLOAD_TYPES[instrument]
                if is_group
                else DISPOSITION_PAYLOAD_TYPES[instrument]
            )
            if is_group:
                authenticated = authenticate_signed_payload(
                    envelope_path,
                    trust=trust,
                    payload_type=payload_type,
                    evaluation_time=now,
                    backend=backend,
                )
                producer_principals = authorize_authenticated_principals(
                    trust=trust,
                    role=GROUP_PRODUCER_ROLE,
                    authenticated_principals=authenticated.authenticated_principals,
                    evaluation_time=now,
                )
                approver_principals = authorize_authenticated_principals(
                    trust=trust,
                    role=GROUP_APPROVER_ROLE,
                    authenticated_principals=authenticated.authenticated_principals,
                    evaluation_time=now,
                    excluded_principals=producer_principals,
                )
                signed_payload = authenticated.payload
                authenticated_principals = authenticated.authenticated_principals
            else:
                authorization = verify_signed_payload(
                    envelope_path,
                    trust=trust,
                    role=GROUP_APPROVER_ROLE,
                    payload_type=payload_type,
                    evaluation_time=now,
                    backend=backend,
                    producer_principal=record["producer"],
                )
                producer_principals = ()
                approver_principals = authorization.authorized_principals
                signed_payload = authorization.payload
                authenticated_principals = authorization.authenticated_principals
            if signed_payload != record_bytes:
                raise ReleaseEvidenceError(
                    f"{instrument} envelope does not sign the exact disposition record bytes"
                )
            if record["instrument"] != instrument:
                raise ReleaseEvidenceError(f"{instrument} disposition domain is invalid")
            if record["disposition"] != "SHIP":
                raise ReleaseEvidenceError(f"{instrument} signed disposition is not SHIP")
            if (
                record["project_id"] != trust.project_id
                or record["repository_id"] != trust.repository_id
            ):
                raise ReleaseEvidenceError(f"{instrument} disposition names the wrong project")
            if record["bundle_set_digest"] != bundle_set or record["snapshot_digest"] != snapshot:
                raise ReleaseEvidenceError(
                    f"{instrument} disposition does not bind the complete release snapshot"
                )
            if record["verifier_sha"] != trust.verifier_sha:
                raise ReleaseEvidenceError(f"{instrument} disposition names an untrusted verifier")
            if not _binds_candidate_snapshot(repository, record["candidate_commit"]):
                raise ReleaseEvidenceError(
                    f"{instrument} candidate commit is not the sealed snapshot"
                )
            issued = parse_instant(record["issued_at"], f"{instrument} issued_at")
            expires = parse_instant(record["expires_at"], f"{instrument} expires_at")
            if not issued <= now < expires:
                raise ReleaseEvidenceError(f"{instrument} disposition time window is invalid")
            if now - issued > timedelta(seconds=trust.disposition_max_age_seconds):
                raise ReleaseEvidenceError(f"{instrument} disposition is older than policy permits")
            if is_group:
                if (
                    record["producer_role"] != GROUP_PRODUCER_ROLE
                    or record["approver_role"] != GROUP_APPROVER_ROLE
                ):
                    raise ReleaseEvidenceError(
                        f"{instrument} group disposition roles are not pinned"
                    )
                if set(producer_principals).intersection(approver_principals):
                    raise ReleaseEvidenceError(
                        f"{instrument} producer signers cannot approve their own artifact"
                    )
            else:
                producer = record["producer"]
                approver = record["approver"]
                if producer == approver:
                    raise ReleaseEvidenceError(f"{instrument} producer and approver are the same")
                if producer not in authenticated_principals:
                    raise ReleaseEvidenceError(
                        f"{instrument} producer is not an authenticated envelope principal"
                    )
                if approver not in approver_principals:
                    raise ReleaseEvidenceError(
                        f"{instrument} named approver is not an authorized gate_approver"
                    )
        except (OSError, CanonicalizationError, ReleaseEvidenceError) as exc:
            out.append(_finding(envelope_path, DISPOSITION_INVALID, str(exc)))
    return out


def _check_dirty_tree(root: Path, repository: SafeGitRepository) -> list[Finding]:
    stdout = repository.status_porcelain()
    if stdout is None:
        message = "parent root is not a git repository, so the gate cannot prove the tree is clean"
        return [_finding(root, DIRTY_TREE, message)]
    if stdout.strip():
        first = stdout.strip().split("\n", 1)[0].strip()
        return [
            _finding(root, DIRTY_TREE, f"working tree is dirty at gate time, starting at {first!r}")
        ]
    return []


# ---- entry points ----


def check_release(
    root: str | Path,
    _evaluation_time: datetime | None = None,
    *,
    export: str | None = None,
    trust_dir: str | Path | None = None,
    expected_project_id: str | None = None,
    expected_repository_id: str | None = None,
    expected_verifier_sha: str | None = None,
    _signature_backend: SignatureBackend | None = None,
    project_root: Path | None = None,
    release: str | None = None,
) -> list[Finding]:
    """Decide whether the parent's samples tree may be released to a client.

    ``release`` names a frozen candidate under ``<harness>/releases/<id>/`` whose records are
    read instead of the harness-root records.
    """
    root_path = Path(root)
    if release is not None and (RELEASE_ID.fullmatch(release) is None or ".." in release):
        return [_finding(root_path, TRUST_INVALID, f"release id {release!r} is malformed")]
    now = _evaluation_time if _evaluation_time is not None else datetime.now(UTC)
    if not root_path.is_dir():
        return [_finding(root_path, DIRTY_TREE, "parent project root is not a directory")]
    try:
        repository = SafeGitRepository(root_path)
    except SafeGitError as exc:
        return [
            _finding(
                root_path,
                DIRTY_TREE,
                f"candidate Git metadata cannot be represented as inert data: {exc}",
            )
        ]
    try:
        return _check_release_snapshot(
            root_path,
            now,
            repository=repository,
            export=export,
            trust_dir=trust_dir,
            expected_project_id=expected_project_id,
            expected_repository_id=expected_repository_id,
            expected_verifier_sha=expected_verifier_sha,
            backend=_signature_backend,
            project_root=project_root,
            release=release,
        )
    finally:
        repository.close()


def _check_release_snapshot(
    root_path: Path,
    now: datetime,
    *,
    repository: SafeGitRepository,
    export: str | None,
    trust_dir: str | Path | None,
    expected_project_id: str | None,
    expected_repository_id: str | None,
    expected_verifier_sha: str | None,
    backend: SignatureBackend | None,
    project_root: Path | None,
    release: str | None = None,
) -> list[Finding]:
    samples = root_path / SAMPLES_DIR
    uuids = exported_uuids(samples)
    findings: list[Finding] = []
    findings += _check_dirty_tree(root_path, repository)
    findings += _check_waiver_absent(root_path)
    if not uuids:
        findings.append(
            _finding(samples, POPULATION_EMPTY, "release population contains no UUID task bundles")
        )
        return findings
    try:
        validate_release_population(samples, uuids)
        expected_digest = bundle_set_digest(samples, uuids)
        snapshot_digest = release_snapshot_digest(samples, uuids)
    except BundleIdentityError as exc:
        findings.append(_finding(samples, EXPORT_MISMATCH, f"unsafe bundle identity: {exc}"))
        return findings
    findings += _check_verdict(root_path, expected_digest)
    findings += _check_edict(root_path, uuids)
    findings += _check_export(root_path, Path(export) if export is not None else None, repository)
    findings += _check_reward_schema(root_path, samples, uuids)
    findings += _check_trial_status(root_path, uuids)
    try:
        trust = load_release_trust(root_path, trust_dir, project_root=project_root)
    except ReleaseEvidenceError as exc:
        findings.append(_finding(root_path, TRUST_INVALID, str(exc)))
        return findings
    expected_identities = {
        "project_id": (expected_project_id, trust.project_id),
        "repository_id": (expected_repository_id, trust.repository_id),
        "verifier_sha": (expected_verifier_sha, trust.verifier_sha),
    }
    identity_mismatch = False
    for field, (expected, configured) in expected_identities.items():
        if expected is not None and expected != configured:
            identity_mismatch = True
            findings.append(
                _finding(
                    root_path,
                    TRUST_INVALID,
                    f"external release policy {field} {configured!r} does not match "
                    f"governance pin {expected!r}",
                )
            )
    if identity_mismatch:
        return findings
    findings += _check_signed_dispositions(
        root_path,
        repository=repository,
        bundle_set=expected_digest,
        snapshot=snapshot_digest,
        trust=trust,
        now=now,
        backend=backend,
        release=release,
    )
    findings += _check_receipts(
        root_path,
        samples,
        uuids,
        trust=trust,
        now=now,
        backend=backend,
    )
    return findings


def check_release_gate(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """Parent-check entry point with the ``PARENT_CHECKS`` signature."""
    return check_release(root, _evaluation_time)


CHECKS: list[tuple[str, Callable[[str, datetime | None], list[Finding]]]] = [
    ("check_release_gate", check_release_gate),
]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release.py", description=(__doc__ or "release gate").split("\n\n")[0]
    )
    parser.add_argument("root", help="parent project root whose samples/ tree is being released")
    parser.add_argument("--export", help="checkout of the *-samples repo that must equal samples/")
    parser.add_argument(
        "--trust-dir",
        help="external trust directory as an explicit ./ path (or set TRINITY_RELEASE_TRUST_DIR)",
    )
    parser.add_argument("--expected-project-id")
    parser.add_argument("--expected-repository-id")
    parser.add_argument("--expected-verifier-sha")
    parser.add_argument("--release", help="frozen release candidate id under <harness>/releases/")
    return parser


def main(argv: list[str]) -> int:
    """Run the gate from the command line; exit 1 on any refusal."""
    arguments = _parser().parse_args(argv[1:])
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            arguments.root,
            project_root=project_root,
            description="candidate root",
            must_exist=True,
        )
        export = (
            None
            if arguments.export is None
            else resolve_project_path(
                arguments.export,
                project_root=project_root,
                description="export directory",
                must_exist=True,
            )
        )
        trust_value = arguments.trust_dir or os.environ.get(TRUST_ENV)
        trust_dir = (
            None
            if trust_value is None
            else resolve_project_path(
                trust_value,
                project_root=project_root,
                description="release trust directory",
                must_exist=True,
            )
        )
    except ProjectPathError as exc:
        print(f"release refused: {exc}", file=sys.stderr)
        return 1
    findings = check_release(
        root,
        export=None if export is None else str(export),
        trust_dir=trust_dir,
        expected_project_id=arguments.expected_project_id,
        expected_repository_id=arguments.expected_repository_id,
        expected_verifier_sha=arguments.expected_verifier_sha,
        project_root=project_root,
        release=arguments.release,
    )
    for item in findings:
        relative = display_project_path(item.path, project_root=project_root)
        location = relative if item.line in (None, 0) else f"{relative}:{item.line}"
        message = redact_project_root(item.message, project_root=project_root)
        print(f"{item.code} {location}: {message}")
    if findings:
        print(f"\nrefused: {len(findings)} release gate violation(s)")
        return 1
    print("clean: audited bytes, SHIP dispositions, oracle receipts, and reward schema agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
