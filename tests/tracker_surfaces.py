"""On-disk surface writers for the tracker fixture, matching real production formats.

Every writer here matches the exact on-disk shape the production code in
``tools/runs.py``, ``tools/pipeline.py``, and ``tools/lanes.py`` emits, verified
against their source. ``tools/tracker.py`` and the dashboard renderer do not exist
yet (Task 3 and Task 5 of the tracking-dashboard plan), so the
``trinity.tracker-card/v1`` payload and the ``.trial/gates.yaml`` and
``.podium/cycles.yaml`` surfaces below are hand-assembled against the schema the
plan fixes rather than produced by a writer that has not landed.
``tools/epochs.py publish`` reads the wall clock internally with no override
parameter, which these writers must never do, so the memory epoch is
hand-assembled too, matching ``epochs.py``'s own JSON shape exactly.

Every timestamp here is a caller-supplied string; nothing in this module reads
the clock. ``tests/tracker_fixtures.py`` composes these writers into one parent
tree; this module owns the byte-exact shape of each individual surface.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from uuid import NAMESPACE_URL, uuid5

from tools import epochs, lanes, pipeline
from tools import runs as runs_module

TRACKER_SCHEMA: Final = "trinity.tracker-card/v1"
_CURRENT_SCHEMA: Final = "trinity.memory-current/v1"
_MANIFEST_SCHEMA: Final = "trinity.memory-epoch/v1"
_STAMP_FORMAT: Final = "%Y-%m-%dT%H:%M:%SZ"


def parse_stamp(stamp: str) -> datetime:
    return datetime.strptime(stamp, _STAMP_FORMAT).replace(tzinfo=UTC)


def shift_stamp(stamp: str, *, hours: int) -> str:
    return (parse_stamp(stamp) + timedelta(hours=hours)).strftime(_STAMP_FORMAT)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def uuid5_for(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, label))


def _write_json(path: Path, body: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class RunFixture:
    """What one run directory carries, so a later test can assert against it."""

    instrument: str
    run_id: str
    principal: str
    started_at: str
    disposition: str
    directory: Path
    card_path: Path | None
    closed_at: str | None


def _write_report(directory: Path, disposition: str) -> Path:
    body = (
        "## Executive summary\n\nsummary of the run\n\n"
        f"## Disposition\n\n{disposition}\n\n"
        "## Findings\n\n- one finding\n\n"
        "## Coverage gaps\n\n- one gap\n\n"
        "## Escalations\n\nnone\n\n"
        "## Flag legend\n\nlegend\n"
    )
    path = directory / "report.md"
    path.write_text(body, encoding="utf-8")
    return path


def _write_progress(directory: Path) -> Path:
    body = (
        "phase: Phase 2\nphases_done: 3\nphases_total: 6\ngates_done: 1\ngates_total: 2\n"
        "open_gates: [design]\ngaps: 1\n"
    )
    path = directory / "progress.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _write_tracker_card(
    directory: Path,
    *,
    instrument: str,
    run_id: str,
    principal: str,
    started_at: str,
    closed_at: str,
    disposition: str,
    report_path: Path,
    progress_path: Path,
) -> Path:
    """Serialize the ``trinity.tracker-card/v1`` payload exactly as the plan fixes it."""
    payload: dict[str, object] = {
        "schema": TRACKER_SCHEMA,
        "instrument": instrument,
        "run_id": run_id,
        "principal": principal,
        "started_at": started_at,
        "closed_at": closed_at,
        "disposition": disposition,
        "phase": "Phase 2",
        "phases_done": 3,
        "phases_total": 6,
        "gates_done": 1,
        "gates_total": 2,
        "open_gates": ["design"],
        "gaps": 1,
        "sources": {
            "run.json": sha256_hex((directory / "run.json").read_bytes()),
            "report.md": sha256_hex(report_path.read_bytes()),
            "progress.yaml": sha256_hex(progress_path.read_bytes()),
        },
        "parser_version": 1,
    }
    path = directory / "tracker.json"
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def write_run(
    root: Path,
    instrument: str,
    run_id: str,
    *,
    principal: str,
    started_at: str,
    disposition: str,
    malformed_card: bool,
) -> RunFixture:
    """Open a run namespace and populate report.md, progress.yaml, and tracker.json."""
    directory = runs_module.open_run(
        root, instrument, run_id, principal=principal, now=parse_stamp(started_at)
    )
    report_path = _write_report(directory, disposition)
    progress_path = _write_progress(directory)
    closed_at: str | None
    card_path: Path | None
    if malformed_card:
        card_path = directory / "tracker.json"
        card_path.write_text("{", encoding="utf-8")
        closed_at = None
    else:
        closed_at = started_at
        card_path = _write_tracker_card(
            directory,
            instrument=instrument,
            run_id=run_id,
            principal=principal,
            started_at=started_at,
            closed_at=closed_at,
            disposition=disposition,
            report_path=report_path,
            progress_path=progress_path,
        )
    return RunFixture(
        instrument=instrument,
        run_id=run_id,
        principal=principal,
        started_at=started_at,
        disposition=disposition,
        directory=directory,
        card_path=card_path,
        closed_at=closed_at,
    )


def write_staged_bundle(root: Path, uuid: str) -> Path:
    bundle = root / "staging" / uuid
    (bundle / "tests").mkdir(parents=True, exist_ok=True)
    (bundle / "task.toml").write_text(f'name = "{uuid}"\n', encoding="utf-8")
    (bundle / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    return bundle


def seal_claim_verdict_place(
    root: Path, uuid: str, *, producer_run_id: str, consumer_run_id: str, sealed_at: str
) -> None:
    """Reuse the real pipeline writers so the sealed queue chain actually verifies."""
    write_staged_bundle(root, uuid)
    lanes.route(root, lanes.LaneClaim(uuid, "sample", 1, "batch-0001", producer_run_id))
    at = parse_stamp(sealed_at)
    pipeline.seal(root, uuid, producer_run_id, at)
    pipeline.claim(root, uuid, consumer_run_id, at)
    pipeline.verdict(root, uuid, "clean", consumer_run_id, at)
    pipeline.place(root, uuid, at)


def write_graduated_anchor(root: Path, uuid: str, *, run_id: str) -> None:
    staged = write_staged_bundle(root, uuid)
    lanes.route(root, lanes.LaneClaim(uuid, "starter", 1, "batch-0001", run_id))
    staged.rename(root / "delivery" / uuid)
    body = f"# GENERATED by ENGRAM Phase H step 6b\n{uuid}: ANCHORED\n"
    (root / lanes.ANCHOR_STANDING_PATH).write_text(body, encoding="utf-8")


def write_memory_epoch(root: Path, *, run_id: str, published_at: str) -> None:
    """Hand-assemble epoch 1 in ``epochs.py``'s own shape without reading the clock."""
    manifest_path = root / epochs.EPOCHS_DIR / "1" / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema": _MANIFEST_SCHEMA,
            "epoch": 1,
            "parent_epoch": 0,
            "published_by": run_id,
            "published_at": published_at,
            "files": {},
            "proposals": [],
        },
    )
    digest = sha256_hex(manifest_path.read_bytes())
    _write_json(
        root / epochs.CURRENT_PATH,
        {"schema": _CURRENT_SCHEMA, "epoch": 1, "manifest_digest": digest},
    )


def write_zero_epoch_marker(root: Path) -> None:
    """Write the no-epoch ``.memory/current.json`` a zero-run parent still carries."""
    _write_json(root / epochs.CURRENT_PATH, {"schema": _CURRENT_SCHEMA, "epoch": 0})


def write_cycle_ledger(root: Path, *, at: str, disposition: str) -> None:
    path = root / ".podium" / "cycles.yaml"
    body = (
        "- cycle: cycle-0001\n"
        "  instrument: MAESTRO\n"
        f"  disposition: {disposition}\n"
        "  stop_reason: quota\n"
        "  samples: 1\n"
        f"  at: {at}\n"
    )
    path.write_text(body, encoding="utf-8")


def write_trial_gate(root: Path, *, gate_id: str) -> None:
    gates_path = root / ".trial" / "gates.yaml"
    gates_path.write_text(
        f"- gate_id: {gate_id}\n"
        "  contract: ENGRAM\n"
        '  phase: "Phase 0.5"\n'
        "  artifact: DIRECTIVE.md\n"
        f"  digest_file: gate-receipts/{gate_id}.sha256\n"
        "  tier: Hard\n",
        encoding="utf-8",
    )
    approvals_dir = root / ".trial" / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    (approvals_dir / gate_id).write_text(f"{'a' * 64}\n", encoding="utf-8")
