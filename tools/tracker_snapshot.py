"""Read-only, clock-free inventory consumed by the dashboard renderer."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import epochs, lanes, pipeline, runs, tracker_cache
else:
    try:
        from tools import epochs, lanes, pipeline, runs, tracker_cache
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        import epochs
        import lanes
        import pipeline
        import runs
        import tracker_cache

PARSER_VERSION: Final = tracker_cache.PARSER_VERSION
CacheLocation = tracker_cache.CacheLocation
RunRecord = tracker_cache.RunRecord
cache_location = tracker_cache.cache_location
_HISTORY_SIZE: Final = 2


@dataclass(frozen=True, slots=True)
class EpochRecord:
    epoch: int
    published_at: str
    published_by: str
    proposals: int


@dataclass(frozen=True, slots=True)
class CycleRecord:
    cycle: int
    instrument: str
    disposition: str
    stop_reason: str
    samples: int
    at: str


@dataclass(frozen=True, slots=True)
class GateRecord:
    gate: str
    contract: str
    phase: str
    artifact: str
    digest_file: str
    tier: str
    approved: bool


@dataclass(frozen=True, slots=True)
class Snapshot:
    root: Path
    as_of: str | None
    runs: tuple[RunRecord, ...]
    residents: tuple[pipeline.Resident, ...]
    staged: tuple[str, ...]
    sealed_uuids: tuple[str, ...]
    claimed_uuids: tuple[str, ...]
    audited_uuids: tuple[str, ...]
    samples_resident: int
    delivery_resident: int
    epochs: tuple[EpochRecord, ...]
    current_epoch: int
    anchor_standing: dict[str, str]
    cycles: tuple[CycleRecord, ...]
    gates: tuple[GateRecord, ...]
    harness_revision: str | None
    boundary: str | None
    diagnostics: tuple[str, ...]
    parsed_runs: int = field(compare=False)


def _flat_rows(path: Path) -> list[dict[str, str]]:
    """Only flat list mappings; malformed rows remain sentinels for diagnostics."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError):
        return [{}]
    rows: list[dict[str, str]] = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("- "):
            rows.append({})
        body = "  " + line[2:] if line.startswith("- ") else line
        if not rows:
            rows.append({"!invalid": "true"})
        match = re.fullmatch(r"  ([a-z_]+):\s*(\S.*?)\s*", body)
        if match is None or match[1] in rows[-1]:
            rows[-1]["!invalid"] = "true"
        else:
            rows[-1][match[1]] = match[2].strip("\"'")
    return rows


def _cycles(root: Path, diagnostics: list[str]) -> tuple[CycleRecord, ...]:
    result: list[CycleRecord] = []
    for index, row in enumerate(_flat_rows(root / ".podium/cycles.yaml"), 1):
        cycle = re.fullmatch(r"(?:cycle-)?([0-9]+)", row.get("cycle", ""))
        at = tracker_cache.normalize_instant(row.get("at", ""))
        if (
            "!invalid" in row
            or cycle is None
            or int(cycle[1]) < 1
            or at is None
            or not re.fullmatch(r"[0-9]+", row.get("samples", ""))
            or not all(row.get(key) for key in ("instrument", "disposition", "stop_reason"))
        ):
            diagnostics.append(f".podium/cycles.yaml row {index}: malformed cycle")
            continue
        result.append(
            CycleRecord(
                int(cycle[1]),
                tracker_cache.plain_text(row["instrument"]),
                tracker_cache.plain_text(row["disposition"]),
                tracker_cache.plain_text(row["stop_reason"]),
                int(row["samples"]),
                at,
            )
        )
    return tuple(sorted(result, key=lambda row: (row.cycle, row.at)))


def _gates(root: Path, diagnostics: list[str]) -> tuple[GateRecord, ...]:
    result: list[GateRecord] = []
    for index, row in enumerate(_flat_rows(root / ".trial/gates.yaml"), 1):
        gate = row.get("gate", row.get("gate_id", ""))
        if (
            "!invalid" in row
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", gate)
            or not all(
                row.get(key) for key in ("contract", "phase", "artifact", "digest_file", "tier")
            )
        ):
            diagnostics.append(f".trial/gates.yaml row {index}: malformed gate")
            continue
        result.append(
            GateRecord(
                gate,
                tracker_cache.plain_text(row["contract"]),
                tracker_cache.plain_text(row["phase"]),
                tracker_cache.plain_text(row["artifact"]),
                tracker_cache.plain_text(row["digest_file"]),
                tracker_cache.plain_text(row["tier"]),
                (root / ".trial/approvals" / gate).exists(),
            )
        )
    return tuple(sorted(result, key=lambda row: row.gate))


def _epochs(root: Path, diagnostics: list[str]) -> tuple[EpochRecord, ...]:
    result: list[EpochRecord] = []
    for path in sorted((root / epochs.EPOCHS_DIR).glob("*/manifest.json")):
        row = epochs._read_json(path) or {}
        epoch, author, proposals = row.get("epoch"), row.get("published_by"), row.get("proposals")
        at = tracker_cache.normalize_instant(str(row.get("published_at", "")))
        if (
            row.get("schema") != epochs.MANIFEST_SCHEMA
            or not isinstance(epoch, int)
            or isinstance(epoch, bool)
            or epoch < 1
            or str(epoch) != path.parent.name
            or not isinstance(author, str)
            or not isinstance(proposals, list)
            or at is None
        ):
            diagnostics.append(f"{path.relative_to(root)}: malformed epoch")
            continue
        result.append(EpochRecord(epoch, at, tracker_cache.plain_text(author), len(proposals)))
    return tuple(sorted(result, key=lambda row: row.epoch))


def load_snapshot(
    root: Path, *, cache: CacheLocation | Path | None = None, persist: bool = True
) -> Snapshot:
    """Project persisted evidence, with disposable parsing work excluded from equality."""
    location = CacheLocation(cache, persist=persist) if isinstance(cache, Path) else cache
    if location is None:
        location = cache_location(root, persist=persist)
    protected = (
        *runs.HARNESS.values(),
        ".trial",
        ".podium",
        "samples",
        "delivery",
        "staging",
        ".sentinel",
    )
    if location is not None and any(
        location.path.resolve().is_relative_to((root / p).resolve()) for p in protected
    ):
        location = None
    records, parsed = tracker_cache.load_runs(root, location)
    diagnostics = [
        f"{runs.HARNESS[r.instrument]}/runs/{r.run_id}/tracker.json: closure unknown"
        for r in records
        if r.closure == "unknown"
    ]
    cycles, gates, published = (
        _cycles(root, diagnostics),
        _gates(root, diagnostics),
        _epochs(root, diagnostics),
    )
    findings, queue = pipeline.walk_queue(root)
    diagnostics.extend(f"queue: {finding.code}" for finding in findings)
    residents = tuple(pipeline._residents(root))
    sealed = tuple(sorted({str(row["uuid"]) for row in queue}))
    claim_ids = {p.name for p in (root / pipeline.CLAIMS_DIR).glob("*") if p.is_dir()}
    verdict_ids = {
        p.stem if p.is_file() else p.name for p in (root / pipeline.VERDICTS_DIR).glob("*")
    }
    ids = sorted(set(sealed) | claim_ids | verdict_ids)
    claims = {uuid: pipeline.claims_for(root, uuid) for uuid in ids}
    instants = [r.started_at for r in records] + [r.closed_at for r in records if r.closed_at]
    instants += [str(row["sealed_at"]) for row in queue]
    instants += [row["claimed_at"] for rows in claims.values() for row in rows]
    instants += [row.published_at for row in published] + [row.at for row in cycles]
    newest = max(
        (stamp for value in instants if (stamp := tracker_cache.normalize_instant(value))),
        default=None,
    )
    current = epochs.current(root)
    boundary = (
        f"epoch-{current - 1}"
        if current >= _HISTORY_SIZE and any(e.epoch == current - 1 for e in published)
        else None
    )
    if boundary is None and len({row.cycle for row in cycles}) >= _HISTORY_SIZE:
        boundary = f"cycle-{sorted({row.cycle for row in cycles})[-2]}"
    revision = tracker_cache.git_output(root, ("ls-files", "-s", "harness")) or ""
    match = re.fullmatch(r"160000 ([0-9a-f]{40,64}) 0\tharness", revision)
    try:
        standing = lanes.anchor_standing(root)
    except lanes.AnchorStandingError:
        standing = {}
        diagnostics.append(".memory/anchor_standing.yaml: malformed standing")
    return Snapshot(
        root=root,
        as_of=newest,
        runs=records,
        residents=residents,
        staged=tuple(sorted(lanes.resident_uuids(root / pipeline.STAGING_DIR))),
        sealed_uuids=sealed,
        claimed_uuids=tuple(uuid for uuid in ids if claims[uuid]),
        audited_uuids=tuple(uuid for uuid in ids if pipeline.verdict_records(root, uuid)),
        samples_resident=sum(r.lane_root == "samples" for r in residents),
        delivery_resident=sum(r.lane_root == "delivery" for r in residents),
        epochs=published,
        current_epoch=current,
        anchor_standing={uuid: tracker_cache.plain_text(state) for uuid, state in standing.items()},
        cycles=cycles,
        gates=gates,
        harness_revision=match[1] if match else None,
        boundary=boundary,
        diagnostics=tuple(diagnostics),
        parsed_runs=parsed,
    )


def as_of_instant(root: Path) -> str | None:
    """Newest normalized persisted instant; no activity has no substitute date."""
    return load_snapshot(root).as_of
