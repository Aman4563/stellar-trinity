"""Fail-closed policy for CRUCIBLE external execution attestations."""

# allow: SIZE_OK - Preserve refusal paths and keyword APIs; new rules live in execution_fidelity.

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

from ..backend import SignatureBackend, VerificationFailureReason
from ..canonical import CanonicalizationError, parse_json
from ..dsse import parse_envelope
from ..errors import AttestationFailureReason, AttestationOutcome
from ..intoto import (
    RELEASE_EXECUTION_PREDICATE,
    ExecutionPredicate,
    ExecutionPredicateV2,
    StatementV1,
    parse_statement,
    validate_subject_binding,
)
from ..merkle import (
    TRAJECTORY_MERKLE_PROFILE,
    TrajectoryFailureReason,
    TrajectoryManifest,
    TrajectoryOutcome,
    parse_trajectory_manifest,
    verify_trajectory_root,
)
from ..replay import ReplayGuard
from ..verify import (
    IN_TOTO_PAYLOAD_TYPE,
    AttestationEvidence,
    admit_attestation_evidence,
    verify_attestation_evidence_result,
)
from . import execution_fidelity
from .execution_fidelity import ExecutionRequirements, verify_telemetry_population

release_version_failure = execution_fidelity.release_version_failure

if TYPE_CHECKING:
    from tools.forensics.filesystem import read_regular
    from tools.project_paths import ProjectPathError, resolve_project_path
else:
    try:
        from tools.forensics.filesystem import read_regular
        from tools.project_paths import ProjectPathError, resolve_project_path
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from forensics.filesystem import read_regular
        from project_paths import ProjectPathError, resolve_project_path

EXECUTION_OPERATOR_ROLE = "execution_operator"
MAX_TRAJECTORY_BYTES: Final = 16 * 1024 * 1024
MAX_TRAJECTORY_TOTAL_BYTES: Final = 64 * 1024 * 1024


def gate_evaluation_time() -> datetime:
    return datetime.now(UTC)


def _read_statement(path: Path) -> tuple[StatementV1 | None, AttestationOutcome | None]:
    try:
        document = path.read_bytes()
    except FileNotFoundError:
        return None, AttestationOutcome.refuse(
            AttestationFailureReason.ENVELOPE_MISSING,
            f"attestation envelope file is missing: {path}",
        )
    except OSError as error:
        return None, AttestationOutcome.refuse(
            AttestationFailureReason.ENVELOPE_UNREADABLE,
            f"attestation envelope file is unreadable: {path}: {error}",
        )

    parsed_envelope = parse_envelope(document)
    if parsed_envelope.envelope is None:
        reason = parsed_envelope.reason or AttestationFailureReason.ENVELOPE_MALFORMED
        if reason is AttestationFailureReason.ENVELOPE_UNREADABLE:
            reason = AttestationFailureReason.ENVELOPE_MALFORMED
        return None, AttestationOutcome.refuse(reason, parsed_envelope.detail)

    try:
        payload = parse_json(parsed_envelope.envelope.payload)
    except CanonicalizationError as error:
        return None, AttestationOutcome.refuse(
            AttestationFailureReason.STATEMENT_MALFORMED,
            f"attestation statement payload is malformed: {error}",
        )
    parsed_statement = parse_statement(payload)
    if parsed_statement.statement is None:
        return None, parsed_statement.outcome
    return parsed_statement.statement, None


def _execution_interval_failure(
    statement: StatementV1,
    evaluation_time: datetime,
) -> AttestationOutcome | None:
    predicate = statement.predicate
    if not isinstance(predicate, (ExecutionPredicate, ExecutionPredicateV2)):
        return None
    interval = predicate.execution_interval
    if interval.started_at <= evaluation_time <= interval.ended_at:
        return None
    return AttestationOutcome.refuse(
        VerificationFailureReason.EVALUATION_TIME_INVALID,
        f"gate evaluation instant {evaluation_time.isoformat()} falls outside signed execution "
        f"interval {interval.started_at.isoformat()} through {interval.ended_at.isoformat()}",
    )


def declared_execution_interval_failure(
    envelope_path: Path,
    evaluation_time: datetime,
) -> AttestationOutcome | None:
    statement, structural_failure = _read_statement(envelope_path)
    if structural_failure is not None:
        return structural_failure
    if statement is None:
        return AttestationOutcome.refuse(
            AttestationFailureReason.STATEMENT_MALFORMED,
            "attestation statement parsing produced no result",
        )
    return _execution_interval_failure(statement, evaluation_time)


def _trajectory_resource_refused(detail: str) -> TrajectoryOutcome:
    return TrajectoryOutcome.refuse(
        TrajectoryFailureReason.EXECUTION_TRAJECTORY_RESOURCE_REFUSED,
        detail,
    )


def resolve_trajectory_documents(
    parent_root: Path,
    manifest: TrajectoryManifest,
) -> tuple[dict[str, bytes] | None, TrajectoryOutcome]:
    """Read every manifest rollout as raw bytes without escaping the parent root."""

    try:
        resolved_root = parent_root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        return None, _trajectory_resource_refused(
            f"parent project root is missing or unreadable: {error}"
        )
    if not resolved_root.is_dir():
        return None, _trajectory_resource_refused("parent project root is not a directory")

    documents: dict[str, bytes] = {}
    total_bytes = 0
    for entry in manifest.rollouts:
        if not entry.path.startswith("./"):
            return None, _trajectory_resource_refused(
                f"trajectory document path {entry.path!r} must start with './'"
            )
        try:
            resolved_resource = resolve_project_path(
                entry.path,
                project_root=resolved_root,
                description="trajectory document path",
                must_exist=True,
            )
            resolved_resource.relative_to(resolved_root)
            if not resolved_resource.is_file():
                return None, _trajectory_resource_refused(
                    f"trajectory document {entry.path!r} is not a regular file"
                )
            raw = read_regular(
                resolved_root / entry.path,
                project_root=resolved_root,
                max_bytes=min(MAX_TRAJECTORY_BYTES, MAX_TRAJECTORY_TOTAL_BYTES - total_bytes),
            )
            total_bytes += len(raw)
            documents[entry.path] = raw
        except (OSError, ProjectPathError, RuntimeError, ValueError) as error:
            return None, _trajectory_resource_refused(
                f"trajectory document {entry.path!r} is missing, unreadable, or escapes the "
                f"parent project root: {error}"
            )
    return documents, TrajectoryOutcome.accept()


def verify_execution_trajectory(
    predicate: ExecutionPredicate | ExecutionPredicateV2,
    *,
    parent_root: Path | None,
    collateral: Mapping[str, bytes] | None,
) -> TrajectoryOutcome:
    """Recompute a profile-gated execution trajectory root from parent-project bytes."""

    if predicate.trajectory_root.name != TRAJECTORY_MERKLE_PROFILE:
        return TrajectoryOutcome.accept()
    manifest_name = predicate.population_sequence_commitment.name
    if collateral is None or manifest_name not in collateral:
        return _trajectory_resource_refused(
            f"trajectory manifest collateral is missing for {manifest_name!r}"
        )
    manifest_document = collateral[manifest_name]
    if type(manifest_document) is not bytes:
        return _trajectory_resource_refused(
            "trajectory manifest must be supplied as immutable bytes"
        )
    parsed = parse_trajectory_manifest(manifest_document)
    if parsed.manifest is None:
        return parsed.outcome
    if parent_root is None:
        return _trajectory_resource_refused(
            "trajectory verification requires the parent project resource root"
        )
    trajectory_documents, resolution = resolve_trajectory_documents(parent_root, parsed.manifest)
    if trajectory_documents is None:
        return resolution
    return verify_trajectory_root(
        manifest_document,
        trajectory_documents,
        predicate.trajectory_root.digest.sha256,
    )


def _trajectory_attestation_outcome(
    statement: StatementV1,
    accepted: AttestationOutcome,
    *,
    parent_root: Path | None,
    collateral: Mapping[str, bytes] | None,
) -> AttestationOutcome:
    predicate = statement.predicate
    if not isinstance(predicate, ExecutionPredicateV2):
        return AttestationOutcome.refuse(
            AttestationFailureReason.PREDICATE_TYPE_UNKNOWN,
            f"execution policy requires predicateType {RELEASE_EXECUTION_PREDICATE!r}",
        )
    trajectory = verify_execution_trajectory(
        predicate,
        parent_root=parent_root,
        collateral=collateral,
    )
    if trajectory.accepted:
        telemetry = verify_telemetry_population(predicate, collateral)
        return accepted if telemetry.accepted else telemetry
    if trajectory.reason is None:
        return AttestationOutcome.refuse(
            VerificationFailureReason.OUTPUT_UNPARSEABLE,
            "trajectory verification refused without a reason",
        )
    return AttestationOutcome.refuse(trajectory.reason, trajectory.detail)


def _execution_policy_outcome(
    evidence: AttestationEvidence,
    artifact: bytes,
    *,
    evaluation_time: datetime,
    expected_audience: str | None,
    subject_name: str | None,
    collateral: Mapping[str, bytes] | None,
    parent_root: Path | None,
) -> AttestationOutcome:
    if not evidence.outcome.accepted:
        return evidence.outcome
    statement = evidence.statement
    if statement is None:
        return AttestationOutcome.refuse(
            VerificationFailureReason.OUTPUT_UNPARSEABLE,
            "execution evidence verification accepted without a parsed statement",
        )
    if statement.predicate_type != RELEASE_EXECUTION_PREDICATE:
        return AttestationOutcome.refuse(
            AttestationFailureReason.EXECUTION_PREDICATE_VERSION_UNSUPPORTED,
            f"observed predicateType {statement.predicate_type!r}; "
            f"required {RELEASE_EXECUTION_PREDICATE!r}",
        )
    interval_failure = _execution_interval_failure(statement, evaluation_time)
    if interval_failure is not None:
        return interval_failure
    if expected_audience is not None and statement.predicate.replay.audience != expected_audience:
        return AttestationOutcome.refuse(
            AttestationFailureReason.AUDIENCE_MISMATCH,
            "signed replay audience does not match the execution gate audience",
        )
    subject_outcome = validate_subject_binding(statement, artifact, subject_name=subject_name)
    if not subject_outcome.accepted:
        return subject_outcome
    return _trajectory_attestation_outcome(
        statement,
        evidence.outcome,
        parent_root=parent_root,
        collateral=collateral,
    )


def _read_artifact(path: Path) -> tuple[bytes | None, AttestationOutcome | None]:
    try:
        return path.read_bytes(), None
    except FileNotFoundError:
        return None, AttestationOutcome.refuse(
            AttestationFailureReason.SUBJECT_MISSING,
            f"subject artifact is missing: {path}",
        )
    except OSError as error:
        return None, AttestationOutcome.refuse(
            AttestationFailureReason.SUBJECT_MISSING,
            f"subject artifact is unreadable: {path}: {error}",
        )


def verify_execution_attestation_evidence(
    *,
    envelope_path: Path,
    artifact: bytes,
    trust_root_path: Path,
    allowed_signers_path: Path,
    trusted_root_version: int,
    backend: SignatureBackend,
    expected_audience: str,
    subject_name: str | None = None,
    collateral: Mapping[str, bytes] | None = None,
    parent_root: Path | None = None,
    release_required: bool = True,
    harness_config_digest: str | None = None,
) -> AttestationOutcome:
    """Revalidate execution evidence and trajectories without replay-store mutation."""

    evaluation_time = gate_evaluation_time()
    evidence = verify_attestation_evidence_result(
        envelope_path=envelope_path,
        trust_root_path=trust_root_path,
        allowed_signers_path=allowed_signers_path,
        required_role=EXECUTION_OPERATOR_ROLE,
        evaluation_time=evaluation_time,
        trusted_root_version=trusted_root_version,
        backend=backend,
        collateral=collateral,
        expected_payload_type=IN_TOTO_PAYLOAD_TYPE,
        statement_parser=ExecutionRequirements(
            release_required, harness_config_digest, collateral
        ).parse,
    )
    return _execution_policy_outcome(
        evidence,
        artifact,
        evaluation_time=evaluation_time,
        expected_audience=expected_audience,
        subject_name=subject_name,
        collateral=collateral,
        parent_root=parent_root,
    )


def verify_execution_attestation(
    *,
    envelope_path: Path,
    artifact_path: Path,
    trust_root_path: Path,
    allowed_signers_path: Path,
    trusted_root_version: int,
    backend: SignatureBackend,
    replay_guard: ReplayGuard,
    subject_name: str | None = None,
    collateral: Mapping[str, bytes] | None = None,
    parent_root: Path | None = None,
    release_required: bool = True,
    harness_config_digest: str | None = None,
) -> AttestationOutcome:
    """Decide whether one execution envelope authorizes evidence for a frozen artifact."""

    evaluation_time = gate_evaluation_time()
    evidence = verify_attestation_evidence_result(
        envelope_path=envelope_path,
        trust_root_path=trust_root_path,
        allowed_signers_path=allowed_signers_path,
        required_role=EXECUTION_OPERATOR_ROLE,
        evaluation_time=evaluation_time,
        trusted_root_version=trusted_root_version,
        backend=backend,
        collateral=collateral,
        expected_payload_type=IN_TOTO_PAYLOAD_TYPE,
        statement_parser=ExecutionRequirements(
            release_required, harness_config_digest, collateral
        ).parse,
    )
    if not evidence.outcome.accepted:
        return evidence.outcome
    artifact, artifact_failure = _read_artifact(artifact_path)
    if artifact is None:
        if artifact_failure is not None:
            return artifact_failure
        return AttestationOutcome.refuse(
            AttestationFailureReason.SUBJECT_MISSING,
            "subject artifact read produced no bytes and no reason",
        )
    policy_outcome = _execution_policy_outcome(
        evidence,
        artifact,
        evaluation_time=evaluation_time,
        expected_audience=None,
        subject_name=subject_name,
        collateral=collateral,
        parent_root=parent_root,
    )
    if not policy_outcome.accepted:
        return policy_outcome
    return admit_attestation_evidence(evidence, replay_guard)
