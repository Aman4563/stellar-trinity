from __future__ import annotations

from pathlib import Path

import pytest
from tools.project_paths import (
    ProjectPathError,
    display_project_path,
    redact_project_root,
    resolve_project_path,
)


@pytest.mark.parametrize(
    "value",
    [
        "candidate-data",
        "/candidate-data",
        "~/candidate-data",
        ".\\candidate-data",
        "./../x",
        "./a/../x",
        "./a//x",
        "./a/./x",
    ],
)
def test_authored_paths_require_canonical_explicit_project_form(tmp_path: Path, value: str) -> None:
    with pytest.raises(ProjectPathError):
        resolve_project_path(value, project_root=tmp_path)


def test_project_root_and_external_siblings_resolve_without_serializing_host_root(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "candidate-data"
    trust = tmp_path / "release-trust"
    candidate.mkdir()
    trust.mkdir()
    assert resolve_project_path("./", project_root=tmp_path) == tmp_path
    resolved = resolve_project_path("./release-trust", project_root=tmp_path, must_exist=True)
    assert resolved == trust
    assert candidate not in resolved.parents
    assert display_project_path(resolved, project_root=tmp_path) == "./release-trust"
    assert str(tmp_path) not in redact_project_root(f"failed at {resolved}", project_root=tmp_path)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ProjectPathError, match="symbolic links"):
        resolve_project_path("./link/file.json", project_root=tmp_path)


@pytest.mark.parametrize("value", [Path("../outside"), "./../outside", "/outside"])
def test_display_never_emits_traversal_or_absolute_paths(tmp_path: Path, value: str | Path) -> None:
    rendered = display_project_path(value, project_root=tmp_path)
    assert rendered == "./<external>"
    assert ".." not in rendered
