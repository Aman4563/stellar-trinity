"""Harbor format-currency gate: exact pin, never stale, proven by Harbor's own validator.

The harness stays stdlib-only, so Harbor is never imported here. Validation runs Harbor's
``TaskConfig`` in an isolated ``uv`` interpreter and leaves a digest-bound receipt per bundle
that the two checks below consume. ``resolve`` snapshots the latest stable release from PyPI
into ``harbor.lock`` at the parent root; every other operation is decidable from disk.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib import request


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING:
    from tools._findings import Finding, Severity, render_finding, serialize_findings
    from tools.project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
else:
    try:
        from tools._findings import Finding, Severity, render_finding, serialize_findings
        from tools.project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        from _findings import Finding, Severity, render_finding, serialize_findings
        from project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )

PYPI_URL = "https://pypi.org/pypi/harbor/json"
LOCK_FILE = "harbor.lock"
CONTRACT_PATH = Path(".seed/contract.yaml")
RECEIPT_DIR = Path(".audit/receipts/harbor")
BUNDLE_ROOTS: tuple[str, ...] = ("staging", "samples", "delivery")
LOCK_STALE_DAYS = 14
PIN_STALE_DAYS = 30
PIN_MINOR_LAG = 1
FETCH_TIMEOUT_SECONDS = 10
VALIDATOR_TIMEOUT_SECONDS = 600
VALIDATOR_PYTHON = "3.12"
DEFAULT_SCHEMA_VERSION = "1.4"
DEFAULT_ORG = "ethara"
NETWORK_LEGACY = "none"
NETWORK_CANONICAL = "no-network"
RETIRED_PIN_KEY = "harbor_version"
PIN_KEYS: tuple[str, ...] = ("harbor_release", RETIRED_PIN_KEY)

EXACT_RELEASE = re.compile(r"\A(\d+)\.(\d+)\.(\d+)\Z")
UUID_DIR = re.compile(
    r"\A[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)
SHA256_HEX = re.compile(r"\A[0-9a-f]{64}\Z")

# Fixed validator script, sent on stdin to the isolated interpreter. Its digest is recorded
# in every receipt so a receipt produced by a different validator surface is refused.
VALIDATOR_SCRIPT = """\
import importlib.metadata
import json
import sys
import tomllib

from harbor.models.task.config import TaskConfig

print(json.dumps({"harbor": importlib.metadata.version("harbor")}))
for path in sys.argv[1:]:
    try:
        with open(path, "rb") as stream:
            data = tomllib.load(stream)
    except Exception as exc:  # noqa: BLE001 - report every parse failure verbatim
        print(json.dumps({"path": path, "ok": False, "message": f"TOML: {exc}"}))
        continue
    try:
        TaskConfig.model_validate(data)
    except Exception as exc:  # noqa: BLE001 - Harbor's message travels verbatim
        print(json.dumps({"path": path, "ok": False, "message": str(exc)}))
    else:
        print(json.dumps({"path": path, "ok": True, "message": ""}))
"""
VALIDATOR_DIGEST = hashlib.sha256(VALIDATOR_SCRIPT.encode("utf-8")).hexdigest()

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class HarborError(Exception):
    """A CLI-level failure with a stable exit code."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True, slots=True)
class Lock:
    latest_version: str
    latest_released_at: datetime
    resolved_at: datetime
    source: str


@dataclass(frozen=True, slots=True)
class Pin:
    version: str | None
    source: str
    finding: Finding | None


@dataclass(frozen=True, slots=True)
class Receipt:
    harbor_version: str
    task_toml_sha256: str
    ok: bool
    message: str
    validated_at: str
    validator_digest: str


@dataclass(frozen=True, slots=True)
class ValidationRun:
    receipts: dict[str, Receipt]
    error: str | None


def _error(path: Path, message: str, code: str) -> Finding:
    return Finding(code, Severity.ERROR, str(path), 0, message)


def _advisory(path: Path, message: str, code: str) -> Finding:
    return Finding(code, Severity.ADVISORY, str(path), 0, message)


def _now(evaluation_time: datetime | None) -> datetime:
    if evaluation_time is None:
        return datetime.now(UTC)
    if evaluation_time.tzinfo is None:
        return evaluation_time.replace(tzinfo=UTC)
    return evaluation_time


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _release_tuple(version: str) -> tuple[int, int, int] | None:
    match = EXACT_RELEASE.match(version)
    if match is None:
        return None
    major, minor, patch = (int(group) for group in match.groups())
    return major, minor, patch


def bundles(root: Path) -> list[Path]:
    """Every uuid-named bundle directory under the task lane roots, sorted by lane then name."""
    found: list[Path] = []
    for lane in BUNDLE_ROOTS:
        lane_root = root / lane
        if not lane_root.is_dir():
            continue
        matches = (
            path for path in lane_root.iterdir() if path.is_dir() and UUID_DIR.match(path.name)
        )
        found.extend(sorted(matches, key=lambda path: path.name))
    return found


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---- harbor.lock -----------------------------------------------------------


def _stable_releases(document: dict[str, Any]) -> list[tuple[tuple[int, int, int], str, datetime]]:
    releases = document.get("releases")
    if not isinstance(releases, dict):
        return []
    stable: list[tuple[tuple[int, int, int], str, datetime]] = []
    for version, files in releases.items():
        parsed = _release_tuple(str(version))
        if parsed is None or not isinstance(files, list) or not files:
            continue
        uploads = [
            moment
            for entry in files
            if isinstance(entry, dict)
            for moment in [_parse_iso(entry.get("upload_time_iso_8601"))]
            if moment is not None
        ]
        if not uploads:
            continue
        stable.append((parsed, str(version), max(uploads)))
    return stable


def read_lock(root: Path) -> Lock:
    path = root / LOCK_FILE
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HarborError(f"{path}: harbor.lock is missing or malformed: {exc}") from exc
    if not isinstance(document, dict):
        raise HarborError(f"{path}: harbor.lock must be a JSON object")
    version = document.get("latest_version")
    released = _parse_iso(document.get("latest_released_at"))
    resolved = _parse_iso(document.get("resolved_at"))
    source = document.get("source")
    if (
        not isinstance(version, str)
        or _release_tuple(version) is None
        or released is None
        or resolved is None
        or not isinstance(source, str)
    ):
        raise HarborError(f"{path}: harbor.lock fields are missing or malformed")
    return Lock(version, released, resolved, source)


def resolve(root: Path, *, offline: bool = False, now: datetime | None = None) -> Lock:
    """Snapshot the latest stable Harbor release into ``harbor.lock`` at the parent root."""
    if offline:
        return read_lock(root)
    try:
        with request.urlopen(PYPI_URL, timeout=FETCH_TIMEOUT_SECONDS) as response:
            document = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise HarborError(f"cannot resolve the latest Harbor release from PyPI: {exc}") from exc
    if not isinstance(document, dict):
        raise HarborError("PyPI response is not a JSON object")
    stable = _stable_releases(document)
    if not stable:
        raise HarborError("PyPI response lists no stable Harbor release")
    _, version, released = max(stable)
    lock = Lock(version, released, _now(now), "pypi")
    payload = {
        "latest_version": lock.latest_version,
        "latest_released_at": _iso(lock.latest_released_at),
        "resolved_at": _iso(lock.resolved_at),
        "source": lock.source,
    }
    (root / LOCK_FILE).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return lock


# ---- the pin ----------------------------------------------------------------


def _yaml_scalar(text: str, path: Sequence[str]) -> str | None:
    """Read one nested scalar from a block-style YAML mapping without a YAML library."""
    level = 0
    parent_indent = -1
    child_indent: int | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if level > 0 and indent <= parent_indent:
            return None
        if child_indent is None:
            child_indent = indent
        if indent != child_indent:
            continue
        key, separator, value = line.strip().partition(":")
        if not separator or key.strip() != path[level]:
            continue
        if level == len(path) - 1:
            scalar = value.strip().strip("'\"")
            return scalar or None
        if value.strip():
            return None
        level += 1
        parent_indent = indent
        child_indent = None
    return None


def pin(root: Path) -> Pin:
    """Resolve the pinned Harbor release from ``.seed/contract.yaml`` or the bundle manifests."""
    contract = root / CONTRACT_PATH
    manifests = [bundle / "task.toml" for bundle in bundles(root)]
    for key in PIN_KEYS:
        if contract.is_file():
            try:
                value = _yaml_scalar(contract.read_text(encoding="utf-8"), ("delivery", key))
            except (OSError, UnicodeDecodeError) as exc:
                message = f"contract is unreadable: {exc}"
                return Pin(None, str(contract), _error(contract, message, "HARBOR_PIN_MALFORMED"))
            if value is not None:
                return _validate_pin(contract, value, f"delivery.{key}")
    for manifest in manifests:
        try:
            with manifest.open("rb") as stream:
                document = tomllib.load(stream)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        metadata = document.get("metadata")
        candidates: list[tuple[str, object]] = [(key, document.get(key)) for key in PIN_KEYS]
        if isinstance(metadata, dict):
            candidates += [(f"metadata.{key}", metadata.get(key)) for key in PIN_KEYS]
        for label, candidate in candidates:
            if isinstance(candidate, str):
                return _validate_pin(manifest, candidate, label)
    location = contract if contract.is_file() or not manifests else manifests[0]
    message = (
        "no Harbor release pin: declare delivery.harbor_release in .seed/contract.yaml "
        "as one exact X.Y.Z release"
    )
    return Pin(None, str(location), _error(location, message, "HARBOR_PIN_MISSING"))


def _validate_pin(location: Path, value: str, label: str) -> Pin:
    if label.endswith(RETIRED_PIN_KEY):
        message = (
            f"{label} uses the retired spelling harbor_version; declare delivery.harbor_release"
        )
        return Pin(None, str(location), _error(location, message, "HARBOR_PIN_MALFORMED"))
    if _release_tuple(value) is None:
        message = (
            f"{label} = {value!r} is not one exact X.Y.Z release: floating specifiers, "
            "development builds, and latest are refused"
        )
        return Pin(None, str(location), _error(location, message, "HARBOR_PIN_MALFORMED"))
    return Pin(value, str(location), None)


# ---- receipts and validation ---------------------------------------------------


def receipt_path(root: Path, uuid: str) -> Path:
    return root / RECEIPT_DIR / f"{uuid}.json"


def read_receipt(path: Path) -> Receipt | None:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    version = document.get("harbor_version")
    digest = document.get("task_toml_sha256")
    ok = document.get("ok")
    message = document.get("message")
    validated_at = document.get("validated_at")
    validator = document.get("validator_digest")
    if (
        not isinstance(version, str)
        or not isinstance(digest, str)
        or SHA256_HEX.match(digest) is None
        or not isinstance(ok, bool)
        or not isinstance(message, str)
        or not isinstance(validated_at, str)
        or not isinstance(validator, str)
    ):
        return None
    return Receipt(version, digest, ok, message, validated_at, validator)


def _write_receipt(path: Path, receipt: Receipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "harbor_version": receipt.harbor_version,
        "task_toml_sha256": receipt.task_toml_sha256,
        "ok": receipt.ok,
        "message": receipt.message,
        "validated_at": receipt.validated_at,
        "validator_digest": receipt.validator_digest,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def validator_command(version: str, manifests: Sequence[Path]) -> list[str]:
    return [
        "uv",
        "run",
        "--no-project",
        "--quiet",
        "--python",
        VALIDATOR_PYTHON,
        "--with",
        f"harbor=={version}",
        "python",
        "-",
        *(str(path) for path in manifests),
    ]


def validate(
    root: Path,
    version: str,
    uuids: Sequence[str] | None = None,
    *,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
) -> ValidationRun:
    """Run Harbor's own manifest validator in an isolated interpreter and write receipts."""
    if _release_tuple(version) is None:
        return ValidationRun({}, f"{version!r} is not one exact X.Y.Z release")
    selected = [bundle for bundle in bundles(root) if uuids is None or bundle.name in uuids]
    manifests = [bundle / "task.toml" for bundle in selected]
    if not manifests:
        return ValidationRun({}, "no bundle manifests to validate")
    if shutil.which("uv") is None:
        return ValidationRun({}, "uv is not installed, so the isolated validator cannot run")
    try:
        completed = runner(
            validator_command(version, manifests),
            input=VALIDATOR_SCRIPT,
            capture_output=True,
            text=True,
            shell=False,
            timeout=VALIDATOR_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ValidationRun({}, f"isolated validator did not run: {exc}")
    results: dict[str, dict[str, Any]] = {}
    installed: str | None = None
    for line in completed.stdout.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        if "harbor" in record and isinstance(record["harbor"], str):
            installed = record["harbor"]
        elif isinstance(record.get("path"), str):
            results[record["path"]] = record
    if installed != version:
        detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
        return ValidationRun(
            {}, f"isolated validator did not report harbor=={version}: {detail[:400]}"
        )
    validated_at = _iso(_now(now))
    receipts: dict[str, Receipt] = {}
    for bundle, manifest in zip(selected, manifests, strict=True):
        record = results.get(str(manifest))
        if record is None:
            return ValidationRun({}, f"validator produced no result for {manifest}")
        receipt = Receipt(
            harbor_version=version,
            task_toml_sha256=sha256_file(manifest),
            ok=bool(record.get("ok")),
            message=str(record.get("message", "")),
            validated_at=validated_at,
            validator_digest=VALIDATOR_DIGEST,
        )
        _write_receipt(receipt_path(root, bundle.name), receipt)
        receipts[bundle.name] = receipt
    return ValidationRun(receipts, None)


# ---- migration --------------------------------------------------------------

_AUTHORS_START = re.compile(r"^(\s*)authors\s*=\s*\[", re.MULTILINE)
# A bare string element is preceded by the opening bracket or a comma, never by `=`,
# so email strings already inside `{ name = ..., email = ... }` tables stay untouched.
_STRING_AUTHOR = re.compile(r'([\[,]\s*)"([^"@\s]+)@([^"\s]+)"')
_TABLE_AUTHOR = re.compile(r"\{\s*email\s*=\s*\"([^\"@\s]+)@([^\"\s]+)\"\s*\}")
_NETWORK_NONE = re.compile(r'^(\s*network_mode\s*=\s*)"none"', re.MULTILINE)
_SCHEMA_LINE = re.compile(r'^schema_version\s*=\s*"[^"]*"', re.MULTILINE)
_SECTION = re.compile(r"^\[([^\]]+)\]\s*$")


def _migrate_authors(block: str) -> str:
    def string_author(match: re.Match[str]) -> str:
        prefix, local, domain = match.group(1), match.group(2), match.group(3)
        return f'{prefix}{{ name = "{local}", email = "{local}@{domain}" }}'

    def table_author(match: re.Match[str]) -> str:
        local, domain = match.group(1), match.group(2)
        return f'{{ name = "{local}", email = "{local}@{domain}" }}'

    block = _TABLE_AUTHOR.sub(table_author, block)
    return _STRING_AUTHOR.sub(string_author, block)


def _split_sections(text: str) -> list[tuple[str | None, list[str]]]:
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in text.splitlines():
        header = _SECTION.match(line)
        if header is not None:
            sections.append((header.group(1).strip(), [line]))
        else:
            sections[-1][1].append(line)
    return sections


def _has_key(lines: Sequence[str], key: str) -> bool:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    return any(pattern.match(line) for line in lines)


def migrate_text(text: str, *, org: str, slug: str) -> str:
    """Apply the seven-step recipe textually so only failing keys move."""
    sections = _split_sections(text)
    rebuilt: list[str] = []
    saw_task = False
    for name, lines in sections:
        body = list(lines)
        if name == "task":
            saw_task = True
            insert_at = 1
            if not _has_key(body, "name"):
                body.insert(insert_at, f'name = "{org}/{slug}"')
                insert_at += 1
            if not _has_key(body, "version"):
                body.insert(insert_at, 'version = "1.0.0"')
            joined = "\n".join(body)
            start = _AUTHORS_START.search(joined)
            if start is not None:
                close = joined.find("]", start.end())
                if close != -1:
                    opening = start.end() - 1
                    joined = (
                        joined[:opening] + _migrate_authors(joined[opening:close]) + joined[close:]
                    )
            body = joined.split("\n")
        if name == "metadata":
            body = [line for line in body if not re.match(r"^\s*harbor_version\s*=", line)]
        rebuilt.extend(body)
    result = "\n".join(rebuilt)
    if not text.endswith("\n") and result.endswith("\n"):
        result = result.rstrip("\n")
    if text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    result = _NETWORK_NONE.sub(rf'\1"{NETWORK_CANONICAL}"', result)
    if _SCHEMA_LINE.search(result):
        result = _SCHEMA_LINE.sub(f'schema_version = "{DEFAULT_SCHEMA_VERSION}"', result, count=1)
    else:
        result = f'schema_version = "{DEFAULT_SCHEMA_VERSION}"\n\n' + result.lstrip("\n")
    if not saw_task:
        result = result.rstrip("\n") + f'\n\n[task]\nname = "{org}/{slug}"\nversion = "1.0.0"\n'
    return result


def migrate(root: Path, uuid: str, *, dry_run: bool = True, org: str = DEFAULT_ORG) -> str:
    """Migrate one bundle manifest to the current shape; return the unified diff."""
    manifest = root / "samples" / uuid / "task.toml"
    if not manifest.is_file():
        manifest = root / "delivery" / uuid / "task.toml"
    if not manifest.is_file():
        raise HarborError(f"no task.toml for bundle {uuid} under {root}")
    before = manifest.read_text(encoding="utf-8")
    slug = f"{root.resolve().name}-{uuid[:8]}"
    after = migrate_text(before, org=org, slug=slug)
    diff = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=str(manifest),
            tofile=f"{manifest} (migrated)",
        )
    )
    if not dry_run and after != before:
        manifest.write_text(after, encoding="utf-8")
    return diff


# ---- checks -----------------------------------------------------------------


def _retired_key_findings(manifest: Path, document: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    metadata = document.get("metadata")
    locations = [("", document)]
    if isinstance(metadata, dict):
        locations.append(("metadata.", metadata))
    for prefix, table in locations:
        if RETIRED_PIN_KEY in table:
            message = (
                f"{prefix}{RETIRED_PIN_KEY} is a retired spelling; the release lives only in "
                ".seed/contract.yaml delivery.harbor_release and the validation receipt"
            )
            out.append(_error(manifest, message, "HARBOR_PIN_MALFORMED"))
    return out


def _load_manifest(manifest: Path) -> dict[str, Any] | None:
    try:
        with manifest.open("rb") as stream:
            document = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return document


def check_harbor_currency(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """Refuse a missing, malformed, stale, untested, or drifting Harbor release pin."""
    root_path = Path(root)
    found = bundles(root_path)
    if not found:
        return []
    now = _now(_evaluation_time)
    out: list[Finding] = []
    pinned = pin(root_path)
    if pinned.finding is not None:
        out.append(pinned.finding)
    for bundle in found:
        manifest = bundle / "task.toml"
        document = _load_manifest(manifest)
        if document is None:
            continue
        out += _retired_key_findings(manifest, document)
    lock_path = root_path / LOCK_FILE
    lock: Lock | None = None
    try:
        lock = read_lock(root_path)
    except HarborError as exc:
        code = "HARBOR_LOCK_MISSING" if not lock_path.is_file() else "HARBOR_LOCK_MALFORMED"
        out.append(_error(lock_path, f"{exc}; run tools/harbor.py resolve", code))
    if lock is not None and now - lock.resolved_at > timedelta(days=LOCK_STALE_DAYS):
        message = (
            f"harbor.lock was resolved at {_iso(lock.resolved_at)}, more than "
            f"{LOCK_STALE_DAYS} days before {_iso(now)}; a stale snapshot cannot certify currency"
        )
        out.append(_error(lock_path, message, "HARBOR_LOCK_STALE"))
    if pinned.version is not None and lock is not None:
        out += _pin_staleness(Path(pinned.source), pinned.version, lock, now)
        out += _untested_findings(root_path, found, pinned.version)
    out += _schema_drift(root_path, found)
    return out


def _pin_staleness(location: Path, version: str, lock: Lock, now: datetime) -> list[Finding]:
    pinned = _release_tuple(version)
    latest = _release_tuple(lock.latest_version)
    if pinned is None or latest is None or pinned == latest:
        return []
    behind_major = pinned[0] < latest[0]
    behind_minor = pinned[0] == latest[0] and pinned[1] < latest[1] - PIN_MINOR_LAG
    aged = now - lock.latest_released_at > timedelta(days=PIN_STALE_DAYS)
    if behind_major or behind_minor or aged:
        message = (
            f"harbor_release {version} is stale against harbor.lock latest "
            f"{lock.latest_version} released {_iso(lock.latest_released_at)}: re-pin to the "
            "latest stable release and re-validate every bundle"
        )
        return [_error(location, message, "HARBOR_PIN_STALE")]
    return []


def _untested_findings(root: Path, found: Sequence[Path], version: str) -> list[Finding]:
    out: list[Finding] = []
    for bundle in found:
        manifest = bundle / "task.toml"
        receipt = read_receipt(receipt_path(root, bundle.name))
        if receipt is None or receipt.harbor_version != version:
            message = (
                f"no validation receipt under harbor_release {version}; run "
                "tools/harbor.py validate and commit .audit/receipts/harbor/"
            )
            out.append(_error(manifest, message, "HARBOR_PIN_UNTESTED"))
    return out


def _schema_drift(root: Path, found: Sequence[Path]) -> list[Finding]:
    contract = root / CONTRACT_PATH
    if not contract.is_file():
        return []
    try:
        bound = _yaml_scalar(contract.read_text(encoding="utf-8"), ("delivery", "schema_version"))
    except (OSError, UnicodeDecodeError):
        return []
    if bound is None:
        return []
    out: list[Finding] = []
    for bundle in found:
        manifest = bundle / "task.toml"
        document = _load_manifest(manifest)
        if document is None:
            continue
        declared = document.get("schema_version")
        if declared != bound:
            message = (
                f"task.toml schema_version {declared!r} differs from the contract pin {bound!r}"
            )
            out.append(_error(manifest, message, "HARBOR_SCHEMA_DRIFT"))
    return out


def check_harbor_validate(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """Refuse any manifest Harbor's own validator rejected, or whose receipt does not bind it."""
    root_path = Path(root)
    found = bundles(root_path)
    if not found:
        return []
    uv_present = shutil.which("uv") is not None
    out: list[Finding] = []
    for bundle in found:
        manifest = bundle / "task.toml"
        path = receipt_path(root_path, bundle.name)
        if not path.is_file():
            if uv_present:
                message = "no Harbor validation receipt; run tools/harbor.py validate"
                out.append(_error(path, message, "HARBOR_RECEIPT_MISSING"))
            else:
                message = (
                    "no Harbor validation receipt and uv is absent, so the isolated validator "
                    "cannot run here; this is a coverage gap, never a pass"
                )
                out.append(_advisory(path, message, "HARBOR_VALIDATOR_UNAVAILABLE"))
            continue
        receipt = read_receipt(path)
        if receipt is None:
            out.append(_error(path, "receipt is malformed", "HARBOR_RECEIPT_TAMPERED"))
            continue
        if receipt.validator_digest != VALIDATOR_DIGEST:
            message = "receipt was produced by a different validator surface"
            out.append(_error(path, message, "HARBOR_RECEIPT_TAMPERED"))
            continue
        if not manifest.is_file() or receipt.task_toml_sha256 != sha256_file(manifest):
            message = (
                "receipt is bound to a different task.toml than the committed one; re-run "
                "tools/harbor.py validate"
            )
            out.append(_error(manifest, message, "HARBOR_SCHEMA_INVALID"))
            continue
        if not receipt.ok:
            message = f"Harbor {receipt.harbor_version} rejects task.toml: {receipt.message}"
            out.append(_error(manifest, message, "HARBOR_SCHEMA_INVALID"))
    return out


CHECKS: list[tuple[str, Callable[[str, datetime | None], list[Finding]]]] = [
    ("harbor_currency", check_harbor_currency),
    ("harbor_validate", check_harbor_validate),
]


# ---- CLI -------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harbor.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    resolve_cmd = commands.add_parser("resolve", help="write harbor.lock from PyPI")
    resolve_cmd.add_argument("root")
    resolve_cmd.add_argument("--offline", action="store_true")
    pin_cmd = commands.add_parser("pin", help="print the pinned Harbor release")
    pin_cmd.add_argument("root")
    validate_cmd = commands.add_parser("validate", help="run Harbor's validator, write receipts")
    validate_cmd.add_argument("root")
    validate_cmd.add_argument("--version", help="override the pinned release")
    validate_cmd.add_argument("--uuid", action="append", dest="uuids")
    migrate_cmd = commands.add_parser("migrate", help="migrate one manifest to the current shape")
    migrate_cmd.add_argument("root")
    migrate_cmd.add_argument("uuid")
    migrate_cmd.add_argument("--write", action="store_true")
    migrate_cmd.add_argument("--org", default=DEFAULT_ORG)
    check_cmd = commands.add_parser("check", help="run both Harbor checks")
    check_cmd.add_argument("root")
    check_cmd.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str]) -> int:
    args = _build_parser().parse_args(argv)
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            str(args.root),
            project_root=project_root,
            description="parent root",
            must_exist=True,
        )
        if args.command == "resolve":
            lock = resolve(root, offline=args.offline)
            print(f"harbor latest {lock.latest_version} released {_iso(lock.latest_released_at)}")
            return 0
        if args.command == "pin":
            pinned = pin(root)
            if pinned.finding is not None:
                item = pinned.finding
                public = Finding(
                    item.code,
                    item.severity,
                    display_project_path(item.path, project_root=project_root),
                    item.line,
                    redact_project_root(item.message, project_root=project_root),
                )
                print(render_finding(public), file=sys.stderr)
                return 1
            print(pinned.version)
            return 0
        if args.command == "validate":
            version = args.version
            if version is None:
                pinned = pin(root)
                if pinned.finding is not None:
                    item = pinned.finding
                    public = Finding(
                        item.code,
                        item.severity,
                        display_project_path(item.path, project_root=project_root),
                        item.line,
                        redact_project_root(item.message, project_root=project_root),
                    )
                    print(render_finding(public), file=sys.stderr)
                    return 1
                version = pinned.version
            assert version is not None
            run = validate(root, version, args.uuids)
            if run.error is not None:
                print(redact_project_root(run.error, project_root=project_root), file=sys.stderr)
                return 3
            failed = 0
            for uuid, receipt in sorted(run.receipts.items()):
                state = "OK" if receipt.ok else "INVALID"
                print(f"{uuid}: {state}")
                if not receipt.ok:
                    failed += 1
                    print(f"    {receipt.message}")
            return 1 if failed else 0
        if args.command == "migrate":
            print(migrate(root, args.uuid, dry_run=not args.write, org=args.org), end="")
            return 0
        findings = [finding_ for _, check in CHECKS for finding_ in check(str(root), None)]
        findings = [
            Finding(
                item.code,
                item.severity,
                display_project_path(item.path, project_root=project_root),
                item.line,
                redact_project_root(item.message, project_root=project_root),
            )
            for item in findings
        ]
        if args.json:
            print(serialize_findings(findings))
        else:
            for finding_ in findings:
                print(render_finding(finding_))
        return 1 if any(f.severity is Severity.ERROR for f in findings) else 0
    except (HarborError, ProjectPathError) as exc:
        captured_root = locals().get("project_root")
        message = (
            str(exc)
            if not isinstance(captured_root, Path)
            else redact_project_root(str(exc), project_root=captured_root)
        )
        print(message, file=sys.stderr)
        return exc.exit_code if isinstance(exc, HarborError) else 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
