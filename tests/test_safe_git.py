"""Regression tests for inert candidate Git metadata snapshots."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from tools.safe_git import SafeGitError, SafeGitRepository

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Safe Git Test",
    "GIT_AUTHOR_EMAIL": "safe-git@trinity.test",
    "GIT_COMMITTER_NAME": "Safe Git Test",
    "GIT_COMMITTER_EMAIL": "safe-git@trinity.test",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(root: Path, *argv: str) -> str:
    completed = subprocess.run(
        ["git", *argv],
        cwd=root,
        env={**os.environ, **GIT_ENV},
        capture_output=True,
        check=False,
        shell=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "candidate"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "tracked.txt").write_text("trusted\n", encoding="utf-8")
    git(root, "add", "tracked.txt")
    git(root, "commit", "-q", "-m", "candidate")
    return root


def marker_command(tmp_path: Path) -> tuple[Path, Path]:
    marker = tmp_path / "executed"
    command = tmp_path / "touch-marker"
    command.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
    command.chmod(0o755)
    return marker, command


def test_snapshot_preserves_head_ancestry_and_dirty_detection_without_hardlinks(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path)
    head = git(root, "rev-parse", "HEAD")
    source_object = root / ".git" / "objects" / head[:2] / head[2:]
    with SafeGitRepository(root) as snapshot:
        copied_object = snapshot.git_dir / "objects" / head[:2] / head[2:]
        assert snapshot.head == head
        assert snapshot.is_ancestor(head, snapshot.head)
        assert snapshot.changed_paths(head, snapshot.head) == set()
        assert snapshot.status_porcelain() == ""
        assert (source_object.stat().st_dev, source_object.stat().st_ino) != (
            copied_object.stat().st_dev,
            copied_object.stat().st_ino,
        )
        (root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
        assert "tracked.txt" in (snapshot.status_porcelain() or "")


def test_ls_files_stage_returns_every_mode_and_gitlinks_filter_matches(tmp_path: Path) -> None:
    root = repository(tmp_path)
    gitlink_oid = "a1b2c3d4" * 5
    git(root, "update-index", "--add", "--cacheinfo", f"160000,{gitlink_oid},vendor")
    blob_oid = git(root, "rev-parse", ":tracked.txt")
    with SafeGitRepository(root) as snapshot:
        assert snapshot.ls_files_stage() == (
            ("100644", blob_oid, "tracked.txt"),
            ("160000", gitlink_oid, "vendor"),
        )
        assert snapshot._gitlinks() == [("vendor", gitlink_oid)]


@pytest.mark.parametrize(
    "malicious_config",
    [
        "[core]\n\tfsmonitor = {command}\n",
        "[core]\n\thooksPath = {command}\n",
        "[diff]\n\texternal = {command}\n",
        '[diff "payload"]\n\ttextconv = {command}\n',
        '[filter "payload"]\n\tclean = {command}\n',
        '[includeIf "gitdir:**"]\n\tpath = {command}\n',
    ],
)
def test_executable_candidate_config_is_rejected_without_execution(
    tmp_path: Path, malicious_config: str
) -> None:
    root = repository(tmp_path)
    marker, command = marker_command(tmp_path)
    config = root / ".git" / "config"
    config.write_text(
        config.read_text(encoding="utf-8") + malicious_config.format(command=command),
        encoding="utf-8",
    )
    with pytest.raises(SafeGitError, match="candidate Git config"):
        SafeGitRepository(root)
    assert not marker.exists()


def test_inherited_git_config_environment_is_discarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = repository(tmp_path)
    marker, command = marker_command(tmp_path)
    hostile_global = tmp_path / "global.gitconfig"
    hostile_global.write_text(f"[core]\n\tfsmonitor = {command}\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(hostile_global))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "diff.external")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(command))
    with SafeGitRepository(root) as snapshot:
        assert snapshot.status_porcelain() == ""
    assert not marker.exists()


def test_installed_parent_hooks_path_is_inert(tmp_path: Path) -> None:
    root = repository(tmp_path)
    marker, command = marker_command(tmp_path)
    hooks = root / ".githooks"
    hooks.mkdir()
    (hooks / "pre-commit").write_text(command.read_text(encoding="utf-8"), encoding="utf-8")
    (hooks / "pre-commit").chmod(0o755)
    git(root, "config", "core.hooksPath", ".githooks")
    with SafeGitRepository(root) as snapshot:
        assert snapshot.status_porcelain() == "?? .githooks/pre-commit"
    assert not marker.exists()


def test_gitdir_indirection_and_object_alternates_are_rejected(tmp_path: Path) -> None:
    root = repository(tmp_path)
    git_dir = root / ".git"
    moved = tmp_path / "metadata"
    git_dir.rename(moved)
    git_dir.write_text(f"gitdir: {moved}\n", encoding="utf-8")
    with pytest.raises(SafeGitError, match="indirection"):
        SafeGitRepository(root)

    git_dir.unlink()
    moved.rename(git_dir)
    alternates = git_dir / "objects" / "info" / "alternates"
    alternates.write_text("/tmp/untrusted-objects\n", encoding="utf-8")
    with pytest.raises(SafeGitError, match="alternate"):
        SafeGitRepository(root)
