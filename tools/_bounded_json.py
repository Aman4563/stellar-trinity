"""Resource-bounded JSON decoding shared by untrusted evidence readers."""

import json
import math
from dataclasses import dataclass
from typing import Final, TypeAlias, assert_never

Json: TypeAlias = "bool | int | float | str | list[Json] | dict[str, Json] | None"
MAX_JSON_BYTES: Final = 16 * 1024 * 1024
MAX_JSON_DEPTH: Final = 64
MAX_JSON_ITEMS: Final = 100000


@dataclass(frozen=True, slots=True)
class BoundedJsonError(ValueError):
    detail: str

    def __str__(self) -> str:
        return self.detail


def _unique_fields(pairs: list[tuple[str, Json]]) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for key, value in pairs:
        if key in result:
            raise BoundedJsonError("duplicate JSON field")
        result[key] = value
    return result


def load_bounded_json(
    data: bytes,
    *,
    max_bytes: int = MAX_JSON_BYTES,
    max_depth: int = MAX_JSON_DEPTH,
    max_items: int = MAX_JSON_ITEMS,
) -> Json:
    """Bound allocation before decoding, then validate every container and scalar.

    The three independent budgets are explicit keyword arguments for shared callers.
    Only UTF-8 is admitted so the byte-level structural scan cannot miss UTF-16 tokens.
    """
    if len(data) > max_bytes or min(max_bytes, max_depth, max_items) < 0:
        raise BoundedJsonError("JSON byte limit exceeded")
    depth = 0
    quoted = False
    escaped = False
    for byte in data:
        if quoted:
            if escaped:
                escaped = False
            elif byte == ord("\\"):
                escaped = True
            elif byte == ord('"'):
                quoted = False
        elif byte == ord('"'):
            quoted = True
        elif byte in b"[{":
            depth += 1
            if depth > max_depth:
                raise BoundedJsonError("JSON depth limit exceeded")
        elif byte in b"]}":
            depth -= 1
    try:
        value: Json = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_fields)
        pending = [(value, 0)]
        while pending:
            node, level = pending.pop()
            match node:
                case dict():
                    if level >= max_depth or len(node) > max_items:
                        raise BoundedJsonError("JSON container limit exceeded")
                    for key, child in node.items():
                        key.encode("utf-8")
                        pending.append((child, level + 1))
                case list():
                    if level >= max_depth or len(node) > max_items:
                        raise BoundedJsonError("JSON container limit exceeded")
                    pending.extend((child, level + 1) for child in node)
                case str():
                    node.encode("utf-8")
                case float():
                    if not math.isfinite(node):
                        raise BoundedJsonError("non-finite JSON number")
                case bool() | int() | None:
                    continue
                case unreachable:
                    assert_never(unreachable)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise BoundedJsonError("malformed or excessive JSON") from error
    return value
