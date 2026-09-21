"""Exact reward-distribution statistics and the preregistration gate for CRUCIBLE step 8o.

Step 8o makes the preregistration itself the gate: a statistic chosen once the reward
population is visible is not evidence, so the binding must precede observation. Until this
module existed the contract named no statistic, which left the gate with nothing to compute
and left every operator with nothing to bind. `DEFERRED.md` section 5 recorded that as an
instrument named without a method. This module supplies the method.

The statistic set is closed at six exact figures, recomputed here as `Fraction` values from
committed per-rollout reward bytes:

  * `reward_cardinality`   the rollout count in the population
  * `reward_support`       the count of distinct canonical reward values
  * `reward_floor_mass`    the count at or below the declared null floor
  * `reward_ceiling_mass`  the count at full reward
  * `reward_median`        the exact median
  * `reward_range`         the exact minimum and maximum

Closure is load-bearing. An open set lets a chooser add the one figure that clears, which is
the exact defect the preregistration exists to prevent, so a document binding a seventh name
or omitting one of the six is refused rather than partially honoured. Every figure is exact:
`reward_support` counts canonical rationals, so two byte-distinct spellings of one value
collapse and no floating-point comparison decides membership.

Ordering is proved with machinery that already exists rather than with a second scheme. The
preregistration is committed at `.audit/preregistration/<uuid>.yaml` and its SHA-256 rides as
a bound resource descriptor inside the `trinity.execution/v2` pre-run commitment, whose duty
to predate the execution interval `tools/attest/intoto.py` already enforces. This module
checks agreement between the committed bytes and that descriptor, and checks that the
commitment instant precedes the earliest observed rollout.

The disposition branch reconciles step 8o with step 7g. Step 7g governs every instrument
whose obligation `DEFERRED.md` defers and fixes that such an instrument caps exactly as the
matching coverage gap would and never raises a disposition; step 8o's matching gap is
`D-COVERAGE-GAP` at `HOLD`. A *moved* preregistration is misconduct an operator chose and
stays `BLOCK` regardless. An *absent* preregistration, while `DEF-REWARD-STATISTICS` still
stands, is machinery nobody built and caps at `HOLD`. Without that branch the gate emitted an
unconditional `BLOCK` on every corpus carrying rollouts, which measures the auditor rather
than the audited and carries no information about any particular delivery.

`no_worse_than_gap` states the incentive rule the branch exists to protect: building a
required instrument must never worsen a disposition against not building it. A contract that
punishes compliance is misspecified, and a live instrument reporting an absent preregistration
therefore caps no lower than the gap the same surface would carry with no instrument at all.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from typing import Final

from tools._findings import Finding, Severity

STATISTIC_NAMES: Final[tuple[str, ...]] = (
    "reward_cardinality",
    "reward_support",
    "reward_floor_mass",
    "reward_ceiling_mass",
    "reward_median",
    "reward_range",
)

BLOCK: Final = "BLOCK"
HOLD: Final = "HOLD"

CODE_ABSENT: Final = "D-REWARD-PREREGISTRATION-ABSENT"
CODE_DEFERRED: Final = "D-REWARD-PREREGISTRATION-DEFERRED"
CODE_MOVED: Final = "D-REWARD-PREREGISTRATION-MOVED"
CODE_MALFORMED: Final = "D-REWARD-PREREGISTRATION-MALFORMED"
CODE_UNORDERED: Final = "D-REWARD-PREREGISTRATION-UNORDERED"
CODE_OUT_OF_BOUND: Final = "D-REWARD-STATISTIC-OUT-OF-BOUND"

_HALF: Final = Fraction(1, 2)


class RewardDistributionError(ValueError):
    """An input this module refuses to summarise rather than summarise wrongly."""


@dataclass(frozen=True, slots=True)
class Population:
    """One observed reward population with the floors its bundle declared."""

    rewards: tuple[Fraction, ...]
    null_floor: Fraction
    full_reward: Fraction


@dataclass(frozen=True, slots=True)
class Statistics:
    """The closed six-figure statistic set, every member exact."""

    reward_cardinality: int
    reward_support: int
    reward_floor_mass: int
    reward_ceiling_mass: int
    reward_median: Fraction
    reward_range: tuple[Fraction, Fraction]

    def as_mapping(self) -> dict[str, tuple[Fraction, ...]]:
        """Return every figure as exact rationals keyed by its closed name.

        `reward_range` carries two members and each is bound separately, so normalising
        every figure to a tuple lets one comparison loop cover the whole closed set without
        a special case that could silently skip an endpoint.
        """
        return {
            "reward_cardinality": (Fraction(self.reward_cardinality),),
            "reward_support": (Fraction(self.reward_support),),
            "reward_floor_mass": (Fraction(self.reward_floor_mass),),
            "reward_ceiling_mass": (Fraction(self.reward_ceiling_mass),),
            "reward_median": (self.reward_median,),
            "reward_range": self.reward_range,
        }


@dataclass(frozen=True, slots=True)
class Bound:
    """An inclusive preregistered interval for one statistic."""

    low: Fraction
    high: Fraction

    def holds(self, value: Fraction) -> bool:
        """Return whether `value` sits inside this inclusive interval."""
        return self.low <= value <= self.high


@dataclass(frozen=True, slots=True)
class Preregistration:
    """A parsed, closed statistic set with the digest the attestation must carry."""

    bounds: Mapping[str, Bound]
    digest: str
    committed_at: datetime


def _median(ordered: Sequence[Fraction]) -> Fraction:
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) * _HALF


def compute(population: Population) -> Statistics:
    """Recompute the closed statistic set exactly from a reward population."""
    if not population.rewards:
        raise RewardDistributionError("an empty reward population has no statistics to compute")
    if population.null_floor > population.full_reward:
        raise RewardDistributionError("the declared null floor exceeds the declared full reward")
    ordered = sorted(population.rewards)
    return Statistics(
        reward_cardinality=len(ordered),
        reward_support=len(set(ordered)),
        reward_floor_mass=sum(1 for value in ordered if value <= population.null_floor),
        reward_ceiling_mass=sum(1 for value in ordered if value == population.full_reward),
        reward_median=_median(ordered),
        reward_range=(ordered[0], ordered[-1]),
    )


def preregistration_digest(raw: bytes) -> str:
    """Return the SHA-256 the pre-run commitment must carry for these committed bytes."""
    return hashlib.sha256(raw).hexdigest()


def _finding(code: str, message: str, path: str) -> Finding:
    return Finding(code, Severity.ERROR, path, None, message)


def parse(
    document: Mapping[str, object] | None,
    *,
    raw: bytes,
    committed_at: datetime,
    path: str,
) -> tuple[Preregistration | None, list[Finding]]:
    """Parse a committed preregistration, refusing any set that is not exactly the six."""
    if document is None:
        return None, []
    declared = document.get("statistics")
    if not isinstance(declared, Mapping):
        message = "the committed preregistration declares no statistics mapping"
        return None, [_finding(CODE_MALFORMED, message, path)]
    names = set(declared.keys())
    expected = set(STATISTIC_NAMES)
    if names != expected:
        extra = sorted(names - expected)
        missing = sorted(expected - names)
        message = (
            "the bound set is not exactly the six named figures; "
            f"unexpected {extra or 'none'}, missing {missing or 'none'}"
        )
        return None, [_finding(CODE_MALFORMED, message, path)]
    bounds: dict[str, Bound] = {}
    for name in STATISTIC_NAMES:
        entry = declared[name]
        if not isinstance(entry, Mapping) or "min" not in entry or "max" not in entry:
            message = f"the bound for {name} declares no inclusive min and max"
            return None, [_finding(CODE_MALFORMED, message, path)]
        bounds[name] = Bound(Fraction(str(entry["min"])), Fraction(str(entry["max"])))
    return Preregistration(bounds, preregistration_digest(raw), committed_at), []


def absent(*, register_stands: bool, path: str) -> Finding:
    """Resolve an absent preregistration under step 7g rather than unconditionally.

    While `DEF-REWARD-STATISTICS` stands in the deferred register the obligation is machinery
    nobody has built, so step 7g caps it exactly as the matching coverage gap would, at
    `HOLD`. Once that row closes the operator had a specified way to bind a statistic set and
    an absence becomes `BLOCK`.
    """
    if register_stands:
        message = (
            "no preregistered statistic set bounds the reward population, and "
            "DEF-REWARD-STATISTICS still stands in the deferred register, so this caps at "
            f"{HOLD} under step 7g as the matching coverage gap would"
        )
        return _finding(CODE_DEFERRED, message, path)
    message = (
        "no preregistered statistic set bounds the reward population and the deferred "
        f"register row is closed, so an absent preregistration is {BLOCK}"
    )
    return _finding(CODE_ABSENT, message, path)


def cap_for(finding: Finding) -> str:
    """Return the disposition cap a reward-distribution finding carries."""
    return HOLD if finding.code == CODE_DEFERRED else BLOCK


def no_worse_than_gap(cap: str, gap_cap: str) -> bool:
    """Return whether a live instrument's cap respects the build-never-hurts rule.

    A required instrument that reports an absence must never cap lower than the
    `D-COVERAGE-GAP` the same surface would carry with no instrument running at all.
    Otherwise implementing the instrument is strictly worse than omitting it, and the
    contract penalises compliance.
    """
    if gap_cap == HOLD:
        return cap != BLOCK
    return True


def moved(*, committed: str, attested: str, path: str) -> Finding | None:
    """Refuse a preregistration whose committed bytes disagree with the attested descriptor."""
    if committed == attested:
        return None
    message = (
        "the committed preregistration digest disagrees with the bound resource descriptor "
        f"in the trinity.execution/v2 pre-run commitment; committed {committed}, "
        f"attested {attested}"
    )
    return _finding(CODE_MOVED, message, path)


def ordered(*, committed_at: datetime, earliest_rollout: datetime, path: str) -> Finding | None:
    """Refuse a preregistration the execution interval did not follow."""
    if committed_at < earliest_rollout:
        return None
    message = (
        "the pre-run commitment does not predate the execution interval, so the statistic "
        f"set was not bound before observation; committed {committed_at.isoformat()}, "
        f"earliest rollout {earliest_rollout.isoformat()}"
    )
    return _finding(CODE_UNORDERED, message, path)


def evaluate(
    statistics: Statistics,
    preregistration: Preregistration,
    *,
    path: str,
) -> list[Finding]:
    """Compare every computed figure against its preregistered bound."""
    findings: list[Finding] = []
    values = statistics.as_mapping()
    for name in STATISTIC_NAMES:
        bound = preregistration.bounds[name]
        for member in values[name]:
            if not bound.holds(member):
                message = (
                    f"{name} computed {member} outside its preregistered bound "
                    f"[{bound.low}, {bound.high}]; this opens investigation and may cap, and a "
                    "distributional anomaly alone never confirms exploitation"
                )
                findings.append(_finding(CODE_OUT_OF_BOUND, message, path))
    return findings
