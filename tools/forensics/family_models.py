"""Private family results and authenticated-input contracts, never release authority."""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools.harness_config import HarnessConfigFailureReason
else:
    try:
        from tools.harness_config import HarnessConfigFailureReason
    except ModuleNotFoundError:
        from harness_config import HarnessConfigFailureReason

from .core import FidelityOutcome as O
from .core import RolloutFidelity, SignalClass, SignalFinding, map_trial_status
from .family_config import ConfigStanding

GROUP_SIZE: Final = 8


class PrivateReason(StrEnum):
    CONFIG_UNPINNED = "config-unpinned"
    CONFIG_DRIFT = "config-drift"
    CONFIG_INADEQUATE = "config-inadequate"
    HANDOFF_UNVERIFIED = "handoff-unverified"
    CONTEXT_UNCOVERED = "context-uncovered"
    FIDELITY_UNVERIFIED = "fidelity-unverified"


@dataclass(frozen=True, slots=True)
class ScorerReceipt:
    """Identity observed at the scorer, authenticated by the caller, never the trace."""

    rollout_id: str
    session_id: str
    sha256: str


@dataclass(frozen=True, slots=True)
class FidelityRoster:
    """Precommitted disjoint groups at fixed N, plus independently verified receipts.

    Each identity is its canonical path relative to trajectory_root. Group membership
    is supplied from the verified commitment, never reconstructed from outcomes.
    """

    group_count: int
    groups: tuple[tuple[str, ...], ...]
    scorer_receipts: tuple[ScorerReceipt, ...] = ()
    operator_statuses: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class PopulationStanding:
    extra: tuple[str, ...]
    missing: tuple[str, ...]
    structure_valid: bool

    @property
    def accepted(self) -> bool:
        return self.structure_valid and not self.extra and not self.missing


@dataclass(frozen=True, slots=True)
class FidelityRow:
    trace: RolloutFidelity
    handoff: SignalFinding
    config: ConfigStanding
    population: PopulationStanding
    operator_status: str | None = None

    @property
    def trial_status(self) -> str:
        trace = RolloutFidelity(
            self.trace.rollout_id, self.trace.family, (*self.trace.findings, self.handoff)
        )
        status = map_trial_status(trace)
        if not self.population.accepted:
            return "indeterminate"
        if status == "nonconforming" or (
            self.config.reconciliation.reason is HarnessConfigFailureReason.HARNESS_CONFIG_DRIFT
        ):
            return "nonconforming"
        if not (
            self.config.pinned
            and self.config.reconciliation.accepted
            and self.config.adequacy.accepted
        ):
            return "indeterminate"
        return status

    @property
    def selected_reason(self) -> PrivateReason | None:
        return select_reason(self.config, self.population, (self,))


def select_reason(
    config: ConfigStanding, population: PopulationStanding, rows: tuple[FidelityRow, ...]
) -> PrivateReason | None:
    if not population.accepted:
        return None
    reasons = (
        (
            not config.pinned
            or config.reconciliation.reason is HarnessConfigFailureReason.HARNESS_CONFIG_MISSING,
            PrivateReason.CONFIG_UNPINNED,
        ),
        (not config.reconciliation.accepted, PrivateReason.CONFIG_DRIFT),
        (not config.adequacy.accepted, PrivateReason.CONFIG_INADEQUATE),
        (
            any(row.handoff.outcome is not O.COVERED_CLEAN for row in rows),
            PrivateReason.HANDOFF_UNVERIFIED,
        ),
        (
            any(
                f.signal in {SignalClass.COMPACTION, SignalClass.OBSERVATION_TRUNCATION}
                and f.outcome is O.INSUFFICIENT_EVIDENCE
                for row in rows
                for f in row.trace.findings
            ),
            PrivateReason.CONTEXT_UNCOVERED,
        ),
        (
            not rows
            or any(
                row.trial_status != "conforming" or row.operator_status not in (None, "conforming")
                for row in rows
            ),
            PrivateReason.FIDELITY_UNVERIFIED,
        ),
    )
    return next((reason for applicable, reason in reasons if applicable), None)


@dataclass(frozen=True, slots=True)
class FidelityLedger:
    rows: tuple[FidelityRow, ...]
    config: ConfigStanding
    population: PopulationStanding
    group_count: int
    groups: tuple[tuple[str, ...], ...]

    @property
    def blocked(self) -> bool:
        return not self.population.accepted

    @property
    def selected_reason(self) -> PrivateReason | None:
        return select_reason(self.config, self.population, self.rows)
