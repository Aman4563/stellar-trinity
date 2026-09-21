"""Both halves of the first-principal enrolment door in tools/enrol.py."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest
from tools import enrol
from tools.attest.canonical import canonicalize
from tools.feedback import integrity
from tools.feedback import main as feedback_main

from tests.parent_fixtures import write_resume_parent

AT: Final = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
STAMP: Final = "2026-09-21T12:00:00Z"
SIGNED: Final = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs ssh-keygen")


def keypair(directory: Path) -> tuple[Path, Path]:
    key = directory / "ada_ed25519"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "ada", "-f", str(key)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return key, key.with_suffix(".pub")


@pytest.fixture
def parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "parent"
    write_resume_parent(root, "ENGRAM", "engram-ada-1")
    (root / "r.json").write_bytes(canonicalize([{"hypothesis": "resume", "confidence": "high"}]))
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"hello"), encoding="utf-8"))
    return root


def feedback(command: str, *options: str) -> int:
    return feedback_main(
        [
            "feedback.py",
            command,
            "./",
            "--instrument",
            "ENGRAM",
            "--run",
            "engram-ada-1",
            "--json",
            *options,
        ]
    )


@SIGNED
def test_enrolled_root_lets_the_first_checkpoint_sign_and_walk(parent: Path) -> None:
    # Given a parent with no trust root and one human with a software key.
    private, public = keypair(parent.parent)
    assert not (parent / ".memory" / "roots.yaml").exists()
    # When the human is enrolled.
    written = enrol.enrol(parent, principal="ada", public_key=public, at=AT)
    # Then the three surfaces exist, the root is closed, and the gate's own parser reads it.
    assert [path.name for path in written] == [
        "roots.yaml",
        "allowed_signers",
        "trusted-root-version",
    ]
    root = json.loads((parent / ".memory" / "roots.yaml").read_bytes())
    assert root["version"] == 1
    assert {role["name"] for role in root["roles"]} == set(enrol.ROLES)
    assert (parent / ".memory" / "trusted-root-version").read_text() == "1\n"
    signers = (parent / ".memory" / "allowed_signers").read_text()
    assert signers.startswith('ada namespaces="trinity.attestation.v1,git" ssh-ed25519 ')
    # And the real feedback door signs seq 1 with that root and the verifier walks it clean.
    shutil.copyfile(private, parent / "key")
    (parent / "key").chmod(0o600)
    assert (
        feedback(
            "append",
            "--principal",
            "ada",
            "--kind",
            "contract_paste",
            "--github-id",
            "ada",
            "--reasoning-file",
            "./r.json",
            "--received-at",
            STAMP,
        )
        == 0
    )
    assert feedback("checkpoint", "--principal", "ada", "--key", "./key", "--at", STAMP) == 0
    assert integrity.check_feedback_chain(str(parent), evaluation_time=AT) == []


@SIGNED
def test_a_second_enrolment_is_refused_and_leaves_the_root_alone(parent: Path) -> None:
    _, public = keypair(parent.parent)
    enrol.enrol(parent, principal="ada", public_key=public, at=AT)
    before = (parent / ".memory" / "roots.yaml").read_bytes()
    with pytest.raises(enrol.EnrolError) as refused:
        enrol.enrol(parent, principal="bob", public_key=public, at=AT)
    assert refused.value.code == enrol.ALREADY_ENROLLED
    assert (parent / ".memory" / "roots.yaml").read_bytes() == before


@SIGNED
def test_one_surface_already_present_is_enough_to_refuse(parent: Path) -> None:
    _, public = keypair(parent.parent)
    (parent / ".memory" / "trusted-root-version").write_text("9\n")
    with pytest.raises(enrol.EnrolError) as refused:
        enrol.enrol(parent, principal="ada", public_key=public, at=AT)
    assert refused.value.code == enrol.ALREADY_ENROLLED
    assert not (parent / ".memory" / "roots.yaml").exists()


def test_private_key_offered_as_public_is_refused(parent: Path) -> None:
    offered = parent.parent / "not-public"
    offered.write_text(
        "-----BEGIN OPENSSH PRIVATE KEY-----\nAAAA\n-----END OPENSSH PRIVATE KEY-----\n"
    )
    with pytest.raises(enrol.EnrolError) as refused:
        enrol.enrol(parent, principal="ada", public_key=offered, at=AT)
    assert refused.value.code == enrol.KEY_INVALID
    assert not any((parent / surface).exists() for surface in enrol.SURFACES)


def test_security_key_is_refused_under_the_software_only_doctrine(parent: Path) -> None:
    offered = parent.parent / "sk.pub"
    offered.write_text("sk-ssh-ed25519@openssh.com AAAAGnNrLXNzaC1lZDI1NTE5QG9wZW5zc2guY29t ada\n")
    with pytest.raises(enrol.EnrolError) as refused:
        enrol.enrol(parent, principal="ada", public_key=offered, at=AT)
    assert refused.value.code == enrol.KEY_INVALID


def test_malformed_principal_and_past_expiry_are_refused(parent: Path) -> None:
    offered = parent.parent / "ok.pub"
    offered.write_text(
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ada\n"
    )
    with pytest.raises(enrol.EnrolError) as principal:
        enrol.enrol(parent, principal="ada bad", public_key=offered, at=AT)
    assert principal.value.code == enrol.PRINCIPAL_INVALID
    with pytest.raises(enrol.EnrolError) as expiry:
        enrol.enrol(parent, principal="ada", public_key=offered, at=AT, expires=AT)
    assert expiry.value.code == enrol.EXPIRY_INVALID
    assert not any((parent / surface).exists() for surface in enrol.SURFACES)


@SIGNED
def test_cli_reports_the_paths_to_commit(parent: Path, capsys: pytest.CaptureFixture[str]) -> None:
    keypair(parent)
    code = enrol.main(
        ["enrol.py", "./", "--principal", "ada", "--public-key", "./ada_ed25519.pub", "--json"]
    )
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {
        "principal": "ada",
        "written": [
            "./.memory/roots.yaml",
            "./.memory/allowed_signers",
            "./.memory/trusted-root-version",
        ],
    }
    assert (
        enrol.main(["enrol.py", "./", "--principal", "ada", "--public-key", "./ada_ed25519.pub"])
        == 3
    )
