"""Descriptor-relative reads: no untrusted path component is followed as a symlink."""

import os
import stat
from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

from .reading import TraceReadError


@dataclass(frozen=True, slots=True)
class DirectoryDescriptor(AbstractContextManager[int]):
    descriptor: int

    def __enter__(self) -> int:
        return self.descriptor

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        os.close(self.descriptor)


def directory_fd(path: Path, *, project_root: Path, create: bool = False) -> DirectoryDescriptor:
    """Retain each directory until its child is opened with O_NOFOLLOW."""
    root = project_root.absolute()
    absolute = path.absolute()
    try:
        parts = absolute.relative_to(root).parts
    except ValueError as error:
        raise TraceReadError from error
    if ".." in parts:
        raise TraceReadError
    with ExitStack() as handles:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        handles.callback(os.close, descriptor)
        for part in parts:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    if not stat.S_ISDIR(
                        os.stat(part, dir_fd=descriptor, follow_symlinks=False).st_mode
                    ):
                        raise TraceReadError from None
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            handles.callback(os.close, child)
            descriptor = child
        retained = os.dup(descriptor)
    return DirectoryDescriptor(retained)


def read_regular(path: Path, *, project_root: Path, max_bytes: int) -> bytes:
    """Refuse nonregular or oversized files on the opened descriptor before reading."""
    with directory_fd(path.parent, project_root=project_root) as parent:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
                raise TraceReadError
            raw = stream.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise TraceReadError
            return raw
