from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest
from tools import sentinel
from tools._findings import FindingJson
from tools.attest import canonical, dsse
from tools.attest.backend_ssh import SshKeygenBackend

from tests.parent_fixtures import git

NOW: Final = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
AUTHOR: Final = "Actor <actor@trinity.test>"
ACTOR: Final = "actor@trinity.test"
CLEARER: Final = "clearer@trinity.test"
ROLE: Final = "sentinel_clearer"
PAYLOAD_TYPE: Final = "application/vnd.trinity.sentinel-clearance+json"
SCHEMA: Final = "trinity.sentinel-clearance/v1"
REFUSAL: Final[FindingJson] = {
    "code": "APPROVAL_PRODUCER_IS_APPROVER",
    "severity": "error",
    "path": "VERDICT.md",
    "line": None,
    "message": "refused",
}


def ssh_keygen_executable() -> str:
    executable = shutil.which("ssh-keygen")
    if executable is None:
        pytest.skip("ssh-keygen is required for software-key integration")
    return executable


def generate_key(directory: Path, name: str) -> tuple[Path, str]:
    executable = ssh_keygen_executable()
    directory.mkdir(parents=True, exist_ok=True)
    key = directory / name
    subprocess.run(
        [executable, "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return key, " ".join(key.with_suffix(".pub").read_text(encoding="utf-8").split()[:2])


def write_trust(
    root: Path,
    *,
    entries: Mapping[str, tuple[Path, str]],
    roles: Mapping[str, int],
    bindings: Mapping[str, tuple[str, ...]],
    expires: str = "2028-01-01T00:00:00Z",
    version: int = 1,
) -> None:
    memory = root / ".memory"
    memory.mkdir(parents=True, exist_ok=True)
    (memory / "allowed_signers").write_text(
        "".join(
            f'{name} namespaces="trinity.attestation.v1,git" {pub}\n'
            for name, (_, pub) in entries.items()
        ),
        encoding="utf-8",
    )
    (memory / "roots.yaml").write_text(
        json.dumps(
            {
                "version": version,
                "expires": expires,
                "roles": [
                    {"name": name, "threshold": threshold} for name, threshold in roles.items()
                ],
                "principals": [
                    {"name": name, "roles": list(bound)} for name, bound in bindings.items()
                ],
                "revocations": [],
            }
        ),
        encoding="utf-8",
    )
    (memory / "trusted-root-version").write_text(f"{version}\n", encoding="utf-8")


def sign_head(root: Path, key: Path, *, name: str, email: str) -> None:
    ssh_keygen_executable()
    for setting, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", ssh_keygen_executable()),
        ("user.signingkey", str(key) + ".pub"),
        ("commit.gpgsign", "true"),
    ):
        git(["config", setting, value], cwd=root)
    git(
        ["commit", "-q", "--allow-empty", "--author", f"{name} <{email}>", "-m", "signed attempt"],
        cwd=root,
    )


def forge_head(root: Path, *, name: str, email: str) -> None:
    git(
        [
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "--author",
            f"{name} <{email}>",
            "-m",
            "claimed attempt",
        ],
        cwd=root,
    )


def verified_actor() -> sentinel.Actor:
    return sentinel.Actor.verified(git_author=AUTHOR, github_login=None, principal=ACTOR)


def plant(root: Path, actor: sentinel.Actor, *, run_id: str = "run-1") -> sentinel.Attempt:
    new, chain = sentinel.record(
        root,
        [REFUSAL],
        actor=actor,
        run_id=run_id,
        git_sha="b" * 40,
        repo="EtharaOrion/argos",
        now=NOW,
    )
    assert not chain and len(new) == 1
    return new[0]


def plant_repeat(root: Path, actor: sentinel.Actor) -> sentinel.Alert:
    for number in range(1, 6):
        plant(root, actor, run_id=f"run-{number}")
    alerts, defect = sentinel.read_alerts(root / sentinel.ALERTS_PATH)
    assert defect is None and len(alerts) == 1
    return alerts[0]


def write_v1(root: Path) -> sentinel.Alert:
    previous = "0" * 64
    records: list[str] = []
    actor: dict[str, canonical.JSONValue] = {
        "git_author": AUTHOR,
        "github_login": None,
        "source": "local",
    }
    for number in range(1, 6):
        body: dict[str, canonical.JSONValue] = {
            "actor": actor,
            "captured_at": "2026-09-16T12:00:00Z",
            "code": "SAB_SELF_APPROVAL",
            "evidence_digest": sentinel.evidence_digest([REFUSAL]),
            "findings": [
                {
                    "code": REFUSAL["code"],
                    "severity": REFUSAL["severity"],
                    "path": REFUSAL["path"],
                    "line": None,
                    "message": REFUSAL["message"],
                }
            ],
            "git_sha": "b" * 40,
            "previous_hash": previous,
            "repo": "EtharaOrion/argos",
            "run_id": f"run-{number}",
            "schema_version": "trinity.sentinel-attempt/v1",
            "seq": number,
            "weight": 3,
        }
        previous = hashlib.sha256(canonical.canonicalize(body)).hexdigest()
        records.append(sentinel.canonical_line({**body, "entry_hash": previous}))
    paths = sentinel.layout(root)
    paths.directory.mkdir(parents=True)
    paths.ledger.write_text("\n".join(records) + "\n", encoding="utf-8")
    sentinel.write_head(paths.head, 5, previous)
    alert_body: dict[str, canonical.JSONValue] = {
        "actor": actor,
        "codes": ["SAB_SELF_APPROVAL"],
        "first_seq": 1,
        "last_seq": 5,
        "previous_hash": "0" * 64,
        "raised_at": "2026-09-16T12:00:00Z",
        "seq": 1,
        "threshold": 5,
        "window_days": sentinel.DEFAULT_WINDOW_DAYS,
    }
    digest = hashlib.sha256(canonical.canonicalize(alert_body)).hexdigest()
    paths.alerts.write_text(
        sentinel.canonical_line({**alert_body, "entry_hash": digest}) + "\n",
        encoding="utf-8",
    )
    sentinel.write_head(paths.alerts_head, 1, digest)
    alerts, defect = sentinel.read_alerts(paths.alerts)
    assert defect is None and len(alerts) == 1
    return alerts[0]


@dataclass(frozen=True, slots=True)
class SigningRoot:
    root: Path
    entries: Mapping[str, tuple[Path, str]]

    def trust(self, *, expires: str = "2028-01-01T00:00:00Z") -> None:
        write_trust(
            self.root,
            entries=self.entries,
            roles={ROLE: 1, "gate_approver": 1},
            bindings={
                ACTOR: (ROLE,),
                CLEARER: (ROLE,),
                "observer@trinity.test": ("gate_approver",),
            },
            expires=expires,
        )

    def key(self, principal: str = CLEARER) -> Path:
        return self.entries[principal][0]


@dataclass(frozen=True, slots=True)
class ClearanceCase:
    signing: SigningRoot
    alert: sentinel.Alert

    def clear(self, principal: str = CLEARER) -> Path:
        return sentinel.write_clearance(
            self.signing.root,
            self.alert,
            key_path=self.signing.key(principal),
            reason="reviewed",
            evaluation_time=NOW,
            now=NOW,
        )

    def status(self) -> sentinel.ClearanceStatus:
        return sentinel.clearance_status(self.signing.root, self.alert, evaluation_time=NOW)

    def envelope(
        self,
        key: Path | None = None,
        *,
        payload_type: str = PAYLOAD_TYPE,
        changes: Mapping[str, canonical.JSONValue] | None = None,
    ) -> Path:
        payload: dict[str, canonical.JSONValue] = {
            "alert_entry_hash": self.alert.entry_hash,
            "cleared_at": "2026-09-16T12:00:00Z",
            "reason": "reviewed",
            "schema": SCHEMA,
            "stream": None,
        }
        payload.update(changes or {})
        envelope = dsse.sign_envelope(
            SshKeygenBackend(),
            payload_type,
            canonical.canonicalize(payload),
            key_path=key or self.signing.key(),
        )
        path = sentinel.clearance_path(self.signing.root, self.alert)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(envelope.to_json())
        return path

    def refused(self, detail: str) -> None:
        status = self.status()
        assert not status.cleared and not status.principals and not status.unsigned
        assert detail.lower() in status.detail.lower()
        findings = sentinel.check_sentinel_chain(str(self.signing.root), NOW)
        assert any(item.code == "SAB_REPEATED_ATTEMPT" for item in findings)


def cli(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(Path(sentinel.__file__).resolve()), *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
