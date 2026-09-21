from __future__ import annotations

import os
from pathlib import Path

import pytest
from tools import bundle_identity


def bundle(root: Path) -> Path:
    root.mkdir()
    (root / "task.toml").write_text("name = 'task'\n", encoding="utf-8")
    script = root / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    return root


def test_identity_binds_paths_bytes_and_executable_bits(tmp_path: Path) -> None:
    root = bundle(tmp_path / "bundle")
    first = bundle_identity.bundle_digest(root)
    (root / "run.sh").chmod(0o755)
    executable = bundle_identity.bundle_digest(root)
    assert executable != first
    (root / "task.toml").rename(root / "task-renamed.toml")
    assert bundle_identity.bundle_digest(root) != executable


def test_identity_refuses_empty_symlink_and_nonregular_bundle(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(bundle_identity.BundleIdentityError, match="no regular files"):
        bundle_identity.bundle_digest(empty)
    root = bundle(tmp_path / "bundle")
    (root / "escape").symlink_to(tmp_path / "outside")
    with pytest.raises(bundle_identity.BundleIdentityError, match="symbolic link"):
        bundle_identity.bundle_digest(root)
    (root / "escape").unlink()
    fifo = root / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(bundle_identity.BundleIdentityError, match="non-regular"):
        bundle_identity.bundle_digest(root)


def test_export_exclusion_is_top_level_and_github_is_identity_bearing(tmp_path: Path) -> None:
    root = bundle(tmp_path / "repository")
    (root / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
    (root / ".github").mkdir()
    (root / ".github" / "gate.yaml").write_text("one\n", encoding="utf-8")
    first = bundle_identity.tree_manifest(root, exclude_top_level=frozenset({".git"}))
    (root / ".git").write_text("gitdir: changed\n", encoding="utf-8")
    assert bundle_identity.tree_manifest(root, exclude_top_level=frozenset({".git"})) == first
    (root / ".github" / "gate.yaml").write_text("two\n", encoding="utf-8")
    assert bundle_identity.tree_manifest(root, exclude_top_level=frozenset({".git"})) != first


def test_bundle_digest_is_stable_when_trajectories_are_added(tmp_path: Path) -> None:
    root = bundle(tmp_path / "bundle")
    first = bundle_identity.bundle_digest(root)

    trajectories = root / "trajectories"
    trajectories.mkdir()
    (trajectories / "rollout-1.json").write_text("{}\n", encoding="utf-8")
    (trajectories / "inspector.html").write_text("<html></html>\n", encoding="utf-8")

    assert bundle_identity.bundle_digest(root) == first


def test_bundle_digest_changes_when_nested_trajectories_are_added(tmp_path: Path) -> None:
    root = bundle(tmp_path / "bundle")
    first = bundle_identity.bundle_digest(root)

    trajectories = root / "tests" / "trajectories"
    trajectories.mkdir(parents=True)
    (trajectories / "x").write_text("nested\n", encoding="utf-8")

    assert bundle_identity.bundle_digest(root) != first


def test_bundle_set_digest_is_stable_when_trajectories_are_added(tmp_path: Path) -> None:
    samples = tmp_path / "samples"
    samples.mkdir()
    root = bundle(samples / "task")
    first = bundle_identity.bundle_set_digest(samples, ["task"])
    snapshot = bundle_identity.release_snapshot_digest(samples, ["task"])

    trajectories = root / "trajectories"
    trajectories.mkdir()
    (trajectories / "rollout-1.json").write_text("{}\n", encoding="utf-8")
    (trajectories / "inspector.html").write_text("<html></html>\n", encoding="utf-8")

    assert bundle_identity.release_snapshot_digest(samples, ["task"]) != snapshot
    assert bundle_identity.bundle_set_digest(samples, ["task"]) == first


def test_root_symlink_is_refused(tmp_path: Path) -> None:
    real = bundle(tmp_path / "real")
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(bundle_identity.BundleIdentityError, match="symbolic link"):
        bundle_identity.bundle_digest(linked)
