"""RED-to-GREEN proof that ``tracker_fixtures.parent_fixture`` builds every surface."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from tests import parent_fixtures
from tests.tracker_fixtures import BASE_INSTANT, TRACKER_SCHEMA, parent_fixture


def test_parent_fixture_builds_every_surface(tmp_path: Path) -> None:
    fixture = parent_fixture(tmp_path / "parent")
    root = fixture.root

    assert len(fixture.runs) == 3
    for run in fixture.runs:
        assert (run.directory / "run.json").is_file()
        assert (run.directory / "report.md").is_file()
        assert (run.directory / "progress.yaml").is_file()
        assert run.card_path is not None
        assert run.card_path.is_file()
        card = json.loads(run.card_path.read_text(encoding="utf-8"))
        assert card["schema"] == TRACKER_SCHEMA
        assert card["run_id"] == run.run_id
        report_digest = hashlib.sha256((run.directory / "report.md").read_bytes()).hexdigest()
        assert card["sources"]["report.md"] == report_digest

    forge_run_id = next(run.run_id for run in fixture.runs if run.instrument == "FORGE")
    assert (root / ".podium" / "queue" / f"{forge_run_id}.jsonl").is_file()

    assert fixture.sample_uuid is not None
    assert (root / "samples" / fixture.sample_uuid).is_dir()
    claims = list((root / ".audit" / "queue.claims" / fixture.sample_uuid).glob("*.json"))
    assert claims
    verdicts = list((root / ".audit" / "verdicts" / fixture.sample_uuid).glob("*.json"))
    assert verdicts
    assert (root / ".seed" / "lanes" / f"{fixture.sample_uuid}.yaml").is_file()

    assert fixture.staging_uuid is not None
    assert (root / "staging" / fixture.staging_uuid).is_dir()

    assert (root / ".memory" / "current.json").is_file()
    current = json.loads((root / ".memory" / "current.json").read_text(encoding="utf-8"))
    assert current["epoch"] == 1
    manifest_path = root / ".memory" / "epochs" / "1" / "manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    assert current["manifest_digest"] == manifest_digest
    assert manifest["schema"] == "trinity.memory-epoch/v1"

    assert (root / ".podium" / "cycles.yaml").is_file()
    assert (root / ".trial" / "gates.yaml").is_file()
    assert list((root / ".trial" / "approvals").iterdir())


def test_zero_runs_builds_only_the_harness_skeleton(tmp_path: Path) -> None:
    fixture = parent_fixture(tmp_path / "parent", zero_runs=True)

    assert fixture.runs == ()
    assert fixture.sample_uuid is None
    assert fixture.staging_uuid is None
    current_path = fixture.root / ".memory" / "current.json"
    assert current_path.is_file()
    current = json.loads(current_path.read_text(encoding="utf-8"))
    assert current == {"schema": "trinity.memory-current/v1", "epoch": 0}
    assert not (fixture.root / ".memory" / "epochs").exists()
    assert not list((fixture.root / ".seed").iterdir())
    assert not (fixture.root / ".podium" / "cycles.yaml").exists()


def test_late_run_precedes_every_other_run(tmp_path: Path) -> None:
    fixture = parent_fixture(tmp_path / "parent", late_run=True)

    assert len(fixture.runs) == 4
    earliest = min(fixture.runs, key=lambda run: run.started_at)
    assert earliest.run_id.endswith("-late-run")
    assert earliest.started_at < BASE_INSTANT


def test_malformed_card_writes_unparseable_bytes(tmp_path: Path) -> None:
    fixture = parent_fixture(tmp_path / "parent", malformed_card=True)

    last = fixture.runs[-1]
    assert last.card_path is not None
    assert last.closed_at is None
    raw = last.card_path.read_text(encoding="utf-8")
    assert raw == "{"


def test_graduated_anchor_is_resident_under_delivery(tmp_path: Path) -> None:
    fixture = parent_fixture(tmp_path / "parent", graduated_anchor=True)

    assert fixture.anchor_uuid is not None
    assert (fixture.root / "delivery" / fixture.anchor_uuid).is_dir()
    assert not (fixture.root / "staging" / fixture.anchor_uuid).exists()
    standing = (fixture.root / ".memory" / "anchor_standing.yaml").read_text(encoding="utf-8")
    assert f"{fixture.anchor_uuid}: ANCHORED" in standing


def test_write_resume_parent_opens_a_real_run(tmp_path: Path) -> None:
    root = tmp_path / "parent"

    run_directory = parent_fixtures.write_resume_parent(
        root, "ENGRAM", "engram-ada-resume-1", approved=True
    )

    assert run_directory == root / ".memory" / "runs" / "engram-ada-resume-1"
    marker = json.loads((run_directory / "run.json").read_text(encoding="utf-8"))
    assert marker["schema"] == "trinity.run/v1"
    assert marker["instrument"] == "ENGRAM"
    assert marker["run_id"] == "engram-ada-resume-1"
    assert marker["principal"] == "ada"
    scope = root / ".memory" / "scope.yaml"
    approval = root / ".memory" / "approval"
    expected = hashlib.sha256(scope.read_bytes()).hexdigest()
    assert approval.read_text(encoding="utf-8") == f"{expected}\n"
    capabilities = (root / ".memory" / "capabilities.yaml").read_text(encoding="utf-8")
    assert "  - id: autonomous_gates\n    state: declared\n" in capabilities
    assert "  - id: contamination\n    state: implemented\n" in capabilities


def test_write_resume_parent_without_approval_leaves_the_gate_open(tmp_path: Path) -> None:
    root = tmp_path / "parent"

    run_directory = parent_fixtures.write_resume_parent(root, "FORGE", "forge-ada-resume-1")

    assert run_directory == root / ".seed" / "runs" / "forge-ada-resume-1"
    assert (root / ".seed" / "contract.yaml").is_file()
    assert (root / ".seed" / "capabilities.yaml").is_file()
    assert not (root / ".seed" / "contract.approved").exists()


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen is unavailable")
def test_write_feedback_trust_binds_the_checkpointer_role(tmp_path: Path) -> None:
    root = tmp_path / "parent"
    parent_fixtures.write_resume_parent(root, "ENGRAM", "engram-ada-resume-1", approved=True)

    private_key = parent_fixtures.write_feedback_trust(root)

    assert private_key.is_file()
    assert not private_key.is_relative_to(root)
    document = json.loads((root / ".memory" / "roots.yaml").read_text(encoding="utf-8"))
    assert document == {
        "expires": "2030-01-01T00:00:00Z",
        "principals": [
            {"expires": "2029-01-01T00:00:00Z", "name": "ada", "roles": ["feedback_checkpointer"]}
        ],
        "revocations": [],
        "roles": [{"name": "feedback_checkpointer", "threshold": 1}],
        "version": 7,
    }
    public = Path(f"{private_key}.pub").read_text(encoding="utf-8").split()
    signers = (root / ".memory" / "allowed_signers").read_text(encoding="utf-8")
    assert signers == f'ada namespaces="trinity.attestation.v1" {public[0]} {public[1]}\n'
    assert (root / ".memory" / "trusted-root-version").read_text(encoding="utf-8") == "7\n"


def test_write_meter_export_reproduces_the_checked_in_sample(tmp_path: Path) -> None:
    path = parent_fixtures.write_meter_export(tmp_path, sessions=parent_fixtures.METER_SESSIONS)

    assert path.read_bytes() == parent_fixtures.METER_EXPORT.read_bytes()
    documents = json.loads(path.read_text(encoding="utf-8"))
    assert [document["info"].get("parentID") for document in documents] == [
        None,
        parent_fixtures.METER_SESSIONS[0][0],
        parent_fixtures.METER_SESSIONS[0][0],
    ]
    root_tokens = documents[0]["info"]["tokens"]
    assert sorted(root_tokens) == ["cache", "input", "output", "reasoning"]
    assert sorted(root_tokens["cache"]) == ["read", "write"]
    assert sorted(documents[0]["info"]["time"]) == ["created", "updated"]
    assert {message["info"]["sessionID"] for message in documents[1]["messages"]} == {
        parent_fixtures.METER_SESSIONS[1][0]
    }
