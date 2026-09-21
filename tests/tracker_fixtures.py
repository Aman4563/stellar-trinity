"""Fixture builder for a parent-shaped Trinity tree, assembled from real writers.

``parent_fixture`` composes the on-disk surface writers in
``tests.tracker_surfaces`` into one parent-shaped tree: one run namespace per
requested instrument, a sealed and placed sample bundle, one unsealed staged
bundle, a published memory epoch, a cycle ledger row, and an approved trial gate.
Every instant is a keyword parameter with a fixed default, so nothing here reads
the clock.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from tests.tracker_surfaces import (
    TRACKER_SCHEMA,
    RunFixture,
    seal_claim_verdict_place,
    shift_stamp,
    uuid5_for,
    write_cycle_ledger,
    write_graduated_anchor,
    write_memory_epoch,
    write_run,
    write_staged_bundle,
    write_trial_gate,
    write_zero_epoch_marker,
)

__all__ = [
    "BASE_INSTANT",
    "INSTRUMENTS",
    "TRACKER_SCHEMA",
    "ParentFixture",
    "RunFixture",
    "parent_fixture",
]

BASE_INSTANT: Final = "2026-09-17T12:00:00Z"
INSTRUMENTS: Final[tuple[str, ...]] = ("ENGRAM", "FORGE", "CRUCIBLE")
_HARNESS_DIRS: Final[tuple[str, ...]] = (
    ".memory",
    ".seed",
    ".audit",
    ".podium",
    ".trial",
    "staging",
    "samples",
    "delivery",
)
_DISPOSITIONS: Final[Mapping[str, str]] = {
    "ENGRAM": "SHIP_ELIGIBLE",
    "FORGE": "HOLD:PILOT_REQUIRED",
    "CRUCIBLE": "BLOCK:INVALID_TASK",
}


@dataclass(frozen=True, slots=True)
class ParentFixture:
    """Every identity ``parent_fixture`` minted, so later tests assert real values."""

    root: Path
    runs: tuple[RunFixture, ...]
    sample_uuid: str | None
    staging_uuid: str | None
    anchor_uuid: str | None


def parent_fixture(
    root: Path,
    *,
    runs: Sequence[str] = INSTRUMENTS,
    late_run: bool = False,
    malformed_card: bool = False,
    graduated_anchor: bool = False,
    zero_runs: bool = False,
    now: str = BASE_INSTANT,
) -> ParentFixture:
    """Build a parent-shaped tree under ``root`` from the real production writers.

    ``zero_runs`` builds only the harness directories plus a no-epoch
    ``.memory/current.json`` and returns immediately. Otherwise one run opens per
    entry in ``runs``, an hour apart starting at ``now``, each closed with a tracker
    card, plus one sealed and placed sample bundle, one unsealed staged bundle, one
    published memory epoch, one cycle ledger row, and one approved trial gate.
    ``late_run`` adds a further run of the first requested instrument whose
    ``started_at`` precedes every other run, exercising the History insert case.
    ``malformed_card`` overwrites the last requested instrument's ``tracker.json``
    with unparseable bytes. ``graduated_anchor`` seats one anchor uuid as
    ``ANCHORED``, resident under ``delivery/`` rather than ``staging/``.
    """
    root.mkdir(parents=True, exist_ok=True)
    for name in _HARNESS_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    if zero_runs:
        write_zero_epoch_marker(root)
        return ParentFixture(
            root=root, runs=(), sample_uuid=None, staging_uuid=None, anchor_uuid=None
        )

    built: list[RunFixture] = []
    run_ids: dict[str, str] = {}
    for index, instrument in enumerate(runs):
        run_id = f"{instrument.lower()}-fixture-run-{index + 1:02d}"
        run_ids[instrument] = run_id
        built.append(
            write_run(
                root,
                instrument,
                run_id,
                principal=f"{instrument.lower()}-operator",
                started_at=shift_stamp(now, hours=index),
                disposition=_DISPOSITIONS[instrument],
                malformed_card=malformed_card and instrument == runs[-1],
            )
        )

    if late_run:
        instrument = runs[0]
        built.append(
            write_run(
                root,
                instrument,
                f"{instrument.lower()}-fixture-late-run",
                principal=f"{instrument.lower()}-operator",
                started_at=shift_stamp(now, hours=-2),
                disposition=_DISPOSITIONS[instrument],
                malformed_card=False,
            )
        )

    write_memory_epoch(root, run_id="engram-fixture-publisher", published_at=now)

    sample_uuid = uuid5_for("tracker-fixture-sample")
    seal_claim_verdict_place(
        root,
        sample_uuid,
        producer_run_id=run_ids.get("FORGE", "forge-fixture-producer"),
        consumer_run_id=run_ids.get("CRUCIBLE", "crucible-fixture-consumer"),
        sealed_at=shift_stamp(now, hours=len(runs)),
    )

    staging_uuid = uuid5_for("tracker-fixture-staged")
    write_staged_bundle(root, staging_uuid)

    anchor_uuid: str | None = None
    if graduated_anchor:
        anchor_uuid = uuid5_for("tracker-fixture-anchor")
        write_graduated_anchor(root, anchor_uuid, run_id="engram-fixture-anchor-registrar")

    write_cycle_ledger(root, at=now, disposition=_DISPOSITIONS[runs[-1]])
    write_trial_gate(root, gate_id="engram-phase-0.5")

    return ParentFixture(
        root=root,
        runs=tuple(built),
        sample_uuid=sample_uuid,
        staging_uuid=staging_uuid,
        anchor_uuid=anchor_uuid,
    )
