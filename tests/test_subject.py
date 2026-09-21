from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from tools import pipeline, runs, subject

from tests.bite_shared.registration import bite

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
RUN = "forge-ada-20260917t120000z-abc123"
OTHER = "forge-bob-20260917t120000z-def456"
UUID_A = str(uuid5(NAMESPACE_URL, "a"))
UUID_B = str(uuid5(NAMESPACE_URL, "b"))


def git(root: Path, *argv: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", *argv],
        cwd=root,
        check=True,
        capture_output=True,
    )


def parent(root: Path) -> None:
    git(root, "init", "-q", "--initial-branch=main")
    (root / "requirements").mkdir()
    (root / "requirements" / "grant.md").write_text("budget: 3\n", encoding="utf-8")
    (root / "touchstones").mkdir()
    (root / ".memory").mkdir()
    (root / ".memory" / "forge_view.yaml").write_text("view: 1\n", encoding="utf-8")
    (root / "staging").mkdir()
    (root / ".podium").mkdir()
    (root / ".podium" / "pipeline.json").write_text('{"max_unaudited": 100}', encoding="utf-8")


def stage(root: Path, uuid: str, marker: str) -> None:
    bundle = root / "staging" / uuid
    (bundle / "tests").mkdir(parents=True)
    (bundle / "task.toml").write_text(f'name = "{marker}"\n', encoding="utf-8")
    (bundle / "tests" / "test.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def forge_run(root: Path, run_id: str, uuid: str) -> Path:
    directory = runs.open_run(root, "FORGE", run_id, principal="ada", now=NOW)
    (directory / "contract.yaml").write_text("archetype: AR1\n", encoding="utf-8")
    (directory / "progress.yaml").write_text("phase: 2\n", encoding="utf-8")
    (directory / "report.md").write_text("## Disposition\n\nHOLD\n", encoding="utf-8")
    stage(root, uuid, uuid)
    pipeline.seal(root, uuid, run_id, NOW)
    return directory


def test_subject_digest_is_stable_and_lists_the_closure(tmp_path: Path) -> None:
    parent(tmp_path)
    forge_run(tmp_path, RUN, UUID_A)

    manifest = subject.subject_manifest(tmp_path, "FORGE", RUN)
    kinds = {entry.kind for entry in manifest}
    paths = {entry.path for entry in manifest}

    assert kinds == {"run", "bundle", "input", "view"}
    assert f".seed/runs/{RUN}/contract.yaml" in paths
    assert f".seed/runs/{RUN}/run.json" in paths
    assert f".seed/runs/{RUN}/progress.yaml" not in paths
    assert f".seed/runs/{RUN}/report.md" not in paths
    assert UUID_A in paths
    assert "requirements/grant.md" in paths
    assert ".memory/forge_view.yaml" in paths
    first = subject.subject_digest(tmp_path, "FORGE", RUN)
    assert first == subject.subject_digest(tmp_path, "FORGE", RUN)
    assert len(first) == 64


@bite("shared.md:A59")
def test_another_runs_commit_does_not_change_the_closure(tmp_path: Path) -> None:
    parent(tmp_path)
    forge_run(tmp_path, RUN, UUID_A)
    before = subject.subject_digest(tmp_path, "FORGE", RUN)

    forge_run(tmp_path, OTHER, UUID_B)
    (tmp_path / ".seed" / "runs" / RUN / "progress.yaml").write_text("phase: 3\n")
    (tmp_path / ".seed" / "runs" / RUN / "report.md").write_text("changed\n")
    (tmp_path / ".seed" / "runs" / RUN / "gate-receipts").mkdir()
    (tmp_path / ".seed" / "runs" / RUN / "gate-receipts" / "x.json").write_text("{}")

    assert subject.subject_digest(tmp_path, "FORGE", RUN) == before


@pytest.mark.parametrize(
    "change",
    ["contract", "bundle-successor", "requirements", "touchstone-added", "view", "trinity"],
)
def test_a_change_inside_the_closure_changes_the_digest(tmp_path: Path, change: str) -> None:
    parent(tmp_path)
    forge_run(tmp_path, RUN, UUID_A)
    (tmp_path / "trinity").mkdir()
    before = subject.subject_digest(tmp_path, "FORGE", RUN)

    match change:
        case "contract":
            (tmp_path / ".seed" / "runs" / RUN / "contract.yaml").write_text("archetype: AR2\n")
        case "bundle-successor":
            pipeline.claim(tmp_path, UUID_A, "crucible-1", NOW)
            pipeline.verdict(tmp_path, UUID_A, "retained", "crucible-1", NOW)
            stage(tmp_path, UUID_B, "two")
            pipeline.seal(tmp_path, UUID_B, RUN, NOW)
        case "requirements":
            (tmp_path / "requirements" / "grant.md").write_text("budget: 4\n")
        case "touchstone-added":
            (tmp_path / "touchstones" / "t1.md").write_text("graded\n")
        case "view":
            (tmp_path / ".memory" / "forge_view.yaml").write_text("view: 2\n")
        case "trinity":
            git(tmp_path, "add", "-A")
            git(tmp_path, "commit", "-qm", "base")
            sub = tmp_path / "trinity"
            git(sub, "init", "-q", "--initial-branch=main")
            (sub / "x").write_text("x")
            git(sub, "add", "-A")
            git(sub, "commit", "-qm", "sub")
            git(tmp_path, "add", "-A")
            git(tmp_path, "commit", "-qm", "gitlink")
        case _:
            raise AssertionError(change)

    assert subject.subject_digest(tmp_path, "FORGE", RUN) != before


def test_crucible_closure_binds_the_bundles_its_run_judged(tmp_path: Path) -> None:
    parent(tmp_path)
    forge_run(tmp_path, RUN, UUID_A)
    forge_run(tmp_path, OTHER, UUID_B)
    (tmp_path / ".memory" / "crucible_view.yaml").write_text("view: c\n", encoding="utf-8")
    crucible = "crucible-cat-20260917t120000z-0000aa"
    runs.open_run(tmp_path, "CRUCIBLE", crucible, principal="cat", now=NOW)
    pipeline.claim(tmp_path, UUID_A, crucible, NOW)
    pipeline.verdict(tmp_path, UUID_A, "clean", crucible, NOW)

    manifest = subject.subject_manifest(tmp_path, "CRUCIBLE", crucible)
    bundles = {entry.path for entry in manifest if entry.kind == "bundle"}

    assert bundles == {UUID_A}
    assert ".memory/crucible_view.yaml" in {entry.path for entry in manifest}
    assert ".memory/forge_view.yaml" not in {entry.path for entry in manifest}


def test_closure_refuses_a_symlink_and_an_unknown_run(tmp_path: Path) -> None:
    parent(tmp_path)
    forge_run(tmp_path, RUN, UUID_A)
    (tmp_path / "requirements" / "link.md").symlink_to(tmp_path / "requirements" / "grant.md")

    with pytest.raises(subject.SubjectError, match="symlink"):
        subject.subject_digest(tmp_path, "FORGE", RUN)
    with pytest.raises(subject.SubjectError, match="no run"):
        subject.subject_digest(tmp_path, "FORGE", OTHER)


def test_manifest_entries_serialize_canonically(tmp_path: Path) -> None:
    parent(tmp_path)
    forge_run(tmp_path, RUN, UUID_A)

    manifest = subject.subject_manifest(tmp_path, "FORGE", RUN)
    text = subject.render_manifest(manifest)

    lines = text.splitlines()
    assert lines == sorted(lines)
    assert all(len(line.split("\t")) == 5 for line in lines)
    assert json.loads(json.dumps([asdict(entry) for entry in manifest]))
