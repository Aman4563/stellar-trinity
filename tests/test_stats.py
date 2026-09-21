from __future__ import annotations

import subprocess
import sys
from fractions import Fraction
from math import comb, isclose

import pytest
from tools import stats
from tools.stats import (
    Interval,
    binomial_cdf,
    bonferroni_confidence,
    clopper_pearson,
    clopper_pearson_upper_bound,
    lot_defective_rate_upper_bound,
    lot_defective_upper_bound,
    minimum_rollouts,
    regularized_incomplete_beta,
)


@pytest.mark.parametrize(
    ("successes", "trials", "k", "expected"),
    [
        (1, 8, 8, Fraction(1)),
        (0, 8, 8, Fraction(0)),
        (4, 8, 2, Fraction(11, 14)),
        (8, 8, 1, Fraction(1)),
        (3, 8, 1, Fraction(3, 8)),
    ],
)
def test_pass_at_k_matches_closed_form(
    successes: int, trials: int, k: int, expected: Fraction
) -> None:
    result = stats.pass_at_k(successes, trials, k)
    assert isinstance(result, Fraction)
    assert result == expected == 1 - Fraction(comb(trials - successes, k), comb(trials, k))


@pytest.mark.parametrize(
    ("successes", "trials", "k"),
    [(0, 8, 9), (0, 8, 0), (0, 8, -1), (-1, 8, 2), (8, 4, 2), (0, 0, 1)],
)
def test_pass_at_k_refuses_bad_counts(successes: int, trials: int, k: int) -> None:
    with pytest.raises(ValueError, match=r"successes|trials|k"):
        stats.pass_at_k(successes, trials, k)


@pytest.mark.parametrize(
    ("member", "expected"),
    [
        ((False, "conforming"), 0),
        ((True, "conforming"), 1),
        ((False, "indeterminate"), 1),
        ((False, "nonconforming"), 1),
    ],
)
def test_group_indicator_worst_case(member: tuple[bool, str], expected: int) -> None:
    outcomes = [*([(False, "conforming")] * 7), member]
    assert stats.group_indicator(outcomes) == expected


@pytest.mark.parametrize("count", [0, 1, 7, 9])
def test_group_indicator_refuses_wrong_member_count(count: int) -> None:
    with pytest.raises(ValueError, match="group"):
        stats.group_indicator([(False, "conforming")] * count)


@pytest.mark.parametrize("token", ["unknown", "", "Conforming"])
def test_group_indicator_refuses_unknown_status_after_success(token: str) -> None:
    outcomes = [*([(True, "conforming")] * 7), (False, token)]
    with pytest.raises(ValueError):
        stats.group_indicator(outcomes)


def test_worst_case_never_drops_groups() -> None:
    clean = [(False, "conforming")] * 8
    affected = [
        [*clean[:7], (False, token)]
        for token in ("nonconforming", "indeterminate", "nonconforming")
    ]
    groups = [clean, clean, [(True, "conforming")] * 8, *affected]
    assert stats.worst_case_group_successes(groups) == (4, len(groups))


@pytest.mark.parametrize("group_count", range(1, 13))
@pytest.mark.parametrize("confidence", [0.5, 0.95, 0.999])
def test_group_upper_bound_is_one_at_full(group_count: int, confidence: float) -> None:
    assert stats.group_upper_bound(group_count, group_count, confidence) == 1.0


@pytest.mark.parametrize(("successes", "trials"), [(0, 8), (2, 8), (7, 8)])
def test_group_upper_bound_delegates(successes: int, trials: int) -> None:
    assert stats.group_upper_bound(successes, trials, 0.95) == clopper_pearson_upper_bound(
        successes, trials, 0.95
    )


@pytest.mark.parametrize(
    ("successes", "trials", "confidence"),
    [(0, 0, 0.95), (-1, 8, 0.95), (9, 8, 0.95), (8, 8, 1.0), (8, 8, 0.0)],
)
def test_group_upper_bound_refuses_invalid_inputs(
    successes: int, trials: int, confidence: float
) -> None:
    with pytest.raises(ValueError):
        stats.group_upper_bound(successes, trials, confidence)


@pytest.mark.parametrize(("comparisons", "expected"), [(1, 6), (4, 9), (7, 10), (8, 10), (16, 12)])
def test_minimum_groups_matches_infeasibility_table(comparisons: int, expected: int) -> None:
    assert stats.minimum_groups(0.40, 0.95, comparisons) == expected


@pytest.mark.parametrize("comparisons", [1, 4, 7, 8, 16])
@pytest.mark.parametrize("ceiling", [0.05, 0.4, 0.99])
@pytest.mark.parametrize("familywise_confidence", [0.5, 0.95])
def test_minimum_groups_result_is_empirically_feasible(
    ceiling: float, familywise_confidence: float, comparisons: int
) -> None:
    confidence = bonferroni_confidence(familywise_confidence, comparisons)
    count = stats.minimum_groups(
        measured_pass_ceiling=ceiling,
        familywise_confidence=familywise_confidence,
        comparisons=comparisons,
    )
    assert count >= 1
    assert stats.group_upper_bound(0, count, confidence) < ceiling
    if count > 1:
        assert stats.group_upper_bound(0, count - 1, confidence) >= ceiling


def test_minimum_groups_refuses_equality_at_the_ceiling() -> None:
    ceiling = clopper_pearson_upper_bound(0, 9, bonferroni_confidence(0.95, 4))
    assert stats.minimum_groups(ceiling, 0.95, 4) == 10


def test_minimum_groups_refuses_unsupported_ceiling() -> None:
    # Given: a ceiling below the supported numerical resolution.
    code = """
from tools.stats import minimum_groups
try:
    minimum_groups(1e-20, 0.95, 4)
except ValueError:
    pass
else:
    raise AssertionError('unsupported ceiling accepted')
"""
    # When: invoke the public function in a killable process.
    result = subprocess.run(
        [sys.executable, "-c", code], timeout=2, capture_output=True, check=False
    )
    # Then: refusal completes, rather than unbounded neighbor adjustment.
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize(
    ("ceiling", "confidence", "comparisons"),
    [
        (0.0, 0.95, 1),
        (1.0, 0.95, 1),
        (float("nan"), 0.95, 1),
        (0.4, 0.0, 1),
        (0.4, 1.0, 1),
        (0.4, 0.95, 0),
        (0.4, 0.95, 10**20),
    ],
)
def test_minimum_groups_refuses_invalid_inputs(
    ceiling: float, confidence: float, comparisons: int
) -> None:
    with pytest.raises(ValueError):
        stats.minimum_groups(ceiling, confidence, comparisons)


def test_eight_groups_infeasible_at_family_eight() -> None:
    assert stats.minimum_groups(0.40, 0.95, 8) > 8


def test_affected_group_fraction_is_exact() -> None:
    clean = [(False, "conforming")] * 8
    groups = [
        clean,
        [(True, "conforming")] * 8,
        [*clean[:6], (False, "nonconforming"), (False, "indeterminate")],
    ]
    result = stats.affected_group_fraction(groups)
    assert isinstance(result, Fraction)
    assert result == Fraction(1, 3)


@pytest.mark.parametrize("token", ["conforming", "nonconforming", "indeterminate"])
def test_affected_group_fraction_extremes(token: str) -> None:
    assert stats.affected_group_fraction([[(False, token)] * 8]) == Fraction(token != "conforming")


@pytest.mark.parametrize("group", [[(False, "conforming")] * 7, [(True, "unknown")] * 8])
def test_group_aggregates_refuse_malformed_groups(group: list[tuple[bool, str]]) -> None:
    with pytest.raises(ValueError):
        stats.worst_case_group_successes([group])
    with pytest.raises(ValueError):
        stats.affected_group_fraction([group])


def test_empty_population_has_no_fraction() -> None:
    assert stats.worst_case_group_successes([]) == (0, 0)
    with pytest.raises(ValueError, match="groups"):
        stats.affected_group_fraction([])


PUBLISHED = 1e-3
IDENTITY = 1e-9

# Published two-sided Clopper-Pearson intervals at 95 percent, cross-checked against an
# exact-rational inversion of the binomial CDF definition that touches no beta function.
REFERENCE = [
    (0, 10, 0.0, 0.3085),
    (1, 10, 0.0025, 0.4450),
    (5, 10, 0.1871, 0.8129),
    (10, 10, 0.6915, 1.0),
    (3, 20, 0.0321, 0.3789),
    (0, 30, 0.0, 0.1157),
    (7, 25, 0.1207, 0.4939),
]
COUNTS = [(successes, trials) for successes, trials, _, _ in REFERENCE]


def exact_binomial_cdf(successes: int, trials: int, rate: float) -> float:
    """Sum the binomial mass function over exact rationals, independent of the harness."""
    probability = Fraction(rate)
    total = sum(
        Fraction(comb(trials, index)) * probability**index * (1 - probability) ** (trials - index)
        for index in range(successes + 1)
    )
    return float(total)


def brute_force_lot_bound(
    population: int, sample: int, observed_defective: int, confidence: float
) -> int:
    """Invert exact-rational hypergeometric tails by exhaustive candidate search."""
    threshold = 1 - Fraction(confidence)
    denominator = comb(population, sample)
    accepted: list[int] = []
    for defective in range(population + 1):
        first = max(0, sample - (population - defective))
        last = min(observed_defective, sample, defective)
        numerator = sum(
            comb(defective, count) * comb(population - defective, sample - count)
            for count in range(first, last + 1)
        )
        if Fraction(numerator, denominator) >= threshold:
            accepted.append(defective)
    return max(accepted)


@pytest.mark.parametrize(("successes", "trials", "lower", "upper"), REFERENCE)
def test_interval_matches_published_values(
    successes: int, trials: int, lower: float, upper: float
) -> None:
    interval = clopper_pearson(successes, trials, 0.95)
    assert interval.lower == pytest.approx(lower, abs=PUBLISHED)
    assert interval.upper == pytest.approx(upper, abs=PUBLISHED)


@pytest.mark.parametrize(("successes", "trials"), COUNTS)
def test_upper_endpoint_solves_the_binomial_cdf_identity(successes: int, trials: int) -> None:
    interval = clopper_pearson(successes, trials, 0.95)
    if successes == trials:
        assert interval.upper == 1.0
        return
    assert binomial_cdf(successes, trials, interval.upper) == pytest.approx(0.025, abs=IDENTITY)


@pytest.mark.parametrize(("successes", "trials"), COUNTS)
def test_lower_endpoint_solves_the_binomial_cdf_identity(successes: int, trials: int) -> None:
    interval = clopper_pearson(successes, trials, 0.95)
    if successes == 0:
        assert interval.lower == 0.0
        return
    remaining = 1.0 - binomial_cdf(successes - 1, trials, interval.lower)
    assert remaining == pytest.approx(0.025, abs=IDENTITY)


@pytest.mark.parametrize(("successes", "trials"), [(0, 10), (2, 20), (7, 25), (13, 40)])
def test_one_sided_bound_solves_the_binomial_cdf_identity(successes: int, trials: int) -> None:
    bound = clopper_pearson_upper_bound(successes, trials, 0.95)
    assert binomial_cdf(successes, trials, bound) == pytest.approx(0.05, abs=IDENTITY)


@pytest.mark.parametrize(("successes", "trials"), [(0, 10), (2, 20), (5, 10), (10, 10)])
def test_one_sided_bound_is_the_two_sided_endpoint_at_double_the_error(
    successes: int, trials: int
) -> None:
    bound = clopper_pearson_upper_bound(successes, trials, 0.95)
    assert bound == pytest.approx(clopper_pearson(successes, trials, 0.90).upper, abs=1e-12)


def test_one_sided_bound_matches_its_closed_form_with_no_successes() -> None:
    assert clopper_pearson_upper_bound(0, 10, 0.95) == pytest.approx(1.0 - 0.05**0.1, abs=1e-12)


@pytest.mark.parametrize(
    ("familywise_confidence", "comparisons", "expected"),
    [(0.95, 1, 0.95), (0.95, 2, 0.975), (0.8, 4, 0.95), (0.5, 10, 0.95)],
)
def test_bonferroni_confidence_matches_hand_computed_values(
    familywise_confidence: float, comparisons: int, expected: float
) -> None:
    assert bonferroni_confidence(familywise_confidence, comparisons) == expected


@pytest.mark.parametrize("confidence", [0.0, 1.0, -0.1, 1.5])
def test_bonferroni_confidence_rejects_invalid_familywise_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        bonferroni_confidence(confidence, 2)


@pytest.mark.parametrize("comparisons", [0, -1, -10])
def test_bonferroni_confidence_rejects_invalid_comparison_count(comparisons: int) -> None:
    with pytest.raises(ValueError, match="comparisons"):
        bonferroni_confidence(0.95, comparisons)


def test_lot_bound_matches_a_hand_verified_zero_defect_case() -> None:
    # For N=20 and n=5, D=8 leaves P(X=0)=C(12,5)/C(20,5)=792/15504 >= 0.05.
    # D=9 leaves only C(11,5)/C(20,5)=462/15504 < 0.05, so the 95% bound is 8.
    assert lot_defective_upper_bound(20, 5, 0, 0.95) == 8
    assert lot_defective_rate_upper_bound(20, 5, 0, 0.95) == 0.4


def test_lot_bound_is_observation_when_the_whole_population_is_sampled() -> None:
    for population in (1, 7, 20):
        for observed_defective in range(population + 1):
            assert (
                lot_defective_upper_bound(population, population, observed_defective, 0.95)
                == observed_defective
            )


def test_lot_bound_is_population_when_every_sampled_item_is_defective() -> None:
    for population, sample in ((1, 1), (20, 5), (40, 17)):
        assert lot_defective_upper_bound(population, sample, sample, 0.95) == population
        assert lot_defective_rate_upper_bound(population, sample, sample, 0.95) == 1.0


def test_lot_bound_widens_as_confidence_rises() -> None:
    bounds = [
        lot_defective_upper_bound(100, 20, 2, confidence) for confidence in (0.50, 0.80, 0.95, 0.99)
    ]
    assert bounds == sorted(bounds)


def test_lot_bound_falls_as_the_sample_grows_at_a_fixed_defect_count() -> None:
    bounds = [lot_defective_upper_bound(100, sample, 1, 0.95) for sample in (5, 10, 20, 40)]
    assert bounds == sorted(bounds, reverse=True)


def test_lot_bound_agrees_with_brute_force_over_small_grids() -> None:
    for population in range(1, 41):
        samples = {1, max(1, population // 3), max(1, population // 2), population}
        for sample in samples:
            observations = {0, sample // 2, sample}
            for observed_defective in observations:
                for confidence in (0.5, 0.8, 0.95):
                    assert lot_defective_upper_bound(
                        population, sample, observed_defective, confidence
                    ) == brute_force_lot_bound(population, sample, observed_defective, confidence)


def test_interval_endpoints_match_their_closed_forms_at_the_extremes() -> None:
    assert clopper_pearson(0, 10, 0.95).upper == pytest.approx(1.0 - 0.025**0.1, abs=1e-12)
    assert clopper_pearson(10, 10, 0.95).lower == pytest.approx(0.025**0.1, abs=1e-12)


def test_no_successes_pins_the_lower_endpoint_at_zero() -> None:
    interval = clopper_pearson(0, 7, 0.95)
    assert interval.lower == 0.0
    assert 0.0 < interval.upper < 1.0


def test_no_failures_pins_the_upper_endpoint_at_one() -> None:
    interval = clopper_pearson(7, 7, 0.95)
    assert interval.upper == 1.0
    assert clopper_pearson_upper_bound(7, 7, 0.95) == 1.0
    assert 0.0 < interval.lower < 1.0


def test_single_trial_covers_both_degenerate_outcomes() -> None:
    lost = clopper_pearson(0, 1, 0.95)
    assert lost.lower == 0.0
    assert lost.upper == pytest.approx(0.975, abs=IDENTITY)
    won = clopper_pearson(1, 1, 0.95)
    assert won.lower == pytest.approx(0.025, abs=IDENTITY)
    assert won.upper == 1.0


def test_interval_unpacks_as_a_plain_lower_upper_pair() -> None:
    interval = clopper_pearson(5, 10, 0.95)
    lower, upper = interval
    assert isinstance(interval, Interval)
    assert isinstance(interval, tuple)
    assert (lower, upper) == (interval.lower, interval.upper)


def test_interval_is_ordered_and_brackets_the_observed_rate() -> None:
    for trials in (1, 5, 12, 40):
        for successes in range(trials + 1):
            interval = clopper_pearson(successes, trials, 0.95)
            assert interval.lower <= successes / trials <= interval.upper


def test_interval_widens_as_confidence_rises() -> None:
    narrow = clopper_pearson(5, 20, 0.80)
    wide = clopper_pearson(5, 20, 0.99)
    assert wide.lower < narrow.lower
    assert narrow.upper < wide.upper


def test_bound_falls_as_rollouts_accumulate_without_a_pass() -> None:
    bounds = [clopper_pearson_upper_bound(0, trials, 0.95) for trials in (10, 20, 50, 100)]
    assert bounds == sorted(bounds, reverse=True)


def test_interval_is_symmetric_under_relabelling_success_as_failure() -> None:
    interval = clopper_pearson(3, 17, 0.95)
    mirrored = clopper_pearson(14, 17, 0.95)
    assert interval.lower == pytest.approx(1.0 - mirrored.upper, abs=1e-12)
    assert interval.upper == pytest.approx(1.0 - mirrored.lower, abs=1e-12)


@pytest.mark.parametrize(
    ("successes", "trials"),
    [(0, 1), (1, 1), (0, 10), (4, 10), (10, 10), (17, 30)],
)
def test_binomial_cdf_matches_exact_rational_summation(successes: int, trials: int) -> None:
    for rate in (0.05, 0.25, 0.5, 0.75, 0.999):
        assert binomial_cdf(successes, trials, rate) == pytest.approx(
            exact_binomial_cdf(successes, trials, rate), abs=1e-12
        )


def test_binomial_cdf_is_total_at_the_last_success_count() -> None:
    for trials in (1, 9, 40):
        for rate in (0.1, 0.4, 0.9):
            assert binomial_cdf(trials, trials, rate) == pytest.approx(1.0, abs=1e-12)


def test_binomial_cdf_handles_degenerate_rates() -> None:
    assert binomial_cdf(0, 5, 0.0) == 1.0
    assert binomial_cdf(4, 5, 1.0) == 0.0
    assert binomial_cdf(5, 5, 1.0) == 1.0


def test_regularized_incomplete_beta_reduces_to_the_identity_when_flat() -> None:
    for x in (0.0, 0.1, 0.5, 0.9, 1.0):
        assert regularized_incomplete_beta(1.0, 1.0, x) == pytest.approx(x, abs=1e-14)


def test_regularized_incomplete_beta_obeys_its_reflection() -> None:
    for a, b, x in ((2.0, 5.0, 0.3), (0.5, 0.5, 0.8), (11.0, 3.0, 0.62), (40.0, 60.0, 0.45)):
        mirrored = 1.0 - regularized_incomplete_beta(b, a, 1.0 - x)
        assert regularized_incomplete_beta(a, b, x) == pytest.approx(mirrored, abs=1e-13)


def test_regularized_incomplete_beta_agrees_with_the_binomial_tail() -> None:
    trials, successes, rate = 25, 7, 0.4
    tail = regularized_incomplete_beta(trials - successes, successes + 1, 1.0 - rate)
    assert tail == pytest.approx(exact_binomial_cdf(successes, trials, rate), abs=1e-12)


def test_minimum_rollouts_names_the_smallest_separating_count() -> None:
    assert minimum_rollouts(0.05, 0.0, 0.95) == 59


@pytest.mark.parametrize(
    ("floor", "margin", "confidence"),
    [(0.05, 0.0, 0.95), (0.10, 0.02, 0.95), (0.25, 0.05, 0.99), (0.5, 0.1, 0.90)],
)
def test_minimum_rollouts_is_the_exact_boundary(
    floor: float, margin: float, confidence: float
) -> None:
    trials = minimum_rollouts(floor, margin, confidence)
    threshold = floor - margin
    assert clopper_pearson_upper_bound(0, trials, confidence) < threshold
    assert clopper_pearson_upper_bound(0, trials - 1, confidence) >= threshold


@pytest.mark.parametrize(
    ("successes", "trials"),
    [(-1, 10), (11, 10), (0, 0), (0, -3), (1, 0)],
)
def test_invalid_counts_are_rejected(successes: int, trials: int) -> None:
    with pytest.raises(ValueError, match=r"trials|successes"):
        clopper_pearson(successes, trials, 0.95)
    with pytest.raises(ValueError, match=r"trials|successes"):
        clopper_pearson_upper_bound(successes, trials, 0.95)
    with pytest.raises(ValueError, match=r"trials|successes"):
        binomial_cdf(successes, trials, 0.5)


@pytest.mark.parametrize("confidence", [0.0, 1.0, -0.1, 1.5, 2.0])
def test_invalid_confidence_is_rejected(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        clopper_pearson(5, 10, confidence)
    with pytest.raises(ValueError, match="confidence"):
        clopper_pearson_upper_bound(5, 10, confidence)


@pytest.mark.parametrize(
    ("population", "sample", "observed_defective", "confidence", "message"),
    [
        (0, 0, 0, 0.95, "population"),
        (-1, 1, 0, 0.95, "population"),
        (10, 0, 0, 0.95, "sample"),
        (10, 11, 0, 0.95, "sample"),
        (10, 5, -1, 0.95, "observed_defective"),
        (10, 5, 6, 0.95, "observed_defective"),
        (10, 5, 1, 0.0, "confidence"),
        (10, 5, 1, 1.0, "confidence"),
    ],
)
def test_lot_bounds_reject_invalid_inputs(
    population: int,
    sample: int,
    observed_defective: int,
    confidence: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        lot_defective_upper_bound(population, sample, observed_defective, confidence)
    with pytest.raises(ValueError, match=message):
        lot_defective_rate_upper_bound(population, sample, observed_defective, confidence)


@pytest.mark.parametrize("rate", [-0.001, 1.001, 2.0])
def test_invalid_rate_is_rejected(rate: float) -> None:
    with pytest.raises(ValueError, match="rate"):
        binomial_cdf(3, 10, rate)


@pytest.mark.parametrize(
    ("a", "b", "x"),
    [(0.0, 1.0, 0.5), (1.0, 0.0, 0.5), (-1.0, 2.0, 0.5), (1.0, 1.0, -0.1), (1.0, 1.0, 1.1)],
)
def test_invalid_beta_arguments_are_rejected(a: float, b: float, x: float) -> None:
    with pytest.raises(ValueError, match="beta"):
        regularized_incomplete_beta(a, b, x)


@pytest.mark.parametrize(
    ("floor", "margin", "confidence"),
    [(0.0, 0.0, 0.95), (1.5, 0.0, 0.95), (0.2, -0.1, 0.95), (0.2, 0.2, 0.95), (0.2, 0.3, 0.95)],
)
def test_minimum_rollouts_rejects_an_unusable_rule(
    floor: float, margin: float, confidence: float
) -> None:
    with pytest.raises(ValueError, match=r"floor|margin"):
        minimum_rollouts(floor, margin, confidence)


def test_minimum_rollouts_rejects_an_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        minimum_rollouts(0.05, 0.0, 1.0)


def test_bound_decides_the_frontier_defeat_rule_as_forge_states_it() -> None:
    floor, margin = 0.05, 0.01
    trials = minimum_rollouts(floor, margin, 0.95)
    defeated = clopper_pearson_upper_bound(0, trials, 0.95)
    cleared = clopper_pearson_upper_bound(1, trials, 0.95)
    assert defeated < floor - margin
    assert cleared >= floor
    assert isclose(binomial_cdf(0, trials, defeated), 0.05, abs_tol=IDENTITY)
