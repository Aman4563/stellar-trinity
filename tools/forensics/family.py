"""G-FID orchestration over an immutable trajectory snapshot; no parent registration."""

import os
import re
import stat
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Final

from .bundle import MAX_BUNDLE_FILES, MAX_TRACE_BYTES, RAW_AGENT_PATHS, TraceBundle
from .capture import capture
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import SignalClass as S
from .core import SignalFinding
from .family_config import FidelityConfig, config_standing
from .family_models import (
    GROUP_SIZE,
    FidelityLedger,
    FidelityRoster,
    FidelityRow,
    PopulationStanding,
    ScorerReceipt,
)
from .filesystem import directory_fd, read_regular
from .guard import refused
from .native import available_sources
from .reading import TraceReadError, json_file, log_records, text
from .registry import analyze_trace

MAX_DISCOVERY_ENTRIES: Final = 8192
MAX_DISCOVERY_DEPTH: Final = 16
MAX_ROLLOUTS: Final = 1024
MAX_FAMILY_BYTES: Final = 64 * 1024 * 1024


def _rollout_roots(root: Path, *, project_root: Path | None = None) -> tuple[Path, ...]:
    """Find artifact-bearing runs without counting their agent/ subtree twice."""
    anchors = {
        "agent.jsonl",
        "trajectory.json",
        "events.jsonl",
        "usage.json",
        "result.json",
        "run-metadata.json",
        "metrics.json",
        "submission.json",
    }
    trusted = project_root if project_root is not None else Path(root.absolute().anchor)
    paths: set[Path] = set()
    pending = [(root, 0)]
    entries = 0
    total_bytes = 0
    while pending:
        directory, depth = pending.pop()
        with directory_fd(directory, project_root=trusted) as parent, os.scandir(parent) as stream:
            populated = False
            for entry in stream:
                populated = True
                entries += 1
                if entries > MAX_DISCOVERY_ENTRIES or depth >= MAX_DISCOVERY_DEPTH:
                    raise TraceReadError
                info = entry.stat(follow_symlinks=False)
                path = directory / entry.name
                if stat.S_ISLNK(info.st_mode):
                    raise TraceReadError
                if stat.S_ISDIR(info.st_mode):
                    pending.append((path, depth + 1))
                elif stat.S_ISREG(info.st_mode):
                    total_bytes += info.st_size
                    if info.st_size > MAX_TRACE_BYTES or total_bytes > MAX_FAMILY_BYTES:
                        raise TraceReadError
                    if path.name in anchors:
                        paths.add(
                            path.parent.parent if path.parent.name == "agent" else path.parent
                        )
                else:
                    raise TraceReadError
            if not populated and directory != root:
                paths.add(directory)
        if len(paths) > MAX_ROLLOUTS:
            raise TraceReadError
    return tuple(sorted(paths))


def _files(directory: Path, *, project_root: Path | None = None) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    trusted = project_root if project_root is not None else Path(directory.absolute().anchor)
    pending = [(directory, 0)]
    entries = 0
    total = 0
    while pending:
        current, depth = pending.pop()
        with directory_fd(current, project_root=trusted) as parent, os.scandir(parent) as stream:
            for entry in stream:
                entries += 1
                if entries > MAX_DISCOVERY_ENTRIES or depth >= MAX_DISCOVERY_DEPTH:
                    raise TraceReadError
                path = current / entry.name
                if entry.is_dir(follow_symlinks=False):
                    pending.append((path, depth + 1))
                else:
                    if len(files) >= MAX_BUNDLE_FILES:
                        raise TraceReadError
                    raw = read_regular(
                        path,
                        project_root=trusted,
                        max_bytes=min(MAX_TRACE_BYTES, MAX_FAMILY_BYTES - total),
                    )
                    total += len(raw)
                    files[path.relative_to(directory).as_posix()] = raw
    return files


def _handoff(bundle: TraceBundle, receipts: tuple[ScorerReceipt, ...]) -> SignalFinding:
    pointer = "./submission.json:1"
    unknown = SignalFinding(
        S.HANDOFF_FAILURE, O.INSUFFICIENT_EVIDENCE, R.FIDELITY_SELF_REPORTED_ONLY, pointer
    )
    if len(receipts) != 1:
        return unknown
    try:
        submitted = json_file(bundle, "submission.json")
        digest, session = text(submitted, "sha256"), text(submitted, "session_id")
        streams = tuple(path for path in (*RAW_AGENT_PATHS, "events.jsonl") if path in bundle.files)
        if len(streams) != 1:
            return unknown
        stream = capture(log_records(bundle.files[streams[0]]), streams[0])
        produced = text(stream.terminal, "submission_sha256")
        if not stream.complete or produced is None or not re.fullmatch(r"[0-9a-f]{64}", produced):
            return unknown
    except TraceReadError:
        return unknown
    receipt = receipts[0]
    if not session or digest is None or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return unknown
    if not receipt.session_id or not re.fullmatch(r"[0-9a-f]{64}", receipt.sha256):
        return unknown
    matched = (
        digest == receipt.sha256 == produced and session == receipt.session_id == stream.session_id
    )
    return SignalFinding(
        S.HANDOFF_FAILURE, O.COVERED_CLEAN if matched else O.VIOLATION, None, pointer
    )


def run_fidelity_family(
    trajectory_root: Path,
    declared_family: str,
    harness_config: FidelityConfig,
    roster: FidelityRoster,
    *,
    project_root: Path | None = None,
) -> FidelityLedger:
    """Run all four instruments. Four arguments preserve the specified public API.

    The caller authenticates roster/config/scorer receipts before invocation and
    supplies an immutable snapshot. This runner never synthesizes attestations.
    Native adapters enforce strongest_supported_outcome, retaining positive evidence.
    """
    config = config_standing(harness_config)
    try:
        roots = _rollout_roots(trajectory_root, project_root=project_root)
    except OSError as error:
        raise TraceReadError from error
    identities = tuple(path.relative_to(trajectory_root).as_posix() for path in roots)
    expected = tuple(identity for group in roster.groups for identity in group)
    valid = (
        roster.group_count > 0
        and len(roster.groups) == roster.group_count
        and all(len(group) == GROUP_SIZE for group in roster.groups)
        and len(set(expected)) == len(expected)
        and all(expected)
        and not trajectory_root.is_symlink()
    )
    population = PopulationStanding(
        tuple(sorted(set(identities) - set(expected))),
        tuple(sorted(set(expected) - set(identities))),
        valid,
    )
    rows: list[FidelityRow] = []
    receipts_by_id: dict[str, list[ScorerReceipt]] = defaultdict(list)
    statuses_by_id: dict[str, list[str]] = defaultdict(list)
    for receipt in roster.scorer_receipts:
        receipts_by_id[receipt.rollout_id].append(receipt)
    for identity, status in roster.operator_statuses:
        statuses_by_id[identity].append(status)
    total_bytes = 0
    for directory, identity in zip(roots, identities, strict=True):
        bundle = TraceBundle(
            declared_family,
            config.harness_version,
            authorization=config.authorization,
            rollout_id=identity,
        )
        try:
            if directory.is_symlink():
                raise TraceReadError
            bundle = replace(bundle, files=_files(directory, project_root=project_root))
            total_bytes += sum(len(raw) for raw in bundle.files.values())
            if total_bytes > MAX_FAMILY_BYTES:
                raise TraceReadError
            sources = available_sources(bundle)
            # Prefer the most specific wrapper only when actual native bytes accompany it.
            if "cybergym_usage" in sources:
                sources -= {"claude_code_jsonl"}
            if "openhands_native_metrics" in sources and "openhands_events" in sources:
                sources -= {"openhands_events"}
            bundle = replace(bundle, accompaniment=sources)
            trace = analyze_trace(bundle)
        except (OSError, TraceReadError):
            trace = refused(bundle, R.FIDELITY_TRACE_UNREADABLE)
        handoff = _handoff(bundle, tuple(receipts_by_id[identity]))
        # Native handoff violations outrank a missing external receipt; incomplete
        # native identities must not become clean merely because a receipt exists.
        native = tuple(f for f in trace.findings if f.signal is S.HANDOFF_FAILURE)
        if any(f.outcome is O.VIOLATION for f in native):
            handoff = next(f for f in native if f.outcome is O.VIOLATION)
        statuses = statuses_by_id[identity]
        operator_status = (
            statuses[0] if len(statuses) == 1 else ("conflicting" if statuses else None)
        )
        rows.append(FidelityRow(trace, handoff, config, population, operator_status))
    return FidelityLedger(tuple(rows), config, population, roster.group_count, roster.groups)
