"""Both-halves fixtures for the release gate in ``tools/release.py``."""

from __future__ import annotations

# allow: SIZE_OK - Retain the existing receipt fixture corpus for the scoped F1 binding tests.
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from tools import release, release_evidence
from tools._findings import Finding
from tools.attest.backend import VerificationResult
from tools.attest.canonical import CanonicalizationError, JSONValue, canonicalize, parse_json
from tools.attest.dsse import Envelope, Signature, parse_envelope
from tools.bundle_identity import release_snapshot_digest
from tools.forensics.family_models import PopulationStanding
from tools.forensics.ledger import ledger_bytes
from tools.release_evidence import (
    CORE_CONTROL_IDS,
    DISPOSITION_PAYLOAD_TYPES,
    DISPOSITION_SCHEMA,
    ORACLE_PAYLOAD_TYPE,
    POLICY_SCHEMA,
)

from tests.bite_shared.registration import bite
from tests.fidelity_binding_fixtures import fidelity_ledger
from tests.parent_fixtures import write_bundle, write_clean_parent

UUID_ONE = "1213efa9-10ca-4f0e-bb27-2f6012454212"
UUID_TWO = "394d9d5c-357d-56c2-81e5-e0a2d32ab101"
UUIDS = [UUID_ONE, UUID_TWO]
NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
AUTHOR_NAME = "Operator"
AUTHOR_EMAIL = "operator@trinity.test"
IMAGE = "sha256:" + "ab" * 32
HARNESS = "sha256:" + "cd" * 32
VERIFIER_SHA = "3" * 40
PROJECT_ID = "project-17"
REPOSITORY_ID = "424242"
PRODUCER = "producer@trinity.test"
APPROVER = "approver@trinity.test"
OPERATOR = "runner@trinity.test"
CLEAN_FIDELITY_LEDGER = ledger_bytes(
    fidelity_ledger(dict.fromkeys((f"r{i}" for i in range(8)), "conforming"))
)
GIT_ENV = {
    "GIT_AUTHOR_NAME": AUTHOR_NAME,
    "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
    "GIT_COMMITTER_NAME": AUTHOR_NAME,
    "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
}


def git(argv: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *argv],
        cwd=cwd,
        capture_output=True,
        check=False,
        env={**os.environ, **GIT_ENV},
        shell=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return completed.stdout


def report(disposition: str, extra: str = "") -> str:
    return (
        "## Executive summary\n\nSummary.\n\n## Disposition\n\n"
        f"{disposition}\n\n## Findings\n\n{extra}\n\n## Coverage gaps\n\nNone.\n\n"
        "## Escalations\n\nNone.\n\n## Flag legend\n\nNone.\n"
    )


class ReceiptBackend:
    keyid_scheme = "test:v1"

    def sign(self, payload: bytes, *, key_path: Path) -> bytes:
        del payload
        return key_path.read_bytes()

    def verify(
        self, payload: bytes, *, signature_path: Path, **_kwargs: object
    ) -> VerificationResult:
        del payload
        return VerificationResult.success(signature_path.read_bytes().decode("utf-8"))


BACKEND = ReceiptBackend()


def envelope(payload_type: str, payload: bytes, *principals: str) -> bytes:
    return Envelope(
        payload_type=payload_type,
        payload=payload,
        signatures=tuple(
            Signature(item.encode("utf-8"), BACKEND.keyid_scheme) for item in principals
        ),
    ).to_json()


def coverage_controls(
    uuid: str, *, omitted: str | None = None, failed: str | None = None
) -> list[dict[str, object]]:
    rows = [
        {
            "control_id": control_id,
            "status": "fail" if control_id == failed else "pass",
            "evidence_digest": "sha256:"
            + hashlib.sha256(
                CLEAN_FIDELITY_LEDGER if control_id == "execution_fidelity" else control_id.encode()
            ).hexdigest(),
            "task_uuid": uuid,
            "verifier_sha": VERIFIER_SHA,
        }
        for control_id in sorted(CORE_CONTROL_IDS)
        if control_id != omitted
    ]
    closure = hashlib.sha256(canonicalize(rows)).hexdigest()
    return [{**row, "closure_digest": closure} for row in rows]


def receipt(root: Path, uuid: str, **overrides: object) -> Path:
    path = root / release.RECEIPT_DIR / f"{uuid}.json.dsse"
    path.parent.mkdir(parents=True, exist_ok=True)
    body: dict[str, object] = {
        "schema": release.RECEIPT_SCHEMA,
        "task_uuid": uuid,
        "bundle_digest": release.bundle_digest(root / "samples" / uuid),
        "started_at": "2026-09-16T10:00:00Z",
        "completed_at": "2026-09-16T11:00:00Z",
        "expires_at": "2026-09-17T12:00:00Z",
        "harbor_version": "0.23.0",
        "image_digest": IMAGE,
        "harness_digest": HARNESS,
        "reward": 1.0,
        "full_reward": 1.0,
        "score": 1.0,
        "runs": [
            {
                "run_id": f"run-{index}",
                "reward": 1.0,
                "score": 1.0,
                "no_op": {"executed": True, "verdict": "rejected", "score": 0.0},
                "known_wrong": {"executed": True, "verdict": "rejected", "score": 0.0},
            }
            for index in range(2)
        ],
        "controls": coverage_controls(uuid),
    }
    body.update(overrides)
    try:
        payload = canonicalize(body)
    except CanonicalizationError:
        payload = json.dumps(body).encode("utf-8")
    path.write_bytes(envelope(ORACLE_PAYLOAD_TYPE, payload, OPERATOR))
    return path


def write_trust(root: Path) -> Path:
    trust = root.parent / "release-trust"
    trust.mkdir(exist_ok=True)
    (trust / "roots.yaml").write_text(
        json.dumps(
            {
                "version": 7,
                "expires": "2027-09-01T00:00:00Z",
                "roles": [
                    {"name": "execution_operator", "threshold": 1},
                    {"name": "gate_approver", "threshold": 1},
                ],
                "principals": [
                    {"name": PRODUCER, "roles": ["execution_operator"]},
                    {"name": APPROVER, "roles": ["gate_approver"]},
                    {"name": OPERATOR, "roles": ["execution_operator"]},
                ],
                "revocations": [],
            }
        ),
        encoding="utf-8",
    )
    (trust / "allowed_signers").write_text("test policy\n", encoding="utf-8")
    (trust / "trusted-root-version").write_text("7\n", encoding="utf-8")
    (trust / "policy.json").write_text(
        json.dumps(
            {
                "schema": POLICY_SCHEMA,
                "trusted_root_version": 7,
                "oracle": {
                    "harbor_version": "0.23.0",
                    "image_digest": IMAGE,
                    "harness_digest": HARNESS,
                    "full_reward": 1.0,
                    "score_min": 0.0,
                    "score_max": 1.0,
                    "negative_score_max": 0.0,
                    "stability_runs": 2,
                    "max_age_seconds": 86400,
                    "required_controls": sorted(CORE_CONTROL_IDS),
                    "positive_control_ids": ["build_assets_harness"],
                    "non_applicable_controls": [],
                },
                "project_id": PROJECT_ID,
                "repository_id": REPOSITORY_ID,
                "verifier_sha": VERIFIER_SHA,
                "disposition_max_age_seconds": 86400,
            }
        ),
        encoding="utf-8",
    )
    return trust


def write_dispositions(root: Path, candidate_commit: str, release_id: str | None = None) -> None:
    digest = release.bundle_set_digest(root / "samples", release.exported_uuids(root / "samples"))
    snapshot = release_snapshot_digest(root / "samples", release.exported_uuids(root / "samples"))
    for instrument, harness in (("FORGE", ".seed"), ("CRUCIBLE", ".audit")):
        directory = root / harness
        if release_id is not None:
            directory = directory / "releases" / release_id
        directory.mkdir(exist_ok=True, parents=True)
        body = json.dumps(
            {
                "schema": DISPOSITION_SCHEMA,
                "instrument": instrument,
                "disposition": "SHIP",
                "project_id": PROJECT_ID,
                "repository_id": REPOSITORY_ID,
                "snapshot_digest": snapshot,
                "bundle_set_digest": digest,
                "candidate_commit": candidate_commit,
                "verifier_sha": VERIFIER_SHA,
                "issued_at": "2026-09-16T11:30:00Z",
                "expires_at": "2026-09-17T11:30:00Z",
                "producer": PRODUCER,
                "approver": APPROVER,
            },
            sort_keys=True,
        ).encode("utf-8")
        (directory / "disposition.json").write_bytes(body)
        (directory / "disposition.json.dsse").write_bytes(
            envelope(DISPOSITION_PAYLOAD_TYPES[instrument], body, PRODUCER, APPROVER)
        )


def use_group_dispositions(
    root: Path,
    *,
    producer_signers: tuple[str, ...],
    approver_signers: tuple[str, ...],
    producer_threshold: int = 1,
    revoked: str | None = None,
) -> None:
    roots_path = root.parent / "release-trust" / "roots.yaml"
    trust = json.loads(roots_path.read_text(encoding="utf-8"))
    trust["roles"] = [
        {"name": "execution_operator", "threshold": 1},
        {"name": "gate_producer", "threshold": producer_threshold},
        {"name": "gate_approver", "threshold": 1},
    ]
    group_principals = [
        *({"name": item, "roles": ["gate_producer"]} for item in producer_signers),
        *({"name": item, "roles": ["gate_approver"]} for item in approver_signers),
    ]
    trust["principals"] = [
        {"name": OPERATOR, "roles": ["execution_operator"]},
        *group_principals,
    ]
    trust["revocations"] = (
        [] if revoked is None else [{"principal": revoked, "revoked_at": "2026-09-16T00:00:00Z"}]
    )
    roots_path.write_text(json.dumps(trust), encoding="utf-8")
    digest = release.bundle_set_digest(root / "samples", release.exported_uuids(root / "samples"))
    snapshot = release_snapshot_digest(root / "samples", release.exported_uuids(root / "samples"))
    candidate_commit = git(["rev-parse", "HEAD^"], cwd=root).strip()
    for instrument, harness in (("FORGE", ".seed"), ("CRUCIBLE", ".audit")):
        body = canonicalize(
            {
                "schema": release_evidence.GROUP_DISPOSITION_SCHEMA,
                "instrument": instrument,
                "disposition": "SHIP",
                "project_id": PROJECT_ID,
                "repository_id": REPOSITORY_ID,
                "snapshot_digest": snapshot,
                "bundle_set_digest": digest,
                "candidate_commit": candidate_commit,
                "verifier_sha": VERIFIER_SHA,
                "issued_at": "2026-09-16T11:30:00Z",
                "expires_at": "2026-09-17T11:30:00Z",
                "producer_role": "gate_producer",
                "approver_role": "gate_approver",
            }
        )
        directory = root / harness
        (directory / "disposition.json").write_bytes(body)
        (directory / "disposition.json.dsse").write_bytes(
            envelope(
                release_evidence.GROUP_DISPOSITION_PAYLOAD_TYPES[instrument],
                body,
                *producer_signers,
                *approver_signers,
            )
        )
    commit_all(root, "group release evidence")


def rollout(root: Path, uuid: str, body: dict[str, object], name: str = "result.json") -> Path:
    run = root / "samples" / uuid / "trajectories" / "opus-5" / "run_1"
    run.mkdir(parents=True, exist_ok=True)
    path = run / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def write_reports(root: Path) -> None:
    samples = root / "samples"
    digest = release.bundle_set_digest(samples, release.exported_uuids(samples))
    (root / "VERDICT.md").write_text(
        report(f"🟢 **SHIP** bundle-set digest `{digest}`"), encoding="utf-8"
    )
    rows = "\n".join(f"| {uuid} | SHIP |" for uuid in release.exported_uuids(samples))
    (root / "EDICT.md").write_text(report("SHIP for the batch.", rows), encoding="utf-8")


def commit_all(root: Path, message: str = "release candidate") -> None:
    git(["add", "-A"], cwd=root)
    git(["commit", "-q", "-m", message], cwd=root)


def reseal(root: Path) -> None:
    commit_all(root, "updated candidate")
    write_dispositions(root, git(["rev-parse", "HEAD"], cwd=root).strip())
    commit_all(root, "seal updated release evidence")


def build_parent(root: Path) -> None:
    def setup(root: Path) -> None:
        git(["init", "-q", "--initial-branch=main"], cwd=root)
        (root / ".audit").mkdir(exist_ok=True)
        (root / ".audit/fidelity.yaml").write_bytes(CLEAN_FIDELITY_LEDGER)
        for uuid in UUIDS:
            write_bundle(root, uuid)
            rollout(root, uuid, {"reward": 1.0, "verifier_result": {"status": "scored"}})
            receipt(root, uuid)
        (root / "samples" / release.REWARD_SCHEMA_NAME).write_text(
            json.dumps(
                {
                    "schema": release.REWARD_SCHEMA,
                    "authoritative": {"path": "result.json", "key": "reward"},
                }
            ),
            encoding="utf-8",
        )
        write_reports(root)
        commit_all(root)
        write_dispositions(root, git(["rev-parse", "HEAD"], cwd=root).strip())
        commit_all(root, "seal release evidence")

    write_clean_parent(root, setup)


def waiver(root: Path, **overrides: object) -> Path:
    body = {"claimed": "acceptance", **overrides}
    path = root / release.WAIVER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def codes(findings: list[Finding]) -> set[str]:
    return {item.code for item in findings}


def fidelity_controls(raw: bytes) -> list[dict[str, object]]:
    rows = coverage_controls(UUID_ONE)
    for row in rows:
        del row["closure_digest"]
        if row["control_id"] == "execution_fidelity":
            row["evidence_digest"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    closure = hashlib.sha256(canonicalize(rows)).hexdigest()
    return [{**row, "closure_digest": closure} for row in rows]


def test_receipt_fidelity_digest_must_match_ledger(parent: Path) -> None:
    # Given: a signed receipt naming a different ledger digest.
    raw = ledger_bytes(fidelity_ledger(dict.fromkeys((f"r{i}" for i in range(8)), "conforming")))
    path = receipt(parent, UUID_ONE, controls=fidelity_controls(b"different ledger"))
    trust = release_evidence.load_release_trust(parent, parent.parent / "release-trust")
    # When: verifying against the supplied auditor ledger.
    with pytest.raises(
        release_evidence.ReleaseEvidenceError, match="ORACLE_FIDELITY_DIGEST_MISMATCH"
    ):
        release_evidence.verify_oracle_receipt(
            path,
            trust=trust,
            task_uuid=UUID_ONE,
            bundle_digest=release.bundle_digest(parent / "samples" / UUID_ONE),
            evaluation_time=NOW,
            backend=BACKEND,
            ledger=raw,
        )
    # Then: a syntactically valid digest cannot substitute for the bound ledger.


@pytest.mark.parametrize("status", ["nonconforming", "indeterminate", "conforming"])
def test_receipt_fidelity_refused_when_ledger_holds_nonconforming(
    parent: Path, status: str
) -> None:
    # Given: a signed passing outcome with the exact digest, even for an affected row.
    raw = ledger_bytes(fidelity_ledger(dict.fromkeys((f"r{i}" for i in range(8)), status)))
    path = receipt(parent, UUID_ONE, controls=fidelity_controls(raw))
    trust = release_evidence.load_release_trust(parent, parent.parent / "release-trust")
    # When: verifying the digest and ledger standing together.
    if status == "conforming":
        result = release_evidence.verify_oracle_receipt(
            path,
            trust=trust,
            task_uuid=UUID_ONE,
            bundle_digest=release.bundle_digest(parent / "samples" / UUID_ONE),
            evaluation_time=NOW,
            backend=BACKEND,
            ledger=raw,
        )
        # Then: the clean half remains accepted.
        assert result.authorized_principals == (OPERATOR,)
    else:
        with pytest.raises(release_evidence.ReleaseEvidenceError, match="ORACLE_FIDELITY_REFUSED"):
            release_evidence.verify_oracle_receipt(
                path,
                trust=trust,
                task_uuid=UUID_ONE,
                bundle_digest=release.bundle_digest(parent / "samples" / UUID_ONE),
                evaluation_time=NOW,
                backend=BACKEND,
                ledger=raw,
            )
        # Then: a matching digest does not turn HOLD evidence into a passing outcome.


@pytest.mark.parametrize(
    "population",
    [
        PopulationStanding(("extra",), (), True),
        PopulationStanding((), ("missing",), True),
        PopulationStanding((), (), False),
    ],
)
def test_receipt_fidelity_refuses_blocked_population(
    parent: Path,
    population: PopulationStanding,
) -> None:
    # Given: a BLOCK-capable population failure despite clean trace signals.
    ledger = fidelity_ledger(dict.fromkeys((f"r{i}" for i in range(8)), "conforming"))
    blocked = replace(
        ledger,
        population=population,
        rows=tuple(replace(row, population=population) for row in ledger.rows),
    )
    raw = ledger_bytes(blocked)
    path = receipt(parent, UUID_ONE, controls=fidelity_controls(raw))
    trust = release_evidence.load_release_trust(parent, parent.parent / "release-trust")
    # When: a passing receipt binds that exact canonical ledger.
    with pytest.raises(release_evidence.ReleaseEvidenceError, match="ORACLE_FIDELITY_REFUSED"):
        release_evidence.verify_oracle_receipt(
            path,
            trust=trust,
            task_uuid=UUID_ONE,
            bundle_digest=release.bundle_digest(parent / "samples" / UUID_ONE),
            evaluation_time=NOW,
            backend=BACKEND,
            ledger=raw,
        )
    # Then: population failure is never permitted by a matching digest.


@pytest.fixture
def parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "parent"
    build_parent(root)
    write_trust(root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TRINITY_RELEASE_TRUST_DIR", "./release-trust")
    monkeypatch.setattr(release_evidence, "SshKeygenBackend", lambda: BACKEND)
    return root


def gate(root: Path, **kwargs: object) -> list[Finding]:
    export = kwargs.get("export")
    return release.check_release(
        str(root), NOW, export=str(export) if export else None, _signature_backend=BACKEND
    )


# ---- clean half ----


def test_clean_parent_passes(parent: Path) -> None:
    assert gate(parent) == []
    assert gate(parent) == []


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "unreadable",
        "symlink",
        "malformed",
        "mismatch",
        "blocked",
        "nonconforming",
        "clean",
    ],
)
def test_release_snapshot_requires_fidelity_ledger(parent: Path, mode: str) -> None:
    # Given: a sealed release whose passing receipt may contradict its auditor ledger.
    path = parent / ".audit/fidelity.yaml"
    match mode:
        case "missing":
            path.unlink()
        case "unreadable":
            path.unlink()
            path.mkdir()
            (path / "not-a-ledger").write_bytes(b"x")
        case "symlink":
            path.rename(parent / "elsewhere.yaml")
            path.symlink_to(parent / "elsewhere.yaml")
        case "malformed":
            path.write_bytes(b"{}\n")
        case "mismatch":
            receipt(parent, UUID_ONE, controls=fidelity_controls(b"different ledger"))
        case "blocked" | "nonconforming":
            ledger = fidelity_ledger(
                dict.fromkeys(
                    (f"r{i}" for i in range(8)),
                    "nonconforming" if mode == "nonconforming" else "conforming",
                )
            )
            if mode == "blocked":
                population = PopulationStanding(("extra",), (), True)
                ledger = replace(
                    ledger,
                    population=population,
                    rows=tuple(replace(row, population=population) for row in ledger.rows),
                )
            raw = ledger_bytes(ledger)
            path.write_bytes(raw)
            receipt(parent, UUID_ONE, controls=fidelity_controls(raw))
        case "clean":
            pass
        case _:
            pytest.fail("unknown fixture mode")
    if mode != "clean":
        reseal(parent)
    # When: checking the production release entry point, not the receipt helper.
    findings = gate(parent)
    # Then: only a matching, readable, clean ledger authorizes release.
    if mode == "clean":
        assert findings == []
    else:
        assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
        assert any(UUID_ONE in item.path for item in findings)


def test_release_number_rejects_giant_integers() -> None:
    assert release._number(10**4301) is None
    assert release._number(-(10**4301)) is None


def test_release_refuses_absent_external_trust(
    parent: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TRINITY_RELEASE_TRUST_DIR")
    assert release.TRUST_INVALID in codes(gate(parent))


def test_release_refuses_candidate_installed_trust(
    parent: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_trust = parent / ".memory" / "release-trust"
    shutil.copytree(parent.parent / "release-trust", candidate_trust)
    commit_all(parent)
    monkeypatch.setenv("TRINITY_RELEASE_TRUST_DIR", "./parent/.memory/release-trust")
    assert release.TRUST_INVALID in codes(gate(parent))


def test_release_refuses_symlinked_external_trust(
    parent: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    link = parent.parent / "trust-link"
    link.symlink_to(parent.parent / "release-trust", target_is_directory=True)
    monkeypatch.setenv("TRINITY_RELEASE_TRUST_DIR", "./trust-link")
    assert release.TRUST_INVALID in codes(gate(parent))


def test_release_trust_string_is_project_relative_but_resolved_path_is_internal_api(
    parent: Path,
) -> None:
    trust = parent.parent / "release-trust"
    with pytest.raises(release_evidence.ReleaseEvidenceError, match=r"start with './'"):
        release_evidence.load_release_trust(parent, str(trust), project_root=parent.parent)
    assert (
        release_evidence.load_release_trust(parent, trust).directory
        == release_evidence.load_release_trust(
            parent, "./release-trust", project_root=parent.parent
        ).directory
    )


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("oracle", "max_age_seconds", 2**53 - 1),
        ("oracle", "stability_runs", 1001),
        (None, "disposition_max_age_seconds", 30 * 24 * 60 * 60 + 1),
    ],
)
def test_external_policy_rejects_unbounded_counts_and_durations(
    parent: Path, section: str | None, field: str, value: int
) -> None:
    path = parent.parent / "release-trust" / "policy.json"
    policy = json.loads(path.read_text(encoding="utf-8"))
    target = policy if section is None else policy[section]
    target[field] = value
    path.write_text(json.dumps(policy), encoding="utf-8")

    findings = gate(parent)

    assert codes(findings) == {release.TRUST_INVALID}
    assert field in findings[0].message


@pytest.mark.parametrize(
    ("argument", "value"),
    [
        ("expected_project_id", "wrong-project"),
        ("expected_repository_id", "999999"),
        ("expected_verifier_sha", "f" * 40),
    ],
)
def test_release_policy_must_match_governance_identity_pins(
    parent: Path, argument: str, value: str
) -> None:
    if argument == "expected_project_id":
        findings = release.check_release(
            str(parent), NOW, _signature_backend=BACKEND, expected_project_id=value
        )
    elif argument == "expected_repository_id":
        findings = release.check_release(
            str(parent), NOW, _signature_backend=BACKEND, expected_repository_id=value
        )
    else:
        findings = release.check_release(
            str(parent), NOW, _signature_backend=BACKEND, expected_verifier_sha=value
        )
    assert codes(findings) == {release.TRUST_INVALID}
    assert "governance pin" in findings[0].message


def test_parent_check_entry_point_matches_registry_signature(parent: Path) -> None:
    assert release.check_release_gate(str(parent), NOW) == []
    assert [name for name, _ in release.CHECKS] == ["check_release_gate"]


def test_ship_inferred_is_accepted(parent: Path) -> None:
    samples = parent / "samples"
    digest = release.bundle_set_digest(samples, UUIDS)
    (parent / "VERDICT.md").write_text(report(f"SHIP:INFERRED {digest}"), encoding="utf-8")
    reseal(parent)
    assert gate(parent) == []


def test_signed_dispositions_are_authoritative(parent: Path) -> None:
    (parent / ".audit" / "disposition.json.dsse").unlink()
    commit_all(parent)
    assert codes(gate(parent)) == {release.DISPOSITION_INVALID}


def test_group_takeover_accepts_authorized_b_and_c_with_original_a_absent(parent: Path) -> None:
    use_group_dispositions(
        parent,
        producer_signers=("producer-b@trinity.test",),
        approver_signers=("approver-c@trinity.test",),
    )
    assert gate(parent) == []


def test_group_threshold_counts_distinct_authorized_identities(parent: Path) -> None:
    use_group_dispositions(
        parent,
        producer_signers=("producer-a@trinity.test",),
        approver_signers=("approver-c@trinity.test",),
        producer_threshold=2,
    )
    for instrument, harness in (("FORGE", ".seed"), ("CRUCIBLE", ".audit")):
        payload = (parent / harness / "disposition.json").read_bytes()
        (parent / harness / "disposition.json.dsse").write_bytes(
            envelope(
                release_evidence.GROUP_DISPOSITION_PAYLOAD_TYPES[instrument],
                payload,
                "producer-a@trinity.test",
                "producer-a@trinity.test",
                "approver-c@trinity.test",
            )
        )
    commit_all(parent, "repeat one producer identity")
    findings = gate(parent)
    assert codes(findings) == {release.DISPOSITION_INVALID}
    assert all("threshold_not_met" in item.message for item in findings)


def test_group_revoked_signer_and_outsider_fail_closed(parent: Path) -> None:
    producer = "producer-b@trinity.test"
    use_group_dispositions(
        parent,
        producer_signers=(producer,),
        approver_signers=("approver-c@trinity.test",),
        revoked=producer,
    )
    findings = gate(parent)
    assert codes(findings) == {release.DISPOSITION_INVALID}
    assert all("revoked" in item.message for item in findings)

    use_group_dispositions(
        parent,
        producer_signers=("outsider@trinity.test",),
        approver_signers=("approver-c@trinity.test",),
    )
    roots = parent.parent / "release-trust" / "roots.yaml"
    trust = json.loads(roots.read_text(encoding="utf-8"))
    for principal in trust["principals"]:
        if principal["name"] == "outsider@trinity.test":
            principal["name"] = "enrolled-producer@trinity.test"
    roots.write_text(json.dumps(trust), encoding="utf-8")
    findings = gate(parent)
    assert codes(findings) == {release.DISPOSITION_INVALID}
    assert all("not_bound" in item.message for item in findings)


def test_group_expired_signer_fails_closed(parent: Path) -> None:
    producer = "producer-b@trinity.test"
    use_group_dispositions(
        parent,
        producer_signers=(producer,),
        approver_signers=("approver-c@trinity.test",),
    )
    roots = parent.parent / "release-trust" / "roots.yaml"
    trust = json.loads(roots.read_text(encoding="utf-8"))
    for principal in trust["principals"]:
        if principal["name"] == producer:
            principal["expires"] = "2026-09-16T00:00:00Z"
    roots.write_text(json.dumps(trust), encoding="utf-8")
    findings = gate(parent)
    assert codes(findings) == {release.DISPOSITION_INVALID}
    assert all("expired" in item.message for item in findings)


def test_group_producer_cannot_supply_own_approval(parent: Path) -> None:
    identity = "dual-role@trinity.test"
    use_group_dispositions(
        parent,
        producer_signers=(identity,),
        approver_signers=(identity,),
    )
    roots = parent.parent / "release-trust" / "roots.yaml"
    trust = json.loads(roots.read_text(encoding="utf-8"))
    trust["principals"] = [
        {"name": OPERATOR, "roles": ["execution_operator"]},
        {"name": identity, "roles": ["gate_producer", "gate_approver"]},
    ]
    roots.write_text(json.dumps(trust), encoding="utf-8")
    findings = gate(parent)
    assert codes(findings) == {release.DISPOSITION_INVALID}
    assert all("self_approval" in item.message for item in findings)


def test_disposition_wrong_bundle_or_self_approval_refused(parent: Path) -> None:
    path = parent / ".seed" / "disposition.json"
    value = json.loads(path.read_bytes())
    value["bundle_set_digest"] = "f" * 64
    value["approver"] = PRODUCER
    payload = json.dumps(value, sort_keys=True).encode("utf-8")
    path.write_bytes(payload)
    (parent / ".seed" / "disposition.json.dsse").write_bytes(
        envelope(DISPOSITION_PAYLOAD_TYPES["FORGE"], payload, PRODUCER)
    )
    commit_all(parent)
    assert codes(gate(parent)) == {release.DISPOSITION_INVALID}


def test_disposition_requires_authenticated_producer(parent: Path) -> None:
    envelope_path = parent / ".seed" / "disposition.json.dsse"
    payload = (parent / ".seed" / "disposition.json").read_bytes()
    envelope_path.write_bytes(envelope(DISPOSITION_PAYLOAD_TYPES["FORGE"], payload, APPROVER))
    commit_all(parent)
    findings = gate(parent)
    assert codes(findings) == {release.DISPOSITION_INVALID}
    assert "producer is not an authenticated" in findings[0].message


def test_copied_forge_envelope_cannot_approve_crucible(parent: Path) -> None:
    (parent / ".audit" / "disposition.json.dsse").write_bytes(
        (parent / ".seed" / "disposition.json.dsse").read_bytes()
    )
    commit_all(parent)
    assert codes(gate(parent)) == {release.DISPOSITION_INVALID}


def test_named_unauthorized_approver_is_refused_despite_authorized_cosigner(parent: Path) -> None:
    other = "other-approver@trinity.test"
    roots = parent.parent / "release-trust" / "roots.yaml"
    trust = json.loads(roots.read_text(encoding="utf-8"))
    trust["principals"].append({"name": other, "roles": ["gate_approver"]})
    roots.write_text(json.dumps(trust), encoding="utf-8")
    record_path = parent / ".audit" / "disposition.json"
    record = json.loads(record_path.read_bytes())
    record["approver"] = "not-authorized@trinity.test"
    payload = json.dumps(record, sort_keys=True).encode("utf-8")
    record_path.write_bytes(payload)
    (parent / ".audit" / "disposition.json.dsse").write_bytes(
        envelope(DISPOSITION_PAYLOAD_TYPES["CRUCIBLE"], payload, PRODUCER, other)
    )
    commit_all(parent)
    findings = gate(parent)
    assert codes(findings) == {release.DISPOSITION_INVALID}
    assert "named approver is not an authorized gate_approver" in findings[0].message


def test_arbitrary_candidate_snapshot_reference_is_refused(parent: Path) -> None:
    path = parent / ".seed" / "disposition.json"
    record = json.loads(path.read_bytes())
    record["candidate_commit"] = "f" * 40
    payload = json.dumps(record, sort_keys=True).encode("utf-8")
    path.write_bytes(payload)
    (parent / ".seed" / "disposition.json.dsse").write_bytes(
        envelope(DISPOSITION_PAYLOAD_TYPES["FORGE"], payload, PRODUCER, APPROVER)
    )
    commit_all(parent)
    assert codes(gate(parent)) == {release.DISPOSITION_INVALID}


def test_post_approval_shared_schema_change_invalidates_dispositions(parent: Path) -> None:
    schema = parent / "samples" / release.REWARD_SCHEMA_NAME
    schema.write_text(schema.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    commit_all(parent)
    assert release.DISPOSITION_INVALID in codes(gate(parent))


def test_post_approval_unclassified_directory_invalidates_dispositions(parent: Path) -> None:
    extra = parent / "samples" / "not-a-task"
    extra.mkdir()
    (extra / "payload.txt").write_text("smuggled\n", encoding="utf-8")
    commit_all(parent)
    assert codes(gate(parent)) == {release.EXPORT_MISMATCH}


# ---- dirty tree ----


def test_dirty_tree_refused(parent: Path) -> None:
    (parent / "scratch.txt").write_text("late edit", encoding="utf-8")
    assert codes(gate(parent)) == {release.DIRTY_TREE}


@pytest.mark.parametrize(
    "malicious_config",
    [
        "[core]\n\tfsmonitor = {command}\n",
        "[core]\n\thooksPath = {command}\n",
        "[diff]\n\texternal = {command}\n",
        '[diff "payload"]\n\ttextconv = {command}\n',
        '[filter "payload"]\n\tclean = {command}\n',
        '[includeIf "gitdir:**"]\n\tpath = {command}\n',
    ],
)
def test_release_rejects_executable_candidate_git_config_without_execution(
    parent: Path, tmp_path: Path, malicious_config: str
) -> None:
    marker = tmp_path / "candidate-git-command-executed"
    command = tmp_path / "touch-marker"
    command.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
    command.chmod(0o755)
    config = parent / ".git" / "config"
    config.write_text(
        config.read_text(encoding="utf-8") + malicious_config.format(command=command),
        encoding="utf-8",
    )
    findings = gate(parent)
    assert codes(findings) == {release.DIRTY_TREE}
    assert "inert data" in findings[0].message
    assert not marker.exists()


def test_release_ignores_inherited_global_git_commands(
    parent: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "global-git-command-executed"
    command = tmp_path / "touch-marker"
    command.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
    command.chmod(0o755)
    hostile_global = tmp_path / "global.gitconfig"
    hostile_global.write_text(f"[core]\n\tfsmonitor = {command}\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile_global))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "diff.external")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(command))
    assert gate(parent) == []
    assert not marker.exists()


def test_non_repository_refused(tmp_path: Path) -> None:
    root = tmp_path / "loose"
    root.mkdir()
    assert codes(gate(root)) >= {release.DIRTY_TREE}


def test_empty_release_population_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "empty-parent"
    root.mkdir()
    git(["init", "-q", "--initial-branch=main"], cwd=root)
    (root / "samples").mkdir()
    (root / "README.md").write_text("empty\n", encoding="utf-8")
    commit_all(root)
    assert release.POPULATION_EMPTY in codes(
        release.check_release(str(root), NOW, _signature_backend=BACKEND)
    )


# ---- verdict ----


@pytest.mark.parametrize("line", ["🟡 **HOLD**", "🔴 BLOCK.", "`HOLD:PILOT_REQUIRED`", "SHIPPED"])
@bite("shared.md:A9")
def test_verdict_not_ship_refused(parent: Path, line: str) -> None:
    (parent / "VERDICT.md").write_text(report(line), encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.VERDICT_NOT_SHIP}


def test_verdict_without_disposition_section_refused(parent: Path) -> None:
    (parent / "VERDICT.md").write_text("## Executive summary\n\nSHIP\n", encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.VERDICT_NOT_SHIP}


def test_symlinked_root_report_is_refused_without_following_it(parent: Path) -> None:
    outside = parent.parent / "outside-verdict.md"
    outside.write_text(report("SHIP"), encoding="utf-8")
    (parent / "VERDICT.md").unlink()
    (parent / "VERDICT.md").symlink_to(outside)
    reseal(parent)
    assert codes(gate(parent)) == {release.VERDICT_NOT_SHIP}


@bite("shared.md:A10")
def test_ship_without_digest_is_unbound(parent: Path) -> None:
    (parent / "VERDICT.md").write_text(report("🟢 **SHIP**"), encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.DISPOSITION_UNBOUND}


def test_ship_bound_to_other_bytes_is_unbound(parent: Path) -> None:
    (parent / "samples" / UUID_ONE / "instruction.md").write_text("edited\n", encoding="utf-8")
    receipt(parent, UUID_ONE)
    reseal(parent)
    assert codes(gate(parent)) == {release.DISPOSITION_UNBOUND}


# ---- edict ----


def test_edict_batch_hold_refused(parent: Path) -> None:
    rows = "\n".join(f"| {uuid} | SHIP |" for uuid in UUIDS)
    (parent / "EDICT.md").write_text(report("`HOLD:PILOT_REQUIRED`", rows), encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.EDICT_NOT_SHIP}


def test_edict_missing_slot_row_refused(parent: Path) -> None:
    rows = f"| {UUID_ONE} | SHIP |\n| {UUID_TWO} | BLOCK:INVALID_TASK |"
    (parent / "EDICT.md").write_text(report("SHIP", rows), encoding="utf-8")
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.EDICT_NOT_SHIP}
    assert UUID_TWO in findings[0].message


def test_edict_shipped_word_is_not_a_ship_token(parent: Path) -> None:
    rows = f"| {UUID_ONE} | SHIPPED |\n| {UUID_TWO} | SHIP |"
    (parent / "EDICT.md").write_text(report("SHIP", rows), encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.EDICT_NOT_SHIP}


# ---- export ----


def test_export_includes_github_and_refuses_extra_workflow(parent: Path, tmp_path: Path) -> None:
    export = tmp_path / "export"
    shutil.copytree(parent / "samples", export)
    (export / ".github").mkdir()
    (export / ".github" / "release-gate.yaml").write_text("workflow\n", encoding="utf-8")
    assert codes(gate(parent, export=export)) == {release.EXPORT_MISMATCH}


def test_export_with_extra_bundle_refused(parent: Path, tmp_path: Path) -> None:
    export = tmp_path / "export"
    shutil.copytree(parent / "samples", export)
    extra = export / "9e0c7d3a-1c2b-4d5e-8f90-1234567890ab"
    extra.mkdir()
    (extra / "task.toml").write_text("copied from delivery_final\n", encoding="utf-8")
    findings = gate(parent, export=export)
    assert codes(findings) == {release.EXPORT_MISMATCH}
    assert "9e0c7d3a" in findings[0].message


@bite("shared.md:A11")
def test_export_with_changed_byte_refused(parent: Path, tmp_path: Path) -> None:
    export = tmp_path / "export"
    shutil.copytree(parent / "samples", export)
    (export / UUID_ONE / "instruction.md").write_text("instruction.md\n\n", encoding="utf-8")
    assert codes(gate(parent, export=export)) == {release.EXPORT_MISMATCH}


def test_samples_submodule_pointer_must_be_audited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    upstream = tmp_path / "samples-upstream"
    upstream.mkdir()
    git(["init", "-q", "--initial-branch=main"], cwd=upstream)
    for uuid in UUIDS:
        write_bundle(upstream, uuid, lane_root=".")
    git(["add", "-A"], cwd=upstream)
    git(["commit", "-q", "-m", "bundles"], cwd=upstream)

    root = tmp_path / "parent"

    def setup(root: Path) -> None:
        git(["init", "-q", "--initial-branch=main"], cwd=root)
        (root / "samples").rmdir()
        (root / ".audit").mkdir(exist_ok=True)
        (root / ".audit/fidelity.yaml").write_bytes(CLEAN_FIDELITY_LEDGER)
        git(
            [
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                "-q",
                str(upstream),
                "samples",
            ],
            cwd=root,
        )
        for uuid in UUIDS:
            rollout(root, uuid, {"reward": 1.0, "verifier_result": {"status": "scored"}})
            receipt(root, uuid)
        (root / "samples" / release.REWARD_SCHEMA_NAME).write_text(
            json.dumps(
                {
                    "schema": release.REWARD_SCHEMA,
                    "authoritative": {"path": "result.json", "key": "reward"},
                }
            ),
            encoding="utf-8",
        )
        git(["add", "-A"], cwd=root / "samples")
        git(["commit", "-q", "-m", "rollouts"], cwd=root / "samples")
        write_reports(root)
        commit_all(root)
        write_dispositions(root, git(["rev-parse", "HEAD"], cwd=root).strip())
        commit_all(root, "seal release evidence")

    write_clean_parent(root, setup)
    write_trust(root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TRINITY_RELEASE_TRUST_DIR", "./release-trust")
    pointer = git(["rev-parse", "HEAD"], cwd=root / "samples").strip()
    findings = release.check_release(str(root), NOW, _signature_backend=BACKEND)
    assert codes(findings) == {release.EXPORT_MISMATCH}
    assert pointer[:12] in findings[0].message

    text = (root / "VERDICT.md").read_text(encoding="utf-8")
    (root / "VERDICT.md").write_text(
        text.replace("## Findings", f"audited samples commit {pointer}\n\n## Findings"),
        encoding="utf-8",
    )
    reseal(root)
    assert release.check_release(str(root), NOW, _signature_backend=BACKEND) == []


# ---- oracle receipts ----


@pytest.fixture
def oracle_v3_receipt(parent: Path) -> Path:
    """Retain the old generated receipt only as refused input."""
    return receipt(
        parent,
        UUID_ONE,
        schema="trinity.oracle-run/v3",
        started_at="2026-09-16T09:00:00Z",
        controls=coverage_controls(UUID_ONE, omitted="execution_fidelity"),
    )


@pytest.fixture
def release_policy_v2(parent: Path) -> Path:
    """Retain the old generated policy only as refused input."""
    path = parent.parent / "release-trust" / "policy.json"
    policy = parse_json(path.read_bytes())
    assert isinstance(policy, dict)
    oracle = policy["oracle"]
    assert isinstance(oracle, dict)
    policy["schema"] = "trinity.release-policy/v2"
    oracle["required_controls"] = list[JSONValue](sorted(CORE_CONTROL_IDS - {"execution_fidelity"}))
    path.write_bytes(canonicalize(policy))
    return path


def test_core_controls_include_execution_fidelity() -> None:
    # Given the mandatory control registry; When its membership is inspected;
    # Then fidelity is the sixth member.
    assert "execution_fidelity" in CORE_CONTROL_IDS
    assert len(CORE_CONTROL_IDS) == 6


def test_policy_omitting_execution_fidelity_is_refused(parent: Path) -> None:
    # Given a current policy carrying only the original five controls.
    path = parent.parent / "release-trust" / "policy.json"
    policy = parse_json(path.read_bytes())
    assert isinstance(policy, dict)
    oracle = policy["oracle"]
    assert isinstance(oracle, dict)
    oracle["required_controls"] = list[JSONValue](sorted(CORE_CONTROL_IDS - {"execution_fidelity"}))
    path.write_bytes(canonicalize(policy))
    # When the release gate loads it.
    findings = gate(parent)
    # Then the inherited missing-core difference names fidelity.
    assert codes(findings) == {release.TRUST_INVALID}
    assert "required_controls omits core controls: execution_fidelity" in findings[0].message


def test_execution_fidelity_can_never_be_non_applicable(parent: Path) -> None:
    # Given every core control and an extension as individually proposed exemptions.
    path = parent.parent / "release-trust" / "policy.json"
    policy = parse_json(path.read_bytes())
    assert isinstance(policy, dict)
    oracle = policy["oracle"]
    assert isinstance(oracle, dict)
    candidates = CORE_CONTROL_IDS | {"execution_fidelity", "extension_control"}
    oracle["required_controls"] = list[JSONValue](sorted(candidates))
    accepted: set[str] = set()
    # When each exemption is loaded with a different, applicable positive control.
    for control in sorted(candidates):
        oracle["positive_control_ids"] = [sorted(candidates - {control})[0]]
        oracle["non_applicable_controls"] = [control]
        path.write_bytes(canonicalize(policy))
        try:
            release_evidence.load_release_trust(parent, path.parent)
        except release_evidence.ReleaseEvidenceError as exc:
            assert str(exc) == "only the trusted judge control may be non-applicable"
        else:
            accepted.add(control)
    # Then the behavioral allowance is exactly the judge, never fidelity.
    assert accepted == {release_evidence.JUDGE_CONTROL_ID}


def test_receipt_without_execution_fidelity_outcome_is_refused(parent: Path) -> None:
    # Given an otherwise valid receipt with a recomputed five-control closure.
    receipt(
        parent,
        UUID_ONE,
        controls=coverage_controls(UUID_ONE, omitted="execution_fidelity"),
        started_at="2026-09-16T09:00:00Z",
    )
    reseal(parent)
    # When the release gate verifies coverage.
    findings = gate(parent)
    # Then the existing one-outcome-per-control rule, not a special fidelity rule, refuses it.
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert findings[0].message == "control outcomes must cover every required control exactly once"


def test_oracle_v3_receipt_is_refused(parent: Path, oracle_v3_receipt: Path) -> None:
    # Given the retained v3 receipt fixture sealed into an otherwise valid candidate.
    assert oracle_v3_receipt.is_file()
    reseal(parent)
    # When the gate verifies the old receipt.
    findings = gate(parent)
    # Then refusal names both the observed and required versions.
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert "ORACLE_SCHEMA_UNSUPPORTED" in findings[0].message
    assert "trinity.oracle-run/v3" in findings[0].message
    assert "trinity.oracle-run/v4" in findings[0].message


def test_release_policy_v2_is_refused(parent: Path, release_policy_v2: Path) -> None:
    # Given the retained v2 policy fixture.
    assert release_policy_v2.is_file()
    # When the gate loads external trust.
    findings = gate(parent)
    # Then refusal names both versions before evaluating its old control roster.
    assert codes(findings) == {release.TRUST_INVALID}
    assert "RELEASE_POLICY_SCHEMA_UNSUPPORTED" in findings[0].message
    assert "trinity.release-policy/v2" in findings[0].message
    assert "trinity.release-policy/v3" in findings[0].message


@pytest.mark.parametrize("extra", [False, True], ids=["missing-field", "extra-field"])
def test_policy_old_schema_refused_before_field_validation(
    parent: Path, release_policy_v2: Path, extra: bool
) -> None:
    # Given an old policy with an incompatible top-level field set.
    policy = parse_json(release_policy_v2.read_bytes())
    assert isinstance(policy, dict)
    if extra:
        policy["unexpected"] = True
    else:
        del policy["oracle"]
    release_policy_v2.write_bytes(canonicalize(policy))
    # When the release gate loads the policy.
    findings = gate(parent)
    # Then the schema refusal precedes the current field-set validation.
    assert codes(findings) == {release.TRUST_INVALID}
    assert "RELEASE_POLICY_SCHEMA_UNSUPPORTED" in findings[0].message
    assert "trinity.release-policy/v2" in findings[0].message
    assert "trinity.release-policy/v3" in findings[0].message


@pytest.mark.parametrize("extra", [False, True], ids=["missing-field", "extra-field"])
def test_receipt_old_schema_refused_before_field_validation(
    parent: Path, oracle_v3_receipt: Path, extra: bool
) -> None:
    # Given an authenticated canonical old receipt with an incompatible field set.
    parsed = parse_envelope(oracle_v3_receipt.read_bytes())
    assert parsed.envelope is not None
    body = parse_json(parsed.envelope.payload)
    assert isinstance(body, dict)
    if extra:
        body["unexpected"] = True
    else:
        del body["controls"]
    oracle_v3_receipt.write_bytes(envelope(ORACLE_PAYLOAD_TYPE, canonicalize(body), OPERATOR))
    reseal(parent)
    # When the release gate verifies the receipt.
    findings = gate(parent)
    # Then the schema refusal precedes the current field-set validation.
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert "ORACLE_SCHEMA_UNSUPPORTED" in findings[0].message
    assert "trinity.oracle-run/v3" in findings[0].message
    assert "trinity.oracle-run/v4" in findings[0].message


def test_execution_fidelity_may_be_a_positive_control(parent: Path) -> None:
    # Given a current policy requiring fidelity as its sole positive control.
    path = parent.parent / "release-trust" / "policy.json"
    policy = parse_json(path.read_bytes())
    assert isinstance(policy, dict)
    oracle = policy["oracle"]
    assert isinstance(oracle, dict)
    oracle["positive_control_ids"] = ["execution_fidelity"]
    path.write_bytes(canonicalize(policy))
    # When the complete release gate runs; Then the existing subset path accepts it.
    assert gate(parent) == []


@bite("shared.md:A12")
def test_missing_receipt_refused(parent: Path) -> None:
    (parent / release.RECEIPT_DIR / f"{UUID_TWO}.json.dsse").unlink()
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_MISSING}
    assert UUID_TWO in findings[0].message


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"schema": "trinity.oracle-run/v0"}, "schema"),
        ({"task_uuid": UUID_TWO}, "task_uuid"),
        ({"bundle_digest": "0" * 64}, "bundle_digest"),
        ({"harbor_version": "0.22.0"}, "harbor_version"),
        ({"image_digest": "python:3.11-slim"}, "image_digest"),
        ({"reward": 0.98}, "positive full reward"),
        ({"runs": []}, "stability run count"),
        ({"score": float("inf")}, "malformed"),
        ({"reward": True, "full_reward": True}, "finite number"),
    ],
)
def test_invalid_receipt_refused(parent: Path, overrides: dict[str, object], fragment: str) -> None:
    receipt(parent, UUID_ONE, **overrides)
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert fragment in findings[0].message


def test_receipt_not_json_object_refused(parent: Path) -> None:
    path = parent / release.RECEIPT_DIR / f"{UUID_ONE}.json.dsse"
    path.write_bytes(envelope(ORACLE_PAYLOAD_TYPE, b"[]\n", OPERATOR))
    reseal(parent)
    assert codes(gate(parent)) == {release.ORACLE_RECEIPT_INVALID}


def test_expired_and_zero_full_reward_receipts_are_refused(parent: Path) -> None:
    receipt(parent, UUID_ONE, expires_at="2026-09-16T11:30:00Z", full_reward=0.0, reward=0.0)
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert "validity window" in findings[0].message


def test_receipt_requires_individual_negative_control_verdicts(parent: Path) -> None:
    runs = [
        {
            "run_id": f"run-{index}",
            "reward": 1.0,
            "score": 1.0,
            "no_op": {"executed": True, "verdict": "accepted", "score": 0.0},
            "known_wrong": {"executed": True, "verdict": "rejected", "score": 0.0},
        }
        for index in range(2)
    ]
    receipt(parent, UUID_ONE, runs=runs)
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert "individually rejected" in findings[0].message


@pytest.mark.parametrize("mode", ["missing", "failed"])
def test_receipt_requires_complete_passing_control_closure(parent: Path, mode: str) -> None:
    control = "trial_reward_accounting"
    controls = coverage_controls(
        UUID_ONE,
        omitted=control if mode == "missing" else None,
        failed=control if mode == "failed" else None,
    )
    receipt(parent, UUID_ONE, controls=controls)
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert control in findings[0].message or "every required control" in findings[0].message


def test_future_oracle_execution_is_refused(parent: Path) -> None:
    receipt(
        parent,
        UUID_ONE,
        started_at="2026-09-17T10:00:00Z",
        completed_at="2026-09-17T11:00:00Z",
        expires_at="2026-09-18T12:00:00Z",
    )
    reseal(parent)
    assert codes(gate(parent)) == {release.ORACLE_RECEIPT_INVALID}


def test_deep_oracle_json_is_a_normal_refusal(parent: Path) -> None:
    payload = b"[" * 200 + b"0" + b"]" * 200
    path = parent / release.RECEIPT_DIR / f"{UUID_ONE}.json.dsse"
    path.write_bytes(envelope(ORACLE_PAYLOAD_TYPE, payload, OPERATOR))
    reseal(parent)
    assert codes(gate(parent)) == {release.ORACLE_RECEIPT_INVALID}


def test_aliased_trust_file_is_refused(parent: Path) -> None:
    trust = parent.parent / "release-trust"
    policy = trust / "policy.json"
    real = trust / "policy.real.json"
    policy.rename(real)
    policy.symlink_to(real.name)
    assert codes(gate(parent)) == {release.TRUST_INVALID}


def test_revoked_and_unauthorized_execution_operators_are_refused(parent: Path) -> None:
    roots = parent.parent / "release-trust" / "roots.yaml"
    value = json.loads(roots.read_text(encoding="utf-8"))
    value["revocations"] = [{"principal": OPERATOR, "revoked_at": "2026-09-16T00:00:00Z"}]
    roots.write_text(json.dumps(value), encoding="utf-8")
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert all("revoked" in item.message for item in findings)

    value["revocations"] = []
    for principal in value["principals"]:
        if principal["name"] == OPERATOR:
            principal["roles"] = ["gate_approver"]
    roots.write_text(json.dumps(value), encoding="utf-8")
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_INVALID}
    assert all("not_bound" in item.message for item in findings)


def test_fabricated_receipt_signer_is_refused(parent: Path) -> None:
    path = parent / release.RECEIPT_DIR / f"{UUID_ONE}.json.dsse"
    parsed = json.loads(path.read_bytes())
    parsed["signatures"][0]["sig"] = "ZmFrZUB0cmluaXR5LnRlc3Q="
    path.write_text(json.dumps(parsed), encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.ORACLE_RECEIPT_INVALID}


# ---- reward schema ----


def test_missing_reward_schema_refused(parent: Path) -> None:
    (parent / "samples" / release.REWARD_SCHEMA_NAME).unlink()
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.REWARD_SCHEMA_AMBIGUOUS}
    assert len(findings) == len(UUIDS)


def test_per_bundle_reward_schema_accepted(parent: Path) -> None:
    (parent / "samples" / release.REWARD_SCHEMA_NAME).unlink()
    for uuid in UUIDS:
        schema = parent / "samples" / uuid / "tests" / release.REWARD_SCHEMA_NAME
        schema.write_text(
            json.dumps(
                {
                    "schema": release.REWARD_SCHEMA,
                    "authoritative": {"path": "verifier/reward.json", "key": "reward"},
                }
            ),
            encoding="utf-8",
        )
        receipt(parent, uuid)
    write_reports(parent)
    reseal(parent)
    assert gate(parent) == []


@bite("shared.md:A13")
def test_three_rewards_in_one_run_refused(parent: Path) -> None:
    rollout(parent, UUID_ONE, {"reward": 16.26}, name="verifier/reward.json")
    rollout(parent, UUID_ONE, {"reward": 0.2877}, name="verifier/score.json")
    receipt(parent, UUID_ONE)
    write_reports(parent)
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.REWARD_SCHEMA_AMBIGUOUS}
    assert "3 different values" in findings[0].message


def test_same_reward_repeated_is_not_ambiguous(parent: Path) -> None:
    rollout(parent, UUID_ONE, {"reward": 1.0}, name="verifier/reward.json")
    receipt(parent, UUID_ONE)
    write_reports(parent)
    reseal(parent)
    assert gate(parent) == []


@pytest.mark.parametrize(
    "document",
    [
        b"{",
        b"[" * 200 + b"0" + b"]" * 200,
        b'{"reward":' + b"9" * 4301 + b"}",
    ],
)
def test_invalid_trajectory_json_is_a_reward_refusal(parent: Path, document: bytes) -> None:
    path = rollout(parent, UUID_ONE, {"reward": 1.0}, name="verifier/invalid.json")
    path.write_bytes(document)
    receipt(parent, UUID_ONE)
    write_reports(parent)
    reseal(parent)

    findings = gate(parent)

    assert codes(findings) == {release.REWARD_SCHEMA_AMBIGUOUS}
    assert "malformed" in findings[0].message


# ---- trial status ----


@pytest.mark.parametrize(
    "body",
    [
        {"score_eval": 0.5325, "verifier_result": {"status": "vacuous", "targets_total": 0}},
        {"score_eval": 1.0, "verifier_result": {"status": "scored", "targets_total": 0}},
    ],
)
@bite("shared.md:A14")
def test_vacuous_rollout_without_invalid_tag_refused(parent: Path, body: dict[str, object]) -> None:
    rollout(parent, UUID_TWO, body)
    receipt(parent, UUID_TWO)
    write_reports(parent)
    reseal(parent)
    assert codes(gate(parent)) == {release.TRIAL_STATUS_INVALID}


def test_vacuous_rollout_tagged_invalid_passes(parent: Path) -> None:
    body: dict[str, object] = {"trial_status": "invalid", "verifier_result": {"status": "vacuous"}}
    rollout(parent, UUID_TWO, body)
    receipt(parent, UUID_TWO)
    write_reports(parent)
    reseal(parent)
    assert gate(parent) == []


@pytest.mark.parametrize("lane_root", ["samples", "delivery", "deliverables"])
def test_deliverables_trajectories_are_also_read(parent: Path, lane_root: str) -> None:
    run = parent / lane_root / UUID_ONE / "trajectories" / "opus-5" / "run_3"
    run.mkdir(parents=True)
    (run / "result.json").write_text(json.dumps({"targets_total": 0}), encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.TRIAL_STATUS_INVALID}


# ---- waiver ----


def test_waiver_never_suppresses_any_release_failure(parent: Path) -> None:
    (parent / release.RECEIPT_DIR / f"{UUID_TWO}.json.dsse").unlink()
    (parent / "VERDICT.md").write_text(report("🟢 **SHIP**"), encoding="utf-8")
    waiver(parent)
    reseal(parent)
    assert codes(gate(parent)) == {
        release.DISPOSITION_UNBOUND,
        release.ORACLE_RECEIPT_MISSING,
        release.WAIVER_INVALID,
    }


def test_waiver_cannot_clear_oracle_failure(parent: Path) -> None:
    (parent / release.RECEIPT_DIR / f"{UUID_TWO}.json.dsse").unlink()
    waiver(parent)
    reseal(parent)
    assert codes(gate(parent)) == {release.ORACLE_RECEIPT_MISSING, release.WAIVER_INVALID}


def test_signed_looking_waiver_is_still_forbidden(parent: Path) -> None:
    (parent / release.RECEIPT_DIR / f"{UUID_TWO}.json.dsse").unlink()
    waiver(parent, signer=APPROVER, signature="fabricated")
    reseal(parent)
    findings = gate(parent)
    assert codes(findings) == {release.ORACLE_RECEIPT_MISSING, release.WAIVER_INVALID}
    invalid = [item for item in findings if item.code == release.WAIVER_INVALID]
    assert "forbidden" in invalid[0].message


def test_waiver_not_json_object_refused(parent: Path) -> None:
    path = parent / release.WAIVER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("42", encoding="utf-8")
    reseal(parent)
    assert codes(gate(parent)) == {release.WAIVER_INVALID}


# ---- helpers and cli ----


def test_disposition_line_stops_at_next_heading() -> None:
    text = "## Disposition\n\n\n## Findings\n\nSHIP\n"
    assert release.disposition_line(text) is None


@pytest.mark.parametrize(
    ("line", "token"),
    [
        ("🟢 **SHIP**", "SHIP"),
        ("`SHIP:INFERRED` at digest x", "SHIP:INFERRED"),
        ("🔴 BLOCK.", "BLOCK"),
        ("🟡 **`HOLD:PILOT_REQUIRED`** for the batch", "HOLD:PILOT_REQUIRED"),
        ("🟢", None),
    ],
)
def test_disposition_token(line: str, token: str | None) -> None:
    assert release.disposition_token(line) == token


def test_bundle_set_digest_is_order_independent(parent: Path) -> None:
    samples = parent / "samples"
    assert release.bundle_set_digest(samples, UUIDS) == release.bundle_set_digest(
        samples, list(reversed(UUIDS))
    )


def test_isolated_cli_help_from_unrelated_directory(tmp_path: Path) -> None:
    script = Path(release.__file__).resolve()
    completed = subprocess.run(
        [sys.executable, "-I", str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        shell=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "usage: release.py" in completed.stdout
    assert "Traceback" not in completed.stderr


def test_isolated_cli_missing_root_refuses_without_traceback(tmp_path: Path) -> None:
    script = Path(release.__file__).resolve()
    completed = subprocess.run(
        [sys.executable, "-I", str(script), "./missing-parent"],
        cwd=tmp_path,
        capture_output=True,
        check=False,
        shell=False,
        text=True,
    )
    assert completed.returncode == 1
    assert "candidate root escapes or is unavailable" in completed.stderr
    assert str(tmp_path) not in completed.stdout + completed.stderr
    assert "Traceback" not in completed.stdout + completed.stderr


def pin_cli_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    check = release.check_release

    def pinned(root: str | Path, _evaluation_time: datetime | None = None, **kwargs: Any) -> Any:
        return check(root, NOW if _evaluation_time is None else _evaluation_time, **kwargs)

    monkeypatch.setattr(release, "check_release", pinned)


def test_cli_reports_and_exits(
    parent: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    pin_cli_clock(monkeypatch)
    assert release.main(["release.py", "./parent"]) == 0
    assert "clean" in capsys.readouterr().out
    (parent / "VERDICT.md").write_text(report("HOLD"), encoding="utf-8")
    reseal(parent)
    assert release.main(["release.py", "./parent"]) == 1
    out = capsys.readouterr().out
    assert release.VERDICT_NOT_SHIP in out
    assert "refused" in out


@pytest.mark.parametrize("root", ["parent", "/parent", "~/parent", ".\\parent", "./../parent"])
def test_cli_rejects_noncanonical_root_without_host_path_leak(
    parent: Path, root: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert release.main(["release.py", root]) == 1
    output = capsys.readouterr()
    assert str(parent.parent) not in output.out + output.err


def test_cli_export_flag(parent: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pin_cli_clock(monkeypatch)
    export = tmp_path / "export"
    shutil.copytree(parent / "samples", export)
    assert release.main(["release.py", "./parent", "--export", "./export"]) == 0
    (export / UUID_TWO / "task.toml").write_text("changed\n", encoding="utf-8")
    assert release.main(["release.py", "./parent", "--export", "./export"]) == 1


# ---- frozen release candidates ------------------------------------------------------------


def test_release_reads_a_frozen_candidate_and_ignores_harness_root_records(
    parent: Path,
) -> None:
    for harness in (".seed", ".audit"):
        (parent / harness / "disposition.json").unlink()
        (parent / harness / "disposition.json.dsse").unlink()
    commit_all(parent, "records withdrawn from the harness roots")
    write_dispositions(parent, git(["rev-parse", "HEAD"], cwd=parent).strip(), "2026.09-rc1")
    commit_all(parent, "seal release candidate")

    assert release.check_release(str(parent), NOW, _signature_backend=BACKEND) != []
    assert (
        release.check_release(str(parent), NOW, _signature_backend=BACKEND, release="2026.09-rc1")
        == []
    )
    malformed = release.check_release(str(parent), NOW, _signature_backend=BACKEND, release="../x")
    assert [item.code for item in malformed] == [release.TRUST_INVALID]
