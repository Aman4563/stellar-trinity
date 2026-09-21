"""Run identity: the namespace one instrument invocation owns on one clone.

Many humans run Trinity at once and sync through git, so every mutable byte an
invocation writes lives under ``<harness>/runs/<run_id>/`` where nobody else writes.
A run id is minted once from instrument, principal, instant, and entropy, and the
``run.json`` inside the namespace binds that ownership so a second principal cannot
adopt the namespace. Nothing here confers authority: the gate authenticates the
principal against enrolment, and a filename is never a signature.
"""

from __future__ import annotations

import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

SCHEMA: Final = "trinity.run/v1"
RUN_ID: Final = re.compile(r"[a-z0-9][a-z0-9.-]{7,79}\Z")
RUNS_DIR: Final = "runs"
HARNESS: Final[dict[str, str]] = {"ENGRAM": ".memory", "FORGE": ".seed", "CRUCIBLE": ".audit"}
_PRINCIPAL_TOKEN: Final = re.compile(r"[^a-z0-9]+")


class RunError(ValueError):
    """A run identity refusal with a closed public code."""

    code: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Run:
    instrument: str
    run_id: str
    principal: str
    started_at: str


def _stamp(now: datetime) -> str:
    return now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_run_id(value: str) -> str:
    if RUN_ID.fullmatch(value) is None or ".." in value:
        raise RunError("invalid-run-id", "run id is outside [a-z0-9][a-z0-9.-]{7,79}")
    return value


def new_run_id(instrument: str, principal: str, now: datetime | None = None) -> str:
    """``<instrument>-<principal>-<stamp>-<6 hex>`` in the closed run-id grammar."""
    instant = datetime.now(UTC) if now is None else now.astimezone(UTC)
    slug = _PRINCIPAL_TOKEN.sub("-", principal.casefold()).strip("-") or "anon"
    stamp = instant.strftime("%Y%m%dt%H%M%Sz")
    return parse_run_id(f"{instrument.casefold()}-{slug[:24]}-{stamp}-{secrets.token_hex(3)}")


def run_dir(root: Path, instrument: str, run_id: str) -> Path:
    """The namespace for ``run_id``; a run id names its instrument as its first token."""
    harness = HARNESS.get(instrument)
    if harness is None:
        raise RunError("invalid-instrument", f"{instrument} owns no run namespace")
    if not parse_run_id(run_id).startswith(f"{instrument.casefold()}-"):
        raise RunError("run-owned", f"{run_id} is not a {instrument} run")
    return root / harness / RUNS_DIR / run_id


def _read_run(path: Path) -> Run | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        return None
    fields = ("instrument", "run_id", "principal", "started_at")
    if not all(isinstance(raw.get(name), str) and raw[name] for name in fields):
        return None
    return Run(*(str(raw[name]) for name in fields))


def open_run(
    root: Path, instrument: str, run_id: str, *, principal: str, now: datetime | None = None
) -> Path:
    """Create the run namespace and bind its owner, or return it when already owned."""
    directory = run_dir(root, instrument, run_id)
    marker = directory / "run.json"
    existing = _read_run(marker)
    if existing is not None:
        if existing.instrument != instrument or existing.principal != principal:
            raise RunError(
                "run-owned",
                f"{run_id} belongs to {existing.instrument} under {existing.principal}",
            )
        return directory
    if marker.exists():
        raise RunError("run-owned", f"{run_id} carries an unreadable run.json")
    directory.mkdir(parents=True, exist_ok=True)
    body = {
        "schema": SCHEMA,
        "instrument": instrument,
        "run_id": run_id,
        "principal": principal,
        "started_at": _stamp(datetime.now(UTC) if now is None else now),
    }
    marker.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return directory


def list_runs(root: Path, instrument: str) -> list[Run]:
    base = root / HARNESS[instrument] / RUNS_DIR
    if not base.is_dir():
        return []
    out: list[Run] = []
    for path in sorted(base.iterdir()):
        if RUN_ID.fullmatch(path.name) is None:
            continue
        run = _read_run(path / "run.json")
        if run is not None and run.run_id == path.name and run.instrument == instrument:
            out.append(run)
    return out
