"""Trusted, durable storage for repeated sentinel incidents.

This program is deployed from independently governed source. It accepts only bounded, closed
JSON emitted by trusted observer orchestration and stores incidents, equivocations, and repeat
alerts in external SQLite state. It has no message delivery or external notification transport.
Authentication of the caller belongs to the CI/service boundary; candidate repository bytes are
never authority.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import sqlite3
import stat
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from tools.project_paths import (
        ProjectPathError,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
else:
    try:
        from tools.project_paths import (
            ProjectPathError,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from project_paths import (
            ProjectPathError,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )

CONFIG_SCHEMA = "trinity.incident-store-config/v2"
LEGACY_CONFIG_SCHEMA = "trinity.incident-mail-config/v1"
EVENT_SCHEMA = "trinity.sentinel-incident/v1"
DEFAULT_THRESHOLD = 5
DEFAULT_WINDOW_SECONDS = 30 * 24 * 60 * 60
MAX_DOCUMENT_BYTES = 65_536
MAX_CODES = 32
MAX_TEXT = 200
MIN_THRESHOLD = 2
MAX_THRESHOLD = 100
MAX_WINDOW_SECONDS = 366 * 24 * 60 * 60
MAX_AGE_SECONDS = 7 * 24 * 60 * 60
MAX_FUTURE_SKEW_SECONDS = 60 * 60
MAX_RUN_ATTEMPT = (2**63) - 1
MAX_JSON_DEPTH = 8
MAX_JSON_NODES = 256
MAX_ALLOWLIST_IDS = 100
MAX_STATUS_ALERTS = 100
MAX_SQL_VARIABLES = 500
EXIT_FAILURE = 1
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_ID = re.compile(r"[A-Za-z0-9._:/@+-]{1,200}\Z")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_CONFIG_REQUIRED = {
    "allowed_observer_repository_ids",
    "allowed_sender_ids",
    "allowed_target_repository_ids",
    "candidate_roots",
    "state_dir",
}
_CONFIG_OPTIONAL = {
    "max_age_seconds",
    "max_future_skew_seconds",
    "schema",
    "threshold",
    "window_seconds",
}
_LEGACY_REMOVED_FIELDS = {
    "sender",
    "smtp_host",
    "smtp_password_env",
    "smtp_port",
    "smtp_transport",
    "smtp_username_env",
    "timeout_seconds",
}
_LEGACY_REQUIRED_REMOVED_FIELDS = _LEGACY_REMOVED_FIELDS - {"timeout_seconds"}
_EVENT_FIELDS = {
    "actor_id",
    "actor_login",
    "commit_sha",
    "evidence_digest",
    "finding_codes",
    "occurred_at",
    "repository",
    "repository_id",
    "run_attempt",
    "run_id",
    "schema",
}
AFFIRMATIVE_CODES = frozenset(
    {
        "SAB_AGENT_WROTE_HUMAN_ROOT",
        "SAB_AUTHOR_SPOOF",
        "SAB_BUNDLE_MUTATED_AFTER_AUDIT",
        "SAB_DIRTY_TREE_CLAIMED_CLEAN",
        "SAB_DISPOSITION_FORGED",
        "SAB_EXPORT_WITHOUT_RECEIPT",
        "SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS",
        "SAB_INERT_INSTRUMENT",
        "SAB_LEDGER_ROLLBACK",
        "SAB_SELF_APPROVAL",
        "SAB_STALE_DIGEST_REUSE",
        "SAB_SUBMODULE_TAMPERED",
    }
)


@dataclass(frozen=True, slots=True)
class Config:
    state_dir: Path
    candidate_roots: tuple[Path, ...]
    threshold: int
    window_seconds: int
    max_age_seconds: int
    max_future_skew_seconds: int
    allowed_sender_ids: frozenset[str]
    allowed_observer_repository_ids: frozenset[str]
    allowed_target_repository_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class Incident:
    event_id: str
    repository_id: str
    repository: str
    run_id: str
    run_attempt: int
    occurred_at: datetime
    actor_id: str
    actor_login: str | None
    commit_sha: str
    evidence_digest: str
    codes: tuple[str, ...]


class _DuplicateKeyError(ValueError):
    pass


def _object_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number {value!r} is forbidden")


def _validate_json_shape(value: object, *, depth: int = 0, nodes: list[int] | None = None) -> None:
    counter = [0] if nodes is None else nodes
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
        raise ValueError("JSON structure exceeds depth or node bounds")
    if isinstance(value, float):
        raise ValueError("JSON floating-point values are forbidden")
    if isinstance(value, dict):
        for child in value.values():
            _validate_json_shape(child, depth=depth + 1, nodes=counter)
    elif isinstance(value, list):
        for child in value:
            _validate_json_shape(child, depth=depth + 1, nodes=counter)


def _loads_bounded(document: bytes) -> object:
    try:
        value: object = json.loads(
            document,
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, _DuplicateKeyError) as exc:
        raise ValueError("document is malformed or contains duplicate JSON keys") from exc
    _validate_json_shape(value)
    return value


def _read_bounded(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError(f"{path} must not be a symbolic link")
    with path.open("rb") as handle:
        document = handle.read(MAX_DOCUMENT_BYTES + 1)
    if len(document) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"{path} exceeds {MAX_DOCUMENT_BYTES} bytes")
    return document


def _closed_json_bytes(document: bytes, description: str) -> dict[str, object]:
    try:
        value = _loads_bounded(document)
    except ValueError as exc:
        raise ValueError(f"{description} is malformed JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{description} must contain a JSON object")
    return cast(dict[str, object], value)


def _closed_json(path: Path) -> dict[str, object]:
    try:
        return _closed_json_bytes(_read_bounded(path), str(path))
    except OSError as exc:
        raise ValueError(f"{path} is unreadable or malformed JSON") from exc


def _owned_private(path: Path, description: str) -> None:
    metadata = path.stat(follow_symlinks=False)
    if stat.S_ISLNK(metadata.st_mode):
        raise ValueError(f"{description} must not be a symbolic link")
    if metadata.st_uid != os.getuid():
        raise ValueError(f"{description} must be owned by the observer account")
    if metadata.st_mode & 0o077:
        raise ValueError(f"{description} must not grant group or other permissions")


def _existing_path_has_symlink(path: Path) -> bool:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if not current.exists() and not current.is_symlink():
            continue
        if current.is_symlink():
            return True
    return False


def _positive_int(value: object, name: str, default: int, maximum: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"config field {name} must be an integer from 1 through {maximum}")
    return value


def _identifier_set(value: object, name: str) -> frozenset[str]:
    if not isinstance(value, list) or not value or len(value) > MAX_ALLOWLIST_IDS:
        raise ValueError(f"config field {name} must be a bounded non-empty list")
    return frozenset(_numeric_identifier(item, f"{name} entry") for item in value)


def _numeric_identifier(value: object, name: str) -> str:
    text = _text(value, name)
    if not text.isascii() or not text.isdigit() or text.startswith("0"):
        raise ValueError(f"field {name} must be a positive decimal platform ID")
    if int(text) > MAX_RUN_ATTEMPT:
        raise ValueError(f"field {name} exceeds the signed 64-bit bound")
    return text


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TEXT:
        raise ValueError(
            f"field {name} must be a non-empty string of at most {MAX_TEXT} characters"
        )
    if _CONTROL.search(value):
        raise ValueError(f"field {name} contains control characters")
    return value


def _safe_identifier(value: object, name: str) -> str:
    text = _text(value, name)
    if _SAFE_ID.fullmatch(text) is None:
        raise ValueError(f"field {name} contains characters outside the identifier allowlist")
    return text


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _config_path(path: Path, root: Path) -> Path:
    try:
        relative_config = path.relative_to(root).as_posix()
        resolved = resolve_project_path(
            "./" + relative_config,
            project_root=root,
            description="incident-store config",
            must_exist=True,
        )
    except ValueError as exc:
        raise ValueError(
            "incident-store config must be beneath project root without symlinks"
        ) from exc
    _owned_private(resolved, "incident-store config")
    return resolved


def _current_config_document(document: dict[str, object]) -> dict[str, object]:
    fields = set(document)
    if not fields >= _CONFIG_REQUIRED or fields - _CONFIG_REQUIRED - _CONFIG_OPTIONAL:
        raise ValueError("incident-store config does not match its closed schema")
    if document.get("schema") != CONFIG_SCHEMA:
        raise ValueError("incident-store config schema is unsupported; run migrate-config for v1")
    return document


def load_config(path: Path, *, project_root: Path | None = None) -> Config:
    """Load owner-controlled transport-free configuration and validate durable state."""
    root = project_root or invocation_root()
    resolved_config = _config_path(path, root)
    document = _current_config_document(_closed_json(resolved_config))
    state_raw = document["state_dir"]
    if not isinstance(state_raw, str):
        raise ValueError("config field state_dir must be a string")
    try:
        state_dir = resolve_project_path(
            state_raw,
            project_root=root,
            description="config field state_dir",
            must_exist=True,
        )
    except ProjectPathError as exc:
        raise ValueError(str(exc)) from exc
    if not state_dir.is_dir():
        raise ValueError("state_dir must be a pre-provisioned durable directory")
    _owned_private(state_dir, "state_dir")
    roots_raw = document["candidate_roots"]
    if not isinstance(roots_raw, list) or not roots_raw:
        raise ValueError("candidate_roots must be a non-empty list")
    roots: list[Path] = []
    for raw in roots_raw:
        if not isinstance(raw, str):
            raise ValueError("candidate_roots entries must be strings")
        try:
            roots.append(
                resolve_project_path(
                    raw,
                    project_root=root,
                    description="candidate_roots entry",
                    must_exist=True,
                )
            )
        except ProjectPathError as exc:
            raise ValueError(str(exc)) from exc
    resolved_state = state_dir.resolve()
    if any(_is_within(resolved_state, candidate_root) for candidate_root in roots):
        raise ValueError("state_dir must be outside every candidate repository")
    threshold = _positive_int(
        document.get("threshold"), "threshold", DEFAULT_THRESHOLD, MAX_THRESHOLD
    )
    if threshold < MIN_THRESHOLD:
        raise ValueError("threshold must require at least two distinct attempts")
    return Config(
        state_dir=state_dir,
        candidate_roots=tuple(roots),
        threshold=threshold,
        window_seconds=_positive_int(
            document.get("window_seconds"),
            "window_seconds",
            DEFAULT_WINDOW_SECONDS,
            MAX_WINDOW_SECONDS,
        ),
        max_age_seconds=_positive_int(
            document.get("max_age_seconds"), "max_age_seconds", 86_400, MAX_AGE_SECONDS
        ),
        max_future_skew_seconds=_positive_int(
            document.get("max_future_skew_seconds"),
            "max_future_skew_seconds",
            300,
            MAX_FUTURE_SKEW_SECONDS,
        ),
        allowed_sender_ids=_identifier_set(document["allowed_sender_ids"], "allowed_sender_ids"),
        allowed_observer_repository_ids=_identifier_set(
            document["allowed_observer_repository_ids"], "allowed_observer_repository_ids"
        ),
        allowed_target_repository_ids=_identifier_set(
            document["allowed_target_repository_ids"], "allowed_target_repository_ids"
        ),
    )


def _atomic_private_write(path: Path, document: bytes) -> None:
    temporary = path.with_name(f".{path.name}.new")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(document)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        path.chmod(0o600)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
        raise


def migrate_config(path: Path, *, project_root: Path | None = None) -> bool:
    """Migrate v1 configuration, retaining exact legacy and unknown data in a private backup."""
    root = project_root or invocation_root()
    resolved = _config_path(path, root)
    original = _read_bounded(resolved)
    document = _closed_json_bytes(original, "incident-store config")
    if document.get("schema") == CONFIG_SCHEMA:
        _current_config_document(document)
        return False
    if document.get("schema", LEGACY_CONFIG_SCHEMA) != LEGACY_CONFIG_SCHEMA:
        raise ValueError("legacy incident config schema is unsupported")
    required_legacy = _CONFIG_REQUIRED | _LEGACY_REQUIRED_REMOVED_FIELDS
    if not set(document) >= required_legacy:
        raise ValueError("legacy incident config is missing required v1 fields")
    migrated = {
        key: value
        for key, value in document.items()
        if key in _CONFIG_REQUIRED or key in _CONFIG_OPTIONAL
    }
    migrated["schema"] = CONFIG_SCHEMA
    _current_config_document(migrated)
    rendered = json.dumps(migrated, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    backup = resolved.with_name(f"{resolved.name}.legacy-v1")
    if backup.exists() or backup.is_symlink():
        if backup.is_symlink() or _read_bounded(backup) != original:
            raise ValueError("legacy config backup already exists with different bytes")
        _owned_private(backup, "legacy config backup")
    else:
        descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(original)
            handle.flush()
            os.fsync(handle.fileno())
    _atomic_private_write(resolved, rendered)
    return True


def _parse_time(value: object) -> datetime:
    text = _text(value, "occurred_at")
    if not text.endswith("Z"):
        raise ValueError("occurred_at must be an RFC 3339 UTC instant")
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError("occurred_at must be an RFC 3339 UTC instant") from exc


def _event_id(repository_id: str, run_id: str, run_attempt: int) -> str:
    identity = json.dumps(
        [repository_id, run_id, run_attempt], ensure_ascii=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(identity).hexdigest()


def _alert_id(event_id: str) -> str:
    return hashlib.sha256(f"repeat-alert:{event_id}".encode()).hexdigest()


def parse_incident(document: bytes, config: Config, *, now: datetime) -> Incident:
    if len(document) > MAX_DOCUMENT_BYTES:
        raise ValueError("incident document exceeds the size limit")
    raw = _loads_bounded(document)
    if not isinstance(raw, dict) or set(raw) != _EVENT_FIELDS:
        raise ValueError("incident document does not match its closed schema")
    value = cast(dict[str, object], raw)
    if value["schema"] != EVENT_SCHEMA:
        raise ValueError("incident schema is unsupported")
    occurred_at = _parse_time(value["occurred_at"])
    if occurred_at < now - timedelta(seconds=config.max_age_seconds):
        raise ValueError("incident timestamp is stale")
    if occurred_at > now + timedelta(seconds=config.max_future_skew_seconds):
        raise ValueError("incident timestamp is in the future")
    run_attempt = value["run_attempt"]
    if (
        isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or not 1 <= run_attempt <= MAX_RUN_ATTEMPT
    ):
        raise ValueError("run_attempt must be a positive signed 64-bit integer")
    codes_raw = value["finding_codes"]
    if not isinstance(codes_raw, list) or not 1 <= len(codes_raw) <= MAX_CODES:
        raise ValueError("finding_codes must be a bounded non-empty list")
    codes: list[str] = []
    for code_raw in codes_raw:
        code = _safe_identifier(code_raw, "finding_codes entry")
        if code not in AFFIRMATIVE_CODES:
            raise ValueError(f"finding code {code!r} is not an affirmative integrity code")
        codes.append(code)
    digest = value["evidence_digest"]
    commit = value["commit_sha"]
    if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
        raise ValueError("evidence_digest must be a lowercase SHA-256 digest")
    if not isinstance(commit, str) or _HEX40.fullmatch(commit) is None:
        raise ValueError("commit_sha must be a full lowercase commit SHA")
    actor_login_raw = value["actor_login"]
    actor_login = (
        None if actor_login_raw is None else _safe_identifier(actor_login_raw, "actor_login")
    )
    repository_id = _numeric_identifier(value["repository_id"], "repository_id")
    run_id = _numeric_identifier(value["run_id"], "run_id")
    return Incident(
        event_id=_event_id(repository_id, run_id, run_attempt),
        repository_id=repository_id,
        repository=_safe_identifier(value["repository"], "repository"),
        run_id=run_id,
        run_attempt=run_attempt,
        occurred_at=occurred_at,
        actor_id=_numeric_identifier(value["actor_id"], "actor_id"),
        actor_login=actor_login,
        commit_sha=commit,
        evidence_digest=digest,
        codes=tuple(sorted(set(codes))),
    )


def _database_path(config: Config) -> Path:
    if _existing_path_has_symlink(config.state_dir) or not config.state_dir.is_dir():
        raise ValueError("state_dir is unavailable or contains symbolic traversal")
    _owned_private(config.state_dir, "state_dir")
    path = config.state_dir / "incidents.sqlite3"
    if path.is_symlink():
        raise ValueError("incident database must not be a symbolic link")
    if path.exists() and not path.is_file():
        raise ValueError("incident database must be a regular file")
    return path


def _prepare_database(path: Path) -> None:
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
    except FileExistsError:
        descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("incident database must be a regular file")
            if metadata.st_uid != os.getuid():
                raise ValueError("incident database must be owned by the observer account")
            if metadata.st_mode & 0o077:
                raise ValueError("incident database must not grant group or other permissions")
        finally:
            os.close(descriptor)
    else:
        try:
            os.fchmod(descriptor, 0o600)
        finally:
            os.close(descriptor)


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
        ).fetchone()
        is not None
    )


def _migrate_legacy_outbox(connection: sqlite3.Connection, config: Config) -> None:
    migration = "archive-mail-outbox-v1"
    if connection.execute(
        "SELECT 1 FROM schema_migrations WHERE migration = ?", (migration,)
    ).fetchone():
        return
    if _table_exists(connection, "outbox"):
        if _table_exists(connection, "legacy_mail_outbox_v1"):
            raise ValueError("both active and archived legacy outbox tables exist")
        connection.execute("ALTER TABLE outbox RENAME TO legacy_mail_outbox_v1")
    if _table_exists(connection, "legacy_mail_outbox_v1"):
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(legacy_mail_outbox_v1)").fetchall()
        }
        if {"event_id", "created_at"} <= columns:
            rows = connection.execute(
                "SELECT event_id, created_at FROM legacy_mail_outbox_v1 ORDER BY event_id"
            ).fetchall()
            for row in rows:
                event_id = str(row["event_id"])
                connection.execute(
                    """INSERT OR IGNORE INTO repeat_alerts
                       (event_id, alert_id, created_at, distinct_run_count, threshold, source)
                       SELECT ?, ?, ?, ?, ?, ?
                       WHERE EXISTS (SELECT 1 FROM incidents WHERE event_id = ?)""",
                    (
                        event_id,
                        _alert_id(event_id),
                        str(row["created_at"]),
                        config.threshold,
                        config.threshold,
                        "legacy-mail-outbox-v1",
                        event_id,
                    ),
                )
    connection.execute(
        "INSERT INTO schema_migrations (migration, applied_at) VALUES (?, ?)",
        (migration, _format_time(datetime.now(UTC))),
    )


@contextlib.contextmanager
def database(config: Config) -> Iterator[sqlite3.Connection]:
    path = _database_path(config)
    _prepare_database(path)
    connection = sqlite3.connect(path, timeout=30, isolation_level=None)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    event_id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    repository TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    run_attempt INTEGER NOT NULL,
                    occurred_at TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_login TEXT,
                    commit_sha TEXT NOT NULL,
                    evidence_digest TEXT NOT NULL,
                    codes_json TEXT NOT NULL,
                    UNIQUE(repository_id, run_id, run_attempt)
                );
                CREATE TABLE IF NOT EXISTS equivocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    existing_digest TEXT NOT NULL,
                    received_digest TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS repeat_alerts (
                    event_id TEXT PRIMARY KEY REFERENCES incidents(event_id),
                    alert_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    distinct_run_count INTEGER NOT NULL,
                    threshold INTEGER NOT NULL,
                    source TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            _migrate_legacy_outbox(connection, config)
            connection.execute("COMMIT")
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        yield connection
    finally:
        connection.close()


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def authorize_source(config: Config, *, sender_id: str, source_repository_id: str) -> None:
    """Authorize immutable IDs supplied by the independently governed observer runtime."""
    sender = _numeric_identifier(sender_id, "observer sender ID")
    source = _numeric_identifier(source_repository_id, "observer source repository ID")
    if sender not in config.allowed_sender_ids:
        raise ValueError("observer sender ID is not authorized")
    if source not in config.allowed_observer_repository_ids:
        raise ValueError("observer repository ID is not authorized")


def authorize_target(config: Config, repository_id: str) -> None:
    target = _numeric_identifier(repository_id, "target repository ID")
    if target not in config.allowed_target_repository_ids:
        raise ValueError("target repository ID is not authorized")


def _incident_values(incident: Incident) -> tuple[object, ...]:
    return (
        incident.event_id,
        incident.repository_id,
        incident.repository,
        incident.run_id,
        incident.run_attempt,
        _format_time(incident.occurred_at),
        incident.actor_id,
        incident.actor_login,
        incident.commit_sha,
        incident.evidence_digest,
        json.dumps(incident.codes, separators=(",", ":")),
    )


def _stored_incident_values(row: sqlite3.Row) -> tuple[object, ...]:
    return tuple(
        row[name]
        for name in (
            "event_id",
            "repository_id",
            "repository",
            "run_id",
            "run_attempt",
            "occurred_at",
            "actor_id",
            "actor_login",
            "commit_sha",
            "evidence_digest",
            "codes_json",
        )
    )


def _incident_fingerprint(values: tuple[object, ...]) -> str:
    document = json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode()
    return hashlib.sha256(document).hexdigest()


def _cluster_already_alerted(
    connection: sqlite3.Connection, cluster: Sequence[sqlite3.Row]
) -> bool:
    """True when any incident in the bounded repeat cluster already carries a repeat alert."""
    event_ids = [str(row["event_id"]) for row in cluster]
    for start in range(0, len(event_ids), MAX_SQL_VARIABLES):
        chunk = event_ids[start : start + MAX_SQL_VARIABLES]
        placeholders = ",".join("?" for _ in chunk)
        if connection.execute(
            f"SELECT 1 FROM repeat_alerts WHERE event_id IN ({placeholders}) LIMIT 1",
            chunk,
        ).fetchone():
            return True
    return False


def ingest(config: Config, incident: Incident, *, now: datetime) -> bool:
    """Transactionally admit one trusted event and record at most one repeat alert per cluster.

    Returns True only on the single ingest that raises the alert. Every later event that joins
    the same alerted window is recorded and returns False.
    """
    with database(config) as connection:
        connection.execute("BEGIN IMMEDIATE")
        try:
            values = _incident_values(incident)
            existing = connection.execute(
                "SELECT * FROM incidents WHERE event_id = ?", (incident.event_id,)
            ).fetchone()
            if existing is not None:
                stored = _stored_incident_values(existing)
                if stored != values:
                    connection.execute(
                        """INSERT INTO equivocations
                           (event_id, observed_at, existing_digest, received_digest)
                           VALUES (?, ?, ?, ?)""",
                        (
                            incident.event_id,
                            _format_time(now),
                            _incident_fingerprint(stored),
                            _incident_fingerprint(values),
                        ),
                    )
                    connection.execute("COMMIT")
                    raise ValueError("event identity was redelivered with conflicting content")
                connection.execute("COMMIT")
                return False
            connection.execute(
                "INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values
            )
            start = _format_time(incident.occurred_at - timedelta(seconds=config.window_seconds))
            end = _format_time(incident.occurred_at + timedelta(seconds=config.window_seconds))
            rows = connection.execute(
                """SELECT * FROM incidents
                   WHERE repository_id = ? AND occurred_at BETWEEN ? AND ?""",
                (incident.repository_id, start, end),
            ).fetchall()
            wanted = set(incident.codes)
            related: list[sqlite3.Row] = []
            for row in rows:
                row_codes = set(cast(list[str], json.loads(str(row["codes_json"]))))
                if wanted & row_codes:
                    related.append(row)
            latest = max(str(row["occurred_at"]) for row in related)
            latest_time = _parse_time(latest)
            bounded_related = [
                row
                for row in related
                if _parse_time(row["occurred_at"])
                >= latest_time - timedelta(seconds=config.window_seconds)
            ]
            distinct_runs = {str(row["run_id"]) for row in bounded_related}
            alerted = False
            if len(distinct_runs) >= config.threshold and not _cluster_already_alerted(
                connection, bounded_related
            ):
                target = next(
                    (
                        row
                        for row in bounded_related
                        if row["event_id"] == incident.event_id
                        and str(row["occurred_at"]) == latest
                    ),
                    max(
                        bounded_related,
                        key=lambda row: (str(row["occurred_at"]), str(row["event_id"])),
                    ),
                )
                target_event_id = str(target["event_id"])
                alerted = (
                    connection.execute(
                        """INSERT OR IGNORE INTO repeat_alerts
                           (event_id, alert_id, created_at, distinct_run_count, threshold, source)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            target_event_id,
                            _alert_id(target_event_id),
                            _format_time(now),
                            len(distinct_runs),
                            config.threshold,
                            "observer-threshold",
                        ),
                    ).rowcount
                    == 1
                )
            connection.execute("COMMIT")
            return alerted
        except BaseException:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise


def status_document(config: Config) -> dict[str, object]:
    """Return bounded human-inspectable authoritative state without changing it."""
    with database(config) as connection:
        incidents = int(connection.execute("SELECT count(*) FROM incidents").fetchone()[0])
        equivocations = int(connection.execute("SELECT count(*) FROM equivocations").fetchone()[0])
        repeat_alerts = int(connection.execute("SELECT count(*) FROM repeat_alerts").fetchone()[0])
        rows = connection.execute(
            """SELECT r.alert_id, r.created_at, r.distinct_run_count, r.threshold, r.source,
                      i.repository_id, i.repository, i.run_id, i.run_attempt, i.occurred_at,
                      i.actor_id, i.actor_login, i.commit_sha, i.evidence_digest, i.codes_json
               FROM repeat_alerts r JOIN incidents i ON i.event_id = r.event_id
               ORDER BY r.created_at DESC, r.alert_id DESC LIMIT ?""",
            (MAX_STATUS_ALERTS,),
        ).fetchall()
    alerts = [
        {
            "actor_id": str(row["actor_id"]),
            "actor_login": row["actor_login"],
            "alert_id": str(row["alert_id"]),
            "codes": cast(list[str], json.loads(str(row["codes_json"]))),
            "commit_sha": str(row["commit_sha"]),
            "created_at": str(row["created_at"]),
            "distinct_run_count": int(row["distinct_run_count"]),
            "evidence_digest": str(row["evidence_digest"]),
            "occurred_at": str(row["occurred_at"]),
            "repository": str(row["repository"]),
            "repository_id": str(row["repository_id"]),
            "run_attempt": int(row["run_attempt"]),
            "run_id": str(row["run_id"]),
            "source": str(row["source"]),
            "threshold": int(row["threshold"]),
        }
        for row in rows
    ]
    return {
        "alerts": alerts,
        "equivocations": equivocations,
        "incidents": incidents,
        "repeat_alerts": repeat_alerts,
        "schema": "trinity.incident-store-status/v1",
        "unsafe_repeat": repeat_alerts > 0,
    }


def check_database(config: Config) -> dict[str, object]:
    """Check SQLite integrity and return current bounded status."""
    with database(config) as connection:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
    if integrity != "ok" or foreign_keys:
        raise ValueError("incident database integrity check failed")
    return status_document(config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ingest_parser = commands.add_parser("ingest")
    ingest_parser.add_argument("--config", required=True)
    ingest_parser.add_argument("--event", required=True)
    ingest_parser.add_argument("--sender-id", required=True)
    ingest_parser.add_argument("--source-repository-id", required=True)
    for name in ("status", "check", "migrate-config"):
        command = commands.add_parser(name)
        command.add_argument("--config", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        project_root = invocation_root()
        config_path = resolve_project_path(
            str(args.config),
            project_root=project_root,
            description="incident-store config",
            must_exist=True,
        )
        if args.command == "migrate-config":
            migrated = migrate_config(config_path, project_root=project_root)
            print("migrated" if migrated else "current")
            return 0
        config = load_config(config_path, project_root=project_root)
        if args.command == "ingest":
            event_path = resolve_project_path(
                str(args.event),
                project_root=project_root,
                description="incident event",
                must_exist=True,
            )
            authorize_source(
                config,
                sender_id=str(args.sender_id),
                source_repository_id=str(args.source_repository_id),
            )
            incident = parse_incident(_read_bounded(event_path), config, now=datetime.now(UTC))
            authorize_target(config, incident.repository_id)
            print("alerted" if ingest(config, incident, now=datetime.now(UTC)) else "recorded")
            return 0
        document = check_database(config) if args.command == "check" else status_document(config)
        print(json.dumps(document, sort_keys=True, separators=(",", ":")))
        return EXIT_FAILURE if bool(document["unsafe_repeat"]) else 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        root = locals().get("project_root")
        message = (
            str(exc)
            if not isinstance(root, Path)
            else redact_project_root(str(exc), project_root=root)
        )
        print(f"incident-store refused: {message}", file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
