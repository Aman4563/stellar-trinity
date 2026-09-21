"""Three-valued fidelity semantics over independently classified findings.

The summarization_count: 0 under enable_summarize: false incident demonstrates
why a self-reported zero is FIDELITY_SELF_REPORTED_ONLY -> INSUFFICIENT_EVIDENCE,
never COVERED_CLEAN. Absence of a record is not a record of absence.
An approved timeout or turn cap that fired exactly as declared is COVERED_CLEAN,
not a violation: faithfully enforcing an approved limit is conforming behaviour.
Only an unapproved or undeclared transformation is a violation.

This core reads no files and knows no family-specific coverage ceilings. Adapters
must supply coverage-backed findings and enforce their format's ceiling before
returning a rollout. A positive violation needs no coverage proof.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, assert_never

TRIAL_CONFORMANCE_RULE: Final = "trinity.trial-conformance/v1"
TRIAL_STATUSES: Final = frozenset({"conforming", "nonconforming", "indeterminate"})
_EVIDENCE_POINTER: Final = re.compile(r"[A-Za-z0-9_./-]+:[1-9][0-9]*(?:#pre_tokens=[0-9]+)?")


class FidelityOutcome(StrEnum):
    VIOLATION = "VIOLATION"
    COVERED_CLEAN = "COVERED_CLEAN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class SignalClass(StrEnum):
    COMPACTION = "COMPACTION"
    OBSERVATION_TRUNCATION = "OBSERVATION_TRUNCATION"
    TURN_CAP = "TURN_CAP"
    TIMEOUT = "TIMEOUT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    REFUSAL = "REFUSAL"
    SETUP_FAILURE = "SETUP_FAILURE"
    HANDOFF_FAILURE = "HANDOFF_FAILURE"


class FidelityRefusal(StrEnum):
    FIDELITY_FAMILY_UNRECOGNIZED = "FIDELITY_FAMILY_UNRECOGNIZED"
    FIDELITY_VERSION_UNSUPPORTED = "FIDELITY_VERSION_UNSUPPORTED"
    FIDELITY_TRACE_CONVERSION_ONLY = "FIDELITY_TRACE_CONVERSION_ONLY"
    FIDELITY_SEQUENCE_INCOMPLETE = "FIDELITY_SEQUENCE_INCOMPLETE"
    FIDELITY_SELF_REPORTED_ONLY = "FIDELITY_SELF_REPORTED_ONLY"
    FIDELITY_TRACE_UNREADABLE = "FIDELITY_TRACE_UNREADABLE"


class EvidencePointerError(ValueError):
    """Reject a malformed locator without retaining or echoing trace content."""

    def __str__(self) -> str:
        return "evidence pointer must be a whitespace-free path:positive-line locator"


@dataclass(frozen=True, slots=True)
class SignalFinding:
    """One classified signal, referencing evidence by locator rather than payload."""

    signal: SignalClass
    outcome: FidelityOutcome
    refusal: FidelityRefusal | None
    evidence_pointer: str

    def __post_init__(self) -> None:
        if _EVIDENCE_POINTER.fullmatch(self.evidence_pointer) is None:
            raise EvidencePointerError


@dataclass(frozen=True, slots=True)
class RolloutFidelity:
    rollout_id: str
    family: str
    findings: tuple[SignalFinding, ...]

    @property
    def overall(self) -> FidelityOutcome:
        """Reduce all observations; duplicates never replace a missing signal class."""
        covered: set[SignalClass] = set()
        insufficient = False
        for finding in self.findings:
            match finding.outcome:
                case FidelityOutcome.VIOLATION:
                    return FidelityOutcome.VIOLATION
                case FidelityOutcome.INSUFFICIENT_EVIDENCE:
                    insufficient = True
                case FidelityOutcome.COVERED_CLEAN:
                    covered.add(finding.signal)
                case unreachable:
                    assert_never(unreachable)
        if insufficient or covered != set(SignalClass):
            return FidelityOutcome.INSUFFICIENT_EVIDENCE
        return FidelityOutcome.COVERED_CLEAN


def demonstrates_coverage(
    family_recognized: bool,
    version_supported: bool,
    native_trace: bool,
    marker_vocabulary_known: bool,
    sequence_contiguous: bool,
) -> tuple[bool, FidelityRefusal | None]:
    """Return the first refusal: family, version, native, vocabulary, sequence.

    The five independent booleans are the specified public coverage contract.
    Unknown marker vocabulary is a version fact. Self-report-only support and
    unreadable traces are classified separately by adapters, not by this predicate.
    """
    for passed, refusal in (
        (family_recognized, FidelityRefusal.FIDELITY_FAMILY_UNRECOGNIZED),
        (version_supported, FidelityRefusal.FIDELITY_VERSION_UNSUPPORTED),
        (native_trace, FidelityRefusal.FIDELITY_TRACE_CONVERSION_ONLY),
        (marker_vocabulary_known, FidelityRefusal.FIDELITY_VERSION_UNSUPPORTED),
        (sequence_contiguous, FidelityRefusal.FIDELITY_SEQUENCE_INCOMPLETE),
    ):
        if not passed:
            return False, refusal
    return True, None


def map_trial_status(rollout: RolloutFidelity) -> str:
    """Apply trinity.trial-conformance/v1, independently of solver success."""
    match rollout.overall:
        case FidelityOutcome.VIOLATION:
            return "nonconforming"
        case FidelityOutcome.INSUFFICIENT_EVIDENCE:
            return "indeterminate"
        case FidelityOutcome.COVERED_CLEAN:
            return "conforming"
        case unreachable:
            assert_never(unreachable)
