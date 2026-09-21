"""Strict parsing of frozen closure cards and their current source bindings."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import runs
else:
    try:
        from tools import runs
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        import runs

SCHEMA: Final = "trinity.tracker-card/v1"
PARSER_VERSION: Final = 1
SOURCE_NAMES: Final = ("run.json", "report.md", "progress.yaml")
COUNT_NAMES: Final = ("phases_done", "phases_total", "gates_done", "gates_total", "gaps")
CARD_KEYS: Final = frozenset(
    {
        "schema",
        "instrument",
        "run_id",
        "principal",
        "started_at",
        "closed_at",
        "disposition",
        "phase",
        "open_gates",
        "sources",
        "parser_version",
        *COUNT_NAMES,
    }
)
INSTANT: Final = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
STAMP: Final = "%Y-%m-%dT%H:%M:%SZ"
IDENTITY_SOURCE: Final = "run.json"
MALFORMED: Final = "TRACKER_CARD_MALFORMED"
IDENTITY_MISMATCH: Final = "TRACKER_CARD_IDENTITY_MISMATCH"
INPUT_MISSING: Final = "TRACKER_CARD_INPUT_MISSING"
SUPERSEDED: Final = "TRACKER_CARD_SUPERSEDED"


@dataclass(frozen=True, slots=True)
class Refusal:
    """Why a card on disk is not a trustworthy closure, under one closed code.

    ``MALFORMED`` is a card the renderer cannot parse or that no longer binds ``run.json``,
    ``IDENTITY_MISMATCH`` is a card that contradicts the run it sits under, ``INPUT_MISSING`` is
    a bound source that is absent or unreadable, and ``SUPERSEDED`` is a card whose identity
    still holds while only the derived ``report.md`` or ``progress.yaml`` moved after closure,
    which is what a lawful resume of the same run leaves behind.
    """

    code: str
    reason: str


def read_card(path: Path, run: runs.Run) -> dict[str, object] | Refusal:
    """Return a validated card, or the one refusal that says why its closure cannot be trusted."""
    try:
        payload = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return Refusal(MALFORMED, "the card is unreadable or is not valid JSON")
    if not isinstance(payload, dict):
        return Refusal(MALFORMED, "the card is not a JSON object")
    if payload.get("schema") != SCHEMA:
        return Refusal(MALFORMED, f"the card does not declare {SCHEMA}")
    if set(payload) != CARD_KEYS:
        missing = ", ".join(sorted(CARD_KEYS - set(payload))) or "none"
        unknown = ", ".join(sorted(set(payload) - CARD_KEYS)) or "none"
        return Refusal(MALFORMED, f"the card omits {missing} and carries unknown {unknown}")
    for name in ("instrument", "run_id", "principal", "started_at"):
        bound = getattr(run, name)
        if payload[name] != bound:
            return Refusal(IDENTITY_MISMATCH, f"the card {name} contradicts run.json {bound}")
    if type(payload["parser_version"]) is not int or payload["parser_version"] != PARSER_VERSION:
        return Refusal(MALFORMED, "the card parser_version is unsupported")
    for name in ("disposition", "phase"):
        if not isinstance(payload[name], str) or not payload[name].strip():
            return Refusal(MALFORMED, f"the card {name} is not a non-empty string")
    for name in COUNT_NAMES:
        if type(payload[name]) is not int or payload[name] < 0:
            return Refusal(MALFORMED, f"the card {name} is not a nonnegative integer")
    gates = payload["open_gates"]
    if not isinstance(gates, list) or not all(isinstance(gate, str) for gate in gates):
        return Refusal(MALFORMED, "the card open_gates is not a list of strings")
    if gates != sorted(gates):
        return Refusal(MALFORMED, "the card open_gates is not sorted")
    sources = payload["sources"]
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_NAMES):
        return Refusal(MALFORMED, "the card sources do not name exactly the run sources")
    if not all(isinstance(d, str) and re.fullmatch(r"[0-9a-f]{64}", d) for d in sources.values()):
        return Refusal(MALFORMED, "the card sources are not lowercase SHA-256 digests")
    closed = payload["closed_at"]
    if not isinstance(closed, str) or INSTANT.fullmatch(closed) is None:
        return Refusal(MALFORMED, "the card closed_at is not a YYYY-MM-DDTHH:MM:SSZ instant")
    try:
        if datetime.strptime(closed, STAMP) < datetime.strptime(run.started_at, STAMP):
            return Refusal(MALFORMED, "the card closed_at precedes started_at")
    except ValueError:
        return Refusal(MALFORMED, "the card closure is not a valid calendar instant")
    current: dict[str, str] = {}
    for name in SOURCE_NAMES:
        try:
            current[name] = hashlib.sha256((path.parent / name).read_bytes()).hexdigest()
        except OSError:
            return Refusal(INPUT_MISSING, f"the card binds {name}, which is absent or unreadable")
    if sources[IDENTITY_SOURCE] != current[IDENTITY_SOURCE]:
        return Refusal(MALFORMED, f"the card does not bind the current {IDENTITY_SOURCE} bytes")
    moved = sorted(name for name in SOURCE_NAMES if sources[name] != current[name])
    if moved:
        return Refusal(SUPERSEDED, f"the run continued after closure: {', '.join(moved)} moved")
    return payload
