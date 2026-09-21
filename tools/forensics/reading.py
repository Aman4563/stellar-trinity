"""Bounded JSON boundary: typed accessors reject malformed consumed fields."""

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools._bounded_json import BoundedJsonError, Json, load_bounded_json
else:
    try:
        from tools._bounded_json import BoundedJsonError, Json, load_bounded_json
    except ModuleNotFoundError:
        from _bounded_json import BoundedJsonError, Json, load_bounded_json

from .bundle import MAX_TRACE_BYTES, MAX_TRACE_LINES, TraceBundle
from .core import FidelityRefusal

__all__ = ["BoundedJsonError", "Json", "load_bounded_json"]


@dataclass(frozen=True, slots=True)
class TraceReadError(ValueError):
    refusal: FidelityRefusal = FidelityRefusal.FIDELITY_TRACE_UNREADABLE

    def __str__(self) -> str:
        return self.refusal.value


def document(raw: bytes) -> Mapping[str, Json]:
    if len(raw) > MAX_TRACE_BYTES:
        raise TraceReadError
    try:
        value = load_bounded_json(raw, max_bytes=MAX_TRACE_BYTES)
    except BoundedJsonError as error:
        raise TraceReadError from error
    return record(value)


def record(value: Json) -> Mapping[str, Json]:
    if not isinstance(value, dict):
        raise TraceReadError
    return value


def child(data: Mapping[str, Json], key: str) -> Mapping[str, Json]:
    return record(data[key]) if key in data else {}


def text(data: Mapping[str, Json], key: str) -> str | None:
    if key not in data:
        return None
    value = data[key]
    if not isinstance(value, str):
        raise TraceReadError
    return value


def integer(data: Mapping[str, Json], key: str) -> int | None:
    if key not in data:
        return None
    value = data[key]
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise TraceReadError
    return value


def boolean(data: Mapping[str, Json], key: str) -> bool | None:
    if key not in data:
        return None
    value = data[key]
    if not isinstance(value, bool):
        raise TraceReadError
    return value


def array(data: Mapping[str, Json], key: str) -> tuple[Json, ...]:
    if key not in data:
        return ()
    value = data[key]
    if not isinstance(value, list):
        raise TraceReadError
    return tuple(value)


def json_file(bundle: TraceBundle, path: str) -> Mapping[str, Json]:
    return document(bundle.files[path]) if path in bundle.files else {}


def log_records(raw: bytes) -> tuple[Mapping[str, Json], ...]:
    if len(raw) > MAX_TRACE_BYTES or raw.count(b"\n") > MAX_TRACE_LINES:
        raise TraceReadError
    lines = raw.splitlines()
    if len(lines) > MAX_TRACE_LINES:
        raise TraceReadError
    return tuple(document(line) for line in lines if line.strip())


def contiguous(indices: tuple[int, ...]) -> bool:
    return all(right == left + 1 for left, right in pairwise(indices))
