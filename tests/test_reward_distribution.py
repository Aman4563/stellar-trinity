"""Both-halves fixtures for the CRUCIBLE step 8o preregistration gate.

Verifier principle 7 requires every registered check to fire on a planted defect and stay
clean on a fixture without one. Each scenario below therefore carries both halves: a check
that only ever fires proves nothing, and neither does one that never fires.
"""

from __future__ import annotations

from datetime import UTC, datetime
from fractions import Fraction

import pytest
from tools import reward_distribution as rd

from tests.bite_shared.registration import bite

PATH = ".audit/preregistration/1213efa9-10ca-4f0e-bb27-2f6012454212.yaml"
COMMITTED = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
FIRST_ROLLOUT = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)

# Eight rollouts: two at the null floor, one at full reward, the rest spread between.
REWARDS = (
    Fraction(0),
    Fraction(0),
    Fraction(1, 4),
    Fraction(1, 4),
    Fraction(1, 2),
    Fraction(3, 4),
    Fraction(7, 8),
    Fraction(1),
)


def population(rewards: tuple[Fraction, ...] = REWARDS) -> rd.Population:
    return rd.Population(rewards=rewards, null_floor=Fraction(0), full_reward=Fraction(1))


def bounds(**overrides: tuple[str, str]) -> dict[str, object]:
    declared: dict[str, tuple[str, str]] = {
        "reward_cardinality": ("8", "8"),
        "reward_support": ("2", "8"),
        "reward_floor_mass": ("0", "2"),
        "reward_ceiling_mass": ("0", "2"),
        "reward_median": ("0", "1"),
        "reward_range": ("0", "1"),
    }
    declared.update(overrides)
    return {"statistics": {k: {"min": low, "max": high} for k, (low, high) in declared.items()}}


def parsed(document: dict[str, object] | None = None) -> rd.Preregistration:
    found, findings = rd.parse(
        document if document is not None else bounds(),
        raw=b"statistics: {}",
        committed_at=COMMITTED,
        path=PATH,
    )
    assert not findings
    assert found is not None
    return found


def test_statistics_are_exact_rationals() -> None:
    """The six figures recompute exactly, with no floating-point summary anywhere."""
    stats = rd.compute(population())
    assert stats.reward_cardinality == 8
    assert stats.reward_support == 6
    assert stats.reward_floor_mass == 2
    assert stats.reward_ceiling_mass == 1
    assert stats.reward_median == Fraction(3, 8)
    assert stats.reward_range == (Fraction(0), Fraction(1))
    assert isinstance(stats.reward_median, Fraction)


def test_support_collapses_byte_distinct_spellings_of_one_value() -> None:
    """Support counts canonical rationals, so 1/2 and 2/4 are one value rather than two."""
    stats = rd.compute(population((Fraction(1, 2), Fraction(2, 4), Fraction(1))))
    assert stats.reward_support == 2


def test_empty_population_is_refused_rather_than_summarised() -> None:
    with pytest.raises(rd.RewardDistributionError):
        rd.compute(population(()))


@bite("crucible.md:P15")
def test_absent_preregistration_caps_at_hold_while_the_register_stands() -> None:
    """Planted half: an absence resolves under step 7g, not as an unconditional BLOCK."""
    finding = rd.absent(register_stands=True, path=PATH)
    assert finding.code == rd.CODE_DEFERRED
    assert rd.cap_for(finding) == rd.HOLD


@bite("crucible.md:P15a")
def test_absent_preregistration_is_block_once_the_register_row_closes() -> None:
    """Clean half: the discipline reactivates the moment the machinery is no longer deferred."""
    finding = rd.absent(register_stands=False, path=PATH)
    assert finding.code == rd.CODE_ABSENT
    assert rd.cap_for(finding) == rd.BLOCK


@bite("crucible.md:P16")
def test_moved_preregistration_is_block_whether_or_not_the_register_stands() -> None:
    """Planted half: a digest disagreement is misconduct an operator chose."""
    finding = rd.moved(committed="a" * 64, attested="b" * 64, path=PATH)
    assert finding is not None
    assert finding.code == rd.CODE_MOVED
    assert rd.cap_for(finding) == rd.BLOCK


@bite("crucible.md:P16a")
def test_agreeing_preregistration_digest_stays_clean() -> None:
    """Clean half: matching committed and attested digests raise nothing."""
    assert rd.moved(committed="a" * 64, attested="a" * 64, path=PATH) is None


@bite("crucible.md:P17")
def test_out_of_bound_statistic_fires() -> None:
    """Planted half: a cardinality of 8 against a bound of [1, 4] is outside its interval."""
    findings = rd.evaluate(
        rd.compute(population()),
        parsed(bounds(reward_cardinality=("1", "4"))),
        path=PATH,
    )
    assert [f.code for f in findings] == [rd.CODE_OUT_OF_BOUND]


@bite("crucible.md:P17a")
def test_in_bound_statistics_stay_clean() -> None:
    """Clean half: every figure inside its preregistered bound raises nothing."""
    assert rd.evaluate(rd.compute(population()), parsed(), path=PATH) == []


@bite("crucible.md:P19")
def test_commitment_not_predating_the_execution_interval_fires() -> None:
    """Planted half: a commitment at or after the first rollout did not precede observation."""
    finding = rd.ordered(committed_at=FIRST_ROLLOUT, earliest_rollout=FIRST_ROLLOUT, path=PATH)
    assert finding is not None
    assert finding.code == rd.CODE_UNORDERED
    assert rd.cap_for(finding) == rd.BLOCK


@bite("crucible.md:P19a")
def test_commitment_predating_the_execution_interval_stays_clean() -> None:
    """Clean half: binding before the first rollout is the ordering the gate wants."""
    assert rd.ordered(committed_at=COMMITTED, earliest_rollout=FIRST_ROLLOUT, path=PATH) is None


@bite("crucible.md:P20")
def test_a_seventh_statistic_is_refused() -> None:
    """Planted half: an open set lets a chooser add the one figure that clears."""
    document = bounds()
    statistics = document["statistics"]
    assert isinstance(statistics, dict)
    statistics["reward_variance"] = {"min": "0", "max": "1"}
    found, findings = rd.parse(document, raw=b"", committed_at=COMMITTED, path=PATH)
    assert found is None
    assert [f.code for f in findings] == [rd.CODE_MALFORMED]


@bite("crucible.md:P20a")
def test_a_missing_statistic_is_refused() -> None:
    """Planted half: omitting a figure is the same defect as adding one."""
    document = bounds()
    statistics = document["statistics"]
    assert isinstance(statistics, dict)
    del statistics["reward_median"]
    found, findings = rd.parse(document, raw=b"", committed_at=COMMITTED, path=PATH)
    assert found is None
    assert [f.code for f in findings] == [rd.CODE_MALFORMED]


@bite("crucible.md:P21")
def test_a_live_instrument_never_caps_below_the_gap_it_replaces() -> None:
    """Planted half: BLOCK against a HOLD gap means building the instrument was punished."""
    assert not rd.no_worse_than_gap(rd.BLOCK, rd.HOLD)


@bite("crucible.md:P21a")
def test_the_deferred_branch_respects_the_build_never_hurts_rule() -> None:
    """Clean half: the cap step 7g assigns is exactly the cap the absent instrument carries."""
    finding = rd.absent(register_stands=True, path=PATH)
    assert rd.no_worse_than_gap(rd.cap_for(finding), rd.HOLD)
