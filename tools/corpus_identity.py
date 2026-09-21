#!/usr/bin/env python3
"""Hold the shared research corpus to ENGRAM invariant E10.

E10 and Phase H step 2d state that every `research/` entry is a side-by-side
pair under one `<source-class>/<canonical-id>-<slug>` stem, that the rendering
is derived from the retained bytes by a named tool at a pinned version, and
that the tool identity, its version, and the ENGRAM-computed content digest
are recorded beside the pair. Nothing executed any of that. This module does.

The recorded deriving tool is a declaration this module holds present and
non-empty; it never re-derives a rendering and never calls an external
converter, because the harness declares no runtime dependency. A pair whose
deriving tool no repository byte establishes records the closed token
`unestablished`, whose meaning is exactly that, and that residual obligation
is registered in DEFERRED.md rather than hidden behind a passing check.

The closed record one pair carries lives in `corpus_identity_manifest.py`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools._findings import Finding, render_finding, serialize_findings
    from tools.corpus_identity_manifest import MANIFEST_SUFFIX, finding, validate, write_manifest
else:
    try:
        from tools._findings import Finding, render_finding, serialize_findings
        from tools.corpus_identity_manifest import (
            MANIFEST_SUFFIX,
            finding,
            validate,
            write_manifest,
        )
    except ModuleNotFoundError:
        from _findings import Finding, render_finding, serialize_findings
        from corpus_identity_manifest import MANIFEST_SUFFIX, finding, validate, write_manifest

USAGE = (
    "usage: corpus_identity.py [check|json] [--root PATH]\n"
    "       corpus_identity.py record [--root PATH] [--tool NAME] [--tool-version VERSION]\n"
    "                                 [--stem STEM ...]"
)
CLEAN = "clean: every research artifact is a digest-bound pair"
RESEARCH = "research"
RENDERING_SUFFIX = ".md"
UNESTABLISHED = "unestablished"
RECORD_MODE = "record"
JSON_MODE = "json"
MODES = {"check", JSON_MODE, RECORD_MODE}
MIN_ARGV = 2
FLAG_ARGUMENTS = 2
SOURCE_CLASSES: frozenset[str] = frozenset(
    {"paper", "institute", "board", "lab", "aggregator", "engineering", "hosted", "lead"}
)


@dataclass(frozen=True, slots=True)
class Invocation:
    mode: str
    root: Path
    tool: str
    version: str
    stems: tuple[str, ...]


def classes(root: Path) -> tuple[list[Path], list[Finding]]:
    """Return every source-class directory under `research/` and every layout refusal."""
    research = root / RESEARCH
    directories: list[Path] = []
    findings: list[Finding] = []
    if not research.is_dir():
        return directories, findings
    for entry in sorted(research.iterdir()):
        if entry.is_file():
            message = "a loose artifact sits outside every source class"
            findings.append(finding(entry, message, "CORPUS_LOOSE_ARTIFACT"))
        elif entry.name not in SOURCE_CLASSES:
            message = f'"{entry.name}" is not one of the closed ENGRAM source classes'
            findings.append(finding(entry, message, "CORPUS_UNKNOWN_CLASS"))
        else:
            directories.append(entry)
    return directories, findings


def pairs(directory: Path) -> tuple[list[tuple[Path, Path]], list[Finding]]:
    """Return every retained-and-rendered pair in one source class, plus every half pair."""
    grouped: dict[str, list[Path]] = {}
    for entry in sorted(directory.iterdir()):
        if entry.is_file() and not entry.name.endswith(MANIFEST_SUFFIX):
            grouped.setdefault(entry.stem, []).append(entry)
    found: list[tuple[Path, Path]] = []
    findings: list[Finding] = []
    for stem, entries in sorted(grouped.items()):
        rendering = directory / f"{stem}{RENDERING_SUFFIX}"
        retained = [entry for entry in entries if entry != rendering]
        if not rendering.is_file():
            message = f"retained source bytes carry no derived {RENDERING_SUFFIX} rendering"
            findings.extend(finding(e, message, "CORPUS_RENDERING_MISSING") for e in retained)
        elif not retained:
            message = "a rendering stands with no retained source bytes under its stem"
            findings.append(finding(rendering, message, "CORPUS_RETAINED_MISSING"))
        else:
            found.extend((entry, rendering) for entry in retained)
    return found, findings


def survey(root: Path) -> tuple[list[tuple[Path, Path]], list[Path], list[Finding]]:
    """Return every pair, every source class, and every layout refusal under `root`."""
    directories, findings = classes(root)
    found: list[tuple[Path, Path]] = []
    for directory in directories:
        located, problems = pairs(directory)
        findings.extend(problems)
        found.extend(located)
    return found, directories, findings


def inspect(root: Path) -> list[Finding]:
    """Return every E10 refusal the research corpus under `root` earns."""
    found, _, findings = survey(root)
    for retained, rendering in found:
        findings.extend(validate(retained, rendering))
    return findings


def summary(root: Path) -> str:
    """Return the one-line corpus census every check mode prints beside its verdict."""
    found, directories, _ = survey(root)
    return f"corpus: {len(found)} pair(s) across {len(directories)} source class(es)"


def record(root: Path, tool: str, version: str, stems: tuple[str, ...]) -> int:
    """Write one sidecar per selected pair, never overwriting a record already on disk."""
    found, _, _ = survey(root)
    written = 0
    for retained, rendering in found:
        if stems and retained.stem not in stems:
            continue
        if write_manifest(retained, rendering, tool, version):
            written += 1
    print(f"recorded {written} manifest(s) naming {tool} at version {version}")
    if written:
        return 0
    print(f"refused: every selected pair under {root / RESEARCH} already records its identity")
    return 1


def parse_args(argv: list[str]) -> Invocation | None:
    """Parse the command line the way every sibling linter does, without argparse."""
    if len(argv) < MIN_ARGV or argv[1] not in MODES:
        return None
    mode = argv[1]
    root = Path.cwd()
    tool = UNESTABLISHED
    version = UNESTABLISHED
    stems: list[str] = []
    args = argv[2:]
    index = 0
    while index < len(args):
        if len(args) - index < FLAG_ARGUMENTS:
            return None
        flag, value = args[index], args[index + 1]
        if flag == "--root":
            root = Path(value)
        elif flag == "--tool" and mode == RECORD_MODE:
            tool = value
        elif flag == "--tool-version" and mode == RECORD_MODE:
            version = value
        elif flag == "--stem" and mode == RECORD_MODE:
            stems.append(value)
        else:
            return None
        index += FLAG_ARGUMENTS
    return Invocation(mode, root, tool, version, tuple(stems))


def main(argv: list[str]) -> int:
    parsed = parse_args(argv)
    if parsed is None:
        print(USAGE)
        return 2
    if parsed.mode == RECORD_MODE:
        return record(parsed.root, parsed.tool, parsed.version, parsed.stems)
    findings = inspect(parsed.root)
    if parsed.mode == JSON_MODE:
        print(serialize_findings(findings))
        print(summary(parsed.root), file=sys.stderr)
        return 1 if findings else 0
    if findings:
        for problem in findings:
            print(render_finding(problem))
        print(f"\n{len(findings)} violation(s)")
    else:
        print(CLEAN)
    print(summary(parsed.root))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
