"""Fail-closed external trust and signed release evidence verification."""

# allow: SIZE_OK - Keep the F1 binding inside the existing signed receipt verifier; no schema split.

from __future__ import annotations

import hashlib
import math
import os
import re
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from tools.attest.backend import SignatureBackend
    from tools.attest.backend_ssh import SshKeygenBackend
    from tools.attest.canonical import CanonicalizationError, JSONValue, canonicalize, parse_json
    from tools.attest.dsse import parse_envelope, verify_envelope
    from tools.attest.trustroot import TrustRoot, TrustRootValidationError
    from tools.forensics.ledger import FidelityLedgerReadError, ledger_bytes, parse_fidelity_ledger
    from tools.project_paths import ProjectPathError, invocation_root, resolve_project_path
else:
    try:
        from tools.attest.backend import SignatureBackend
        from tools.attest.backend_ssh import SshKeygenBackend
        from tools.attest.canonical import (
            CanonicalizationError,
            JSONValue,
            canonicalize,
            parse_json,
        )
        from tools.attest.dsse import parse_envelope, verify_envelope
        from tools.attest.trustroot import TrustRoot, TrustRootValidationError
        from tools.forensics.ledger import (
            FidelityLedgerReadError,
            ledger_bytes,
            parse_fidelity_ledger,
        )
        from tools.project_paths import ProjectPathError, invocation_root, resolve_project_path
    except ModuleNotFoundError:  # pragma: no cover
        from attest.backend import SignatureBackend
        from attest.backend_ssh import SshKeygenBackend
        from attest.canonical import CanonicalizationError, JSONValue, canonicalize, parse_json
        from attest.dsse import parse_envelope, verify_envelope
        from attest.trustroot import TrustRoot, TrustRootValidationError
        from forensics.ledger import FidelityLedgerReadError, ledger_bytes, parse_fidelity_ledger
        from project_paths import ProjectPathError, invocation_root, resolve_project_path

_SSH_BACKEND_TYPE = SshKeygenBackend

TRUST_ENV = "TRINITY_RELEASE_TRUST_DIR"
POLICY_SCHEMA = "trinity.release-policy/v3"
ORACLE_SCHEMA = "trinity.oracle-run/v4"
ORACLE_PAYLOAD_TYPE = "application/vnd.trinity.oracle-run+json"
DISPOSITION_SCHEMA = "trinity.release-disposition/v2"
GROUP_DISPOSITION_SCHEMA = "trinity.release-disposition/v3"
DISPOSITION_PAYLOAD_TYPES = {
    "FORGE": "application/vnd.trinity.release-disposition.forge+json",
    "CRUCIBLE": "application/vnd.trinity.release-disposition.crucible+json",
}
GROUP_DISPOSITION_PAYLOAD_TYPES = {
    "FORGE": "application/vnd.trinity.release-disposition.v3.forge+json",
    "CRUCIBLE": "application/vnd.trinity.release-disposition.v3.crucible+json",
}
GROUP_PRODUCER_ROLE = "gate_producer"
GROUP_APPROVER_ROLE = "gate_approver"
MAX_TRUST_BYTES = 512 * 1024
MAX_EVIDENCE_BYTES = 1024 * 1024
MIN_STABILITY_RUNS = 2
MAX_STABILITY_RUNS = 1000
MAX_ORACLE_AGE_SECONDS = 366 * 24 * 60 * 60
MAX_DISPOSITION_AGE_SECONDS = 30 * 24 * 60 * 60
HEX40 = 40
HEX64 = 64
CORE_CONTROL_IDS = frozenset(
    {
        "build_assets_harness",
        "oracle_noop_known_wrong_adversary_integrity",
        "alternate_correct_mutant_grading_instruction_scope",
        "judge_completeness_repeatability",
        "trial_reward_accounting",
        "execution_fidelity",
    }
)
JUDGE_CONTROL_ID = "judge_completeness_repeatability"

# The one closed set of gate and signing outputs that may land after the commit a receipt or
# disposition binds, or sit uncommitted at gate time. Every binder (gate receipts, gate
# promotion and signing, sabotage disposition binding, publisher snapshot binding) and the
# dirty-tree check read this set and no other, so that no ordering of sealing commits can
# satisfy one check while tripping another.
SEALING_PATHS: frozenset[str] = frozenset(
    {"DIRECTIVE.md", "EDICT.md", "VERDICT.md", "TRACKING.md", "SCORE.md"}
)
SEALING_PREFIXES: tuple[str, ...] = (
    ".memory/gate-receipts/",
    ".seed/gate-receipts/",
    ".audit/gate-receipts/",
    ".memory/disposition.json",
    ".seed/disposition.json",
    ".audit/disposition.json",
    ".sentinel/",
    ".trinity-runtime/",
    ".trinity-install/",
)


RUN_SEALING_PATH = re.compile(
    r"\A\.(?:memory|seed|audit)/runs/[A-Za-z0-9][A-Za-z0-9.-]{7,79}/"
    r"(?:gate-receipts/[^/]+|disposition\.json|report\.md|tracker\.json)\Z"
)
RELEASE_SEALING_PATH = re.compile(
    r"\A\.(?:seed|audit)/releases/[a-z0-9][a-z0-9.-]{2,63}/disposition\.json(?:\.dsse)?\Z"
)


def is_sealing_path(path: str) -> bool:
    """A gate or signing output that may land after the commit a record binds.

    Run namespaces are not exempt as a whole: only a run's receipts, its qualification
    record, its report, and its closure card are outputs; every other byte under the run
    is subject.
    """
    return (
        path in SEALING_PATHS
        or path.startswith(SEALING_PREFIXES)
        or RUN_SEALING_PATH.fullmatch(path) is not None
        or RELEASE_SEALING_PATH.fullmatch(path) is not None
    )


def seals_only(paths: Iterable[str]) -> bool:
    """True when every path is a sealing artifact; an empty set seals nothing and is False."""
    seen = False
    for path in paths:
        if not is_sealing_path(path):
            return False
        seen = True
    return seen


_POLICY_FIELDS = frozenset(
    {
        "schema",
        "trusted_root_version",
        "project_id",
        "repository_id",
        "verifier_sha",
        "disposition_max_age_seconds",
        "oracle",
    }
)
_ORACLE_POLICY_FIELDS = frozenset(
    {
        "harbor_version",
        "image_digest",
        "harness_digest",
        "full_reward",
        "score_min",
        "score_max",
        "negative_score_max",
        "stability_runs",
        "max_age_seconds",
        "required_controls",
        "positive_control_ids",
        "non_applicable_controls",
    }
)
_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "task_uuid",
        "bundle_digest",
        "started_at",
        "completed_at",
        "expires_at",
        "harbor_version",
        "image_digest",
        "harness_digest",
        "full_reward",
        "reward",
        "score",
        "runs",
        "controls",
    }
)
_RUN_FIELDS = frozenset({"run_id", "reward", "score", "no_op", "known_wrong"})
_CONTROL_FIELDS = frozenset({"executed", "verdict", "score"})
_COVERAGE_FIELDS = frozenset(
    {"control_id", "status", "evidence_digest", "task_uuid", "verifier_sha", "closure_digest"}
)


class ReleaseEvidenceError(ValueError):
    """External trust or signed release evidence was absent or invalid."""


@dataclass(frozen=True, slots=True)
class OraclePolicy:
    harbor_version: str
    image_digest: str
    harness_digest: str
    full_reward: float
    score_min: float
    score_max: float
    negative_score_max: float
    stability_runs: int
    max_age_seconds: int
    required_controls: tuple[str, ...]
    positive_control_ids: frozenset[str]
    non_applicable_controls: frozenset[str]


@dataclass(frozen=True, slots=True)
class ReleaseTrust:
    directory: Path
    root: TrustRoot
    allowed_signers: Path
    trusted_root_version: int
    project_id: str
    repository_id: str
    verifier_sha: str
    disposition_max_age_seconds: int
    oracle: OraclePolicy


@dataclass(frozen=True, slots=True)
class SignedAuthorization:
    payload: bytes
    authenticated_principals: tuple[str, ...]
    authorized_principals: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AuthenticatedEnvelope:
    payload: bytes
    authenticated_principals: tuple[str, ...]


def safe_read_bytes(path: Path, *, maximum: int) -> bytes:
    """Bounded no-follow read of one stable regular file."""

    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or stat.S_ISLNK(before.st_mode):
            raise ReleaseEvidenceError(f"{path} is not a regular file")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise ReleaseEvidenceError(f"cannot safely open {path}: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ReleaseEvidenceError(f"{path} changed before it could be read")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65536, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise ReleaseEvidenceError(f"{path} exceeds the {maximum}-byte limit")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        final = path.lstat()
    except OSError as exc:
        raise ReleaseEvidenceError(f"{path} disappeared while being read") from exc

    def fingerprint(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    if fingerprint(before) != fingerprint(after) or fingerprint(before) != fingerprint(final):
        raise ReleaseEvidenceError(f"{path} changed while being read")
    return b"".join(chunks)


def _closed(value: object, fields: frozenset[str], location: str) -> dict[str, JSONValue]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ReleaseEvidenceError(f"{location} does not carry the closed field set")
    return cast(dict[str, JSONValue], value)


def _string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReleaseEvidenceError(f"{location} must be a non-empty string")
    return value


def _number(value: object, location: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ReleaseEvidenceError(f"{location} must be a finite number")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ReleaseEvidenceError(f"{location} must be a finite number") from exc
    if not math.isfinite(number):
        raise ReleaseEvidenceError(f"{location} must be a finite number")
    return number


def _positive_int(
    value: object, location: str, minimum: int = 1, maximum: int | None = None
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        bounds = f"at least {minimum}"
        if maximum is not None:
            bounds += f" and at most {maximum}"
        raise ReleaseEvidenceError(f"{location} must be an integer of {bounds}")
    return value


def _digest(value: object, location: str) -> str:
    text = _string(value, location)
    prefix, separator, hexadecimal = text.partition(":")
    if prefix != "sha256" or separator != ":" or len(hexadecimal) != HEX64:
        raise ReleaseEvidenceError(f"{location} must be a lowercase sha256 digest")
    if any(character not in "0123456789abcdef" for character in hexadecimal):
        raise ReleaseEvidenceError(f"{location} must be a lowercase sha256 digest")
    return text


def _git_sha(value: object, location: str) -> str:
    text = _string(value, location)
    if len(text) != HEX40 or any(character not in "0123456789abcdef" for character in text):
        raise ReleaseEvidenceError(f"{location} must be a full lowercase 40-character commit SHA")
    return text


def parse_instant(value: object, location: str) -> datetime:
    text = _string(value, location)
    if not text.endswith("Z"):
        raise ReleaseEvidenceError(f"{location} must be an RFC 3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except (OverflowError, ValueError) as exc:
        raise ReleaseEvidenceError(f"{location} must be an RFC 3339 UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ReleaseEvidenceError(f"{location} must be an RFC 3339 UTC timestamp")
    return parsed.astimezone(UTC)


def _string_list(value: object, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ReleaseEvidenceError(f"{location} must be a non-empty list")
    result = tuple(_string(item, location) for item in value)
    if len(set(result)) != len(result):
        raise ReleaseEvidenceError(f"{location} must not contain duplicates")
    return result


def _external_directory(
    candidate_root: Path,
    configured: str | Path | None,
    *,
    project_root: Path | None,
) -> Path:
    selected = configured if configured is not None else os.environ.get(TRUST_ENV)
    if selected is None or not str(selected).strip():
        raise ReleaseEvidenceError(f"external trust is not configured; set {TRUST_ENV}")
    try:
        if isinstance(selected, Path):
            if not selected.is_absolute():
                raise ReleaseEvidenceError("internal release trust Path must already be resolved")
            absolute = selected
        else:
            absolute = resolve_project_path(
                selected,
                project_root=project_root or invocation_root(),
                description="release trust directory",
                must_exist=True,
            )
    except ProjectPathError as exc:
        raise ReleaseEvidenceError(str(exc)) from exc
    try:
        info = absolute.lstat()
        resolved = absolute.resolve(strict=True)
        candidate = candidate_root.absolute().resolve(strict=True)
    except OSError as exc:
        raise ReleaseEvidenceError(f"release trust directory is unavailable: {exc}") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or resolved != absolute:
        raise ReleaseEvidenceError("release trust directory must be real and symlink-free")
    if resolved == candidate or candidate in resolved.parents:
        raise ReleaseEvidenceError("release trust directory must live outside the candidate tree")
    return resolved


def _trust_file(directory: Path, name: str) -> Path:
    path = directory / name
    if path.parent != directory:
        raise ReleaseEvidenceError(f"invalid trust filename {name!r}")
    safe_read_bytes(path, maximum=MAX_TRUST_BYTES)
    if path.resolve(strict=True).parent != directory:
        raise ReleaseEvidenceError(f"trust file {name} escapes the trust directory")
    return path


def load_release_trust(
    candidate_root: Path,
    configured: str | Path | None = None,
    *,
    project_root: Path | None = None,
) -> ReleaseTrust:
    """Load trust; external strings are ``./`` paths, while resolved Paths are internal-only."""

    directory = _external_directory(candidate_root, configured, project_root=project_root)
    roots_path = _trust_file(directory, "roots.yaml")
    allowed = _trust_file(directory, "allowed_signers")
    version_path = _trust_file(directory, "trusted-root-version")
    policy_path = _trust_file(directory, "policy.json")
    try:
        root = TrustRoot.from_json(safe_read_bytes(roots_path, maximum=MAX_TRUST_BYTES))
        version_text = safe_read_bytes(version_path, maximum=64).decode("utf-8").strip()
        trusted_version = int(version_text)
        policy_value = parse_json(safe_read_bytes(policy_path, maximum=MAX_TRUST_BYTES))
    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        CanonicalizationError,
        TrustRootValidationError,
    ) as exc:
        raise ReleaseEvidenceError(f"external release trust is malformed: {exc}") from exc
    if trusted_version < 1 or version_text != str(trusted_version):
        raise ReleaseEvidenceError("trusted-root-version must be one positive canonical integer")
    if root.version != trusted_version:
        raise ReleaseEvidenceError("trust root version must equal the independently pinned version")
    if not isinstance(policy_value, dict):
        raise ReleaseEvidenceError("release policy must be an object")
    observed_schema = policy_value.get("schema")
    if observed_schema != POLICY_SCHEMA:
        raise ReleaseEvidenceError(
            f"RELEASE_POLICY_SCHEMA_UNSUPPORTED: observed {observed_schema!r}; "
            f"required {POLICY_SCHEMA}"
        )
    policy = _closed(policy_value, _POLICY_FIELDS, "release policy")
    if policy["trusted_root_version"] != trusted_version:
        raise ReleaseEvidenceError("release policy root version is not pinned")
    oracle = _closed(policy.get("oracle"), _ORACLE_POLICY_FIELDS, "oracle policy")
    required = _string_list(oracle.get("required_controls"), "required_controls")
    positive = frozenset(_string_list(oracle.get("positive_control_ids"), "positive_control_ids"))
    non_applicable_raw = oracle.get("non_applicable_controls")
    if not isinstance(non_applicable_raw, list):
        raise ReleaseEvidenceError("non_applicable_controls must be a list")
    non_applicable = frozenset(
        _string(item, "non_applicable_controls") for item in non_applicable_raw
    )
    required_set = set(required)
    missing_core = sorted(CORE_CONTROL_IDS - required_set)
    if missing_core:
        raise ReleaseEvidenceError(
            f"required_controls omits core controls: {', '.join(missing_core)}"
        )
    if not positive or not positive <= required_set:
        raise ReleaseEvidenceError(
            "positive_control_ids must be a non-empty required-control subset"
        )
    if not non_applicable <= {JUDGE_CONTROL_ID} or not non_applicable <= required_set:
        raise ReleaseEvidenceError("only the trusted judge control may be non-applicable")
    if positive & non_applicable:
        raise ReleaseEvidenceError("a positive control cannot be non-applicable")
    full = _number(oracle.get("full_reward"), "full_reward")
    low = _number(oracle.get("score_min"), "score_min")
    high = _number(oracle.get("score_max"), "score_max")
    negative = _number(oracle.get("negative_score_max"), "negative_score_max")
    if full <= 0 or not low <= negative < high:
        raise ReleaseEvidenceError("oracle reward or score policy is invalid")
    return ReleaseTrust(
        directory=directory,
        root=root,
        allowed_signers=allowed,
        trusted_root_version=trusted_version,
        project_id=_string(policy.get("project_id"), "project_id"),
        repository_id=_string(policy.get("repository_id"), "repository_id"),
        verifier_sha=_git_sha(policy.get("verifier_sha"), "verifier_sha"),
        disposition_max_age_seconds=_positive_int(
            policy.get("disposition_max_age_seconds"),
            "disposition_max_age_seconds",
            maximum=MAX_DISPOSITION_AGE_SECONDS,
        ),
        oracle=OraclePolicy(
            harbor_version=_string(oracle.get("harbor_version"), "harbor_version"),
            image_digest=_digest(oracle.get("image_digest"), "image_digest"),
            harness_digest=_digest(oracle.get("harness_digest"), "harness_digest"),
            full_reward=full,
            score_min=low,
            score_max=high,
            negative_score_max=negative,
            stability_runs=_positive_int(
                oracle.get("stability_runs"),
                "stability_runs",
                MIN_STABILITY_RUNS,
                MAX_STABILITY_RUNS,
            ),
            max_age_seconds=_positive_int(
                oracle.get("max_age_seconds"),
                "max_age_seconds",
                maximum=MAX_ORACLE_AGE_SECONDS,
            ),
            required_controls=required,
            positive_control_ids=positive,
            non_applicable_controls=non_applicable,
        ),
    )


def verify_signed_payload(
    envelope_path: Path,
    *,
    trust: ReleaseTrust,
    role: str,
    payload_type: str,
    evaluation_time: datetime,
    backend: SignatureBackend | None = None,
    producer_principal: str | None = None,
    excluded_principals: tuple[str, ...] = (),
) -> SignedAuthorization:
    authenticated = authenticate_signed_payload(
        envelope_path,
        trust=trust,
        payload_type=payload_type,
        evaluation_time=evaluation_time,
        backend=backend,
    )
    authorization = authorize_authenticated_principals(
        trust=trust,
        role=role,
        authenticated_principals=authenticated.authenticated_principals,
        evaluation_time=evaluation_time,
        producer_principal=producer_principal,
        excluded_principals=excluded_principals,
    )
    return SignedAuthorization(
        payload=authenticated.payload,
        authenticated_principals=authenticated.authenticated_principals,
        authorized_principals=authorization,
    )


def authenticate_signed_payload(
    envelope_path: Path,
    *,
    trust: ReleaseTrust,
    payload_type: str,
    evaluation_time: datetime,
    backend: SignatureBackend | None = None,
) -> AuthenticatedEnvelope:
    """Authenticate every signature and return deduplicated signer principals."""

    document = safe_read_bytes(envelope_path, maximum=MAX_EVIDENCE_BYTES)
    parsed = parse_envelope(document)
    if parsed.envelope is None:
        raise ReleaseEvidenceError(f"DSSE envelope is invalid: {parsed.reason}: {parsed.detail}")
    selected_backend = backend or SshKeygenBackend()
    if payload_type in GROUP_DISPOSITION_PAYLOAD_TYPES.values() and isinstance(
        selected_backend, _SSH_BACKEND_TYPE
    ):
        policy_failure = selected_backend.validate_group_allowed_signers_policy(
            trust.allowed_signers
        )
        if policy_failure is not None:
            reason = (
                policy_failure.reason.value
                if policy_failure.reason is not None
                else "output_unparseable"
            )
            raise ReleaseEvidenceError(
                f"group signer policy refused: {reason}: {policy_failure.detail}"
            )
    signature = verify_envelope(
        selected_backend,
        parsed.envelope,
        expected_payload_type=payload_type,
        allowed_signers_path=trust.allowed_signers,
        evaluation_time=evaluation_time,
    )
    if not signature.accepted:
        raise ReleaseEvidenceError(
            f"DSSE signature refused: {signature.reason_value}: {signature.detail}"
        )
    return AuthenticatedEnvelope(
        payload=parsed.envelope.payload,
        authenticated_principals=signature.principals,
    )


def authorize_authenticated_principals(
    *,
    trust: ReleaseTrust,
    role: str,
    authenticated_principals: tuple[str, ...],
    evaluation_time: datetime,
    producer_principal: str | None = None,
    excluded_principals: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Apply one trust-root role to already authenticated DSSE identities."""

    authorization = trust.root.authorize(
        role_name=role,
        verified_principals=authenticated_principals,
        evaluation_time=evaluation_time,
        trusted_version=trust.trusted_root_version,
        producer_principal=producer_principal,
        excluded_principals=excluded_principals,
    )
    if not authorization.accepted:
        raise ReleaseEvidenceError(
            f"signer authorization refused: {authorization.reason_value}: {authorization.detail}"
        )
    return authorization.principals


def _check_negative(value: object, policy: OraclePolicy, location: str) -> None:
    control = _closed(value, _CONTROL_FIELDS, location)
    if control.get("executed") is not True or control.get("verdict") != "rejected":
        raise ReleaseEvidenceError(f"{location} must be executed and individually rejected")
    score = _number(control.get("score"), f"{location} score")
    if not policy.score_min <= score <= policy.negative_score_max:
        raise ReleaseEvidenceError(f"{location} score is outside the negative bound")


def _coverage_closure(rows: list[dict[str, JSONValue]]) -> str:
    bodies = [
        {
            "control_id": row["control_id"],
            "status": row["status"],
            "evidence_digest": row["evidence_digest"],
            "task_uuid": row["task_uuid"],
            "verifier_sha": row["verifier_sha"],
        }
        for row in sorted(rows, key=lambda item: str(item["control_id"]))
    ]
    return hashlib.sha256(canonicalize(bodies)).hexdigest()


def _verify_coverage(
    value: object,
    *,
    trust: ReleaseTrust,
    task_uuid: str,
    ledger: bytes,
) -> None:
    if not isinstance(value, list):
        raise ReleaseEvidenceError("controls must be a list")
    rows = [_closed(item, _COVERAGE_FIELDS, "control outcome") for item in value]
    ids = [str(row["control_id"]) for row in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(trust.oracle.required_controls):
        raise ReleaseEvidenceError(
            "control outcomes must cover every required control exactly once"
        )
    closure = _coverage_closure(rows)
    for row in rows:
        control_id = str(row["control_id"])
        expected_status = (
            "not_applicable" if control_id in trust.oracle.non_applicable_controls else "pass"
        )
        if row["status"] != expected_status:
            raise ReleaseEvidenceError(
                f"control {control_id} is missing, failed, skipped, or waived"
            )
        if row["task_uuid"] != task_uuid or row["verifier_sha"] != trust.verifier_sha:
            raise ReleaseEvidenceError(f"control {control_id} is not bound to task and verifier")
        _digest(row["evidence_digest"], f"control {control_id} evidence_digest")
        if control_id == "execution_fidelity":
            try:
                parsed = parse_fidelity_ledger(ledger)
            except FidelityLedgerReadError:
                raise ReleaseEvidenceError("ORACLE_FIDELITY_REFUSED") from None
            digest = "sha256:" + hashlib.sha256(ledger_bytes(parsed)).hexdigest()
            if row["evidence_digest"] != digest:
                raise ReleaseEvidenceError("ORACLE_FIDELITY_DIGEST_MISMATCH")
            if (
                parsed.blocked
                or not parsed.rows
                or any(item.trial_status != "conforming" for item in parsed.rows)
            ):
                raise ReleaseEvidenceError("ORACLE_FIDELITY_REFUSED")
        if row["closure_digest"] != closure:
            raise ReleaseEvidenceError(f"control {control_id} is not bound to the manifest closure")


def verify_oracle_receipt(
    envelope_path: Path,
    *,
    trust: ReleaseTrust,
    task_uuid: str,
    bundle_digest: str,
    evaluation_time: datetime,
    backend: SignatureBackend | None = None,
    ledger: bytes,
) -> SignedAuthorization:
    signed = verify_signed_payload(
        envelope_path,
        trust=trust,
        role="execution_operator",
        payload_type=ORACLE_PAYLOAD_TYPE,
        evaluation_time=evaluation_time,
        backend=backend,
    )
    try:
        value = parse_json(signed.payload)
        if canonicalize(value) != signed.payload:
            raise ReleaseEvidenceError("oracle receipt is not exact canonical JSON")
    except CanonicalizationError as exc:
        raise ReleaseEvidenceError(f"oracle receipt payload is malformed: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseEvidenceError("oracle receipt must be an object")
    observed_schema = value.get("schema")
    if observed_schema != ORACLE_SCHEMA:
        raise ReleaseEvidenceError(
            f"ORACLE_SCHEMA_UNSUPPORTED: observed schema {observed_schema!r}; "
            f"required {ORACLE_SCHEMA}"
        )
    receipt = _closed(value, _RECEIPT_FIELDS, "oracle receipt")
    if receipt.get("task_uuid") != task_uuid:
        raise ReleaseEvidenceError("oracle receipt task_uuid does not bind this task")
    if receipt.get("bundle_digest") != bundle_digest:
        raise ReleaseEvidenceError("oracle receipt bundle_digest does not bind this bundle")
    policy = trust.oracle
    for field, expected in {
        "harbor_version": policy.harbor_version,
        "image_digest": policy.image_digest,
        "harness_digest": policy.harness_digest,
    }.items():
        if receipt.get(field) != expected:
            raise ReleaseEvidenceError(f"oracle receipt {field} does not match external policy")
    started = parse_instant(receipt.get("started_at"), "started_at")
    completed = parse_instant(receipt.get("completed_at"), "completed_at")
    expires = parse_instant(receipt.get("expires_at"), "expires_at")
    if not started <= completed <= evaluation_time < expires:
        raise ReleaseEvidenceError("oracle receipt time order or validity window is invalid")
    if evaluation_time - completed > timedelta(seconds=policy.max_age_seconds):
        raise ReleaseEvidenceError("oracle receipt is older than policy permits")
    full = _number(receipt.get("full_reward"), "full_reward")
    reward = _number(receipt.get("reward"), "reward")
    score = _number(receipt.get("score"), "score")
    if full <= 0 or full != policy.full_reward or reward != full:
        raise ReleaseEvidenceError(
            "oracle receipt does not declare positive full reward from policy"
        )
    if not policy.score_min <= score <= policy.score_max:
        raise ReleaseEvidenceError("oracle receipt score is outside policy")
    runs = receipt.get("runs")
    if not isinstance(runs, list) or len(runs) != policy.stability_runs:
        raise ReleaseEvidenceError("oracle receipt has the wrong stability run count")
    seen: set[str] = set()
    for index, raw in enumerate(runs):
        run = _closed(raw, _RUN_FIELDS, f"oracle run {index}")
        run_id = _string(run.get("run_id"), "run_id")
        if run_id in seen:
            raise ReleaseEvidenceError("oracle receipt repeats a run_id")
        seen.add(run_id)
        if _number(run.get("reward"), "run reward") != full:
            raise ReleaseEvidenceError(f"oracle run {index} did not reach full reward")
        run_score = _number(run.get("score"), "run score")
        if not policy.score_min <= run_score <= policy.score_max:
            raise ReleaseEvidenceError(f"oracle run {index} score is outside policy")
        _check_negative(run.get("no_op"), policy, f"oracle run {index} no_op")
        _check_negative(run.get("known_wrong"), policy, f"oracle run {index} known_wrong")
    _verify_coverage(receipt.get("controls"), trust=trust, task_uuid=task_uuid, ledger=ledger)
    return signed
