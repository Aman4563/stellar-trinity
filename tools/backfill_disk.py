"""Bounded filesystem ingestion for the four historical layout families."""

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from tools import forensics
from tools.attest import canonical, dsse
from tools.attest.policies import execution_fidelity
from tools.backfill_models import BackfillError, Failure
from tools.forensics.bundle import MAX_BUNDLE_FILES, RAW_AGENT_PATHS
from tools.forensics.filesystem import directory_fd, read_regular
from tools.forensics.reading import TraceReadError, child, document, log_records, text

MAX_ENTRIES: Final = 8192
MAX_BUNDLE_BYTES: Final = 64 * 1024 * 1024
MAX_DEPTH: Final = 8
RUN_NAME: Final = re.compile(r"run_([1-9][0-9]*|0)\Z")


def children(path: Path, *, project_root: Path | None = None) -> tuple[Path, ...]:
    if path.is_symlink() or not path.is_dir():
        raise BackfillError(Failure.UNSAFE_PATH)
    entries: list[Path] = []
    trusted = project_root if project_root is not None else Path(path.absolute().anchor)
    try:
        with directory_fd(path, project_root=trusted) as parent, os.scandir(parent) as stream:
            for entry in stream:
                if len(entries) >= MAX_ENTRIES:
                    raise BackfillError(Failure.INPUT_TOO_LARGE)
                if entry.is_symlink():
                    raise BackfillError(Failure.UNSAFE_PATH)
                entries.append(path / entry.name)
    except (OSError, TraceReadError) as error:
        raise BackfillError(Failure.UNSAFE_PATH) from error
    return tuple(sorted(entries))


class Reader:
    """A per-bundle mutable read budget, shared across every rollout and history file."""

    __slots__ = ("byte_count", "entry_count", "project_root")

    def __init__(self, *, project_root: Path | None = None) -> None:
        self.byte_count = 0
        self.entry_count = 0
        self.project_root = project_root

    def read(self, path: Path) -> bytes:
        self.entry_count += 1
        if self.entry_count > MAX_ENTRIES:
            raise BackfillError(Failure.INPUT_TOO_LARGE)
        trusted = (
            self.project_root if self.project_root is not None else Path(path.absolute().anchor)
        )
        try:
            raw = read_regular(
                path,
                project_root=trusted,
                max_bytes=min(forensics.MAX_TRACE_BYTES, MAX_BUNDLE_BYTES - self.byte_count),
            )
        except TraceReadError as error:
            raise BackfillError(Failure.INPUT_TOO_LARGE) from error
        except OSError as error:
            raise BackfillError(Failure.UNSAFE_PATH) from error
        self.byte_count += len(raw)
        if (
            len(raw) > forensics.MAX_TRACE_BYTES
            or raw.count(b"\n") > forensics.MAX_TRACE_LINES
            or self.byte_count > MAX_BUNDLE_BYTES
        ):
            raise BackfillError(Failure.INPUT_TOO_LARGE)
        return raw

    def files(self, root: Path) -> Mapping[str, bytes]:
        files: dict[str, bytes] = {}
        pending = [(root, 0)]
        while pending:
            directory, depth = pending.pop()
            for path in children(directory, project_root=self.project_root):
                self.entry_count += 1
                if self.entry_count > MAX_ENTRIES or depth >= MAX_DEPTH:
                    raise BackfillError(Failure.INPUT_TOO_LARGE)
                if path.is_dir():
                    pending.append((path, depth + 1))
                    continue
                if len(files) >= MAX_BUNDLE_FILES:
                    raise BackfillError(Failure.INPUT_TOO_LARGE)
                files[path.relative_to(root).as_posix()] = self.read(path)
        return files


def _version(files: Mapping[str, bytes], native: bool) -> str:
    values: set[str] = set()
    paths = ("config.json", "usage.json", "run-metadata.json")
    for path in paths:
        if path in files:
            data = document(files[path])
            value = text(data, "harness_version") or text(child(data, "agent"), "version")
            if value:
                values.add(value)
    if native:
        for path in (*RAW_AGENT_PATHS, "events.jsonl"):
            if path in files:
                records = log_records(files[path])
                if records:
                    value = text(records[0], "version") or text(records[0], "harness_version")
                    if value:
                        values.add(value)
    elif "agent/trajectory.json" in files:
        data = document(files["agent/trajectory.json"])
        value = text(data, "schema_version")
        if value:
            values.add(value.removeprefix("ATIF-v"))
    return next(iter(values)) if len(values) == 1 else "unknown"


def trace_bundle(run: Path, reader: Reader) -> forensics.TraceBundle:
    files = dict(reader.files(run))
    raw = any(path in files for path in RAW_AGENT_PATHS)
    harbor = {"config.json", "result.json"} <= files.keys()
    metrics = {"run-metadata.json", "metrics.json"} <= files.keys()
    trajectory = tuple(path for path in files if path.startswith("trajectory/"))
    usage = "usage.json" in files
    if metrics:
        family = "openhands_native_metrics"
    elif harbor:
        family = "claude_code_jsonl" if raw else "atif_normalized"
        if "events.jsonl" in files:
            family = "openhands_events"
    elif usage and trajectory:
        family = "claude_code_jsonl" if raw else "atif_normalized"
        if "agent/trajectory.json" not in files:
            parts = [files[path] for path in trajectory if path.endswith(".json")]
            if parts:
                files["agent/trajectory.json"] = b'{"steps":[' + b",".join(parts) + b"]}"
    elif usage:
        family = "cybergym_usage"
    else:
        raise BackfillError(Failure.FAMILY_UNRECOGNIZED)
    if family not in forensics.FIDELITY_FAMILIES:
        raise BackfillError(Failure.FAMILY_UNRECOGNIZED)
    version = _version(files, family != "atif_normalized")
    return forensics.TraceBundle(
        family=family,
        harness_version=version,
        files=files,
        rollout_id=f"{run.parent.name}/{run.name}",
    )


def history(root: Path, reader: Reader) -> str | None:
    """Read optional execution.json through the policy's non-authorizing diagnosis branch."""
    path = root / "execution.json"
    if not path.exists() and not path.is_symlink():
        return None
    parsed = dsse.parse_envelope(reader.read(path))
    if parsed.envelope is None:
        raise BackfillError(Failure.MALFORMED)
    value = canonical.parse_json(parsed.envelope.payload)
    result = execution_fidelity.ExecutionRequirements(
        release_required=False, harness_config_digest=None, collateral=None
    ).parse(value)
    return result.outcome.reason.name if result.outcome.reason is not None else None


def runs(configuration: Path, *, project_root: Path | None = None) -> tuple[Path, ...]:
    paths = children(configuration, project_root=project_root)
    if not paths or any(
        not path.is_dir() or RUN_NAME.fullmatch(path.name) is None for path in paths
    ):
        raise BackfillError(Failure.MALFORMED)
    return tuple(sorted(paths, key=lambda path: int(path.name.removeprefix("run_"))))
