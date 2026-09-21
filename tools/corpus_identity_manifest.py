#!/usr/bin/env python3
"""The closed `engram.identity/v1` record one research pair carries beside it.

This is the manifest layer of the E10 checker: the digest ENGRAM computes over
retained bytes, the closed field set the sidecar carries, and the refusals a
sidecar earns when it does not bind the exact bytes under the exact stem it
names. `corpus_identity.py` walks the corpus and owns the command line; this
module owns one pair's record. Neither ever re-derives a rendering.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools._findings import Finding, Severity
else:
    try:
        from tools._findings import Finding, Severity
    except ModuleNotFoundError:
        from _findings import Finding, Severity

SCHEMA = "engram.identity/v1"
MANIFEST_SUFFIX = ".identity.json"
FIELDS: tuple[str, ...] = (
    "schema",
    "source_class",
    "stem",
    "retained",
    "rendering",
    "content_digest",
    "rendering_digest",
    "deriving_tool",
    "deriving_tool_version",
)


def finding(path: Path, message: str, code: str) -> Finding:
    """Return one corpus refusal, always an error, always located by path alone."""
    return Finding(code, Severity.ERROR, str(path), None, message)


def digest(path: Path) -> str:
    """Return the SHA-256 ENGRAM computes over an artifact's retained bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_for(retained: Path) -> Path:
    """Return the sidecar path that records one pair's identity beside it."""
    return retained.with_name(f"{retained.stem}{MANIFEST_SUFFIX}")


def manifest_payload(retained: Path, rendering: Path, tool: str, version: str) -> dict[str, str]:
    """Build the closed `engram.identity/v1` record for one retained and rendered pair."""
    return {
        "schema": SCHEMA,
        "source_class": retained.parent.name,
        "stem": retained.stem,
        "retained": retained.name,
        "rendering": rendering.name,
        "content_digest": digest(retained),
        "rendering_digest": digest(rendering),
        "deriving_tool": tool,
        "deriving_tool_version": version,
    }


def write_manifest(retained: Path, rendering: Path, tool: str, version: str) -> bool:
    """Write the sidecar beside the pair, declining to overwrite a record already there."""
    path = manifest_for(retained)
    if path.exists():
        return False
    payload = manifest_payload(retained, rendering, tool, version)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return True


def read_manifest(path: Path) -> tuple[dict[str, str] | None, list[Finding]]:
    """Return one pair's closed identity record, or the refusal its bytes earn."""
    if not path.is_file():
        message = "the pair records no deriving tool, version, or content digest beside it"
        return None, [finding(path, message, "CORPUS_MANIFEST_MISSING")]
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        message = f"the manifest is unreadable: {exc.__class__.__name__}: {exc}"
        return None, [finding(path, message, "CORPUS_MANIFEST_MALFORMED")]
    if not isinstance(parsed, dict) or sorted(parsed) != sorted(FIELDS):
        message = f"the manifest field set is not exactly: {', '.join(FIELDS)}"
        return None, [finding(path, message, "CORPUS_MANIFEST_MALFORMED")]
    record: dict[str, str] = {str(key): str(value) for key, value in parsed.items()}
    if record["schema"] != SCHEMA:
        message = f'the manifest schema is "{record["schema"]}" rather than {SCHEMA}'
        return None, [finding(path, message, "CORPUS_MANIFEST_MALFORMED")]
    return record, []


def validate(retained: Path, rendering: Path) -> list[Finding]:
    """Refuse a pair whose manifest does not bind these exact bytes under this exact stem."""
    path = manifest_for(retained)
    record, findings = read_manifest(path)
    if record is None:
        return findings
    named = {
        "source_class": retained.parent.name,
        "stem": retained.stem,
        "retained": retained.name,
        "rendering": rendering.name,
    }
    drifted = sorted(key for key, value in named.items() if record[key] != value)
    if drifted:
        message = f"the manifest names another pair; {', '.join(drifted)} disagree with the path"
        findings.append(finding(path, message, "CORPUS_STEM_MISMATCH"))
    if record["content_digest"] != digest(retained):
        message = f"{retained.name} no longer hashes to the recorded content_digest"
        findings.append(finding(path, message, "CORPUS_DIGEST_MISMATCH"))
    if record["rendering_digest"] != digest(rendering):
        message = f"{rendering.name} no longer hashes to the recorded rendering_digest"
        findings.append(finding(path, message, "CORPUS_RENDERING_DIGEST_MISMATCH"))
    if not record["deriving_tool"] or not record["deriving_tool_version"]:
        message = "the deriving tool identity or its pinned version is recorded empty"
        findings.append(finding(path, message, "CORPUS_TOOL_UNRECORDED"))
    return findings
