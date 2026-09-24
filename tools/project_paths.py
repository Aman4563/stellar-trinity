"""Project-root path doctrine for authored Trinity interfaces.

External path strings are canonical POSIX-style ``./`` paths anchored to the process working
directory captured by the trusted CLI entry point. Absolute paths exist only after validation for
containment and security checks; they are never suitable for serialization or diagnostics.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath


class ProjectPathError(ValueError):
    """An authored path violated the project-root path doctrine."""


def invocation_root() -> Path:
    """Capture the trusted orchestrator's process working directory.

    When TRINITY_AUTHORITY_ROOT is set, use that directory instead of the current
    working directory. This lets a hook or wrapper script invoke gate.py from
    inside an audited candidate while telling Trinity the true governance authority
    lives outside the candidate (where the gate policy legitimately resides). The
    operator is responsible for setting this to a trusted directory; unset falls
    back to the historical CWD behaviour so existing invocations are unaffected.
    """

    env_override = os.environ.get("TRINITY_AUTHORITY_ROOT")
    if env_override:
        try:
            root = Path(env_override).resolve(strict=True)
            metadata = root.lstat()
        except OSError as exc:
            raise ProjectPathError(
                f"TRINITY_AUTHORITY_ROOT is unavailable: {exc}"
            ) from exc
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise ProjectPathError(
                "TRINITY_AUTHORITY_ROOT must be a real directory"
            )
        return root

    try:
        root = Path.cwd().resolve(strict=True)
        metadata = root.lstat()
    except OSError as exc:
        raise ProjectPathError("invocation root is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise ProjectPathError("invocation root must be a real directory")
    return root


def _relative_parts(value: str, description: str) -> tuple[str, ...]:
    if not value.startswith("./"):
        raise ProjectPathError(f"{description} must start with './'")
    if "\\" in value:
        raise ProjectPathError(f"{description} must use forward slashes")
    if "\x00" in value:
        raise ProjectPathError(f"{description} is not a valid project-root path")
    suffix = value[2:]
    if suffix == "":
        return ()
    path = PurePosixPath(suffix)
    if path.is_absolute() or any(
        part in {"", ".", ".."} or part.startswith("~") for part in path.parts
    ):
        raise ProjectPathError(f"{description} must not contain traversal or redundant segments")
    if path.as_posix() != suffix:
        raise ProjectPathError(f"{description} must be a canonical './' path")
    return path.parts


def _reject_symlink_components(root: Path, parts: tuple[str, ...], description: str) -> None:
    current = root
    for part in parts:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ProjectPathError(f"{description} is unavailable") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise ProjectPathError(f"{description} must not traverse symbolic links")


def resolve_project_path(
    value: str,
    *,
    project_root: Path,
    description: str = "path",
    must_exist: bool = False,
) -> Path:
    """Validate one authored string and resolve it beneath an explicit trusted root."""

    parts = _relative_parts(value, description)
    _reject_symlink_components(project_root, parts, description)
    target = project_root.joinpath(*parts)
    try:
        resolved = target.resolve(strict=must_exist)
        resolved.relative_to(project_root)
    except (OSError, ValueError) as exc:
        raise ProjectPathError(
            f"{description} escapes or is unavailable beneath project root"
        ) from exc
    return resolved


def display_project_path(path: str | Path, *, project_root: Path) -> str:
    """Render an internal path as a canonical project-root path, or a redacted identifier."""

    candidate = Path(path)
    if not candidate.is_absolute():
        text = candidate.as_posix()
        if text in {"", "."}:
            return "./"
        try:
            parts = _relative_parts(f"./{text.removeprefix('./')}", "display path")
        except ProjectPathError:
            return "./<external>"
        return "./" + "/".join(parts)
    try:
        relative = candidate.relative_to(project_root)
    except ValueError:
        return "./<external>"
    text = relative.as_posix()
    return "./" if text == "." else f"./{text}"


def redact_project_root(text: str, *, project_root: Path) -> str:
    """Remove the trusted host root from an externally visible diagnostic."""

    root = str(project_root)
    return text.replace(root + os.sep, "./").replace(root, "./")
