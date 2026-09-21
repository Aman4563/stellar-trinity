import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from tools.attest.backend_ssh import SshKeygenBackend
from tools.attest.canonical import JSONValue, canonicalize
from tools.attest.dsse import sign_envelope
from tools.attest.intoto import APPROVAL_PREDICATE_TYPE, STATEMENT_TYPE
from tools.attest.verify import IN_TOTO_PAYLOAD_TYPE

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "attest"
ALLOWED_SIGNERS = FIXTURES / "allowed_signers"
TRUST_ROOT = FIXTURES / "trust_root.json"
VALID_KEY = "TEST_ONLY_valid_ed25519"
ARTIFACT = b"cli artifact bytes\n"
COLLATERAL = b"failed probe\n"


def descriptor(name: str, content: bytes) -> dict[str, JSONValue]:
    return {"name": name, "digest": {"sha256": hashlib.sha256(content).hexdigest()}}


def approval_payload() -> bytes:
    statement: JSONValue = {
        "_type": STATEMENT_TYPE,
        "subject": [
            {"name": "artifact.bin", "digest": {"sha256": hashlib.sha256(ARTIFACT).hexdigest()}}
        ],
        "predicateType": APPROVAL_PREDICATE_TYPE,
        "predicate": {
            "producerIdentity": "producer@trinity.test",
            "approverIdentity": "valid-signer@trinity.test",
            "producerModelLineage": "provider/model-a/2026-08",
            "approverModelLineage": "provider/model-b/2026-08",
            "failedBreakAttempt": descriptor("failed-break.jsonl", b"failed probe\n"),
            "replay": {
                "nonce": "nonce-1",
                "audience": "project-a",
                "sequence": 1,
                "runId": "run-1",
            },
        },
    }
    return json.dumps(statement, separators=(",", ":")).encode()


def copy_private_key(tmp_path: Path) -> Path:
    target = tmp_path / VALID_KEY
    target.write_bytes((FIXTURES / VALID_KEY).read_bytes())
    target.chmod(0o600)
    return target


def build_cli_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    artifact_path = candidate / "artifact.bin"
    artifact_path.write_bytes(ARTIFACT)
    backend = SshKeygenBackend(timeout_seconds=5.0)
    envelope = sign_envelope(
        backend,
        IN_TOTO_PAYLOAD_TYPE,
        approval_payload(),
        key_path=copy_private_key(candidate),
    )
    envelope_path = tmp_path / "attestation.dsse.json"
    envelope_path.write_bytes(envelope.to_json())
    trust_root_path = tmp_path / "trust-root.json"
    trust_root_path.write_text(
        json.dumps(
            {
                "version": 7,
                "expires": "2030-01-01T00:00:00Z",
                "roles": [
                    {"name": "gate_approver", "threshold": 1},
                    {"name": "execution_operator", "threshold": 1},
                ],
                "principals": [
                    {
                        "name": "valid-signer@trinity.test",
                        "roles": ["gate_approver", "execution_operator"],
                        "expires": "2029-01-01T00:00:00Z",
                    }
                ],
                "revocations": [],
            }
        ),
        encoding="utf-8",
    )
    return envelope_path, artifact_path, trust_root_path


def run_cli(
    envelope_path: Path,
    artifact_path: Path,
    replay_store: Path,
    *,
    trust_root_path: Path = TRUST_ROOT,
    extra_arguments: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    authority_root = artifact_path.parent.parent

    def relative(path: Path) -> str:
        return "./" + path.relative_to(authority_root).as_posix()

    collateral_path = artifact_path.with_name("failed-break.jsonl")
    collateral_path.write_bytes(COLLATERAL)
    manifest_path = artifact_path.with_name("collateral.json")
    manifest_path.write_text(
        json.dumps({"failed-break.jsonl": relative(collateral_path)}),
        encoding="utf-8",
    )
    policy_path = authority_root / ".trinity" / "attest-gate.json"
    policy_path.parent.mkdir(parents=True)
    configured_store = authority_root / "state" / replay_store.name
    selected_trust_root = trust_root_path
    if not selected_trust_root.is_relative_to(authority_root):
        selected_trust_root = authority_root / "trust" / "trust-root.json"
        selected_trust_root.parent.mkdir()
        selected_trust_root.write_bytes(trust_root_path.read_bytes())
    allowed_signers = authority_root / "trust" / "allowed-signers"
    allowed_signers.parent.mkdir(exist_ok=True)
    allowed_signers.write_bytes(ALLOWED_SIGNERS.read_bytes())
    policy_path.write_bytes(
        canonicalize(
            {
                "expectedAudience": "project-a",
                "projectRoot": "./candidate",
                "replayStore": relative(configured_store),
                "trustedRootVersion": 7,
            }
        )
    )
    policy_path.chmod(0o600)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.attest",
            "verify",
            relative(envelope_path),
            relative(artifact_path),
            relative(selected_trust_root),
            relative(allowed_signers),
            relative(manifest_path),
            *extra_arguments,
        ],
        cwd=authority_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_accepts_a_valid_attestation(tmp_path: Path) -> None:
    envelope_path, artifact_path, trust_root_path = build_cli_files(tmp_path)

    result = run_cli(
        envelope_path,
        artifact_path,
        tmp_path / "accepted-replay.jsonl",
        trust_root_path=trust_root_path,
    )

    assert result.returncode == 0
    assert "accepted" in result.stdout
    assert "valid-signer@trinity.test" in result.stdout


def test_cli_refusal_prints_the_specific_reason(tmp_path: Path) -> None:
    envelope_path, artifact_path, trust_root_path = build_cli_files(tmp_path)
    artifact_path.write_bytes(b"tampered artifact\n")

    result = run_cli(
        envelope_path,
        artifact_path,
        tmp_path / "refused-replay.jsonl",
        trust_root_path=trust_root_path,
    )

    assert result.returncode != 0
    assert "subject_digest_mismatch" in result.stdout


def test_cli_missing_envelope_prints_the_specific_reason(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    artifact_path = candidate / "artifact.bin"
    artifact_path.write_bytes(ARTIFACT)

    result = run_cli(
        tmp_path / "missing.dsse.json",
        artifact_path,
        tmp_path / "missing-replay.jsonl",
    )

    assert result.returncode != 0
    assert "envelope escapes or is unavailable" in result.stdout


def test_cli_derives_the_role_from_the_signed_predicate(tmp_path: Path) -> None:
    envelope_path, artifact_path, trust_root_path = build_cli_files(tmp_path)

    result = run_cli(
        envelope_path,
        artifact_path,
        tmp_path / "role-replay.jsonl",
        trust_root_path=trust_root_path,
    )

    assert result.returncode == 0
    assert "accepted" in result.stdout


def test_cli_caller_cannot_revive_a_revoked_signer_with_a_historical_instant(
    tmp_path: Path,
) -> None:
    envelope_path, artifact_path, trust_root_path = build_cli_files(tmp_path)
    document = json.loads(trust_root_path.read_bytes())
    assert isinstance(document, dict)
    document["revocations"] = [
        {
            "principal": "valid-signer@trinity.test",
            "revoked_at": "2026-06-01T00:00:00Z",
        }
    ]
    trust_root_path.write_text(json.dumps(document), encoding="utf-8")

    result = run_cli(
        envelope_path,
        artifact_path,
        tmp_path / "rollback-replay.jsonl",
        trust_root_path=trust_root_path,
    )

    assert result.returncode == 1
    assert "principal_revoked" in result.stdout


def test_cli_usage_error_exits_two() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tools.attest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "Usage:" in result.stdout


def test_cli_help_flags_exit_zero_without_running_an_operation(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    for flag in ("-h", "--help"):
        result = subprocess.run(
            [sys.executable, "-m", "tools.attest", flag],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout
        assert "evaluated_at:" not in result.stdout
        assert result.stderr == ""


def test_cli_rejects_deprecated_presenter_policy_arguments(tmp_path: Path) -> None:
    envelope_path, artifact_path, trust_root_path = build_cli_files(tmp_path)

    result = run_cli(
        envelope_path,
        artifact_path,
        tmp_path / "configured-replay.jsonl",
        trust_root_path=trust_root_path,
        extra_arguments=(
            "gate_approver",
            "2026-01-01T00:00:00Z",
            "7",
            str(tmp_path / "attacker-replay.jsonl"),
            "attacker-audience",
        ),
    )

    assert result.returncode == 2
    assert "wrong number of arguments" in result.stdout
