# allow: SIZE_OK - Task 19 requires its regression matrix beside the historical policy cases.

import hashlib
import json
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tools.attest import verify as attest_verify
from tools.attest.backend import (
    SignatureBackendError,
    VerificationFailureReason,
    VerificationResult,
)
from tools.attest.backend_ssh import SshKeygenBackend
from tools.attest.canonical import JSONValue, canonicalize
from tools.attest.dsse import Envelope, Signature
from tools.attest.errors import AttestationFailureReason, AttestationOutcome
from tools.attest.intoto import (
    APPROVAL_PREDICATE_TYPE,
    EXECUTION_PREDICATE_TYPE,
    STATEMENT_TYPE,
)
from tools.attest.merkle import (
    TRAJECTORY_MERKLE_PROFILE,
    TrajectoryFailureReason,
    TrajectoryManifest,
    parse_trajectory_manifest,
)
from tools.attest.policies import execution as execution_policy
from tools.attest.policies.execution import (
    resolve_trajectory_documents,
    verify_execution_attestation,
    verify_execution_attestation_evidence,
)
from tools.attest.replay import ReplayGuard
from tools.attest.verify import IN_TOTO_PAYLOAD_TYPE

from tests import test_attest_verify as generic_tests
from tests.attest_execution_fixtures import (
    FIDELITY_COLLATERAL,
    HARNESS_DIGEST,
    with_fidelity,
    without_fidelity,
)
from tests.harness_imports import integrity
from tests.test_integrity_parent import trajectory_execution_root

ARTIFACT = b"frozen task bytes\n"
EVALUATION_TIME = datetime(2027, 1, 1, tzinfo=UTC)
OPERATOR_A = "operator-a@trinity.test"
OPERATOR_B = "operator-b@trinity.test"
OUTSIDER = "self-asserted-operator@trinity.test"
ROLE = "execution_operator"
VERSION = 7
COLLATERAL = {
    "trajectory-root": b"trajectory\n",
    "policy.yaml": b"policy\n",
    "scorer": b"scorer\n",
    "population": (
        Path(__file__).parent / "fixtures/attest/trajectory/trajectory-manifest.json"
    ).read_bytes(),
    "decoy": b"decoy\n",
    "schedule": b"schedule\n",
    "budget": b"budget\n",
    **FIDELITY_COLLATERAL,
}
TRAJECTORY_FIXTURE = Path(__file__).parent / "fixtures" / "attest" / "trajectory"
TRAJECTORY_ROOT = "a52f097eff460208f03f586418085d0fb3d45d37ca47b621605b3ac5811a99fa"


@pytest.fixture(autouse=True)
def fixed_gate_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(execution_policy, "gate_evaluation_time", lambda: EVALUATION_TIME)


class StubBackend:
    keyid_scheme = "test-signature:v1"

    def __init__(self, principals: dict[bytes, str]) -> None:
        self._principals = principals

    def sign(self, payload: bytes, *, key_path: Path) -> bytes:
        del payload, key_path
        raise SignatureBackendError(
            VerificationFailureReason.TOOL_FAILURE,
            "the verification stub does not sign",
        )

    def verify(
        self,
        payload: bytes,
        *,
        signature_path: Path,
        allowed_signers_path: Path,
        evaluation_time: datetime,
    ) -> VerificationResult:
        del payload, allowed_signers_path, evaluation_time
        principal = self._principals.get(signature_path.read_bytes())
        if principal is None:
            return VerificationResult.failure(
                VerificationFailureReason.SIGNATURE_INVALID,
                "stub signature is invalid",
            )
        return VerificationResult.success(principal)


def descriptor(name: str, content: bytes) -> dict[str, JSONValue]:
    return {"name": name, "digest": {"sha256": hashlib.sha256(content).hexdigest()}}


def execution_statement(
    *,
    committed_at: str = "2026-08-26T09:59:59Z",
    started_at: str = "2026-12-31T23:00:00Z",
    ended_at: str = "2027-01-01T01:00:00Z",
) -> dict[str, JSONValue]:
    return with_fidelity(
        {
            "_type": STATEMENT_TYPE,
            "subject": [
                {"name": "task.bin", "digest": {"sha256": hashlib.sha256(ARTIFACT).hexdigest()}}
            ],
            "predicateType": EXECUTION_PREDICATE_TYPE,
            "predicate": {
                "operatorIdentity": OPERATOR_A,
                "trajectoryRoot": descriptor("trajectory-root", b"trajectory\n"),
                "policyManifest": descriptor("policy.yaml", b"policy\n"),
                "scorerClosure": descriptor("scorer", b"scorer\n"),
                "populationSequenceCommitment": descriptor("population", COLLATERAL["population"]),
                "preRunCommitment": {
                    "committedAt": committed_at,
                    "hiddenDecoySeed": descriptor("decoy", b"decoy\n"),
                    "jobSchedule": descriptor("schedule", b"schedule\n"),
                },
                "executionInterval": {
                    "startedAt": started_at,
                    "endedAt": ended_at,
                },
                "rolloutDurations": [{"rollout": "rollout-1", "seconds": 12.5}],
                "budgetEnvelope": descriptor("budget", b"budget\n"),
                "replay": {
                    "nonce": "nonce-1",
                    "audience": "audit-project",
                    "sequence": 1,
                    "runId": "run-1",
                },
            },
        }
    )


def approval_statement() -> dict[str, JSONValue]:
    return {
        "_type": STATEMENT_TYPE,
        "subject": [
            {"name": "task.bin", "digest": {"sha256": hashlib.sha256(ARTIFACT).hexdigest()}}
        ],
        "predicateType": APPROVAL_PREDICATE_TYPE,
        "predicate": {
            "producerIdentity": "producer@trinity.test",
            "approverIdentity": OPERATOR_A,
            "producerModelLineage": "provider/model-a/2026-08",
            "approverModelLineage": "provider/model-b/2026-08",
            "failedBreakAttempt": descriptor("failed-break.jsonl", b"failed probe\n"),
            "replay": {
                "nonce": "nonce-1",
                "audience": "audit-project",
                "sequence": 1,
                "runId": "run-1",
            },
        },
    }


def principal(
    name: str,
    *,
    roles: tuple[str, ...] = (ROLE,),
    expires: str = "2029-01-01T00:00:00Z",
) -> dict[str, JSONValue]:
    return {"name": name, "roles": list(roles), "expires": expires}


def trust_root(
    *,
    threshold: int = 1,
    expires: str = "2030-01-01T00:00:00Z",
    principals: list[JSONValue] | None = None,
    revocations: list[JSONValue] | None = None,
) -> dict[str, JSONValue]:
    return {
        "version": VERSION,
        "expires": expires,
        "roles": [{"name": ROLE, "threshold": threshold}],
        "principals": (
            [principal(OPERATOR_A), principal(OPERATOR_B)] if principals is None else principals
        ),
        "revocations": [] if revocations is None else revocations,
    }


def write_inputs(
    tmp_path: Path,
    *,
    statement: dict[str, JSONValue] | None = None,
    signatures: tuple[bytes, ...] = (b"signature-a",),
    root: dict[str, JSONValue] | None = None,
) -> tuple[Path, Path, Path, ReplayGuard]:
    artifact_path = tmp_path / "task.bin"
    artifact_path.write_bytes(ARTIFACT)
    payload = json.dumps(
        execution_statement() if statement is None else statement,
        separators=(",", ":"),
    ).encode()
    envelope_path = tmp_path / "execution.dsse"
    envelope_path.write_bytes(
        Envelope(
            payload_type=IN_TOTO_PAYLOAD_TYPE,
            payload=payload,
            signatures=tuple(
                Signature(sig=signature, keyid=StubBackend.keyid_scheme) for signature in signatures
            ),
        ).to_json()
    )
    root_path = tmp_path / "roots.json"
    root_path.write_bytes(canonicalize(trust_root() if root is None else root))
    return (
        envelope_path,
        artifact_path,
        root_path,
        ReplayGuard(tmp_path / "replay.jsonl", expected_audience="audit-project"),
    )


def verify(
    inputs: tuple[Path, Path, Path, ReplayGuard],
    backend: StubBackend,
) -> AttestationOutcome:
    envelope_path, artifact_path, root_path, replay_guard = inputs
    return verify_execution_attestation(
        envelope_path=envelope_path,
        artifact_path=artifact_path,
        trust_root_path=root_path,
        allowed_signers_path=tmp_allowed_signers(root_path),
        trusted_root_version=VERSION,
        backend=backend,
        replay_guard=replay_guard,
        subject_name="task.bin",
        collateral=COLLATERAL,
        harness_config_digest=HARNESS_DIGEST,
    )


def tmp_allowed_signers(root_path: Path) -> Path:
    path = root_path.with_name("allowed_signers")
    path.write_text("stub policy\n", encoding="utf-8")
    return path


def accepting_backend(*principals: str) -> StubBackend:
    return StubBackend(
        {
            f"signature-{chr(ord('a') + index)}".encode(): principal
            for index, principal in enumerate(principals)
        }
    )


def assert_refused(outcome: AttestationOutcome, reason: AttestationFailureReason) -> None:
    assert outcome.accepted is False
    assert outcome.reason is reason
    assert outcome.detail
    assert outcome.principals == ()


def fixture_manifest() -> TrajectoryManifest:
    document = (TRAJECTORY_FIXTURE / "trajectory-manifest.json").read_bytes()
    parsed = parse_trajectory_manifest(document)
    assert parsed.manifest is not None
    return parsed.manifest


def profile_execution_statement(manifest_document: bytes) -> dict[str, JSONValue]:
    statement = execution_statement()
    predicate = statement["predicate"]
    assert isinstance(predicate, dict)
    predicate["trajectoryRoot"] = {
        "name": TRAJECTORY_MERKLE_PROFILE,
        "digest": {"sha256": TRAJECTORY_ROOT},
    }
    predicate["populationSequenceCommitment"] = descriptor(
        "trajectory-manifest.json", manifest_document
    )
    return statement


def profile_collateral(manifest_document: bytes) -> dict[str, bytes]:
    collateral = dict(COLLATERAL)
    del collateral["trajectory-root"]
    del collateral["population"]
    collateral["trajectory-manifest.json"] = manifest_document
    return collateral


def test_trajectory_documents_resolve_relative_to_parent_root(tmp_path: Path) -> None:
    shutil_target = tmp_path / "deliverables"
    shutil.copytree(TRAJECTORY_FIXTURE / "deliverables", shutil_target)

    documents, outcome = resolve_trajectory_documents(tmp_path, fixture_manifest())

    assert outcome.accepted is True
    assert documents == {
        entry.path: (tmp_path / entry.path.removeprefix("./")).read_bytes()
        for entry in fixture_manifest().rollouts
    }


def test_trajectory_document_symlink_escape_is_refused(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    outside = tmp_path / "outside.json"
    shutil.copytree(TRAJECTORY_FIXTURE / "deliverables", parent / "deliverables")
    outside.write_bytes(b'{"result":"invented"}\n')
    rollout = parent / "deliverables/task/trajectories/rollout-1.json"
    rollout.unlink()
    rollout.symlink_to(outside)

    documents, outcome = resolve_trajectory_documents(parent, fixture_manifest())

    assert documents is None
    assert outcome.reason is TrajectoryFailureReason.EXECUTION_TRAJECTORY_RESOURCE_REFUSED


def test_execution_evidence_reads_the_authenticated_envelope_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = write_inputs(tmp_path)
    envelope_path, _artifact_path, root_path, _replay_guard = inputs
    allowed_signers_path = tmp_allowed_signers(root_path)
    read_envelope = attest_verify._read_envelope
    calls = 0

    def counted_read(path: Path) -> tuple[bytes | None, AttestationOutcome | None]:
        nonlocal calls
        calls += 1
        return read_envelope(path)

    monkeypatch.setattr(attest_verify, "_read_envelope", counted_read)

    outcome = verify_execution_attestation_evidence(
        envelope_path=envelope_path,
        artifact=ARTIFACT,
        trust_root_path=root_path,
        allowed_signers_path=allowed_signers_path,
        trusted_root_version=VERSION,
        backend=accepting_backend(OPERATOR_A),
        expected_audience="audit-project",
        subject_name="task.bin",
        collateral=COLLATERAL,
        harness_config_digest=HARNESS_DIGEST,
    )

    assert outcome.accepted is True
    assert calls == 1


def test_trajectory_refusal_does_not_consume_replay_admission(tmp_path: Path) -> None:
    manifest_document = (TRAJECTORY_FIXTURE / "trajectory-manifest.json").read_bytes()
    shutil.copytree(TRAJECTORY_FIXTURE / "deliverables", tmp_path / "deliverables")
    inputs = write_inputs(tmp_path, statement=profile_execution_statement(manifest_document))
    envelope_path, artifact_path, root_path, replay_guard = inputs
    allowed_signers_path = tmp_allowed_signers(root_path)
    rollout = tmp_path / "deliverables/task/trajectories/rollout-1.json"
    clean_rollout = rollout.read_bytes()
    rollout.write_bytes(b'{"result":"mutated"}\n')

    refused = verify_execution_attestation(
        envelope_path=envelope_path,
        artifact_path=artifact_path,
        trust_root_path=root_path,
        allowed_signers_path=allowed_signers_path,
        trusted_root_version=VERSION,
        backend=accepting_backend(OPERATOR_A),
        replay_guard=replay_guard,
        subject_name="task.bin",
        collateral=profile_collateral(manifest_document),
        parent_root=tmp_path,
        harness_config_digest=HARNESS_DIGEST,
    )
    rollout.write_bytes(clean_rollout)
    accepted = verify_execution_attestation(
        envelope_path=envelope_path,
        artifact_path=artifact_path,
        trust_root_path=root_path,
        allowed_signers_path=allowed_signers_path,
        trusted_root_version=VERSION,
        backend=accepting_backend(OPERATOR_A),
        replay_guard=replay_guard,
        subject_name="task.bin",
        collateral=profile_collateral(manifest_document),
        parent_root=tmp_path,
        harness_config_digest=HARNESS_DIGEST,
    )

    assert refused.reason is TrajectoryFailureReason.EXECUTION_TRAJECTORY_DIGEST_MISMATCH
    assert accepted == AttestationOutcome.accept((OPERATOR_A,))


def test_missing_execution_envelope_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path)
    missing = (tmp_path / "missing.dsse", inputs[1], inputs[2], inputs[3])

    assert_refused(
        verify(missing, accepting_backend(OPERATOR_A)),
        AttestationFailureReason.ENVELOPE_MISSING,
    )


def test_unreadable_execution_envelope_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path)
    unreadable = tmp_path / "envelope-directory"
    unreadable.mkdir()

    assert_refused(
        verify((unreadable, inputs[1], inputs[2], inputs[3]), accepting_backend(OPERATOR_A)),
        AttestationFailureReason.ENVELOPE_UNREADABLE,
    )


def test_malformed_execution_envelope_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path)
    inputs[0].write_bytes(b'{"payload":')

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A)),
        AttestationFailureReason.ENVELOPE_MALFORMED,
    )


def test_non_execution_predicate_type_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path, statement=approval_statement())

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A)),
        AttestationFailureReason.EXECUTION_PREDICATE_VERSION_UNSUPPORTED,
    )


def test_self_asserted_operator_role_is_not_authorization(tmp_path: Path) -> None:
    statement = execution_statement()
    predicate = statement["predicate"]
    assert isinstance(predicate, dict)
    predicate["operatorIdentity"] = OUTSIDER
    inputs = write_inputs(tmp_path, statement=statement)

    assert_refused(
        verify(inputs, accepting_backend(OUTSIDER)),
        AttestationFailureReason.PRINCIPAL_NOT_BOUND_TO_ROLE,
    )


def test_execution_operator_threshold_not_met_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path, root=trust_root(threshold=2))

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A)),
        AttestationFailureReason.THRESHOLD_NOT_MET,
    )


def test_expired_trust_root_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path, root=trust_root(expires="2027-01-01T00:00:00Z"))

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A)),
        AttestationFailureReason.TRUST_ROOT_EXPIRED,
    )


def test_expired_execution_operator_is_refused(tmp_path: Path) -> None:
    root = trust_root(
        threshold=2,
        principals=[
            principal(OPERATOR_A),
            principal(OPERATOR_B, expires="2027-01-01T00:00:00Z"),
        ],
    )
    inputs = write_inputs(tmp_path, signatures=(b"signature-a", b"signature-b"), root=root)

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A, OPERATOR_B)),
        AttestationFailureReason.PRINCIPAL_EXPIRED,
    )


def test_revoked_execution_operator_is_refused(tmp_path: Path) -> None:
    root = trust_root(
        threshold=2,
        revocations=[{"principal": OPERATOR_B, "revoked_at": "2026-12-01T00:00:00Z"}],
    )
    inputs = write_inputs(tmp_path, signatures=(b"signature-a", b"signature-b"), root=root)

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A, OPERATOR_B)),
        AttestationFailureReason.PRINCIPAL_REVOKED,
    )


def test_replayed_execution_envelope_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path)
    backend = accepting_backend(OPERATOR_A)
    assert verify(inputs, backend).accepted is True

    assert_refused(
        verify(inputs, backend),
        AttestationFailureReason.REPLAYED_ENVELOPE,
    )


def test_declared_subject_digest_mismatch_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path)
    inputs[1].write_bytes(b"mutated task bytes\n")

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A)),
        AttestationFailureReason.SUBJECT_DIGEST_MISMATCH,
    )


def test_commitment_equal_to_execution_start_is_refused(tmp_path: Path) -> None:
    inputs = write_inputs(
        tmp_path,
        statement=execution_statement(committed_at="2026-12-31T23:00:00Z"),
    )

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A)),
        AttestationFailureReason.COMMITMENT_NOT_BEFORE_EXECUTION,
    )


def test_evaluation_instant_outside_execution_interval_is_refused(tmp_path: Path) -> None:
    statement = execution_statement(
        started_at="2026-08-26T10:00:00Z",
        ended_at="2026-08-26T11:00:00Z",
    )
    outcome = verify(write_inputs(tmp_path, statement=statement), accepting_backend(OPERATOR_A))

    assert outcome.accepted is False
    assert outcome.reason is VerificationFailureReason.EVALUATION_TIME_INVALID
    assert "execution interval" in outcome.detail


def test_same_principal_twice_does_not_meet_threshold_two(tmp_path: Path) -> None:
    inputs = write_inputs(
        tmp_path,
        signatures=(b"signature-a", b"signature-b"),
        root=trust_root(threshold=2),
    )

    assert_refused(
        verify(inputs, accepting_backend(OPERATOR_A, OPERATOR_A)),
        AttestationFailureReason.THRESHOLD_NOT_MET,
    )


def test_valid_execution_attestation_is_accepted(tmp_path: Path) -> None:
    inputs = write_inputs(tmp_path)

    assert verify(inputs, accepting_backend(OPERATOR_A)) == AttestationOutcome.accept((OPERATOR_A,))


def test_release_mode_refuses_v1_predicate(tmp_path: Path) -> None:
    # Given an otherwise valid historical execution envelope.
    inputs = write_inputs(tmp_path, statement=without_fidelity(execution_statement()))
    # When verified with the default release policy.
    outcome = verify(inputs, accepting_backend(OPERATOR_A))
    # Then the version is refused, naming observed and required versions.
    assert not outcome.accepted
    assert outcome.reason is not None
    assert outcome.reason.name == "EXECUTION_PREDICATE_VERSION_UNSUPPORTED"
    assert "trinity.execution/v1" in outcome.detail
    assert "trinity.execution/v2" in outcome.detail


def test_version_check_precedes_field_verification(tmp_path: Path) -> None:
    # Given a v1 envelope with malformed predicate and subject fields.
    statement = without_fidelity(execution_statement())
    statement["predicate"] = {}
    statement["subject"] = []
    inputs = write_inputs(tmp_path, statement=statement)
    # When release verification runs.
    outcome = verify(inputs, accepting_backend(OPERATOR_A))
    # Then no field refusal masks the downgrade.
    assert outcome.reason is not None
    assert outcome.reason.name == "EXECUTION_PREDICATE_VERSION_UNSUPPORTED"


@pytest.mark.parametrize("broken", [False, True])
def test_diagnosis_mode_parses_v1_but_never_accepts(tmp_path: Path, broken: bool) -> None:
    # Given a clean or field-malformed v1 envelope.
    statement = without_fidelity(execution_statement())
    if broken:
        statement["predicate"] = {}
    envelope, artifact, root, guard = write_inputs(tmp_path, statement=statement)
    # When diagnosis is explicitly requested.
    outcome = verify_execution_attestation(
        envelope_path=envelope,
        artifact_path=artifact,
        trust_root_path=root,
        allowed_signers_path=tmp_allowed_signers(root),
        trusted_root_version=VERSION,
        backend=accepting_backend(OPERATOR_A),
        replay_guard=guard,
        collateral=COLLATERAL,
        release_required=False,
    )
    # Then every new obligation remains unverifiable and replay state is untouched.
    assert not outcome.accepted
    assert not (tmp_path / "replay.jsonl").exists()
    for name in (*FIDELITY_COLLATERAL, "rolloutTelemetry"):
        assert f"{name}=unverifiable" in outcome.detail
    assert ("parsed" in outcome.detail) is (not broken)


def fidelity_outcome(
    tmp_path: Path,
    *,
    missing: str | None = None,
    digest: str = HARNESS_DIGEST,
    mismatch: bool = False,
) -> AttestationOutcome:
    manifest = (TRAJECTORY_FIXTURE / "trajectory-manifest.json").read_bytes()
    statement = with_fidelity(profile_execution_statement(manifest))
    if mismatch:
        predicate = statement["predicate"]
        assert isinstance(predicate, dict)
        for name in ("rolloutDurations", "rolloutTelemetry"):
            rows = predicate[name]
            assert isinstance(rows, list)
            row = rows[0]
            assert isinstance(row, dict)
            row["rollout"] = "invented"
    collateral = {**profile_collateral(manifest), **FIDELITY_COLLATERAL}
    if missing is not None:
        del collateral[missing]
    shutil.copytree(TRAJECTORY_FIXTURE / "deliverables", tmp_path / "deliverables")
    envelope, _artifact, root, _guard = write_inputs(tmp_path, statement=statement)
    return verify_execution_attestation_evidence(
        envelope_path=envelope,
        artifact=ARTIFACT,
        trust_root_path=root,
        allowed_signers_path=tmp_allowed_signers(root),
        trusted_root_version=VERSION,
        backend=accepting_backend(OPERATOR_A),
        expected_audience="audit-project",
        collateral=collateral,
        parent_root=tmp_path,
        harness_config_digest=digest,
    )


def test_release_mode_refuses_harness_config_divergence(tmp_path: Path) -> None:
    # Given a supplied policy digest unlike the signed descriptor; when verified.
    outcome = fidelity_outcome(tmp_path, digest="f" * 64)
    # Then the independently supplied pin governs acceptance.
    assert outcome.reason is not None
    assert outcome.reason.name == "EXECUTION_HARNESS_CONFIG_DIVERGENT"


def test_release_mode_refuses_absent_roster(tmp_path: Path) -> None:
    # Given absent roster bytes; when verified.
    outcome = fidelity_outcome(tmp_path, missing="populationRoster")
    # Then absence is not satisfied by a signed digest alone.
    assert outcome.reason is not None
    assert outcome.reason.name == "EXECUTION_ROSTER_UNBOUND"


def test_release_mode_refuses_absent_capture(tmp_path: Path) -> None:
    # Given absent raw capture bytes; when verified.
    outcome = fidelity_outcome(tmp_path, missing="observationCapture")
    # Then absence has a specific refusal.
    assert outcome.reason is not None
    assert outcome.reason.name == "EXECUTION_CAPTURE_UNBOUND"


def test_release_mode_refuses_telemetry_manifest_mismatch(tmp_path: Path) -> None:
    # Given mutually consistent durations/telemetry but different committed rollout IDs.
    outcome = fidelity_outcome(tmp_path, mismatch=True)
    # Then the manifest, not another operator field, fixes the population.
    assert outcome.reason is not None
    assert outcome.reason.name == "EXECUTION_TELEMETRY_INCONSISTENT"


_OLD_REFUSAL_TESTS: dict[AttestationFailureReason, Callable[[Path], None]] = {
    reason: getattr(generic_tests, f"test_{name}")
    for reason, name in zip(
        (reason for reason in AttestationFailureReason if not reason.name.startswith("EXECUTION_")),
        (
            "missing_envelope_file_is_refused",
            "unreadable_envelope_file_is_refused",
            "malformed_envelope_is_refused",
            "unexpected_payload_type_is_refused",
            "invalid_signature_is_a_pae_mismatch",
            "no_signatures_is_refused",
            "unknown_keyid_scheme_is_refused",
            "malformed_statement_is_refused",
            "unexpected_statement_type_is_refused",
            "unknown_predicate_type_is_refused",
            "malformed_predicate_is_refused",
            "missing_subject_is_refused",
            "subject_digest_mismatch_is_refused",
            "unsupported_digest_algorithm_is_refused",
            "missing_trust_root_is_refused",
            "malformed_trust_root_is_refused",
            "expired_trust_root_is_refused",
            "rolled_back_trust_root_is_refused",
            "unknown_role_is_refused",
            "principal_not_bound_to_role_is_refused",
            "threshold_not_met_is_refused",
            "revoked_principal_is_refused",
            "expired_principal_is_refused",
            "predicate_self_approval_is_refused",
            "replayed_envelope_is_refused",
            "missing_nonce_is_refused",
            "reused_nonce_is_refused",
            "non_monotonic_sequence_is_refused",
            "audience_mismatch_is_refused",
            "commitment_not_before_execution_is_refused",
        ),
        strict=True,
    )
}


@pytest.mark.parametrize("reason", tuple(_OLD_REFUSAL_TESTS))
def test_existing_refusal_codes_remain_reachable(
    tmp_path: Path, reason: AttestationFailureReason
) -> None:
    # Given each historical refusal scenario; when its real verifier is exercised.
    # Then the original test asserts the exact enum member remains reachable.
    _OLD_REFUSAL_TESTS[reason](tmp_path)


def test_integrity_message_names_supported_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    # Given a well-formed non-execution envelope at the execution retention surface.
    root = trajectory_execution_root(tmp_path, "wrong-predicate")
    envelope = Envelope(
        IN_TOTO_PAYLOAD_TYPE, canonicalize(approval_statement()), (Signature(b"x"),)
    ).to_json()
    directory = root / integrity.EXECUTION_ATTESTATIONS_PATH
    directory.mkdir(parents=True)
    (directory / f"{hashlib.sha256(envelope).hexdigest()}.dsse").write_bytes(envelope)
    # When parent verification reports the supported carriers.
    findings = integrity.check_execution_attestations(
        str(root), EVALUATION_TIME, accepting_backend(OPERATOR_A)
    )
    # Then both supported parser versions are named, not just historical v1.
    assert any(
        "trinity.execution/v1" in item.message and "trinity.execution/v2" in item.message
        for item in findings
    )


@pytest.mark.parametrize("name", tuple(FIDELITY_COLLATERAL))
def test_release_recomputes_each_fidelity_collateral_digest(tmp_path: Path, name: str) -> None:
    # Given complete v2 collateral with one byte-bound resource tampered.
    envelope, _artifact, root, _guard = write_inputs(tmp_path)
    collateral = {**COLLATERAL, name: b"tampered"}
    # When release evidence is verified.
    outcome = verify_execution_attestation_evidence(
        envelope_path=envelope,
        artifact=ARTIFACT,
        trust_root_path=root,
        allowed_signers_path=tmp_allowed_signers(root),
        trusted_root_version=VERSION,
        backend=accepting_backend(OPERATOR_A),
        expected_audience="audit-project",
        collateral=collateral,
        harness_config_digest=HARNESS_DIGEST,
    )
    # Then the signed descriptor is checked against actual bytes.
    assert_refused(outcome, AttestationFailureReason.SUBJECT_DIGEST_MISMATCH)


def test_diagnosis_never_accepts_complete_v2(tmp_path: Path) -> None:
    # Given complete v2 evidence, including the independently supplied digest.
    envelope, _artifact, root, _guard = write_inputs(tmp_path)
    # When the evidence-only API is called in diagnosis mode.
    outcome = verify_execution_attestation_evidence(
        envelope_path=envelope,
        artifact=ARTIFACT,
        trust_root_path=root,
        allowed_signers_path=tmp_allowed_signers(root),
        trusted_root_version=VERSION,
        backend=accepting_backend(OPERATOR_A),
        expected_audience="audit-project",
        collateral=COLLATERAL,
        harness_config_digest=HARNESS_DIGEST,
        release_required=False,
    )
    # Then diagnosis cannot return a reusable acceptance.
    assert_refused(outcome, AttestationFailureReason.EXECUTION_DIAGNOSIS_ONLY)


@pytest.mark.skipif(shutil.which("ssh-keygen") is None, reason="ssh-keygen is required")
@pytest.mark.parametrize("case", ["clean", "planted"])
def test_frozen_signed_v2_envelopes(case: str) -> None:
    # Given checked-in bytes signed by the existing test-only key, without re-signing.
    fixtures = TRAJECTORY_FIXTURE.parent
    # When the real execution evidence policy verifies them.
    outcome = verify_execution_attestation_evidence(
        envelope_path=fixtures / "execution-v2" / case / "execution.dsse",
        artifact=ARTIFACT,
        trust_root_path=fixtures / "trust_root.json",
        allowed_signers_path=fixtures / "allowed_signers",
        trusted_root_version=VERSION,
        backend=SshKeygenBackend(),
        expected_audience="audit-project",
        collateral=COLLATERAL,
        harness_config_digest=HARNESS_DIGEST,
    )
    # Then historical non-JSON config bytes cannot satisfy the canonical config interface.
    if case == "clean":
        assert outcome.reason is AttestationFailureReason.EXECUTION_HARNESS_CONFIG_DIVERGENT
    else:
        assert_refused(outcome, AttestationFailureReason.EXECUTION_HARNESS_CONFIG_DIVERGENT)
