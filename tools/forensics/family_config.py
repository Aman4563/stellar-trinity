"""Re-derived config standing; grants and effective bytes come from verified custody."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import harness_config as hc
    from tools.attest.canonical import CanonicalizationError
else:
    try:
        from tools import harness_config as hc
        from tools.attest.canonical import CanonicalizationError
    except ModuleNotFoundError:
        import harness_config as hc
        from attest.canonical import CanonicalizationError

from .bundle import Authorization
from .filesystem import read_regular
from .reading import TraceReadError, document

MAX_CONFIG_BYTES: Final = 1024 * 1024


@dataclass(frozen=True, slots=True)
class FidelityConfig:
    """Caller authenticates the precommitment, approval and effective capture separately.

    source is an immutable committed snapshot, not a candidate-selected trust root.
    trace_version is the attested carrier version (ATIF may differ from the harness).
    Neither this value nor the family runner verifies signatures or grants authority.
    """

    source: Path
    mirror: bytes | None
    bound_digest: str | None
    effective: bytes | None
    approved_digest: str | None
    adequacy: hc.HarnessApproval | None
    trace_version: str | None = None


@dataclass(frozen=True, slots=True)
class ConfigStanding:
    pinned: bool
    reconciliation: hc.ReconcileOutcome
    adequacy: hc.AdequacyOutcome
    digest: str | None
    authorization: Authorization
    harness_version: str


def config_standing(binding: FidelityConfig) -> ConfigStanding:
    try:
        raw = read_regular(
            binding.source,
            project_root=Path(binding.source.absolute().anchor),
            max_bytes=MAX_CONFIG_BYTES,
        )
        document(raw)
    except (OSError, TraceReadError):
        raw = None
    bound = hc.parse_harness_config(raw).config
    effective = hc.parse_harness_config(binding.effective).config
    digest = hc.harness_config_digest(raw) if raw is not None and bound is not None else None
    observed = (
        hc.harness_config_digest(binding.effective)
        if binding.effective is not None and effective is not None
        else None
    )
    mirrored = False
    if raw is not None and binding.mirror is not None:
        try:
            mirrored = hc.mirror_matches(raw, binding.mirror)
        except CanonicalizationError:
            mirrored = False
    pinned = bool(digest and digest == binding.bound_digest == binding.approved_digest and mirrored)
    reconciliation = hc.reconcile(digest, observed, bound, effective)
    adequacy = hc.AdequacyOutcome(
        False, hc.HarnessConfigFailureReason.HARNESS_CONFIG_UNAPPROVED, ""
    )
    authorization = Authorization()
    version = binding.trace_version or ""
    if bound is not None:
        adequacy = hc.evaluate_adequacy(bound, binding.adequacy, binding.adequacy)
        authorization = Authorization(
            compaction=bound.compaction_policy.enabled,
            max_message_chars=bound.observation_truncation.max_message_chars,
            max_turns=bound.max_turns,
            max_iterations=bound.max_iterations,
            context_window_tokens=bound.context_window_tokens,
            timeout_seconds=bound.wall_clock_timeout_seconds,
        )
        version = binding.trace_version or bound.harness_version
    return ConfigStanding(pinned, reconciliation, adequacy, digest, authorization, version)
