"""Native capture boundary; inventories prevent a single good record proving a run."""

from collections.abc import Mapping
from dataclasses import dataclass

from .bundle import RAW_AGENT_PATHS
from .contracts import CAPTURE_PROFILE
from .reading import Json, TraceReadError, array, contiguous, integer, text


@dataclass(frozen=True, slots=True)
class NativeCapture:
    records: tuple[Mapping[str, Json], ...]
    pointer: str
    start: Mapping[str, Json]
    terminal: Mapping[str, Json]
    complete: bool
    session_id: str | None

    def of_type(self, kind: str) -> tuple[Mapping[str, Json], ...]:
        return tuple(event for event in self.records if text(event, "type") == kind)

    def inventoried(self, kind: str, key: str) -> bool:
        records = self.of_type(kind)
        identities = tuple(text(event, key) for event in records)
        expected: list[str] = []
        for value in array(self.terminal, key + "s"):
            if not isinstance(value, str) or not value:
                raise TraceReadError
            expected.append(value)
        return (
            bool(identities)
            and all(identities)
            and len(set(identities)) == len(identities)
            and len(set(expected)) == len(expected)
            and set(identities) == set(expected)
        )


def capture(records: tuple[Mapping[str, Json], ...], path: str) -> NativeCapture:
    claude = path in RAW_AGENT_PATHS
    start = records[0] if records else {}
    terminal = records[-1] if records else {}
    key = "index" if claude else "id"
    indices = tuple(integer(event, key) for event in records)
    sequence = tuple(index for index in indices if index is not None)
    session_id = text(start, "session_id")
    complete = (
        len(records) > 1
        and len(sequence) == len(records)
        and sequence[0] in (0, 1)
        and contiguous(sequence)
        and text(start, "capture_profile") == CAPTURE_PROFILE
        and bool(session_id)
        and all(text(event, "session_id") == session_id for event in records)
        and (
            text(start, "type") == "system" and text(start, "subtype") == "init"
            if claude
            else text(start, "type") == "SessionStart"
        )
        and text(terminal, "type") == ("result" if claude else "Terminal")
        and sum(text(event, "type") == ("result" if claude else "Terminal") for event in records)
        == 1
    )
    return NativeCapture(records, f"./{path}:1", start, terminal, complete, session_id)
