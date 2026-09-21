from __future__ import annotations

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from tools import lanes

from tests.bite_shared.registration import bite

CLAIM_UUID = str(uuid5(NAMESPACE_URL, "claim"))
OTHER_UUID = str(uuid5(NAMESPACE_URL, "other"))
BATCH = "batch-0001"
RUN = "forge-ada-1"


def stage(root: Path, uuid: str) -> Path:
    bundle = root / "staging" / uuid
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "task.toml").write_text('name = "one"\n', encoding="utf-8")
    return bundle


def claim(task_lane: str, uuid: str = CLAIM_UUID, slot: int = 1) -> lanes.LaneClaim:
    return lanes.LaneClaim(uuid=uuid, task_lane=task_lane, slot=slot, batch=BATCH, run_id=RUN)


def prepare(root: Path) -> None:
    (root / "samples").mkdir(parents=True)
    (root / "delivery").mkdir()
    stage(root, CLAIM_UUID)


def assert_refused(root: Path, task_lane: str, code: str) -> lanes.RouteError:
    with pytest.raises(lanes.RouteError) as refused:
        lanes.route(root, claim(task_lane))
    assert refused.value.code == code
    assert refused.value.code in lanes.ROUTE_CODES
    assert str(refused.value) == f"{code}: {refused.value.detail}"
    return refused.value


# ---- registration ----


@bite("forge.md:F63")
def test_route_registers_a_sample_claim_without_counting_capacity(tmp_path: Path) -> None:
    prepare(tmp_path)
    for index in range(40):
        (tmp_path / "samples" / str(uuid5(NAMESPACE_URL, f"r{index}"))).mkdir()

    assert lanes.route(tmp_path, claim("sample")) == "sample"
    assert lanes.registered_lanes(tmp_path) == {CLAIM_UUID: "sample"}
    assert (tmp_path / lanes.LANES_DIR / f"{CLAIM_UUID}.yaml").read_text(encoding="utf-8") == (
        f"uuid: {CLAIM_UUID}\ntask_lane: sample\nslot: 1\nbatch: {BATCH}\nrun_id: {RUN}\n"
    )


def test_route_registers_a_starter(tmp_path: Path) -> None:
    prepare(tmp_path)

    assert lanes.route(tmp_path, claim("starter")) == "starter"


def test_route_refuses_a_delivery_claim_because_overflow_is_decided_at_merge(
    tmp_path: Path,
) -> None:
    prepare(tmp_path)

    refused = assert_refused(tmp_path, "delivery", "invalid-claim")

    assert refused.detail == "claim field task_lane is outside its closed form"


def test_delivery_ceiling_is_ten_thousand() -> None:
    assert lanes.DELIVERY_CEILING == 10000
    assert lanes.LANE_CEILINGS == {"samples": 30, "delivery": 10000}


# ---- immutability and idempotence ----


@bite("forge.md:F46")
def test_route_refuses_a_lane_change_for_a_registered_uuid(tmp_path: Path) -> None:
    prepare(tmp_path)
    lanes.route(tmp_path, claim("starter"))

    refused = assert_refused(tmp_path, "sample", "lane-immutable")

    assert refused.detail == f"uuid {CLAIM_UUID} is already registered as starter"


def test_route_is_idempotent_for_a_registered_uuid(tmp_path: Path) -> None:
    prepare(tmp_path)
    lanes.route(tmp_path, claim("sample"))
    path = tmp_path / lanes.LANES_DIR / f"{CLAIM_UUID}.yaml"
    before = path.read_bytes()

    assert lanes.route(tmp_path, claim("sample", slot=7)) == "sample"
    assert path.read_bytes() == before


def test_route_returns_the_registered_lane_after_placement(tmp_path: Path) -> None:
    prepare(tmp_path)
    lanes.route(tmp_path, claim("sample"))
    (tmp_path / "staging" / CLAIM_UUID).rename(tmp_path / "samples" / CLAIM_UUID)

    assert lanes.route(tmp_path, claim("sample")) == "sample"


# ---- registry bytes ----


def test_registered_lanes_reads_legacy_registry_and_per_uuid_files(tmp_path: Path) -> None:
    prepare(tmp_path)
    legacy = tmp_path / lanes.LEGACY_LANES_PATH
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        f"lanes:\n  - uuid: {OTHER_UUID}\t# comment\n\n    task_lane: delivery\n", encoding="utf-8"
    )

    lanes.route(tmp_path, claim("sample"))

    assert lanes.registered_lanes(tmp_path) == {OTHER_UUID: "delivery", CLAIM_UUID: "sample"}


@pytest.mark.parametrize(
    "body",
    [
        f"lanes:\n  - uuid: {OTHER_UUID}\n",
        f"lanes:\n  - uuid: {OTHER_UUID}\n    task_lane: sample\n    task_lane: sample\n",
        f"lanes:\n  - uuid: {OTHER_UUID}\n    task_lane: elsewhere\n",
        f"lanes:\n  - uuid: {OTHER_UUID}\n    task_lane: sample\n  - uuid: {OTHER_UUID}\n"
        "    task_lane: delivery\n",
        b"lanes:\n\xff\n",
    ],
)
def test_route_refuses_an_unreadable_legacy_registry(tmp_path: Path, body: str | bytes) -> None:
    prepare(tmp_path)
    registry = tmp_path / lanes.LEGACY_LANES_PATH
    registry.parent.mkdir(parents=True)
    if isinstance(body, bytes):
        registry.write_bytes(body)
    else:
        registry.write_text(body, encoding="utf-8")

    assert_refused(tmp_path, "sample", "registry-unreadable")


@pytest.mark.parametrize(
    "body",
    [
        f"uuid: {OTHER_UUID}\ntask_lane: elsewhere\n",
        f"uuid: {CLAIM_UUID}\ntask_lane: sample\n",
        "task_lane: sample\n",
        b"\xff",
    ],
)
def test_route_refuses_an_unreadable_per_uuid_record(tmp_path: Path, body: str | bytes) -> None:
    prepare(tmp_path)
    record = tmp_path / lanes.LANES_DIR / f"{OTHER_UUID}.yaml"
    record.parent.mkdir(parents=True)
    if isinstance(body, bytes):
        record.write_bytes(body)
    else:
        record.write_text(body, encoding="utf-8")

    assert_refused(tmp_path, "sample", "registry-unreadable")


def test_conflicting_legacy_and_per_uuid_lanes_are_unreadable(tmp_path: Path) -> None:
    prepare(tmp_path)
    legacy = tmp_path / lanes.LEGACY_LANES_PATH
    legacy.parent.mkdir(parents=True)
    legacy.write_text(f"lanes:\n  - uuid: {OTHER_UUID}\n    task_lane: sample\n", encoding="utf-8")
    record = tmp_path / lanes.LANES_DIR / f"{OTHER_UUID}.yaml"
    record.parent.mkdir(parents=True)
    record.write_text(f"uuid: {OTHER_UUID}\ntask_lane: starter\n", encoding="utf-8")

    assert_refused(tmp_path, "sample", "registry-unreadable")


def test_route_refuses_when_the_registry_cannot_be_written(tmp_path: Path) -> None:
    prepare(tmp_path)
    seed = tmp_path / ".seed"
    seed.mkdir()
    seed.chmod(0o500)
    try:
        assert_refused(tmp_path, "sample", "registry-write-failed")
    finally:
        seed.chmod(0o700)
    assert not (tmp_path / lanes.LANES_DIR).exists()


# ---- claim and residency shape ----


@pytest.mark.parametrize(
    ("invalid", "field"),
    [
        (lanes.LaneClaim("11111111-2222-4333-8444-555555555555", "sample", 1, BATCH, RUN), "uuid"),
        (lanes.LaneClaim(CLAIM_UUID.upper(), "sample", 1, BATCH, RUN), "uuid"),
        (lanes.LaneClaim(CLAIM_UUID, "elsewhere", 1, BATCH, RUN), "task_lane"),
        (lanes.LaneClaim(CLAIM_UUID, "sample", 0, BATCH, RUN), "slot"),
        (lanes.LaneClaim(CLAIM_UUID, "sample", 1, "", RUN), "batch"),
        (lanes.LaneClaim(CLAIM_UUID, "sample", 1, "batch one", RUN), "batch"),
        (lanes.LaneClaim(CLAIM_UUID, "sample", 1, "x" * 65, RUN), "batch"),
        (lanes.LaneClaim(CLAIM_UUID, "sample", 1, BATCH, ""), "run_id"),
        (lanes.LaneClaim(CLAIM_UUID, "sample", 1, BATCH, "bad run"), "run_id"),
    ],
)
def test_route_refuses_an_invalid_claim(
    tmp_path: Path, invalid: lanes.LaneClaim, field: str
) -> None:
    prepare(tmp_path)

    with pytest.raises(lanes.RouteError) as refused:
        lanes.route(tmp_path, invalid)

    assert refused.value.code == "invalid-claim"
    assert refused.value.detail == f"claim field {field} is outside its closed form"


@pytest.mark.parametrize("state", ["absent", "placed", "symlink", "both"])
def test_route_refuses_a_bundle_that_is_not_staged(tmp_path: Path, state: str) -> None:
    (tmp_path / "samples").mkdir()
    (tmp_path / "delivery").mkdir()
    match state:
        case "absent":
            (tmp_path / "staging").mkdir()
        case "placed":
            (tmp_path / "staging").mkdir()
            (tmp_path / "samples" / CLAIM_UUID).mkdir()
        case "symlink":
            (tmp_path / "staging").mkdir()
            (tmp_path / "staging" / CLAIM_UUID).symlink_to(tmp_path / "samples")
        case "both":
            stage(tmp_path, CLAIM_UUID)
            (tmp_path / "delivery" / CLAIM_UUID).mkdir()
        case _:
            raise AssertionError(state)

    assert_refused(tmp_path, "sample", "not-staged")


def test_every_route_code_renders_from_the_detail_table() -> None:
    assert set(lanes.ROUTE_DETAILS) == lanes.ROUTE_CODES
