"""Immutable supplied artifacts and configuration authorization, never filesystem access."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

from .core import FidelityOutcome, FidelityRefusal, RolloutFidelity

MAX_TRACE_BYTES: Final = 4 * 1024 * 1024
MAX_TRACE_LINES: Final = 100_000
MAX_BUNDLE_FILES: Final = 32
RAW_AGENT_PATHS: Final = ("agent/agent.jsonl", "agent.jsonl")
NATIVE_FAMILIES: Final = frozenset(
    {
        "claude_code_jsonl",
        "openhands_events",
        "openhands_native_metrics",
        "cybergym_usage",
    }
)


@dataclass(frozen=True, slots=True)
class Authorization:
    """Bound policy supplied by the caller, never inferred from trace declarations."""

    compaction: bool = False
    max_message_chars: int | None = None
    max_turns: int | None = None
    max_iterations: int | None = None
    context_window_tokens: int | None = None
    timeout_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class TraceBundle:
    family: str
    harness_version: str
    files: Mapping[str, bytes] = field(default_factory=dict)
    accompaniment: frozenset[str] = frozenset()
    authorization: Authorization = Authorization()
    rollout_id: str = "synthetic-rollout"

    def __post_init__(self) -> None:
        object.__setattr__(self, "files", MappingProxyType(dict(self.files)))


FamilyAdapter = Callable[[TraceBundle], RolloutFidelity]


def strongest_supported_outcome(
    family: str, accompaniment: frozenset[str]
) -> tuple[FidelityOutcome, FidelityRefusal | None]:
    """Format ceiling only: positive violations survive; coverage still needs proof.

    Accompaniment names are family keys plus raw_agent_jsonl. Adapters derive the
    latter from supplied bytes, never accepting a claim of a nonexistent source.
    """
    if family == "atif_normalized":
        sources = accompaniment & NATIVE_FAMILIES
        if len(sources) == 1:
            return strongest_supported_outcome(next(iter(sources)), accompaniment)
        return (
            FidelityOutcome.INSUFFICIENT_EVIDENCE,
            FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY,
        )
    if family == "cybergym_usage" and "raw_agent_jsonl" not in accompaniment:
        return (FidelityOutcome.INSUFFICIENT_EVIDENCE, FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY)
    if family in NATIVE_FAMILIES:
        return FidelityOutcome.COVERED_CLEAN, None
    return (FidelityOutcome.INSUFFICIENT_EVIDENCE, FidelityRefusal.FIDELITY_FAMILY_UNRECOGNIZED)
