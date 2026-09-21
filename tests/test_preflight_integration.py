from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from tools import preflight

from tools import feedback, gate  # isort: skip
from tools.preflight_receipt import invoke_json

from tests.parent_fixtures import git, write_feedback_trust, write_resume_parent

SCRIPT = Path(__file__).resolve().parents[1] / "tools/preflight.py"


def test_pre_push_invocation_is_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "parent"
    write_resume_parent(root, "CRUCIBLE", "crucible-ada-1")
    git(["init", "-q"], cwd=root)
    shutil.copytree(
        SCRIPT.parent, root / "trinity/tools", ignore=shutil.ignore_patterns("__pycache__")
    )
    hook = SCRIPT.parent.parent / "templates/pre-push"
    command = (
        "python3 trinity/tools/gate.py ./ --instrument CRUCIBLE --moment report --check --json"
    )
    assert command + " > .sentinel/pre-push.json 2>.sentinel/pre-push.err" in hook.read_text()
    result = subprocess.run(
        command.split(), cwd=root, capture_output=True, text=True, check=False, timeout=60
    )
    assert result.returncode == 3
    assert set(json.loads(result.stdout)) == {
        "instrument",
        "moment",
        "run_id",
        "ceiling",
        "codes",
        "sabotage_recorded",
        "receipt",
        "record",
        "install",
        "migration",
        "findings",
    }


def test_final_disposition_fields_are_frozen() -> None:
    assert {
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
    } == gate.FINAL_DISPOSITION_FIELDS


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs ssh-keygen")
def test_signed_feedback_is_verified_before_qualification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "parent"
    write_resume_parent(root, "FORGE", "forge-ada-1")
    git(["init", "-q"], cwd=root)
    key = write_feedback_trust(root)
    shutil.copyfile(key, root / "key")
    (root / "key").chmod(0o600)
    (root / "reason.json").write_text('[{"hypothesis":"resume","confidence":"high"}]')
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"resume")))
    common = ["./", "--instrument", "FORGE", "--run", "forge-ada-1", "--json"]
    assert (
        invoke_json(
            feedback.main,
            [
                "feedback.py",
                "append",
                *common,
                "--principal",
                "ada",
                "--kind",
                "contract_paste",
                "--github-id",
                "ada",
                "--reasoning-file",
                "./reason.json",
            ],
        ).status
        == 0
    )
    assert (
        invoke_json(
            feedback.main,
            [
                "feedback.py",
                "checkpoint",
                *common,
                "--principal",
                "ada",
                "--key",
                "./key",
            ],
        ).status
        == 0
    )
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            *common,
            "--principal",
            "ada",
            "--moment",
            "report",
            "--check",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    receipt = json.loads(result.stdout)
    assert result.returncode == 3
    assert receipt["feedback"] == {
        "chain_walk": "ran:pass",
        "head_seq": 1,
        "head_entry_hash": receipt["feedback"]["head_entry_hash"],
        "checkpoint": "signed",
        "pending_records": 0,
    }
    assert receipt["never_skip"]["freshness"] == "ran:fail"


@pytest.mark.parametrize("options", [[], ["--at", "invalid"]])
def test_cli_usage_has_exit_one(tmp_path: Path, options: list[str]) -> None:
    argv = [sys.executable, str(SCRIPT)]
    if options:
        argv += [
            "./",
            "--instrument",
            "FORGE",
            "--run",
            "forge-ada-1",
            "--principal",
            "ada",
            "--moment",
            "report",
            *options,
        ]
    result = subprocess.run(argv, cwd=tmp_path, capture_output=True, check=False, timeout=30)
    assert result.returncode == 1


def test_receipt_symlink_is_refused_before_gate_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "parent"
    directory = write_resume_parent(root, "FORGE", "forge-ada-1")
    outside = tmp_path / "outside"
    outside.mkdir()
    (directory / "gate-receipts").symlink_to(outside, target_is_directory=True)
    monkeypatch.chdir(root)
    status = preflight.main(
        [
            "preflight.py",
            "./",
            "--instrument",
            "FORGE",
            "--run",
            "forge-ada-1",
            "--principal",
            "ada",
            "--moment",
            "report",
        ]
    )
    assert status == 3
    assert list(outside.iterdir()) == []
