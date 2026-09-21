"""Diagnosis values carry no release authority or raw trajectory payloads."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

BACKFILL_FORBIDDEN_PREFIXES: Final = (".seed/", ".audit/attestations/")
GROUP_SIZE: Final = 8
CEILING: Final = 0.40
CONFIDENCE: Final = 0.95
HEADLINE: Final = (
    "Eight rollouts per configuration form ONE pass@8 group, not eight. "
    "Eight-run configurations fail the group-count requirement before compaction is considered."
)


class Failure(StrEnum):
    FORBIDDEN_WRITE = "BACKFILL_FORBIDDEN_WRITE"
    INPUT_TOO_LARGE = "BACKFILL_INPUT_TOO_LARGE"
    UNSAFE_PATH = "BACKFILL_UNSAFE_PATH"
    MALFORMED = "BACKFILL_INPUT_MALFORMED"
    FAMILY_UNRECOGNIZED = "FIDELITY_FAMILY_UNRECOGNIZED"
    NO_DIAGNOSIS = "BACKFILL_NO_APPLICABLE_DISPOSITION"


@dataclass(frozen=True, slots=True)
class BackfillError(ValueError):
    reason: Failure

    def __str__(self) -> str:
        return self.reason.value


class Disposition(StrEnum):
    CONFIRMED_SUPPRESSION = "confirmed_suppression"
    UNKNOWN_COVERAGE = "unknown_coverage"
    INSUFFICIENT_GROUPS = "insufficient_groups"


@dataclass(frozen=True, slots=True)
class ConfigurationDiagnosis:
    configuration: str
    rollout_count: int
    group_count: int
    remainder_rollouts: int
    worst_case_successes: int
    worst_case_upper_bound: float | None
    zero_success_upper_bound: float | None


@dataclass(frozen=True, slots=True)
class BundleDiagnosis:
    bundle: str
    disposition: Disposition
    confirmed_suppression: tuple[str, ...]
    unknown_coverage: tuple[str, ...]
    insufficient_groups: tuple[str, ...]
    rollout_count: int
    group_count: int
    comparisons: int
    minimum_groups: int
    required_groups: int
    configurations: tuple[ConfigurationDiagnosis, ...]
    historical_execution: str | None
    arithmetic_conclusion: str
    headline: str = HEADLINE
    comparison_assumption: str = (
        "one look times observed model configurations; optimistic lower bound"
    )
    population_standing: str = (
        "derived groups are not a precommitted or independently verified population"
    )
    outcome_assumption: str = (
        "historical scores are unverified; every outcome is imputed successful in worst-case bounds"
    )
    authority: str = (
        "diagnosis only; fresh independent pilots required, never retroactive attestation"
    )
