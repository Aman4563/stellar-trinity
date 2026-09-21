"""Historical diagnosis, never certification.

Precedence: confirmed_suppression > unknown_coverage > insufficient_groups.
Every independent reason survives reduction. Configurations never share groups.
"""

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import assert_never

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import forensics, stats
from tools.backfill_cli import run_cli, write_report
from tools.backfill_disk import Reader, children, history, runs, trace_bundle
from tools.backfill_models import (
    BACKFILL_FORBIDDEN_PREFIXES,
    CEILING,
    CONFIDENCE,
    GROUP_SIZE,
    BackfillError,
    BundleDiagnosis,
    ConfigurationDiagnosis,
    Disposition,
    Failure,
)


def diagnose_bundle(bundle_root: Path, *, project_root: Path | None = None) -> BundleDiagnosis:
    """Derive an optimistic sample-feasibility diagnosis from observed run directories.

    One observed configuration is one comparison under a single assumed look.
    Unknown historical look budgets can only increase the required sample size.
    Results are not independently verified; worst-case arithmetic imputes every
    outcome as successful rather than treating an absent score as a failure.
    """
    reader = Reader(project_root=project_root)
    configurations = children(bundle_root / "trajectories", project_root=project_root)
    if not configurations:
        raise BackfillError(Failure.FAMILY_UNRECOGNIZED)
    comparisons = len(configurations)
    minimum = stats.minimum_groups(CEILING, CONFIDENCE, comparisons)
    required = max(GROUP_SIZE, minimum)
    confidence = stats.bonferroni_confidence(CONFIDENCE, comparisons)
    suppression: list[str] = []
    unknown: list[str] = []
    insufficient: list[str] = []
    summaries: list[ConfigurationDiagnosis] = []
    for configuration in configurations:
        outcomes: list[tuple[bool, str]] = []
        for run in runs(configuration, project_root=project_root):
            result = forensics.analyze_trace(trace_bundle(run, reader))
            outcomes.append((True, forensics.map_trial_status(result)))
            for finding in result.findings:
                locator = f"{result.rollout_id}:{finding.signal}:{finding.evidence_pointer}"
                match finding.outcome:
                    case forensics.FidelityOutcome.VIOLATION:
                        suppression.append(locator)
                    case forensics.FidelityOutcome.INSUFFICIENT_EVIDENCE:
                        unknown.append(f"{locator}:{finding.refusal}")
                    case forensics.FidelityOutcome.COVERED_CLEAN:
                        continue
                    case unreachable:
                        assert_never(unreachable)
            if result.overall is forensics.FidelityOutcome.INSUFFICIENT_EVIDENCE and not any(
                finding.outcome is forensics.FidelityOutcome.INSUFFICIENT_EVIDENCE
                for finding in result.findings
            ):
                unknown.append(f"{result.rollout_id}:missing signal coverage")
        complete = len(outcomes) // GROUP_SIZE * GROUP_SIZE
        groups = [outcomes[index : index + GROUP_SIZE] for index in range(0, complete, GROUP_SIZE)]
        successes, count = stats.worst_case_group_successes(groups)
        remainder = len(outcomes) - complete
        if count < required or remainder:
            insufficient.append(
                f"{configuration.name}: {len(outcomes)} rollouts form {count} complete groups; "
                f"{required} required per configuration; {remainder} ungrouped rollouts retained"
            )
        summaries.append(
            ConfigurationDiagnosis(
                configuration.name,
                len(outcomes),
                count,
                remainder,
                successes,
                stats.group_upper_bound(successes, count, confidence) if count else None,
                stats.group_upper_bound(0, count, confidence) if count else None,
            )
        )
    if suppression:
        disposition = Disposition.CONFIRMED_SUPPRESSION
    elif unknown:
        disposition = Disposition.UNKNOWN_COVERAGE
    elif insufficient:
        disposition = Disposition.INSUFFICIENT_GROUPS
    else:
        # The closed vocabulary has no clean/sufficient success or release disposition.
        raise BackfillError(Failure.NO_DIAGNOSIS)
    return BundleDiagnosis(
        bundle=bundle_root.name,
        disposition=disposition,
        confirmed_suppression=tuple(suppression),
        unknown_coverage=tuple(unknown),
        insufficient_groups=tuple(insufficient),
        rollout_count=sum(item.rollout_count for item in summaries),
        group_count=sum(item.group_count for item in summaries),
        comparisons=comparisons,
        minimum_groups=minimum,
        required_groups=required,
        configurations=tuple(summaries),
        historical_execution=history(bundle_root, reader),
        arithmetic_conclusion=(
            "insufficient complete groups per configuration, independently of suppression"
            if insufficient
            else "sample floor met only; independence, custody and outcomes remain unverified"
        ),
    )


def main(argv: Sequence[str]) -> int:
    return run_cli(argv, diagnose_bundle)


__all__ = [
    "BACKFILL_FORBIDDEN_PREFIXES",
    "BackfillError",
    "BundleDiagnosis",
    "diagnose_bundle",
    "main",
    "write_report",
]

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
