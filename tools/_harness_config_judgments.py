"""Independent approval checks and value-redacted configuration reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, assert_never

if TYPE_CHECKING:
    from tools._harness_config_schema import ApprovalSource, HarnessConfigFailureReason
    from tools.attest.canonical import canonical_sha256, parse_json
    from tools.harness_config import HarnessConfig
else:
    try:
        from tools._harness_config_schema import ApprovalSource, HarnessConfigFailureReason
        from tools.attest.canonical import canonical_sha256, parse_json
    except ModuleNotFoundError:  # pragma: no cover - direct tools/ execution
        from _harness_config_schema import ApprovalSource, HarnessConfigFailureReason
        from attest.canonical import canonical_sha256, parse_json


@dataclass(frozen=True, slots=True)
class HarnessApproval:
    """Human-owned grant resolved independently of the configuration declaration.

    Callers must supply the recorded requirements value or touchstones disposition,
    never construct a grant from the candidate's self-declared approval.
    """

    authorizes_compaction: bool
    min_message_chars: int
    min_headroom_tokens: int
    source: ApprovalSource
    approved_by: str


@dataclass(frozen=True, slots=True)
class AdequacyOutcome:
    """Machine-checkable adequacy standing, not a human sufficiency judgment."""

    accepted: bool
    reason: HarnessConfigFailureReason | None
    detail: str


@dataclass(frozen=True, slots=True)
class ReconcileOutcome:
    """Binding standing with field names only in drift details."""

    accepted: bool
    reason: HarnessConfigFailureReason | None
    detail: str


def evaluate_adequacy(
    config: HarnessConfig,
    requirements_value: HarnessApproval | None,
    touchstones_disposition: HarnessApproval | None,
) -> AdequacyOutcome:
    """Check independent approval before the machine-checkable adequacy predicates.

    Residual adequacy, including whether 168,000 tokens suffice for a 300-turn
    task, is a human judgment registered as a DEFERRED.md row, not a silent pass.
    Compaction is explicitly opt-in: anthropics/claude-code #64520 documents the
    v2.1.159 silent-default failure this authorization requirement prevents.
    """
    declaration = config.configuration_adequacy
    match declaration.approval_source:
        case ApprovalSource.REQUIREMENTS:
            approval = requirements_value
        case ApprovalSource.TOUCHSTONES:
            approval = touchstones_disposition
        case unreachable:
            assert_never(unreachable)
    if (
        approval is None
        or approval.source != declaration.approval_source
        or approval.approved_by != declaration.approved_by
    ):
        return AdequacyOutcome(
            False, HarnessConfigFailureReason.HARNESS_CONFIG_UNAPPROVED, "configurationAdequacy"
        )
    inadequate = tuple(
        name
        for name, failed in (
            ("headroomArgument", not declaration.headroom_argument.strip()),
            (
                "compactionPolicy",
                config.compaction_policy.enabled and not approval.authorizes_compaction,
            ),
            (
                "maxMessageChars",
                config.observation_truncation.max_message_chars < approval.min_message_chars,
            ),
            (
                "contextWindowTokens, maxOutputTokens",
                config.context_window_tokens - config.max_output_tokens
                < approval.min_headroom_tokens,
            ),
        )
        if failed
    )
    if inadequate:
        return AdequacyOutcome(
            False, HarnessConfigFailureReason.HARNESS_CONFIG_INADEQUATE, ", ".join(inadequate)
        )
    return AdequacyOutcome(True, None, "")


def reconcile(
    bound_digest: str | None,
    observed_digest: str | None,
    bound_config: HarnessConfig | None,
    observed_config: HarnessConfig | None,
) -> ReconcileOutcome:
    """Compare the two bindings without disclosing configuration values.

    The four inputs preserve the public binding API: each side supplies its
    independently computed digest and parsed configuration for redacted diagnostics.
    """
    if not bound_digest or not observed_digest or bound_config is None or observed_config is None:
        return ReconcileOutcome(False, HarnessConfigFailureReason.HARNESS_CONFIG_MISSING, "")
    differing = []
    for field in fields(bound_config):
        if getattr(bound_config, field.name) != getattr(observed_config, field.name):
            first, *rest = field.name.split("_")
            differing.append(first + "".join(part.capitalize() for part in rest))
    if bound_digest != observed_digest or differing:
        return ReconcileOutcome(
            False, HarnessConfigFailureReason.HARNESS_CONFIG_DRIFT, ", ".join(sorted(differing))
        )
    return ReconcileOutcome(True, None, "")


def mirror_matches(source_bytes: bytes, mirrored_bytes: bytes) -> bool:
    """Compare canonical digests; malformed JSON raises CanonicalizationError."""
    return canonical_sha256(parse_json(source_bytes)) == canonical_sha256(
        parse_json(mirrored_bytes)
    )
