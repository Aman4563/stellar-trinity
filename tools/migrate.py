"""Versioned, fail-closed project-structure migration for Trinity authoring workspaces.

The migrator recognizes a deliberately small matrix of unsigned legacy structures. It never
creates authority, reads secrets, edits approval material, or rewrites signed envelopes. Every
write is rooted beneath the invocation root, backed up byte-for-byte, journaled atomically, and
checked against its planned postcondition.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal, TypedDict


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING:
    from tools.attest.canonical import parse_json
    from tools.bundle_identity import FileIdentity, manifest_digest, tree_manifest
    from tools.harbor import DEFAULT_ORG, migrate_text
    from tools.project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
else:
    try:
        from tools.attest.canonical import parse_json
        from tools.bundle_identity import FileIdentity, manifest_digest, tree_manifest
        from tools.harbor import DEFAULT_ORG, migrate_text
        from tools.project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        from attest.canonical import parse_json
        from bundle_identity import FileIdentity, manifest_digest, tree_manifest
        from harbor import DEFAULT_ORG, migrate_text
        from project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )

JOURNAL_VERSION = 2
PROJECT_V1 = "trinity.project/v1"
PROJECT_V2 = "trinity.project/v2"
PROJECT_FILE = "./.trinity/project.json"
JOURNAL_FILE = "./.trinity/migrations/state.json"
LOCK_FILE = "./.trinity/migrations/migrate.lock"
BACKUP_DIR = "./.trinity/migrations/backups"
REVALIDATION_FILE = "./.trinity/migrations/needs-revalidation.json"
PIPELINE_QUEUE = "./.podium/queue.jsonl"
PROGRESS_CACHES = ("./.memory/progress.yaml", "./.seed/progress.yaml", "./.audit/progress.yaml")
ABSENT_DIGEST = hashlib.sha256(b"trinity:migration:absent\n").hexdigest()
EMPTY_PLAN_DIGEST = hashlib.sha256(b"").hexdigest()
BACKUP_MODE = 0o400
MISSING = object()
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
PROJECT_PATHS = {
    "audit": "./.audit",
    "delivery": "./delivery",
    "memory": "./.memory",
    "podium": "./.podium",
    "samples": "./samples",
    "seed": "./.seed",
}
PROJECT_FIELDS = frozenset({"schema_version", "paths"})
REISSUE_ACTIONS = {
    "trinity.pilot-policy/v1": (
        "Human governance must re-issue trinity.pilot-policy/v2 before a fresh pilot, supplying "
        "groupSize=8, groupCount, comparisonFamily, permittedLooks, maxAffectedGroupFraction, "
        "harnessConfigDigest and executionFidelityRequired=true with a feasible measured ceiling; "
        "the external execution_operator must sign the pre-run population commitment."
    ),
    "trinity.pilot-attempt/v1": (
        "The pilot registry owner must re-issue trinity.pilot-attempt/v2 from a fresh independent "
        "pilot with precommitted disjoint solverGroups, per-rollout outcome and trialStatus, "
        "harnessConfigDigest, groupCommitmentDigest, fidelityLedgerDigest and "
        "executionAttestationDigest; CRUCIBLE derives conformance and the external "
        "execution_operator signs the new execution/v2 evidence, never the migrator."
    ),
    "trinity.execution/v1": (
        "The external execution_operator must independently execute and re-issue signed "
        "trinity.execution/v2 with harnessConfig, effectiveConfigReconciliation, populationRoster, "
        "observationCapture and per-rollout rolloutTelemetry bound to the pre-run commitment; "
        "CRUCIBLE must validate the new evidence and affected release evidence must be re-signed."
    ),
    "trinity.oracle-run/v3": (
        "The external execution_operator must run the controls and re-issue a signed "
        "trinity.oracle-run/v4 receipt under trinity.release-policy/v3 with exactly one outcome "
        "per required control under one controls manifest digest, including all six core "
        "controls and mandatory execution_fidelity; the release verifier must validate it."
    ),
    "trinity.release-policy/v2": (
        "Human governance must re-issue trinity.release-policy/v3 in the external release trust "
        "directory, supplying oracle.required_controls with all six core controls including "
        "execution_fidelity, never marking execution_fidelity non-applicable, and retaining "
        "governed identity, verifier and trust pins; the authorized external execution_operator "
        "must sign fresh oracle-run/v4 receipts under that policy, not sign a migrated policy."
    ),
}
JOURNAL_FIELDS = frozenset(
    {"version", "steps", "before_sha256", "after_sha256", "backups", "status"}
)
STEP_FIELDS = frozenset(
    {
        "id",
        "path",
        "before_sha256",
        "after_sha256",
        "backup",
        "before_mode",
        "after_mode",
        "needs_revalidation",
        "status",
    }
)
STEP_STATUSES = frozenset({"pending", "applied", "needs_revalidation"})
JOURNAL_STATUSES = frozenset({"planned", "applying", "complete", "hold"})
QUEUE_FIELDS = frozenset(
    {"seq", "uuid", "bundle_digest", "sealed_at", "producer_run_id", "prev_hash", "entry_hash"}
)
SENSITIVE_NAMES = frozenset(
    {
        "approval",
        "approval.json",
        "approval.yaml",
        "allowed_signers",
        "roots.yaml",
        "trusted-root-version",
    }
)

MigrationStatus = Literal["noop", "planned", "complete", "hold"]


class JournalStep(TypedDict):
    id: str
    path: str
    before_sha256: str
    after_sha256: str
    backup: str | None
    before_mode: int | None
    after_mode: int
    needs_revalidation: bool
    status: str


class Journal(TypedDict):
    version: int
    steps: list[JournalStep]
    before_sha256: str
    after_sha256: str
    backups: list[str]
    status: str


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    data: bytes
    mode: int


@dataclass(frozen=True, slots=True)
class PlannedWrite:
    id: str
    path: str
    before: bytes | None
    after: bytes
    needs_revalidation: bool = False
    before_mode: int | None = None
    after_mode: int = 0o600

    def journal_step(self) -> JournalStep:
        before_digest = _digest_optional(self.before)
        backup = None if self.before is None else f"{BACKUP_DIR}/{before_digest}"
        return {
            "id": self.id,
            "path": self.path,
            "before_sha256": before_digest,
            "after_sha256": _digest(self.after),
            "backup": backup,
            "before_mode": self.before_mode,
            "after_mode": self.after_mode,
            "needs_revalidation": self.needs_revalidation,
            "status": "pending",
        }


@dataclass(frozen=True, slots=True)
class MigrationReport:
    status: MigrationStatus
    changed: tuple[str, ...]
    needs_revalidation: tuple[str, ...]
    blocked: tuple[str, ...]
    required_actions: tuple[str, ...]
    dry_run: bool

    def to_json(self) -> dict[str, object]:
        return {
            "schema": "trinity.migration-report/v1",
            "status": self.status,
            "changed": list(self.changed),
            "needs_revalidation": list(self.needs_revalidation),
            "blocked": list(self.blocked),
            "required_actions": list(self.required_actions),
            "dry_run": self.dry_run,
        }


class MigrationError(ValueError):
    """A migration input or persisted state cannot be trusted."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_optional(data: bytes | None) -> str:
    return ABSENT_DIGEST if data is None else _digest(data)


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _root_relative(value: str) -> tuple[str, ...]:
    if not value.startswith("./") or "\\" in value or "\x00" in value:
        raise MigrationError(f"recorded path {value!r} is not a canonical './' path")
    suffix = value[2:]
    if not suffix:
        raise MigrationError("migration records may not name the project root")
    parsed = PurePosixPath(suffix)
    if parsed.is_absolute() or parsed.as_posix() != suffix:
        raise MigrationError(f"recorded path {value!r} is not canonical")
    if any(part in {"", ".", ".."} or part.startswith("~") for part in parsed.parts):
        raise MigrationError(f"recorded path {value!r} contains traversal")
    return parsed.parts


def _path(root: Path, value: str, *, allow_missing: bool = True) -> Path:
    parts = _root_relative(value)
    current = root
    for part in parts:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if allow_missing:
                continue
            raise MigrationError(f"{value} is missing") from None
        except OSError as exc:
            raise MigrationError(f"{value} cannot be inspected: {exc}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise MigrationError(f"{value} traverses symbolic link {part!r}")
    try:
        current.absolute().resolve(strict=False).relative_to(root)
    except (OSError, ValueError) as exc:
        raise MigrationError(f"{value} escapes the project root") from exc
    return current


def _validated_mode(info_mode: int, relative: str) -> int:
    mode = stat.S_IMODE(info_mode)
    if info_mode & (stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX) or mode & 0o022:
        raise MigrationError(f"{relative} has an unsafe regular-file mode {mode:#o}")
    return mode


def _snapshot_optional(root: Path, relative: str) -> FileSnapshot | None:
    target = _path(root, relative)
    try:
        info = target.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise MigrationError(f"{relative} cannot be inspected: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise MigrationError(f"{relative} is not a regular file")
    try:
        return FileSnapshot(target.read_bytes(), _validated_mode(info.st_mode, relative))
    except OSError as exc:
        raise MigrationError(f"{relative} cannot be read: {exc}") from exc


def _read_optional(root: Path, relative: str) -> bytes | None:
    snapshot = _snapshot_optional(root, relative)
    return None if snapshot is None else snapshot.data


def _virtual_snapshot(
    root: Path, relative: str, originals: dict[str, FileSnapshot | None] | None
) -> FileSnapshot | None:
    if originals is not None and relative in originals:
        return originals[relative]
    return _snapshot_optional(root, relative)


def _planned_write(
    root: Path,
    *,
    step_id: str,
    path: str,
    before: bytes | None,
    after: bytes,
    needs_revalidation: bool = False,
    originals: dict[str, FileSnapshot | None] | None = None,
) -> PlannedWrite:
    snapshot = _virtual_snapshot(root, path, originals)
    if (None if snapshot is None else snapshot.data) != before:
        raise MigrationError(f"{path} virtual planning bytes are inconsistent")
    before_mode = None if snapshot is None else snapshot.mode
    after_mode = 0o600 if before_mode is None else before_mode
    return PlannedWrite(
        step_id,
        path,
        before,
        after,
        needs_revalidation,
        before_mode,
        after_mode,
    )


def _assert_writable_surface(relative: str) -> None:
    parts = _root_relative(relative)
    lowered = {part.lower() for part in parts}
    if any(
        part in SENSITIVE_NAMES
        or "private-key" in part
        or "private_key" in part
        or part.endswith((".dsse", ".key", ".pem", ".crt"))
        for part in lowered
    ):
        raise MigrationError(f"migration may not write authority or signed path {relative}")
    if parts[0] in {"release-trust", ".secrets"}:
        raise MigrationError(f"migration may not write external governance path {relative}")


def _project_document(paths: dict[str, str] | None = None) -> bytes:
    return _canonical_json({"schema_version": PROJECT_V2, "paths": paths or PROJECT_PATHS})


def _parse_project(before: bytes) -> tuple[bytes | None, str | None]:
    try:
        value = json.loads(before)
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"{PROJECT_FILE} is unreadable JSON: {exc}"
    if not isinstance(value, dict) or set(value) != PROJECT_FIELDS:
        return None, f"{PROJECT_FILE} has unknown or missing fields; restore a supported manifest"
    version = value.get("schema_version")
    paths = value.get("paths")
    if not isinstance(version, str) or not version:
        return None, f"{PROJECT_FILE} has an empty or non-string schema_version"
    if version not in {PROJECT_V1, PROJECT_V2}:
        return None, f"{PROJECT_FILE} schema_version {version!r} is unsupported"
    if not isinstance(paths, dict) or set(paths) != set(PROJECT_PATHS):
        return None, f"{PROJECT_FILE} paths do not carry the closed Trinity path set"
    normalized: dict[str, str] = {}
    for key, expected in PROJECT_PATHS.items():
        candidate = paths.get(key)
        if not isinstance(candidate, str) or not candidate:
            return None, f"{PROJECT_FILE} paths.{key} is empty or non-string"
        if version == PROJECT_V1 and not candidate.startswith("./"):
            candidate = f"./{candidate}"
        try:
            _root_relative(candidate)
        except MigrationError as exc:
            return None, f"{PROJECT_FILE} paths.{key} is unsafe: {exc}"
        if candidate != expected:
            return None, f"{PROJECT_FILE} paths.{key} must be {expected!r}, got {candidate!r}"
        normalized[key] = candidate
    after = _project_document(normalized)
    if version == PROJECT_V2:
        return (None, None) if before == after else (None, f"{PROJECT_FILE} v2 is not canonical")
    return after, None


def legacy_bundle_digest(
    bundle_root: Path, replacements: dict[str, FileSnapshot | None] | None = None
) -> str:
    """Reproduce the pre-bundle-identity pipeline digest from commit 07aca95."""

    if not bundle_root.is_dir():
        raise MigrationError(f"bundle {bundle_root.name} is unavailable")
    files = sorted(path for path in bundle_root.rglob("*") if path.is_file() or path.is_symlink())
    hasher = hashlib.sha256()
    for path in files:
        relative = path.relative_to(bundle_root).as_posix()
        replacement = MISSING if replacements is None else replacements.get(relative, MISSING)
        if replacement is None:
            continue
        hasher.update(relative.encode("utf-8"))
        hasher.update(b"\0")
        if replacement is not MISSING:
            if not isinstance(replacement, FileSnapshot):
                raise MigrationError(f"replacement path {relative} has invalid snapshot data")
            payload = replacement.data
            hasher.update(b"file\0")
        elif path.is_symlink():
            payload = str(path.readlink()).encode("utf-8")
            hasher.update(b"symlink\0")
        else:
            payload = path.read_bytes()
            hasher.update(b"file\0")
        hasher.update(str(len(payload)).encode("ascii"))
        hasher.update(b"\0")
        hasher.update(payload)
        hasher.update(b"\0")
    return hasher.hexdigest()


def _virtual_bundle_digest(bundle_root: Path, replacements: dict[str, FileSnapshot | None]) -> str:
    manifest = list(tree_manifest(bundle_root))
    found = {item.path for item in manifest}
    if {path for path, value in replacements.items() if value is not None} - found:
        raise MigrationError(f"replacement path is absent from bundle {bundle_root.name}")
    changed: list[FileIdentity] = []
    for item in manifest:
        replacement = replacements.get(item.path, MISSING)
        if replacement is None:
            continue
        if replacement is MISSING:
            changed.append(item)
        else:
            if not isinstance(replacement, FileSnapshot):
                raise MigrationError(f"replacement path {item.path} has invalid snapshot data")
            changed.append(
                FileIdentity(
                    path=item.path,
                    digest=_digest(replacement.data),
                    executable=bool(replacement.mode & 0o111),
                )
            )
    return manifest_digest(tuple(changed))


def _bundle_originals(
    bundle: Path, root: Path, originals: dict[str, FileSnapshot | None] | None
) -> dict[str, FileSnapshot | None]:
    if originals is None:
        return {}
    prefix = f"./{bundle.relative_to(root).as_posix()}/"
    return {
        path.removeprefix(prefix): snapshot
        for path, snapshot in originals.items()
        if path.startswith(prefix)
    }


def _chain_digest(entry: dict[str, object]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _digest(canonical.encode("utf-8"))


def _load_queue(data: bytes) -> list[dict[str, object]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MigrationError(f"{PIPELINE_QUEUE} is not UTF-8: {exc}") from exc
    records: list[dict[str, object]] = []
    previous = "0" * 64
    for number, line in enumerate(text.splitlines(), start=1):
        if not line:
            raise MigrationError(f"{PIPELINE_QUEUE} line {number} is blank")
        try:
            entry = json.loads(line)
        except ValueError as exc:
            raise MigrationError(f"{PIPELINE_QUEUE} line {number} is invalid JSON: {exc}") from exc
        if not isinstance(entry, dict) or set(entry) != QUEUE_FIELDS:
            raise MigrationError(f"{PIPELINE_QUEUE} line {number} has an unknown queue schema")
        if entry.get("seq") != number or entry.get("prev_hash") != previous:
            raise MigrationError(f"{PIPELINE_QUEUE} line {number} does not link in sequence")
        if entry.get("entry_hash") != _chain_digest(entry):
            raise MigrationError(f"{PIPELINE_QUEUE} line {number} has an invalid entry_hash")
        uuid = entry.get("uuid")
        digest = entry.get("bundle_digest")
        if not isinstance(uuid, str) or UUID.fullmatch(uuid) is None:
            raise MigrationError(f"{PIPELINE_QUEUE} line {number} has an invalid uuid")
        if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
            raise MigrationError(f"{PIPELINE_QUEUE} line {number} has an invalid bundle_digest")
        previous = str(entry["entry_hash"])
        records.append(entry)
    return records


def _render_queue(records: list[dict[str, object]]) -> bytes:
    previous = "0" * 64
    lines: list[str] = []
    for entry in records:
        entry["prev_hash"] = previous
        entry["entry_hash"] = _chain_digest(entry)
        previous = str(entry["entry_hash"])
        lines.append(json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def _manifest_paths(root: Path) -> list[tuple[str, Path, str]]:
    out: list[tuple[str, Path, str]] = []
    for lane in ("staging", "samples", "delivery"):
        lane_path = _path(root, f"./{lane}")
        if not lane_path.exists():
            continue
        if not lane_path.is_dir():
            raise MigrationError(f"./{lane} is not a directory")
        for child in sorted(lane_path.iterdir(), key=lambda item: item.name):
            if UUID.fullmatch(child.name) is None:
                continue
            relative = f"./{lane}/{child.name}/task.toml"
            manifest = _path(root, relative)
            if manifest.is_file():
                out.append((relative, manifest, child.name))
    return out


def _plan_harbor(
    root: Path, originals: dict[str, FileSnapshot | None] | None = None
) -> tuple[list[PlannedWrite], list[str]]:
    writes: list[PlannedWrite] = []
    blocked: list[str] = []
    for relative, _manifest, uuid in _manifest_paths(root):
        snapshot = _virtual_snapshot(root, relative, originals)
        if snapshot is None:
            blocked.append(f"{relative}: disappeared from the original migration snapshot")
            continue
        before = snapshot.data
        try:
            document = tomllib.loads(before.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            blocked.append(f"{relative}: malformed Harbor TOML ({exc}); repair and revalidate")
            continue
        version = document.get("schema_version")
        if not isinstance(version, str) or not version:
            blocked.append(
                f"{relative}: empty or missing schema_version; select a supported schema"
            )
            continue
        metadata = document.get("metadata")
        retired_pin = isinstance(metadata, dict) and "harbor_version" in metadata
        legacy_network = any(
            isinstance(document.get(section), dict)
            and document[section].get("network_mode") == "none"
            for section in ("agent", "verifier")
        )
        task = document.get("task")
        legacy_authors = (
            isinstance(task, dict)
            and isinstance(task.get("authors"), list)
            and any(
                isinstance(item, str) or (isinstance(item, dict) and set(item) == {"email"})
                for item in task["authors"]
            )
        )
        missing_task_identity = (
            not isinstance(task, dict)
            or not isinstance(task.get("name"), str)
            or not isinstance(task.get("version"), str)
        )
        legacy = (
            version == "1.0"
            or retired_pin
            or legacy_network
            or legacy_authors
            or missing_task_identity
        )
        if not legacy:
            if version != "1.4":
                blocked.append(
                    f"{relative}: schema_version {version!r} is outside the supported "
                    "1.0 -> 1.4 matrix"
                )
            continue
        if version not in {"1.0", "1.4"}:
            blocked.append(
                f"{relative}: legacy fields under schema_version {version!r} are ambiguous; "
                "migrate manually"
            )
            continue
        slug = f"{root.name}-{uuid[:8]}"
        after_text = migrate_text(before.decode("utf-8"), org=DEFAULT_ORG, slug=slug)
        after = after_text.encode("utf-8")
        try:
            parsed_after = tomllib.loads(after_text)
        except tomllib.TOMLDecodeError as exc:  # pragma: no cover - guards the existing API
            blocked.append(f"{relative}: Harbor migration did not produce valid TOML ({exc})")
            continue
        if parsed_after.get("schema_version") != "1.4":
            blocked.append(f"{relative}: Harbor migration did not reach schema_version 1.4")
            continue
        if after != before:
            writes.append(
                _planned_write(
                    root,
                    step_id=f"harbor-{uuid}",
                    path=relative,
                    before=before,
                    after=after,
                    needs_revalidation=True,
                    originals=originals,
                )
            )
    return writes, blocked


def _plan_queue(
    root: Path,
    harbor_writes: Sequence[PlannedWrite],
    originals: dict[str, FileSnapshot | None] | None = None,
) -> tuple[PlannedWrite | None, list[str], list[str]]:
    queue_snapshot = _virtual_snapshot(root, PIPELINE_QUEUE, originals)
    if queue_snapshot is None:
        return None, [], []
    before = queue_snapshot.data
    try:
        records = _load_queue(before)
    except MigrationError as exc:
        return None, [str(exc)], []
    latest_index: dict[str, int] = {}
    for index, record in enumerate(records):
        latest_index[str(record["uuid"])] = index
    harbor_by_uuid = {write.id.removeprefix("harbor-"): write for write in harbor_writes}
    changed = False
    revalidate: list[str] = []
    blocked: list[str] = []
    for uuid, index in sorted(latest_index.items()):
        record = records[index]
        homes: list[str] = []
        for lane in ("staging", "samples", "delivery"):
            relative = f"./{lane}/{uuid}"
            try:
                metadata = (root / lane / uuid).lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISDIR(metadata.st_mode):
                raise MigrationError(f"queue record {uuid} has an unsafe object at {relative}")
            homes.append(relative)
        if len(homes) > 1:
            raise MigrationError(f"queue record {uuid} resolves under more than one root")
        if not homes:
            verdict = root / ".audit" / "verdicts" / f"{uuid}.json"
            try:
                raw = json.loads(verdict.read_text(encoding="utf-8")) if verdict.is_file() else None
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                raw = None
            if (
                isinstance(raw, dict)
                and set(raw) <= {"uuid", "bundle_digest", "outcome"}
                and all(isinstance(value, str) for value in raw.values())
                and raw.get("uuid") == verdict.stem
                and isinstance(raw.get("bundle_digest"), str)
                and HEX64.fullmatch(raw["bundle_digest"]) is not None
                and raw.get("outcome") == "retained"
                and raw["bundle_digest"] == record["bundle_digest"]
            ):
                continue
            raise MigrationError(f"queue record {uuid} resolves under no root")
        bundle = _path(root, homes[0], allow_missing=False)
        bundle_originals = _bundle_originals(bundle, root, originals)
        try:
            old_digest = legacy_bundle_digest(bundle, bundle_originals)
            current_digest = (
                _virtual_bundle_digest(bundle, bundle_originals)
                if bundle_originals
                else manifest_digest(tree_manifest(bundle))
            )
        except (MigrationError, OSError, ValueError) as exc:
            blocked.append(f"{PIPELINE_QUEUE} uuid {uuid}: cannot identify current bytes ({exc})")
            continue
        sealed = str(record["bundle_digest"])
        harbor_write = harbor_by_uuid.get(uuid)
        if sealed not in {old_digest, current_digest}:
            blocked.append(
                f"{PIPELINE_QUEUE} uuid {uuid}: seal matches neither legacy nor current identity; "
                "restore bytes or reseal"
            )
            continue
        if harbor_write is None:
            migrated_digest = current_digest
        else:
            migrated_digest = _virtual_bundle_digest(
                bundle,
                {
                    **bundle_originals,
                    "task.toml": FileSnapshot(harbor_write.after, harbor_write.after_mode),
                },
            )
        if sealed == migrated_digest:
            continue
        record["bundle_digest"] = migrated_digest
        changed = True
        verdict = root / ".audit" / "verdicts" / f"{uuid}.json"
        if verdict.is_file():
            revalidate.append(
                f"{uuid}: prior verdict remains byte-for-byte but names the legacy digest; "
                "rerun audit and resign release evidence"
            )
    if blocked or not changed:
        return None, blocked, revalidate
    after = _render_queue(records)
    return (
        _planned_write(
            root,
            step_id="pipeline-legacy-digest",
            path=PIPELINE_QUEUE,
            before=before,
            after=after,
            needs_revalidation=bool(revalidate),
            originals=originals,
        ),
        [],
        revalidate,
    )


def _plan_progress(
    root: Path,
    originals: dict[str, FileSnapshot | None] | None = None,
    *,
    apply_backups: bool = False,
) -> tuple[PlannedWrite | None, list[str], list[str]]:
    """Retain a legacy harness progress cache: backed up, never rewritten, parsed, or deleted.

    The roster is the three harness roots as literal paths, so a run-scoped
    ``<harness>/runs/<run_id>/progress.yaml`` is outside it by construction. Nothing is planned
    for the legacy bytes; only the immutable content-addressed backup and one revalidation record
    naming the replacing generator are produced.
    """

    blocked: list[str] = []
    revalidate: list[str] = []
    for relative in PROGRESS_CACHES:
        try:
            snapshot = _virtual_snapshot(root, relative, originals)
            if snapshot is None:
                continue
            if apply_backups:
                retained = PlannedWrite(
                    f"progress-legacy-cache-{_digest(snapshot.data)}",
                    relative,
                    snapshot.data,
                    snapshot.data,
                    True,
                    snapshot.mode,
                    snapshot.mode,
                )
                _create_backup(root, retained.journal_step(), snapshot.data)
        except (MigrationError, OSError) as exc:
            blocked.append(
                f"{relative}: legacy progress cache cannot be preserved ({exc}); restore safe "
                "bytes before retrying"
            )
            continue
        revalidate.append(
            f"{relative}: legacy harness progress cache retained with an immutable backup under "
            f"{BACKUP_DIR}; progress.py rebuild is the replacing generator for the run-scoped "
            "projection"
        )
    return None, blocked, revalidate


def _schema_records(data: bytes, location: str) -> list[str]:
    """Detect discriminators only; this never authenticates or accepts evidence."""
    value = parse_json(data)
    if not isinstance(value, dict):
        raise MigrationError(f"{location}: expected a JSON object for schema inspection")
    if "payload" in value:
        payload = value["payload"]
        if not isinstance(payload, str):
            raise MigrationError(f"{location}: DSSE payload must be base64 text")
        value = parse_json(base64.b64decode(payload, validate=True))
        if not isinstance(value, dict):
            raise MigrationError(f"{location}: DSSE payload must be a JSON object")
    return [
        f"{location}: {schema}: {REISSUE_ACTIONS[schema]}"
        for field in ("schemaVersion", "predicateType", "schema")
        if isinstance(schema := value.get(field), str) and schema in REISSUE_ACTIONS
    ]


def _schema_revalidation(root: Path, trust_dir: str | None) -> tuple[str, ...]:
    records: list[str] = []
    for relative in ("./.seed/pilot-policy.json", "./.seed/pilot-attempts.jsonl"):
        data = _read_optional(root, relative)
        if data is None:
            continue
        if relative.endswith(".jsonl"):
            for number, line in enumerate(data.splitlines(), 1):
                records.extend(_schema_records(line, f"{relative}:{number}"))
        else:
            records.extend(_schema_records(data, relative))
    for relative in ("./.audit/attestations/execution", "./.audit/receipts/oracle"):
        directory = _path(root, relative)
        if not directory.exists():
            continue
        if not directory.is_dir():
            raise MigrationError(f"{relative}: expected an evidence directory")
        for entry in sorted(directory.rglob("*")):
            name = f"./{entry.relative_to(root).as_posix()}"
            path = _path(root, name)
            if path.is_dir():
                continue
            data = _read_optional(root, name)
            if data is not None:
                records.extend(_schema_records(data, name))
    configured = trust_dir if trust_dir is not None else os.environ.get("TRINITY_RELEASE_TRUST_DIR")
    if configured is not None:
        authority = invocation_root()
        directory = resolve_project_path(
            configured,
            project_root=authority,
            description="release trust directory",
            must_exist=True,
        )
        if directory == root or root in directory.parents or not directory.is_dir():
            raise MigrationError("release trust directory must live outside the candidate tree")
        relative = display_project_path(directory / "policy.json", project_root=authority)
        data = _read_optional(authority, relative)
        if data is None:
            raise MigrationError(f"external governance {relative}: policy is missing")
        records.extend(_schema_records(data, f"external governance {relative}"))
    return tuple(records)


def _plan(
    root: Path,
    originals: dict[str, FileSnapshot | None] | None = None,
    reissues: tuple[str, ...] = (),
    *,
    apply_backups: bool = False,
) -> tuple[list[PlannedWrite], list[str], list[str]]:
    writes: list[PlannedWrite] = []
    blocked: list[str] = []
    revalidate: list[str] = list(reissues)
    project_snapshot = _virtual_snapshot(root, PROJECT_FILE, originals)
    project = None if project_snapshot is None else project_snapshot.data
    if project is None:
        writes.append(
            _planned_write(
                root,
                step_id="project-manifest-bootstrap",
                path=PROJECT_FILE,
                before=None,
                after=_project_document(),
                originals=originals,
            )
        )
    else:
        after, error = _parse_project(project)
        if error is not None:
            blocked.append(error)
        elif after is not None:
            writes.append(
                _planned_write(
                    root,
                    step_id="project-manifest-v1-v2",
                    path=PROJECT_FILE,
                    before=project,
                    after=after,
                    originals=originals,
                )
            )
    try:
        harbor_writes, harbor_blocked = _plan_harbor(root, originals)
    except MigrationError as exc:
        harbor_writes, harbor_blocked = [], [str(exc)]
    writes.extend(harbor_writes)
    blocked.extend(harbor_blocked)
    revalidate.extend(
        f"{write.path}: rerun Harbor validation and issue new signatures for affected evidence"
        for write in harbor_writes
    )
    queue_write, queue_blocked, queue_revalidation = _plan_queue(root, harbor_writes, originals)
    if queue_write is not None:
        writes.append(queue_write)
    blocked.extend(queue_blocked)
    revalidate.extend(queue_revalidation)
    if queue_blocked and harbor_writes:
        blocked.append(
            "Harbor writes were not applied because their legacy queue seals could not be proven"
        )
    _, progress_blocked, progress_revalidation = _plan_progress(
        root, originals, apply_backups=apply_backups
    )
    blocked.extend(progress_blocked)
    revalidate.extend(progress_revalidation)
    if revalidate:
        existing_snapshot = _virtual_snapshot(root, REVALIDATION_FILE, originals)
        existing = None if existing_snapshot is None else existing_snapshot.data
        after = _revalidation_bytes(revalidate)
        if existing != after:
            writes.append(
                _planned_write(
                    root,
                    step_id="needs-revalidation-report",
                    path=REVALIDATION_FILE,
                    before=existing,
                    after=after,
                    needs_revalidation=True,
                    originals=originals,
                )
            )
    return writes, blocked, revalidate


def _plan_digest(
    steps: Sequence[JournalStep], field: Literal["before_sha256", "after_sha256"]
) -> str:
    hasher = hashlib.sha256()
    for step in steps:
        bound = {
            "id": step["id"],
            "path": step["path"],
            "digest": step[field],
            "backup": step["backup"],
            "before_mode": step["before_mode"],
            "after_mode": step["after_mode"],
            "needs_revalidation": step["needs_revalidation"],
        }
        hasher.update(json.dumps(bound, sort_keys=True, separators=(",", ":")).encode())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _validate_step(value: object) -> JournalStep:
    if not isinstance(value, dict) or set(value) != STEP_FIELDS:
        raise MigrationError("migration journal step has an unknown or missing field")
    if not isinstance(value.get("id"), str) or not value["id"]:
        raise MigrationError("migration journal step id is empty")
    path = value.get("path")
    if not isinstance(path, str):
        raise MigrationError("migration journal step path is not a string")
    _root_relative(path)
    _assert_writable_surface(path)
    for field in ("before_sha256", "after_sha256"):
        digest = value.get(field)
        if not isinstance(digest, str) or HEX64.fullmatch(digest) is None:
            raise MigrationError(f"migration journal step {field} is not a sha256")
    backup = value.get("backup")
    if backup is not None:
        if not isinstance(backup, str):
            raise MigrationError("migration journal backup path is invalid")
        _root_relative(backup)
        if not backup.startswith(f"{BACKUP_DIR}/"):
            raise MigrationError("migration journal backup is outside the backup store")
    before_mode = value.get("before_mode")
    after_mode = value.get("after_mode")
    if before_mode is not None and type(before_mode) is not int:
        raise MigrationError("migration journal before_mode is invalid")
    if type(after_mode) is not int:
        raise MigrationError("migration journal after_mode is invalid")
    if before_mode is not None:
        _validated_mode(stat.S_IFREG | before_mode, path)
    _validated_mode(stat.S_IFREG | after_mode, path)
    if value["before_sha256"] == ABSENT_DIGEST:
        if before_mode is not None or backup is not None:
            raise MigrationError("absent migration source may not carry a mode or backup")
    elif before_mode is None or backup != f"{BACKUP_DIR}/{value['before_sha256']}":
        raise MigrationError("existing migration source has inconsistent mode or backup")
    needs_revalidation = value.get("needs_revalidation")
    if not isinstance(needs_revalidation, bool):
        raise MigrationError("migration journal needs_revalidation is invalid")
    status = value.get("status")
    if status not in STEP_STATUSES:
        raise MigrationError(f"migration journal step status {status!r} is unknown")
    return {
        "id": str(value["id"]),
        "path": str(value["path"]),
        "before_sha256": str(value["before_sha256"]),
        "after_sha256": str(value["after_sha256"]),
        "backup": None if value["backup"] is None else str(value["backup"]),
        "before_mode": before_mode,
        "after_mode": after_mode,
        "needs_revalidation": needs_revalidation,
        "status": str(value["status"]),
    }


def _load_journal(root: Path) -> Journal | None:
    data = _read_optional(root, JOURNAL_FILE)
    if data is None:
        return None
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise MigrationError(f"{JOURNAL_FILE} is unreadable: {exc}") from exc
    if not isinstance(value, dict) or set(value) != JOURNAL_FIELDS:
        raise MigrationError(f"{JOURNAL_FILE} has an unknown or incomplete schema")
    if value.get("version") != JOURNAL_VERSION:
        raise MigrationError(
            f"{JOURNAL_FILE} version {value.get('version')!r} is unsupported; use matching "
            "Trinity tooling"
        )
    raw_steps = value.get("steps")
    if not isinstance(raw_steps, list):
        raise MigrationError(f"{JOURNAL_FILE} steps is not a list")
    steps = [_validate_step(item) for item in raw_steps]
    if len({step["id"] for step in steps}) != len(steps):
        raise MigrationError(f"{JOURNAL_FILE} repeats a step id")
    before = value.get("before_sha256")
    after = value.get("after_sha256")
    if before != _plan_digest(steps, "before_sha256") or after != _plan_digest(
        steps, "after_sha256"
    ):
        raise MigrationError(f"{JOURNAL_FILE} plan hashes do not match its steps")
    backups = value.get("backups")
    expected_backups = sorted(str(step["backup"]) for step in steps if step["backup"] is not None)
    if backups != expected_backups:
        raise MigrationError(f"{JOURNAL_FILE} backup inventory does not match its steps")
    if value.get("status") not in JOURNAL_STATUSES:
        raise MigrationError(f"{JOURNAL_FILE} status is unknown")
    journal_status = str(value["status"])
    if journal_status == "complete" and any(step["status"] == "pending" for step in steps):
        raise MigrationError(f"{JOURNAL_FILE} claims completion with a pending step")
    if journal_status == "planned" and any(step["status"] != "pending" for step in steps):
        raise MigrationError(f"{JOURNAL_FILE} planned state contains a completed step")
    if any(
        (step["status"] == "needs_revalidation") != step["needs_revalidation"]
        for step in steps
        if step["status"] != "pending"
    ):
        raise MigrationError(f"{JOURNAL_FILE} step status contradicts its revalidation binding")
    journal: Journal = {
        "version": JOURNAL_VERSION,
        "steps": steps,
        "before_sha256": str(before),
        "after_sha256": str(after),
        "backups": expected_backups,
        "status": journal_status,
    }
    _verify_backups(root, journal)
    _verify_journal_targets(root, journal)
    return journal


def _verify_backups(root: Path, journal: Journal) -> None:
    for step in journal["steps"]:
        backup = step["backup"]
        if backup is None:
            continue
        snapshot = _snapshot_optional(root, backup)
        target = _snapshot_optional(root, step["path"])
        target_digest = ABSENT_DIGEST if target is None else _digest(target.data)
        if snapshot is None and target_digest == step["before_sha256"]:
            continue
        if (
            snapshot is None
            or _digest(snapshot.data) != step["before_sha256"]
            or snapshot.mode != BACKUP_MODE
        ):
            raise MigrationError(f"backup {backup} is missing or tampered; restore it before retry")


def _verify_journal_targets(root: Path, journal: Journal) -> None:
    for step in journal["steps"]:
        snapshot = _snapshot_optional(root, step["path"])
        current = ABSENT_DIGEST if snapshot is None else _digest(snapshot.data)
        allowed = {step["before_sha256"], step["after_sha256"]}
        if current not in allowed:
            raise MigrationError(
                f"{step['path']} matches neither journal before nor after sha256; restore or "
                "revalidate manually"
            )
        if step["status"] in {"applied", "needs_revalidation"} and current != step["after_sha256"]:
            raise MigrationError(f"{step['path']} was changed after its migration postcondition")
        expected_mode = (
            step["after_mode"] if current == step["after_sha256"] else step["before_mode"]
        )
        current_mode = None if snapshot is None else snapshot.mode
        if current_mode != expected_mode:
            raise MigrationError(f"{step['path']} mode changed outside its migration plan")


def _journal_for(writes: Sequence[PlannedWrite]) -> Journal:
    steps = [write.journal_step() for write in writes]
    return {
        "version": JOURNAL_VERSION,
        "steps": steps,
        "before_sha256": _plan_digest(steps, "before_sha256") if steps else EMPTY_PLAN_DIGEST,
        "after_sha256": _plan_digest(steps, "after_sha256") if steps else EMPTY_PLAN_DIGEST,
        "backups": sorted(str(step["backup"]) for step in steps if step["backup"] is not None),
        "status": "planned",
    }


def _originals_from_journal(root: Path, journal: Journal) -> dict[str, FileSnapshot | None]:
    originals: dict[str, FileSnapshot | None] = {}
    for step in journal["steps"]:
        if step["before_sha256"] == ABSENT_DIGEST:
            originals[step["path"]] = None
            continue
        backup = None if step["backup"] is None else _snapshot_optional(root, step["backup"])
        if backup is not None:
            before_mode = step["before_mode"]
            if before_mode is None:  # guarded by journal schema validation
                raise MigrationError("existing migration source lacks its original mode")
            originals[step["path"]] = FileSnapshot(backup.data, before_mode)
            continue
        current = _snapshot_optional(root, step["path"])
        if (
            current is None
            or _digest(current.data) != step["before_sha256"]
            or current.mode != step["before_mode"]
        ):
            raise MigrationError(
                f"{step['path']} cannot reconstruct its verified original migration snapshot"
            )
        originals[step["path"]] = current
    return originals


def _bind_incomplete_journal(journal: Journal, writes: Sequence[PlannedWrite]) -> None:
    expected = _journal_for(writes)
    if len(journal["steps"]) != len(expected["steps"]):
        raise MigrationError("incomplete journal does not match the full derived migration plan")
    for persisted, derived in zip(journal["steps"], expected["steps"], strict=True):
        persisted_identity = (
            persisted["id"],
            persisted["path"],
            persisted["before_sha256"],
            persisted["after_sha256"],
            persisted["backup"],
            persisted["before_mode"],
            persisted["after_mode"],
            persisted["needs_revalidation"],
        )
        derived_identity = (
            derived["id"],
            derived["path"],
            derived["before_sha256"],
            derived["after_sha256"],
            derived["backup"],
            derived["before_mode"],
            derived["after_mode"],
            derived["needs_revalidation"],
        )
        if persisted_identity != derived_identity:
            raise MigrationError(
                "incomplete journal step is not exactly bound to the derived supported operation"
            )
    if (
        journal["before_sha256"] != expected["before_sha256"]
        or journal["after_sha256"] != expected["after_sha256"]
        or journal["backups"] != expected["backups"]
    ):
        raise MigrationError("incomplete journal plan metadata does not match the derived plan")


def _mkdir_secure(path: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    if not current.is_dir() or current.is_symlink():
        raise MigrationError(f"cannot create migration file beneath non-directory {current.name}")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        directory.chmod(0o700)
        _fsync_directory(directory.parent)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_replace(path: Path, data: bytes, mode: int = 0o600) -> None:
    _mkdir_secure(path.parent)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_journal(root: Path, journal: Journal) -> None:
    _atomic_replace(_path(root, JOURNAL_FILE), _canonical_json(journal))


def _create_backup(root: Path, step: JournalStep, before: bytes) -> None:
    backup = step["backup"]
    if backup is None:
        raise MigrationError(f"{step['path']} has bytes but no backup path")
    path = _path(root, backup)
    _mkdir_secure(path.parent)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, BACKUP_MODE)
    except FileExistsError:
        existing = _snapshot_optional(root, backup)
        if (
            existing is None
            or _digest(existing.data) != step["before_sha256"]
            or existing.mode != BACKUP_MODE
        ):
            raise MigrationError(f"backup {backup} already exists with different bytes") from None
        return
    os.fchmod(descriptor, BACKUP_MODE)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(before)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(path.parent)


def _lock(root: Path) -> tuple[int, Path]:
    path = _path(root, LOCK_FILE)
    _mkdir_secure(path.parent)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise MigrationError(
            f"{LOCK_FILE} already exists; confirm no migrator is running, then remove only "
            "that lock"
        ) from exc
    os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
    os.fsync(descriptor)
    _fsync_directory(path.parent)
    return descriptor, path


def _rollback(root: Path, applied: Sequence[JournalStep]) -> None:
    for step in reversed(applied):
        target = _path(root, step["path"])
        if step["backup"] is None:
            if target.exists():
                target.unlink()
                _fsync_directory(target.parent)
        else:
            backup = _read_optional(root, step["backup"])
            if backup is None or _digest(backup) != step["before_sha256"]:
                raise MigrationError(f"cannot roll back {step['path']}: backup is unavailable")
            before_mode = step["before_mode"]
            if before_mode is None:
                raise MigrationError(f"cannot roll back {step['path']}: original mode is missing")
            _atomic_replace(target, backup, before_mode)
        step["status"] = "pending"


def _revalidation_bytes(items: Sequence[str]) -> bytes:
    return _canonical_json(
        {
            "schema_version": "trinity.needs-revalidation/v1",
            "records": list(items),
            "required_action": (
                "rerun the named audit or validation and issue new signatures; old evidence "
                "is not grandfathered"
            ),
        }
    )


def _journal_revalidation(root: Path, journal: Journal | None) -> tuple[str, ...]:
    if journal is None:
        return ()
    unresolved: list[str] = []
    for step in journal["steps"]:
        if step["status"] != "needs_revalidation":
            continue
        if step["id"].startswith("harbor-"):
            uuid = step["id"].removeprefix("harbor-")
            manifest = _read_optional(root, step["path"])
            receipt = _read_optional(root, f"./.audit/receipts/harbor/{uuid}.json")
            value: object = None
            if receipt is not None:
                with contextlib.suppress(UnicodeDecodeError, ValueError):
                    value = json.loads(receipt)
            valid = (
                manifest is not None
                and isinstance(value, dict)
                and value.get("ok") is True
                and value.get("task_toml_sha256") == _digest(manifest)
            )
            if not valid:
                unresolved.append(
                    f"{step['path']}: rerun Harbor validation and issue new signatures for "
                    "affected evidence"
                )
        elif step["id"] == "pipeline-legacy-digest":
            queue = _read_optional(root, PIPELINE_QUEUE)
            if queue is None:
                unresolved.append(f"{PIPELINE_QUEUE}: restore and revalidate the migrated queue")
                continue
            for record in _load_queue(queue):
                uuid = str(record["uuid"])
                verdict = _read_optional(root, f"./.audit/verdicts/{uuid}.json")
                if verdict is None:
                    continue
                value = None
                with contextlib.suppress(UnicodeDecodeError, ValueError):
                    value = json.loads(verdict)
                if (
                    not isinstance(value, dict)
                    or value.get("bundle_digest") != record["bundle_digest"]
                ):
                    unresolved.append(
                        f"{uuid}: rerun audit against the current bundle identity and resign "
                        "affected release evidence"
                    )
    return tuple(unresolved)


def migrate(root: Path, *, dry_run: bool = False, trust_dir: str | None = None) -> MigrationReport:
    """Plan or apply every supported migration beneath ``root``."""

    try:
        root = root.resolve(strict=True)
        if not root.is_dir() or root.is_symlink():
            raise MigrationError("project root must be a real directory")
        journal = _load_journal(root)
        reissues = _schema_revalidation(root, trust_dir)
        if journal is not None and journal["status"] != "complete":
            originals = _originals_from_journal(root, journal)
            writes, blocked, revalidation = _plan(
                root, originals, reissues, apply_backups=not dry_run
            )
            _bind_incomplete_journal(journal, writes)
        else:
            writes, blocked, revalidation = _plan(
                root, reissues=reissues, apply_backups=not dry_run
            )
    except (MigrationError, OSError, ValueError) as exc:
        return MigrationReport(
            "hold", (), (), (str(exc),), ("repair persisted migration state",), dry_run
        )
    if blocked:
        actions = tuple(
            "restore the exact prior bytes or perform a reviewed manual migration and revalidation"
            for _ in blocked
        )
        return MigrationReport("hold", (), tuple(revalidation), tuple(blocked), actions, dry_run)
    journal_revalidation = _journal_revalidation(root, journal)
    revalidation = list(dict.fromkeys((*revalidation, *journal_revalidation)))
    if journal is not None and journal["status"] == "complete" and not writes:
        return MigrationReport(
            "hold" if reissues else "noop", (), tuple(revalidation), (), reissues, dry_run
        )
    if not writes:
        return MigrationReport(
            "hold" if reissues else "noop", (), tuple(revalidation), (), reissues, dry_run
        )
    for write in writes:
        _assert_writable_surface(write.path)
    changed = tuple(write.path for write in writes)
    if dry_run:
        return MigrationReport(
            "hold" if reissues else "planned", changed, tuple(revalidation), (), reissues, True
        )
    state = _journal_for(writes)
    if journal is not None and journal["status"] != "complete":
        state = journal
    descriptor: int | None = None
    lock_path: Path | None = None
    applied_this_run: list[JournalStep] = []
    try:
        descriptor, lock_path = _lock(root)
        if journal is None or journal["status"] == "complete":
            _write_journal(root, state)
        state["status"] = "applying"
        _write_journal(root, state)
        for step, write in zip(state["steps"], writes, strict=True):
            current = _snapshot_optional(root, write.path)
            current_digest = ABSENT_DIGEST if current is None else _digest(current.data)
            current_mode = None if current is None else current.mode
            if current_digest == step["after_sha256"] and current_mode == write.after_mode:
                step["status"] = "needs_revalidation" if write.needs_revalidation else "applied"
                _write_journal(root, state)
                continue
            if current_digest != step["before_sha256"] or current_mode != write.before_mode:
                raise MigrationError(f"{write.path} changed after planning; no write was made")
            if current is not None:
                _create_backup(root, step, current.data)
            target = _path(root, write.path)
            applied_this_run.append(step)
            _atomic_replace(target, write.after, write.after_mode)
            applied = _snapshot_optional(root, write.path)
            if (
                applied is None
                or _digest(applied.data) != step["after_sha256"]
                or applied.mode != write.after_mode
            ):
                raise MigrationError(f"{write.path} failed its migration postcondition")
            step["status"] = "needs_revalidation" if write.needs_revalidation else "applied"
            _write_journal(root, state)
        state["status"] = "complete"
        _write_journal(root, state)
    except (MigrationError, OSError, ValueError) as exc:
        try:
            _rollback(root, applied_this_run)
            state["status"] = "hold"
            _write_journal(root, state)
        except (MigrationError, OSError, ValueError) as rollback_exc:
            exc = MigrationError(f"{exc}; rollback also refused: {rollback_exc}")
        return MigrationReport(
            "hold",
            (),
            tuple(revalidation),
            (str(exc),),
            ("repair the reported bytes from immutable backups, then retry",),
            False,
        )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if lock_path is not None:
            with contextlib.suppress(FileNotFoundError):
                lock_path.unlink()
                _fsync_directory(lock_path.parent)
    return MigrationReport(
        "hold" if reissues else "complete",
        changed,
        tuple(revalidation) or _journal_revalidation(root, state),
        (),
        reissues,
        False,
    )


def compatibility_check(root: Path, *, apply: bool) -> MigrationReport:
    """Gate-facing lightweight entry point; checking is read-only, applying is authoring-only."""

    return migrate(root, dry_run=not apply)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="migrate.py", description=__doc__)
    parser.add_argument("root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="apply; default is a read-only dry run")
    mode.add_argument("--check", action="store_true", help="inspect without writing")
    parser.add_argument("--trust-dir", help="external release trust directory, as for release.py")
    parser.add_argument("--json", action="store_true")
    return parser


def _render(report: MigrationReport) -> str:
    lines = [f"migration: {report.status}"]
    lines.extend(f"  change {path}" for path in report.changed)
    lines.extend(f"  needs_revalidation {item}" for item in report.needs_revalidation)
    lines.extend(f"  HOLD {item}" for item in report.blocked)
    lines.extend(f"  action {item}" for item in report.required_actions)
    return "\n".join(lines)


def main(argv: Sequence[str]) -> int:
    args = _parser().parse_args(argv[1:])
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            args.root,
            project_root=project_root,
            description="project root",
            must_exist=True,
        )
    except ProjectPathError as exc:
        print(f"migration refused: {exc}", file=sys.stderr)
        return 2
    report = migrate(root, dry_run=not args.apply, trust_dir=args.trust_dir)
    if args.json:
        public = report.to_json()
        public["changed"] = [
            display_project_path(_path(root, item), project_root=project_root)
            for item in report.changed
        ]
        text = json.dumps(public, indent=2, sort_keys=True)
        print(redact_project_root(text, project_root=project_root))
    else:
        print(redact_project_root(_render(report), project_root=project_root))
    return 2 if report.status == "hold" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
