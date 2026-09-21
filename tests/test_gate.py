"""Both-halves fixtures for the gate entry point in tools/gate.py."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tools import layout
from tools._findings import Finding, Severity
from tools.attest.backend import VerificationResult
from tools.attest.dsse import Envelope, Signature, parse_envelope

from tests.bite_shared.registration import bite
from tests.harness_imports import load_harness

gate = load_harness("gate")
integrity = load_harness("integrity")
runs = load_harness("runs")
subject = load_harness("subject")
reports = load_harness("reports")

HUMAN = "Human Operator"
HUMAN_EMAIL = "human@trinity.test"
NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
TEST_UUID = "0a463270-a79e-45d1-8102-af28bec64c47"
FINAL_DISPOSITION_FIELDS = {
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
}
HOOK_BODY = (
    "#!/bin/sh\npython3 trinity/tools/gate.py . --instrument CRUCIBLE --moment report --check\n"
)


class SigningBackend:
    keyid_scheme = "test:v1"

    def sign(self, payload: bytes, *, key_path: Path) -> bytes:
        return payload[:16] + key_path.read_bytes()

    def verify(
        self,
        payload: bytes,
        *,
        signature_path: Path,
        allowed_signers_path: Path,
        evaluation_time: datetime | None = None,
    ) -> VerificationResult:
        del payload, signature_path, allowed_signers_path, evaluation_time
        raise AssertionError("signing test does not verify")


class RefusingBackend(SigningBackend):
    def __init__(self) -> None:
        self.called = False

    def sign(self, payload: bytes, *, key_path: Path) -> bytes:
        del payload, key_path
        self.called = True
        raise AssertionError("invalid candidate reached the signing backend")


class IdentityBackend(SigningBackend):
    def verify(
        self,
        payload: bytes,
        *,
        signature_path: Path,
        allowed_signers_path: Path,
        evaluation_time: datetime | None = None,
    ) -> VerificationResult:
        del payload, allowed_signers_path, evaluation_time
        return VerificationResult.success(signature_path.read_bytes().decode("utf-8"))


def git(argv: list[str], *, cwd: Path) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": HUMAN,
        "GIT_AUTHOR_EMAIL": HUMAN_EMAIL,
        "GIT_COMMITTER_NAME": HUMAN,
        "GIT_COMMITTER_EMAIL": HUMAN_EMAIL,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    completed = subprocess.run(
        ["git", *argv],
        cwd=cwd,
        capture_output=True,
        check=False,
        env=environment,
        shell=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return completed.stdout.strip()


def commit_all(root: Path, message: str = "commit") -> str:
    git(["add", "-A"], cwd=root)
    git(["-c", "commit.gpgsign=false", "commit", "-q", "--allow-empty", "-m", message], cwd=root)
    return git(["rev-parse", "HEAD"], cwd=root)


def make_parent(tmp_path: Path) -> Path:
    root = tmp_path / "parent"
    root.mkdir()
    git(["init", "-q", "-b", "main"], cwd=root)
    (root / "README.md").write_text("parent\n", encoding="utf-8")
    commit_all(root, "genesis")
    return root


def test_record_sentinel_persists_only_project_relative_paths(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    findings = [
        Finding(
            "APPROVAL_PRODUCER_IS_APPROVER",
            Severity.ERROR,
            str(root / "VERDICT.md"),
            None,
            f"refused approval in {root}",
        )
    ]

    gate.record_sentinel(root, findings, run_id="relative-paths", ci=False)

    lines = (root / ".sentinel/attempts.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert all(str(root) not in line for line in lines)
    assert json.loads(lines[0])["findings"][0]["path"] == "./VERDICT.md"


def write_release_trust(tmp_path: Path) -> Path:
    trust = tmp_path / "release-trust"
    trust.mkdir()
    controls = [
        "build_assets_harness",
        "oracle_noop_known_wrong_adversary_integrity",
        "alternate_correct_mutant_grading_instruction_scope",
        "judge_completeness_repeatability",
        "trial_reward_accounting",
        "execution_fidelity",
    ]
    (trust / "roots.yaml").write_text(
        json.dumps(
            {
                "version": 1,
                "expires": "2030-01-01T00:00:00Z",
                "roles": [{"name": "gate_approver", "threshold": 1}],
                "principals": [
                    {
                        "name": "approver@trinity.test",
                        "roles": ["gate_approver"],
                        "expires": "2030-01-01T00:00:00Z",
                    }
                ],
                "revocations": [],
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    (trust / "allowed_signers").write_text("test policy\n", encoding="utf-8")
    (trust / "trusted-root-version").write_text("1\n", encoding="utf-8")
    (trust / "policy.json").write_text(
        json.dumps(
            {
                "schema": "trinity.release-policy/v3",
                "trusted_root_version": 1,
                "project_id": "project-17",
                "repository_id": "424242",
                "verifier_sha": "3" * 40,
                "disposition_max_age_seconds": 3600,
                "oracle": {
                    "harbor_version": "0.3.0",
                    "image_digest": f"sha256:{'1' * 64}",
                    "harness_digest": f"sha256:{'2' * 64}",
                    "full_reward": 1.0,
                    "score_min": 0.0,
                    "score_max": 1.0,
                    "negative_score_max": 0.1,
                    "stability_runs": 3,
                    "max_age_seconds": 3600,
                    "required_controls": controls,
                    "positive_control_ids": controls,
                    "non_applicable_controls": [],
                },
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    return trust


def configure_group_trust(
    trust: Path,
    *,
    producer_threshold: int = 1,
    producers: tuple[str, ...] = ("producer-b@trinity.test",),
    approvers: tuple[str, ...] = ("approver-c@trinity.test",),
) -> None:
    root = json.loads((trust / "roots.yaml").read_text(encoding="utf-8"))
    root["roles"] = [
        {"name": "gate_producer", "threshold": producer_threshold},
        {"name": "gate_approver", "threshold": 1},
    ]
    root["principals"] = [
        *({"name": item, "roles": ["gate_producer"]} for item in producers),
        *({"name": item, "roles": ["gate_approver"]} for item in approvers),
    ]
    (trust / "roots.yaml").write_text(json.dumps(root), encoding="utf-8")


def partial(path: Path, payload_type: str, payload: bytes, principal: str) -> Path:
    path.write_bytes(
        Envelope(payload_type, payload, (Signature(principal.encode(), "test:v1"),)).to_json()
    )
    return path


def promoted_parent(tmp_path: Path, instrument: str = "FORGE") -> tuple[Path, Path]:
    root = make_parent(tmp_path)
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate bundle")
    gate.mint_record(root, instrument=instrument, findings=[], now=NOW)
    commit_all(root, "mint qualification")
    trust = write_release_trust(tmp_path)
    gate.promote(
        root,
        instrument=instrument,
        approver="approver@trinity.test",
        now=NOW,
        trust_dir=trust,
    )
    return root, trust


def error(code: str) -> Finding:
    return Finding(code, Severity.ERROR, "VERDICT.md", None, "refused")


def advisory(code: str) -> Finding:
    return Finding(code, Severity.ADVISORY, "VERDICT.md", None, "noted")


def write_report(root: Path, report: str, token: str) -> None:
    (root / report).write_text(
        f"# {report}\n\n## Disposition\n\n{token}\n\n## Findings\n\nnone\n", encoding="utf-8"
    )


def write_hook(root: Path, body: str = HOOK_BODY) -> None:
    hook = root / gate.HOOK_PATH
    hook.parent.mkdir(exist_ok=True)
    hook.write_text(body, encoding="utf-8")


def codes(findings: list[object]) -> set[str]:
    return {item.code for item in findings}  # type: ignore[attr-defined]


def gate_codes(root: Path) -> set[str]:
    return codes(gate.check_gate_receipts(str(root), NOW))


def sealed_parent(tmp_path: Path, ceiling_findings: list[Finding], token: str) -> Path:
    """A parent whose CRUCIBLE record, receipt, and report were minted, then committed."""

    root = make_parent(tmp_path)
    write_hook(root)
    commit_all(root, "hook")
    gate.write_receipt(
        root, instrument="CRUCIBLE", moment="report", findings=ceiling_findings, run_id="run-1"
    )
    gate.mint_record(root, instrument="CRUCIBLE", findings=ceiling_findings, now=NOW)
    write_report(root, "VERDICT.md", token)
    commit_all(root, "seal")
    return root


# ---- ceiling rule ----------------------------------------------------------------


@bite("shared.md:A36")
def test_empty_error_set_is_ship_eligible_never_ship() -> None:
    assert gate.ceiling([]) == gate.SHIP_ELIGIBLE
    assert gate.ceiling([advisory("SAB_SUBMODULE_UNVERIFIED")]) == gate.SHIP_ELIGIBLE
    assert gate.SHIP not in gate.CEILINGS


def test_ordinary_error_is_hold() -> None:
    assert gate.ceiling([error("INTEGRITY_VIOLATION")]) == gate.HOLD


@pytest.mark.parametrize(
    "code", ["SAB_DISPOSITION_UNBOUND", "RELEASE_VERDICT_NOT_SHIP", "TRINITY_FRESHNESS_BEHIND"]
)
def test_sabotage_release_and_freshness_errors_are_block(code: str) -> None:
    assert gate.ceiling([error("INTEGRITY_VIOLATION"), error(code)]) == gate.BLOCK


# ---- receipts and records ------------------------------------------------------------


def test_preflight_writes_a_receipt_and_mints_no_record(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    receipt = gate.write_receipt(
        root, instrument="FORGE", moment="preflight", findings=[error("X_ONE")], run_id="r/1"
    )
    assert receipt == root / ".seed" / gate.RECEIPT_DIR / "r_1.json"
    value = json.loads(receipt.read_text("utf-8"))
    assert set(value) == gate.RECEIPT_FIELDS
    assert value["moment"] == "preflight"
    assert value["ceiling"] == gate.HOLD
    assert value["codes"] == ["X_ONE"]
    assert value["tree_sha"] == git(["rev-parse", "HEAD"], cwd=root)
    assert not (root / ".seed" / gate.DISPOSITION_RECORD).exists()


def test_report_moment_mints_the_closed_record_at_the_ceiling(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    path = gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    record = json.loads(path.read_bytes())
    assert set(record) == gate.DISPOSITION_FIELDS
    assert record["disposition"] == gate.SHIP_ELIGIBLE
    assert record["tree_sha"] == git(["rev-parse", "HEAD"], cwd=root)
    assert record["trinity_commit"] == gate.SHA40_ZERO
    assert record["bundle_digest"] == gate.SHA64_ZERO
    assert record["producer"] == HUMAN_EMAIL
    assert record["approver"] == gate.UNSIGNED_APPROVER
    assert record["generated_at"] == "2026-09-16T12:00:00Z"


def test_bundle_digest_matches_release_digest(tmp_path: Path) -> None:
    release = load_harness("release")
    root = make_parent(tmp_path)
    bundle = root / "samples" / "0a463270-a79e-45d1-8102-af28bec64c47"
    (bundle / "tests").mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    (bundle / "tests" / "test.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    expected = release.bundle_set_digest(root / "samples", release.exported_uuids(root / "samples"))
    assert gate.bundle_set_digest(root) == expected


# ---- promote ------------------------------------------------------------------------


def test_promote_refuses_a_record_that_is_not_eligible(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    gate.mint_record(root, instrument="CRUCIBLE", findings=[error("X")], now=NOW)
    with pytest.raises(gate.GateError, match="not SHIP_ELIGIBLE"):
        gate.promote(root, instrument="CRUCIBLE", approver="approver@trinity.test")


def test_promote_refuses_self_approval(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    with pytest.raises(gate.GateError, match="approver equals"):
        gate.promote(root, instrument="CRUCIBLE", approver=HUMAN_EMAIL)
    with pytest.raises(gate.GateError, match="named approver"):
        gate.promote(root, instrument="CRUCIBLE", approver=gate.UNSIGNED_APPROVER)


def test_promote_refuses_when_samples_moved_since_minting(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    bundle = root / "samples" / "0a463270-a79e-45d1-8102-af28bec64c47"
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(gate.GateError, match="moved"):
        gate.promote(root, instrument="CRUCIBLE", approver="approver@trinity.test")


def test_promote_refuses_changes_after_qualification_was_sealed(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    commit_all(root, "seal qualification")
    (root / "README.md").write_text("changed after qualification\n", encoding="utf-8")
    commit_all(root, "unqualified change")
    with pytest.raises(gate.GateError, match="does not bind HEAD"):
        gate.promote(root, instrument="CRUCIBLE", approver="approver@trinity.test")


def test_promote_refuses_instrument_without_final_release_domain(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    with pytest.raises(gate.GateError, match="no final release disposition domain"):
        gate.promote(root, instrument="ENGRAM", approver="approver@trinity.test")


def test_promote_rewrites_an_eligible_record_to_ship_bound_to_head(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate bundle")
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    head = commit_all(root, "mint")
    path = gate.promote(
        root,
        instrument="CRUCIBLE",
        approver="approver@trinity.test",
        now=NOW,
        trust_dir=write_release_trust(tmp_path),
    )
    record = json.loads(path.read_bytes())
    assert record["disposition"] == gate.SHIP
    assert record["approver"] == "approver@trinity.test"
    assert record["candidate_commit"] == head
    assert set(record) == FINAL_DISPOSITION_FIELDS
    instruction = gate.signing_instruction(root, "CRUCIBLE")
    assert "sign-partial" in instruction
    assert ".audit/disposition.json.dsse" in instruction
    assert "TRUSTED_SIGNER_CODE_DIR" in instruction
    assert "TRUSTED_RELEASE_TRUST_DIR" in instruction
    assert "python3 -I" in instruction
    assert f"{root}/trinity/tools/gate.py" not in instruction
    assert '"--root=$CANDIDATE_ROOT"' in instruction
    assert "CANDIDATE_ROOT=./candidate-data" in instruction
    assert "TRUSTED_SIGNER_CODE_DIR=./trusted-signer" in instruction
    assert str(tmp_path) not in instruction


def test_group_promotion_is_default_only_when_governance_roles_exist(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate")
    gate.mint_record(root, instrument="FORGE", findings=[], now=NOW)
    commit_all(root, "qualification")
    trust = write_release_trust(tmp_path)
    with pytest.raises(gate.GateError, match="gate_producer"):
        gate.promote(root, instrument="FORGE", now=NOW, trust_dir=trust)
    configure_group_trust(trust)
    record = json.loads(
        gate.promote(root, instrument="FORGE", now=NOW, trust_dir=trust).read_bytes()
    )
    assert set(record) == gate.GROUP_DISPOSITION_FIELDS
    assert record["schema"] == gate.GROUP_DISPOSITION_SCHEMA
    assert record["producer_role"] == "gate_producer"
    assert record["approver_role"] == "gate_approver"


def test_cosign_assembly_combines_independent_partial_envelopes(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    record = root / ".audit" / gate.DISPOSITION_RECORD
    record.parent.mkdir()
    record.write_bytes(b'{"record":"exact bytes"}')
    payload_type = gate.DISPOSITION_PAYLOAD_TYPES["CRUCIBLE"]
    producer = tmp_path / "producer.dsse"
    approver = tmp_path / "approver.dsse"
    producer.write_bytes(
        Envelope(payload_type, record.read_bytes(), (Signature(b"producer", "test:v1"),)).to_json()
    )
    approver.write_bytes(
        Envelope(payload_type, record.read_bytes(), (Signature(b"approver", "test:v1"),)).to_json()
    )
    output = tmp_path / "combined.dsse"
    gate.assemble_cosigned_envelope(
        root,
        instrument="CRUCIBLE",
        producer_envelope=producer,
        approver_envelope=approver,
        output=output,
    )
    parsed = parse_envelope(output.read_bytes())
    assert parsed.envelope is not None
    assert len(parsed.envelope.signatures) == 2


def test_group_quorum_resumes_across_sessions_and_status_uses_signatures(tmp_path: Path) -> None:
    root, trust = promoted_parent(tmp_path)
    configure_group_trust(
        trust,
        producer_threshold=2,
        producers=("producer-a@trinity.test", "producer-b@trinity.test", "producer-d@trinity.test"),
    )
    gate.mint_record(root, instrument="FORGE", findings=[], now=NOW)
    gate.promote(root, instrument="FORGE", now=NOW, trust_dir=trust)
    payload = (root / ".seed" / gate.DISPOSITION_RECORD).read_bytes()
    payload_type = gate.GROUP_DISPOSITION_PAYLOAD_TYPES["FORGE"]
    first = partial(tmp_path / "first.dsse", payload_type, payload, "producer-a@trinity.test")
    second = partial(tmp_path / "second.dsse", payload_type, payload, "producer-b@trinity.test")
    approval = partial(tmp_path / "approval.dsse", payload_type, payload, "approver-c@trinity.test")
    output = tmp_path / "complete.dsse"
    gate.assemble_cosigned_envelope(root, instrument="FORGE", output=output, envelope_paths=[first])
    waiting = gate.signing_status(
        root,
        instrument="FORGE",
        trust_dir=trust,
        envelope_paths=[],
        complete_envelope=output,
        backend=IdentityBackend(),
        now=NOW,
    )
    assert waiting["complete"] is False
    assert waiting["roles"]["gate_producer"]["missing"] == 1
    gate.assemble_cosigned_envelope(
        root, instrument="FORGE", output=output, envelope_paths=[second, approval]
    )
    complete = gate.signing_status(
        root,
        instrument="FORGE",
        trust_dir=trust,
        envelope_paths=[],
        complete_envelope=output,
        backend=IdentityBackend(),
        now=NOW,
    )
    assert complete["complete"] is True
    assert complete["authenticated_principals"] == [
        "producer-a@trinity.test",
        "producer-b@trinity.test",
        "approver-c@trinity.test",
    ]
    parsed = parse_envelope(output.read_bytes())
    assert parsed.envelope is not None and len(parsed.envelope.signatures) == 3


def test_real_software_ed25519_team_signing_uses_safe_candidate_path(tmp_path: Path) -> None:
    executable = shutil.which("ssh-keygen")
    if executable is None:
        pytest.skip("ssh-keygen is required for software-key integration")
    root = make_parent(tmp_path)
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate")
    gate.mint_record(root, instrument="FORGE", findings=[], now=NOW)
    commit_all(root, "qualification")
    trust = write_release_trust(tmp_path)
    configure_group_trust(trust)
    gate.promote(root, instrument="FORGE", now=NOW, trust_dir=trust)
    keys: dict[str, Path] = {}
    allowed: list[str] = []
    for principal in ("producer-b@trinity.test", "approver-c@trinity.test"):
        key = tmp_path / principal.split("@", 1)[0]
        subprocess.run(
            [executable, "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
            check=True,
            capture_output=True,
        )
        public = key.with_suffix(".pub").read_text(encoding="utf-8").split()
        allowed.append(f"{principal} {public[0]} {public[1]}")
        keys[principal] = key
    (trust / "allowed_signers").write_text("\n".join(allowed) + "\n", encoding="utf-8")
    partials: list[Path] = []
    for principal, key in keys.items():
        output = tmp_path / f"{principal.split('@', 1)[0]}.dsse"
        gate.sign_partial_envelope(
            root,
            instrument="FORGE",
            trust_dir=trust,
            key_path=key,
            output=output,
            now=NOW,
        )
        partials.append(output)
    complete = tmp_path / "team.dsse"
    gate.assemble_cosigned_envelope(
        root, instrument="FORGE", output=complete, envelope_paths=partials
    )
    status = gate.signing_status(
        root,
        instrument="FORGE",
        trust_dir=trust,
        envelope_paths=[],
        complete_envelope=complete,
        now=NOW,
    )
    assert status["complete"] is True
    assert set(status["authenticated_principals"]) == set(keys)


def test_partial_signing_mode_signs_exact_record_bytes(tmp_path: Path) -> None:
    root, trust = promoted_parent(tmp_path)
    record = root / ".seed" / gate.DISPOSITION_RECORD
    key = tmp_path / "private-key"
    key.write_bytes(b"producer-key")
    output = tmp_path / "producer.dsse"
    gate.sign_partial_envelope(
        root,
        instrument="FORGE",
        trust_dir=trust,
        key_path=key,
        output=output,
        backend=SigningBackend(),
        now=NOW,
    )
    parsed = parse_envelope(output.read_bytes())
    assert parsed.envelope is not None
    assert parsed.envelope.payload == record.read_bytes()
    assert parsed.envelope.payload_type == gate.DISPOSITION_PAYLOAD_TYPES["FORGE"]


def test_partial_signing_rejects_invalid_payload_before_key_or_backend_access(
    tmp_path: Path,
) -> None:
    root = make_parent(tmp_path)
    record = root / ".seed" / gate.DISPOSITION_RECORD
    record.parent.mkdir()
    record.write_bytes(b'{"candidate":"controlled"}')
    backend = RefusingBackend()
    with pytest.raises(gate.GateError, match="closed v2 field set"):
        gate.sign_partial_envelope(
            root,
            instrument="FORGE",
            trust_dir=write_release_trust(tmp_path),
            key_path=tmp_path / "key-that-must-not-be-opened",
            output=tmp_path / "partial.dsse",
            backend=backend,
            now=NOW,
        )
    assert not backend.called


def test_partial_signing_rejects_executable_candidate_git_config_before_key_access(
    tmp_path: Path,
) -> None:
    root, trust = promoted_parent(tmp_path)
    marker = tmp_path / "fsmonitor-executed"
    command = tmp_path / "touch-marker"
    command.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
    command.chmod(0o755)
    config = root / ".git" / "config"
    config.write_text(
        config.read_text(encoding="utf-8") + f"[core]\n\tfsmonitor = {command}\n",
        encoding="utf-8",
    )
    backend = RefusingBackend()
    with pytest.raises(gate.GateError, match="sealed snapshot"):
        gate.sign_partial_envelope(
            root,
            instrument="FORGE",
            trust_dir=trust,
            key_path=tmp_path / "key-that-must-not-be-opened",
            output=tmp_path / "partial.dsse",
            backend=backend,
            now=NOW,
        )
    assert not backend.called
    assert not marker.exists()


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("verifier_sha", "4" * 40, "external release trust"),
        ("snapshot_digest", "4" * 64, "complete candidate snapshot"),
        ("candidate_commit", "4" * 40, "sealed snapshot"),
        ("expires_at", "2026-09-16T14:00:00Z", "expiry exceeds external policy"),
        ("approver", HUMAN_EMAIL, "must be distinct"),
    ],
)
def test_partial_signing_completes_candidate_validation_before_key_access(
    tmp_path: Path, field: str, replacement: str, message: str
) -> None:
    root, trust = promoted_parent(tmp_path)
    record = root / ".seed" / gate.DISPOSITION_RECORD
    value = gate.parse_json(record.read_bytes())
    assert isinstance(value, dict)
    value[field] = replacement
    record.write_bytes(gate.canonicalize(value))
    backend = RefusingBackend()
    with pytest.raises(gate.GateError, match=message):
        gate.sign_partial_envelope(
            root,
            instrument="FORGE",
            trust_dir=trust,
            key_path=tmp_path / "key-that-must-not-be-opened",
            output=tmp_path / "partial.dsse",
            backend=backend,
            now=NOW,
        )
    assert not backend.called


def test_partial_signing_rejects_signer_code_inside_candidate_before_key_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path)
    candidate_gate = root / "trinity" / "tools" / "gate.py"
    candidate_gate.parent.mkdir(parents=True)
    candidate_gate.write_text("raise AssertionError('must not execute')\n", encoding="utf-8")
    backend = RefusingBackend()
    monkeypatch.setattr(gate, "__file__", str(candidate_gate))
    with pytest.raises(gate.GateError, match="outside the candidate tree"):
        gate.sign_partial_envelope(
            root,
            instrument="FORGE",
            trust_dir=tmp_path / "unused-trust",
            key_path=tmp_path / "key-that-must-not-be-opened",
            output=tmp_path / "partial.dsse",
            backend=backend,
            now=NOW,
        )
    assert not backend.called


def test_trusted_isolated_cli_treats_malicious_candidate_code_as_data(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    marker = tmp_path / "candidate-code-executed"
    malicious = root / "trinity" / "tools" / "gate.py"
    malicious.parent.mkdir(parents=True)
    malicious.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate including hostile gate")
    gate.mint_record(root, instrument="FORGE", findings=[], now=NOW)
    commit_all(root, "mint qualification")
    trust = write_release_trust(tmp_path)
    gate.promote(
        root,
        instrument="FORGE",
        approver="approver@trinity.test",
        now=datetime.now(UTC),
        trust_dir=trust,
    )
    key = tmp_path / "producer-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
        check=True,
        capture_output=True,
    )
    output = tmp_path / "producer.dsse"
    assert gate.__file__ is not None
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            str(Path(gate.__file__).resolve()),
            "sign-partial",
            "--root=./parent",
            "--instrument",
            "FORGE",
            "--trust-dir",
            "./release-trust",
            "--key",
            "./producer-key",
            "--output",
            "./producer.dsse",
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert not marker.exists()
    parsed = parse_envelope(output.read_bytes())
    assert parsed.envelope is not None
    assert parsed.envelope.payload == (root / ".seed" / gate.DISPOSITION_RECORD).read_bytes()
    assert "OPENSSH PRIVATE KEY" in key.read_text(encoding="utf-8")


def test_qualification_registry_excludes_final_authorization_checks() -> None:
    integrity = gate._harness_module("integrity")
    names = {check.__name__ for check in integrity.QUALIFICATION_CHECKS}
    assert "check_bundle_layout" in names
    assert "check_gates_installed" in names
    assert "check_disposition_binding" not in names
    assert "check_release_gate" not in names
    assert "check_gate_receipts" not in names


# ---- check_gate_receipts -----------------------------------------------------------------


def test_non_git_root_is_out_of_scope(tmp_path: Path) -> None:
    root = tmp_path / "plain"
    root.mkdir()
    write_report(root, "VERDICT.md", "SHIP")
    assert gate.check_gate_receipts(str(root), NOW) == []


@bite("shared.md:A33")
def test_report_without_receipt_is_refused(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    write_report(root, "VERDICT.md", "HOLD")
    commit_all(root, "report by hand")
    assert gate_codes(root) == {gate.GATE_PREFLIGHT_MISSING}


def test_report_with_receipt_binding_head_passes(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [error("X")], "HOLD")
    assert gate_codes(root) == set()


def test_receipt_bound_to_a_stale_tree_is_refused(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [error("X")], "HOLD")
    (root / "README.md").write_text("moved\n", encoding="utf-8")
    commit_all(root, "unrelated change after the gate")
    assert gate_codes(root) == {gate.GATE_PREFLIGHT_MISSING}


def test_preflight_receipt_alone_does_not_satisfy_the_report_moment(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    gate.write_receipt(root, instrument="CRUCIBLE", moment="preflight", findings=[], run_id="run-1")
    write_report(root, "VERDICT.md", "HOLD")
    commit_all(root, "preflight only")
    assert gate_codes(root) == {gate.GATE_PREFLIGHT_MISSING}


@bite("shared.md:A34")
def test_ship_over_a_hold_record_is_a_mismatch(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [error("X")], "SHIP")
    assert gate_codes(root) == {gate.GATE_DISPOSITION_MISMATCH}


def test_hold_over_a_block_record_is_a_mismatch(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [error("SAB_DIRTY_TREE")], "HOLD:PILOT_REQUIRED")
    assert gate_codes(root) == {gate.GATE_DISPOSITION_MISMATCH}


def test_block_over_a_hold_record_is_allowed(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [error("X")], "BLOCK:INVALID_TASK")
    assert gate_codes(root) == set()


def test_ship_eligible_report_over_eligible_record_passes(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [], "SHIP_ELIGIBLE")
    assert gate_codes(root) == set()


def test_ship_report_over_eligible_record_is_a_mismatch(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [], "SHIP")
    assert gate_codes(root) == {gate.GATE_DISPOSITION_MISMATCH}


def test_unknown_report_token_is_not_compared(tmp_path: Path) -> None:
    root = sealed_parent(tmp_path, [error("X")], "PENDING")
    assert gate_codes(root) == set()


@bite("shared.md:A35")
def test_missing_hook_is_refused(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    assert gate_codes(root) == {gate.GATE_HOOK_MISSING}


def test_hook_that_does_not_invoke_the_gate_is_refused(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root, "#!/bin/sh\nexit 0\n")
    assert gate_codes(root) == {gate.GATE_HOOK_MISSING}


def test_hook_invoking_the_gate_passes(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    assert gate_codes(root) == set()


def test_sealing_commit_may_touch_reports_receipts_and_ledger_only(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    commit_all(root, "hook")
    gate.write_receipt(root, instrument="FORGE", moment="report", findings=[], run_id="run-1")
    write_report(root, "EDICT.md", "SHIP_ELIGIBLE")
    (root / "TRACKING.md").write_text("tracker\n", encoding="utf-8")
    (root / ".sentinel").mkdir()
    (root / ".sentinel" / "attempts.jsonl").write_text("", encoding="utf-8")
    commit_all(root, "seal")
    assert gate_codes(root) == set()
    (root / "samples").mkdir()
    (root / "samples" / "smuggled.txt").write_text("x\n", encoding="utf-8")
    gate.write_receipt(root, instrument="FORGE", moment="report", findings=[], run_id="run-2")
    commit_all(root, "seal with a smuggled byte")
    # The receipt written by run-2 binds the previous HEAD, and this commit touched samples/.
    assert gate_codes(root) == {gate.GATE_PREFLIGHT_MISSING}


def test_receipt_binds_through_report_promotion_and_signing_commits(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    commit_all(root, "hook")
    gate.write_receipt(root, instrument="CRUCIBLE", moment="report", findings=[], run_id="r")
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    write_report(root, "VERDICT.md", "SHIP_ELIGIBLE")
    (root / "TRACKING.md").write_text("tracker\n", encoding="utf-8")
    commit_all(root, "report run output")
    (root / ".audit" / gate.DISPOSITION_RECORD).write_bytes(b'{"promoted":"bytes"}')
    commit_all(root, "promoted record")
    (root / ".trinity-runtime").mkdir()
    (root / ".trinity-runtime" / "producer.dsse").write_bytes(b"{}")
    commit_all(root, "producer partial")
    (root / ".audit" / gate.DISPOSITION_ENVELOPE).write_bytes(b"{}")
    commit_all(root, "assembled envelope")
    assert gate_codes(root) == set()
    (root / "README.md").write_text("subject moved\n", encoding="utf-8")
    commit_all(root, "subject change")
    assert gate_codes(root) == {gate.GATE_PREFLIGHT_MISSING}


def test_mint_record_keeps_bytes_that_still_describe_head(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    path = gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    first = path.read_bytes()
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW + timedelta(hours=1))
    assert path.read_bytes() == first
    commit_all(root, "seal")
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW + timedelta(hours=2))
    assert path.read_bytes() == first
    gate.mint_record(root, instrument="CRUCIBLE", findings=[error("X")], now=NOW)
    assert path.read_bytes() != first
    assert gate.load_record(path)["disposition"] == gate.HOLD
    (root / "README.md").write_text("subject moved\n", encoding="utf-8")
    commit_all(root, "subject change")
    gate.mint_record(root, instrument="CRUCIBLE", findings=[error("X")], now=NOW)
    assert gate.load_record(path)["tree_sha"] == git(["rev-parse", "HEAD"], cwd=root)


def test_mint_record_does_not_clobber_a_promoted_record_still_bound_to_head(
    tmp_path: Path,
) -> None:
    root = make_parent(tmp_path)
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate bundle")
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    commit_all(root, "mint")
    path = gate.promote(
        root,
        instrument="CRUCIBLE",
        approver="approver@trinity.test",
        now=NOW,
        trust_dir=write_release_trust(tmp_path),
    )
    promoted = path.read_bytes()
    commit_all(root, "seal promoted record")
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW + timedelta(minutes=30))
    assert path.read_bytes() == promoted
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW + timedelta(hours=2))
    assert path.read_bytes() != promoted
    assert gate.load_record(path)["disposition"] == gate.SHIP_ELIGIBLE
    gate.mint_record(root, instrument="CRUCIBLE", findings=[error("X")], now=NOW)
    assert path.read_bytes() != promoted
    assert gate.load_record(path)["disposition"] == gate.HOLD


# ---- CLI -----------------------------------------------------------------------------


def test_cli_exit_codes_follow_the_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_parent(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gate, "run_gate", lambda _root: [])
    monkeypatch.setattr(gate, "record_sentinel", lambda *_a, **_k: [])
    code = gate.main(
        [
            "gate.py",
            "./parent",
            "--instrument",
            "CRUCIBLE",
            "--moment",
            "report",
            "--run-id",
            "r1",
            "--json",
        ]
    )
    assert code == gate.EXIT_CLEAN
    payload = json.loads(capsys.readouterr().out)
    assert payload["ceiling"] == gate.SHIP_ELIGIBLE
    assert payload["receipt"].startswith("./")
    assert payload["record"].startswith("./")
    assert str(tmp_path) not in json.dumps(payload)
    assert (root / ".audit" / gate.DISPOSITION_RECORD).is_file()
    assert (root / ".audit" / gate.RECEIPT_DIR / "r1.json").is_file()

    monkeypatch.setattr(gate, "run_gate", lambda _root: [error("X")])
    assert (
        gate.main(["gate.py", "./parent", "--instrument", "FORGE", "--moment", "preflight"])
        == gate.EXIT_HOLD
    )
    monkeypatch.setattr(gate, "run_gate", lambda _root: [error("SAB_DIRTY_TREE")])
    assert (
        gate.main(["gate.py", "./parent", "--instrument", "ENGRAM", "--moment", "preflight"])
        == gate.EXIT_BLOCK
    )


def test_cli_check_mode_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_parent(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gate, "run_gate", lambda _root: [])
    monkeypatch.setattr(gate, "record_sentinel", lambda *_a, **_k: [])
    code = gate.main(
        [
            "gate.py",
            "./parent",
            "--instrument",
            "CRUCIBLE",
            "--moment",
            "report",
            "--check",
            "--json",
        ]
    )
    assert code == gate.EXIT_CLEAN
    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt"] is None and payload["record"] is None
    assert not (root / ".audit").exists()


def test_cli_records_sabotage_through_the_sentinel(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    recorded = gate.record_sentinel(root, [error("SAB_DISPOSITION_UNBOUND")], run_id="r1", ci=False)
    assert recorded == ["SAB_DISPOSITION_FORGED"]
    assert (root / ".sentinel" / "attempts.jsonl").is_file()


def test_local_moments_of_one_pass_share_one_attempt_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    monkeypatch.setattr(gate, "run_gate", lambda _root: [error("SAB_DISPOSITION_UNBOUND")])
    head = git(["rev-parse", "HEAD"], cwd=root)
    assert gate.local_run_id(root) == f"local-{head}"
    for moment in ("preflight", "report", "report"):
        argv = ["gate.py", "./parent", "--instrument", "ENGRAM", "--moment", moment]
        if moment == "report":
            argv.append("--check")
        assert gate.main(argv) == gate.EXIT_BLOCK
    sentinel = load_harness("sentinel")
    attempts, defect = sentinel.read_ledger(root / ".sentinel" / "attempts.jsonl")
    assert defect is None
    assert {item.run_id for item in attempts} == {f"local-{head}"}
    assert [str(item.code) for item in attempts] == ["SAB_DISPOSITION_FORGED"]
    alerts, alert_defect = sentinel.read_alerts(root / ".sentinel" / "alerts.jsonl")
    assert alert_defect is None
    assert alerts == []
    assert gate.local_run_id(tmp_path / "not-a-repo").startswith("local-")


def test_cli_promote_refuses_and_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_parent(tmp_path)
    monkeypatch.chdir(tmp_path)
    gate.mint_record(root, instrument="CRUCIBLE", findings=[error("X")], now=NOW)
    code = gate.main(
        ["gate.py", "promote", "./parent", "--instrument", "CRUCIBLE", "--approver", "a@b.test"]
    )
    assert code == gate.EXIT_BLOCK
    assert "promote refused" in capsys.readouterr().err


@pytest.mark.parametrize("root", ["parent", "/parent", "~/parent", ".\\parent", "./../parent"])
def test_gate_cli_rejects_noncanonical_root_without_leaking_host_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    root: str,
) -> None:
    make_parent(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = gate.main(["gate.py", root, "--instrument", "CRUCIBLE", "--moment", "report", "--check"])
    assert code == gate.EXIT_USAGE
    output = capsys.readouterr()
    assert str(tmp_path) not in output.out + output.err


def test_real_gate_run_on_a_bare_parent_holds_or_blocks(tmp_path: Path) -> None:
    """The unmocked path: a parent with nothing scaffolded cannot be SHIP_ELIGIBLE."""

    root = make_parent(tmp_path)
    findings = gate.run_gate(root)
    assert findings
    assert gate.ceiling(findings) in {gate.HOLD, gate.BLOCK}


# ---- install ------------------------------------------------------------------------


READBACK = {
    "required_status_checks": {"strict": True, "contexts": ["release-gate", "gate"]},
    "enforce_admins": {"enabled": True},
    "allow_force_pushes": {"enabled": False},
}


RULESET_RULES = [
    {
        "type": "required_status_checks",
        "ruleset_source_type": "Organization",
        "ruleset_source": "EtharaOrion",
        "ruleset_id": 42,
        "parameters": {
            "required_status_checks": [{"context": "gate", "integration_id": 1}],
            "strict_required_status_checks_policy": True,
        },
    },
    {
        "type": "non_fast_forward",
        "ruleset_source_type": "Organization",
        "ruleset_source": "EtharaOrion",
        "ruleset_id": 42,
    },
]
RULESET = {"id": 42, "enforcement": "active", "bypass_actors": []}


def fake_gh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    put_status: int = 0,
    existing: str = "none",
    bypass_actors: int = 0,
) -> Path:
    """A `gh` on PATH that records every argv and answers with canned JSON, no network.

    ``existing`` names what already protects ``main`` before any PUT: ``none`` answers the
    classic endpoint with 404 and the rules endpoint with an empty array, ``classic`` answers
    the classic endpoint with a conforming read-back, and ``ruleset`` answers the rules
    endpoint with an active organization ruleset. A successful PUT makes classic protection
    readable afterwards.
    """

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "gh.log"
    marker = tmp_path / "gh.put-ok"
    put_marker = f'{marker}-$(printf %s "$4" | tr / -)'
    get_marker = f'{marker}-$(printf %s "$2" | tr / -)'
    ruleset = dict(RULESET, bypass_actors=[{"actor_id": 1}] * bypass_actors)
    rules = RULESET_RULES if existing == "ruleset" else []
    script = bin_dir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        f'printf \'%s\\n\' "$*" >> "{log}"\n'
        'case "$*" in\n'
        '  "auth status") exit 0 ;;\n'
        f'  api\\ -X\\ PUT*) cat >/dev/null; [ {put_status} -eq 0 ] && touch "{put_marker}" '
        '&& echo "{}" && exit 0; '
        'echo "HTTP 403: Resource not accessible by integration" >&2; exit 1 ;;\n'
        f"  api\\ repos/*/rules/branches/*) printf '%s' '{json.dumps(rules)}'; exit 0 ;;\n"
        f"  api\\ orgs/*/rulesets/*|api\\ repos/*/rulesets/*) printf '%s' '{json.dumps(ruleset)}'; "
        "exit 0 ;;\n"
        "  api\\ repos/*/branches/*/protection) "
        f'if [ "{existing}" = classic ] || [ -e "{get_marker}" ]; '
        f"then printf '%s' '{json.dumps(READBACK)}'; exit 0; fi; "
        'echo "HTTP 404: Not Found" >&2; exit 1 ;;\n'
        "esac\n"
        "exit 1\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return log


def github_parent(tmp_path: Path) -> Path:
    root = make_parent(tmp_path)
    git(["remote", "add", "origin", "git@github.com:EtharaOrion/argos.git"], cwd=root)
    (root / ".gitmodules").write_text(
        '[submodule "memory"]\n\tpath = .memory\n'
        "\turl = git@github.com:EtharaOrion/argos-memory.git\n"
        '[submodule "samples"]\n\tpath = samples\n'
        "\turl = org-302118749@github.com:EtharaOrion/argos-samples.git\n"
        '[submodule "delivery"]\n\tpath = delivery\n'
        "\turl = git@github.com:EtharaOrion/argos-delivery.git\n"
        '[submodule "harness"]\n\tpath = harness\n'
        "\turl = git@github.com:EtharaOrion/argos-harness.git\n"
        '[submodule "staging"]\n\tpath = staging\n'
        "\turl = git@github.com:EtharaOrion/argos-staging.git\n"
        '[submodule "trinity"]\n\tpath = trinity\n'
        "\turl = git@github.com:EtharaOrion/trinity.git\n",
        encoding="utf-8",
    )
    commit_all(root, "modules")
    return root


def test_parse_github_repo_accepts_every_remote_spelling() -> None:
    for url in (
        "git@github.com:EtharaOrion/argos.git",
        "https://github.com/EtharaOrion/argos",
        "org-302118749@github.com:EtharaOrion/argos.git",
        "ssh://git@github.com/EtharaOrion/argos.git/",
    ):
        assert gate.parse_github_repo(url) == "EtharaOrion/argos", url
    assert gate.parse_github_repo("https://gitlab.com/x/y.git") is None


def test_gated_submodule_repos_skips_the_trinity_root(tmp_path: Path) -> None:
    root = github_parent(tmp_path)
    assert gate.gated_submodule_repos(root) == [
        "EtharaOrion/argos-memory",
        "EtharaOrion/argos-samples",
        "EtharaOrion/argos-delivery",
        "EtharaOrion/argos-harness",
        "EtharaOrion/argos-staging",
    ]


def test_gated_submodules_cover_every_roster_root_and_staging(tmp_path: Path) -> None:
    root = tmp_path
    (root / ".gitmodules").write_text(
        '[submodule "samples"]\n\tpath = samples\n'
        "\turl = git@github.com:EtharaOrion/argos-samples.git\n"
        '[submodule "delivery"]\n\tpath = delivery\n'
        "\turl = git@github.com:EtharaOrion/argos-delivery.git\n"
        '[submodule "harness"]\n\tpath = harness\n'
        "\turl = git@github.com:EtharaOrion/argos-harness.git\n"
        '[submodule "staging"]\n\tpath = staging\n'
        "\turl = git@github.com:EtharaOrion/argos-staging.git\n"
        '[submodule "memory"]\n\tpath = .memory\n'
        "\turl = git@github.com:EtharaOrion/argos-memory.git\n"
        '[submodule "trinity"]\n\tpath = trinity\n'
        "\turl = git@github.com:EtharaOrion/trinity.git\n",
        encoding="utf-8",
    )
    repos = gate.gated_submodule_repos(root)
    assert repos == [
        "EtharaOrion/argos-memory",
        "EtharaOrion/argos-samples",
        "EtharaOrion/argos-delivery",
        "EtharaOrion/argos-harness",
        "EtharaOrion/argos-staging",
    ]


def test_block_codes_are_closed() -> None:
    blocking = {code for code in layout.LAYOUT_CODES if gate.is_block_code(code)}
    assert blocking == layout.BLOCKING_CODES
    for code in layout.BLOCKING_CODES:
        assert gate.ceiling([error(code)]) == gate.BLOCK
    assert gate.ceiling([error(layout.PARENT_LAYOUT_PLAIN_DIRECTORY)]) == gate.HOLD


def test_gated_submodules_are_derived_from_the_roster() -> None:
    assert gate.GATED_SUBMODULES == layout.PROTECTED_ROOTS


@bite("shared.md:A37")
def test_install_is_idempotent_and_protects_parent_and_submodules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    log = fake_gh(tmp_path, monkeypatch)
    first = gate.install(root, now=NOW)
    doors = {relative for relative, _ in gate.door_templates()}
    hooks = {relative for relative, _ in gate.hook_templates()}
    assert set(first.written) == {
        ".github/workflows/sentinel.yaml",
        gate.ATTRIBUTES_PATH,
        gate.CODEOWNERS_PATH,
        *hooks,
        *doors,
    }
    assert doors == set(integrity.FRONT_DOOR_CONTRACTS)
    for relative, template in gate.door_templates():
        assert (root / relative).read_bytes() == template.read_bytes()
    assert integrity.check_front_doors(str(root)) == []
    assert first.hooks_path_set
    assert git(["config", "core.hooksPath"], cwd=root) == ".githooks"
    assert os.access(root / gate.HOOK_PATH, os.X_OK)
    for name in gate.WORKFLOW_TEMPLATES:
        assert (root / ".github/workflows" / name).read_bytes() == (
            gate.TEMPLATES_DIR / name
        ).read_bytes()
    owners = (root / gate.CODEOWNERS_PATH).read_text(encoding="utf-8").splitlines()
    assert owners == [
        "/.github/ @EtharaOrion/research",
        "/trinity @EtharaOrion/research",
        "/.gitmodules @EtharaOrion/research",
    ]
    assert first.repos == (
        "EtharaOrion/argos",
        "EtharaOrion/argos-memory",
        "EtharaOrion/argos-samples",
        "EtharaOrion/argos-delivery",
        "EtharaOrion/argos-harness",
        "EtharaOrion/argos-staging",
    )
    assert first.protected == first.repos and first.unprotected == ()
    calls = log.read_text(encoding="utf-8").splitlines()
    assert [call for call in calls if call.startswith("api -X PUT ")] == [
        f"api -X PUT repos/{repo}/branches/main/protection --input -" for repo in first.repos
    ]
    for repo in first.repos:
        receipt = json.loads(
            (
                root / gate.INSTALL_DIR / gate.PROTECTION_DIR / f"{repo.replace('/', '-')}.json"
            ).read_text(encoding="utf-8")
        )
        assert receipt["applied"] is True
        assert receipt["read_back_contexts"] == ["release-gate", "gate"]
    assert first.complete
    assert gate.check_gates_installed(str(root)) == []

    second = gate.install(root, now=NOW + timedelta(days=1))
    assert second.written == ()
    assert set(second.unchanged) == set(first.written)
    assert (root / gate.CODEOWNERS_PATH).read_text(encoding="utf-8").splitlines() == owners
    receipts = {
        repo: (
            root / gate.INSTALL_DIR / gate.PROTECTION_DIR / f"{repo.replace('/', '-')}.json"
        ).read_bytes()
        for repo in first.repos
    }
    gate.install(root, now=NOW + timedelta(days=2))
    for repo, before in receipts.items():
        path = root / gate.INSTALL_DIR / gate.PROTECTION_DIR / f"{repo.replace('/', '-')}.json"
        assert path.read_bytes() == before, "an unchanged protection receipt is never rewritten"


def test_install_merges_codeowners_without_clobbering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    (root / ".github").mkdir()
    (root / gate.CODEOWNERS_PATH).write_text("/docs/ @EtharaOrion/writers\n", encoding="utf-8")
    monkeypatch.setenv(gate.CODEOWNERS_TEAM_ENV, "@Example/security")
    gate.install(root, now=NOW)
    lines = (root / gate.CODEOWNERS_PATH).read_text(encoding="utf-8").splitlines()
    assert lines == [
        "/docs/ @EtharaOrion/writers",
        "/.github/ @Example/security",
        "/trinity @Example/security",
        "/.gitmodules @Example/security",
    ]


def test_install_dry_run_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    report = gate.install(root, dry_run=True)
    assert set(report.written) >= {gate.HOOK_PATH, gate.CODEOWNERS_PATH}
    assert not (root / ".github").exists() and not (root / gate.INSTALL_DIR).exists()
    assert not report.complete


@bite("shared.md:A38")
def test_refused_protection_writes_a_false_receipt_and_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch, put_status=1)
    monkeypatch.chdir(tmp_path)
    code = gate.main(["gate.py", "install", "./parent"])
    assert code == gate.EXIT_INSTALL_INCOMPLETE
    receipt = json.loads(
        (root / gate.INSTALL_DIR / gate.PROTECTION_DIR / "EtharaOrion-argos.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["applied"] is False and receipt["reason"].startswith("gh-refused")
    findings = gate.check_gates_installed(str(root))
    assert {item.code for item in findings} == {gate.GATE_PROTECTION_MISSING}
    assert all(item.severity is Severity.ERROR for item in findings)
    assert gate.ceiling(findings) == gate.HOLD


def test_absent_gh_is_a_receipt_not_a_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = github_parent(tmp_path)
    # PATH has to carry git and never gh. Exposing git's own directory drags in a sibling
    # gh wherever the two share one prefix, which is /usr/bin on the CI runner, so link git
    # into a directory this test owns and expose that alone.
    git_only = tmp_path / "git-only-bin"
    git_only.mkdir()
    (git_only / "git").symlink_to(Path(shutil.which("git") or "/usr/bin/git"))
    monkeypatch.setenv("PATH", str(git_only))
    assert shutil.which("gh") is None
    report = gate.install(root, now=NOW)
    assert [reason.startswith("gh-absent") for _repo, reason in report.unprotected] == [True] * 6
    assert {item.code for item in gate.check_gates_installed(str(root))} == {
        gate.GATE_PROTECTION_MISSING
    }


def test_missing_workflow_and_codeowners_are_refused(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    found = {item.code: item.severity for item in gate.check_gates_installed(str(root))}
    assert found == {
        gate.GATE_WORKFLOW_MISSING: Severity.ERROR,
        gate.GATE_HOOK_MISSING: Severity.ERROR,
        gate.GATE_ATTRIBUTES_MISSING: Severity.ERROR,
        gate.GATE_MERGE_DRIVER_MISSING: Severity.ERROR,
        gate.GATE_CODEOWNERS_MISSING: Severity.ERROR,
        gate.GATE_PROTECTION_UNVERIFIED: Severity.ADVISORY,
    }


def test_drifted_workflow_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    gate.install(root, now=NOW)
    target = root / ".github/workflows/sentinel.yaml"
    target.write_text(target.read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")
    codes_found = {item.code for item in gate.check_gates_installed(str(root))}
    assert codes_found == {gate.GATE_WORKFLOW_MISSING}


def test_receipt_lacking_a_required_check_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    gate.install(root, now=NOW)
    receipt = root / gate.INSTALL_DIR / gate.PROTECTION_DIR / "EtharaOrion-argos.json"
    value = json.loads(receipt.read_text(encoding="utf-8"))
    value["read_back_contexts"] = []
    receipt.write_text(json.dumps(value), encoding="utf-8")
    findings = gate.check_gates_installed(str(root))
    assert [item.code for item in findings] == [gate.GATE_PROTECTION_MISSING]
    assert "gate" in findings[0].message


def test_preflight_runs_install_and_check_mode_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gate, "run_gate", lambda _root: [])
    monkeypatch.setattr(gate, "record_sentinel", lambda *_a, **_k: [])
    code = gate.main(
        [
            "gate.py",
            "./parent",
            "--instrument",
            "FORGE",
            "--moment",
            "preflight",
            "--check",
            "--json",
        ]
    )
    assert code == gate.EXIT_CLEAN
    assert json.loads(capsys.readouterr().out)["install"] is None
    assert not (root / ".github").exists()
    code = gate.main(
        ["gate.py", "./parent", "--instrument", "FORGE", "--moment", "preflight", "--json"]
    )
    assert code == gate.EXIT_CLEAN
    payload = json.loads(capsys.readouterr().out)
    assert payload["install"]["protected"] == [
        "EtharaOrion/argos",
        "EtharaOrion/argos-memory",
        "EtharaOrion/argos-samples",
        "EtharaOrion/argos-delivery",
        "EtharaOrion/argos-harness",
        "EtharaOrion/argos-staging",
    ]
    assert not (root / ".github/workflows/release-gate.yaml").exists()
    assert (root / ".github/workflows/sentinel.yaml").is_file()
    assert (root / gate.HOOK_PATH).is_file()


def test_preflight_cannot_be_eligible_when_protection_installation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch, put_status=1)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gate, "run_gate", lambda _root: [])
    monkeypatch.setattr(gate, "record_sentinel", lambda *_a, **_k: [])
    code = gate.main(["gate.py", "./parent", "--instrument", "FORGE", "--moment", "preflight"])
    assert code == gate.EXIT_HOLD


def test_release_workflow_template_is_external_governance_only() -> None:
    text = (gate.TEMPLATES_DIR / "release-gate.yaml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "candidate_repository_id:" in text
    assert "TRINITY_EXPECTED_PARENT_REPOSITORY_ID" in text
    assert "TRINITY_EXPECTED_SAMPLES_REPOSITORY_ID" in text
    assert "TRINITY_EXPECTED_PROJECT_ID" in text
    assert "TRINITY_VERIFIER_SHA" in text
    assert "TRINITY_RELEASE_TRUST_DIR" in text
    assert "environment: release-governance" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "python3 -I candidate-data" not in text
    assert 'runpy.run_path("./verifier/tools/release.py"' in text
    assert "github.workspace" not in text
    assert "TRINITY_RELEASE_TRUST_DIR: ./release-trust" in text
    assert "path: ./candidate-data" in text


def test_isolated_verifier_bootstrap_imports_only_pinned_checkout(tmp_path: Path) -> None:
    root = gate.TEMPLATES_DIR.parent
    script = (
        'import runpy,sys; sys.path.insert(0,"verifier"); '
        'sys.argv=["release.py",*sys.argv[1:]]; '
        'runpy.run_path("verifier/tools/release.py",run_name="__main__")'
    )
    workspace = tmp_path
    (workspace / "verifier").symlink_to(root, target_is_directory=True)
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=workspace,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 2
    assert "ModuleNotFoundError" not in completed.stderr
    assert "usage: release.py" in completed.stderr


@bite("shared.md:A41")
def test_hook_template_invokes_gate_with_canonical_root_and_never_recommends_bypass(
    tmp_path: Path,
) -> None:
    hook = (gate.TEMPLATES_DIR / gate.HOOK_TEMPLATE).read_text(encoding="utf-8")
    command = next(
        line for line in hook.splitlines() if "tools/gate.py" in line and "python3" in line
    )
    assert " ./ " in command, "the hook must pass the canonical './' root the gate demands"
    assert " . " not in command
    for forbidden in ("--no-verify", "--force", "hooksPath false", "core.hooksPath ''"):
        assert forbidden not in hook
    assert "--no-verify" not in (gate.__doc__ or "")
    workspace = tmp_path
    (workspace / "trinity").symlink_to(gate.TEMPLATES_DIR.parent, target_is_directory=True)
    for root_argument in (".", "./"):
        completed = subprocess.run(
            [
                sys.executable,
                "trinity/tools/gate.py",
                root_argument,
                "--instrument",
                "CRUCIBLE",
                "--moment",
                "report",
                "--check",
                "--json",
            ],
            cwd=workspace,
            capture_output=True,
            check=False,
            text=True,
        )
        refused = "must start with './'" in completed.stderr
        assert refused == (root_argument == "."), (root_argument, completed.stderr)
    assert completed.returncode != gate.EXIT_USAGE, completed.stderr


def _receipt(root: Path, repo: str = "EtharaOrion/argos") -> dict[str, object]:
    path = root / gate.INSTALL_DIR / gate.PROTECTION_DIR / f"{repo.replace('/', '-')}.json"
    parsed: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return parsed


@bite("shared.md:A45")
def test_ruleset_protection_is_read_back_without_a_write_and_clears_the_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    log = fake_gh(tmp_path, monkeypatch, put_status=1, existing="ruleset")
    report = gate.install(root, now=NOW)
    assert report.complete and report.unprotected == ()
    calls = log.read_text(encoding="utf-8").splitlines()
    assert not any(call.startswith("api -X PUT") for call in calls)
    assert "api repos/EtharaOrion/argos/rules/branches/main" in calls
    assert "api orgs/EtharaOrion/rulesets/42" in calls
    receipt = _receipt(root)
    assert receipt["applied"] is True
    assert receipt["reason"] == "in force: rulesets read back"
    assert receipt["read_back_contexts"] == ["gate"]
    assert gate.check_gates_installed(str(root)) == []


def test_protection_never_requires_a_pull_request_review() -> None:
    body = gate.protection_body()

    assert body["required_pull_request_reviews"] is None
    assert body["required_status_checks"] == {
        "strict": True,
        "contexts": list(gate.REQUIRED_CHECKS),
    }
    assert body["allow_force_pushes"] is False and body["enforce_admins"] is True
    assert not any(rule["type"] == "pull_request" for rule in RULESET_RULES)


def test_classic_protection_already_in_force_needs_no_admin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    log = fake_gh(tmp_path, monkeypatch, put_status=1, existing="classic")
    report = gate.install(root, now=NOW)
    assert report.complete
    assert not any(call.startswith("api -X PUT") for call in log.read_text("utf-8").splitlines())
    assert _receipt(root)["reason"] == "in force: classic protection read back"
    assert gate.check_gates_installed(str(root)) == []


def test_ruleset_with_bypass_actors_does_not_count_as_protection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch, put_status=1, existing="ruleset", bypass_actors=1)
    report = gate.install(root, now=NOW)
    assert not report.complete
    receipt = _receipt(root)
    assert receipt["applied"] is False
    assert "ruleset 42 lets 1 actor(s) bypass it" in str(receipt["reason"])
    assert {item.code for item in gate.check_gates_installed(str(root))} == {
        gate.GATE_PROTECTION_MISSING
    }


def test_refusal_with_nothing_in_force_names_the_administrator_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch, put_status=1)
    gate.install(root, now=NOW)
    reason = str(_receipt(root)["reason"])
    assert reason.startswith("gh-refused: HTTP 403")
    assert "nothing already in force" in reason
    assert "an administrator applies classic protection or an active ruleset" in reason


# ---- run-scoped qualification: the closure, not HEAD -----------------------------------


RUN_A = "forge-ada-20260917t120000z-aaaaaa"
RUN_B = "forge-bob-20260917t120000z-bbbbbb"


def scoped_run(root: Path, run_id: str, token: str = "HOLD:PILOT_REQUIRED") -> Path:
    directory = Path(runs.open_run(root, "FORGE", run_id, principal=run_id.split("-")[1], now=NOW))
    (directory / "contract.yaml").write_text("archetype: AR1\n", encoding="utf-8")
    gate.write_receipt(
        root, instrument="FORGE", moment="report", findings=[error("X")], run_id=run_id, run=run_id
    )
    gate.mint_record(root, instrument="FORGE", findings=[error("X")], now=NOW, run=run_id)
    (directory / "report.md").write_text(
        f"## Executive summary\n\nx\n\n## Disposition\n\n{token}\n\n## Findings\n\nx\n\n"
        "## Coverage gaps\n\nx\n\n## Escalations\n\nx\n\n## Flag legend\n\nx\n",
        encoding="utf-8",
    )
    return directory


def test_scoped_receipt_survives_a_foreign_commit_and_dies_on_a_closure_change(
    tmp_path: Path,
) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    (root / "requirements").mkdir()
    (root / "requirements" / "grant.md").write_text("budget: 1\n", encoding="utf-8")
    scoped_run(root, RUN_A)
    commit_all(root, "run a")
    assert gate_codes(root) == set()

    scoped_run(root, RUN_B)
    (root / "unrelated.md").write_text("someone else\n", encoding="utf-8")
    commit_all(root, "run b lands beside run a")
    assert gate_codes(root) == set()

    (root / "requirements" / "grant.md").write_text("budget: 2\n", encoding="utf-8")
    commit_all(root, "the grant changed under both runs")
    findings = gate.check_gate_receipts(str(root))

    assert {item.code for item in findings} == {gate.GATE_PREFLIGHT_MISSING}
    assert len(findings) == 2
    assert all("binding its subject closure" in item.message for item in findings)


def test_scoped_record_is_kept_while_the_closure_holds_and_reminted_when_it_moves(
    tmp_path: Path,
) -> None:
    root = make_parent(tmp_path)
    directory = scoped_run(root, RUN_A)
    record = directory / gate.DISPOSITION_RECORD
    before = record.read_bytes()

    gate.mint_record(
        root, instrument="FORGE", findings=[error("X")], now=NOW + timedelta(days=1), run=RUN_A
    )
    assert record.read_bytes() == before

    (directory / "contract.yaml").write_text("archetype: AR2\n", encoding="utf-8")
    gate.mint_record(
        root, instrument="FORGE", findings=[error("X")], now=NOW + timedelta(days=1), run=RUN_A
    )
    after = json.loads(record.read_text("utf-8"))

    assert record.read_bytes() != before
    assert set(after) == gate.QUALIFICATION_FIELDS
    assert after["schema"] == gate.QUALIFICATION_SCHEMA
    assert after["run_id"] == RUN_A and after["disposition"] == gate.HOLD


def test_scoped_run_report_cannot_state_above_its_record(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    scoped_run(root, RUN_A, token="SHIP_ELIGIBLE")

    findings = gate.check_gate_receipts(str(root))

    assert {item.code for item in findings} == {gate.GATE_DISPOSITION_MISMATCH}


def test_rendered_root_report_needs_no_head_bound_receipt(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    scoped_run(root, RUN_A)
    reports.render_root_reports(root)
    commit_all(root, "rendered")

    assert gate_codes(root) == set()
    assert (root / "EDICT.md").read_text("utf-8").startswith(gate.GENERATED_BANNER)


def test_cli_run_opens_the_namespace_and_writes_scoped_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path)
    write_hook(root)
    fake_gh(tmp_path, monkeypatch)
    monkeypatch.chdir(root.parent)
    monkeypatch.setattr(gate, "run_gate", lambda _root: [error("X")])
    monkeypatch.setenv("GITHUB_ACTOR", "ada")

    assert (
        gate.main(
            ["gate.py", "./parent", "--instrument", "FORGE", "--moment", "report", "--run", RUN_A]
        )
        == gate.EXIT_HOLD
    )

    directory = root / ".seed" / "runs" / RUN_A
    assert json.loads((directory / "run.json").read_text("utf-8"))["principal"] == "ada"
    receipts = sorted((directory / gate.RECEIPT_DIR).glob("report-*.json"))
    assert [path.name for path in receipts] == ["report-0001.json"]
    receipt = json.loads(receipts[0].read_text("utf-8"))
    assert receipt["schema_version"] == gate.RUN_RECEIPT_SCHEMA
    assert receipt["subject_digest"] == subject.subject_digest(root, "FORGE", RUN_A)
    assert gate.load_qualification(directory / gate.DISPOSITION_RECORD) is not None
    assert not (root / ".seed" / gate.DISPOSITION_RECORD).exists()
    monkeypatch.setenv("GITHUB_ACTOR", "bob")
    assert (
        gate.main(
            ["gate.py", "./parent", "--instrument", "FORGE", "--moment", "report", "--run", RUN_A]
        )
        == gate.EXIT_USAGE
    )


# ---- frozen release candidates -----------------------------------------------------------


@bite("shared.md:A64")
def test_promote_into_a_release_candidate_leaves_the_qualified_record_and_later_main_alone(
    tmp_path: Path,
) -> None:
    root = make_parent(tmp_path)
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate bundle")
    gate.mint_record(root, instrument="CRUCIBLE", findings=[], now=NOW)
    head = commit_all(root, "mint")
    trust = write_release_trust(tmp_path)

    path = gate.promote(
        root,
        instrument="CRUCIBLE",
        approver="approver@trinity.test",
        now=NOW,
        trust_dir=trust,
        release="2026.09-rc1",
    )

    assert path == root / ".audit" / "releases" / "2026.09-rc1" / "disposition.json"
    record = json.loads(path.read_bytes())
    assert record["disposition"] == gate.SHIP and record["candidate_commit"] == head
    qualified = json.loads((root / ".audit" / "disposition.json").read_bytes())
    assert qualified["disposition"] == gate.SHIP_ELIGIBLE
    instruction = gate.signing_instruction(root, "CRUCIBLE", "2026.09-rc1")
    assert ".audit/releases/2026.09-rc1/disposition.json.dsse" in instruction
    assert "--release 2026.09-rc1" in instruction
    (root / "unrelated.md").write_text("main moved on\n", encoding="utf-8")
    commit_all(root, "later work on main")
    assert json.loads(path.read_bytes()) == record
    with pytest.raises(gate.GateError, match="release id"):
        gate.release_dir(root, "CRUCIBLE", "../escape")
    with pytest.raises(gate.GateError, match="release id"):
        gate.release_dir(root, "CRUCIBLE", "Bad")


def test_release_candidate_promotion_does_not_overwrite_another_candidate(tmp_path: Path) -> None:
    root = make_parent(tmp_path)
    bundle = root / "samples" / TEST_UUID
    bundle.mkdir(parents=True)
    (bundle / "task.toml").write_text("schema_version = '1.4'\n", encoding="utf-8")
    commit_all(root, "candidate bundle")
    gate.mint_record(root, instrument="FORGE", findings=[], now=NOW)
    commit_all(root, "mint")
    trust = write_release_trust(tmp_path)
    first = gate.promote(
        root, instrument="FORGE", approver="a@x", now=NOW, trust_dir=trust, release="rc-1"
    )
    before = first.read_bytes()

    second = gate.promote(
        root, instrument="FORGE", approver="b@x", now=NOW, trust_dir=trust, release="rc-2"
    )

    assert first.read_bytes() == before
    assert second != first and json.loads(second.read_bytes())["approver"] == "b@x"
