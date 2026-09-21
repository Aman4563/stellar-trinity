"""Two clones of one parent, syncing only through git, driven through the real CLI.

Every scenario here is a race or an attack that a single-clone Trinity never faced. The
remote is a bare repository, each runner has its own clone, and every assertion is made
on the merged tree that the remote would hold, verified by the same commands the pre-push
hook and the merge check run.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from tools import lanes, pipeline, runs, sentinel, subject
from tools._findings import FindingJson

from tests.bite_shared.registration import bite

ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
ADA = "forge-ada-20260917t120000z-aaaaaa"
BOB = "forge-bob-20260917t120000z-bbbbbb"
CAT = "crucible-cat-20260917t120000z-cccccc"
DAN = "crucible-dan-20260917t120000z-dddddd"


def git(root: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", "-c", "commit.gpgsign=false", *argv],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise AssertionError(f"git {' '.join(argv)} failed: {done.stderr}")
    return done.stdout.strip()


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


def sync(root: Path) -> None:
    """Pull with rebase, reconcile, commit the reconciliation, push."""
    git(root, "pull", "-q", "--rebase", "origin", "main")
    pipeline.reconcile(root)
    commit_all(root, "reconcile")
    git(root, "push", "-q", "origin", "main")


def pipe(root: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "./trinity/tools/pipeline.py", *argv],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def stage_bundle(root: Path, uuid: str) -> Path:
    bundle = root / "staging" / uuid
    (bundle / "tests").mkdir(parents=True, exist_ok=True)
    (bundle / "task.toml").write_text(f'name = "{uuid}"\n', encoding="utf-8")
    (bundle / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    return bundle


def author(root: Path, run_id: str, uuid: str, at: datetime, lane: str = "sample") -> None:
    stage_bundle(root, uuid)
    lanes.route(root, lanes.LaneClaim(uuid, lane, 1, "batch-0001", run_id))
    pipeline.seal(root, uuid, run_id, at)


def judge(root: Path, run_id: str, uuid: str, at: datetime, outcome: str = "clean") -> None:
    pipeline.claim(root, uuid, run_id, at)
    pipeline.verdict(root, uuid, outcome, run_id, at)


def uid(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, label))


@pytest.fixture
def clones(tmp_path: Path) -> tuple[Path, Path, Path]:
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "--initial-branch=main", str(remote))
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "-q", "--initial-branch=main")
    for name in ("staging", "samples", "delivery", ".podium", "requirements", "touchstones"):
        (seed / name).mkdir()
        (seed / name / ".gitkeep").write_text("", encoding="utf-8")
    (seed / ".podium" / "pipeline.json").write_text('{"max_unaudited": 100}', encoding="utf-8")
    (seed / ".gitignore").write_text(".sentinel/pre-push*\n", encoding="utf-8")
    commit_all(seed, "genesis")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-q", "origin", "main")
    ada = tmp_path / "ada"
    bob = tmp_path / "bob"
    git(tmp_path, "clone", "-q", str(remote), str(ada))
    git(tmp_path, "clone", "-q", str(remote), str(bob))
    for clone in (ada, bob):
        (clone / "trinity").symlink_to(ROOT, target_is_directory=True)
        (clone / ".git" / "info" / "exclude").write_text("trinity\n", encoding="utf-8")
    return remote, ada, bob


def merged(tmp_path: Path, remote: Path) -> Path:
    view = tmp_path / "merged"
    if view.exists():
        subprocess.run(["rm", "-rf", str(view)], check=True)
    git(tmp_path, "clone", "-q", str(remote), str(view))
    (view / "trinity").symlink_to(ROOT, target_is_directory=True)
    return view


# ---- the thirty-first sample race ---------------------------------------------------------


@bite("shared.md:A67")
def test_two_clones_placing_past_thirty_route_the_overflow_at_merge(
    tmp_path: Path, clones: tuple[Path, Path, Path]
) -> None:
    remote, ada, bob = clones
    for index in range(16):
        author(ada, ADA, uid(f"ada-{index}"), NOW + timedelta(seconds=index))
        judge(ada, CAT, uid(f"ada-{index}"), NOW + timedelta(seconds=index))
        pipeline.place(ada, uid(f"ada-{index}"))
    for index in range(16):
        author(bob, BOB, uid(f"bob-{index}"), NOW + timedelta(seconds=index, milliseconds=500))
        judge(bob, DAN, uid(f"bob-{index}"), NOW + timedelta(seconds=index, milliseconds=500))
        pipeline.place(bob, uid(f"bob-{index}"))
    assert len(lanes.resident_uuids(ada / "samples")) == 16
    assert len(lanes.resident_uuids(bob / "samples")) == 16
    commit_all(ada, "ada places sixteen")
    commit_all(bob, "bob places sixteen")

    sync(ada)
    sync(bob)
    sync(ada)

    view = merged(tmp_path, remote)
    assert len(lanes.resident_uuids(view / "samples")) == 30
    assert len(lanes.resident_uuids(view / "delivery")) == 2
    assert pipeline.reconcile(view, check=True).findings == ()
    assert pipeline.verify(view, NOW) == []
    overflow = sorted(lanes.resident_uuids(view / "delivery"))
    assert overflow == sorted([uid("ada-15"), uid("bob-15")])
    samples_readme = (view / "samples" / "README.md").read_text(encoding="utf-8")
    delivery_readme = (view / "delivery" / "README.md").read_text(encoding="utf-8")
    assert all(item not in samples_readme and item in delivery_readme for item in overflow)
    assert pipe(view, "reconcile", "./", "--check").returncode == 0


# ---- queue streams under merge --------------------------------------------------------------


def test_stream_prefix_rule_refuses_a_rewritten_history_at_push_time(
    clones: tuple[Path, Path, Path],
) -> None:
    remote, ada, _bob = clones
    author(ada, ADA, uid("one"), NOW)
    commit_all(ada, "seal one")
    git(ada, "push", "-q", "origin", "main")
    accepted = git(ada, "rev-parse", "HEAD")
    author(ada, ADA, uid("two"), NOW + timedelta(seconds=1))
    assert pipe(ada, "verify", "./", "--accepted", accepted).returncode == 0

    stream = pipeline.stream_path(ada, ADA)
    stream.write_text(stream.read_text().splitlines()[-1] + "\n")
    refused = pipe(ada, "verify", "./", "--accepted", accepted)

    assert refused.returncode == 1
    assert "is not a prefix of the stream on disk" in refused.stdout
    del remote


def test_conflicting_bytes_under_one_uuid_surface_after_merge(
    clones: tuple[Path, Path, Path],
) -> None:
    remote, ada, bob = clones
    shared = uid("shared")
    author(ada, ADA, shared, NOW)
    commit_all(ada, "ada seals shared")
    stage_bundle(bob, shared)
    (bob / "staging" / shared / "task.toml").write_text('name = "different bytes"\n')
    lanes.route(bob, lanes.LaneClaim(shared, "sample", 1, "batch-0001", BOB))
    pipeline.seal(bob, shared, BOB, NOW + timedelta(seconds=1))
    commit_all(bob, "bob seals shared with other bytes")

    git(ada, "push", "-q", "origin", "main")
    git(bob, "fetch", "-q", "origin")
    merge = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", "merge", "-q", "origin/main"],
        cwd=bob,
        capture_output=True,
        text=True,
        check=False,
    )

    if merge.returncode != 0:
        assert "staging" in merge.stdout + merge.stderr
        return
    findings = pipeline.verify(bob, NOW)
    assert "PIPELINE_STREAM_CONFLICT" in {item.code for item in findings}
    del remote


def test_backpressure_is_enforced_over_the_merged_stream_union(
    clones: tuple[Path, Path, Path],
) -> None:
    remote, ada, bob = clones
    for clone in (ada, bob):
        (clone / ".podium" / "pipeline.json").write_text('{"max_unaudited": 3}', encoding="utf-8")
    for index in range(2):
        author(ada, ADA, uid(f"a{index}"), NOW + timedelta(seconds=index))
        author(bob, BOB, uid(f"b{index}"), NOW + timedelta(seconds=index))
    commit_all(ada, "ada seals two")
    commit_all(bob, "bob seals two")
    git(ada, "push", "-q", "origin", "main")
    git(bob, "pull", "-q", "--rebase", "origin", "main")

    findings = pipeline.verify(bob, NOW)

    assert "PIPELINE_BACKPRESSURE" in {item.code for item in findings}
    with pytest.raises(pipeline.PipelineError, match="backpressure"):
        author(bob, BOB, uid("b2"), NOW + timedelta(seconds=9))
    del remote


# ---- audit claims across clones -------------------------------------------------------------


def test_two_auditors_claiming_one_bundle_resolve_to_the_earliest_after_merge(
    clones: tuple[Path, Path, Path],
) -> None:
    remote, ada, bob = clones
    target = uid("contested")
    author(ada, ADA, target, NOW)
    commit_all(ada, "seal contested")
    git(ada, "push", "-q", "origin", "main")
    git(bob, "pull", "-q", "--rebase", "origin", "main")
    pipeline.claim(ada, target, CAT, NOW + timedelta(minutes=2))
    pipeline.claim(bob, target, DAN, NOW + timedelta(minutes=1))
    pipeline.verdict(ada, target, "clean", CAT, NOW + timedelta(minutes=3))
    commit_all(ada, "cat judges")
    commit_all(bob, "dan claims")
    git(ada, "push", "-q", "origin", "main")
    git(bob, "pull", "-q", "--rebase", "origin", "main")

    digest = str(pipeline.sealed_records(bob)[target]["bundle_digest"])
    owner = pipeline.claim_owner(bob, target, digest)
    findings = pipeline.verify(bob, NOW + timedelta(minutes=4))

    assert owner is not None and owner["consumer_run_id"] == DAN
    assert {item.code for item in findings} == {"PIPELINE_VERDICT_UNOWNED"}
    with pytest.raises(pipeline.PipelineError, match="already judged"):
        pipeline.claim(bob, target, "crucible-eve", NOW + timedelta(minutes=5))
    del remote


# ---- qualification binding across foreign commits -------------------------------------------


def test_a_runs_qualification_survives_the_other_clones_push(
    clones: tuple[Path, Path, Path],
) -> None:
    remote, ada, bob = clones
    author(ada, ADA, uid("ada-q"), NOW)
    directory = runs.open_run(ada, "FORGE", ADA, principal="ada", now=NOW)
    (directory / "contract.yaml").write_text("archetype: AR1\n", encoding="utf-8")
    before = subject.subject_digest(ada, "FORGE", ADA)
    commit_all(ada, "ada run")
    git(ada, "push", "-q", "origin", "main")

    author(bob, BOB, uid("bob-q"), NOW + timedelta(seconds=1))
    runs.open_run(bob, "FORGE", BOB, principal="bob", now=NOW)
    commit_all(bob, "bob run")
    git(bob, "pull", "-q", "--rebase", "origin", "main")
    git(bob, "push", "-q", "origin", "main")
    git(ada, "pull", "-q", "--rebase", "origin", "main")

    assert subject.subject_digest(ada, "FORGE", ADA) == before
    (ada / "requirements" / "grant.md").write_text("budget: 1\n", encoding="utf-8")
    assert subject.subject_digest(ada, "FORGE", ADA) != before
    del remote


# ---- sentinel streams under merge -----------------------------------------------------------


def test_sentinel_streams_merge_and_repeats_still_aggregate(
    tmp_path: Path, clones: tuple[Path, Path, Path]
) -> None:
    remote, ada, bob = clones
    actor = sentinel.Actor.for_ci(git_author="Ada <ada@x>", github_login="ada")
    finding: FindingJson = {
        "code": "SAB_DIRTY_TREE",
        "severity": "error",
        "path": "x",
        "line": None,
        "message": "m",
    }
    for index in range(3):
        sentinel.record(
            ada,
            [finding],
            actor=actor,
            run_id=f"ada-{index}",
            git_sha="b" * 40,
            repo="acme/x",
            now=NOW + timedelta(minutes=index),
            stream=f"forge-ada-{index}",
        )
    for index in range(2):
        sentinel.record(
            bob,
            [finding],
            actor=actor,
            run_id=f"bob-{index}",
            git_sha="b" * 40,
            repo="acme/x",
            now=NOW + timedelta(minutes=10 + index),
            stream=f"forge-bob-{index}",
        )
    commit_all(ada, "ada sentinel")
    commit_all(bob, "bob sentinel")
    git(ada, "push", "-q", "origin", "main")
    git(bob, "pull", "-q", "--rebase", "origin", "main")
    git(bob, "push", "-q", "origin", "main")

    view = merged(tmp_path, remote)
    assert sentinel.check_sentinel_chain(str(view)) == []
    assert len(sentinel.all_attempts(view)) == 5
    sentinel.record(
        view,
        [finding],
        actor=actor,
        run_id="eve-1",
        git_sha="b" * 40,
        repo="acme/x",
        now=NOW + timedelta(minutes=20),
        stream="forge-eve-1",
    )
    codes = {item.code for item in sentinel.check_sentinel_chain(str(view))}
    assert codes == {sentinel.SabotageCode.SAB_REPEATED_ATTEMPT}


# ---- rebase of unpublished proposals --------------------------------------------------------


def test_rebasing_unpublished_work_keeps_every_bound_byte_identical(
    clones: tuple[Path, Path, Path],
) -> None:
    remote, ada, bob = clones
    author(bob, BOB, uid("bob-r"), NOW)
    commit_all(bob, "bob seals")
    git(bob, "push", "-q", "origin", "main")
    author(ada, ADA, uid("ada-r"), NOW + timedelta(seconds=1))
    directory = runs.open_run(ada, "FORGE", ADA, principal="ada", now=NOW)
    (directory / "contract.yaml").write_text("archetype: AR1\n", encoding="utf-8")
    digest_before = subject.subject_digest(ada, "FORGE", ADA)
    stream_before = pipeline.stream_path(ada, ADA).read_bytes()
    commit_all(ada, "ada proposal")

    git(ada, "pull", "-q", "--rebase", "origin", "main")

    assert subject.subject_digest(ada, "FORGE", ADA) == digest_before
    assert pipeline.stream_path(ada, ADA).read_bytes() == stream_before
    assert pipeline.verify(ada, NOW) == []
    assert json.loads((directory / "run.json").read_text())["run_id"] == ADA
    del remote
