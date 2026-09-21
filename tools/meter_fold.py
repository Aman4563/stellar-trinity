"""The consumption fold: one session export decoded into a per-session token tree.

This module reads and folds; it opens no path, writes nothing, and never touches the clock.
Every instant it reports was recorded by the export, so one export always folds to one answer.

Field names come from a capture of ``opencode export <id> --sanitize`` on opencode 1.1.51,
mirrored by ``tests/parent_fixtures.py`` and ``tests/fixtures/meter/export-sample.json``: a
document is ``{"info", "messages"}``, ``info.parentID`` is the session-tree edge, ``info.time``
records millisecond instants, and each assistant message records ``info.tokens`` as
``{"input", "output", "cache": {"read", "write"}}``. A user turn records no tokens at all.
Both one document and an array of documents are accepted, because ``opencode export`` emits
the first and a captured multi-session tree is stored as the second.

An export in any other shape is refused with ``METER_EXPORT_UNRECOGNIZED`` rather than folded
into zeros: absence of evidence is never evidence of a cheap run.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools._bounded_json import BoundedJsonError, Json, load_bounded_json
else:
    from _bounded_json import BoundedJsonError, Json, load_bounded_json

EXPORT_UNRECOGNIZED: Final = "METER_EXPORT_UNRECOGNIZED"
TOKEN_FIELDS: Final = ("input", "output", "cache")
CACHE_FIELDS: Final = ("read", "write")
MAX_EXPORT_BYTES: Final = 64 * 1024 * 1024
MAX_EXPORT_ITEMS: Final = 4_000_000


class MeterError(ValueError):
    """A refusal carrying one closed public code and a mechanical detail."""

    code: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Counts:
    """One fold of consumption, over a single session or over a whole subtree."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    messages: int = 0
    first: int | None = None
    last: int | None = None

    def merge(self, other: Counts) -> Counts:
        ends = [value for value in (self.first, self.last, other.first, other.last) if value]
        return Counts(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read=self.cache_read + other.cache_read,
            cache_write=self.cache_write + other.cache_write,
            messages=self.messages + other.messages,
            first=min(ends) if ends else None,
            last=max(ends) if ends else None,
        )


@dataclass(frozen=True, slots=True)
class Session:
    """One export document reduced to its tree edge, its own fold, and its metered turns."""

    session_id: str
    parent: str | None
    counts: Counts
    metered: int


@dataclass(frozen=True, slots=True)
class Entry:
    """One session's place in a walked tree, beside its own fold and its subtree fold."""

    session_id: str
    parent: str | None
    depth: int
    own: Counts
    subtree: Counts


@dataclass(frozen=True, slots=True)
class Fold:
    """Every walked session of the selected roots, and the total over those roots."""

    roots: list[str]
    entries: list[Entry]
    totals: Counts


def _mapping(value: Json, label: str) -> dict[str, Json]:
    if not isinstance(value, dict):
        raise MeterError(EXPORT_UNRECOGNIZED, f"{label} is not a JSON object")
    return value


def _text(value: Json, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise MeterError(EXPORT_UNRECOGNIZED, f"{label} is not a non-empty string")
    return value


def _whole(value: Json, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise MeterError(EXPORT_UNRECOGNIZED, f"{label} is not a non-negative integer")
    return value


def _instants(info: dict[str, Json], label: str, *, required: bool) -> list[int]:
    recorded = info.get("time")
    if recorded is None:
        if required:
            raise MeterError(EXPORT_UNRECOGNIZED, f"{label} records no time")
        return []
    moments = _mapping(recorded, f"{label} time")
    if required and "created" not in moments:
        raise MeterError(EXPORT_UNRECOGNIZED, f"{label} time records no created instant")
    return [
        _whole(value, f"{label} time {name}")
        for name, value in sorted(moments.items())
        if value is not None
    ]


def _turn(value: Json, label: str) -> Counts | None:
    """Fold one message's recorded token counts, or None when that turn records none."""
    if value is None:
        return None
    record = _mapping(value, label)
    absent = [name for name in TOKEN_FIELDS if name not in record]
    if absent:
        raise MeterError(EXPORT_UNRECOGNIZED, f"{label} records no {', '.join(absent)}")
    cache = _mapping(record["cache"], f"{label} cache")
    missing = [name for name in CACHE_FIELDS if name not in cache]
    if missing:
        raise MeterError(EXPORT_UNRECOGNIZED, f"{label} cache records no {', '.join(missing)}")
    return Counts(
        input_tokens=_whole(record["input"], f"{label} input"),
        output_tokens=_whole(record["output"], f"{label} output"),
        cache_read=_whole(cache["read"], f"{label} cache read"),
        cache_write=_whole(cache["write"], f"{label} cache write"),
    )


def _session(document: Json) -> Session:
    record = _mapping(document, "export document")
    if "info" not in record or "messages" not in record:
        raise MeterError(EXPORT_UNRECOGNIZED, "an export document is not an info and messages pair")
    info = _mapping(record["info"], "session info")
    session_id = _text(info.get("id"), "session id")
    parent = info.get("parentID")
    messages = record["messages"]
    if not isinstance(messages, list):
        raise MeterError(EXPORT_UNRECOGNIZED, f"session {session_id} messages is not an array")
    instants = _instants(info, f"session {session_id}", required=True)
    counts, metered = Counts(), 0
    for index, message in enumerate(messages):
        label = f"session {session_id} message {index}"
        body = _mapping(_mapping(message, label).get("info"), f"{label} info")
        instants += _instants(body, label, required=False)
        turn = _turn(body.get("tokens"), f"{label} tokens")
        if turn is not None:
            counts, metered = counts.merge(turn), metered + 1
    folded = replace(counts, messages=len(messages), first=min(instants), last=max(instants))
    edge = None if parent is None else _text(parent, "parentID")
    return Session(session_id, edge, folded, metered)


def read_export(data: bytes) -> dict[str, Session]:
    """Decode one export document, or an array of them, into export-ordered session records."""
    try:
        payload = load_bounded_json(data, max_bytes=MAX_EXPORT_BYTES, max_items=MAX_EXPORT_ITEMS)
    except BoundedJsonError as exc:
        raise MeterError(EXPORT_UNRECOGNIZED, f"the export is not bounded JSON: {exc}") from exc
    if isinstance(payload, dict):
        documents: list[Json] = [payload]
    elif isinstance(payload, list) and payload:
        documents = list(payload)
    else:
        raise MeterError(EXPORT_UNRECOGNIZED, "the export is neither a document nor an array")
    sessions: dict[str, Session] = {}
    for document in documents:
        session = _session(document)
        if session.session_id in sessions:
            raise MeterError(EXPORT_UNRECOGNIZED, f"session {session.session_id} appears twice")
        sessions[session.session_id] = session
    if not any(session.metered for session in sessions.values()):
        raise MeterError(EXPORT_UNRECOGNIZED, "no message in the export records a token count")
    return sessions


def _children(sessions: dict[str, Session]) -> dict[str, list[str]]:
    kin: dict[str, list[str]] = {session_id: [] for session_id in sessions}
    for session_id, session in sessions.items():
        parent = session.parent
        if parent is not None and parent in sessions and parent != session_id:
            kin[parent].append(session_id)
    return kin


def _descend(node: str, kin: dict[str, list[str]], seen: set[str]) -> list[str]:
    """Walk one subtree in export order, tolerating a parent cycle rather than recursing on it."""
    if node in seen:
        return []
    seen.add(node)
    walked = [node]
    for child in kin[node]:
        walked += _descend(child, kin, seen)
    return walked


def roots_of(sessions: dict[str, Session], selected: str | None) -> list[str]:
    """Name the selected root, or every session whose parent the export does not carry."""
    if selected is not None:
        if selected not in sessions:
            raise ValueError(f"--root {selected} names no session in the export")
        return [selected]
    return [
        session_id
        for session_id, session in sessions.items()
        if session.parent is None or session.parent not in sessions
    ]


def fold(sessions: dict[str, Session], roots: list[str]) -> Fold:
    """Sum every descendant into its ancestors and total the selected roots."""
    kin = _children(sessions)
    entries: list[Entry] = []
    totals = Counts()
    for root in roots:
        walked = _descend(root, kin, set())
        depths = {root: 0}
        subtrees: dict[str, Counts] = {}
        for session_id in walked:
            for child in kin[session_id]:
                depths[child] = depths[session_id] + 1
        for session_id in reversed(walked):
            gathered = sessions[session_id].counts
            for child in kin[session_id]:
                gathered = gathered.merge(subtrees[child])
            subtrees[session_id] = gathered
        entries += [
            Entry(
                session_id=session_id,
                parent=sessions[session_id].parent,
                depth=depths[session_id],
                own=sessions[session_id].counts,
                subtree=subtrees[session_id],
            )
            for session_id in walked
        ]
        totals = totals.merge(subtrees[root])
    return Fold(roots=list(roots), entries=entries, totals=totals)
