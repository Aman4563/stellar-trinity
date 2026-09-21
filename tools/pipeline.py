"""Sealed-bundle queue: the only channel from FORGE (producer) to CRUCIBLE (consumer).

FORGE seals a slot under ``staging/<uuid>/`` after its Phase 2 Bucket D passes,
appending its uuid and digest to the hash-chained ``.podium/queue.jsonl``.
CRUCIBLE claims the sealed bytes with an atomic ``O_EXCL`` claim file, then uses
``verdict`` to record the uuid, digest, and ``clean`` or ``retained`` outcome in
``.audit/verdicts/<uuid>.json`` and release the claim. Verdicts are immutable at
the sealed digest. Claim and verify locate bundles across staging, samples, and
delivery; only an absent bundle with a matching retained verdict is exempt from
byte checks. FORGE uses ``route`` before sealing to bind the slot's task lane by the
residency rule in ``tools/lanes.py`` and ``place`` afterwards to rename clean staged
bytes into that registered lane root, within each root's ceiling. No finding, pass
criterion, or hardness row enters the queue, the registry, or the verdict.

Finding codes from ``verify``: ``PIPELINE_CHAIN_BROKEN``, ``PIPELINE_SEALED_MUTATED``,
``PIPELINE_UNSEALED_AUDIT``, ``PIPELINE_BACKPRESSURE``, ``PIPELINE_STALE_CLAIM``, and
``PIPELINE_CONFIG_INVALID``, ``PIPELINE_PLACED_UNCLEAN``, ``PIPELINE_STREAM_CONFLICT``,
``PIPELINE_STREAM_REWRITTEN``, and ``PIPELINE_VERDICT_UNOWNED``. ``seal``, ``claim``, and
``verdict`` raise ``PipelineError``; ``place`` raises its closed-code ``PlaceError`` and
``route`` its closed-code ``RouteError``: a seal past the backpressure bound, a claim on
bytes that moved after sealing, and a second claim on a bundle another consumer already
holds.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING:
    from tools._findings import Finding, Severity, render_finding, serialize_findings
    from tools.bundle_identity import BundleIdentityError
    from tools.bundle_identity import bundle_digest as canonical_bundle_digest
    from tools.lanes import (
        ANCHOR_STANDING_PATH,
        GRADUATED_ANCHOR_STATES,
        LANE_CEILINGS,
        LANE_UNRESOLVED_DETAILS,
        LANES_DIR,
        LEGACY_LANES_PATH,
        TASK_LANE_ROOTS,
        AnchorStandingError,
        LaneClaim,
        RouteError,
        anchor_standing,
        registered_lanes,
        registry_items,
        resident_uuids,
        route,
    )
    from tools.project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
    from tools.report_staging import staged_reports
    from tools.reports import check_root_reports, is_parent, render_root_reports
else:
    try:
        from tools._findings import Finding, Severity, render_finding, serialize_findings
        from tools.bundle_identity import BundleIdentityError
        from tools.bundle_identity import bundle_digest as canonical_bundle_digest
        from tools.lanes import (
            ANCHOR_STANDING_PATH,
            GRADUATED_ANCHOR_STATES,
            LANE_CEILINGS,
            LANE_UNRESOLVED_DETAILS,
            LANES_DIR,
            LEGACY_LANES_PATH,
            TASK_LANE_ROOTS,
            AnchorStandingError,
            LaneClaim,
            RouteError,
            anchor_standing,
            registered_lanes,
            registry_items,
            resident_uuids,
            route,
        )
        from tools.project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
        from tools.report_staging import staged_reports
        from tools.reports import check_root_reports, is_parent, render_root_reports
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from _findings import Finding, Severity, render_finding, serialize_findings
        from bundle_identity import BundleIdentityError
        from bundle_identity import bundle_digest as canonical_bundle_digest
        from lanes import (
            ANCHOR_STANDING_PATH,
            GRADUATED_ANCHOR_STATES,
            LANE_CEILINGS,
            LANE_UNRESOLVED_DETAILS,
            LANES_DIR,
            LEGACY_LANES_PATH,
            TASK_LANE_ROOTS,
            AnchorStandingError,
            LaneClaim,
            RouteError,
            anchor_standing,
            registered_lanes,
            registry_items,
            resident_uuids,
            route,
        )
        from project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
        from report_staging import staged_reports
        from reports import check_root_reports, is_parent, render_root_reports

QUEUE_PATH = Path(".podium/queue.jsonl")
QUEUE_DIR = Path(".podium/queue")
LEGACY_STREAM = "legacy"
_STREAM_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
CONFIG_PATH = Path(".podium/pipeline.json")
VERDICTS_DIR = Path(".audit/verdicts")
CLAIMS_DIR = Path(".audit/queue.claims")
STAGING_DIR = Path("staging")
LANE_DIRS: tuple[Path, ...] = (Path("samples"), Path("delivery"))
BUNDLE_DIRS = (STAGING_DIR, *LANE_DIRS)

PLACE_CODES = frozenset(
    {
        "queue-broken",
        "unsealed",
        "multi-root",
        "absent",
        "bundle-unreadable",
        "staged-digest-mismatch",
        "verdict-missing",
        "verdict-digest-mismatch",
        "verdict-legacy",
        "retained",
        "lane-unresolved",
        "lane-root-missing",
        "cross-device",
        "rename-failed",
        "post-rename-digest-drift",
    }
)
PLACE_DETAILS: dict[str, tuple[str, ...]] = {
    "queue-broken": ("sealed queue is broken",),
    "unsealed": ("bundle {uuid} was never sealed",),
    "multi-root": ("bundle {uuid} is resident under more than one root",),
    "absent": ("bundle {uuid} is absent from staging/, samples/, and delivery/",),
    "bundle-unreadable": ("bundle is unreadable at {path}",),
    "staged-digest-mismatch": ("bundle {uuid} under {lane}/ differs from its sealed digest",),
    "verdict-missing": ("bundle {uuid} has no valid verdict",),
    "verdict-digest-mismatch": ("verdict for {uuid} differs from its sealed digest",),
    "verdict-legacy": ("verdict for {uuid} has no outcome",),
    "retained": ("verdict retained findings; FORGE must author a successor",),
    "lane-unresolved": LANE_UNRESOLVED_DETAILS,
    "lane-root-missing": ("lane root {lane}/ is missing or is not a directory",),
    "cross-device": ("bundle {uuid} cannot be renamed across devices",),
    "rename-failed": ("bundle {uuid} could not be renamed into {lane}/",),
    "post-rename-digest-drift": ("bundle {uuid} under {lane}/ changed after rename",),
}

GENESIS_HASH = "0" * 64
DEFAULT_MAX_UNAUDITED = 31  # one full FORGE batch, thirty ordinary slots plus its anchor
DEFAULT_CLAIM_TTL_HOURS = 6.0

QUEUE_FIELDS = frozenset(
    {"seq", "uuid", "bundle_digest", "sealed_at", "producer_run_id", "prev_hash", "entry_hash"}
)
CLAIM_FIELDS = frozenset({"uuid", "bundle_digest", "consumer_run_id", "claimed_at"})
VERDICT_OUTCOMES = frozenset({"clean", "retained"})
VERDICT_FIELDS = frozenset({"uuid", "bundle_digest", "outcome", "consumer_run_id"})

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


class PipelineError(ValueError):
    """Raised when a pipeline operation must refuse."""


class PlaceError(PipelineError):
    """A placement refusal with a closed public code and mechanical detail."""

    code: str
    detail: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _now(evaluation_time: datetime | None = None) -> datetime:
    if evaluation_time is None:
        return datetime.now(UTC)
    if evaluation_time.tzinfo is None:
        raise PipelineError("evaluation time must carry a timezone")
    return evaluation_time.astimezone(UTC)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_stamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PipelineError(f"timestamp {value!r} is not an RFC 3339 UTC instant")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise PipelineError(f"timestamp {value!r} is not an RFC 3339 UTC instant") from exc


def _finding(path: Path, code: str, message: str, line: int | None = None) -> Finding:
    return Finding(code, Severity.ERROR, str(path), line, message)


def _refuses(findings: Iterable[Finding]) -> bool:
    """Only an error-severity finding refuses; an advisory is printed and lets the command pass."""
    return any(item.severity is Severity.ERROR for item in findings)


def chain_digest(entry: dict[str, object]) -> str:
    """Digest a queue line the way the feedback chain does: canonical JSON minus entry_hash."""
    body = {key: value for key, value in entry.items() if key not in ("entry_hash", "stream")}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def bundle_digest(bundle_root: Path) -> str:
    """Return the shared canonical bundle identity or a pipeline refusal."""
    try:
        return canonical_bundle_digest(bundle_root)
    except BundleIdentityError as exc:
        raise PipelineError(str(exc)) from exc


def _occupancy(root: Path, uuid: str) -> list[tuple[Path, str]]:
    """Inventory bundle roots without treating links or other objects as absence."""
    occupants: list[tuple[Path, str]] = []
    for directory in BUNDLE_DIRS:
        path = root / directory / uuid
        try:
            metadata = os.lstat(path)
        except FileNotFoundError:
            continue
        occupants.append((path, "dir" if stat.S_ISDIR(metadata.st_mode) else "unsafe"))
    return occupants


def _bundle_homes(root: Path, uuid: str) -> list[Path]:
    occupants = _occupancy(root, uuid)
    for path, kind in occupants:
        if kind == "unsafe":
            raise PipelineError(f"bundle {uuid} has an unsafe object at {path}")
    return [path for path, kind in occupants if kind == "dir"]


def _bundle_path(root: Path, uuid: str) -> Path:
    homes = _bundle_homes(root, uuid)
    if len(homes) > 1:
        raise PipelineError(f"bundle {uuid} is resident under more than one root")
    if not homes:
        raise PipelineError(f"bundle {uuid} is absent from staging/, samples/, and delivery/")
    return homes[0]


def load_config(root: Path) -> tuple[int, float]:
    """Return (max_unaudited, claim_ttl_hours) from .podium/pipeline.json or the defaults."""
    config_path = root / CONFIG_PATH
    if not config_path.is_file():
        return DEFAULT_MAX_UNAUDITED, DEFAULT_CLAIM_TTL_HOURS
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(f"pipeline config is unreadable: {exc}") from exc
    if not isinstance(raw, dict):
        raise PipelineError("pipeline config must be a JSON object")
    unknown = sorted(set(raw) - {"max_unaudited", "claim_ttl_hours"})
    if unknown:
        raise PipelineError(f"pipeline config carries unknown fields: {', '.join(unknown)}")
    max_unaudited = raw.get("max_unaudited", DEFAULT_MAX_UNAUDITED)
    ttl = raw.get("claim_ttl_hours", DEFAULT_CLAIM_TTL_HOURS)
    if isinstance(max_unaudited, bool) or not isinstance(max_unaudited, int) or max_unaudited < 1:
        raise PipelineError("max_unaudited must be a positive integer")
    if isinstance(ttl, bool) or not isinstance(ttl, int | float) or ttl <= 0:
        raise PipelineError("claim_ttl_hours must be a positive number")
    return max_unaudited, float(ttl)


def streams(root: Path) -> dict[str, Path]:
    """Every queue stream on disk: the legacy singleton plus one file per producer run."""
    found: dict[str, Path] = {}
    legacy = root / QUEUE_PATH
    if legacy.is_file():
        found[LEGACY_STREAM] = legacy
    directory = root / QUEUE_DIR
    if directory.is_dir():
        for path in sorted(directory.glob("*.jsonl")):
            if path.is_file() and _STREAM_NAME.fullmatch(path.stem) and path.stem != LEGACY_STREAM:
                found[path.stem] = path
    return found


def stream_path(root: Path, run_id: str) -> Path:
    if _STREAM_NAME.fullmatch(run_id) is None or run_id == LEGACY_STREAM or ".." in run_id:
        raise PipelineError(f"producer run id {run_id!r} cannot name a queue stream")
    return root / QUEUE_DIR / f"{run_id}.jsonl"


def _read_queue_lines(queue_path: Path) -> list[tuple[int, dict[str, object]]]:
    if not queue_path.is_file():
        return []
    out: list[tuple[int, dict[str, object]]] = []
    with queue_path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                raise PipelineError(f"queue line {number} is blank")
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PipelineError(f"queue line {number} is not JSON: {exc}") from exc
            if not isinstance(entry, dict):
                raise PipelineError(f"queue line {number} is not an object")
            out.append((number, entry))
    return out


def _line_shape_errors(entry: dict[str, object]) -> list[str]:
    errors: list[str] = []
    fields = set(entry)
    errors += [f"missing field {name}" for name in sorted(QUEUE_FIELDS - fields)]
    errors += [f"unknown field {name}" for name in sorted(fields - QUEUE_FIELDS)]
    if errors:
        return errors
    seq = entry["seq"]
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 1:
        errors.append("seq is not a positive integer")
    uuid = entry["uuid"]
    if not isinstance(uuid, str) or _UUID.fullmatch(uuid) is None:
        errors.append("uuid is not a lowercase uuid")
    for name in ("bundle_digest", "prev_hash", "entry_hash"):
        value = entry[name]
        if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
            errors.append(f"{name} is not a lowercase hex sha-256 digest")
    try:
        _parse_stamp(entry["sealed_at"])
    except PipelineError as exc:
        errors.append(str(exc))
    run_id = entry["producer_run_id"]
    if not isinstance(run_id, str) or not run_id:
        errors.append("producer_run_id is not a non-empty string")
    return errors


def walk_stream(
    root: Path, name: str, queue_path: Path
) -> tuple[list[Finding], list[dict[str, object]]]:
    """Verify one stream's chain and return findings plus its accepted records in order."""
    out: list[Finding] = []
    records: list[dict[str, object]] = []
    try:
        lines = _read_queue_lines(queue_path)
    except PipelineError as exc:
        return [_finding(queue_path, "PIPELINE_CHAIN_BROKEN", str(exc))], []
    prev_hash = GENESIS_HASH
    expected_seq = 1
    for number, entry in lines:
        shape = _line_shape_errors(entry)
        if name != LEGACY_STREAM and not shape and entry["producer_run_id"] != name:
            shape.append(f"producer_run_id {entry['producer_run_id']!r} is not the stream {name}")
        if shape:
            out += [
                _finding(queue_path, "PIPELINE_CHAIN_BROKEN", message, number) for message in shape
            ]
            return out, records
        if entry["seq"] != expected_seq:
            message = f"seq is {entry['seq']!r} where the chain expects {expected_seq}"
            out.append(_finding(queue_path, "PIPELINE_CHAIN_BROKEN", message, number))
            return out, records
        if entry["prev_hash"] != prev_hash:
            message = f"prev_hash does not link to the preceding line, expected {prev_hash}"
            out.append(_finding(queue_path, "PIPELINE_CHAIN_BROKEN", message, number))
            return out, records
        recomputed = chain_digest(entry)
        if entry["entry_hash"] != recomputed:
            message = f"entry_hash does not cover this line, expected {recomputed}"
            out.append(_finding(queue_path, "PIPELINE_CHAIN_BROKEN", message, number))
            return out, records
        records.append({**entry, "stream": name})
        prev_hash = str(entry["entry_hash"])
        expected_seq += 1
    del root
    return out, records


def _record_order(record: dict[str, object]) -> tuple[str, str, int]:
    return (str(record["sealed_at"]), str(record["stream"]), int(str(record["seq"])))


def walk_queue(root: Path) -> tuple[list[Finding], list[dict[str, object]]]:
    """Verify every stream and return findings plus the union of records in seal order."""
    out: list[Finding] = []
    records: list[dict[str, object]] = []
    for name, queue_path in streams(root).items():
        findings, accepted = walk_stream(root, name, queue_path)
        out += findings
        records += accepted
    return out, sorted(records, key=_record_order)


def _latest_per_stream(records: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """The latest record per uuid, streams reconciled: equal digests dedupe, unequal conflict."""
    per_stream: dict[tuple[str, str], dict[str, object]] = {}
    for record in records:
        per_stream[(str(record["stream"]), str(record["uuid"]))] = record
    latest: dict[str, dict[str, object]] = {}
    for record in sorted(per_stream.values(), key=_record_order):
        uuid = str(record["uuid"])
        held = latest.get(uuid)
        if held is None:
            latest[uuid] = record
        elif held["bundle_digest"] != record["bundle_digest"]:
            raise PipelineError(
                f"stream conflict: {uuid} is sealed at different digests by "
                f"{held['stream']} and {record['stream']}"
            )
    return latest


def _stream_conflicts(root: Path, records: list[dict[str, object]]) -> list[Finding]:
    try:
        _latest_per_stream(records)
    except PipelineError as exc:
        return [_finding(root / QUEUE_DIR, "PIPELINE_STREAM_CONFLICT", str(exc))]
    return []


def sealed_records(root: Path) -> dict[str, dict[str, object]]:
    """Latest sealed record per uuid, raising on a broken chain."""
    findings, records = walk_queue(root)
    if findings:
        raise PipelineError(findings[0].message)
    return _latest_per_stream(records)


def seal(root: Path, uuid: str, run_id: str, evaluation_time: datetime | None = None) -> str:
    """Seal ``staging/<uuid>/`` by appending its digest to the queue. Returns the digest."""
    if _UUID.fullmatch(uuid) is None:
        raise PipelineError(f"{uuid!r} is not a lowercase uuid")
    if not run_id:
        raise PipelineError("producer run id must be non-empty")
    homes = _bundle_homes(root, uuid)
    if any(root / lane / uuid in homes for lane in LANE_DIRS):
        raise PipelineError(f"bundle {uuid} is already placed; changed bytes make a new uuid")
    staged = root / STAGING_DIR / uuid
    if staged not in homes:
        raise PipelineError(f"bundle {uuid} is not staged")
    digest = bundle_digest(staged)
    max_unaudited, _ = load_config(root)
    latest = sealed_records(root)
    if uuid in latest:
        sealed_digest = str(latest[uuid]["bundle_digest"])
        recorded = _read_verdict(root, uuid, sealed_digest)
        if recorded is not None:
            refusals = {
                "retained": f"bundle {uuid} was retained; author a successor under a new uuid",
                "clean": f"bundle {uuid} was judged clean; place it, never reseal",
                None: f"bundle {uuid} has a legacy verdict; never reseal it",
            }
            raise PipelineError(refusals[recorded.get("outcome")])
        if sealed_digest == digest:
            raise PipelineError(f"bundle {uuid} is already sealed at this digest")
        raise PipelineError(
            f"bundle {uuid} is sealed and awaiting audit; "
            "a sealed bundle is frozen until a verdict lands"
        )
    depth = len(_pending_from(root, latest))
    if depth >= max_unaudited:
        raise PipelineError(
            f"backpressure: {depth} sealed bundles await audit, the bound is {max_unaudited}"
        )
    queue_path = stream_path(root, run_id)
    findings, records = walk_stream(root, run_id, queue_path)
    if findings:
        raise PipelineError(findings[0].message)
    prev_hash = str(records[-1]["entry_hash"]) if records else GENESIS_HASH
    entry: dict[str, object] = {
        "seq": len(records) + 1,
        "uuid": uuid,
        "bundle_digest": digest,
        "sealed_at": _stamp(_now(evaluation_time)),
        "producer_run_id": run_id,
        "prev_hash": prev_hash,
    }
    entry["entry_hash"] = chain_digest(entry)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with queue_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return digest


def _parse_verdict(path: Path, uuid: str) -> dict[str, str] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or not set(raw) <= VERDICT_FIELDS:
        return None
    if not all(isinstance(value, str) for value in raw.values()):
        return None
    if raw.get("uuid") != uuid:
        return None
    digest = raw.get("bundle_digest")
    if not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
        return None
    if "outcome" in raw and raw["outcome"] not in VERDICT_OUTCOMES:
        return None
    if path.parent.name == uuid and path.stem != digest:
        return None
    return {key: value for key, value in raw.items() if isinstance(value, str)}


def verdict_records(root: Path, uuid: str) -> dict[str, dict[str, str]]:
    """Every readable verdict for ``uuid`` keyed by bundle digest, legacy layout included."""
    out: dict[str, dict[str, str]] = {}
    legacy = _parse_verdict(root / VERDICTS_DIR / f"{uuid}.json", uuid)
    if legacy is not None:
        out[legacy["bundle_digest"]] = legacy
    directory = root / VERDICTS_DIR / uuid
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            record = _parse_verdict(path, uuid)
            if record is not None:
                out[record["bundle_digest"]] = record
    return out


def _read_verdict(root: Path, uuid: str, digest: str | None = None) -> dict[str, str] | None:
    """The verdict at ``digest``, or the single verdict on disk when no digest is named."""
    records = verdict_records(root, uuid)
    if digest is not None:
        return records.get(digest)
    if len(records) == 1:
        return next(iter(records.values()))
    return None


def _read_verdict_digest(root: Path, uuid: str, digest: str | None = None) -> str | None:
    record = _read_verdict(root, uuid, digest)
    return record["bundle_digest"] if record is not None else None


def _parse_claim(path: Path, uuid: str) -> dict[str, str] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or set(raw) != CLAIM_FIELDS:
        return None
    if not all(isinstance(value, str) for value in raw.values()):
        return None
    if raw["uuid"] != uuid or _HEX64.fullmatch(raw["bundle_digest"]) is None:
        return None
    if path.parent.name == uuid and path.stem != raw["consumer_run_id"]:
        return None
    try:
        _parse_stamp(raw["claimed_at"])
    except PipelineError:
        return None
    return {key: value for key, value in raw.items() if isinstance(value, str)}


def _claim_paths(root: Path, uuid: str) -> list[Path]:
    paths: list[Path] = []
    legacy = root / CLAIMS_DIR / f"{uuid}.json"
    if legacy.is_file():
        paths.append(legacy)
    directory = root / CLAIMS_DIR / uuid
    if directory.is_dir():
        paths += sorted(path for path in directory.glob("*.json") if path.is_file())
    return paths


def claims_for(root: Path, uuid: str) -> list[dict[str, str]]:
    """Every readable claim on ``uuid`` in ownership order: earliest instant, then run id."""
    found = [
        record
        for path in _claim_paths(root, uuid)
        if (record := _parse_claim(path, uuid)) is not None
    ]
    return sorted(found, key=lambda item: (item["claimed_at"], item["consumer_run_id"]))


def claim_owner(root: Path, uuid: str, digest: str) -> dict[str, str] | None:
    """The claim that owns ``uuid`` at ``digest``: the earliest claim bound to that digest."""
    for record in claims_for(root, uuid):
        if record["bundle_digest"] == digest:
            return record
    return None


def _read_claim(root: Path, uuid: str, consumer_run_id: str | None = None) -> dict[str, str] | None:
    """One consumer's claim, or the single claim on disk when no consumer is named."""
    records = claims_for(root, uuid)
    if consumer_run_id is not None:
        for record in records:
            if record["consumer_run_id"] == consumer_run_id:
                return record
        return None
    return records[0] if len(records) == 1 else None


def _pending_from(root: Path, latest: dict[str, dict[str, object]]) -> list[str]:
    out: list[str] = []
    for uuid in sorted(latest, key=lambda key: _record_order(latest[key])):
        digest = str(latest[uuid]["bundle_digest"])
        if _read_verdict_digest(root, uuid, digest) != digest:
            out.append(uuid)
    return out


def pending(root: Path) -> list[str]:
    """Sealed uuids with no verdict at the sealed digest, in seal order."""
    return _pending_from(root, sealed_records(root))


def claim(
    root: Path, uuid: str, consumer_run_id: str, evaluation_time: datetime | None = None
) -> Path:
    """Claim a sealed bundle for one consumer run. Refuses while another claim stands.

    Claims are files named by their consumer under ``.audit/queue.claims/<uuid>/``, so two
    clones claiming the same bundle never conflict at merge; the earliest claim at the
    sealed digest owns the bundle and ``verify`` reports a verdict by anyone else.
    """
    if not consumer_run_id or _STREAM_NAME.fullmatch(consumer_run_id) is None:
        raise PipelineError("consumer run id must be non-empty")
    latest = sealed_records(root)
    if uuid not in latest:
        raise PipelineError(f"bundle {uuid} was never sealed")
    record = latest[uuid]
    current = bundle_digest(_bundle_path(root, uuid))
    if current != record["bundle_digest"]:
        raise PipelineError(f"bundle {uuid} bytes moved after sealing; refuse to audit")
    digest = str(record["bundle_digest"])
    if _read_verdict_digest(root, uuid, digest) == digest:
        raise PipelineError(f"bundle {uuid} is already judged at this digest")
    if claim_owner(root, uuid, digest) is not None:
        raise PipelineError(f"bundle {uuid} is already claimed by another consumer")
    claims_dir = root / CLAIMS_DIR / uuid
    claims_dir.mkdir(parents=True, exist_ok=True)
    claim_path = claims_dir / f"{consumer_run_id}.json"
    body: dict[str, object] = {
        "uuid": uuid,
        "bundle_digest": record["bundle_digest"],
        "consumer_run_id": consumer_run_id,
        "claimed_at": _stamp(_now(evaluation_time)),
    }
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        descriptor = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise PipelineError(f"bundle {uuid} is already claimed by another consumer") from exc
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return claim_path


def release_claim(root: Path, uuid: str, consumer_run_id: str | None = None) -> None:
    """Drop one consumer's claim when it gives up; a verdict never releases its claim."""
    for path in _claim_paths(root, uuid):
        record = _parse_claim(path, uuid)
        if record is None:
            continue
        if consumer_run_id is None or record["consumer_run_id"] == consumer_run_id:
            path.unlink()


def verdict(
    root: Path,
    uuid: str,
    outcome: str,
    consumer_run_id: str,
    evaluation_time: datetime | None = None,
) -> Path:
    """Record the owning claim's outcome once per sealed digest. The claim stays as evidence."""
    if outcome not in VERDICT_OUTCOMES:
        raise PipelineError("outcome must be clean or retained")
    latest = sealed_records(root)
    if uuid not in latest:
        raise PipelineError(f"bundle {uuid} was never sealed")
    digest = str(latest[uuid]["bundle_digest"])
    held = _read_claim(root, uuid, consumer_run_id)
    owner = claim_owner(root, uuid, digest)
    if held is None and owner is None:
        raise PipelineError(f"bundle {uuid} is not claimed")
    if held is None or (owner is not None and owner["consumer_run_id"] != consumer_run_id):
        raise PipelineError(f"claim on {uuid} belongs to another consumer")
    if held["bundle_digest"] != digest:
        raise PipelineError(f"claim on {uuid} is stale; the bundle was resealed")
    if bundle_digest(_bundle_path(root, uuid)) != digest:
        raise PipelineError(f"bundle {uuid} bytes moved after sealing; refuse to record a verdict")
    if _read_verdict_digest(root, uuid, digest) == digest:
        raise PipelineError(f"verdict for {uuid} already exists at this digest")
    _now(evaluation_time)
    path = root / VERDICTS_DIR / uuid / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "uuid": uuid,
        "bundle_digest": digest,
        "outcome": outcome,
        "consumer_run_id": consumer_run_id,
    }
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.replace(temporary, path)  # noqa: PTH105 - publication must be one atomic replace.
        finally:
            temporary.unlink(missing_ok=True)
    return path


def _all_claim_paths(root: Path) -> list[Path]:
    claims_dir = root / CLAIMS_DIR
    if not claims_dir.is_dir():
        return []
    paths: list[Path] = []
    for entry in sorted(claims_dir.iterdir()):
        if entry.is_file() and entry.suffix == ".json":
            paths.append(entry)
        elif entry.is_dir():
            paths += sorted(path for path in entry.glob("*.json") if path.is_file())
    return paths


def _claim_findings(
    root: Path, latest: dict[str, dict[str, object]], now: datetime, ttl_hours: float
) -> list[Finding]:
    out: list[Finding] = []
    for claim_path in _all_claim_paths(root):
        try:
            raw = json.loads(claim_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            out.append(_finding(claim_path, "PIPELINE_STALE_CLAIM", f"claim is unreadable: {exc}"))
            continue
        if not isinstance(raw, dict) or set(raw) != CLAIM_FIELDS:
            out.append(_finding(claim_path, "PIPELINE_STALE_CLAIM", "claim has the wrong shape"))
            continue
        uuid = str(raw["uuid"])
        if uuid not in latest:
            out.append(
                _finding(claim_path, "PIPELINE_UNSEALED_AUDIT", f"claim names unsealed {uuid}")
            )
            continue
        digest = str(latest[uuid]["bundle_digest"])
        if _read_verdict_digest(root, uuid, digest) == digest:
            continue
        owner = claim_owner(root, uuid, digest)
        if owner is not None and owner["consumer_run_id"] != raw["consumer_run_id"]:
            continue
        try:
            claimed_at = _parse_stamp(raw["claimed_at"])
        except PipelineError as exc:
            out.append(_finding(claim_path, "PIPELINE_STALE_CLAIM", str(exc)))
            continue
        if now - claimed_at > timedelta(hours=ttl_hours):
            message = f"claim on {uuid} is older than {ttl_hours} hours with no verdict"
            out.append(_finding(claim_path, "PIPELINE_STALE_CLAIM", message))
    return out


def _unowned_verdict_findings(root: Path, latest: dict[str, dict[str, object]]) -> list[Finding]:
    """A verdict written by a consumer that does not own the claim at that digest."""
    out: list[Finding] = []
    for uuid, record in latest.items():
        digest = str(record["bundle_digest"])
        recorded = verdict_records(root, uuid).get(digest)
        if recorded is None or "consumer_run_id" not in recorded:
            continue
        owner = claim_owner(root, uuid, digest)
        if owner is not None and owner["consumer_run_id"] != recorded["consumer_run_id"]:
            message = (
                f"verdict on {uuid} was written by {recorded['consumer_run_id']} while "
                f"{owner['consumer_run_id']} holds the earliest claim"
            )
            out.append(_finding(root / VERDICTS_DIR / uuid, "PIPELINE_VERDICT_UNOWNED", message))
    return out


def resolve_task_lane(root: Path, uuid: str) -> str:
    """Read indent-bounded dash items, including each opening line in its body.

    A nonblank line at or above the dash indent ends the item. UUID rows may
    include the dash; task_lane rows require indentation and an unquoted token.
    Identical duplicate bindings are accepted, but distinct tokens disagree.
    """
    details = PLACE_DETAILS["lane-unresolved"]
    try:
        record_token = registered_lanes(root).get(uuid) if (root / LANES_DIR).is_dir() else None
    except RouteError as exc:
        raise PlaceError("lane-unresolved", details[0]) from exc
    if record_token is not None:
        return TASK_LANE_ROOTS[record_token]
    try:
        lines = (root / LEGACY_LANES_PATH).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise PlaceError("lane-unresolved", details[0]) from exc
    uuid_row = re.compile(rf"^[ \t]*(?:-[ \t]+)?uuid:[ \t]*{re.escape(uuid)}[ \t]*(?:#.*)?$")
    lane_row = re.compile(r"^[ \t]+task_lane:[ \t]*([A-Za-z_]+)[ \t]*(?:#.*)?$")
    lanes: set[str] = set()
    for body in registry_items(lines):
        if not any(uuid_row.fullmatch(row) for row in body):
            continue
        tokens = [match[1] for row in body if (match := lane_row.fullmatch(row))]
        if not tokens:
            raise PlaceError("lane-unresolved", details[2])
        if len(tokens) > 1:
            raise PlaceError("lane-unresolved", details[3])
        lanes.add(tokens[0])
    if not lanes:
        raise PlaceError("lane-unresolved", details[1])
    if len(lanes) > 1:
        raise PlaceError("lane-unresolved", details[4])
    token = next(iter(lanes))
    if token not in TASK_LANE_ROOTS:
        raise PlaceError("lane-unresolved", details[5].format(value=token[:32]))
    return TASK_LANE_ROOTS[token]


def _placement_digest(root: Path, path: Path) -> str:
    """Keep identity-reader diagnostics outside the placement public payload."""
    try:
        return bundle_digest(path)
    except (BundleIdentityError, PipelineError) as exc:
        detail = PLACE_DETAILS["bundle-unreadable"][0].format(
            path=display_project_path(path.absolute(), project_root=root.absolute())
        )
        raise PlaceError("bundle-unreadable", detail) from exc


def place(root: Path, uuid: str, evaluation_time: datetime | None = None) -> tuple[str, Path]:
    """Authorize a clean binding before an idempotent retry or one atomic rename.

    A destination already occupied at inventory time is rejected before rename:
    a staged source plus a destination directory is multi-root, any other object
    is unreadable. Post-rename drift is refused without ever renaming back.
    Placement has no time-dependent authorization rule.
    """
    del evaluation_time
    try:
        latest = sealed_records(root)
    except (PipelineError, OSError, UnicodeDecodeError) as exc:
        raise PlaceError("queue-broken", PLACE_DETAILS["queue-broken"][0]) from exc
    if uuid not in latest:
        raise PlaceError("unsealed", PLACE_DETAILS["unsealed"][0].format(uuid=uuid))
    try:
        occupants = _occupancy(root, uuid)
    except OSError as exc:
        detail = PLACE_DETAILS["bundle-unreadable"][0].format(
            path=display_project_path(
                (root / STAGING_DIR / uuid).absolute(), project_root=root.absolute()
            )
        )
        raise PlaceError("bundle-unreadable", detail) from exc
    for path, kind in occupants:
        if kind == "unsafe":
            detail = PLACE_DETAILS["bundle-unreadable"][0].format(
                path=display_project_path(path.absolute(), project_root=root.absolute())
            )
            raise PlaceError("bundle-unreadable", detail)
    homes = [path for path, kind in occupants if kind == "dir"]
    if len(homes) > 1:
        raise PlaceError("multi-root", PLACE_DETAILS["multi-root"][0].format(uuid=uuid))
    if not homes:
        raise PlaceError("absent", PLACE_DETAILS["absent"][0].format(uuid=uuid))
    home = homes[0]
    digest = str(latest[uuid]["bundle_digest"])
    records = verdict_records(root, uuid)
    recorded = records.get(digest)
    if recorded is None and records:
        raise PlaceError(
            "verdict-digest-mismatch", PLACE_DETAILS["verdict-digest-mismatch"][0].format(uuid=uuid)
        )
    if recorded is None:
        raise PlaceError("verdict-missing", PLACE_DETAILS["verdict-missing"][0].format(uuid=uuid))
    if "outcome" not in recorded:
        raise PlaceError("verdict-legacy", PLACE_DETAILS["verdict-legacy"][0].format(uuid=uuid))
    if recorded["outcome"] == "retained":
        raise PlaceError("retained", PLACE_DETAILS["retained"][0])
    lane = resolve_task_lane(root, uuid)
    placed = home.parent.name in {directory.name for directory in LANE_DIRS}
    if _placement_digest(root, home) != digest:
        raise PlaceError(
            "staged-digest-mismatch",
            PLACE_DETAILS["staged-digest-mismatch"][0].format(uuid=uuid, lane=home.parent.name),
        )
    if placed:
        return "placed", home
    lane_root = root / lane
    try:
        lane_is_directory = stat.S_ISDIR(os.lstat(lane_root).st_mode)
    except FileNotFoundError:
        lane_is_directory = False
    except OSError as exc:
        raise PlaceError(
            "lane-root-missing", PLACE_DETAILS["lane-root-missing"][0].format(lane=lane)
        ) from exc
    if not lane_is_directory:
        raise PlaceError(
            "lane-root-missing", PLACE_DETAILS["lane-root-missing"][0].format(lane=lane)
        )
    destination = lane_root / uuid
    try:
        os.rename(home, destination)  # noqa: PTH104 - placement is one rename, never a copy.
    except OSError as exc:
        code = "cross-device" if exc.errno == errno.EXDEV else "rename-failed"
        raise PlaceError(code, PLACE_DETAILS[code][0].format(uuid=uuid, lane=lane)) from exc
    if _placement_digest(root, destination) != digest:
        raise PlaceError(
            "post-rename-digest-drift",
            PLACE_DETAILS["post-rename-digest-drift"][0].format(uuid=uuid, lane=lane),
        )
    return "placed", destination


def _tolerant_latest(records: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    """Latest record per uuid without raising on a conflict; verify reports that separately."""
    try:
        return _latest_per_stream(records)
    except PipelineError:
        latest: dict[str, dict[str, object]] = {}
        for record in records:
            latest[str(record["uuid"])] = record
        return latest


def _git_show(root: Path, ref: str, relative: Path) -> bytes | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "show", f"{ref}:{relative.as_posix()}"],
            capture_output=True,
            check=False,
            timeout=10.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def _accepted_prefix_findings(root: Path, accepted: str) -> list[Finding]:
    """Every stream at the accepted ref is a byte prefix of the same stream now."""
    out: list[Finding] = []
    probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{accepted}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        message = f"accepted ref {accepted!r} cannot be resolved; stream history is unverifiable"
        return [_finding(root / QUEUE_DIR, "PIPELINE_STREAM_REWRITTEN", message)]
    listing = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "ls-tree",
            "--name-only",
            "-r",
            accepted,
            "--",
            QUEUE_DIR.as_posix(),
            QUEUE_PATH.as_posix(),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    for relative in sorted(line for line in listing.stdout.splitlines() if line.endswith(".jsonl")):
        before = _git_show(root, accepted, Path(relative))
        if before is None:
            continue
        try:
            now_bytes = (root / relative).read_bytes()
        except OSError:
            now_bytes = b""
        if not now_bytes.startswith(before):
            message = f"{relative} at {accepted} is not a prefix of the stream on disk"
            out.append(_finding(root / relative, "PIPELINE_STREAM_REWRITTEN", message))
    return out


GENERATED_BANNER = "GENERATED SECTION. DO NOT HAND-EDIT."
LANE_README_SECTIONS = ("## Promoted set", "## Standing", "## Screening roots")


@dataclass(frozen=True, slots=True)
class Resident:
    """One bundle resident under a lane root with the facts reconcile orders it by."""

    uuid: str
    lane_root: str
    task_lane: str | None
    sealed_at: str | None
    stream: str | None
    seq: int
    digest: str | None
    outcome: str | None

    @property
    def order(self) -> tuple[int, str, str, int, str]:
        fixed = 0 if self.sealed_at is None else 1
        starter = 0 if self.task_lane == "starter" else 1
        return (fixed * 2 + starter, self.sealed_at or "", self.stream or "", self.seq, self.uuid)


@dataclass(frozen=True, slots=True)
class Reconciliation:
    moves: tuple[tuple[str, str, str], ...]
    readmes: tuple[str, ...]
    findings: tuple[Finding, ...]


def _declared_submodule(root: Path, name: str) -> bool:
    """True when ``.gitmodules`` declares a submodule whose path is ``name``."""

    try:
        text = (root / ".gitmodules").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key.strip().lower() == "path" and value.strip().strip("/") == name:
            return True
    return False


def _residents(root: Path) -> list[Resident]:
    _, records = walk_queue(root)
    latest = _tolerant_latest(records)
    lanes = registered_lanes(root)
    out: list[Resident] = []
    for lane_root in LANE_DIRS:
        directory = root / lane_root
        if not directory.is_dir():
            continue
        for uuid in sorted(resident_uuids(directory)):
            record = latest.get(uuid)
            digest = str(record["bundle_digest"]) if record is not None else None
            verdict_record = verdict_records(root, uuid).get(digest) if digest is not None else None
            out.append(
                Resident(
                    uuid=uuid,
                    lane_root=lane_root.name,
                    task_lane=lanes.get(uuid),
                    sealed_at=str(record["sealed_at"]) if record is not None else None,
                    stream=str(record["stream"]) if record is not None else None,
                    seq=int(str(record["seq"])) if record is not None else 0,
                    digest=digest,
                    outcome=verdict_record.get("outcome") if verdict_record else None,
                )
            )
    return out


def _target_roots(residents: list[Resident], standing: dict[str, str]) -> dict[str, str]:
    """The lane root every resident belongs under once the ceilings are applied.

    Residents with no seal record are fixed where they stand and counted first; a
    registered ``delivery`` lane stays under ``delivery/``. A ``starter`` is an anchor:
    once ENGRAM publishes its anchor-standing row as graduated it moves to ``delivery/``
    because its calibration purpose is served, and until then it takes a place inside
    the sample ceiling ahead of every ordinary bundle. Every other sealed resident
    competes for the remaining places in seal order, and the overflow routes to
    ``delivery/``, so ``samples/`` never holds more than the ceiling.
    """
    targets: dict[str, str] = {}
    candidates: list[Resident] = []
    fixed_samples = 0
    for resident in residents:
        if resident.sealed_at is None or resident.task_lane == "delivery":
            targets[resident.uuid] = resident.lane_root
            if resident.lane_root == "samples":
                fixed_samples += 1
        elif (
            resident.task_lane == "starter"
            and standing.get(resident.uuid) in GRADUATED_ANCHOR_STATES
        ):
            targets[resident.uuid] = "delivery"
        else:
            candidates.append(resident)
    capacity = max(LANE_CEILINGS["samples"] - fixed_samples, 0)
    for index, resident in enumerate(sorted(candidates, key=lambda item: item.order)):
        targets[resident.uuid] = "samples" if index < capacity else "delivery"
    return targets


def render_lane_readme(lane_root: str, residents: list[Resident]) -> str:
    """The deterministic README for one lane root, a pure function of its residents."""
    rows = sorted(residents, key=lambda item: item.order)
    lines = [GENERATED_BANNER, "", f"# {lane_root}", "", LANE_README_SECTIONS[0], ""]
    lines.append("| uuid | task_lane | sealed_at | stream |")
    lines.append("| --- | --- | --- | --- |")
    for item in rows:
        lines.append(
            f"| {item.uuid} | {item.task_lane or 'unregistered'} | "
            f"{item.sealed_at or 'unsealed'} | {item.stream or 'none'} |"
        )
    lines += ["", LANE_README_SECTIONS[1], "", "| uuid | verdict |", "| --- | --- |"]
    for item in rows:
        lines.append(f"| {item.uuid} | {item.outcome or 'none'} |")
    lines += ["", LANE_README_SECTIONS[2], "", "No screening root is recorded by reconcile.", ""]
    return "\n".join(lines)


def reconcile(root: Path, *, check: bool = False) -> Reconciliation:
    """Route the overflow past the sample ceiling into delivery and render both READMEs.

    A pure function of the tree: the same call in ``check`` mode reports every move and
    README the tree still needs as ``PIPELINE_RECONCILE_DRIFT`` without writing, which is
    what the pre-push hook and the merge check run.
    """
    residents = _residents(root)
    findings: list[Finding] = []
    try:
        standing = anchor_standing(root)
    except AnchorStandingError as exc:
        # An unreadable standing file graduates nothing; the drift is named, never guessed.
        findings.append(_finding(root / ANCHOR_STANDING_PATH, "PIPELINE_RECONCILE_DRIFT", str(exc)))
        standing = {}
    targets = _target_roots(residents, standing)
    moves: list[tuple[str, str, str]] = []
    for resident in sorted(residents, key=lambda item: item.order):
        target = targets[resident.uuid]
        if target == resident.lane_root:
            continue
        source = root / resident.lane_root / resident.uuid
        destination = root / target / resident.uuid
        if destination.exists():
            findings.append(
                _finding(
                    destination,
                    "PIPELINE_RECONCILE_DRIFT",
                    f"{resident.uuid} must move to {target}/ but that path is occupied",
                )
            )
            continue
        if check:
            findings.append(
                _finding(
                    source,
                    "PIPELINE_RECONCILE_DRIFT",
                    f"{resident.uuid} belongs under {target}/ by "
                    + ("anchor standing" if resident.task_lane == "starter" else "seal order"),
                )
            )
            continue
        try:
            os.rename(source, destination)  # noqa: PTH104 - one rename, never a copy.
        except OSError as exc:
            findings.append(
                _finding(source, "PIPELINE_RECONCILE_DRIFT", f"cannot move {resident.uuid}: {exc}")
            )
            continue
        moves.append((resident.uuid, resident.lane_root, target))
    if not check:
        residents = _residents(root)
    delivered = sum(1 for item in residents if targets.get(item.uuid) == "delivery")
    if delivered > LANE_CEILINGS["delivery"]:
        message = (
            f"delivery/ would hold {delivered}, above its ceiling of {LANE_CEILINGS['delivery']}"
        )
        findings.append(_finding(root / "delivery", "PIPELINE_LANE_FULL", message))
    readmes: list[str] = []
    for lane_root in LANE_DIRS:
        directory = root / lane_root
        if not directory.is_dir():
            continue
        # A lane that is a submodule and is not checked out is an existing but
        # empty directory: its content is absent, not drifted. Continuous
        # integration checks the parent out with submodules disabled, and reading
        # that absence as drift would refuse every run. An empty lane that is not
        # a declared submodule still owes a rendered README and is left alone.
        if not any(directory.iterdir()) and _declared_submodule(root, lane_root.name):
            continue
        members = [
            item
            for item in residents
            if (targets.get(item.uuid) if check else item.lane_root) == lane_root.name
        ]
        rendered = render_lane_readme(lane_root.name, members)
        readme = directory / "README.md"
        try:
            current = readme.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            current = None
        if current == rendered:
            continue
        if check:
            findings.append(
                _finding(
                    readme, "PIPELINE_RECONCILE_DRIFT", f"{lane_root}/README.md is not rendered"
                )
            )
            continue
        readme.write_text(rendered, encoding="utf-8")
        readmes.append(str(lane_root / "README.md"))
    if check:
        findings += check_root_reports(str(root))
    else:
        readmes += render_root_reports(root)
    return Reconciliation(tuple(moves), tuple(readmes), tuple(findings))


def check_reconcile(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """Parent-check entry point: the tree must equal its own reconciliation."""
    root_path = Path(root)
    if not any((root_path / lane).is_dir() for lane in LANE_DIRS):
        return check_root_reports(root)
    return list(reconcile(root_path, check=True).findings)


def verify(
    root: Path, evaluation_time: datetime | None = None, accepted: str | None = None
) -> list[Finding]:
    """Run every pipeline refusal and return the findings."""
    out: list[Finding] = []
    try:
        max_unaudited, ttl_hours = load_config(root)
    except PipelineError as exc:
        return [_finding(root / CONFIG_PATH, "PIPELINE_CONFIG_INVALID", str(exc))]
    chain_findings, records = walk_queue(root)
    out += chain_findings
    out += _stream_conflicts(root, records)
    if accepted is not None:
        out += _accepted_prefix_findings(root, accepted)
    latest = _tolerant_latest(records)
    for uuid, record in latest.items():
        occupants = _occupancy(root, uuid)
        unsafe = [path for path, kind in occupants if kind == "unsafe"]
        if unsafe:
            for path in unsafe:
                out.append(_finding(path, "PIPELINE_SEALED_MUTATED", f"unsafe object at {path}"))
            continue
        homes = [path for path, kind in occupants if kind == "dir"]
        if len(homes) > 1:
            out.append(
                _finding(homes[0], "PIPELINE_SEALED_MUTATED", "resident under more than one root")
            )
            continue
        if not occupants:
            recorded = _read_verdict(root, uuid, str(record["bundle_digest"]))
            if recorded is not None and recorded.get("outcome") == "retained":
                continue
            out.append(_finding(root / STAGING_DIR / uuid, "PIPELINE_SEALED_MUTATED", "missing"))
            continue
        bundle_root = homes[0]
        if bundle_root.parent.name in {lane.name for lane in LANE_DIRS}:
            recorded = _read_verdict(root, uuid, str(record["bundle_digest"]))
            if recorded is None or recorded.get("outcome") == "retained":
                out.append(
                    _finding(
                        bundle_root,
                        "PIPELINE_PLACED_UNCLEAN",
                        f"placed bundle {uuid} lacks a clean verdict at its sealed digest",
                    )
                )
        recorded = _read_verdict(root, uuid, str(record["bundle_digest"]))
        if (
            bundle_root.parent == root / STAGING_DIR
            and recorded is not None
            and recorded.get("outcome") == "retained"
            and list(bundle_root.iterdir()) == [bundle_root / "trajectories"]
            and stat.S_ISDIR((bundle_root / "trajectories").lstat().st_mode)
        ):
            continue
        try:
            current = bundle_digest(bundle_root)
        except PipelineError as exc:
            out.append(_finding(bundle_root, "PIPELINE_SEALED_MUTATED", str(exc)))
            continue
        if current != record["bundle_digest"]:
            message = f"sealed digest {record['bundle_digest']} no longer matches the bundle bytes"
            if bundle_root.parent == root / STAGING_DIR and recorded is None:
                message = f"bundle {uuid} was reworked before its verdict; {message}"
            out.append(_finding(bundle_root, "PIPELINE_SEALED_MUTATED", message))
    verdicts_dir = root / VERDICTS_DIR
    if verdicts_dir.is_dir():
        for verdict_path in sorted(verdicts_dir.glob("*.json")):
            uuid = verdict_path.stem
            if uuid not in latest:
                message = f"verdict exists for {uuid}, which was never sealed"
                out.append(_finding(verdict_path, "PIPELINE_UNSEALED_AUDIT", message))
    out += _unowned_verdict_findings(root, latest)
    if not chain_findings:
        depth = len(_pending_from(root, latest))
        if depth > max_unaudited:
            message = f"{depth} sealed bundles await audit, above the bound of {max_unaudited}"
            out.append(_finding(root / QUEUE_PATH, "PIPELINE_BACKPRESSURE", message))
        out += _claim_findings(root, latest, _now(evaluation_time), ttl_hours)
    return out


def check_pipeline(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """Parent-check entry point with the ParentCheck signature."""
    root_path = Path(root)
    if not (root_path / QUEUE_PATH).is_file() and not (root_path / CLAIMS_DIR).is_dir():
        return []
    return verify(root_path, _evaluation_time)


CHECKS: list[tuple[str, Callable[[str, datetime | None], list[Finding]]]] = [
    ("check_pipeline", check_pipeline),
    ("check_reconcile", check_reconcile),
]


def status(root: Path, evaluation_time: datetime | None = None) -> dict[str, object]:
    findings = verify(root, evaluation_time)
    _, records = walk_queue(root)
    latest = _tolerant_latest(records)
    pending_uuids = _pending_from(root, latest)
    claimed = sorted(
        uuid
        for uuid in latest
        if claim_owner(root, uuid, str(latest[uuid]["bundle_digest"])) is not None
        and uuid in pending_uuids
    )
    buckets: dict[str, list[str]] = {"staged": [], "placeable": [], "retained": [], "placed": []}
    for uuid in sorted(latest):
        recorded = _read_verdict(root, uuid, str(latest[uuid]["bundle_digest"]))
        matching = recorded is not None
        if matching and recorded is not None and recorded.get("outcome") == "retained":
            buckets["retained"].append(uuid)
        occupants = _occupancy(root, uuid)
        if len(occupants) != 1 or occupants[0][1] != "dir":
            continue
        home = occupants[0][0]
        if home.parent == root / STAGING_DIR:
            buckets["staged"].append(uuid)
            if matching and recorded is not None and recorded.get("outcome") == "clean":
                buckets["placeable"].append(uuid)
        else:
            buckets["placed"].append(uuid)
    return {
        "sealed": len(latest),
        "pending": pending_uuids,
        "claimed": claimed,
        "findings": [f.code for f in findings],
        **buckets,
    }


REPORT_REFUSAL_EXIT = 3


def _render_reports(root: Path, arguments: argparse.Namespace, project_root: Path) -> int:
    """Render or check the root reports alone: the entry point a git hook runs."""
    written: list[str] = []
    findings: list[Finding] = []
    if is_parent(root):
        if not arguments.check:
            written = render_root_reports(root)
        elif arguments.staged:
            staged = staged_reports(root)
            written, findings = list(staged.written), list(staged.findings)
        else:
            findings = check_root_reports(str(root))
    public = [
        Finding(
            item.code,
            item.severity,
            display_project_path(item.path, project_root=project_root),
            item.line,
            redact_project_root(item.message, project_root=project_root),
        )
        for item in findings
    ]
    if arguments.json and arguments.check:
        print(serialize_findings(public))
    elif arguments.json:
        print(json.dumps({"reports": written}, indent=2, sort_keys=True))
    else:
        for name in written:
            verb = "wrote" if arguments.check else "rendered"
            suffix = "; review the rendered bytes and git add them" if arguments.check else ""
            print(f"{verb} {name}{suffix}")
        for item in public:
            print(f"{item.code}: {render_finding(item)}")
    return REPORT_REFUSAL_EXIT if _refuses(public) else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 tools/pipeline.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    seal_parser = sub.add_parser("seal", help="seal staging/<uuid> into the queue")
    seal_parser.add_argument("root")
    seal_parser.add_argument("uuid")
    seal_parser.add_argument("--run-id", required=True)
    pending_parser = sub.add_parser("pending", help="list sealed bundles awaiting audit")
    pending_parser.add_argument("root")
    claim_parser = sub.add_parser("claim", help="claim a sealed bundle for one consumer")
    claim_parser.add_argument("root")
    claim_parser.add_argument("uuid")
    claim_parser.add_argument("--run-id", required=True)
    verdict_parser = sub.add_parser("verdict", help="record a claim-bound sealed bundle outcome")
    verdict_parser.add_argument("root")
    verdict_parser.add_argument("uuid")
    verdict_parser.add_argument("--outcome", choices=sorted(VERDICT_OUTCOMES), required=True)
    verdict_parser.add_argument("--run-id", required=True)
    route_parser = sub.add_parser(
        "route", help="bind a staged bundle's task lane by the residency rule and register it"
    )
    route_parser.add_argument("root")
    route_parser.add_argument("uuid")
    route_parser.add_argument("--lane", choices=["sample", "starter"], required=True)
    route_parser.add_argument("--slot", type=int, required=True)
    route_parser.add_argument("--batch", required=True)
    route_parser.add_argument("--run-id", required=True)
    place_parser = sub.add_parser(
        "place", help="place clean staged bytes into their registered lane"
    )
    place_parser.add_argument("root")
    place_parser.add_argument("uuid")
    reconcile_parser = sub.add_parser(
        "reconcile", help="route the overflow past the sample ceiling and render lane READMEs"
    )
    reconcile_parser.add_argument("root")
    reconcile_parser.add_argument("--check", action="store_true")
    reconcile_parser.add_argument("--json", action="store_true")
    render_parser = sub.add_parser(
        "render-reports", help="render the root reports from the tree without moving a bundle"
    )
    render_parser.add_argument("root")
    render_parser.add_argument("--check", action="store_true")
    render_parser.add_argument("--staged", action="store_true")
    render_parser.add_argument("--json", action="store_true")
    release_parser = sub.add_parser("release", help="drop one consumer's claim")
    release_parser.add_argument("root")
    release_parser.add_argument("uuid")
    release_parser.add_argument("--run-id", required=True)
    verify_parser = sub.add_parser("verify", help="verify the queue and refuse on any defect")
    verify_parser.add_argument("root")
    verify_parser.add_argument("--json", action="store_true")
    verify_parser.add_argument("--accepted", help="git ref whose streams must be prefixes")
    status_parser = sub.add_parser("status", help="print queue status as JSON")
    status_parser.add_argument("root")
    return parser


def main(argv: list[str]) -> int:
    arguments = _parser().parse_args(argv[1:])
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            str(arguments.root),
            project_root=project_root,
            description="parent root",
            must_exist=True,
        )
        if arguments.command == "seal":
            print(seal(root, arguments.uuid, arguments.run_id))
            return 0
        if arguments.command == "pending":
            for uuid in pending(root):
                print(uuid)
            return 0
        if arguments.command == "claim":
            print(claim(root, arguments.uuid, arguments.run_id))
            return 0
        if arguments.command == "verdict":
            path = verdict(root, arguments.uuid, arguments.outcome, arguments.run_id)
            print(display_project_path(path, project_root=project_root))
            return 0
        if arguments.command == "route":
            claim_row = LaneClaim(
                uuid=str(arguments.uuid),
                task_lane=str(arguments.lane),
                slot=int(arguments.slot),
                batch=str(arguments.batch),
                run_id=str(arguments.run_id),
            )
            print(route(root, claim_row))
            return 0
        if arguments.command == "place":
            outcome, path = place(root, arguments.uuid)
            print(f"{outcome} {display_project_path(path, project_root=project_root)}")
            return 0
        if arguments.command == "render-reports":
            return _render_reports(root, arguments, project_root)
        if arguments.command == "reconcile":
            done = reconcile(root, check=arguments.check)
            public = [
                Finding(
                    item.code,
                    item.severity,
                    display_project_path(item.path, project_root=project_root),
                    item.line,
                    redact_project_root(item.message, project_root=project_root),
                )
                for item in done.findings
            ]
            if arguments.json:
                print(
                    json.dumps(
                        {
                            "moves": [list(move) for move in done.moves],
                            "readmes": list(done.readmes),
                            "findings": json.loads(serialize_findings(public)),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
            else:
                for uuid, origin, target in done.moves:
                    print(f"moved {uuid} {origin}/ -> {target}/")
                for readme in done.readmes:
                    print(f"rendered {readme}")
                for item in public:
                    print(render_finding(item))
            return 1 if _refuses(done.findings) else 0
        if arguments.command == "release":
            release_claim(root, arguments.uuid, arguments.run_id)
            return 0
        if arguments.command == "verify":
            findings = verify(root, accepted=arguments.accepted)
            findings = [
                Finding(
                    item.code,
                    item.severity,
                    display_project_path(item.path, project_root=project_root),
                    item.line,
                    redact_project_root(item.message, project_root=project_root),
                )
                for item in findings
            ]
            if arguments.json:
                print(serialize_findings(findings))
            else:
                for item in findings:
                    print(render_finding(item))
            return 1 if findings else 0
        if arguments.command == "status":
            print(json.dumps(status(root), indent=2, sort_keys=True))
            return 0
    except (PlaceError, RouteError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except (PipelineError, ProjectPathError) as exc:
        if arguments.command == "place" and isinstance(exc, PipelineError):
            refusal = PlaceError("queue-broken", PLACE_DETAILS["queue-broken"][0])
            print(f"refused: {refusal}", file=sys.stderr)
            return 1
        captured_root = locals().get("project_root")
        message = (
            str(exc)
            if not isinstance(captured_root, Path)
            else redact_project_root(str(exc), project_root=captured_root)
        )
        print(f"refused: {message}", file=sys.stderr)
        return 1 if isinstance(exc, PipelineError) else 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
