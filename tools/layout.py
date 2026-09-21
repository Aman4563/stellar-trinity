"""Parent layout: incomplete or retired registration holds; crossed boundaries block.

A legitimate file named HARDNESS.md is a known basename false-positive and must
be renamed by the operator. solution/ is lawful bundle content, private at mount
time rather than forbidden at repository level.

A runner root that is itself a trinity project, one whose own .gitmodules registers a
checked-out trinity/ submodule carrying the gate, is that project's root and not a
boundary the parent may scan: its .audit/ belongs to its own CRUCIBLE and its layout
is its own gate's finding. The recognition rests on the registered gitlink, never on
report markdown at the root, so dropping AGENTS.md beside a leak exempts nothing.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final

__all__ = [
    "BLOCKING_CODES",
    "BUNDLE_FORBIDDEN",
    "KNOWN_ROOTS",
    "LAYOUT_CODES",
    "LAYOUT_ROSTER",
    "PARENT_LAYOUT_BOUNDARY_LEAK",
    "PARENT_LAYOUT_BRANCH_INVALID",
    "PARENT_LAYOUT_GITMODULES_INVALID",
    "PARENT_LAYOUT_PARENT_TRACKS_BUNDLE",
    "PARENT_LAYOUT_PLAIN_DIRECTORY",
    "PARENT_LAYOUT_RETIRED_ROOT",
    "PARENT_LAYOUT_RUNTIME_UNIGNORED",
    "PARENT_LAYOUT_SCAN_TRUNCATED",
    "PARENT_LAYOUT_SHARED_REMOTE",
    "PARENT_LAYOUT_SUBMODULE_MISSING",
    "PARENT_LAYOUT_SYMLINK",
    "PARENT_LAYOUT_UNKNOWN_SUBMODULE",
    "PROTECTED_ROOTS",
    "REQUIRED_ROOTS",
    "RETIRED_ROOTS",
    "SCAN_MAX_ENTRIES",
    "TRINITY_PROJECT_GATE",
    "Audience",
    "GitmodulesSection",
    "LayoutRoot",
    "RootKind",
    "ScanResult",
    "declared_paths",
    "is_bundle_shaped",
    "is_trinity_project_root",
    "parse_gitmodules",
    "scan_forbidden",
    "section_for",
]


class RootKind(StrEnum):
    TOOLING = "tooling"
    HARNESS = "harness"
    BUNDLE_PUBLIC = "bundle_public"
    BUNDLE_PRIVATE = "bundle_private"
    STAGING = "staging"
    RUNNER = "runner"


class Audience(StrEnum):
    VENDORED = "vendored"
    INSTRUMENT = "instrument"
    PUBLIC = "public"
    CORPUS = "corpus"


@dataclass(frozen=True, slots=True)
class LayoutRoot:
    path: str
    kind: RootKind
    required: bool
    audience: Audience
    forbidden: tuple[str, ...]


BUNDLE_FORBIDDEN: Final = (
    ".memory",
    ".seed",
    ".audit",
    ".trial",
    ".podium",
    "trinity",
    "requirements",
    "touchstones",
    "deliverables",
    ".secrets",
    ".trinity-runtime",
    "HARDNESS.md",
)
RETIRED_ROOTS: Final = ("deliverables",)
LAYOUT_ROSTER: Final[tuple[LayoutRoot, ...]] = (
    LayoutRoot("trinity", RootKind.TOOLING, True, Audience.VENDORED, ()),
    LayoutRoot(
        ".memory",
        RootKind.HARNESS,
        True,
        Audience.INSTRUMENT,
        (
            "BUNDLE_SHAPED",
            ".seed",
            ".audit",
            ".trial",
            ".podium",
            "trinity",
            "samples",
            "delivery",
            "deliverables",
        ),
    ),
    LayoutRoot("samples", RootKind.BUNDLE_PUBLIC, True, Audience.PUBLIC, BUNDLE_FORBIDDEN),
    LayoutRoot("delivery", RootKind.BUNDLE_PRIVATE, True, Audience.CORPUS, BUNDLE_FORBIDDEN),
    LayoutRoot(
        "harness",
        RootKind.RUNNER,
        True,
        Audience.PUBLIC,
        (
            ".memory",
            ".seed",
            ".audit",
            ".trial",
            ".podium",
            "trinity",
            "samples",
            "delivery",
            "deliverables",
            "requirements",
            "touchstones",
            "HARDNESS.md",
            ".secrets",
        ),
    ),
    LayoutRoot("staging", RootKind.STAGING, False, Audience.CORPUS, BUNDLE_FORBIDDEN),
)
REQUIRED_ROOTS: Final = tuple(root.path for root in LAYOUT_ROSTER if root.required)
KNOWN_ROOTS: Final = frozenset(root.path for root in LAYOUT_ROSTER)
PROTECTED_ROOTS: Final = tuple(root.path for root in LAYOUT_ROSTER if root.path != "trinity")
SCAN_MAX_ENTRIES: Final = 20_000
GITMODULES_MAX_BYTES: Final = 1 << 20
TRINITY_PROJECT_GATE: Final = "tools/gate.py"

PARENT_LAYOUT_GITMODULES_INVALID: Final = "PARENT_LAYOUT_GITMODULES_INVALID"
PARENT_LAYOUT_SUBMODULE_MISSING: Final = "PARENT_LAYOUT_SUBMODULE_MISSING"
PARENT_LAYOUT_PLAIN_DIRECTORY: Final = "PARENT_LAYOUT_PLAIN_DIRECTORY"
PARENT_LAYOUT_BRANCH_INVALID: Final = "PARENT_LAYOUT_BRANCH_INVALID"
PARENT_LAYOUT_RETIRED_ROOT: Final = "PARENT_LAYOUT_RETIRED_ROOT"
PARENT_LAYOUT_RUNTIME_UNIGNORED: Final = "PARENT_LAYOUT_RUNTIME_UNIGNORED"
PARENT_LAYOUT_SCAN_TRUNCATED: Final = "PARENT_LAYOUT_SCAN_TRUNCATED"
PARENT_LAYOUT_UNKNOWN_SUBMODULE: Final = "PARENT_LAYOUT_UNKNOWN_SUBMODULE"
PARENT_LAYOUT_SHARED_REMOTE: Final = "PARENT_LAYOUT_SHARED_REMOTE"
PARENT_LAYOUT_PARENT_TRACKS_BUNDLE: Final = "PARENT_LAYOUT_PARENT_TRACKS_BUNDLE"
PARENT_LAYOUT_BOUNDARY_LEAK: Final = "PARENT_LAYOUT_BOUNDARY_LEAK"
PARENT_LAYOUT_SYMLINK: Final = "PARENT_LAYOUT_SYMLINK"
BLOCKING_CODES: Final = frozenset(
    {
        PARENT_LAYOUT_UNKNOWN_SUBMODULE,
        PARENT_LAYOUT_SHARED_REMOTE,
        PARENT_LAYOUT_PARENT_TRACKS_BUNDLE,
        PARENT_LAYOUT_BOUNDARY_LEAK,
        PARENT_LAYOUT_SYMLINK,
    }
)
LAYOUT_CODES: Final = BLOCKING_CODES | frozenset(
    {
        PARENT_LAYOUT_GITMODULES_INVALID,
        PARENT_LAYOUT_SUBMODULE_MISSING,
        PARENT_LAYOUT_PLAIN_DIRECTORY,
        PARENT_LAYOUT_BRANCH_INVALID,
        PARENT_LAYOUT_RETIRED_ROOT,
        PARENT_LAYOUT_RUNTIME_UNIGNORED,
        PARENT_LAYOUT_SCAN_TRUNCATED,
    }
)
_SUBMODULE_HEAD: Final = re.compile(r"^\s*\[submodule\b")
_SUBMODULE_NAME: Final = re.compile(r'^\s*\[submodule\s+"([^"\n]+)"\]\s*(?:[#;].*)?$')
_GITMODULES_KEY: Final = re.compile(r"^\s*([A-Za-z][A-Za-z0-9-]*)\s*=\s*(.*?)\s*$")
_UUID5: Final = re.compile(
    r"\A[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)


@dataclass(frozen=True, slots=True)
class GitmodulesSection:
    name: str
    keys: Mapping[str, str]

    @property
    def path(self) -> str:
        """Return the declared path, or an empty string when absent."""
        return self.keys.get("path", "")

    @property
    def url(self) -> str:
        """Return the declared remote, or an empty string when absent."""
        return self.keys.get("url", "")

    @property
    def branch(self) -> str:
        """Return the declared branch, or an empty string when absent."""
        return self.keys.get("branch", "")

    @property
    def update(self) -> str:
        """Return the declared update policy, or an empty string when absent."""
        return self.keys.get("update", "")


def parse_gitmodules(text: str) -> tuple[tuple[GitmodulesSection, ...], tuple[str, ...]]:
    """Parse first-wins submodule keys and report malformed or incomplete sections."""
    sections: list[GitmodulesSection] = []
    malformed: list[str] = []
    keys: dict[str, str] | None = None
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("["):
            keys = None
            if _SUBMODULE_HEAD.match(line):
                if header := _SUBMODULE_NAME.fullmatch(line):
                    keys = {}
                    sections.append(GitmodulesSection(header[1], MappingProxyType(keys)))
                else:
                    malformed.append(f"line {number}: malformed submodule header")
        elif keys is not None and line.strip() and not line.lstrip().startswith(("#", ";")):
            if key := _GITMODULES_KEY.fullmatch(line):
                if key[1].lower() in keys:
                    malformed.append(f'section "{sections[-1].name}" repeats key {key[1].lower()}')
                keys.setdefault(key[1].lower(), key[2])
            else:
                malformed.append(f"line {number}: malformed submodule key")
    for section in sections:
        missing = tuple(key for key in ("path", "url") if not section.keys.get(key))
        if missing:
            malformed.append(f"submodule {section.name!r}: missing {', '.join(missing)}")
    return tuple(sections), tuple(malformed)


def section_for(sections: Sequence[GitmodulesSection], wanted: str) -> GitmodulesSection | None:
    """Return the first section whose declared path starts with the wanted segment."""
    return next(
        (section for section in sections if section.path.strip("/").split("/", 1)[0] == wanted),
        None,
    )


def declared_paths(sections: Sequence[GitmodulesSection]) -> frozenset[str]:
    """Return the nonempty first path segments declared by the sections."""
    return frozenset(
        section.path.strip("/").split("/", 1)[0] for section in sections if section.path.strip("/")
    )


def is_bundle_shaped(name: str) -> bool:
    """Recognize the lowercase UUID5 directory-name shape used for task bundles."""
    return _UUID5.fullmatch(name) is not None


def _is_regular(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink()
    except OSError:
        return False


def is_trinity_project_root(checkout: Path) -> bool:
    """Recognize a checkout that is itself a trinity project root.

    True only when the checkout is a git checkout whose own ``.gitmodules`` registers
    the ``trinity`` submodule at exactly ``trinity`` and that submodule is checked out
    with the gate inside it. Symlinks anywhere on that path answer false, and so does
    any root report or agent markdown, which proves nothing about ownership.
    """
    try:
        metadata = checkout / ".git"
        if metadata.is_symlink() or not (metadata.is_dir() or metadata.is_file()):
            return False
        gitmodules = checkout / ".gitmodules"
        if not _is_regular(gitmodules) or gitmodules.stat().st_size > GITMODULES_MAX_BYTES:
            return False
        sections, _ = parse_gitmodules(gitmodules.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return False
    section = section_for(sections, "trinity")
    if section is None or section.path.strip("/") != "trinity":
        return False
    vendored = checkout / "trinity"
    try:
        if vendored.is_symlink() or not vendored.is_dir():
            return False
        vendored_metadata = vendored / ".git"
        if vendored_metadata.is_symlink() or not (
            vendored_metadata.is_dir() or vendored_metadata.is_file()
        ):
            return False
    except OSError:
        return False
    return _is_regular(vendored / TRINITY_PROJECT_GATE)


@dataclass(frozen=True, slots=True)
class ScanResult:
    leaks: tuple[str, ...]
    symlinks: tuple[str, ...]
    truncated: bool
    entries: int
    unreadable: tuple[str, ...] = ()


def scan_forbidden(
    checkout: Path, forbidden: Sequence[str], *, max_entries: int = SCAN_MAX_ENTRIES
) -> ScanResult:
    """Scan bounded checkout entries without following symlinks or entering .git."""
    leaks: list[str] = []
    symlinks: list[str] = []
    unreadable: list[str] = []
    pending = [checkout]
    entries = 0
    truncated = False
    directories = frozenset(name for name in forbidden if "." not in name.lstrip("."))
    basenames = frozenset(forbidden) - directories
    while pending and entries <= max_entries:
        directory = pending.pop()
        try:
            with os.scandir(directory) as children:
                for entry in children:
                    entries += 1
                    if entries > max_entries:
                        truncated = True
                        break
                    if entry.name == ".git":
                        continue
                    relative = Path(entry.path).relative_to(checkout)
                    if entry.is_symlink():
                        symlinks.append(relative.as_posix())
                        continue
                    is_directory = entry.is_dir(follow_symlinks=False)
                    directory_parts = relative.parts if is_directory else relative.parts[:-1]
                    if (
                        directories.intersection(directory_parts)
                        or entry.name in basenames
                        or (
                            "BUNDLE_SHAPED" in forbidden
                            and any(is_bundle_shaped(part) for part in directory_parts)
                        )
                    ):
                        leaks.append(relative.as_posix())
                    if is_directory:
                        pending.append(Path(entry.path))
        except OSError:
            truncated = True
            unreadable.append(directory.relative_to(checkout).as_posix())
    return ScanResult(
        tuple(sorted(leaks)), tuple(sorted(symlinks)), truncated, entries, tuple(sorted(unreadable))
    )
