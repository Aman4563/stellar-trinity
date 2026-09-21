"""Synthetic auditor results for binding tests, never external pilot evidence."""

from collections.abc import Mapping
from pathlib import Path

from tools.forensics.bundle import Authorization
from tools.forensics.core import FidelityOutcome, RolloutFidelity, SignalClass, SignalFinding
from tools.forensics.family_config import ConfigStanding
from tools.forensics.family_models import FidelityLedger, FidelityRow, PopulationStanding
from tools.forensics.ledger import emit_fidelity_ledger, project_for_pilot
from tools.harness_config import AdequacyOutcome, ReconcileOutcome
from tools.pilot import GENESIS_DIGEST


def fidelity_ledger(statuses: Mapping[str, str]) -> FidelityLedger:
    config = ConfigStanding(
        True,
        ReconcileOutcome(True, None, ""),
        AdequacyOutcome(True, None, ""),
        "c" * 64,
        Authorization(),
        "2.1.158",
    )
    population = PopulationStanding((), (), True)
    outcomes = {
        "conforming": FidelityOutcome.COVERED_CLEAN,
        "nonconforming": FidelityOutcome.VIOLATION,
        "indeterminate": FidelityOutcome.INSUFFICIENT_EVIDENCE,
    }
    handoff = SignalFinding(
        SignalClass.HANDOFF_FAILURE, FidelityOutcome.COVERED_CLEAN, None, "scorer.json:1"
    )
    rows = tuple(
        FidelityRow(
            RolloutFidelity(
                identity,
                "claude_code_jsonl",
                tuple(
                    SignalFinding(signal, outcomes[status], None, "agent.jsonl:1")
                    for signal in SignalClass
                ),
            ),
            handoff,
            config,
            population,
        )
        for identity, status in statuses.items()
    )
    identities = tuple(statuses)
    groups = tuple(identities[index : index + 8] for index in range(0, len(identities), 8))
    return FidelityLedger(rows, config, population, len(groups), groups)


def bind_registry_ledger(root: Path, records: list[dict[str, object]]) -> None:
    from tests.test_pilot import (  # noqa: PLC0415 - avoid fixture import cycle
        parsed_attempts,
        redigest,
    )

    statuses = {
        rollout.rollout_id: rollout.trial_status
        for attempt in parsed_attempts(records)
        for group in attempt.solver_groups
        for rollout in group.rollouts
    }
    ledger = fidelity_ledger(statuses)
    emit_fidelity_ledger(ledger, root / ".audit", project_root=root)
    digest = project_for_pilot(ledger)["fidelityLedgerDigest"]
    previous = GENESIS_DIGEST
    for record in records:
        record["fidelityLedgerDigest"] = digest
        record["previousRecordDigest"] = previous
        redigest(record)
        previous = str(record["recordDigest"])
