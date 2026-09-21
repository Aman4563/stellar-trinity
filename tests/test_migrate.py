from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest
from tools import migrate
from tools.bundle_identity import manifest_digest, tree_manifest

UUID = "11111111-2222-4333-8444-555555555555"
RUN_ID = "engram-20260101-000000-aaaaaaaa"
LEGACY_PROGRESS = b"schema_version: trinity.progress/v0\nphase: 2\nnote: legacy flat cache\n"

REFUSED_SCHEMAS = (
    (".seed/pilot-policy.json", "trinity.pilot-policy/v1", "schemaVersion", "groupCount"),
    (".seed/pilot-attempts.jsonl", "trinity.pilot-attempt/v1", "schemaVersion", "solverGroups"),
    (
        ".audit/attestations/execution/old.dsse",
        "trinity.execution/v1",
        "predicateType",
        "rolloutTelemetry",
    ),
    (
        ".audit/receipts/oracle/old.json.dsse",
        "trinity.oracle-run/v3",
        "schema",
        "execution_fidelity",
    ),
    ("policy.json", "trinity.release-policy/v2", "schema", "required_controls"),
)


@pytest.mark.parametrize(
    "case",
    [(schema, mode) for schema in REFUSED_SCHEMAS for mode in ("--check", "--json", "--apply")],
)
def test_refused_schema_requires_reissue_without_rewriting_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: tuple[tuple[str, str, str, str], str]
) -> None:
    # Given a legacy record at its consumer's real location, including external trust.
    (relative, schema, discriminator, required_field), mode = case
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    trust = tmp_path / "governance"
    trust.mkdir()
    monkeypatch.setenv("TRINITY_RELEASE_TRUST_DIR", "./governance")
    (trust / "policy.json").write_text('{"schema":"trinity.release-policy/v3"}')
    path = (trust if schema == "trinity.release-policy/v2" else candidate) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({discriminator: schema}).encode()
    original = payload + b"\n"
    if relative.endswith(".dsse"):
        original = json.dumps(
            {
                "payloadType": "application/vnd.in-toto+json",
                "payload": base64.b64encode(payload).decode(),
                "signatures": [],
            }
        ).encode()
    if relative.endswith(".jsonl"):
        original *= 2  # Each refused line is an instance, even with equal bytes.
    path.write_bytes(original)
    script = Path(migrate.__file__).resolve()

    # When the actual CLI checks or applies the migration plan.
    result = subprocess.run(
        [sys.executable, str(script), "./candidate", mode, "--json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    # Then every instance names the re-issuance action and the source stays byte-exact.
    assert result.stdout, result.stderr
    report = json.loads(result.stdout)
    records = report["needs_revalidation"]
    assert len(records) == (2 if relative.endswith(".jsonl") else 1)
    assert all(schema in record and required_field in record for record in records)
    assert all("re-issue" in record for record in records)
    assert all("execution_operator" in record for record in records)
    assert result.returncode == 2 and report["status"] == "hold"
    assert path.read_bytes() == original
    if mode == "--apply":
        sidecar = json.loads((candidate / migrate.REVALIDATION_FILE.removeprefix("./")).read_text())
        assert sidecar["records"] == records
        assert any(
            step["status"] == "needs_revalidation" for step in read_journal(candidate)["steps"]
        )
        repeated = subprocess.run(
            [sys.executable, str(script), "./candidate", "--check", "--json"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert json.loads(repeated.stdout)["needs_revalidation"] == records
        assert repeated.returncode == 2
    else:
        assert not (candidate / ".trinity").exists()


@pytest.mark.parametrize("schema", REFUSED_SCHEMAS[:4])
def test_current_schema_is_not_migration_authority(
    tmp_path: Path, schema: tuple[str, str, str, str]
) -> None:
    # Given a current discriminator, without evidence that could authorize release.
    relative, legacy, field, _ = schema
    current = legacy.rsplit("/v", 1)
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    original = json.dumps({field: f"{current[0]}/v{int(current[1]) + 1}"}).encode()
    path.write_bytes(original)

    # When the compatibility planner inspects it.
    report = migrate.migrate(tmp_path, dry_run=True)

    # Then it does not claim a schema migration or change the evidence.
    assert report.needs_revalidation == ()
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "relative",
    [".seed/pilot-policy.json", ".audit/attestations/execution", ".audit/receipts/oracle"],
)
def test_schema_inspection_refuses_symlink_without_writes(tmp_path: Path, relative: str) -> None:
    # Given an evidence path redirected outside the candidate.
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    path = candidate / relative
    path.parent.mkdir(parents=True)
    path.symlink_to(target, target_is_directory=True)

    # When application is requested.
    report = migrate.migrate(candidate)

    # Then migration holds before any candidate write.
    assert report.status == "hold"
    assert "symbolic link" in " ".join(report.blocked)
    assert not (candidate / ".trinity").exists()


def test_explicit_trust_directory_overrides_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a governance-selected directory different from the environment fallback.
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    governance = tmp_path / "selected"
    governance.mkdir()
    policy = governance / "policy.json"
    original = b'{"schema":"trinity.release-policy/v2"}\n'
    policy.write_bytes(original)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TRINITY_RELEASE_TRUST_DIR", "./absent")

    # When the operator supplies the same explicit selector as release.py.
    report = migrate.migrate(candidate, trust_dir="./selected", dry_run=True)

    # Then only the selected policy is reported and it remains untouched.
    assert report.status == "hold" and not report.blocked
    assert "./selected/policy.json" in report.needs_revalidation[0]
    assert policy.read_bytes() == original


def project_v1() -> bytes:
    return (
        json.dumps(
            {
                "schema_version": migrate.PROJECT_V1,
                "paths": {
                    key: value.removeprefix("./") for key, value in migrate.PROJECT_PATHS.items()
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()


def legacy_manifest() -> bytes:
    return b"""schema_version = "1.0"

[task]
uuid_v5 = "11111111-2222-4333-8444-555555555555"
authors = [{ email = "author@example.test" }]

[metadata]
harbor_version = "0.20.0"

[agent]
network_mode = "none"
"""


def current_manifest() -> bytes:
    return b"""schema_version = "1.4"

[task]
name = "example/task"
version = "1.0.0"
uuid_v5 = "11111111-2222-4333-8444-555555555555"
authors = [{ name = "author", email = "author@example.test" }]
"""


def write_manifest(root: Path, content: bytes) -> Path:
    path = root / "samples" / UUID / "task.toml"
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    return path


def write_legacy_queue(root: Path) -> tuple[Path, str]:
    bundle = root / "samples" / UUID
    digest = migrate.legacy_bundle_digest(bundle)
    return write_queue(root, digest), digest


def write_queue(root: Path, digest: str) -> Path:
    entry: dict[str, object] = {
        "seq": 1,
        "uuid": UUID,
        "bundle_digest": digest,
        "sealed_at": "2026-09-16T12:00:00Z",
        "producer_run_id": "forge-1",
        "prev_hash": "0" * 64,
    }
    entry["entry_hash"] = migrate._chain_digest(entry)
    path = root / ".podium" / "queue.jsonl"
    path.parent.mkdir()
    path.write_text(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    return path


def read_journal(root: Path) -> migrate.Journal:
    return cast(
        migrate.Journal,
        json.loads((root / ".trinity" / "migrations" / "state.json").read_text()),
    )


def write_verdict(root: Path, digest: str) -> Path:
    path = root / ".audit" / "verdicts" / f"{UUID}.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"uuid": UUID, "bundle_digest": digest, "outcome": "retained"}))
    return path


def write_progress_cache(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(LEGACY_PROGRESS)
    return path


def backup_path(root: Path, data: bytes) -> Path:
    return root / ".trinity" / "migrations" / "backups" / hashlib.sha256(data).hexdigest()


def test_manifest_paths_include_staging(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, legacy_manifest())
    (tmp_path / "samples").rename(tmp_path / "staging")
    staged = tmp_path / "staging" / UUID / manifest.name

    paths = migrate._manifest_paths(tmp_path)

    assert paths == [(f"./staging/{UUID}/task.toml", staged, UUID)]


def test_plan_queue_resolves_bundle_under_staging(tmp_path: Path) -> None:
    write_manifest(tmp_path, current_manifest())
    write_legacy_queue(tmp_path)
    (tmp_path / "samples").rename(tmp_path / "staging")

    write, blocked, revalidate = migrate._plan_queue(tmp_path, [])

    assert blocked == [] and revalidate == []
    assert write is not None
    assert json.loads(write.after)["bundle_digest"] == manifest_digest(
        tree_manifest(tmp_path / "staging" / UUID)
    )


@pytest.mark.parametrize(
    "roots", [("staging", "samples"), ("staging", "delivery"), ("samples", "delivery")]
)
def test_plan_queue_refuses_bundle_under_two_roots(tmp_path: Path, roots: tuple[str, str]) -> None:
    for lane in roots:
        bundle = tmp_path / lane / UUID
        bundle.mkdir(parents=True)
        (bundle / "task.toml").write_bytes(current_manifest())
    write_queue(tmp_path, manifest_digest(tree_manifest(bundle)))

    with pytest.raises(migrate.MigrationError) as raised:
        migrate._plan_queue(tmp_path, [])

    assert str(raised.value) == f"queue record {UUID} resolves under more than one root"


def test_plan_queue_skips_absent_retained_record(tmp_path: Path) -> None:
    write_queue(tmp_path, "a" * 64)
    write_verdict(tmp_path, "a" * 64)

    result = migrate._plan_queue(tmp_path, [])

    assert result == (None, [], [])


@pytest.mark.parametrize(
    "verdict_bytes",
    [
        None,
        b"not-json",
        b"\xff",
        b"[]",
        b'{"outcome":"retained"}',
        json.dumps({"uuid": UUID, "bundle_digest": "a" * 64}).encode(),
        json.dumps({"uuid": UUID, "bundle_digest": "a" * 64, "outcome": "clean"}).encode(),
        json.dumps({"uuid": UUID, "bundle_digest": "a" * 64, "outcome": "unknown"}).encode(),
        json.dumps({"uuid": "wrong", "bundle_digest": "a" * 64, "outcome": "retained"}).encode(),
        json.dumps({"uuid": UUID, "bundle_digest": "A" * 64, "outcome": "retained"}).encode(),
        json.dumps({"uuid": UUID, "bundle_digest": "a" * 63, "outcome": "retained"}).encode(),
        json.dumps({"uuid": UUID, "bundle_digest": 12, "outcome": "retained"}).encode(),
        json.dumps({"uuid": UUID, "bundle_digest": "a" * 64, "outcome": ["retained"]}).encode(),
        json.dumps(
            {"uuid": UUID, "bundle_digest": "a" * 64, "outcome": "retained", "extra": "x"}
        ).encode(),
    ],
)
def test_plan_queue_refuses_absent_record_without_retained_verdict(
    tmp_path: Path, verdict_bytes: bytes | None
) -> None:
    write_queue(tmp_path, "a" * 64)
    if verdict_bytes is not None:
        write_verdict(tmp_path, "a" * 64).write_bytes(verdict_bytes)

    with pytest.raises(migrate.MigrationError) as raised:
        migrate._plan_queue(tmp_path, [])

    assert str(raised.value) == f"queue record {UUID} resolves under no root"


@pytest.mark.parametrize("kind", ["file", "dangling-link", "live-link"])
@pytest.mark.parametrize("lane", ["staging", "samples", "delivery"])
def test_plan_queue_refuses_unsafe_object_even_with_retained_verdict(
    tmp_path: Path, kind: str, lane: str
) -> None:
    write_queue(tmp_path, "a" * 64)
    write_verdict(tmp_path, "a" * 64)
    path = tmp_path / lane / UUID
    path.parent.mkdir()
    if kind == "file":
        path.write_text("unsafe")
    else:
        target = tmp_path / "target"
        if kind == "live-link":
            target.mkdir()
        path.symlink_to(target, target_is_directory=True)

    with pytest.raises(migrate.MigrationError) as raised:
        migrate._plan_queue(tmp_path, [])

    assert str(raised.value) == f"queue record {UUID} has an unsafe object at ./{lane}/{UUID}"


def test_plan_queue_refuses_stale_retained_verdict(tmp_path: Path) -> None:
    write_queue(tmp_path, "b" * 64)
    write_verdict(tmp_path, "a" * 64)

    with pytest.raises(migrate.MigrationError) as raised:
        migrate._plan_queue(tmp_path, [])

    assert str(raised.value) == f"queue record {UUID} resolves under no root"


def test_plan_queue_checks_present_retained_bundle_bytes(tmp_path: Path) -> None:
    write_manifest(tmp_path, current_manifest())
    write_queue(tmp_path, "a" * 64)
    write_verdict(tmp_path, "a" * 64)
    (tmp_path / "samples").rename(tmp_path / "staging")

    write, blocked, revalidate = migrate._plan_queue(tmp_path, [])

    assert write is None and revalidate == []
    assert blocked == [
        f"{migrate.PIPELINE_QUEUE} uuid {UUID}: seal matches neither legacy nor current identity; "
        "restore bytes or reseal"
    ]


def test_missing_manifest_bootstraps_and_repeated_apply_is_noop(tmp_path: Path) -> None:
    first = migrate.migrate(tmp_path)
    assert first.status == "complete"
    project = json.loads((tmp_path / ".trinity" / "project.json").read_text())
    assert project == {"schema_version": migrate.PROJECT_V2, "paths": migrate.PROJECT_PATHS}
    journal = read_journal(tmp_path)
    assert set(journal) == migrate.JOURNAL_FIELDS
    assert journal["version"] == migrate.JOURNAL_VERSION
    assert journal["status"] == "complete"
    assert all(str(step["path"]).startswith("./") for step in journal["steps"])
    assert migrate.migrate(tmp_path).status == "noop"


def test_v1_bare_paths_upgrade_with_exact_immutable_backup(tmp_path: Path) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    original = project_v1()
    project.write_bytes(original)
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    assert json.loads(project.read_text())["schema_version"] == migrate.PROJECT_V2
    journal = read_journal(tmp_path)
    step = next(item for item in journal["steps"] if item["path"] == migrate.PROJECT_FILE)
    backup = tmp_path / str(step["backup"]).removeprefix("./")
    assert backup.read_bytes() == original
    assert backup.stat().st_mode & 0o222 == 0
    assert step["before_sha256"] == hashlib.sha256(original).hexdigest()
    assert step["after_sha256"] == hashlib.sha256(project.read_bytes()).hexdigest()


def test_dry_run_plans_without_writing_any_byte(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, legacy_manifest())
    before = manifest.read_bytes()
    report = migrate.migrate(tmp_path, dry_run=True)
    assert report.status == "planned"
    assert migrate.PROJECT_FILE in report.changed
    assert manifest.read_bytes() == before
    assert not (tmp_path / ".trinity").exists()


def test_harbor_legacy_discriminators_use_known_migration_and_require_revalidation(
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path, legacy_manifest())
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    text = manifest.read_text()
    assert 'schema_version = "1.4"' in text
    assert 'network_mode = "no-network"' in text
    assert "harbor_version" not in text
    assert '{ name = "author", email = "author@example.test" }' in text
    journal = read_journal(tmp_path)
    step = next(item for item in journal["steps"] if item["path"].endswith("task.toml"))
    assert step["status"] == "needs_revalidation"
    assert any(path.endswith("task.toml") for path in report.changed)


def test_unknown_project_or_harbor_version_holds_without_partial_write(tmp_path: Path) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    project.write_text(
        json.dumps({"schema_version": "trinity.project/v99", "paths": migrate.PROJECT_PATHS})
    )
    manifest = write_manifest(tmp_path, legacy_manifest().replace(b'"1.0"', b'"1.2"', 1))
    project_before = project.read_bytes()
    manifest_before = manifest.read_bytes()
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "unsupported" in " ".join(report.blocked)
    assert "outside the supported" in " ".join(report.blocked) or "ambiguous" in " ".join(
        report.blocked
    )
    assert project.read_bytes() == project_before
    assert manifest.read_bytes() == manifest_before
    assert not (tmp_path / ".trinity" / "migrations").exists()


def test_unknown_journal_version_holds_closed(tmp_path: Path) -> None:
    state = tmp_path / ".trinity" / "migrations" / "state.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps(
            {
                "version": 99,
                "steps": [],
                "before_sha256": hashlib.sha256(b"").hexdigest(),
                "after_sha256": hashlib.sha256(b"").hexdigest(),
                "backups": [],
                "status": "applying",
            }
        )
    )
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "version 99" in report.blocked[0]
    assert not (tmp_path / ".trinity" / "project.json").exists()


def test_tampered_backup_and_target_are_refused(tmp_path: Path) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    project.write_bytes(project_v1())
    assert migrate.migrate(tmp_path).status == "complete"
    journal = read_journal(tmp_path)
    step = next(item for item in journal["steps"] if item["backup"] is not None)
    backup = tmp_path / str(step["backup"]).removeprefix("./")
    backup.chmod(0o600)
    backup.write_text("tampered")
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "tampered" in report.blocked[0]

    backup.write_bytes(project_v1())
    backup.chmod(migrate.BACKUP_MODE)
    project.write_text("changed outside migration")
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "neither journal before nor after" in report.blocked[0]


def test_symlink_and_traversal_are_refused(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "samples").symlink_to(outside, target_is_directory=True)
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "symbolic link" in report.blocked[0]

    with pytest.raises(migrate.MigrationError, match="traversal"):
        migrate._path(tmp_path, "./../outside")
    with pytest.raises(migrate.MigrationError, match="canonical"):
        migrate._path(tmp_path, "/absolute")


def test_failure_rolls_back_and_retry_resumes_from_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = write_manifest(tmp_path, legacy_manifest())
    original = manifest.read_bytes()
    real_replace = migrate._atomic_replace
    failed = False

    def fail_manifest(path: Path, data: bytes, mode: int = 0o600) -> None:
        nonlocal failed
        if path == manifest and not failed:
            failed = True
            raise OSError("injected write failure")
        real_replace(path, data, mode)

    monkeypatch.setattr(migrate, "_atomic_replace", fail_manifest)
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert not (tmp_path / ".trinity" / "project.json").exists()
    assert manifest.read_bytes() == original
    assert read_journal(tmp_path)["status"] == "hold"

    monkeypatch.setattr(migrate, "_atomic_replace", real_replace)
    retried = migrate.migrate(tmp_path)
    assert retried.status == "complete"
    assert (tmp_path / ".trinity" / "project.json").is_file()
    assert b'network_mode = "no-network"' in manifest.read_bytes()


def test_legacy_queue_preserves_ids_and_pending_progress_without_faking_verdict(
    tmp_path: Path,
) -> None:
    write_manifest(tmp_path, current_manifest())
    queue, legacy_digest = write_legacy_queue(tmp_path)
    verdict = tmp_path / ".audit" / "verdicts" / f"{UUID}.json"
    verdict.parent.mkdir(parents=True)
    verdict_bytes = json.dumps({"uuid": UUID, "bundle_digest": legacy_digest}).encode()
    verdict.write_bytes(verdict_bytes)
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    entry = json.loads(queue.read_text())
    assert entry["uuid"] == UUID
    assert entry["producer_run_id"] == "forge-1"
    assert entry["bundle_digest"] != legacy_digest
    assert entry["entry_hash"] == migrate._chain_digest(entry)
    assert verdict.read_bytes() == verdict_bytes
    assert report.needs_revalidation and UUID in report.needs_revalidation[0]
    sidecar = json.loads(
        (tmp_path / ".trinity" / "migrations" / "needs-revalidation.json").read_text()
    )
    assert UUID in sidecar["records"][0]


def test_unproven_legacy_queue_digest_holds_and_preserves_queue(tmp_path: Path) -> None:
    write_manifest(tmp_path, current_manifest())
    queue, _ = write_legacy_queue(tmp_path)
    entry = json.loads(queue.read_text())
    entry["bundle_digest"] = "f" * 64
    entry["entry_hash"] = migrate._chain_digest(entry)
    queue.write_text(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    before = queue.read_bytes()
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "neither legacy nor current" in " ".join(report.blocked)
    assert queue.read_bytes() == before
    assert not (tmp_path / ".trinity").exists()


@pytest.mark.parametrize("multiple_steps", [False, True], ids=["one-step", "multi-step"])
@pytest.mark.parametrize("crash_point", ["crash0", "after-backup", "after-write", "before-journal"])
def test_process_interruption_resumes_exact_original_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    multiple_steps: bool,
    crash_point: str,
) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    project.write_bytes(project_v1())
    manifest = write_manifest(tmp_path, legacy_manifest()) if multiple_steps else None
    original_project = project.read_bytes()
    real_backup = migrate._create_backup
    real_replace = migrate._atomic_replace
    real_journal = migrate._write_journal
    interrupted = False

    def crash_backup(root: Path, step: migrate.JournalStep, before: bytes) -> None:
        nonlocal interrupted
        real_backup(root, step, before)
        if not interrupted and step["path"] == migrate.PROJECT_FILE:
            interrupted = True
            raise SystemExit("after backup")

    def crash_replace(path: Path, data: bytes, mode: int = 0o600) -> None:
        nonlocal interrupted
        real_replace(path, data, mode)
        if not interrupted and path == project:
            interrupted = True
            raise SystemExit("after write")

    def crash_journal(root: Path, journal: migrate.Journal) -> None:
        nonlocal interrupted
        if crash_point == "crash0" and not interrupted:
            interrupted = True
            raise SystemExit("before initial journal")
        if (
            crash_point == "before-journal"
            and not interrupted
            and project.is_file()
            and project.read_bytes() == migrate._project_document()
            and any(step["path"] == migrate.PROJECT_FILE for step in journal["steps"])
        ):
            interrupted = True
            raise SystemExit("after write before completed step journal")
        real_journal(root, journal)

    if crash_point == "after-backup":
        monkeypatch.setattr(migrate, "_create_backup", crash_backup)
    elif crash_point == "after-write":
        monkeypatch.setattr(migrate, "_atomic_replace", crash_replace)
    else:
        monkeypatch.setattr(migrate, "_write_journal", crash_journal)

    with pytest.raises(SystemExit):
        migrate.migrate(tmp_path)
    assert not (tmp_path / ".trinity" / "migrations" / "migrate.lock").exists()

    monkeypatch.setattr(migrate, "_create_backup", real_backup)
    monkeypatch.setattr(migrate, "_atomic_replace", real_replace)
    monkeypatch.setattr(migrate, "_write_journal", real_journal)
    resumed = migrate.migrate(tmp_path)
    assert resumed.status == "complete"
    assert json.loads(project.read_text())["schema_version"] == migrate.PROJECT_V2
    if crash_point != "crash0":
        journal = read_journal(tmp_path)
        project_step = next(
            step for step in journal["steps"] if step["path"] == migrate.PROJECT_FILE
        )
        assert (
            tmp_path / str(project_step["backup"]).removeprefix("./")
        ).read_bytes() == original_project
    if manifest is not None:
        assert 'schema_version = "1.4"' in manifest.read_text()


def test_self_consistent_journal_cannot_redirect_known_step_to_authority_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    project.write_bytes(project_v1())
    real_backup = migrate._create_backup

    def interrupt(root: Path, step: migrate.JournalStep, before: bytes) -> None:
        real_backup(root, step, before)
        raise SystemExit("leave incomplete journal")

    monkeypatch.setattr(migrate, "_create_backup", interrupt)
    with pytest.raises(SystemExit):
        migrate.migrate(tmp_path)
    marker = tmp_path / ".memory" / "roots.yaml"
    marker.parent.mkdir()
    marker.write_bytes(project_v1())
    marker_before = marker.read_bytes()
    state_path = tmp_path / ".trinity" / "migrations" / "state.json"
    state = cast(migrate.Journal, json.loads(state_path.read_text()))
    step = state["steps"][0]
    step["path"] = "./.memory/roots.yaml"
    step["before_mode"] = marker.stat().st_mode & 0o777
    state["before_sha256"] = migrate._plan_digest(state["steps"], "before_sha256")
    state["after_sha256"] = migrate._plan_digest(state["steps"], "after_sha256")
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(migrate, "_create_backup", real_backup)

    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "authority or signed path" in report.blocked[0]
    assert marker.read_bytes() == marker_before


def test_self_consistent_journal_cannot_change_bound_mode_or_revalidation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    project.write_bytes(project_v1())
    project.chmod(0o644)
    original = project.read_bytes()
    real_backup = migrate._create_backup

    def interrupt(root: Path, step: migrate.JournalStep, before: bytes) -> None:
        real_backup(root, step, before)
        raise SystemExit("leave incomplete journal")

    monkeypatch.setattr(migrate, "_create_backup", interrupt)
    with pytest.raises(SystemExit):
        migrate.migrate(tmp_path)
    state_path = tmp_path / ".trinity" / "migrations" / "state.json"
    state = cast(migrate.Journal, json.loads(state_path.read_text()))
    state["steps"][0]["after_mode"] = 0o600
    state["steps"][0]["needs_revalidation"] = True
    state["before_sha256"] = migrate._plan_digest(state["steps"], "before_sha256")
    state["after_sha256"] = migrate._plan_digest(state["steps"], "after_sha256")
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(migrate, "_create_backup", real_backup)

    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "exactly bound" in report.blocked[0]
    assert project.read_bytes() == original
    assert project.stat().st_mode & 0o777 == 0o644


def test_harbor_change_reseals_queue_that_used_current_pre_migration_identity(
    tmp_path: Path,
) -> None:
    manifest = write_manifest(tmp_path, legacy_manifest())
    manifest.chmod(0o744)
    bundle = manifest.parent
    before_digest = manifest_digest(tree_manifest(bundle))
    queue = write_queue(tmp_path, before_digest)
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    entry = json.loads(queue.read_text())
    assert entry["bundle_digest"] != before_digest
    assert entry["bundle_digest"] == manifest_digest(tree_manifest(bundle))
    assert manifest.stat().st_mode & 0o777 == 0o744


def test_modes_are_journaled_preserved_and_restored_on_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    project.write_bytes(project_v1())
    project.chmod(0o640)
    manifest = write_manifest(tmp_path, legacy_manifest())
    manifest.chmod(0o740)
    real_replace = migrate._atomic_replace
    failed = False

    def fail_manifest(path: Path, data: bytes, mode: int = 0o600) -> None:
        nonlocal failed
        if path == manifest and not failed:
            failed = True
            raise OSError("intentional rollback")
        real_replace(path, data, mode)

    monkeypatch.setattr(migrate, "_atomic_replace", fail_manifest)
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert project.read_bytes() == project_v1()
    assert project.stat().st_mode & 0o777 == 0o640
    assert manifest.read_bytes() == legacy_manifest()
    assert manifest.stat().st_mode & 0o777 == 0o740
    journal = read_journal(tmp_path)
    modes = {step["path"]: (step["before_mode"], step["after_mode"]) for step in journal["steps"]}
    assert modes[migrate.PROJECT_FILE] == (0o640, 0o640)
    assert modes[f"./samples/{UUID}/task.toml"] == (0o740, 0o740)


def test_insecure_regular_file_mode_holds_without_escalation(tmp_path: Path) -> None:
    project = tmp_path / ".trinity" / "project.json"
    project.parent.mkdir()
    project.write_bytes(project_v1())
    project.chmod(0o666)
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert "unsafe regular-file mode" in report.blocked[0]
    assert project.stat().st_mode & 0o777 == 0o666


def test_signed_v2_v3_and_key_files_remain_byte_exact(tmp_path: Path) -> None:
    signed = {
        tmp_path / ".seed" / "disposition.json": b'{"schema":"trinity.release-disposition/v2"}',
        tmp_path / ".seed" / "disposition.json.dsse": b"v2-envelope",
        tmp_path
        / ".audit"
        / "disposition.json": b'{"schema":"trinity.group-release-disposition/v3"}',
        tmp_path / ".audit" / "disposition.json.dsse": b"v3-envelope",
        tmp_path / ".seed" / "software-private.key": b"private bytes",
    }
    for path, data in signed.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    assert migrate.migrate(tmp_path).status == "complete"
    assert all(path.read_bytes() == data for path, data in signed.items())


def test_unknown_legacy_signature_is_preserved_while_harbor_requires_revalidation(
    tmp_path: Path,
) -> None:
    write_manifest(tmp_path, legacy_manifest())
    signature = tmp_path / ".audit" / "legacy-signature.dsse"
    signature.parent.mkdir(parents=True)
    original = b'{"payloadType":"unknown.legacy/v0","signatures":["opaque"]}'
    signature.write_bytes(original)
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    assert report.needs_revalidation
    assert signature.read_bytes() == original


def test_cli_rejects_noncanonical_root_and_dry_run_is_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(tmp_path)
    assert migrate.main(["migrate.py", "project"]) == 2
    assert migrate.main(["migrate.py", "./project", "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "planned"
    assert not (project / ".trinity").exists()


def test_legacy_harness_progress_is_backed_up_and_left_in_place(tmp_path: Path) -> None:
    cache = write_progress_cache(tmp_path / ".memory" / "progress.yaml")
    mode = cache.stat().st_mode & 0o777
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    backup = backup_path(tmp_path, LEGACY_PROGRESS)
    assert backup.read_bytes() == LEGACY_PROGRESS
    assert backup.stat().st_mode & 0o777 == migrate.BACKUP_MODE
    assert cache.read_bytes() == LEGACY_PROGRESS
    assert cache.stat().st_mode & 0o777 == mode
    assert "./.memory/progress.yaml" not in report.changed


@pytest.mark.parametrize("harness", [".memory", ".seed", ".audit"])
def test_legacy_harness_progress_emits_a_revalidation_row(tmp_path: Path, harness: str) -> None:
    write_progress_cache(tmp_path / harness / "progress.yaml")
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    row = next(item for item in report.needs_revalidation if f"./{harness}/progress.yaml" in item)
    assert "progress.py rebuild" in row


def test_run_scoped_progress_is_never_migrated(tmp_path: Path) -> None:
    cache = write_progress_cache(tmp_path / ".memory" / "runs" / RUN_ID / "progress.yaml")
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    assert not any("progress.yaml" in item for item in report.needs_revalidation)
    assert not backup_path(tmp_path, LEGACY_PROGRESS).exists()
    assert cache.read_bytes() == LEGACY_PROGRESS


def test_progress_migration_is_idempotent(tmp_path: Path) -> None:
    write_progress_cache(tmp_path / ".audit" / "progress.yaml")
    first = migrate.migrate(tmp_path)
    backups = tmp_path / ".trinity" / "migrations" / "backups"
    stored = sorted(path.name for path in backups.iterdir())
    assert stored == [hashlib.sha256(LEGACY_PROGRESS).hexdigest()]
    second = migrate.migrate(tmp_path)
    assert second.status == "noop"
    assert sorted(path.name for path in backups.iterdir()) == stored
    assert [item for item in second.needs_revalidation if "progress.yaml" in item] == [
        item for item in first.needs_revalidation if "progress.yaml" in item
    ]
    assert len([item for item in second.needs_revalidation if "progress.yaml" in item]) == 1


def test_migration_never_deletes_the_legacy_cache(tmp_path: Path) -> None:
    cache = write_progress_cache(tmp_path / ".seed" / "progress.yaml")
    assert migrate.migrate(tmp_path).status == "complete"
    assert migrate.migrate(tmp_path, dry_run=True).status == "noop"
    assert cache.is_file()
    assert cache.read_bytes() == LEGACY_PROGRESS
    journal = read_journal(tmp_path)
    assert all(step["path"] != "./.seed/progress.yaml" for step in journal["steps"])
