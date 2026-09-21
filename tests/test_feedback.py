from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

import pytest
from tools import runs, subject
from tools.attest.backend_ssh import SshKeygenBackend
from tools.attest.canonical import JSONValue, canonicalize, parse_json
from tools.feedback import integrity, main

from tests.parent_fixtures import write_feedback_trust, write_resume_parent

STAMP: Final = "2026-09-21T12:00:00Z"
NOW: Final = datetime.fromisoformat(STAMP)
SCRIPT: Final = Path(__file__).resolve().parents[1] / "tools/feedback.py"
SIGNED: Final = pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="needs ssh-keygen")


@dataclass(frozen=True, slots=True)
class Parent:
    root: Path
    directory: Path
    instrument: str
    run_id: str

    def call(self, command: str, *options: str) -> int:
        return main(
            [
                "feedback.py",
                command,
                "./",
                "--instrument",
                self.instrument,
                "--run",
                self.run_id,
                "--json",
                *options,
            ]
        )

    def append(self, *options: str) -> int:
        return self.call(
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
            *options,
        )

    def checkpoint(self) -> int:
        key = write_feedback_trust(self.root)
        shutil.copyfile(key, self.root / "key")
        (self.root / "key").chmod(0o600)
        return self.call("checkpoint", "--principal", "ada", "--key", "./key", "--at", STAMP)

    def lines(self) -> list[JSONValue]:
        return [
            parse_json(line)
            for line in (self.directory / integrity.FEEDBACK_CHAIN).read_bytes().splitlines()
        ]


@pytest.fixture
def parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Parent:
    root = tmp_path / "parent"
    directory = write_resume_parent(root, "ENGRAM", "engram-ada-1")
    (root / "r.json").write_bytes(canonicalize([{"hypothesis": "resume", "confidence": "high"}]))
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"hello"), encoding="utf-8"))
    return Parent(root, directory, "ENGRAM", "engram-ada-1")


@SIGNED
def test_append_produces_a_chain_integrity_accepts(parent: Parent) -> None:
    # Given two turns in one namespace.
    assert parent.append() == 0
    assert parent.append() == 0
    # When the current head is signed.
    assert parent.checkpoint() == 0
    # Then the real verifier walks this run, not an unused root-level copy.
    assert integrity.check_feedback_chain(str(parent.root), evaluation_time=NOW) == []
    chain = parent.directory / integrity.FEEDBACK_CHAIN
    chain.write_bytes(chain.read_bytes().replace(b'"seq":2', b'"seq":3'))
    assert integrity.check_feedback_chain(str(parent.root), evaluation_time=NOW)


def test_chain_line_is_canonical_json_byte_for_byte(parent: Parent) -> None:
    # Given a capture request; when appended; then exact canonical bytes are emitted.
    assert parent.append() == 0
    for line in (parent.directory / integrity.FEEDBACK_CHAIN).read_text().splitlines():
        assert canonicalize(parse_json(line)).decode().removesuffix("\n") == line
        assert set(json.loads(line)) == integrity.CHAIN_FIELDS


def test_entry_hash_uses_the_verifier_digest_function(
    parent: Parent, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given the verifier's digest seam has a distinct result.
    monkeypatch.setattr(integrity, "chain_digest", lambda _entry: "b" * 64)
    # When captured; then that result is persisted.
    assert parent.append() == 0
    assert (
        '"entry_hash":"' + "b" * 64 + '"'
        in (parent.directory / integrity.FEEDBACK_CHAIN).read_text()
    )


@SIGNED
def test_checkpoint_payload_is_the_verifier_payload(
    parent: Parent, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a distinguishable payload returned by the verifier.
    assert parent.append() == 0
    payload = b"verifier-owned-payload\n"
    monkeypatch.setattr(integrity, "checkpoint_signature_payload", lambda *_args: payload)
    # When signed; then actual SSH verification accepts exactly those bytes.
    assert parent.checkpoint() == 0
    result = SshKeygenBackend().verify(
        payload,
        signature_path=parent.directory / "feedback-head.sig",
        allowed_signers_path=parent.root / ".memory/allowed_signers",
        evaluation_time=NOW,
    )
    assert result.verified


def test_genesis_prev_hash_is_sixty_four_zeros(parent: Parent) -> None:
    # Given no chain; when captured; then genesis links to zero.
    assert parent.append() == 0
    assert (
        json.loads((parent.directory / integrity.FEEDBACK_CHAIN).read_bytes())["prev_hash"]
        == "0" * 64
    )


def test_seq_is_dense_and_monotonic_across_three_appends(parent: Parent) -> None:
    # Given a fresh namespace; when three turns arrive; then no sequence is skipped.
    for _ in range(3):
        assert parent.append() == 0
    assert [line["seq"] for line in parent.lines() if isinstance(line, dict)] == [1, 2, 3]


def test_checkpoint_without_an_enrolled_root_refuses_and_writes_nothing(
    parent: Parent, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given an unsigned chain without trust.
    assert parent.append() == 0
    before = {path.name: path.read_bytes() for path in parent.directory.iterdir()}
    # When checkpointing; then refusal leaves every byte unchanged.
    assert parent.call("checkpoint", "--principal", "ada", "--key", "./missing", "--at", STAMP) == 3
    assert "FEEDBACK_CHECKPOINT_UNENROLLED" in capsys.readouterr().out
    assert {path.name: path.read_bytes() for path in parent.directory.iterdir()} == before


@SIGNED
@pytest.mark.parametrize("instrument", ["ENGRAM", "FORGE", "CRUCIBLE"])
def test_checkpoint_log_name_follows_the_harness(parent: Parent, instrument: str) -> None:
    # Given each supported instrument's namespace.
    run_id = f"{instrument.lower()}-ada-2"
    directory = runs.open_run(parent.root, instrument, run_id, principal="ada")
    lane = Parent(parent.root, directory, instrument, run_id)
    assert lane.append() == 0
    # When checkpointed; then only the declared roster is written.
    assert lane.checkpoint() == 0
    harness = runs.HARNESS[instrument].removeprefix(".")
    assert {path.name for path in directory.iterdir()} == {
        "run.json",
        "feedback.yaml",
        integrity.FEEDBACK_CHAIN,
        integrity.FEEDBACK_CHECKPOINTS[harness],
        "feedback-head.sig",
    }
    assert integrity.check_feedback_chain(str(parent.root), NOW) == []


def test_append_refuses_a_foreign_run(parent: Parent, capsys: pytest.CaptureFixture[str]) -> None:
    # Given ada owns the run; when bob writes; then ownership refuses.
    assert parent.append("--principal", "bob") == 3
    assert "run-owned" in capsys.readouterr().out
    assert not (parent.directory / integrity.FEEDBACK_CHAIN).exists()


@pytest.mark.parametrize(
    "flag,value,code",
    [
        ("--kind", "invented", "FEEDBACK_KIND_UNKNOWN"),
        ("--github-id", "", "FEEDBACK_IDENTITY_UNRESOLVED"),
        ("--github-id", "unattributed", "FEEDBACK_IDENTITY_UNRESOLVED"),
    ],
)
def test_append_refuses_a_kind_outside_the_closed_vocabulary(
    parent: Parent, capsys: pytest.CaptureFixture[str], flag: str, value: str, code: str
) -> None:
    # Given an unsupported kind; when captured; then no ledger is authored.
    assert parent.append(flag, value) == 3
    assert code in capsys.readouterr().out
    assert not (parent.directory / "feedback.yaml").exists()


def test_verbatim_bytes_are_never_modified(parent: Parent) -> None:
    # Given exact pipe bytes, including CRLF, tabs and non-ASCII.
    assert callable(main)
    raw = "hello\r\n\t世界\n".encode()
    # When the real CLI reads stdin; then the digest and ledger preserve it.
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "append",
            "./",
            "--instrument",
            "ENGRAM",
            "--run",
            parent.run_id,
            "--principal",
            "ada",
            "--kind",
            "question",
            "--github-id",
            "ada",
            "--reasoning-file",
            "./r.json",
            "--received-at",
            STAMP,
            "--json",
        ],
        input=raw,
        capture_output=True,
        cwd=parent.root,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    entry = json.loads((parent.directory / integrity.FEEDBACK_CHAIN).read_bytes())
    assert entry["verbatim_sha256"] == hashlib.sha256(raw).hexdigest()
    record = json.loads((parent.directory / "feedback.yaml").read_text()[2:])
    assert record["verbatim"].encode() == raw
    assert entry["record_sha256"] == hashlib.sha256(canonicalize(record)).hexdigest()


def test_feedback_paths_are_inside_the_subject_closure(parent: Parent) -> None:
    # Given the pre-capture closure (ADR 0005 decision 3).
    before = subject.subject_digest(parent.root, parent.instrument, parent.run_id)
    # When feedback arrives; then qualification must bind a fresh closure.
    assert parent.append() == 0
    assert subject.subject_digest(parent.root, parent.instrument, parent.run_id) != before


@SIGNED
def test_walk_head_matches_the_printed_head(
    parent: Parent, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given a published head.
    assert parent.append() == 0
    appended = json.loads(capsys.readouterr().out)
    assert parent.checkpoint() == 0
    capsys.readouterr()
    # When walked; then it reports the same sequence and digest.
    assert parent.call("walk") == 0
    assert json.loads(capsys.readouterr().out) == appended


@pytest.mark.parametrize(
    "damage,code",
    [
        ("chain", "FEEDBACK_CHAIN_BROKEN"),
        ("checkpoint", "FEEDBACK_HEAD_ROLLED_BACK"),
    ],
)
def test_append_refuses_damaged_history(
    parent: Parent, capsys: pytest.CaptureFixture[str], damage: str, code: str
) -> None:
    # Given existing history that has been changed outside the capture path.
    assert parent.append() == 0
    if damage == "chain":
        (parent.directory / integrity.FEEDBACK_CHAIN).write_text("{}\n")
    else:
        (parent.directory / "checkpoints.yaml").write_text("- root: " + "f" * 64 + "\n")
    before = {path.name: path.read_bytes() for path in parent.directory.iterdir()}
    # When appending; then refuse without repairing or extending the damaged history.
    assert parent.append() == 3
    assert code in capsys.readouterr().out
    assert {path.name: path.read_bytes() for path in parent.directory.iterdir()} == before
