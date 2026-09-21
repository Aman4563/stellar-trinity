"""Release-only fidelity checks over explicit inputs, never candidate policy files."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from ..canonical import JSONValue
from ..errors import AttestationFailureReason, AttestationOutcome
from ..intoto import (
    RELEASE_EXECUTION_PREDICATE,
    ExecutionPredicateV2,
    StatementParseResult,
    parse_statement,
)
from ..merkle import parse_trajectory_manifest

V2_OBLIGATIONS: Final = (
    "harnessConfig",
    "populationRoster",
    "observationCapture",
    "effectiveConfigReconciliation",
    "rolloutTelemetry",
)


def release_version_failure(value: JSONValue) -> AttestationOutcome | None:
    if isinstance(value, dict):
        observed = value.get("predicateType")
        if observed != RELEASE_EXECUTION_PREDICATE:
            return AttestationOutcome.refuse(
                AttestationFailureReason.EXECUTION_PREDICATE_VERSION_UNSUPPORTED,
                f"observed predicateType {observed!r}; required {RELEASE_EXECUTION_PREDICATE!r}",
            )
    return None


@dataclass(frozen=True, slots=True)
class ExecutionRequirements:
    release_required: bool
    harness_config_digest: str | None
    collateral: Mapping[str, bytes] | None

    def parse(self, value: JSONValue) -> StatementParseResult:
        if self.release_required:
            failure = release_version_failure(value)
            if failure is not None:
                return StatementParseResult(None, failure)
        parsed = parse_statement(value)
        if not self.release_required:
            status = "parsed" if parsed.statement is not None else "structurally refused"
            obligations = "; ".join(f"{name}=unverifiable" for name in V2_OBLIGATIONS)
            return StatementParseResult(
                parsed.statement,
                AttestationOutcome.refuse(
                    AttestationFailureReason.EXECUTION_DIAGNOSIS_ONLY,
                    f"diagnosis only: {status}, not authenticated or release-authorizing; "
                    f"{obligations}; {parsed.outcome.detail}",
                ),
            )
        if parsed.statement is None:
            return parsed
        predicate = parsed.statement.predicate
        assert isinstance(predicate, ExecutionPredicateV2)
        for resource, reason in (
            (predicate.population_roster, AttestationFailureReason.EXECUTION_ROSTER_UNBOUND),
            (predicate.observation_capture, AttestationFailureReason.EXECUTION_CAPTURE_UNBOUND),
        ):
            if self.collateral is None or resource.name not in self.collateral:
                return StatementParseResult(
                    None,
                    AttestationOutcome.refuse(
                        reason,
                        f"required collateral bytes are missing for {resource.name!r}",
                    ),
                )
        if predicate.harness_config.digest.sha256 != self.harness_config_digest:
            return StatementParseResult(
                None,
                AttestationOutcome.refuse(
                    AttestationFailureReason.EXECUTION_HARNESS_CONFIG_DIVERGENT,
                    f"signed harnessConfig digest {predicate.harness_config.digest.sha256!r} "
                    f"differs from supplied pilot policy digest {self.harness_config_digest!r}",
                ),
            )
        return parsed


def verify_telemetry_population(
    predicate: ExecutionPredicateV2,
    collateral: Mapping[str, bytes] | None,
) -> AttestationOutcome:
    name = predicate.population_sequence_commitment.name
    if collateral is None or name not in collateral:
        return AttestationOutcome.refuse(
            AttestationFailureReason.EXECUTION_TELEMETRY_INCONSISTENT,
            "rolloutTelemetry requires the committed trajectory manifest",
        )
    parsed = parse_trajectory_manifest(collateral[name])
    if parsed.manifest is None:
        return AttestationOutcome.refuse(
            AttestationFailureReason.EXECUTION_TELEMETRY_INCONSISTENT,
            f"rolloutTelemetry population is unverifiable: {parsed.outcome.detail}",
        )
    expected = {entry.rollout_id for entry in parsed.manifest.rollouts}
    observed = {entry.rollout for entry in predicate.rollout_telemetry}
    if observed != expected:
        return AttestationOutcome.refuse(
            AttestationFailureReason.EXECUTION_TELEMETRY_INCONSISTENT,
            "rolloutTelemetry differs from trajectory manifest: "
            f"missing {sorted(expected - observed)!r}; "
            f"extra {sorted(observed - expected)!r}",
        )
    return AttestationOutcome.accept(())
