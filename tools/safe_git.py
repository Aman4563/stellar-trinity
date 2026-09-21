"""Run read-only Git queries without loading an untrusted checkout's Git control plane.

The candidate's object and index bytes are copied into a fresh bare repository owned by the
verifier. Candidate configuration, hooks, refs, attributes metadata, alternates, and environment
directives are never copied or loaded. The caller must still provide an immutable candidate
filesystem snapshot for the duration of a verification.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import BinaryIO

GIT_TIMEOUT_SECONDS = 30.0
MAX_CONTROL_BYTES = 16 * 1024 * 1024
HEX40 = re.compile(r"\A[0-9a-fA-F]{40}\Z")
LOOSE_OBJECT_DIRECTORY = re.compile(r"\A[0-9a-f]{2}\Z")
LOOSE_OBJECT_NAME = re.compile(r"\A[0-9a-f]{38}\Z")
SHARED_INDEX_NAME = re.compile(r"\Asharedindex\.[0-9a-f]{40}\Z")
PACKED_REF_FIELDS = 2
INDEX_ENTRY_FIELDS = 3
CONFIG_SECTION = re.compile(
    r'^\s*\[\s*([A-Za-z0-9.-]+)(?:\s+"(?:[^"\\]|\\.)*")?\s*\]\s*(?:[#;].*)?$'
)
CONFIG_KEY = re.compile(r"\s*([A-Za-z][A-Za-z0-9.-]*)\s*(?:=|$)")
UNSAFE_CORE_KEYS = frozenset(
    {"askpass", "attributesfile", "editor", "fsmonitor", "hookspath", "pager", "sshcommand"}
)
UNSAFE_DIFF_KEYS = frozenset({"command", "external", "textconv"})


class SafeGitError(ValueError):
    """The candidate cannot be represented as inert Git data."""


def _trusted_git() -> Path:
    candidates = [
        shutil.which("git", path=os.defpath),
        "/usr/bin/git",
        "/bin/git",
        "/usr/local/bin/git",
        "/opt/homebrew/bin/git",
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        path = Path(candidate)
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return resolved
    raise SafeGitError("trusted Git executable is unavailable")


def _regular_stat(path: Path) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise SafeGitError(f"Git metadata is unavailable at {path}: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise SafeGitError(f"Git metadata must be a regular file: {path}")
    return metadata


def _read_regular(path: Path, *, maximum: int | None = None) -> bytes:
    before = _regular_stat(path)
    if maximum is not None and before.st_size > maximum:
        raise SafeGitError(f"Git control file is too large: {path}")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise SafeGitError(f"Git metadata changed while opening: {path}")
            data = handle.read()
        after = path.lstat()
    except OSError as exc:
        raise SafeGitError(f"Git metadata cannot be read at {path}: {exc}") from exc
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise SafeGitError(f"Git metadata changed while reading: {path}")
    return data


def _copy_regular(source: Path, target: Path) -> None:
    data = _read_regular(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def _validate_candidate_config(git_dir: Path) -> None:
    config_path = git_dir / "config"
    try:
        text = _read_regular(config_path, maximum=MAX_CONTROL_BYTES).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SafeGitError("candidate Git config is not UTF-8") from exc
    section = ""
    continuation = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if continuation:
            continuation = raw_line.rstrip().endswith("\\")
            continue
        if not line or line.startswith(("#", ";")):
            continue
        section_match = CONFIG_SECTION.fullmatch(raw_line)
        if section_match is not None:
            section = section_match.group(1).lower().split(".", 1)[0]
            if section in {"include", "includeif"}:
                raise SafeGitError("candidate Git config contains an include directive")
            continuation = raw_line.rstrip().endswith("\\")
            continue
        key_match = CONFIG_KEY.match(raw_line)
        if key_match is None or not section:
            raise SafeGitError("candidate Git config has unsupported syntax")
        key = key_match.group(1).lower()
        if section == "core" and key == "hookspath":
            # The parent gate installs this relative hook directory. The candidate
            # config is never copied into the isolated repository, whose hooks path
            # is explicitly disabled. Keep every other candidate path forbidden.
            value = raw_line.split("=", 1)[1].strip() if "=" in raw_line else ""
            if value == ".githooks":
                continue
        if section == "core" and key in UNSAFE_CORE_KEYS:
            raise SafeGitError(f"candidate Git config contains executable core.{key}")
        if section == "diff" and key in UNSAFE_DIFF_KEYS:
            raise SafeGitError(f"candidate Git config contains executable diff.{key}")
        if section == "filter":
            raise SafeGitError("candidate Git config contains a filter driver")
        if section == "credential" and key == "helper":
            raise SafeGitError("candidate Git config contains a credential helper")
        if section == "interactive" and key == "difffilter":
            raise SafeGitError("candidate Git config contains interactive.diffFilter")
        continuation = raw_line.rstrip().endswith("\\")


def _candidate_git_dir(root: Path) -> Path:
    git_dir = root / ".git"
    try:
        metadata = git_dir.lstat()
    except OSError as exc:
        raise SafeGitError(f"candidate has no readable .git directory: {exc}") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise SafeGitError("candidate .git indirection or symlink is forbidden")
    for forbidden in (
        git_dir / "commondir",
        git_dir / "objects" / "info" / "alternates",
        git_dir / "objects" / "info" / "http-alternates",
    ):
        if forbidden.exists() or forbidden.is_symlink():
            raise SafeGitError(
                f"candidate shared or alternate object metadata is forbidden: {forbidden}"
            )
    _validate_candidate_config(git_dir)
    return git_dir


def _head_oid(git_dir: Path) -> str:
    try:
        head = _read_regular(git_dir / "HEAD", maximum=4096).decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise SafeGitError("candidate HEAD is not ASCII") from exc
    if HEX40.fullmatch(head):
        return head.lower()
    if not head.startswith("ref: "):
        raise SafeGitError("candidate HEAD is not a full object id or symbolic ref")
    ref = head.removeprefix("ref: ")
    parts = ref.split("/")
    if not ref.startswith("refs/") or any(not part or part in {".", ".."} for part in parts):
        raise SafeGitError("candidate HEAD symbolic ref is unsafe")
    loose_ref = git_dir.joinpath(*parts)
    if loose_ref.exists() or loose_ref.is_symlink():
        try:
            oid = _read_regular(loose_ref, maximum=4096).decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise SafeGitError("candidate HEAD ref is not ASCII") from exc
        if not HEX40.fullmatch(oid):
            raise SafeGitError("candidate HEAD ref is not a full object id")
        return oid.lower()
    packed_refs = git_dir / "packed-refs"
    if not packed_refs.exists():
        raise SafeGitError("candidate HEAD ref is missing")
    try:
        packed = _read_regular(packed_refs, maximum=MAX_CONTROL_BYTES).decode("ascii")
    except UnicodeDecodeError as exc:
        raise SafeGitError("candidate packed-refs is not ASCII") from exc
    for line in packed.splitlines():
        if not line or line.startswith(("#", "^")):
            continue
        fields = line.split(" ", 1)
        if len(fields) == PACKED_REF_FIELDS and fields[1] == ref and HEX40.fullmatch(fields[0]):
            return fields[0].lower()
    raise SafeGitError("candidate HEAD ref is absent from packed-refs")


class SafeGitRepository:
    """Disposable trusted Git metadata populated only with candidate object and index bytes."""

    def __init__(self, root: Path, *, _metadata_dir: Path | None = None) -> None:
        try:
            self.root = root.resolve(strict=True)
        except OSError as exc:
            raise SafeGitError(f"candidate root cannot be resolved: {exc}") from exc
        self.executable = _trusted_git()
        self._temporary = tempfile.TemporaryDirectory(prefix="trinity-safe-git-")
        self._base = Path(self._temporary.name)
        self.git_dir = self._base / "repository.git"
        self.environment = self._environment()
        try:
            candidate_git_dir = (
                _candidate_git_dir(self.root) if _metadata_dir is None else _metadata_dir
            )
            if _metadata_dir is not None:
                _validate_candidate_config(candidate_git_dir)
            self._candidate_git_dir = candidate_git_dir
            self._initialize()
            self._import_objects(candidate_git_dir)
            self._import_index(candidate_git_dir)
            self.head = _head_oid(candidate_git_dir)
            (self.git_dir / "HEAD").write_text(self.head + "\n", encoding="ascii")
            if self.run("cat-file", "-e", f"{self.head}^{{commit}}") is None:
                raise SafeGitError("candidate HEAD commit is absent or invalid")
        except BaseException:
            self.close()
            raise

    def _environment(self) -> dict[str, str]:
        return {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "HOME": str(self._base),
            "LC_ALL": "C",
            "PATH": os.defpath,
        }

    def _initialize(self) -> None:
        try:
            completed = subprocess.run(
                [str(self.executable), "init", "--bare", "--quiet", str(self.git_dir)],
                cwd=self._base,
                env=self.environment,
                capture_output=True,
                check=False,
                shell=False,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SafeGitError(f"trusted bare repository initialization failed: {exc}") from exc
        if completed.returncode != 0:
            raise SafeGitError("trusted bare repository initialization was refused")

    def _command(self, *argv: str, work_tree: bool = False) -> list[str]:
        command = [
            str(self.executable),
            "--no-pager",
            f"--git-dir={self.git_dir}",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.bare=false",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-c",
            "protocol.file.allow=never",
        ]
        if work_tree:
            command.append(f"--work-tree={self.root}")
        command.extend(argv)
        return command

    def _run_raw(
        self, *argv: str, stdin: BinaryIO | None = None, work_tree: bool = False
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(
                self._command(*argv, work_tree=work_tree),
                cwd=self._base,
                env=self.environment,
                stdin=stdin,
                capture_output=True,
                check=False,
                shell=False,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SafeGitError(f"trusted Git invocation failed: {exc}") from exc

    def run(self, *argv: str, work_tree: bool = False) -> str | None:
        completed = self._run_raw(*argv, work_tree=work_tree)
        if completed.returncode != 0:
            return None
        try:
            return completed.stdout.decode("utf-8").strip()
        except UnicodeDecodeError:
            return None

    def _import_objects(self, candidate_git_dir: Path) -> None:
        objects = candidate_git_dir / "objects"
        try:
            objects_metadata = objects.lstat()
            entries = sorted(objects.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise SafeGitError(f"candidate object database is unreadable: {exc}") from exc
        if not stat.S_ISDIR(objects_metadata.st_mode):
            raise SafeGitError("candidate object database is not a directory")
        destination = self.git_dir / "objects"
        for directory in entries:
            if not LOOSE_OBJECT_DIRECTORY.fullmatch(directory.name):
                continue
            try:
                metadata = directory.lstat()
            except OSError as exc:
                raise SafeGitError(
                    f"candidate loose-object directory is unreadable: {exc}"
                ) from exc
            if not stat.S_ISDIR(metadata.st_mode):
                raise SafeGitError(f"candidate loose-object directory is unsafe: {directory}")
            for source in sorted(directory.iterdir(), key=lambda item: item.name):
                if not LOOSE_OBJECT_NAME.fullmatch(source.name):
                    raise SafeGitError(f"candidate loose-object path is malformed: {source}")
                _copy_regular(source, destination / directory.name / source.name)
        pack_dir = objects / "pack"
        if not pack_dir.exists():
            return
        try:
            pack_metadata = pack_dir.lstat()
            pack_entries = sorted(pack_dir.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise SafeGitError(f"candidate pack directory is unreadable: {exc}") from exc
        if not stat.S_ISDIR(pack_metadata.st_mode):
            raise SafeGitError("candidate pack directory is not a directory")
        for source in pack_entries:
            if source.suffix != ".pack":
                continue
            trusted_pack = self._base / "imports" / source.name
            _copy_regular(source, trusted_pack)
            try:
                with trusted_pack.open("rb") as pack:
                    completed = self._run_raw("index-pack", "--stdin", stdin=pack)
            except OSError as exc:
                raise SafeGitError(f"candidate pack cannot be imported: {exc}") from exc
            if completed.returncode != 0:
                raise SafeGitError("candidate pack is invalid")

    def _import_index(self, candidate_git_dir: Path) -> None:
        index = candidate_git_dir / "index"
        if not index.exists() and not index.is_symlink():
            raise SafeGitError("candidate index is missing")
        _copy_regular(index, self.git_dir / "index")
        for source in candidate_git_dir.iterdir():
            if SHARED_INDEX_NAME.fullmatch(source.name):
                _copy_regular(source, self.git_dir / source.name)

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        if not HEX40.fullmatch(ancestor) or not HEX40.fullmatch(descendant):
            return False
        completed = self._run_raw("merge-base", "--is-ancestor", ancestor, descendant)
        return completed.returncode == 0

    def changed_paths(self, ancestor: str, descendant: str) -> set[str] | None:
        if not HEX40.fullmatch(ancestor) or not HEX40.fullmatch(descendant):
            return None
        output = self.run("diff-tree", "--no-commit-id", "--name-only", "-r", ancestor, descendant)
        return None if output is None else {path for path in output.splitlines() if path}

    def status_porcelain(self) -> str | None:
        completed = self._run_raw(
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--ignore-submodules=all",
            work_tree=True,
        )
        if completed.returncode != 0:
            return None
        try:
            status_output = completed.stdout.decode("utf-8").rstrip("\n")
        except UnicodeDecodeError:
            return None
        if status_output:
            return status_output
        try:
            gitlinks = self._gitlinks()
            for path, expected in gitlinks:
                submodule_root = self.root.joinpath(*path.split("/"))
                metadata_dir = self._submodule_metadata(submodule_root)
                with SafeGitRepository(submodule_root, _metadata_dir=metadata_dir) as submodule:
                    if submodule.head != expected or submodule.status_porcelain():
                        return f" M {path}"
        except SafeGitError:
            return None
        return ""

    def ls_files_stage(self) -> tuple[tuple[str, str, str], ...]:
        """Every index entry as (mode, oid, path), validated for safe path text."""
        completed = self._run_raw("ls-files", "--stage", "-z")
        if completed.returncode != 0:
            raise SafeGitError("trusted index cannot be enumerated")
        out: list[tuple[str, str, str]] = []
        for entry in completed.stdout.split(b"\0"):
            if not entry:
                continue
            metadata, separator, raw_path = entry.partition(b"\t")
            fields = metadata.split()
            if not separator or len(fields) != INDEX_ENTRY_FIELDS:
                raise SafeGitError("candidate index entry is malformed")
            try:
                path = raw_path.decode("utf-8")
                mode = fields[0].decode("ascii")
                oid = fields[1].decode("ascii")
            except UnicodeDecodeError as exc:
                raise SafeGitError("candidate index path or object id is not text") from exc
            parts = path.split("/")
            if not HEX40.fullmatch(oid) or any(not part or part in {".", ".."} for part in parts):
                raise SafeGitError("candidate index entry is unsafe")
            out.append((mode, oid.lower(), path))
        return tuple(out)

    def _gitlinks(self) -> list[tuple[str, str]]:
        return [(path, oid) for mode, oid, path in self.ls_files_stage() if mode == "160000"]

    def _submodule_metadata(self, submodule_root: Path) -> Path:
        try:
            root_metadata = submodule_root.lstat()
        except OSError as exc:
            raise SafeGitError(f"candidate submodule is unavailable: {exc}") from exc
        if not stat.S_ISDIR(root_metadata.st_mode):
            raise SafeGitError("candidate submodule worktree is not a directory")
        control = submodule_root / ".git"
        try:
            text = _read_regular(control, maximum=4096).decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise SafeGitError("candidate submodule .git file is not UTF-8") from exc
        if not text.startswith("gitdir: "):
            raise SafeGitError("candidate submodule .git file is not a gitdir pointer")
        raw_target = Path(text.removeprefix("gitdir: "))
        unresolved = raw_target if raw_target.is_absolute() else submodule_root / raw_target
        try:
            target = unresolved.resolve(strict=True)
            allowed = (self._candidate_git_dir / "modules").resolve(strict=True)
            target.relative_to(allowed)
        except (OSError, ValueError) as exc:
            raise SafeGitError("candidate submodule gitdir escapes its parent metadata") from exc
        try:
            target_metadata = target.lstat()
        except OSError as exc:
            raise SafeGitError(f"candidate submodule gitdir is unavailable: {exc}") from exc
        if not stat.S_ISDIR(target_metadata.st_mode):
            raise SafeGitError("candidate submodule gitdir is not a directory")
        for forbidden in (
            target / "commondir",
            target / "objects" / "info" / "alternates",
            target / "objects" / "info" / "http-alternates",
        ):
            if forbidden.exists() or forbidden.is_symlink():
                raise SafeGitError("candidate submodule uses shared or alternate objects")
        return target

    def close(self) -> None:
        self._temporary.cleanup()

    def __enter__(self) -> SafeGitRepository:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
