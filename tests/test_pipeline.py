from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from string import Formatter
from uuid import NAMESPACE_URL, uuid5

import pytest
from tools import lanes, pipeline, reports
from tools import runs as runs_module
from tools._findings import Finding
from tools.bundle_identity import BundleIdentityError

from tests.bite_shared.registration import bite
from tests.parent_fixtures import write_lane_registry

ROOT = Path(__file__).parents[1]
UUID_A = "11111111-2222-4333-8444-555555555555"
UUID_B = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def make_bundle(root: Path, uuid: str, marker: str = "one", lane: str = "staging") -> Path:
    bundle = root / lane / uuid
    (bundle / "tests").mkdir(parents=True, exist_ok=True)
    (bundle / "task.toml").write_text(f'name = "{marker}"\n', encoding="utf-8")
    (bundle / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    return bundle


def write_verdict(root: Path, uuid: str, digest: str) -> Path:
    verdicts = root / ".audit" / "verdicts"
    verdicts.mkdir(parents=True, exist_ok=True)
    path = verdicts / f"{uuid}.json"
    path.write_text(json.dumps({"uuid": uuid, "bundle_digest": digest}), encoding="utf-8")
    return path


def verdict_path_at(root: Path, uuid: str) -> Path:
    digest = pipeline.sealed_records(root)[uuid]["bundle_digest"]
    return root / pipeline.VERDICTS_DIR / uuid / f"{digest}.json"


def codes(findings: list[Finding]) -> list[str]:
    return sorted(finding.code for finding in findings)


def fresh_uuid(index: int) -> str:
    return f"{index:08x}-0000-4000-8000-{index:012x}"


# ---- digest ----


def test_bundle_digest_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    first = pipeline.bundle_digest(tmp_path / pipeline.STAGING_DIR / UUID_A)
    assert first == pipeline.bundle_digest(tmp_path / pipeline.STAGING_DIR / UUID_A)
    make_bundle(tmp_path, UUID_A, marker="two")
    assert first != pipeline.bundle_digest(tmp_path / pipeline.STAGING_DIR / UUID_A)


def test_bundle_digest_refuses_missing_bundle(tmp_path: Path) -> None:
    with pytest.raises(pipeline.PipelineError):
        pipeline.bundle_digest(tmp_path / pipeline.STAGING_DIR / UUID_A)


def test_bundle_digest_refuses_symlink_and_binds_executable_bit(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path, UUID_A)
    first = pipeline.bundle_digest(bundle)
    (bundle / "tests" / "test.sh").chmod(0o755)
    assert pipeline.bundle_digest(bundle) != first
    (bundle / "escape").symlink_to(tmp_path / "outside")
    with pytest.raises(pipeline.PipelineError, match="symbolic link"):
        pipeline.bundle_digest(bundle)


# ---- seal and chain ----


def test_seal_appends_chained_record_and_verify_is_clean(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    lines = (tmp_path / pipeline.QUEUE_DIR / "forge-1.jsonl").read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["seq"] == 1
    assert entry["bundle_digest"] == digest
    assert entry["prev_hash"] == pipeline.GENESIS_HASH
    assert entry["entry_hash"] == pipeline.chain_digest(entry)
    assert pipeline.verify(tmp_path, NOW) == []
    assert pipeline.pending(tmp_path) == [UUID_A]


def test_seal_links_second_record_to_first(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    make_bundle(tmp_path, UUID_B)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.seal(tmp_path, UUID_B, "forge-1", NOW)
    _, records = pipeline.walk_queue(tmp_path)
    assert records[1]["prev_hash"] == records[0]["entry_hash"]
    assert records[1]["seq"] == 2


def test_seal_refuses_duplicate_digest_and_bad_inputs(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    with pytest.raises(pipeline.PipelineError, match="already sealed"):
        pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    with pytest.raises(pipeline.PipelineError, match="uuid"):
        pipeline.seal(tmp_path, "not-a-uuid", "forge-1", NOW)
    with pytest.raises(pipeline.PipelineError, match="run id"):
        pipeline.seal(tmp_path, UUID_B, "", NOW)


@bite("forge.md:F82")
@pytest.mark.parametrize("claimed", [False, True])
def test_seal_refuses_reseal_before_verdict(tmp_path: Path, claimed: bool) -> None:
    # Given a frozen bundle, with or without an auditor's claim.
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    if claimed:
        pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    queue = pipeline.stream_path(tmp_path, "forge-1")
    before = queue.read_bytes()
    make_bundle(tmp_path, UUID_A, marker="two")

    # When the same producer tries to reseal changed bytes.
    with pytest.raises(pipeline.PipelineError, match="frozen until a verdict lands"):
        pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)

    # Then the seal is unchanged and the public buckets still identify frozen work.
    assert queue.read_bytes() == before
    shown = pipeline.status(tmp_path, NOW)
    assert shown["pending"] == [UUID_A]
    assert shown["claimed"] == ([UUID_A] if claimed else [])
    assert shown["findings"] == ["PIPELINE_SEALED_MUTATED"]


@pytest.mark.parametrize("changed", [False, True])
def test_seal_refuses_retained_uuid(tmp_path: Path, changed: bool) -> None:
    # Given a retained predecessor, regardless of whether its bytes were edited.
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    pipeline.verdict(tmp_path, UUID_A, "retained", "crucible-1", NOW)
    if changed:
        make_bundle(tmp_path, UUID_A, marker="two")

    # When resealing that uuid, then a new successor uuid is required.
    with pytest.raises(pipeline.PipelineError, match="was retained; author a successor"):
        pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)


@pytest.mark.parametrize("changed", [False, True])
def test_seal_refuses_clean_uuid(tmp_path: Path, changed: bool) -> None:
    # Given a clean bundle awaiting placement.
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)
    if changed:
        make_bundle(tmp_path, UUID_A, marker="two")

    # When resealing that uuid, then placement rather than rework is required.
    with pytest.raises(pipeline.PipelineError, match="was judged clean; place it, never reseal"):
        pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)


@bite("crucible.md:Q1")
def test_verify_flags_reworked_sealed_bundle(tmp_path: Path) -> None:
    # Given sealed bytes changed before the auditor recorded a verdict.
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    make_bundle(tmp_path, UUID_A, marker="two")

    # When the pipeline verifies the staged bundle.
    findings = pipeline.verify(tmp_path, NOW)

    # Then the existing refusal identifies premature rework, not a reseal remedy.
    assert codes(findings) == ["PIPELINE_SEALED_MUTATED"]
    assert "reworked before its verdict" in findings[0].message


def test_cli_refuses_reseal_before_verdict(tmp_path: Path) -> None:
    # Given a changed sealed bundle on the real CLI's project surface.
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    make_bundle(tmp_path, UUID_A, marker="two")

    # When the author invokes seal again.
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/pipeline.py"),
            "seal",
            "./",
            UUID_A,
            "--run-id",
            "forge-1",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    # Then the process refuses rather than publishing a replacement seal.
    assert result.returncode == 1
    assert "frozen until a verdict lands" in result.stderr


@bite("shared.md:A19")
def test_chain_broken_on_tampered_line(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    make_bundle(tmp_path, UUID_B)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.seal(tmp_path, UUID_B, "forge-1", NOW)
    queue = pipeline.stream_path(tmp_path, "forge-1")
    lines = queue.read_text().splitlines()
    entry = json.loads(lines[0])
    entry["producer_run_id"] = "someone-else"
    lines[0] = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    queue.write_text("\n".join(lines) + "\n")
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_CHAIN_BROKEN"]
    with pytest.raises(pipeline.PipelineError):
        pipeline.pending(tmp_path)


def test_chain_broken_on_rollback(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    make_bundle(tmp_path, UUID_B)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.seal(tmp_path, UUID_B, "forge-1", NOW)
    queue = pipeline.stream_path(tmp_path, "forge-1")
    lines = queue.read_text().splitlines()
    queue.write_text(lines[1] + "\n")
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_CHAIN_BROKEN"]


def test_chain_broken_on_unknown_field_and_bad_json(tmp_path: Path) -> None:
    queue = tmp_path / ".podium" / "queue.jsonl"
    queue.parent.mkdir(parents=True)
    queue.write_text("{not json}\n")
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_CHAIN_BROKEN"]
    make_bundle(tmp_path, UUID_A)
    queue.unlink()
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    queue = pipeline.stream_path(tmp_path, "forge-1")
    entry = json.loads(queue.read_text().splitlines()[0])
    entry["finding"] = "must never travel here"
    entry["entry_hash"] = pipeline.chain_digest(entry)
    queue.write_text(json.dumps(entry, sort_keys=True) + "\n")
    findings = pipeline.verify(tmp_path, NOW)
    assert codes(findings) == ["PIPELINE_CHAIN_BROKEN"]
    assert "unknown field finding" in findings[0].message


# ---- mutation and unsealed audit ----


@bite("shared.md:A20")
def test_sealed_mutated_fires_and_claim_refuses(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    (tmp_path / pipeline.STAGING_DIR / UUID_A / "tests" / "conftest.py").write_text("x = 1\n")
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_SEALED_MUTATED"]
    with pytest.raises(pipeline.PipelineError, match="moved after sealing"):
        pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)


def test_sealed_mutated_fires_when_bundle_deleted(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    for path in sorted((tmp_path / pipeline.STAGING_DIR / UUID_A).rglob("*"), reverse=True):
        path.unlink() if path.is_file() else path.rmdir()
    (tmp_path / pipeline.STAGING_DIR / UUID_A).rmdir()
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_SEALED_MUTATED"]


@bite("shared.md:A21")
def test_unsealed_audit_fires_for_verdict_without_seal(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    write_verdict(tmp_path, UUID_B, "f" * 64)
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_UNSEALED_AUDIT"]


def test_verdict_at_sealed_digest_is_clean_and_clears_pending(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    write_verdict(tmp_path, UUID_A, digest)
    assert pipeline.verify(tmp_path, NOW) == []
    assert pipeline.pending(tmp_path) == []


# ---- claims ----


@bite("shared.md:A23")
def test_second_claim_on_same_uuid_is_refused(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    first = pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    assert first.is_file()
    with pytest.raises(pipeline.PipelineError, match="already claimed"):
        pipeline.claim(tmp_path, UUID_A, "crucible-2", NOW)
    body = json.loads(first.read_text())
    assert body["consumer_run_id"] == "crucible-1"
    pipeline.release_claim(tmp_path, UUID_A)
    assert not first.exists()
    pipeline.claim(tmp_path, UUID_A, "crucible-2", NOW)


def test_claim_refuses_unsealed_uuid_and_empty_run_id(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    with pytest.raises(pipeline.PipelineError, match="never sealed"):
        pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    with pytest.raises(pipeline.PipelineError, match="run id"):
        pipeline.claim(tmp_path, UUID_A, "", NOW)


def test_stale_claim_fires_after_ttl_and_not_before(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    assert pipeline.verify(tmp_path, NOW + timedelta(hours=5)) == []
    assert codes(pipeline.verify(tmp_path, NOW + timedelta(hours=7))) == ["PIPELINE_STALE_CLAIM"]
    write_verdict(tmp_path, UUID_A, digest)
    assert pipeline.verify(tmp_path, NOW + timedelta(hours=7)) == []


def test_claim_on_unsealed_uuid_file_is_unsealed_audit(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    claims = tmp_path / ".audit" / "queue.claims"
    claims.mkdir(parents=True)
    (claims / f"{UUID_B}.json").write_text(
        json.dumps(
            {
                "uuid": UUID_B,
                "bundle_digest": "0" * 64,
                "consumer_run_id": "x",
                "claimed_at": "2026-09-16T00:00:00Z",
            }
        )
    )
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_UNSEALED_AUDIT"]


# ---- backpressure ----


@bite("shared.md:A22")
def test_backpressure_fires_at_thirty_two_and_not_at_thirty_one(tmp_path: Path) -> None:
    assert pipeline.DEFAULT_MAX_UNAUDITED == 31, "one batch: thirty ordinary slots plus an anchor"
    for index in range(1, 32):
        make_bundle(tmp_path, fresh_uuid(index))
        pipeline.seal(tmp_path, fresh_uuid(index), "forge-1", NOW)
    assert pipeline.verify(tmp_path, NOW) == []
    make_bundle(tmp_path, fresh_uuid(32))
    with pytest.raises(pipeline.PipelineError, match="backpressure"):
        pipeline.seal(tmp_path, fresh_uuid(32), "forge-1", NOW)
    # A thirty-second record forced past the producer guard is still refused by verify.
    (tmp_path / ".podium" / "pipeline.json").write_text('{"max_unaudited": 32}')
    pipeline.seal(tmp_path, fresh_uuid(32), "forge-1", NOW)
    (tmp_path / ".podium" / "pipeline.json").unlink()
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_BACKPRESSURE"]


def test_backpressure_clears_when_verdicts_land(tmp_path: Path) -> None:
    (tmp_path / ".podium").mkdir()
    (tmp_path / ".podium" / "pipeline.json").write_text('{"max_unaudited": 2}')
    digests = []
    for index in range(1, 3):
        make_bundle(tmp_path, fresh_uuid(index))
        digests.append(pipeline.seal(tmp_path, fresh_uuid(index), "forge-1", NOW))
    make_bundle(tmp_path, fresh_uuid(3))
    with pytest.raises(pipeline.PipelineError, match="backpressure"):
        pipeline.seal(tmp_path, fresh_uuid(3), "forge-1", NOW)
    write_verdict(tmp_path, fresh_uuid(1), digests[0])
    pipeline.seal(tmp_path, fresh_uuid(3), "forge-1", NOW)
    assert pipeline.verify(tmp_path, NOW) == []


def test_config_invalid_fires(tmp_path: Path) -> None:
    (tmp_path / ".podium").mkdir()
    config = tmp_path / ".podium" / "pipeline.json"
    make_bundle(tmp_path, UUID_A)
    config.write_text('{"max_unaudited": 0}')
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_CONFIG_INVALID"]
    config.write_text('{"surprise": 1}')
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_CONFIG_INVALID"]
    config.write_text('{"claim_ttl_hours": true}')
    assert codes(pipeline.verify(tmp_path, NOW)) == ["PIPELINE_CONFIG_INVALID"]
    config.write_text('{"max_unaudited": 3, "claim_ttl_hours": 1.5}')
    assert pipeline.load_config(tmp_path) == (3, 1.5)


# ---- parent check and CLI ----


def test_check_pipeline_is_silent_without_queue(tmp_path: Path) -> None:
    assert pipeline.check_pipeline(str(tmp_path), NOW) == []
    assert pipeline.CHECKS[0][0] == "check_pipeline"


def test_cli_round_trip(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)

    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "tools" / "pipeline.py"), *arguments],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    sealed = run("seal", "./", UUID_A, "--run-id", "forge-1")
    assert sealed.returncode == 0, sealed.stderr
    digest = sealed.stdout.strip()
    assert len(digest) == 64
    listed = run("pending", "./")
    assert listed.stdout.strip() == UUID_A
    claimed = run("claim", "./", UUID_A, "--run-id", "crucible-1")
    assert claimed.returncode == 0, claimed.stderr
    refused = run("claim", "./", UUID_A, "--run-id", "crucible-2")
    assert refused.returncode == 1
    assert "already claimed" in refused.stderr
    assert run("verify", "./").returncode == 0
    (tmp_path / pipeline.STAGING_DIR / UUID_A / "task.toml").write_text("tampered\n")
    verified = run("verify", "./", "--json")
    assert verified.returncode == 1
    assert json.loads(verified.stdout)[0]["code"] == "PIPELINE_SEALED_MUTATED"
    shown = run("status", "./")
    assert json.loads(shown.stdout)["claimed"] == [UUID_A]


def test_seal_refuses_unstaged_bundle(tmp_path: Path) -> None:
    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    assert str(refused.value) == f"bundle {UUID_A} is not staged"


@pytest.mark.parametrize("lane", ["samples", "delivery"])
@pytest.mark.parametrize("staged", [False, True])
def test_seal_refuses_already_placed_uuid(tmp_path: Path, lane: str, staged: bool) -> None:
    make_bundle(tmp_path, UUID_A, lane=lane)
    if staged:
        make_bundle(tmp_path, UUID_A)

    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    assert str(refused.value) == (
        f"bundle {UUID_A} is already placed; changed bytes make a new uuid"
    )


@pytest.mark.parametrize("outcome", ["clean", "retained"])
def test_verdict_writes_outcome_and_keeps_claim(tmp_path: Path, outcome: str) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    claim_path = pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)

    result = pipeline.verdict(tmp_path, UUID_A, outcome, "crucible-1", NOW)

    assert result == tmp_path / pipeline.VERDICTS_DIR / UUID_A / f"{digest}.json"
    expected = {
        "uuid": UUID_A,
        "bundle_digest": digest,
        "outcome": outcome,
        "consumer_run_id": "crucible-1",
    }
    assert result.read_text().strip() == json.dumps(expected, sort_keys=True, separators=(",", ":"))
    assert claim_path.exists(), "the owning claim stays as the ownership record"
    assert pipeline.pending(tmp_path) == []
    assert list(result.parent.iterdir()) == [result]


@pytest.mark.parametrize("claimed", [False, True])
def test_verdict_refuses_unclaimed_or_foreign_claim(tmp_path: Path, claimed: bool) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    if claimed:
        pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)

    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.verdict(tmp_path, UUID_A, "clean", "other", NOW)
    assert str(refused.value) == (
        f"claim on {UUID_A} belongs to another consumer"
        if claimed
        else f"bundle {UUID_A} is not claimed"
    )
    assert not (tmp_path / pipeline.VERDICTS_DIR / UUID_A).exists()


@bite("shared.md:A42")
def test_verdict_refuses_stale_claim_after_reseal(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    claim_path = pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    make_bundle(tmp_path, UUID_A, marker="two")
    write_stream_record(
        tmp_path,
        "forge-1",
        UUID_A,
        pipeline.bundle_digest(tmp_path / "staging" / UUID_A),
        "2026-09-16T12:00:01Z",
    )

    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)
    assert str(refused.value) == f"claim on {UUID_A} is stale; the bundle was resealed"
    assert claim_path.exists()


@pytest.mark.parametrize("outcome", ["clean", "invalid"])
def test_verdict_refuses_moved_bytes_and_bad_outcome(tmp_path: Path, outcome: str) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    make_bundle(tmp_path, UUID_A, marker="two")

    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.verdict(tmp_path, UUID_A, outcome, "crucible-1", NOW)
    assert str(refused.value) == (
        f"bundle {UUID_A} bytes moved after sealing; refuse to record a verdict"
        if outcome == "clean"
        else "outcome must be clean or retained"
    )


@pytest.mark.parametrize("resealed", [False, True])
def test_verdict_refuses_duplicate_at_same_digest_but_supersedes_older(
    tmp_path: Path, resealed: bool
) -> None:
    make_bundle(tmp_path, UUID_A)
    first = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    if resealed:
        previous = write_verdict(tmp_path, UUID_A, first)
        make_bundle(tmp_path, UUID_A, marker="two")
        write_stream_record(
            tmp_path,
            "forge-1",
            UUID_A,
            pipeline.bundle_digest(tmp_path / "staging" / UUID_A),
            "2026-09-16T12:00:01Z",
        )
        claim_path = pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    else:
        claim_path = pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
        previous = write_verdict(tmp_path, UUID_A, first)
    before = previous.read_bytes()

    if resealed:
        result = pipeline.verdict(tmp_path, UUID_A, "retained", "crucible-1", NOW)
        assert json.loads(result.read_text()) == {
            "uuid": UUID_A,
            "bundle_digest": pipeline.bundle_digest(tmp_path / pipeline.STAGING_DIR / UUID_A),
            "outcome": "retained",
            "consumer_run_id": "crucible-1",
        }
    else:
        with pytest.raises(pipeline.PipelineError) as refused:
            pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)
        assert str(refused.value) == f"verdict for {UUID_A} already exists at this digest"
        assert previous.read_bytes() == before
        assert claim_path.exists()


@pytest.mark.parametrize("lane", ["samples", "delivery"])
def test_verify_locates_sealed_bundle_after_it_left_staging(tmp_path: Path, lane: str) -> None:
    bundle = make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)
    target = tmp_path / lane / UUID_A
    target.parent.mkdir()
    os.rename(bundle, target)  # noqa: PTH104 - exercise the placement primitive without copying.

    assert pipeline.verify(tmp_path, NOW) == []
    assert pipeline.bundle_digest(target) == digest
    with pytest.raises(pipeline.PipelineError, match="already judged"):
        pipeline.claim(tmp_path, UUID_A, "crucible-2", NOW)


@pytest.mark.parametrize("lane", ["samples", "delivery"])
def test_verify_reports_bundle_under_two_roots(tmp_path: Path, lane: str) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    make_bundle(tmp_path, UUID_A, lane=lane)

    findings = pipeline.verify(tmp_path, NOW)

    assert codes(findings) == ["PIPELINE_SEALED_MUTATED"]
    assert "resident under more than one root" in findings[0].message
    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    assert str(refused.value) == f"bundle {UUID_A} is resident under more than one root"


@pytest.mark.parametrize("state", ["absent", "present", "mutated", "stale", "symlink", "file"])
def test_verify_skips_only_absent_retained_bundle(tmp_path: Path, state: str) -> None:
    bundle = make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    pipeline.verdict(tmp_path, UUID_A, "retained", "crucible-1", NOW)
    if state in {"mutated", "stale"}:
        make_bundle(tmp_path, UUID_A, marker="two")
    if state == "stale":
        write_stream_record(
            tmp_path,
            "forge-1",
            UUID_A,
            pipeline.bundle_digest(bundle),
            "2026-09-16T12:00:01Z",
        )
    if state not in {"present", "mutated"}:
        shutil.rmtree(bundle)
    if state == "symlink":
        bundle.symlink_to(tmp_path / "missing")
    if state == "file":
        bundle.write_text("not a bundle")

    findings = pipeline.verify(tmp_path, NOW)

    assert codes(findings) == (
        [] if state in {"absent", "present"} else ["PIPELINE_SEALED_MUTATED"]
    )
    if state in {"symlink", "file"}:
        assert f"unsafe object at {bundle}" in findings[0].message
    if state == "stale":
        assert "missing" in findings[0].message


@pytest.mark.parametrize("outcome", ["clean", "retained"])
def test_verify_accepts_trajectory_residue_only_after_retained_verdict(
    tmp_path: Path, outcome: str
) -> None:
    # Given a judged predecessor reduced to its preserved rollout evidence.
    bundle = make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    pipeline.verdict(tmp_path, UUID_A, outcome, "crucible-1", NOW)
    shutil.rmtree(bundle / "tests")
    (bundle / "task.toml").unlink()
    (bundle / "trajectories").mkdir()
    (bundle / "trajectories/run.json").write_text('{"evidence": "preserved"}\n')
    make_bundle(tmp_path, UUID_B, marker="successor")
    pipeline.seal(tmp_path, UUID_B, "forge-2", NOW)

    # When the pipeline verifies the predecessor beside a newly sealed successor.
    findings = pipeline.verify(tmp_path, NOW)

    # Then only a retained verdict permits trajectory-only residue.
    assert codes(findings) == ([] if outcome == "retained" else ["PIPELINE_SEALED_MUTATED"])


def test_legacy_verdict_without_outcome_still_clears_pending(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    write_verdict(tmp_path, UUID_A, digest)

    assert pipeline.pending(tmp_path) == []
    assert pipeline._read_verdict(tmp_path, UUID_A) == {"uuid": UUID_A, "bundle_digest": digest}


@pytest.mark.parametrize("lane", ["staging", "samples", "delivery"])
@pytest.mark.parametrize("kind", ["dir", "file", "symlink", "dangling", "fifo"])
def test_occupancy_classifies_objects_without_following_links(
    tmp_path: Path, lane: str, kind: str
) -> None:
    path = tmp_path / lane / UUID_A
    path.parent.mkdir()
    if kind == "dir":
        path.mkdir()
    elif kind == "file":
        path.write_text("bytes")
    elif kind in {"symlink", "dangling"}:
        path.symlink_to(tmp_path if kind == "symlink" else tmp_path / "absent")
    else:
        os.mkfifo(path)

    assert pipeline._occupancy(tmp_path, UUID_A) == [(path, "dir" if kind == "dir" else "unsafe")]
    if kind == "dir":
        assert pipeline._bundle_path(tmp_path, UUID_A) == path
    else:
        with pytest.raises(pipeline.PipelineError) as refused:
            pipeline._bundle_homes(tmp_path, UUID_A)
        assert str(refused.value) == f"bundle {UUID_A} has an unsafe object at {path}"


def test_bundle_path_refuses_absence(tmp_path: Path) -> None:
    assert pipeline._occupancy(tmp_path, UUID_A) == []
    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline._bundle_path(tmp_path, UUID_A)
    assert str(refused.value) == f"bundle {UUID_A} is absent from staging/, samples/, and delivery/"


@pytest.mark.parametrize(
    "payload",
    [
        "{",
        "[]",
        "null",
        "{}",
        json.dumps({"uuid": UUID_B, "bundle_digest": "a" * 64}),
        json.dumps({"uuid": UUID_A, "bundle_digest": "A" * 64}),
        json.dumps({"uuid": UUID_A, "bundle_digest": "a" * 63}),
        json.dumps({"uuid": UUID_A, "bundle_digest": 3}),
        json.dumps({"uuid": UUID_A, "bundle_digest": "a" * 64, "outcome": None}),
        json.dumps({"uuid": UUID_A, "bundle_digest": "a" * 64, "outcome": "invalid"}),
        json.dumps({"uuid": UUID_A, "bundle_digest": "a" * 64, "finding": "private"}),
    ],
)
def test_read_verdict_rejects_invalid_payload(tmp_path: Path, payload: str) -> None:
    path = write_verdict(tmp_path, UUID_A, "a" * 64)
    path.write_text(payload)

    assert pipeline._read_verdict(tmp_path, UUID_A) is None
    assert pipeline._read_verdict_digest(tmp_path, UUID_A) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("uuid", UUID_B),
        ("bundle_digest", "A" * 64),
        ("bundle_digest", "a" * 63),
        ("claimed_at", "invalid"),
        ("claimed_at", "2026-09-16T12:00:00"),
        ("consumer_run_id", 3),
        ("extra", "private"),
    ],
)
def test_read_claim_rejects_invalid_fields(tmp_path: Path, field: str, value: str | int) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    path = pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    raw = json.loads(path.read_text())
    raw[field] = value
    path.write_text(json.dumps(raw))

    assert pipeline._read_claim(tmp_path, UUID_A) is None
    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)
    assert str(refused.value) == f"bundle {UUID_A} is not claimed"


@pytest.mark.parametrize("payload", ["{", "[]", "null", "{}"])
def test_read_claim_rejects_invalid_shape(tmp_path: Path, payload: str) -> None:
    path = tmp_path / pipeline.CLAIMS_DIR / f"{UUID_A}.json"
    path.parent.mkdir(parents=True)
    path.write_text(payload)

    assert pipeline._read_claim(tmp_path, UUID_A) is None


@pytest.mark.parametrize("outcome", ["invalid", "clean"])
def test_verdict_refuses_bad_outcome_before_unsealed_bundle(tmp_path: Path, outcome: str) -> None:
    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.verdict(tmp_path, UUID_A, outcome, "crucible-1", NOW)
    assert str(refused.value) == (
        "outcome must be clean or retained"
        if outcome == "invalid"
        else f"bundle {UUID_A} was never sealed"
    )


@pytest.mark.parametrize("consumer", ["crucible-1", "other"])
def test_cli_verdict_round_trip(tmp_path: Path, consumer: str) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    claim_path = pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)

    result = subprocess.run(
        [
            sys.executable,
            "./trinity/tools/pipeline.py",
            "verdict",
            "./",
            UUID_A,
            "--outcome",
            "clean",
            "--run-id",
            consumer,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    path = verdict_path_at(tmp_path, UUID_A)
    if consumer == "crucible-1":
        assert result.returncode == 0, result.stderr
        assert json.loads(path.read_text())["outcome"] == "clean"
        assert claim_path.exists()
    else:
        assert result.returncode == 1
        assert result.stderr == f"refused: claim on {UUID_A} belongs to another consumer\n"
        assert not path.exists()
        assert claim_path.exists()


@pytest.mark.parametrize("consumer", ["crucible-1", "other"])
def test_verdict_checks_claim_before_current_bytes(tmp_path: Path, consumer: str) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    make_bundle(tmp_path, UUID_A, marker="two")
    second = pipeline.bundle_digest(tmp_path / "staging" / UUID_A)
    write_stream_record(tmp_path, "forge-1", UUID_A, second, "2026-09-16T12:00:01Z")
    write_verdict(tmp_path, UUID_A, second)
    make_bundle(tmp_path, UUID_A, marker="three")

    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.verdict(tmp_path, UUID_A, "clean", consumer, NOW)

    assert str(refused.value) == (
        f"claim on {UUID_A} is stale; the bundle was resealed"
        if consumer == "crucible-1"
        else f"bundle {UUID_A} is not claimed"
    )


def test_verdict_checks_current_bytes_before_duplicate(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    write_verdict(tmp_path, UUID_A, digest)
    make_bundle(tmp_path, UUID_A, marker="two")

    with pytest.raises(pipeline.PipelineError) as refused:
        pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)

    assert str(refused.value) == (
        f"bundle {UUID_A} bytes moved after sealing; refuse to record a verdict"
    )


@pytest.mark.parametrize("outcome", ["clean", "legacy", "missing"])
def test_verify_refuses_absence_without_matching_retained_verdict(
    tmp_path: Path, outcome: str
) -> None:
    bundle = make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    if outcome == "clean":
        pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
        pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)
    if outcome == "legacy":
        write_verdict(tmp_path, UUID_A, digest)
    shutil.rmtree(bundle)

    findings = pipeline.verify(tmp_path, NOW)

    assert codes(findings) == ["PIPELINE_SEALED_MUTATED"]
    assert "missing" in findings[0].message


def test_verify_prioritizes_unsafe_object_over_multiple_homes(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    make_bundle(tmp_path, UUID_A, lane="samples")
    unsafe = tmp_path / "delivery" / UUID_A
    unsafe.parent.mkdir()
    unsafe.symlink_to(tmp_path / "missing")

    findings = pipeline.verify(tmp_path, NOW)

    assert codes(findings) == ["PIPELINE_SEALED_MUTATED"]
    assert f"unsafe object at {unsafe}" in findings[0].message


LANE_REFUSALS = (
    "registry missing or unreadable",
    "no row names the uuid",
    "no task_lane in the row",
    "more than one task_lane in a row",
    "rows disagree on task_lane",
    'task_lane "unknown" is outside starter, sample, delivery',
)
REFUSAL_CASES = (
    "queue-broken",
    "unsealed",
    "multi-root",
    "absent",
    "bundle-unreadable",
    "staged-digest-mismatch",
    "verdict-missing",
    "verdict-digest-mismatch",
    "verdict-legacy",
    "retained",
    "lane-root-missing",
    "cross-device",
    "rename-failed",
    "post-rename-digest-drift",
    *(f"lane-{index}" for index in range(6)),
)


def prepare_placement(root: Path, lane: str = "sample", outcome: str = "clean") -> Path:
    bundle = make_bundle(root, UUID_A)
    (root / "samples").mkdir(exist_ok=True)
    (root / "delivery").mkdir(exist_ok=True)
    write_lane_registry(root, [(UUID_A, lane)])
    pipeline.seal(root, UUID_A, "forge-1", NOW)
    pipeline.claim(root, UUID_A, "crucible-1", NOW)
    pipeline.verdict(root, UUID_A, outcome, "crucible-1", NOW)
    return bundle


def placement_refusal(root: Path, case: str, monkeypatch: pytest.MonkeyPatch) -> str:
    bundle = prepare_placement(root)
    verdict_path = verdict_path_at(root, UUID_A)
    registry = root / ".seed/lanes.yaml"
    match case:
        case "queue-broken":
            pipeline.stream_path(root, "forge-1").write_text("private chain failure\n")
        case "unsealed":
            pipeline.stream_path(root, "forge-1").unlink()
        case "multi-root":
            make_bundle(root, UUID_A, lane="samples")
        case "absent":
            shutil.rmtree(bundle)
        case "bundle-unreadable":
            shutil.rmtree(bundle)
            bundle.symlink_to(root / "missing")
        case "staged-digest-mismatch":
            make_bundle(root, UUID_A, marker="changed")
        case "verdict-missing":
            verdict_path.unlink()
        case "verdict-digest-mismatch":
            body = json.loads(verdict_path.read_text())
            body["bundle_digest"] = "f" * 64
            verdict_path.unlink()
            (verdict_path.parent / f"{'f' * 64}.json").write_text(json.dumps(body))
        case "verdict-legacy":
            verdict_path.unlink()
            write_verdict(root, UUID_A, pipeline.bundle_digest(bundle))
        case "retained":
            body = json.loads(verdict_path.read_text())
            body["outcome"] = "retained"
            verdict_path.write_text(json.dumps(body))
        case "lane-root-missing":
            (root / "samples").rmdir()
        case "cross-device" | "rename-failed":

            def refuse_rename(_source: Path, _destination: Path) -> None:
                number = errno.EXDEV if case == "cross-device" else errno.EACCES
                raise OSError(number, "private operating system detail")

            monkeypatch.setattr(os, "rename", refuse_rename)
        case "post-rename-digest-drift":
            original = pipeline.bundle_digest

            def drifting_digest(path: Path) -> str:
                return original(path) if path == bundle else "f" * 64

            monkeypatch.setattr(pipeline, "bundle_digest", drifting_digest)
        case "lane-0":
            registry.unlink()
        case "lane-1":
            registry.write_text(registry.read_text().replace(UUID_A, UUID_B))
        case "lane-2":
            registry.write_text(registry.read_text().replace("    task_lane: sample\n", ""))
        case "lane-3":
            registry.write_text(registry.read_text() + "    task_lane: sample\n")
        case "lane-4":
            write_lane_registry(root, [(UUID_A, "delivery")])
        case "lane-5":
            registry.write_text(
                registry.read_text().replace("task_lane: sample", "task_lane: unknown")
            )
        case _:
            raise AssertionError(f"unknown refusal fixture: {case}")
    return "lane-unresolved" if case.startswith("lane-") and case[-1].isdigit() else case


def assert_place_refused(root: Path, code: str) -> pipeline.PlaceError:
    with pytest.raises(pipeline.PlaceError) as refused:
        pipeline.place(root, UUID_A, NOW)
    assert refused.value.code == code
    assert refused.value.code in pipeline.PLACE_CODES
    assert str(refused.value) == f"{code}: {refused.value.detail}"
    return refused.value


def test_place_renames_clean_staged_bundle_to_samples(tmp_path: Path) -> None:
    staged = prepare_placement(tmp_path)
    inode = staged.stat().st_ino
    digest = pipeline.bundle_digest(staged)

    result = pipeline.place(tmp_path, UUID_A, NOW)

    target = tmp_path / "samples" / UUID_A
    assert result == ("placed", target)
    assert target.stat().st_ino == inode
    assert pipeline.bundle_digest(target) == digest
    assert not staged.exists()


def test_place_routes_delivery_lane(tmp_path: Path) -> None:
    prepare_placement(tmp_path, "delivery")

    result = pipeline.place(tmp_path, UUID_A, NOW)

    assert result == ("placed", tmp_path / "delivery" / UUID_A)


def test_place_routes_starter_to_samples(tmp_path: Path) -> None:
    prepare_placement(tmp_path, "starter")

    result = pipeline.place(tmp_path, UUID_A, NOW)

    assert result == ("placed", tmp_path / "samples" / UUID_A)


def test_cli_route_round_trip(tmp_path: Path) -> None:
    routed = str(uuid5(NAMESPACE_URL, "routed"))
    make_bundle(tmp_path, routed)
    (tmp_path / "samples").mkdir()
    (tmp_path / "delivery").mkdir()
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)
    argv = [sys.executable, "./trinity/tools/pipeline.py", "route", "./", routed]
    bound = ["--lane", "sample", "--slot", "1", "--batch", "batch-0001", "--run-id", "forge-ada"]

    accepted = subprocess.run(
        [*argv, *bound], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    repeated = subprocess.run(
        [*argv, *bound], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    changed = subprocess.run(
        [
            *argv,
            "--lane",
            "starter",
            "--slot",
            "1",
            "--batch",
            "batch-0001",
            "--run-id",
            "forge-ada",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    for result in (accepted, repeated):
        assert result.returncode == 0, result.stderr
        assert result.stdout == "sample\n"
        assert result.stderr == ""
    assert changed.returncode == 1
    assert changed.stdout == ""
    assert changed.stderr == (
        f"refused: lane-immutable: uuid {routed} is already registered as sample\n"
    )
    assert (tmp_path / ".seed" / "lanes" / f"{routed}.yaml").read_text(encoding="utf-8") == (
        f"uuid: {routed}\ntask_lane: sample\nslot: 1\nbatch: batch-0001\nrun_id: forge-ada\n"
    )


def test_place_is_idempotent_on_already_placed_uuid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare_placement(tmp_path)
    first = pipeline.place(tmp_path, UUID_A, NOW)
    before = {path: path.stat().st_mtime_ns for path in tmp_path.rglob("*")}

    def refuse_rename(_source: Path, _destination: Path) -> None:
        pytest.fail("an authorized retry must not rename")

    monkeypatch.setattr(os, "rename", refuse_rename)

    second = pipeline.place(tmp_path, UUID_A, NOW)

    assert second == first
    assert {path: path.stat().st_mtime_ns for path in tmp_path.rglob("*")} == before


@pytest.mark.parametrize("outcome", ["missing", "retained"])
@bite("forge.md:F59")
def test_place_refuses_placed_bundle_without_clean_verdict(tmp_path: Path, outcome: str) -> None:
    bundle = prepare_placement(tmp_path, outcome="retained")
    bundle.rename(tmp_path / "samples" / UUID_A)
    if outcome == "missing":
        verdict_path_at(tmp_path, UUID_A).unlink()

    assert_place_refused(tmp_path, "verdict-missing" if outcome == "missing" else "retained")


def test_place_refuses_multi_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = placement_refusal(tmp_path, "multi-root", monkeypatch)
    assert_place_refused(tmp_path, code)


def test_place_refuses_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = placement_refusal(tmp_path, "absent", monkeypatch)
    assert_place_refused(tmp_path, code)


@pytest.mark.parametrize("lane", ["staging", "samples"])
@bite("forge.md:F60")
def test_place_refuses_staged_digest_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lane: str
) -> None:
    code = placement_refusal(tmp_path, "staged-digest-mismatch", monkeypatch)
    if lane == "samples":
        (tmp_path / "staging" / UUID_A).rename(tmp_path / lane / UUID_A)
    error = assert_place_refused(tmp_path, code)
    assert lane in error.detail


def test_place_refuses_verdict_digest_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = placement_refusal(tmp_path, "verdict-digest-mismatch", monkeypatch)
    assert_place_refused(tmp_path, code)


def test_place_refuses_legacy_verdict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = placement_refusal(tmp_path, "verdict-legacy", monkeypatch)
    assert_place_refused(tmp_path, code)


@pytest.mark.parametrize("index", range(6))
@bite("forge.md:F61")
def test_place_refuses_lane_unresolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, index: int
) -> None:
    code = placement_refusal(tmp_path, f"lane-{index}", monkeypatch)
    error = assert_place_refused(tmp_path, code)
    assert error.detail == LANE_REFUSALS[index]


def test_place_refuses_lane_root_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = placement_refusal(tmp_path, "lane-root-missing", monkeypatch)
    assert_place_refused(tmp_path, code)


def test_place_refuses_cross_device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = placement_refusal(tmp_path, "cross-device", monkeypatch)
    assert_place_refused(tmp_path, code)
    assert (tmp_path / "staging" / UUID_A).is_dir()
    assert not (tmp_path / "samples" / UUID_A).exists()


def test_place_refuses_rename_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = placement_refusal(tmp_path, "rename-failed", monkeypatch)
    assert_place_refused(tmp_path, code)
    assert (tmp_path / "staging" / UUID_A).is_dir()


@pytest.mark.parametrize("other_homes", [False, True])
def test_place_refuses_symlinked_staging_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, other_homes: bool
) -> None:
    code = placement_refusal(tmp_path, "bundle-unreadable", monkeypatch)
    if other_homes:
        make_bundle(tmp_path, UUID_A, lane="samples")
        make_bundle(tmp_path, UUID_A, lane="delivery")
    assert_place_refused(tmp_path, code)


def test_place_reports_post_rename_digest_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = placement_refusal(tmp_path, "post-rename-digest-drift", monkeypatch)
    assert_place_refused(tmp_path, code)
    assert not (tmp_path / "staging" / UUID_A).exists()
    assert (tmp_path / "samples" / UUID_A).is_dir()


def test_place_refuses_queue_broken(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    code = placement_refusal(tmp_path, "queue-broken", monkeypatch)
    assert_place_refused(tmp_path, code)


@pytest.mark.parametrize("case", REFUSAL_CASES)
def test_every_place_refusal_code_is_enumerated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    code = placement_refusal(tmp_path, case, monkeypatch)
    assert_place_refused(tmp_path, code)
    expected = {"lane-unresolved", *(item for item in REFUSAL_CASES if not item[-1].isdigit())}
    assert expected == pipeline.PLACE_CODES


@pytest.mark.parametrize("case", REFUSAL_CASES)
def test_place_details_render_only_from_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], case: str
) -> None:
    code = placement_refusal(tmp_path, case, monkeypatch)
    monkeypatch.chdir(tmp_path)

    result = pipeline.main(["pipeline.py", "place", "./", UUID_A])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert set(pipeline.PLACE_DETAILS) == pipeline.PLACE_CODES
    for name, templates in pipeline.PLACE_DETAILS.items():
        assert len(templates) == (6 if name == "lane-unresolved" else 1)
        for template in templates:
            assert {field for _, field, _, _ in Formatter().parse(template) if field} <= {
                "uuid",
                "lane",
                "path",
                "value",
            }
    assert captured.err in {
        "refused: "
        + code
        + ": "
        + template.format(uuid=UUID_A, lane=lane, path=f"./{path_lane}/{UUID_A}", value="unknown")
        + "\n"
        for template in pipeline.PLACE_DETAILS[code]
        for lane in ("staging", "samples", "delivery")
        for path_lane in ("staging", "samples", "delivery")
    }


@pytest.mark.parametrize("state", ["missing", "retained", "stale", "legacy", "clean"])
@pytest.mark.parametrize("lane", ["samples", "delivery"])
@bite("shared.md:A43")
def test_verify_flags_placed_bundle_without_clean_verdict(
    tmp_path: Path, state: str, lane: str
) -> None:
    bundle = prepare_placement(tmp_path)
    verdict_path = verdict_path_at(tmp_path, UUID_A)
    body = json.loads(verdict_path.read_text())
    if state == "missing":
        verdict_path.unlink()
    else:
        if state == "retained":
            body["outcome"] = "retained"
        if state == "stale":
            body["bundle_digest"] = "f" * 64
        if state == "legacy":
            del body["outcome"]
        verdict_path.write_text(json.dumps(body))
    bundle.rename(tmp_path / lane / UUID_A)

    findings = pipeline.verify(tmp_path, NOW)

    assert codes(findings) == ([] if state in {"legacy", "clean"} else ["PIPELINE_PLACED_UNCLEAN"])


def test_status_reports_staged_placeable_retained_placed(tmp_path: Path) -> None:
    for index in (4, 3, 2, 1):
        uuid = fresh_uuid(index)
        bundle = make_bundle(tmp_path, uuid)
        pipeline.seal(tmp_path, uuid, "forge-1", NOW)
        if index != 1:
            pipeline.claim(tmp_path, uuid, "crucible-1", NOW)
            pipeline.verdict(
                tmp_path, uuid, "retained" if index == 3 else "clean", "crucible-1", NOW
            )
        if index == 4:
            (tmp_path / "delivery").mkdir()
            bundle.rename(tmp_path / "delivery" / uuid)

    result = pipeline.status(tmp_path, NOW)

    assert result == {
        "sealed": 4,
        "pending": [fresh_uuid(1)],
        "claimed": [],
        "findings": [],
        "staged": [fresh_uuid(1), fresh_uuid(2), fresh_uuid(3)],
        "placeable": [fresh_uuid(2)],
        "retained": [fresh_uuid(3)],
        "placed": [fresh_uuid(4)],
    }


@pytest.mark.parametrize("outcome", ["clean", "retained"])
def test_cli_place_round_trip(tmp_path: Path, outcome: str) -> None:
    prepare_placement(tmp_path, outcome=outcome)
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)

    results = [
        subprocess.run(
            [sys.executable, "./trinity/tools/pipeline.py", "place", "./", UUID_A],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        for _ in range(2)
    ]

    for result in results:
        if outcome == "clean":
            assert result.returncode == 0, result.stderr
            assert result.stdout == f"placed ./samples/{UUID_A}\n"
            assert result.stderr == ""
        else:
            assert result.returncode == 1
            assert result.stdout == ""
            assert result.stderr == (
                "refused: retained: verdict retained findings; FORGE must author a successor\n"
            )


@pytest.mark.parametrize(
    "row",
    [
        "  - uuid: {uuid}\n    task_lane: sample # comment\n",
        "\t- uuid: {uuid}\t# comment\n\t\ttask_lane: sample\n",
        "  - slot: 1\n    uuid: {uuid}\n    task_lane: sample\n",
        "  - uuid: {uuid}\n\n    task_lane: sample\n",
        "  - uuid: {uuid}\n    task_lane: sample\n  - uuid: {uuid}\n    task_lane: sample\n",
    ],
)
def test_resolve_task_lane_accepts_indent_bounded_rows(tmp_path: Path, row: str) -> None:
    registry = write_lane_registry(tmp_path, [])
    registry.write_text("lanes:\n" + row.format(uuid=UUID_A))

    result = pipeline.resolve_task_lane(tmp_path, UUID_A)

    assert result == "samples"


@pytest.mark.parametrize(
    "suffix",
    [
        "  task_lane: sample\n",
        "task_lane: sample\n",
        "  - task_lane: sample\n",
        '    task_lane: "sample"\n',
        "    task_lane: sample-evil\n",
        "    task_lane:\nsample\n",
    ],
)
def test_resolve_task_lane_refuses_out_of_body_or_non_tokens(tmp_path: Path, suffix: str) -> None:
    registry = write_lane_registry(tmp_path, [])
    registry.write_text(f"lanes:\n  - uuid: {UUID_A}\n{suffix}")

    with pytest.raises(pipeline.PlaceError) as refused:
        pipeline.resolve_task_lane(tmp_path, UUID_A)

    assert refused.value.detail == "no task_lane in the row"


def test_resolve_task_lane_bounds_public_token(tmp_path: Path) -> None:
    write_lane_registry(tmp_path, [(UUID_A, "x" * 80)])

    with pytest.raises(pipeline.PlaceError) as refused:
        pipeline.resolve_task_lane(tmp_path, UUID_A)

    assert refused.value.detail == f'task_lane "{"x" * 32}" is outside starter, sample, delivery'


@pytest.mark.parametrize("placed", [False, True])
@pytest.mark.parametrize("failure", [pipeline.PipelineError, BundleIdentityError])
def test_place_maps_digest_errors_without_private_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, placed: bool, failure: type[ValueError]
) -> None:
    bundle = prepare_placement(tmp_path)
    if placed:
        bundle.rename(tmp_path / "samples" / UUID_A)

    def unreadable(_path: Path) -> str:
        raise failure("private auditor text")

    monkeypatch.setattr(pipeline, "bundle_digest", unreadable)

    error = assert_place_refused(tmp_path, "bundle-unreadable")
    assert "private" not in str(error)


def test_cli_place_maps_unwrapped_pipeline_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)

    def broken(_root: Path, _uuid: str) -> tuple[str, Path]:
        raise pipeline.PipelineError("private chain failure")

    monkeypatch.setattr(pipeline, "place", broken)

    result = pipeline.main(["pipeline.py", "place", "./", UUID_A])

    captured = capsys.readouterr()
    assert result == 1
    assert captured.out == ""
    assert captured.err == f"refused: queue-broken: {pipeline.PLACE_DETAILS['queue-broken'][0]}\n"


@pytest.mark.parametrize(
    ("fault", "code"),
    [
        ("non-utf8-queue", "queue-broken"),
        ("file-at-lane-root", "bundle-unreadable"),
        ("unreadable-occupant", "bundle-unreadable"),
    ],
)
def test_place_maps_filesystem_faults_to_closed_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    code: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    make_bundle(tmp_path, UUID_A)
    write_lane_registry(tmp_path, [(UUID_A, "sample")])
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
    pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-1", NOW)
    if fault == "non-utf8-queue":
        pipeline.stream_path(tmp_path, "forge-1").write_bytes(b"\xff\xfe not json\n")
    elif fault == "file-at-lane-root":
        shutil.rmtree(tmp_path / "samples", ignore_errors=True)
        (tmp_path / "samples").write_text("not a directory", encoding="utf-8")
    else:
        original = os.lstat

        def deny(path: object, *args: object, **kwargs: object) -> os.stat_result:
            if str(path).endswith(UUID_A):
                raise PermissionError(errno.EACCES, "private operating system detail")
            return original(path, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(os, "lstat", deny)
    with pytest.raises(pipeline.PlaceError) as caught:
        pipeline.place(tmp_path, UUID_A, NOW)
    assert caught.value.code == code
    assert "private operating system detail" not in str(caught.value)
    assert digest not in str(caught.value)
    monkeypatch.chdir(tmp_path)
    assert pipeline.main(["pipeline.py", "place", "./", UUID_A]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith(f"refused: {code}: ")
    assert "Traceback" not in captured.err


# ---- queue streams ----


def test_seal_writes_the_producer_stream_and_legacy_queue_still_reads(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    make_bundle(tmp_path, UUID_B)
    legacy = tmp_path / pipeline.QUEUE_PATH
    legacy.parent.mkdir(parents=True)
    entry: dict[str, object] = {
        "seq": 1,
        "uuid": UUID_B,
        "bundle_digest": pipeline.bundle_digest(tmp_path / "staging" / UUID_B),
        "sealed_at": "2026-09-16T11:00:00Z",
        "producer_run_id": "old-run",
        "prev_hash": pipeline.GENESIS_HASH,
    }
    entry["entry_hash"] = pipeline.chain_digest(entry)
    legacy.write_text(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")

    pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)

    stream = tmp_path / pipeline.QUEUE_DIR / "forge-ada.jsonl"
    assert stream.is_file()
    assert json.loads(stream.read_text().splitlines()[0])["seq"] == 1
    assert pipeline.verify(tmp_path, NOW) == []
    assert pipeline.pending(tmp_path) == [UUID_B, UUID_A]
    assert set(pipeline.streams(tmp_path)) == {"legacy", "forge-ada"}


def test_two_streams_chain_independently(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    make_bundle(tmp_path, UUID_B)
    pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)
    pipeline.seal(tmp_path, UUID_B, "forge-bob", NOW + timedelta(seconds=1))

    _, records = pipeline.walk_queue(tmp_path)

    assert [record["seq"] for record in records] == [1, 1]
    assert all(record["prev_hash"] == pipeline.GENESIS_HASH for record in records)
    assert [record["stream"] for record in records] == ["forge-ada", "forge-bob"]


def test_stream_record_must_name_its_own_producer(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)
    stream = tmp_path / pipeline.QUEUE_DIR / "forge-ada.jsonl"
    stream.rename(tmp_path / pipeline.QUEUE_DIR / "forge-bob.jsonl")

    findings = pipeline.verify(tmp_path, NOW)

    assert codes(findings) == ["PIPELINE_CHAIN_BROKEN"]
    assert "producer_run_id" in findings[0].message


def write_stream_record(root: Path, run_id: str, uuid: str, digest: str, sealed_at: str) -> Path:
    path = pipeline.stream_path(root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, object] = {
        "seq": 1,
        "uuid": uuid,
        "bundle_digest": digest,
        "sealed_at": sealed_at,
        "producer_run_id": run_id,
        "prev_hash": pipeline.GENESIS_HASH,
    }
    entry["entry_hash"] = pipeline.chain_digest(entry)
    path.write_text(json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n")
    return path


def test_same_uuid_in_two_streams_dedupes_on_equal_digest(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)
    write_stream_record(tmp_path, "forge-bob", UUID_A, digest, "2026-09-16T12:00:05Z")

    assert pipeline.verify(tmp_path, NOW) == []
    latest = pipeline.sealed_records(tmp_path)
    assert latest[UUID_A]["producer_run_id"] == "forge-ada"
    assert pipeline.pending(tmp_path) == [UUID_A]


@bite("shared.md:A56")
def test_same_uuid_in_two_streams_with_different_bytes_is_a_conflict(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)
    write_stream_record(tmp_path, "forge-bob", UUID_A, "f" * 64, "2026-09-16T12:00:05Z")

    findings = pipeline.verify(tmp_path, NOW)

    assert "PIPELINE_STREAM_CONFLICT" in codes(findings)
    with pytest.raises(pipeline.PipelineError, match="conflict"):
        pipeline.sealed_records(tmp_path)


def test_reseal_from_another_stream_is_frozen_not_a_supersession(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)
    make_bundle(tmp_path, UUID_A, marker="edited elsewhere")

    with pytest.raises(pipeline.PipelineError, match="frozen until a verdict lands"):
        pipeline.seal(tmp_path, UUID_A, "forge-bob", NOW + timedelta(seconds=1))


def test_backpressure_counts_pending_across_streams(tmp_path: Path) -> None:
    (tmp_path / ".podium").mkdir()
    (tmp_path / ".podium" / "pipeline.json").write_text('{"max_unaudited": 2}')
    make_bundle(tmp_path, UUID_A)
    make_bundle(tmp_path, UUID_B)
    make_bundle(tmp_path, fresh_uuid(3))
    pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)
    pipeline.seal(tmp_path, UUID_B, "forge-bob", NOW)

    with pytest.raises(pipeline.PipelineError, match="backpressure"):
        pipeline.seal(tmp_path, fresh_uuid(3), "forge-cat", NOW)


@bite("shared.md:A57")
def test_verify_accepted_refuses_a_rewritten_stream(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "--initial-branch=main"], cwd=tmp_path, check=True)
    make_bundle(tmp_path, UUID_A)
    make_bundle(tmp_path, UUID_B)
    pipeline.seal(tmp_path, UUID_A, "forge-ada", NOW)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-qm", "accepted"],
        cwd=tmp_path,
        check=True,
    )
    pipeline.seal(tmp_path, UUID_B, "forge-ada", NOW + timedelta(seconds=1))
    assert pipeline.verify(tmp_path, NOW, accepted="HEAD") == []

    stream = tmp_path / pipeline.QUEUE_DIR / "forge-ada.jsonl"
    stream.write_text(stream.read_text().splitlines()[-1] + "\n")
    findings = pipeline.verify(tmp_path, NOW, accepted="HEAD")

    assert "PIPELINE_STREAM_REWRITTEN" in codes(findings)
    assert "PIPELINE_STREAM_REWRITTEN" in codes(pipeline.verify(tmp_path, NOW, accepted="nope"))


# ---- claim ownership across clones ----


def write_claim(root: Path, uuid: str, digest: str, run_id: str, claimed_at: str) -> Path:
    path = root / pipeline.CLAIMS_DIR / uuid / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "uuid": uuid,
        "bundle_digest": digest,
        "consumer_run_id": run_id,
        "claimed_at": claimed_at,
    }
    path.write_text(json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n")
    return path


@bite("shared.md:A58")
def test_earliest_claim_owns_and_a_later_clone_verdict_is_unowned(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    write_claim(tmp_path, UUID_A, digest, "crucible-late", "2026-09-16T12:00:30Z")
    write_claim(tmp_path, UUID_A, digest, "crucible-early", "2026-09-16T12:00:10Z")

    owner = pipeline.claim_owner(tmp_path, UUID_A, digest)
    assert owner is not None and owner["consumer_run_id"] == "crucible-early"
    with pytest.raises(pipeline.PipelineError, match="another consumer"):
        pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-late", NOW)
    assert pipeline.verify(tmp_path, NOW) == []

    late = tmp_path / pipeline.VERDICTS_DIR / UUID_A / f"{digest}.json"
    late.parent.mkdir(parents=True)
    late.write_text(
        json.dumps(
            {
                "uuid": UUID_A,
                "bundle_digest": digest,
                "outcome": "clean",
                "consumer_run_id": "crucible-late",
            }
        )
    )
    findings = pipeline.verify(tmp_path, NOW)

    assert codes(findings) == ["PIPELINE_VERDICT_UNOWNED"]
    assert "crucible-early holds the earliest claim" in findings[0].message


def test_claim_ties_break_on_run_id_and_stale_claims_do_not_own(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    write_claim(tmp_path, UUID_A, "e" * 64, "crucible-aaa", "2026-09-16T11:00:00Z")
    write_claim(tmp_path, UUID_A, digest, "crucible-bbb", "2026-09-16T12:00:10Z")
    write_claim(tmp_path, UUID_A, digest, "crucible-abc", "2026-09-16T12:00:10Z")

    owner = pipeline.claim_owner(tmp_path, UUID_A, digest)

    assert owner is not None and owner["consumer_run_id"] == "crucible-abc"
    assert pipeline.verdict(tmp_path, UUID_A, "clean", "crucible-abc", NOW).is_file()
    assert pipeline.status(tmp_path, NOW)["claimed"] == []


def test_release_drops_only_the_named_consumer(tmp_path: Path) -> None:
    make_bundle(tmp_path, UUID_A)
    digest = pipeline.seal(tmp_path, UUID_A, "forge-1", NOW)
    early = write_claim(tmp_path, UUID_A, digest, "crucible-early", "2026-09-16T12:00:10Z")
    late = write_claim(tmp_path, UUID_A, digest, "crucible-late", "2026-09-16T12:00:30Z")

    pipeline.release_claim(tmp_path, UUID_A, "crucible-early")

    assert not early.exists() and late.exists()
    owner = pipeline.claim_owner(tmp_path, UUID_A, digest)
    assert owner is not None and owner["consumer_run_id"] == "crucible-late"


# ---- reconcile: overflow routing at merge ----


def seal_and_place(root: Path, uuid: str, run_id: str, at: datetime, lane: str = "sample") -> None:
    make_bundle(root, uuid, marker=uuid)
    lanes.route(root, lanes.LaneClaim(uuid, lane, 1, "batch-0001", run_id))
    pipeline.seal(root, uuid, run_id, at)
    pipeline.claim(root, uuid, "crucible-1", at)
    pipeline.verdict(root, uuid, "clean", "crucible-1", at)
    pipeline.place(root, uuid, at)


def lane_uuid(index: int) -> str:
    return str(uuid5(NAMESPACE_URL, f"lane-{index}"))


def lane_project(
    root: Path, count: int, runs: tuple[str, ...] = ("forge-ada", "forge-bob")
) -> None:
    (root / "samples").mkdir(exist_ok=True)
    (root / "delivery").mkdir(exist_ok=True)
    (root / ".podium").mkdir(exist_ok=True)
    (root / ".podium" / "pipeline.json").write_text('{"max_unaudited": 1000}')
    for index in range(count):
        seal_and_place(
            root, lane_uuid(index), runs[index % len(runs)], NOW + timedelta(seconds=index)
        )


@bite("forge.md:F42")
def test_reconcile_routes_every_sample_past_thirty_to_delivery_by_seal_order(
    tmp_path: Path,
) -> None:
    lane_project(tmp_path, 33)

    done = pipeline.reconcile(tmp_path)

    assert [move[0] for move in done.moves] == [lane_uuid(30), lane_uuid(31), lane_uuid(32)]
    assert all(move[1:] == ("samples", "delivery") for move in done.moves)
    assert len(lanes.resident_uuids(tmp_path / "samples")) == 30
    assert len(lanes.resident_uuids(tmp_path / "delivery")) == 3
    assert done.findings == ()
    assert set(done.readmes) == {"samples/README.md", "delivery/README.md", reports.TRACKER}
    assert pipeline.reconcile(tmp_path, check=True).findings == ()
    assert pipeline.verify(tmp_path, NOW) == []


def write_anchor_standing(root: Path, rows: dict[str, str]) -> None:
    (root / ".memory").mkdir(exist_ok=True)
    body = "# GENERATED by ENGRAM Phase H step 6b\n" + "".join(
        f"{uuid}: {state}\n" for uuid, state in rows.items()
    )
    (root / lanes.ANCHOR_STANDING_PATH).write_text(body, encoding="utf-8")


@bite("forge.md:F80")
def test_reconcile_keeps_an_ungraduated_anchor_inside_a_strict_thirty(
    tmp_path: Path,
) -> None:
    lane_project(tmp_path, 30)
    seal_and_place(tmp_path, lane_uuid(99), "forge-cat", NOW + timedelta(hours=1), lane="starter")

    done = pipeline.reconcile(tmp_path)

    assert done.moves == ((lane_uuid(29), "samples", "delivery"),)
    assert len(lanes.resident_uuids(tmp_path / "samples")) == 30
    assert lane_uuid(99) in lanes.resident_uuids(tmp_path / "samples")
    write_anchor_standing(tmp_path, {lane_uuid(99): "CANDIDATE"})
    assert pipeline.reconcile(tmp_path, check=True).findings == ()


@bite("forge.md:F81")
@pytest.mark.parametrize("state", sorted(lanes.GRADUATED_ANCHOR_STATES))
def test_reconcile_graduates_an_anchor_into_delivery_once_its_row_is_folded(
    tmp_path: Path, state: str
) -> None:
    lane_project(tmp_path, 31)
    seal_and_place(tmp_path, lane_uuid(99), "forge-cat", NOW - timedelta(hours=1), lane="starter")
    pipeline.reconcile(tmp_path)
    assert lane_uuid(99) in lanes.resident_uuids(tmp_path / "samples")
    assert lane_uuid(29) in lanes.resident_uuids(tmp_path / "delivery")
    write_anchor_standing(tmp_path, {lane_uuid(99): state})

    checked = pipeline.reconcile(tmp_path, check=True)
    assert f"{lane_uuid(99)} belongs under delivery/ by anchor standing" in [
        item.message for item in checked.findings
    ]

    done = pipeline.reconcile(tmp_path)

    # The graduated anchor leaves and the next ordinary bundle by seal order takes its place.
    assert set(done.moves) == {
        (lane_uuid(99), "samples", "delivery"),
        (lane_uuid(29), "delivery", "samples"),
    }
    assert len(lanes.resident_uuids(tmp_path / "samples")) == 30
    assert lane_uuid(99) in lanes.resident_uuids(tmp_path / "delivery")
    assert pipeline.reconcile(tmp_path, check=True).findings == ()


def test_reconcile_names_a_malformed_anchor_standing_and_graduates_nothing(
    tmp_path: Path,
) -> None:
    lane_project(tmp_path, 2)
    seal_and_place(tmp_path, lane_uuid(99), "forge-cat", NOW, lane="starter")
    (tmp_path / ".memory").mkdir()
    (tmp_path / lanes.ANCHOR_STANDING_PATH).write_text("not: a-row\n", encoding="utf-8")

    done = pipeline.reconcile(tmp_path)

    assert done.moves == ()
    assert [item.code for item in done.findings] == ["PIPELINE_RECONCILE_DRIFT"]
    assert "line 1 is not <uuid>: <state>" in done.findings[0].message
    assert lane_uuid(99) in lanes.resident_uuids(tmp_path / "samples")


@bite("forge.md:F64")
def test_reconcile_check_reports_drift_without_writing(tmp_path: Path) -> None:
    lane_project(tmp_path, 31)
    reports.render_root_reports(tmp_path)
    tracker_bytes = (tmp_path / reports.TRACKER).read_text(encoding="utf-8")
    before = sorted(lanes.resident_uuids(tmp_path / "samples"))

    done = pipeline.reconcile(tmp_path, check=True)

    assert sorted(lanes.resident_uuids(tmp_path / "samples")) == before
    assert not (tmp_path / "samples" / "README.md").exists()
    assert (tmp_path / reports.TRACKER).read_text(encoding="utf-8") == tracker_bytes
    assert {item.code for item in done.findings} == {"PIPELINE_RECONCILE_DRIFT"}
    messages = [item.message for item in done.findings]
    assert f"{lane_uuid(30)} belongs under delivery/ by seal order" in messages
    assert "samples/README.md is not rendered" in messages
    assert "delivery/README.md is not rendered" in messages
    assert pipeline.check_reconcile(str(tmp_path)) == list(done.findings)


def test_reconcile_readmes_list_only_residents_so_overflow_moves_to_delivery_readme(
    tmp_path: Path,
) -> None:
    lane_project(tmp_path, 31)

    pipeline.reconcile(tmp_path)

    samples_readme = (tmp_path / "samples" / "README.md").read_text(encoding="utf-8")
    delivery_readme = (tmp_path / "delivery" / "README.md").read_text(encoding="utf-8")
    assert lane_uuid(30) not in samples_readme
    assert lane_uuid(30) in delivery_readme
    assert lane_uuid(0) in samples_readme and lane_uuid(0) not in delivery_readme
    for text in (samples_readme, delivery_readme):
        assert text.startswith(pipeline.GENERATED_BANNER)
        assert [line for line in text.splitlines() if line.startswith("## ")] == list(
            pipeline.LANE_README_SECTIONS
        )
    assert "| clean |" in samples_readme


def test_reconcile_is_idempotent_and_never_edits_a_hand_edit_silently(tmp_path: Path) -> None:
    lane_project(tmp_path, 2)
    first = pipeline.reconcile(tmp_path)
    second = pipeline.reconcile(tmp_path)
    (tmp_path / "samples" / "README.md").write_text("hand edited\n", encoding="utf-8")

    assert first.readmes and second.readmes == () and second.moves == ()
    assert [item.message for item in pipeline.reconcile(tmp_path, check=True).findings] == [
        "samples/README.md is not rendered"
    ]


def test_reconcile_fixes_unsealed_legacy_residents_and_counts_them_first(tmp_path: Path) -> None:
    lane_project(tmp_path, 30)
    legacy = str(uuid5(NAMESPACE_URL, "legacy"))
    (tmp_path / "samples" / legacy).mkdir()

    done = pipeline.reconcile(tmp_path)

    assert legacy in lanes.resident_uuids(tmp_path / "samples")
    assert [move[0] for move in done.moves] == [lane_uuid(29)]


def test_reconcile_leaves_registered_delivery_where_it_stands(tmp_path: Path) -> None:
    lane_project(tmp_path, 2)
    legacy = str(uuid5(NAMESPACE_URL, "legacy-delivery"))
    make_bundle(tmp_path, legacy, lane="delivery")
    write_lane_registry(tmp_path, [(legacy, "delivery")])

    done = pipeline.reconcile(tmp_path)

    assert done.moves == ()
    assert legacy in lanes.resident_uuids(tmp_path / "delivery")


def test_reconcile_refuses_an_occupied_destination(tmp_path: Path) -> None:
    lane_project(tmp_path, 31)
    (tmp_path / "delivery" / lane_uuid(30)).mkdir()

    done = pipeline.reconcile(tmp_path)

    assert done.moves == ()
    assert any("that path is occupied" in item.message for item in done.findings)


def test_reconcile_reports_a_full_delivery_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane_project(tmp_path, 32)
    monkeypatch.setitem(lanes.LANE_CEILINGS, "delivery", 1)

    done = pipeline.reconcile(tmp_path, check=True)

    assert "PIPELINE_LANE_FULL" in {item.code for item in done.findings}


def test_cli_reconcile_round_trip(tmp_path: Path) -> None:
    lane_project(tmp_path, 31)
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)
    argv = [sys.executable, "./trinity/tools/pipeline.py", "reconcile", "./"]

    checked = subprocess.run(
        [*argv, "--check"], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    applied = subprocess.run(argv, cwd=tmp_path, capture_output=True, text=True, check=False)
    clean = subprocess.run(
        [*argv, "--check", "--json"], cwd=tmp_path, capture_output=True, text=True, check=False
    )

    assert checked.returncode == 1 and "belongs under delivery/ by seal order" in checked.stdout
    assert applied.returncode == 0, applied.stderr
    assert f"moved {lane_uuid(30)} samples/ -> delivery/" in applied.stdout
    assert clean.returncode == 0
    assert json.loads(clean.stdout) == {"findings": [], "moves": [], "readmes": []}


# ---- render-reports ----


def render_reports_cli(root: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    """Run the report-only entry point the hooks run, from a parent root holding ./trinity."""
    return subprocess.run(
        [sys.executable, "./trinity/tools/pipeline.py", "render-reports", "./", *flags],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def commit_parent(root: Path) -> None:
    """Commit every byte of a scratch parent, so only a later edit is unstaged."""
    git = ["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=Trinity"]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "parent"], check=True)


def index_bytes(root: Path, name: str) -> bytes:
    """The bytes git holds for ``name`` in the index, which a commit publishes."""
    done = subprocess.run(
        ["git", "-C", str(root), "show", f":{name}"], capture_output=True, check=True
    )
    return done.stdout


def residency(root: Path) -> tuple[list[str], list[str]]:
    return (
        sorted(lanes.resident_uuids(root / "samples")),
        sorted(lanes.resident_uuids(root / "delivery")),
    )


def finding_codes(stdout: str) -> list[str]:
    return [str(item["code"]) for item in json.loads(stdout)]


def test_cli_render_reports_writes_reports_and_moves_nothing(tmp_path: Path) -> None:
    lane_project(tmp_path, 33)
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)
    resident = residency(tmp_path)

    done = render_reports_cli(tmp_path)

    assert done.returncode == 0, done.stderr
    assert f"rendered {reports.TRACKER}" in done.stdout
    assert (tmp_path / reports.TRACKER).exists()
    assert residency(tmp_path) == resident
    assert len(resident[0]) == 33 and resident[1] == []


def test_cli_render_reports_check_refuses_drift(tmp_path: Path) -> None:
    lane_project(tmp_path, 33)
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)
    render_reports_cli(tmp_path)
    clean = render_reports_cli(tmp_path, "--check")
    tracker = tmp_path / reports.TRACKER
    drifted = tracker.read_bytes() + b"x"
    tracker.write_bytes(drifted)

    done = render_reports_cli(tmp_path, "--check", "--json")

    assert clean.returncode == 0, clean.stdout
    assert done.returncode == 3
    assert finding_codes(done.stdout) == ["REPORT_NOT_RENDERED"]
    assert tracker.read_bytes() == drifted


def test_cli_render_reports_staged_refuses_and_writes_expected_bytes(tmp_path: Path) -> None:
    lane_project(tmp_path, 33)
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)
    render_reports_cli(tmp_path)
    tracker = tmp_path / reports.TRACKER
    expected = tracker.read_bytes()
    stale = expected + b"stale\n"
    tracker.write_bytes(stale)
    commit_parent(tmp_path)

    done = render_reports_cli(tmp_path, "--check", "--staged", "--json")

    assert done.returncode == 3
    assert finding_codes(done.stdout) == ["REPORT_NOT_STAGED"]
    assert tracker.read_bytes() == expected
    assert index_bytes(tmp_path, reports.TRACKER) == stale


def test_cli_render_reports_staged_refuses_unstaged_inputs(tmp_path: Path) -> None:
    lane_project(tmp_path, 33)
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)
    render_reports_cli(tmp_path)
    commit_parent(tmp_path)
    staged_clean = render_reports_cli(tmp_path, "--check", "--staged")
    runs_module.open_run(
        tmp_path, "FORGE", "forge-eve-unstaged", principal="eve", now=NOW + timedelta(days=1)
    )

    done = render_reports_cli(tmp_path, "--check", "--staged", "--json")

    assert staged_clean.returncode == 0, staged_clean.stdout
    assert done.returncode == 3
    assert "REPORT_INPUTS_UNSTAGED" in finding_codes(done.stdout)


def test_render_reports_is_a_no_op_outside_a_parent(tmp_path: Path) -> None:
    (tmp_path / "trinity").symlink_to(ROOT, target_is_directory=True)

    rendered = render_reports_cli(tmp_path)
    checked = render_reports_cli(tmp_path, "--check", "--staged")
    listed = render_reports_cli(tmp_path, "--json")

    assert (rendered.returncode, rendered.stdout) == (0, "")
    assert (checked.returncode, checked.stdout) == (0, "")
    assert listed.returncode == 0 and json.loads(listed.stdout) == {"reports": []}
    assert [path.name for path in tmp_path.iterdir()] == ["trinity"]
