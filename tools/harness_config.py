"""Parse declared harness configuration; acceptance does not establish adequacy."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import _harness_config_judgments as judgments
    from tools import _harness_config_schema as schema
    from tools.attest.canonical import (
        CanonicalizationError,
        JSONValue,
        canonicalize_json,
        parse_json,
    )
else:
    try:
        from tools import _harness_config_judgments as judgments
        from tools import _harness_config_schema as schema
        from tools.attest.canonical import (
            CanonicalizationError,
            JSONValue,
            canonicalize_json,
            parse_json,
        )
    except ModuleNotFoundError:  # pragma: no cover - supports direct execution from tools/
        import _harness_config_judgments as judgments
        import _harness_config_schema as schema
        from attest.canonical import (
            CanonicalizationError,
            JSONValue,
            canonicalize_json,
            parse_json,
        )

HARNESS_CONFIG_SCHEMA: Final = "trinity.harness-config/v1"
HARNESS_CONFIG_PATH: Final = Path(".seed/harness-config.json")
HARNESS_CONFIG_SOURCE: Final = Path("harness/harness-config.json")
HARNESS_CONFIG_FIELDS: Final = frozenset(
    {
        "schemaVersion",
        "harnessName",
        "harnessVersion",
        "modelId",
        "modelSnapshot",
        "adapter",
        "bridgeEndpointClass",
        "contextWindowTokens",
        "maxOutputTokens",
        "compactionPolicy",
        "observationTruncation",
        "maxTurns",
        "maxIterations",
        "toolCallCap",
        "wallClockTimeoutSeconds",
        "temperature",
        "topP",
        "seed",
        "systemPromptDigest",
        "sandbox",
        "networkPolicy",
        "retryPolicy",
        "reasoningEffort",
        "condenserConfig",
        "configurationAdequacy",
    }
)
HarnessConfigFailureReason = schema.HarnessConfigFailureReason
HarnessApproval = judgments.HarnessApproval
AdequacyOutcome = judgments.AdequacyOutcome
ReconcileOutcome = judgments.ReconcileOutcome
evaluate_adequacy = judgments.evaluate_adequacy
reconcile = judgments.reconcile
mirror_matches = judgments.mirror_matches
_HEX64: Final = re.compile(r"[0-9a-f]{64}\Z")
_TEMPERATURE_MAX: Final = 2.0


@dataclass(frozen=True, slots=True)
class HarnessConfig:
    schema_version: str
    harness_name: str
    harness_version: str
    model_id: str
    model_snapshot: str
    adapter: str
    bridge_endpoint_class: str
    context_window_tokens: int
    max_output_tokens: int
    compaction_policy: schema.CompactionPolicy
    observation_truncation: schema.ObservationTruncation
    max_turns: int
    max_iterations: int
    tool_call_cap: int
    wall_clock_timeout_seconds: int
    temperature: float
    top_p: float
    seed: int
    system_prompt_digest: str
    sandbox: schema.Sandbox
    network_policy: str
    retry_policy: schema.RetryPolicy
    reasoning_effort: str
    condenser_config: schema.CondenserConfig
    configuration_adequacy: schema.ConfigurationAdequacy


@dataclass(frozen=True, slots=True)
class HarnessConfigOutcome:
    accepted: bool
    reason: HarnessConfigFailureReason | None
    detail: str


@dataclass(frozen=True, slots=True)
class HarnessConfigParseResult:
    config: HarnessConfig | None
    outcome: HarnessConfigOutcome


def _sampling(value: JSONValue, name: str, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise schema.SchemaError(schema.INVALID, f"{name} must be a number")
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise schema.SchemaError(schema.INVALID, f"{name} is outside its finite range")
    return float(value)


def _configuration(value: JSONValue) -> HarnessConfig:
    if not isinstance(value, dict):
        raise schema.SchemaError(
            HarnessConfigFailureReason.HARNESS_CONFIG_MALFORMED, "document must be an object"
        )
    if "schemaVersion" in value and value["schemaVersion"] != HARNESS_CONFIG_SCHEMA:
        raise schema.SchemaError(
            HarnessConfigFailureReason.HARNESS_CONFIG_SCHEMA_UNSUPPORTED,
            f"schemaVersion must be {HARNESS_CONFIG_SCHEMA}",
        )
    body = schema.closed_object(value, HARNESS_CONFIG_FIELDS, "harnessConfig")
    context = schema.positive(body["contextWindowTokens"], "contextWindowTokens")
    output = schema.positive(body["maxOutputTokens"], "maxOutputTokens")
    if context <= output:
        raise schema.SchemaError(
            HarnessConfigFailureReason.HARNESS_CONFIG_NEGATIVE_HEADROOM,
            "contextWindowTokens must exceed maxOutputTokens",
        )
    model_id = schema.text(body["modelId"], "modelId")
    if model_id.count("/") > 1:
        raise schema.SchemaError(
            HarnessConfigFailureReason.HARNESS_CONFIG_MODEL_ID_AMBIGUOUS,
            "modelId contains more than one slash; provider/model boundary is ambiguous",
        )
    digest = schema.text(body["systemPromptDigest"], "systemPromptDigest")
    if _HEX64.fullmatch(digest) is None:
        raise schema.SchemaError(schema.INVALID, "systemPromptDigest must be 64 lowercase hex")
    return HarnessConfig(
        schema_version=HARNESS_CONFIG_SCHEMA,
        harness_name=schema.text(body["harnessName"], "harnessName"),
        harness_version=schema.text(body["harnessVersion"], "harnessVersion"),
        model_id=model_id,
        model_snapshot=schema.text(body["modelSnapshot"], "modelSnapshot"),
        adapter=schema.text(body["adapter"], "adapter"),
        bridge_endpoint_class=schema.text(body["bridgeEndpointClass"], "bridgeEndpointClass"),
        context_window_tokens=context,
        max_output_tokens=output,
        compaction_policy=schema.compaction(body["compactionPolicy"]),
        observation_truncation=schema.truncation(body["observationTruncation"]),
        max_turns=schema.positive(body["maxTurns"], "maxTurns"),
        max_iterations=schema.positive(body["maxIterations"], "maxIterations"),
        tool_call_cap=schema.positive(body["toolCallCap"], "toolCallCap"),
        wall_clock_timeout_seconds=schema.positive(
            body["wallClockTimeoutSeconds"], "wallClockTimeoutSeconds"
        ),
        temperature=_sampling(body["temperature"], "temperature", _TEMPERATURE_MAX),
        top_p=_sampling(body["topP"], "topP", 1.0),
        seed=schema.integer(body["seed"], "seed"),
        system_prompt_digest=digest,
        sandbox=schema.sandbox(body["sandbox"]),
        network_policy=schema.text(body["networkPolicy"], "networkPolicy"),
        retry_policy=schema.retry(body["retryPolicy"]),
        reasoning_effort=schema.text(body["reasoningEffort"], "reasoningEffort"),
        condenser_config=schema.condenser(body["condenserConfig"]),
        configuration_adequacy=schema.adequacy(body["configurationAdequacy"]),
    )


def parse_harness_config(document: str | bytes | None) -> HarnessConfigParseResult:
    """Return a typed configuration or refusal, never judging approval or adequacy."""
    if document is None:
        return HarnessConfigParseResult(
            None,
            HarnessConfigOutcome(
                False, HarnessConfigFailureReason.HARNESS_CONFIG_MISSING, "configuration is absent"
            ),
        )
    try:
        config = _configuration(parse_json(document))
    except CanonicalizationError as error:
        return HarnessConfigParseResult(
            None,
            HarnessConfigOutcome(
                False, HarnessConfigFailureReason.HARNESS_CONFIG_MALFORMED, str(error)
            ),
        )
    except schema.SchemaError as error:
        return HarnessConfigParseResult(
            None, HarnessConfigOutcome(False, error.reason, error.detail)
        )
    return HarnessConfigParseResult(config, HarnessConfigOutcome(True, None, ""))


def harness_config_digest(config_bytes: bytes) -> str:
    """Hash trinity.jcs-lf.v1 bytes; malformed JSON raises CanonicalizationError."""
    return hashlib.sha256(canonicalize_json(config_bytes)).hexdigest()
