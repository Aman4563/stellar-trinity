"""FORGE-owned task lane registry: one immutable record per uuid, safe to merge.

A task lane is routed and never discovered, and under many concurrent runners it is
decided at the merge, never at the clone. Every author registers a staged bundle as
``starter`` or ``sample`` at ``.seed/lanes/<uuid>.yaml`` and places it under ``samples/``;
``pipeline.py reconcile`` then orders every resident bundle by seal order, keeps the
first thirty under ``samples/``, and renames the overflow into ``delivery/``. Nothing
here counts capacity, so two clones registering at once never disagree, and a record is
never edited because a lane is immutable for the life of a uuid.

The legacy singleton ``.seed/lanes.yaml`` stays readable so a project that registered
bundles before per-uuid records keeps its routing.
"""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SAMPLE_CEILING: Final = 30
DELIVERY_CEILING: Final = 10000
LANES_DIR: Final = Path(".seed/lanes")
LEGACY_LANES_PATH: Final = Path(".seed/lanes.yaml")
STAGING_DIR: Final = Path("staging")
TASK_LANE_ROOTS: Final[dict[str, str]] = {
    "starter": "samples",
    "sample": "samples",
    "delivery": "delivery",
}
CLAIMABLE_LANES: Final = frozenset({"starter", "sample"})
LANE_CEILINGS: Final[dict[str, int]] = {"samples": SAMPLE_CEILING, "delivery": DELIVERY_CEILING}
# ENGRAM publishes one anchor-standing row per designated anchor uuid with each epoch.
# A starter holds a place inside the sample ceiling until its row graduates, then
# reconcile moves it into delivery/ because its calibration purpose is served.
ANCHOR_STANDING_PATH: Final = Path(".memory/anchor_standing.yaml")
ANCHOR_STATES: Final = frozenset({"CANDIDATE", "ANCHORED", "SUPERSEDED"})
GRADUATED_ANCHOR_STATES: Final = frozenset({"ANCHORED", "SUPERSEDED"})
LANE_UNRESOLVED_DETAILS: Final[tuple[str, ...]] = (
    "registry missing or unreadable",
    "no row names the uuid",
    "no task_lane in the row",
    "more than one task_lane in a row",
    "rows disagree on task_lane",
    'task_lane "{value}" is outside starter, sample, delivery',
)

ROUTE_CODES: Final = frozenset(
    {
        "invalid-claim",
        "not-staged",
        "registry-unreadable",
        "lane-immutable",
        "registry-write-failed",
    }
)
ROUTE_DETAILS: Final[dict[str, str]] = {
    "invalid-claim": "claim field {field} is outside its closed form",
    "not-staged": "bundle {uuid} is not a directory under staging/ alone",
    "registry-unreadable": "registry is unreadable at {where}",
    "lane-immutable": "uuid {uuid} is already registered as {lane}",
    "registry-write-failed": "registry could not be written",
}

_UUID5 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_BATCH = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")
_RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
_ITEM_OPENING = re.compile(r"^([ \t]*)-[ \t]")
_UUID_ROW = re.compile(r"^[ \t]*(?:-[ \t]+)?uuid:[ \t]*([0-9a-f-]+)[ \t]*(?:#.*)?$")
_LANE_ROW = re.compile(r"^[ \t]+task_lane:[ \t]*([A-Za-z_]+)[ \t]*(?:#.*)?$")
_RECORD_LINE = re.compile(r"^([a-z_]+):[ \t]*(\S.*?)[ \t]*$")
_STANDING_LINE = re.compile(r"^([0-9a-f-]+):[ \t]*([A-Z]+)[ \t]*(?:#.*)?$")


@dataclass(frozen=True, slots=True)
class LaneClaim:
    """The lane FORGE bound for one slot at Phase 0.5, presented to ``route`` at seal time."""

    uuid: str
    task_lane: str
    slot: int
    batch: str
    run_id: str


class RouteError(ValueError):
    """A routing refusal with a closed public code and mechanical detail."""

    code: str
    detail: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _unreadable(where: str) -> RouteError:
    return RouteError(
        "registry-unreadable", ROUTE_DETAILS["registry-unreadable"].format(where=where)
    )


def registry_items(lines: list[str]) -> Iterator[list[str]]:
    """Yield each indent-bounded dash item of the legacy registry, opening line included."""
    for index, line in enumerate(lines):
        opening = _ITEM_OPENING.match(line)
        if opening is None:
            continue
        dash_indent = len(opening[1])
        end = index + 1
        while end < len(lines):
            following = lines[end]
            indent = len(following) - len(following.lstrip(" \t"))
            if following.strip() and indent <= dash_indent:
                break
            end += 1
        yield lines[index:end]


def _legacy_lanes(root: Path) -> dict[str, str]:
    path = root / LEGACY_LANES_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise _unreadable(str(LEGACY_LANES_PATH)) from exc
    lanes: dict[str, str] = {}
    for number, body in enumerate(registry_items(lines), start=1):
        uuids = [match[1] for row in body if (match := _UUID_ROW.fullmatch(row))]
        tokens = [match[1] for row in body if (match := _LANE_ROW.fullmatch(row))]
        if len(uuids) != 1 or len(tokens) != 1 or tokens[0] not in TASK_LANE_ROOTS:
            raise _unreadable(f"{LEGACY_LANES_PATH} row {number}")
        if lanes.get(uuids[0], tokens[0]) != tokens[0]:
            raise _unreadable(f"{LEGACY_LANES_PATH} row {number}")
        lanes[uuids[0]] = tokens[0]
    return lanes


def _record_lanes(root: Path) -> dict[str, str]:
    directory = root / LANES_DIR
    if not directory.is_dir():
        return {}
    lanes: dict[str, str] = {}
    for path in sorted(directory.glob("*.yaml")):
        where = f"{LANES_DIR}/{path.name}"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise _unreadable(where) from exc
        fields: dict[str, str] = {}
        for line in lines:
            match = _RECORD_LINE.fullmatch(line)
            if match is None or match[1] in fields:
                raise _unreadable(where)
            fields[match[1]] = match[2]
        uuid = fields.get("uuid")
        lane = fields.get("task_lane")
        if uuid != path.stem or lane not in TASK_LANE_ROOTS:
            raise _unreadable(where)
        lanes[uuid] = lane
    return lanes


def registered_lanes(root: Path) -> dict[str, str]:
    """Every registered uuid with its lane token, from per-uuid records and the legacy file."""
    records = _record_lanes(root)
    legacy = _legacy_lanes(root)
    for uuid, lane in legacy.items():
        if records.get(uuid, lane) != lane:
            raise _unreadable(f"{LANES_DIR}/{uuid}.yaml against {LEGACY_LANES_PATH}")
    return {**legacy, **records}


class AnchorStandingError(ValueError):
    """``.memory/anchor_standing.yaml`` is present but not a flat uuid-to-state map."""


def anchor_standing(root: Path) -> dict[str, str]:
    """Every designated anchor uuid with its published row state; absent means none."""
    path = root / ANCHOR_STANDING_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise AnchorStandingError(f"{ANCHOR_STANDING_PATH} is unreadable") from exc
    standing: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _STANDING_LINE.fullmatch(line)
        if (
            match is None
            or _UUID5.fullmatch(match[1]) is None
            or match[2] not in ANCHOR_STATES
            or match[1] in standing
        ):
            raise AnchorStandingError(
                f"{ANCHOR_STANDING_PATH} line {number} is not <uuid>: <state>"
            )
        standing[match[1]] = match[2]
    return standing


def _is_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(os.lstat(path).st_mode)
    except FileNotFoundError:
        return False


def resident_uuids(lane_root: Path) -> set[str]:
    """The uuid5 bundle directories resident under one lane root, none when it is absent."""
    if not lane_root.is_dir():
        return set()
    return {
        path.name
        for path in lane_root.iterdir()
        if _UUID5.fullmatch(path.name) and _is_directory(path)
    }


def _validate(claim: LaneClaim) -> None:
    checks = (
        ("uuid", _UUID5.fullmatch(claim.uuid) is not None),
        ("task_lane", claim.task_lane in CLAIMABLE_LANES),
        ("slot", claim.slot >= 1),
        ("batch", _BATCH.fullmatch(claim.batch) is not None),
        ("run_id", _RUN.fullmatch(claim.run_id) is not None),
    )
    for field, valid in checks:
        if not valid:
            raise RouteError("invalid-claim", ROUTE_DETAILS["invalid-claim"].format(field=field))


def route(root: Path, claim: LaneClaim) -> str:
    """Register one staged bundle's lane. Returns the registered token.

    A uuid already registered with the same token is returned without a write; a
    different token is refused because a lane is immutable. Capacity is never counted
    here: the merge decides overflow through ``pipeline.py reconcile``.
    """
    _validate(claim)
    registered = registered_lanes(root).get(claim.uuid)
    if registered is not None:
        if registered != claim.task_lane:
            raise RouteError(
                "lane-immutable",
                ROUTE_DETAILS["lane-immutable"].format(uuid=claim.uuid, lane=registered),
            )
        return registered
    staged = _is_directory(root / STAGING_DIR / claim.uuid)
    placed = any((root / lane / claim.uuid).exists() for lane in LANE_CEILINGS)
    if not staged or placed:
        raise RouteError("not-staged", ROUTE_DETAILS["not-staged"].format(uuid=claim.uuid))
    path = root / LANES_DIR / f"{claim.uuid}.yaml"
    body = (
        f"uuid: {claim.uuid}\n"
        f"task_lane: {claim.task_lane}\n"
        f"slot: {claim.slot}\n"
        f"batch: {claim.batch}\n"
        f"run_id: {claim.run_id}\n"
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(body)
    except OSError as exc:
        raise RouteError("registry-write-failed", ROUTE_DETAILS["registry-write-failed"]) from exc
    return claim.task_lane
