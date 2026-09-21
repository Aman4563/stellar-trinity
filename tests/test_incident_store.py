from __future__ import annotations

import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tools import incident_store
from tools.incident_store import Config, ingest, parse_incident

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def config(tmp_path: Path, *, threshold: int = 2) -> Config:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    return Config(
        state_dir=state,
        candidate_roots=(candidate,),
        threshold=threshold,
        window_seconds=30 * 24 * 60 * 60,
        max_age_seconds=86_400,
        max_future_skew_seconds=300,
        allowed_sender_ids=frozenset({"1001"}),
        allowed_observer_repository_ids=frozenset({"2002"}),
        allowed_target_repository_ids=frozenset({"3003"}),
    )


def config_document(*, state_dir: str = "./state") -> dict[str, object]:
    return {
        "allowed_observer_repository_ids": ["2002"],
        "allowed_sender_ids": ["1001"],
        "allowed_target_repository_ids": ["3003"],
        "candidate_roots": ["./candidate"],
        "max_age_seconds": 86_400,
        "max_future_skew_seconds": 300,
        "schema": incident_store.CONFIG_SCHEMA,
        "state_dir": state_dir,
        "threshold": 2,
        "window_seconds": 30 * 24 * 60 * 60,
    }


def write_config(tmp_path: Path, document: dict[str, object] | None = None) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(document or config_document()), encoding="utf-8")
    path.chmod(0o600)
    return path


def event(
    *,
    run_id: str,
    run_attempt: int = 1,
    at: datetime = NOW,
    actor_id: str = "17",
    codes: list[str] | None = None,
) -> bytes:
    payload = {
        "actor_id": actor_id,
        "actor_login": "alice",
        "commit_sha": "a" * 40,
        "evidence_digest": "b" * 64,
        "finding_codes": codes or ["SAB_SELF_APPROVAL"],
        "occurred_at": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": "EtharaOrion/argos",
        "repository_id": "3003",
        "run_attempt": run_attempt,
        "run_id": run_id,
        "schema": incident_store.EVENT_SCHEMA,
    }
    return json.dumps(payload).encode()


def alerts(cfg: Config) -> list[sqlite3.Row]:
    with incident_store.database(cfg) as connection:
        return connection.execute("SELECT * FROM repeat_alerts ORDER BY event_id").fetchall()


def test_two_distinct_attempts_record_one_durable_alert_and_duplicate_is_idempotent(
    tmp_path: Path,
) -> None:
    cfg = config(tmp_path)
    first = parse_incident(event(run_id="101"), cfg, now=NOW)
    second = parse_incident(event(run_id="102", run_attempt=2), cfg, now=NOW)
    assert ingest(cfg, first, now=NOW) is False
    assert ingest(cfg, second, now=NOW) is True
    assert ingest(cfg, second, now=NOW + timedelta(seconds=1)) is False
    recorded = alerts(cfg)
    assert len(recorded) == 1
    assert recorded[0]["event_id"] == second.event_id
    assert recorded[0]["source"] == "observer-threshold"
    assert recorded[0]["distinct_run_count"] == 2


def test_further_repeats_inside_an_alerted_window_signal_at_most_once(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    runs = [
        parse_incident(
            event(run_id=str(101 + index), at=NOW + timedelta(minutes=index)), cfg, now=NOW
        )
        for index in range(5)
    ]
    assert ingest(cfg, runs[0], now=NOW) is False
    assert ingest(cfg, runs[1], now=NOW) is True
    for later in runs[2:]:
        assert ingest(cfg, later, now=NOW) is False
    recorded = alerts(cfg)
    assert len(recorded) == 1
    assert recorded[0]["event_id"] == runs[1].event_id
    assert recorded[0]["distinct_run_count"] == 2
    document = incident_store.status_document(cfg)
    assert document["repeat_alerts"] == 1
    assert document["incidents"] == 5


def test_a_new_episode_after_the_alerted_run_leaves_the_window_alerts_again(
    tmp_path: Path,
) -> None:
    cfg = config(tmp_path)
    window = timedelta(seconds=cfg.window_seconds)
    first = parse_incident(event(run_id="101", at=NOW), cfg, now=NOW)
    second = parse_incident(event(run_id="102", at=NOW), cfg, now=NOW)
    assert ingest(cfg, first, now=NOW) is False
    assert ingest(cfg, second, now=NOW) is True
    later_now = NOW + window + timedelta(hours=2)
    third = parse_incident(
        event(run_id="103", at=later_now - timedelta(hours=1)), cfg, now=later_now
    )
    fourth = parse_incident(event(run_id="104", at=later_now), cfg, now=later_now)
    assert ingest(cfg, third, now=later_now) is False
    assert ingest(cfg, fourth, now=later_now) is True
    recorded = alerts(cfg)
    assert len(recorded) == 2
    assert {row["event_id"] for row in recorded} == {second.event_id, fourth.event_id}


def test_same_actor_with_distinct_codes_is_not_a_repeat(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    first = parse_incident(event(run_id="101", codes=["SAB_SELF_APPROVAL"]), cfg, now=NOW)
    second = parse_incident(event(run_id="102", codes=["SAB_INERT_INSTRUMENT"]), cfg, now=NOW)
    assert ingest(cfg, first, now=NOW) is False
    assert ingest(cfg, second, now=NOW) is False
    assert alerts(cfg) == []


def test_multiple_codes_are_grouped_into_one_attempt_and_one_alert(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    codes = ["SAB_SELF_APPROVAL", "SAB_STALE_DIGEST_REUSE"]
    first = parse_incident(event(run_id="101", codes=codes), cfg, now=NOW)
    second = parse_incident(event(run_id="102", codes=codes), cfg, now=NOW)
    assert ingest(cfg, first, now=NOW) is False
    assert ingest(cfg, second, now=NOW) is True
    assert len(alerts(cfg)) == 1


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (event(run_id="501", at=NOW - timedelta(days=2)), "stale"),
        (event(run_id="502", at=NOW + timedelta(minutes=6)), "future"),
        (event(run_id="503", codes=["TEST_FAILED"]), "affirmative"),
    ],
)
def test_authoritative_ingest_rejects_bad_time_and_generic_failures(
    tmp_path: Path, document: bytes, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        parse_incident(document, config(tmp_path), now=NOW)


def test_status_is_nonzero_only_after_meaningful_unsafe_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = config(tmp_path)
    config_path = write_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    first = parse_incident(event(run_id="101"), cfg, now=NOW)
    second = parse_incident(event(run_id="102"), cfg, now=NOW)
    assert ingest(cfg, first, now=NOW) is False
    assert incident_store.main(["status", "--config", "./config.json"]) == 0
    assert ingest(cfg, second, now=NOW) is True
    assert incident_store.main(["status", "--config", "./config.json"]) == 1
    document = incident_store.status_document(cfg)
    assert document["unsafe_repeat"] is True
    assert document["repeat_alerts"] == 1
    assert config_path.exists()


def test_equivocation_is_retained_without_forging_a_repeat_alert(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    original = parse_incident(event(run_id="401"), cfg, now=NOW)
    conflict_document = json.loads(event(run_id="401"))
    conflict_document["commit_sha"] = "c" * 40
    conflict = parse_incident(json.dumps(conflict_document).encode(), cfg, now=NOW)
    assert ingest(cfg, original, now=NOW) is False
    with pytest.raises(ValueError, match="conflicting"):
        ingest(cfg, conflict, now=NOW)
    status = incident_store.status_document(cfg)
    assert status["equivocations"] == 1
    assert status["unsafe_repeat"] is False
    with incident_store.database(cfg) as connection:
        stored = connection.execute("SELECT commit_sha FROM incidents").fetchone()[0]
        diagnostic = connection.execute("SELECT * FROM equivocations").fetchone()
    assert stored == "a" * 40
    assert diagnostic["event_id"] == original.event_id
    assert diagnostic["existing_digest"] != diagnostic["received_digest"]


def test_out_of_order_events_alert_on_the_newest_once(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    newest = parse_incident(event(run_id="202", at=NOW), cfg, now=NOW)
    older = parse_incident(event(run_id="201", at=NOW - timedelta(hours=1)), cfg, now=NOW)
    assert ingest(cfg, newest, now=NOW) is False
    assert ingest(cfg, older, now=NOW) is True
    assert ingest(cfg, newest, now=NOW) is False
    rows = alerts(cfg)
    assert len(rows) == 1
    assert rows[0]["event_id"] == newest.event_id


def test_run_retries_are_stored_but_do_not_count_as_distinct_attempts(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    first = parse_incident(event(run_id="301", run_attempt=1), cfg, now=NOW)
    retry = parse_incident(event(run_id="301", run_attempt=2), cfg, now=NOW)
    assert ingest(cfg, first, now=NOW) is False
    assert ingest(cfg, retry, now=NOW) is False
    assert alerts(cfg) == []


def test_concurrent_ingest_records_one_repeat_alert(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    first = parse_incident(event(run_id="801"), cfg, now=NOW)
    second = parse_incident(event(run_id="802"), cfg, now=NOW)
    ingest(cfg, first, now=NOW)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: ingest(cfg, second, now=NOW), range(2)))
    assert sum(results) == 1
    assert len(alerts(cfg)) == 1


def test_legacy_database_preserves_incidents_and_archives_outbox_in_place(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    incident = parse_incident(event(run_id="901"), cfg, now=NOW)
    path = cfg.state_dir / "incidents.sqlite3"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE incidents (
            event_id TEXT PRIMARY KEY, repository_id TEXT NOT NULL, repository TEXT NOT NULL,
            run_id TEXT NOT NULL, run_attempt INTEGER NOT NULL, occurred_at TEXT NOT NULL,
            actor_id TEXT NOT NULL, actor_login TEXT, commit_sha TEXT NOT NULL,
            evidence_digest TEXT NOT NULL, codes_json TEXT NOT NULL,
            UNIQUE(repository_id, run_id, run_attempt)
        );
        CREATE TABLE outbox (
            event_id TEXT PRIMARY KEY REFERENCES incidents(event_id),
            message_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL, next_attempt_at TEXT NOT NULL, attempts INTEGER NOT NULL,
            sent_at TEXT, last_error TEXT, lease_token TEXT, lease_until TEXT, unknown_note TEXT
        );
        """
    )
    connection.execute(
        "INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        incident_store._incident_values(incident),
    )
    connection.execute(
        "INSERT INTO outbox VALUES (?, ?, ?, ?, 0, NULL, NULL, NULL, NULL, ?)",
        (incident.event_id, "legacy-id", incident_store._format_time(NOW), "later", "preserve-me"),
    )
    connection.commit()
    connection.close()
    path.chmod(0o600)
    with incident_store.database(cfg) as migrated:
        tables = {
            row[0] for row in migrated.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "outbox" not in tables
        assert "legacy_mail_outbox_v1" in tables
        assert migrated.execute("SELECT count(*) FROM incidents").fetchone()[0] == 1
        legacy = migrated.execute("SELECT * FROM legacy_mail_outbox_v1").fetchone()
        alert = migrated.execute("SELECT * FROM repeat_alerts").fetchone()
    assert legacy["unknown_note"] == "preserve-me"
    assert alert["event_id"] == incident.event_id
    assert alert["source"] == "legacy-mail-outbox-v1"


def test_legacy_config_migration_keeps_exact_private_backup_and_removes_transport_fields(
    tmp_path: Path,
) -> None:
    (tmp_path / "candidate").mkdir()
    (tmp_path / "state").mkdir(mode=0o700)
    legacy = config_document()
    legacy["schema"] = incident_store.LEGACY_CONFIG_SCHEMA
    legacy.update(
        {
            "sender": "historical-address.example",
            "smtp_host": "historical-host",
            "smtp_password_env": "OLD_SECRET_NAME",
            "smtp_port": 465,
            "smtp_transport": "ssl",
            "smtp_username_env": "OLD_USER_NAME",
            "timeout_seconds": 10,
            "unknown_future_data": {"keep": True},
        }
    )
    path = write_config(tmp_path, legacy)
    original = path.read_bytes()
    assert incident_store.migrate_config(path, project_root=tmp_path) is True
    backup = path.with_name("config.json.legacy-v1")
    assert backup.read_bytes() == original
    assert backup.stat().st_mode & 0o077 == 0
    current = json.loads(path.read_text(encoding="utf-8"))
    assert current == config_document()
    loaded = incident_store.load_config(path, project_root=tmp_path)
    assert loaded.state_dir == tmp_path / "state"
    assert incident_store.migrate_config(path, project_root=tmp_path) is False


def test_concurrent_store_operations_never_call_umask_or_escape_symlinks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store_root = tmp_path / "store"
    store_root.mkdir()
    cfg = config(store_root, threshold=10)
    first = parse_incident(event(run_id="1000"), cfg, now=NOW)

    migration_paths: list[Path] = []
    for index in range(2):
        root = tmp_path / f"migration-{index}"
        root.mkdir()
        (root / "candidate").mkdir()
        (root / "state").mkdir(mode=0o700)
        legacy = config_document()
        legacy["schema"] = incident_store.LEGACY_CONFIG_SCHEMA
        legacy.update(
            {
                "sender": "historical-address.example",
                "smtp_host": "historical-host",
                "smtp_password_env": "OLD_SECRET_NAME",
                "smtp_port": 465,
                "smtp_transport": "ssl",
                "smtp_username_env": "OLD_USER_NAME",
            }
        )
        migration_paths.append(write_config(root, legacy))

    def reject_umask(_mask: int) -> int:
        raise AssertionError("process-global umask mutation is forbidden")

    monkeypatch.setattr(os, "umask", reject_umask)
    assert ingest(cfg, first, now=NOW) is False
    incidents = [
        parse_incident(event(run_id=str(1001 + index)), cfg, now=NOW) for index in range(4)
    ]
    with ThreadPoolExecutor(max_workers=6) as executor:
        ingest_futures = [executor.submit(ingest, cfg, item, now=NOW) for item in incidents]
        migration_futures = [
            executor.submit(incident_store.migrate_config, path, project_root=path.parent)
            for path in migration_paths
        ]
        assert [future.result() for future in ingest_futures] == [False] * 4
        assert [future.result() for future in migration_futures] == [True] * 2

    database_path = cfg.state_dir / "incidents.sqlite3"
    assert database_path.stat().st_mode & 0o777 == 0o600
    assert cfg.state_dir.stat().st_mode & 0o777 == 0o700
    for path in migration_paths:
        assert path.with_name("config.json.legacy-v1").stat().st_mode & 0o777 == 0o600

    outside_database = tmp_path / "outside.sqlite3"
    outside_database.write_bytes(b"outside database")
    outside_database.chmod(0o600)
    escape_root = tmp_path / "escape-store"
    escape_root.mkdir()
    escape_cfg = config(escape_root)
    (escape_cfg.state_dir / "incidents.sqlite3").symlink_to(outside_database)
    with pytest.raises(ValueError, match="symbolic link"), incident_store.database(escape_cfg):
        pass
    assert outside_database.read_bytes() == b"outside database"

    outside_backup = tmp_path / "outside-backup"
    outside_backup.write_bytes(b"outside backup")
    outside_backup.chmod(0o600)
    symlink_path = migration_paths[0].with_name("linked-config.json")
    symlink_path.write_bytes(migration_paths[0].with_name("config.json.legacy-v1").read_bytes())
    symlink_path.chmod(0o600)
    symlink_path.with_name("linked-config.json.legacy-v1").symlink_to(outside_backup)
    with pytest.raises(ValueError, match="backup already exists"):
        incident_store.migrate_config(symlink_path, project_root=symlink_path.parent)
    assert outside_backup.read_bytes() == b"outside backup"


def test_load_config_rejects_symlink_state_and_state_inside_candidate(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    state = candidate / "state"
    state.mkdir(mode=0o700)
    path = write_config(tmp_path, config_document(state_dir="./candidate/state"))
    with pytest.raises(ValueError, match="outside"):
        incident_store.load_config(path, project_root=tmp_path)
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    link = tmp_path / "state-link"
    link.symlink_to(external, target_is_directory=True)
    path.write_text(json.dumps(config_document(state_dir="./state-link")), encoding="utf-8")
    with pytest.raises(ValueError, match="symbolic links"):
        incident_store.load_config(path, project_root=tmp_path)


@pytest.mark.parametrize(
    "value", ["state", "/state", "~/state", ".\\state", "./../state", "./link/state"]
)
def test_load_config_rejects_noncanonical_or_escaping_paths(tmp_path: Path, value: str) -> None:
    (tmp_path / "candidate").mkdir()
    (tmp_path / "state").mkdir(mode=0o700)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    path = write_config(tmp_path, config_document(state_dir=value))
    with pytest.raises(ValueError):
        incident_store.load_config(path, project_root=tmp_path)


def test_authorization_uses_external_numeric_allowlists(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    incident_store.authorize_source(cfg, sender_id="1001", source_repository_id="2002")
    with pytest.raises(ValueError, match="sender"):
        incident_store.authorize_source(cfg, sender_id="9999", source_repository_id="2002")
    incident_store.authorize_target(cfg, "3003")
    with pytest.raises(ValueError, match="target"):
        incident_store.authorize_target(cfg, "9999")


@pytest.mark.parametrize(
    "document",
    [
        b'{"schema":"x","schema":"y"}',
        json.dumps({"nested": [[[[[[[[[1]]]]]]]]]}).encode(),
        json.dumps({"run_attempt": 1.5}).encode(),
    ],
)
def test_duplicate_deep_and_float_json_are_controlled_refusals(
    tmp_path: Path, document: bytes
) -> None:
    with pytest.raises(ValueError):
        parse_incident(document, config(tmp_path), now=NOW)


def test_run_attempt_document_size_and_control_characters_are_bounded(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    document = json.loads(event(run_id="601"))
    document["run_attempt"] = 2**63
    with pytest.raises(ValueError, match="signed 64-bit"):
        parse_incident(json.dumps(document).encode(), cfg, now=NOW)
    with pytest.raises(ValueError, match="size limit"):
        parse_incident(b" " * (incident_store.MAX_DOCUMENT_BYTES + 1), cfg, now=NOW)
    document = json.loads(event(run_id="701"))
    document["repository"] = "safe/repo\nforged"
    with pytest.raises(ValueError, match="control"):
        parse_incident(json.dumps(document).encode(), cfg, now=NOW)


def test_runtime_has_no_delivery_transport_or_reset_command() -> None:
    source = Path(incident_store.__file__).read_text(encoding="utf-8")
    forbidden = ("smtplib", "email.message", "send_message", "starttls", "dispatch")
    assert all(term not in source for term in forbidden)
    parser = incident_store.build_parser()
    help_text = parser.format_help()
    assert "{ingest,status,check,migrate-config}" in help_text
    with pytest.raises(SystemExit):
        parser.parse_args(["dispatch", "--config", "./config.json"])
