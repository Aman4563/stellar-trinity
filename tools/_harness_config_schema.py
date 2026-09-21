"""Typed nested boundaries for the closed harness configuration schema."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools.attest.canonical import JSONValue
else:
    try:
        from tools.attest.canonical import JSONValue
    except ModuleNotFoundError:  # pragma: no cover - direct tools/ execution
        from attest.canonical import JSONValue


class HarnessConfigFailureReason(StrEnum):
    HARNESS_CONFIG_MISSING = "HARNESS_CONFIG_MISSING"
    HARNESS_CONFIG_MALFORMED = "HARNESS_CONFIG_MALFORMED"
    HARNESS_CONFIG_SCHEMA_UNSUPPORTED = "HARNESS_CONFIG_SCHEMA_UNSUPPORTED"
    HARNESS_CONFIG_FIELD_UNKNOWN = "HARNESS_CONFIG_FIELD_UNKNOWN"
    HARNESS_CONFIG_FIELD_ABSENT = "HARNESS_CONFIG_FIELD_ABSENT"
    HARNESS_CONFIG_VALUE_INVALID = "HARNESS_CONFIG_VALUE_INVALID"
    HARNESS_CONFIG_NEGATIVE_HEADROOM = "HARNESS_CONFIG_NEGATIVE_HEADROOM"
    HARNESS_CONFIG_MODEL_ID_AMBIGUOUS = "HARNESS_CONFIG_MODEL_ID_AMBIGUOUS"
    HARNESS_CONFIG_UNAPPROVED = "HARNESS_CONFIG_UNAPPROVED"
    HARNESS_CONFIG_INADEQUATE = "HARNESS_CONFIG_INADEQUATE"
    HARNESS_CONFIG_DRIFT = "HARNESS_CONFIG_DRIFT"


@dataclass(frozen=True, slots=True)
class SchemaError(Exception):
    reason: HarnessConfigFailureReason
    detail: str

    def __str__(self) -> str:
        return f"{self.reason}: {self.detail}"


INVALID: Final = HarnessConfigFailureReason.HARNESS_CONFIG_VALUE_INVALID
COMPACTION_FIELDS: Final = frozenset({"enabled", "trigger", "thresholdTokens"})
TRUNCATION_FIELDS: Final = frozenset({"maxMessageChars", "maxObservationChars"})
SANDBOX_FIELDS: Final = frozenset({"cpuMillicores", "memoryBytes"})
RETRY_FIELDS: Final = frozenset({"maxRetries", "retryOnStatus"})
CONDENSER_FIELDS: Final = frozenset({"type", "enabled"})
ADEQUACY_FIELDS: Final = frozenset(
    {"approvedBy", "approvalSource", "headroomArgument", "approvedAt"}
)


@dataclass(frozen=True, slots=True)
class CompactionPolicy:
    enabled: bool
    trigger: CompactionTrigger
    threshold_tokens: int


class CompactionTrigger(StrEnum):
    NONE = "none"
    AUTO = "auto"
    MANUAL = "manual"


class ApprovalSource(StrEnum):
    REQUIREMENTS = "requirements"
    TOUCHSTONES = "touchstones"


@dataclass(frozen=True, slots=True)
class ObservationTruncation:
    max_message_chars: int
    max_observation_chars: int


@dataclass(frozen=True, slots=True)
class Sandbox:
    cpu_millicores: int
    memory_bytes: int


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_retries: int
    retry_on_status: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CondenserConfig:
    type: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class ConfigurationAdequacy:
    approved_by: str
    approval_source: ApprovalSource
    headroom_argument: str
    approved_at: str


def closed_object(value: JSONValue, fields: frozenset[str], name: str) -> dict[str, JSONValue]:
    if not isinstance(value, dict):
        raise SchemaError(INVALID, f"{name} must be an object")
    missing = fields - value.keys()
    unknown = value.keys() - fields
    if missing:
        raise SchemaError(
            HarnessConfigFailureReason.HARNESS_CONFIG_FIELD_ABSENT,
            f"{name} missing fields: {', '.join(sorted(missing))}",
        )
    if unknown:
        raise SchemaError(
            HarnessConfigFailureReason.HARNESS_CONFIG_FIELD_UNKNOWN,
            f"{name} unknown fields: {', '.join(sorted(unknown))}",
        )
    return value


def text(value: JSONValue, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(INVALID, f"{name} must be a non-empty string")
    return value


def integer(value: JSONValue, name: str) -> int:
    if type(value) is not int:
        raise SchemaError(INVALID, f"{name} must be an integer")
    return value


def positive(value: JSONValue, name: str) -> int:
    parsed = integer(value, name)
    if parsed <= 0:
        raise SchemaError(INVALID, f"{name} must be positive")
    return parsed


def boolean(value: JSONValue, name: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaError(INVALID, f"{name} must be a boolean")
    return value


def compaction(value: JSONValue) -> CompactionPolicy:
    body = closed_object(value, COMPACTION_FIELDS, "compactionPolicy")
    enabled = boolean(body["enabled"], "compactionPolicy.enabled")
    try:
        trigger = CompactionTrigger(text(body["trigger"], "compactionPolicy.trigger"))
    except ValueError as error:
        raise SchemaError(
            INVALID, "compactionPolicy.trigger must be none, auto, or manual"
        ) from error
    if enabled and trigger == CompactionTrigger.NONE:
        raise SchemaError(INVALID, "compactionPolicy.enabled requires an active trigger")
    return CompactionPolicy(
        enabled, trigger, positive(body["thresholdTokens"], "compactionPolicy.thresholdTokens")
    )


def truncation(value: JSONValue) -> ObservationTruncation:
    body = closed_object(value, TRUNCATION_FIELDS, "observationTruncation")
    return ObservationTruncation(
        positive(body["maxMessageChars"], "observationTruncation.maxMessageChars"),
        positive(body["maxObservationChars"], "observationTruncation.maxObservationChars"),
    )


def sandbox(value: JSONValue) -> Sandbox:
    body = closed_object(value, SANDBOX_FIELDS, "sandbox")
    return Sandbox(
        positive(body["cpuMillicores"], "sandbox.cpuMillicores"),
        positive(body["memoryBytes"], "sandbox.memoryBytes"),
    )


def retry(value: JSONValue) -> RetryPolicy:
    body = closed_object(value, RETRY_FIELDS, "retryPolicy")
    retries = integer(body["maxRetries"], "retryPolicy.maxRetries")
    if retries < 0:
        raise SchemaError(INVALID, "retryPolicy.maxRetries must be nonnegative")
    raw = body["retryOnStatus"]
    if not isinstance(raw, list):
        raise SchemaError(INVALID, "retryPolicy.retryOnStatus must be an array")
    statuses = tuple(integer(item, "retryPolicy.retryOnStatus") for item in raw)
    if statuses != tuple(sorted(set(statuses))):
        raise SchemaError(INVALID, "retryPolicy.retryOnStatus must be sorted and distinct")
    return RetryPolicy(retries, statuses)


def condenser(value: JSONValue) -> CondenserConfig:
    body = closed_object(value, CONDENSER_FIELDS, "condenserConfig")
    return CondenserConfig(
        text(body["type"], "condenserConfig.type"),
        boolean(body["enabled"], "condenserConfig.enabled"),
    )


def adequacy(value: JSONValue) -> ConfigurationAdequacy:
    body = closed_object(value, ADEQUACY_FIELDS, "configurationAdequacy")
    try:
        source = ApprovalSource(
            text(body["approvalSource"], "configurationAdequacy.approvalSource")
        )
    except ValueError as error:
        raise SchemaError(INVALID, "configurationAdequacy.approvalSource is unsupported") from error
    return ConfigurationAdequacy(
        text(body["approvedBy"], "configurationAdequacy.approvedBy"),
        source,
        text(body["headroomArgument"], "configurationAdequacy.headroomArgument"),
        text(body["approvedAt"], "configurationAdequacy.approvedAt"),
    )
