"""Disposable content-addressed run projections; never an evidence writer."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, TypeAlias

if TYPE_CHECKING:
    from tools import reports, runs, tracker
else:
    try:
        from tools import reports, runs, tracker
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        import reports
        import runs
        import tracker

PARSER_VERSION: Final = 3
JSONValue: TypeAlias = str | int | float | bool | list["JSONValue"] | dict[str, "JSONValue"] | None


@dataclass(frozen=True, slots=True)
class CacheLocation:
    path: Path
    persist: bool = True


def plain_text(value: str) -> str:
    text = "".join(
        c for c in " ".join(value.split()) if " " <= c <= "~" and c not in "<>[]()!`|&*~"
    )
    text = re.sub(r":([a-z0-9_+-]+):", r"\1", text.replace("://", ""))
    text = re.sub(r"(?<![A-Za-z0-9_])_+|_+(?![A-Za-z0-9_])", "", text)
    return " ".join(text.split())[:80].strip()


@dataclass(frozen=True, slots=True)
class RunRecord:
    instrument: str
    run_id: str
    principal: str
    started_at: str
    disposition: str
    phase: str
    phases_done: int
    phases_total: int
    gates_done: int
    gates_total: int
    open_gates: tuple[str, ...]
    gap_count: int
    closed_at: str | None
    closure: Literal["closed", "open", "unknown"]
    has_escalations: bool

    @property
    def gaps(self) -> int:
        return self.gap_count


def normalize_instant(value: str) -> str | None:
    try:
        instant = datetime.fromisoformat(value)
        if instant.tzinfo is None:
            return None
        return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError):
        return None


def git_output(root: Path, args: tuple[str, ...]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            env={**os.environ, "GIT_MASTER": "1"},
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def cache_location(root: Path, *, persist: bool = True) -> CacheLocation | None:
    """Resolve Git's per-worktree cache, or degrade to an uncached inventory."""
    value = git_output(root, ("rev-parse", "--git-path", "trinity/tracker-cache/v1"))
    if not value:
        return None
    path = (root / value).resolve()
    try:
        if persist:
            path.mkdir(parents=True, exist_ok=True)
        return CacheLocation(path, persist=persist)
    except OSError:
        return None


def _cache_key(directory: Path, root: Path) -> str | None:
    parts = [str(PARSER_VERSION), directory.relative_to(root).as_posix()]
    for name in (*tracker.SOURCE_NAMES, tracker.CARD_NAME):
        try:
            digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        except FileNotFoundError:
            digest = "absent"
        except OSError:
            return None
        parts.extend((name, digest))
    return hashlib.sha256(json.dumps(parts).encode()).hexdigest()


def _text(payload: dict[str, JSONValue], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise TypeError(key)
    return value


def _count(payload: dict[str, JSONValue], key: str) -> int:
    value = payload[key]
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise TypeError(key)
    return value


def _cached(path: Path, run: runs.Run) -> RunRecord | None:
    try:
        envelope: JSONValue = json.loads(path.read_bytes())
        if not isinstance(envelope, dict):
            return None
        if (
            envelope.get("key") != path.stem
            or envelope.get("run_id") != run.run_id
            or envelope.get("instrument") != run.instrument
        ):
            return None
        payload = envelope.get("run")
        digest = hashlib.sha256(
            json.dumps([path.stem, payload], sort_keys=True).encode()
        ).hexdigest()
        if envelope.get("sha256") != digest:
            return None
        if not isinstance(payload, dict) or set(payload) != {f.name for f in fields(RunRecord)}:
            return None
        if payload["run_id"] != run.run_id or payload["instrument"] != run.instrument:
            return None
        closed, closure = payload["closed_at"], payload["closure"]
        gates, escalations = payload["open_gates"], payload["has_escalations"]
        if closure not in ("closed", "open", "unknown") or not isinstance(escalations, bool):
            return None
        if closed is not None and (
            not isinstance(closed, str) or normalize_instant(closed) != closed
        ):
            return None
        if (closure == "closed") != (closed is not None) or not isinstance(gates, list):
            return None
        gate_ids = tuple(value for value in gates if isinstance(value, str))
        if len(gate_ids) != len(gates):
            return None
        return RunRecord(
            instrument=_text(payload, "instrument"),
            run_id=_text(payload, "run_id"),
            principal=_text(payload, "principal"),
            started_at=_text(payload, "started_at"),
            disposition=_text(payload, "disposition"),
            phase=_text(payload, "phase"),
            phases_done=_count(payload, "phases_done"),
            phases_total=_count(payload, "phases_total"),
            gates_done=_count(payload, "gates_done"),
            gates_total=_count(payload, "gates_total"),
            open_gates=gate_ids,
            gap_count=_count(payload, "gap_count"),
            closed_at=closed,
            closure="closed" if closure == "closed" else "open" if closure == "open" else "unknown",
            has_escalations=escalations,
        )
    except (OSError, UnicodeDecodeError, ValueError, TypeError, KeyError):
        return None


def _parse_run(directory: Path, run: runs.Run) -> RunRecord:
    try:
        text = (directory / "report.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        text = ""
    sections = reports._sections(text)
    progress = reports._progress(directory)
    card_path = directory / tracker.CARD_NAME
    closure: Literal["closed", "open", "unknown"] = "open"
    closed_at = None
    if os.path.lexists(card_path):
        card = tracker._read_card(card_path, run)
        closure = "unknown"
        if isinstance(card, dict):
            closed_at = normalize_instant(str(card["closed_at"]))
            if closed_at is not None:
                closure = "closed"
    return RunRecord(
        instrument=run.instrument,
        run_id=run.run_id,
        principal=plain_text(run.principal),
        started_at=normalize_instant(run.started_at) or "unknown",
        disposition=plain_text(reports._disposition(sections)),
        phase=plain_text(progress.get("phase") or "unknown"),
        phases_done=reports._int(progress.get("phases_done", "0")),
        phases_total=reports._int(progress.get("phases_total", "0")),
        gates_done=reports._int(progress.get("gates_done", "0")),
        gates_total=reports._int(progress.get("gates_total", "0")),
        open_gates=tuple(
            sorted(
                plain_text(g)
                for g in progress.get("open_gates", "").strip("[] ").split(",")
                if g.strip()
            )
        ),
        gap_count=reports._int(progress.get("gaps", "0")),
        closed_at=closed_at,
        closure=closure,
        has_escalations=bool(sections.get("Escalations", "").strip()),
    )


def load_runs(root: Path, cache: CacheLocation | None) -> tuple[tuple[RunRecord, ...], int]:
    records: list[RunRecord] = []
    parsed = 0
    for instrument in sorted(runs.HARNESS):
        for run in runs.list_runs(root, instrument):
            directory = runs.run_dir(root, instrument, run.run_id)
            key = _cache_key(directory, root) if cache is not None else None
            path = cache.path / "runs" / f"{key}.json" if cache is not None and key else None
            record = _cached(path, run) if path is not None else None
            if record is None:
                record = _parse_run(directory, run)
                parsed += 1
                if path is not None and cache is not None and cache.persist:
                    try:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        payload = asdict(record)
                        digest = hashlib.sha256(
                            json.dumps([key, payload], sort_keys=True).encode()
                        ).hexdigest()
                        body = json.dumps(
                            {
                                "key": key,
                                "run_id": run.run_id,
                                "instrument": run.instrument,
                                "run": payload,
                                "sha256": digest,
                            },
                            sort_keys=True,
                        )
                        tracker._atomic_write(path, body + "\n")
                    except OSError:
                        path = None
            records.append(record)
    return tuple(sorted(records, key=lambda r: (r.started_at, r.instrument, r.run_id))), parsed
