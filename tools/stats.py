"""Exact binomial and finite-lot confidence bounds for Trinity's pilot statistics. Stdlib only.

FORGE Phase 4 item 4 fixes the Clopper-Pearson exact upper bound as the estimator for a
pilot's pass rate, under a rule predeclared in `.seed/pilot.yaml` that names the rollout
count, the one-sided confidence level, the frontier-defeat floor, and the separating
margin. A solver clears the floor when its upper bound sits at or above it, a task
defeats the frontier only when the bound stays strictly below the floor by the margin,
and a rollout count too small to separate the floor at that confidence is an
underpowered pilot rather than a measurement. This module computes those quantities.

The Clopper-Pearson interval is the set of rates a two-sided binomial test would not
reject at level `alpha`. Inverting that test gives endpoints that are beta quantiles:

    lower = B(alpha / 2; k, n - k + 1)
    upper = B(1 - alpha / 2; k + 1, n - k)

which follows from the identity between the binomial tail and the regularized incomplete
beta function, P(X <= k; n, p) = I(1 - p; n - k, k + 1). The one-sided bound is the same
upper endpoint taken at the full `alpha` rather than at `alpha / 2`.

Numerical method, chosen because the harness declares no dependencies and so has no
scipy to call:

  1. `regularized_incomplete_beta` evaluates I(x; a, b) in the Numerical Recipes
     formulation: a closed-form log-gamma prefactor times a continued fraction evaluated
     by Lentz's modified algorithm, which carries its own zero-denominator guard. The
     fraction converges quickly only for x below (a + 1) / (a + b + 2), so above that
     point the reflection I(x; a, b) = 1 - I(1 - x; b, a) moves the argument back into
     the fast region.
  2. `_beta_quantile` inverts that function by bisection on the unit interval. I(x; a, b)
     is strictly increasing in x, so a unit bracket is always valid and bisection is
     unconditionally convergent. Halving that bracket exhausts double precision in about
     sixty steps, well inside the iteration cap. Bisection is slower than a Newton step
     and has no failure mode, which is the trade a fail-closed harness wants.

`binomial_cdf` sums the mass function directly in log space rather than routing through
the beta identity, so it remains an independent check on the interval rather than a
restatement of it. FORGE Phase 4 batch certification instead samples without replacement
from a frozen finite stratum. Its hypergeometric upper bound sums integer combinations and
compares the resulting rational tail to the confidence threshold by cross multiplication,
so that decision introduces no floating-point rounding.

Group release fixes N disjoint groups of exactly eight independent rollouts before
observing outcomes. Z*_g is 1 if any member succeeds or is not conforming, else 0;
X* = sum(Z*_g), and affected groups are never removed from N. For familywise confidence
q and M comparisons, alpha = (1 - q) / M. Release requires, for every required solver,
U = Beta_inverse(1 - alpha; X* + 1, N - X*) < measured_pass_ceiling, with U = 1 when
X* = N. Integrity failures and the governance-owned affected-group limit block
independently. The exact unbiased descriptive pass@k estimate is
1 - C(n-c, k) / C(n, k); it does not replace the fixed-population group bound.

With zero successes, P(X = 0) = (1 - U)**N = alpha, hence U(0, N) = 1 - alpha**(1/N).
Feasibility therefore requires N > ln(alpha) / ln(1 - measured_pass_ceiling).
minimum_groups seeds from the ceiling of this ratio and evaluates neighboring counts
to preserve the strict inequality despite floating-point rounding. FORGE's
measured_group_floor is max(8, minimum_groups(measured_pass_ceiling,
familywise_confidence, comparisons)); the helper itself returns the mathematical minimum.
At measured_pass_ceiling 0.40 and familywise_confidence 0.95, the verified table is:

    Comparisons M       1    4    7    8    16
    Minimum groups N    6    9   10   10    12

Eight rollouts are one pass@8 group, not eight groups. Eight groups cannot clear the
ceiling at M = 8, even with zero successes and no affected groups.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from enum import StrEnum
from fractions import Fraction
from typing import Final, NamedTuple

_CF_MAX_STEPS = 500
_CF_EPSILON = 3.0e-16
_CF_TINY = 1.0e-30
_BISECTION_MAX_STEPS = 200
_BISECTION_TOLERANCE = 1.0e-17
_GROUP_SIZE: Final = 8
_MIN_GROUP_CEILING: Final = 1e-12


class _TrialStatus(StrEnum):
    """Closed trial-conformance vocabulary, independent of success."""

    CONFORMING = "conforming"
    NONCONFORMING = "nonconforming"
    INDETERMINATE = "indeterminate"


class Interval(NamedTuple):
    """A closed confidence interval on a rate, ordered as `(lower, upper)`."""

    lower: float
    upper: float


def _guard(value: float) -> float:
    """Keep a Lentz recurrence away from an exact zero denominator."""
    return _CF_TINY if abs(value) < _CF_TINY else value


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """Evaluate the continued fraction of I(x; a, b) by Lentz's modified algorithm."""
    c = 1.0
    d = 1.0 / _guard(1.0 - (a + b) * x / (a + 1.0))
    fraction = d
    for step in range(1, _CF_MAX_STEPS + 1):
        even = step * (b - step) * x / ((a + 2.0 * step - 1.0) * (a + 2.0 * step))
        d = 1.0 / _guard(1.0 + even * d)
        c = _guard(1.0 + even / c)
        fraction *= d * c
        odd = -(a + step) * (a + b + step) * x / ((a + 2.0 * step) * (a + 2.0 * step + 1.0))
        d = 1.0 / _guard(1.0 + odd * d)
        c = _guard(1.0 + odd / c)
        delta = d * c
        fraction *= delta
        if abs(delta - 1.0) < _CF_EPSILON:
            return fraction
    raise ArithmeticError(f"continued fraction for I({x}; {a}, {b}) did not converge")


def regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """Return I(x; a, b), the incomplete beta integral normalized to run from 0 to 1."""
    if a <= 0.0 or b <= 0.0:
        raise ValueError(f"beta shape parameters must be positive, got a={a} b={b}")
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"beta argument must lie in [0, 1], got {x}")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def _beta_quantile(probability: float, a: float, b: float) -> float:
    """Invert I(x; a, b) = probability by bisection, exploiting monotonicity in x."""
    low = 0.0
    high = 1.0
    for _ in range(_BISECTION_MAX_STEPS):
        if high - low <= _BISECTION_TOLERANCE:
            break
        middle = 0.5 * (low + high)
        if regularized_incomplete_beta(a, b, middle) < probability:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def _check_counts(successes: int, trials: int) -> None:
    """Reject a rollout tally that no binomial experiment could have produced."""
    if trials < 1:
        raise ValueError(f"trials must be at least 1, got {trials}")
    if not 0 <= successes <= trials:
        raise ValueError(f"successes must lie in [0, {trials}], got {successes}")


def _check_confidence(confidence: float) -> None:
    """Reject a confidence level that names no interval."""
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must lie strictly inside (0, 1), got {confidence}")


def binomial_cdf(successes: int, trials: int, rate: float) -> float:
    """Return P(X <= successes) for X drawn from Binomial(trials, rate).

    Summed term by term in log space, so a large `trials` cannot overflow the binomial
    coefficient, and totalled with `math.fsum` so the tail terms keep their precision.
    """
    _check_counts(successes, trials)
    if not 0.0 <= rate <= 1.0:
        raise ValueError(f"rate must lie in [0, 1], got {rate}")
    if rate == 0.0:
        return 1.0
    if rate == 1.0:
        return 1.0 if successes == trials else 0.0
    log_rate = math.log(rate)
    log_rest = math.log1p(-rate)
    log_trials = math.lgamma(trials + 1.0)
    terms = [
        math.exp(
            log_trials
            - math.lgamma(index + 1.0)
            - math.lgamma(trials - index + 1.0)
            + index * log_rate
            + (trials - index) * log_rest
        )
        for index in range(successes + 1)
    ]
    return min(math.fsum(terms), 1.0)


def clopper_pearson(successes: int, trials: int, confidence: float) -> Interval:
    """Return the two-sided Clopper-Pearson interval on the success rate.

    Each tail carries `(1 - confidence) / 2`. With no successes the lower endpoint is
    exactly 0 and with no failures the upper endpoint is exactly 1, because the beta
    quantile that would define the endpoint has a degenerate shape parameter there.
    """
    _check_counts(successes, trials)
    _check_confidence(confidence)
    tail = (1.0 - confidence) / 2.0
    lower = 0.0 if successes == 0 else _beta_quantile(tail, successes, trials - successes + 1)
    if successes == trials:
        return Interval(lower, 1.0)
    return Interval(lower, _beta_quantile(1.0 - tail, successes + 1, trials - successes))


def clopper_pearson_upper_bound(successes: int, trials: int, confidence: float) -> float:
    """Return the one-sided Clopper-Pearson exact upper bound on the success rate.

    This is the estimator FORGE Phase 4 item 4 names for a pilot's pass rate. It equals
    the upper endpoint of the two-sided interval taken at `2 * confidence - 1`, since the
    two-sided construction spends half its error budget on the lower tail.
    """
    _check_counts(successes, trials)
    _check_confidence(confidence)
    if successes == trials:
        return 1.0
    return _beta_quantile(confidence, successes + 1, trials - successes)


def bonferroni_confidence(familywise_confidence: float, comparisons: int) -> float:
    """Return the per-comparison confidence preserving a familywise confidence.

    Bonferroni divides the familywise error budget equally across `comparisons`, giving
    `1 - (1 - familywise_confidence) / comparisons`. The input float is first converted
    through its exact binary ratio, so the correction itself introduces no intermediate
    floating-point rounding before the result is returned under this module's float contract.
    """
    _check_confidence(familywise_confidence)
    if comparisons < 1:
        raise ValueError(f"comparisons must be at least 1, got {comparisons}")
    numerator, denominator = familywise_confidence.as_integer_ratio()
    confidence = Fraction(numerator, denominator)
    return float(1 - (1 - confidence) / comparisons)


def pass_at_k(successes: int, trials: int, k: int) -> Fraction:
    """Return the unbiased combinatorial pass@k estimate as an exact rational."""
    _check_counts(successes, trials)
    if not 1 <= k <= trials:
        raise ValueError(f"k must lie in [1, {trials}], got {k}")
    return 1 - Fraction(math.comb(trials - successes, k), math.comb(trials, k))


def _parse_group(outcomes: Sequence[tuple[bool, str]]) -> tuple[tuple[bool, _TrialStatus], ...]:
    """Parse every member before reduction, so success cannot hide an unknown token."""
    if len(outcomes) != _GROUP_SIZE:
        raise ValueError(f"group must contain exactly {_GROUP_SIZE} members, got {len(outcomes)}")
    return tuple((success, _TrialStatus(status)) for success, status in outcomes)


def group_indicator(outcomes: Sequence[tuple[bool, str]]) -> int:
    """Return worst-case success for one declared eight-member pass@8 group."""
    members = _parse_group(outcomes)
    return int(any(success or status != _TrialStatus.CONFORMING for success, status in members))


def worst_case_group_successes(groups: Sequence[Sequence[tuple[bool, str]]]) -> tuple[int, int]:
    """Return (X*, N) without excluding any affected group from the fixed population."""
    return sum(group_indicator(group) for group in groups), len(groups)


def group_upper_bound(x_star: int, group_count: int, confidence: float) -> float:
    """Return the one-sided group bound, guarding the degenerate full-success beta."""
    return clopper_pearson_upper_bound(x_star, group_count, confidence)


def minimum_groups(
    measured_pass_ceiling: float, familywise_confidence: float, comparisons: int
) -> int:
    """Find the smallest feasible N for ceilings in [1e-12, 1).

    Smaller ceilings are unsupported: quantile resolution and integer-neighbor
    rounding cannot establish strict feasibility reliably in that domain.
    """
    confidence = bonferroni_confidence(familywise_confidence, comparisons)
    _check_confidence(confidence)
    if not _MIN_GROUP_CEILING <= measured_pass_ceiling < 1.0:
        raise ValueError(
            f"measured_pass_ceiling must lie inside [1e-12, 1), got {measured_pass_ceiling}"
        )
    log_alpha = math.log1p(-confidence)
    count = max(1, math.ceil(log_alpha / math.log1p(-measured_pass_ceiling)))
    for _ in range(4):
        if -math.expm1(log_alpha / count) >= measured_pass_ceiling:
            count += 1
        elif count > 1 and -math.expm1(log_alpha / (count - 1)) < measured_pass_ceiling:
            count -= 1
        else:
            return count
    raise ValueError("measured_pass_ceiling cannot resolve strict feasibility")


def affected_group_fraction(groups: Sequence[Sequence[tuple[bool, str]]]) -> Fraction:
    """Return the exact affected share; an empty population has no defined fraction."""
    if not groups:
        raise ValueError("groups must contain at least 1 group")
    affected = sum(
        any(status != _TrialStatus.CONFORMING for _, status in _parse_group(group))
        for group in groups
    )
    return Fraction(affected, len(groups))


def _check_lot_counts(population: int, sample: int, observed_defective: int) -> None:
    """Reject a finite-lot tally that no simple random sample could have produced."""
    if population < 1:
        raise ValueError(f"population must be at least 1, got {population}")
    if not 0 < sample <= population:
        raise ValueError(f"sample must lie in [1, {population}], got {sample}")
    if not 0 <= observed_defective <= sample:
        raise ValueError(f"observed_defective must lie in [0, {sample}], got {observed_defective}")


def _hypergeometric_tail_at_least(
    population: int,
    sample: int,
    observed_defective: int,
    defective: int,
    threshold: tuple[int, int],
) -> bool:
    """Return whether P(X <= observed_defective) is at least `1 - confidence`."""
    first = max(0, sample - (population - defective))
    last = min(observed_defective, sample, defective)
    tail_numerator = sum(
        math.comb(defective, count) * math.comb(population - defective, sample - count)
        for count in range(first, last + 1)
    )
    tail_denominator = math.comb(population, sample)
    threshold_numerator, threshold_denominator = threshold
    return tail_numerator * threshold_denominator >= tail_denominator * threshold_numerator


def lot_defective_upper_bound(
    population: int, sample: int, observed_defective: int, confidence: float
) -> int:
    """Return the exact one-sided upper bound on defectives in a finite population.

    FORGE Phase 4 batch certification draws a simple random sample without replacement
    from one frozen difficulty stratum. This returns the smallest `D` for which every
    candidate lot containing more than `D` defectives would produce
    `observed_defective` or fewer sampled defects with probability below `1 - confidence`.
    Hypergeometric tails are monotone in the candidate defective count, so bisection finds
    the boundary while exact integer cross multiplication decides each side of it.
    """
    _check_lot_counts(population, sample, observed_defective)
    _check_confidence(confidence)
    if observed_defective == sample:
        return population

    confidence_numerator, confidence_denominator = confidence.as_integer_ratio()
    threshold = (
        confidence_denominator - confidence_numerator,
        confidence_denominator,
    )
    accepted = observed_defective
    rejected = population
    while rejected - accepted > 1:
        candidate = (accepted + rejected) // 2
        if _hypergeometric_tail_at_least(
            population,
            sample,
            observed_defective,
            candidate,
            threshold,
        ):
            accepted = candidate
        else:
            rejected = candidate
    return accepted


def lot_defective_rate_upper_bound(
    population: int, sample: int, observed_defective: int, confidence: float
) -> float:
    """Return the exact finite-lot upper bound as a fraction of the population."""
    bound = lot_defective_upper_bound(population, sample, observed_defective, confidence)
    return bound / population


def minimum_rollouts(floor: float, margin: float, confidence: float) -> int:
    """Return the smallest rollout count that can separate `floor` by `margin`.

    A pilot defeats the frontier only when its upper bound stays strictly below
    `floor - margin`, so the count that can separate the floor is the one whose best
    possible outcome, zero passes, already lands below that threshold. With no successes
    the bound closes to `1 - (1 - confidence) ** (1 / n)`, which inverts directly; the
    two loops then walk the seed to the exact integer rather than trusting the rounding.
    A realized count below this number is FORGE's `HOLD:UNDERPOWERED_PILOT`.
    """
    _check_confidence(confidence)
    if not 0.0 < floor <= 1.0:
        raise ValueError(f"floor must lie inside (0, 1], got {floor}")
    if margin < 0.0:
        raise ValueError(f"margin must not be negative, got {margin}")
    threshold = floor - margin
    if not 0.0 < threshold < 1.0:
        raise ValueError(f"floor less margin must lie inside (0, 1), got {threshold}")
    seed = math.log(1.0 - confidence) / math.log1p(-threshold)
    trials = max(1, math.ceil(seed))
    while trials > 1 and clopper_pearson_upper_bound(0, trials - 1, confidence) < threshold:
        trials -= 1
    while clopper_pearson_upper_bound(0, trials, confidence) >= threshold:
        trials += 1
    return trials
