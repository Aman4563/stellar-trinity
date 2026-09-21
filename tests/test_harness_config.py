"""Closed harness configuration boundaries, including the observed incident."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from tools import harness_config as hc
from tools._harness_config_schema import ApprovalSource
from tools.attest.canonical import JSONValue, canonical_sha256
from tools.harness_config import (
    HARNESS_CONFIG_FIELDS,
    harness_config_digest,
    parse_harness_config,
)
from tools.harness_config import (
    HarnessConfigFailureReason as Reason,
)


def incident_configuration() -> dict[str, JSONValue]:
    return {
        "schemaVersion": "trinity.harness-config/v1",
        "harnessName": "claude-code",
        "harnessVersion": "2.1.159",
        "modelId": "anthropic/claude-opus-5",
        "modelSnapshot": "claude-opus-5-20260901",
        "adapter": "claude-code",
        "bridgeEndpointClass": "direct",
        "contextWindowTokens": 200000,
        "maxOutputTokens": 32000,
        "compactionPolicy": {"enabled": True, "trigger": "auto", "thresholdTokens": 168000},
        "observationTruncation": {"maxMessageChars": 30000, "maxObservationChars": 60000},
        "maxTurns": 300,
        "maxIterations": 200,
        "toolCallCap": 1000,
        "wallClockTimeoutSeconds": 3600,
        "temperature": 1.0,
        "topP": 1.0,
        "seed": 42,
        "systemPromptDigest": "a" * 64,
        "sandbox": {"cpuMillicores": 2000, "memoryBytes": 8589934592},
        "networkPolicy": "restricted",
        "retryPolicy": {"maxRetries": 4, "retryOnStatus": [429, 500, 503]},
        "reasoningEffort": "high",
        "condenserConfig": {"type": "none", "enabled": False},
        "configurationAdequacy": {
            "approvedBy": "operator",
            "approvalSource": "requirements",
            "headroomArgument": "168000 tokens declared; adequacy is assessed separately.",
            "approvedAt": "2026-09-18T00:00:00Z",
        },
    }


def test_accepts_the_incident_configuration() -> None:
    # Given the observed configuration, not a claim that it was adequate.
    document = json.dumps(incident_configuration())
    # When parsing the declared configuration.
    result = parse_harness_config(document)
    # Then the actual observed limits survive unchanged.
    assert result.outcome.accepted and result.outcome.reason is None
    assert result.config is not None
    assert result.config.context_window_tokens == 200000
    assert result.config.max_output_tokens == 32000
    assert result.config.compaction_policy.threshold_tokens == 168000
    assert result.config.compaction_policy.trigger == "auto"
    assert result.config.observation_truncation.max_message_chars == 30000
    assert result.config.retry_policy.max_retries == 4
    assert result.config.max_turns == 300
    assert result.config.max_iterations == 200


@pytest.mark.parametrize(
    "section",
    [
        None,
        "compactionPolicy",
        "observationTruncation",
        "sandbox",
        "retryPolicy",
        "condenserConfig",
        "configurationAdequacy",
    ],
)
def test_refuses_unknown_field(section: str | None) -> None:
    # Given an extra field at any object boundary.
    value = incident_configuration()
    target = value if section is None else value[section]
    assert isinstance(target, dict)
    target["undeclared"] = True
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then nothing outside the schema survives.
    assert result.config is None
    assert result.outcome.reason == Reason.HARNESS_CONFIG_FIELD_UNKNOWN


@pytest.mark.parametrize("field", tuple(incident_configuration()))
def test_refuses_absent_field(field: str) -> None:
    # Given any one of the independently enumerated 25 fields missing.
    value = incident_configuration()
    assert len(value) == 25 and frozenset(value) == HARNESS_CONFIG_FIELDS
    del value[field]
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then defaults cannot silently replace declarations.
    assert result.config is None
    assert result.outcome.reason == Reason.HARNESS_CONFIG_FIELD_ABSENT


def test_refuses_unsupported_schema_version_first() -> None:
    # Given an unsupported schema with both absent and unknown fields.
    value = {"schemaVersion": "trinity.harness-config/v0", "unexpected": False}
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then version refusal precedes field validation.
    assert result.outcome.reason == Reason.HARNESS_CONFIG_SCHEMA_UNSUPPORTED


@pytest.mark.parametrize("output", [200000, 200001])
def test_refuses_negative_headroom(output: int) -> None:
    # Given zero or negative headroom.
    value = incident_configuration() | {"maxOutputTokens": output}
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then the dedicated refusal fires.
    assert result.outcome.reason == Reason.HARNESS_CONFIG_NEGATIVE_HEADROOM


def test_refuses_compaction_enabled_with_trigger_none() -> None:
    # Given contradictory compaction declarations.
    value = incident_configuration() | {
        "compactionPolicy": {"enabled": True, "trigger": "none", "thresholdTokens": 168000}
    }
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then the contradiction is refused.
    assert result.outcome.reason == Reason.HARNESS_CONFIG_VALUE_INVALID


def test_refuses_ambiguous_model_id() -> None:
    # Given the observed bridge model-id defect.
    value = incident_configuration() | {"modelId": "anthropic/glm-5/3"}
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then the dedicated ambiguity refusal fires.
    assert result.outcome.reason == Reason.HARNESS_CONFIG_MODEL_ID_AMBIGUOUS
    assert "modelId" in result.outcome.detail


@pytest.mark.parametrize(
    "field,number",
    [
        ("temperature", -0.1),
        ("temperature", 2.1),
        ("temperature", float("nan")),
        ("temperature", float("inf")),
        ("temperature", True),
        ("topP", -0.1),
        ("topP", 1.1),
        ("topP", float("-inf")),
        ("topP", False),
    ],
)
def test_refuses_bad_temperature_and_top_p(field: str, number: JSONValue) -> None:
    # Given an out-of-range, non-finite, or boolean sampling parameter.
    value = incident_configuration() | {field: number}
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then it cannot produce a configuration.
    assert result.config is None and not result.outcome.accepted
    assert result.outcome.reason in {
        Reason.HARNESS_CONFIG_VALUE_INVALID,
        Reason.HARNESS_CONFIG_MALFORMED,
    }


@pytest.mark.parametrize("statuses", [[500, 429], [429, 429], [True], [429.0], ["429"]])
def test_refuses_unsorted_or_duplicate_retry_status(statuses: list[JSONValue]) -> None:
    # Given a noncanonical or non-integer retry list.
    value = incident_configuration() | {"retryPolicy": {"maxRetries": 4, "retryOnStatus": statuses}}
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then it is refused rather than silently sorted or deduplicated.
    assert result.outcome.reason == Reason.HARNESS_CONFIG_VALUE_INVALID


def test_refuses_bad_adequacy_source() -> None:
    # Given an approval source outside the closed vocabulary.
    value = incident_configuration()
    adequacy = value["configurationAdequacy"]
    assert isinstance(adequacy, dict)
    adequacy["approvalSource"] = "self"
    # When parsing.
    result = parse_harness_config(json.dumps(value))
    # Then structural approval provenance is refused, without an adequacy judgment.
    assert result.outcome.reason == Reason.HARNESS_CONFIG_VALUE_INVALID


def test_digest_is_canonical_and_stable() -> None:
    # Given reordered keys, changed whitespace, and one changed configuration value.
    value = incident_configuration()
    original = json.dumps(value).encode()
    reordered = json.dumps(dict(reversed(list(value.items()))), indent=2).encode()
    changed = json.dumps(value | {"maxTurns": 1000}).encode()
    # When hashing each representation through the public boundary.
    digests = tuple(harness_config_digest(raw) for raw in (original, reordered, changed))
    # Then only the semantic change alters the shared canonical-profile digest.
    assert digests[0] == digests[1] == canonical_sha256(value)
    assert digests[0] != digests[2]


@pytest.fixture
def config() -> hc.HarnessConfig:
    result = parse_harness_config(json.dumps(incident_configuration()))
    assert result.config is not None
    return result.config


@pytest.fixture
def approval() -> hc.HarnessApproval:
    return hc.HarnessApproval(True, 30000, 168000, ApprovalSource.REQUIREMENTS, "operator")


@pytest.mark.parametrize("source", list(ApprovalSource))
def test_adequacy_refuses_self_declared_approval(
    config: hc.HarnessConfig, source: ApprovalSource
) -> None:
    # Given a declaration without independent approval.
    declared = replace(config.configuration_adequacy, approval_source=source)
    # When checking adequacy.
    result = hc.evaluate_adequacy(replace(config, configuration_adequacy=declared), None, None)
    # Then self-approval fails closed.
    assert not result.accepted and result.reason == Reason.HARNESS_CONFIG_UNAPPROVED


@pytest.mark.parametrize("authorized", [False, True])
def test_adequacy_refuses_unauthorized_compaction(
    config: hc.HarnessConfig, approval: hc.HarnessApproval, authorized: bool
) -> None:
    # Given explicit compaction authorization or its denial.
    grant = replace(approval, authorizes_compaction=authorized)
    # When checking the identical enabled config.
    result = hc.evaluate_adequacy(config, grant, None)
    # Then only opt-in compaction passes.
    assert result.accepted is authorized
    assert result.reason == (None if authorized else Reason.HARNESS_CONFIG_INADEQUATE)


def test_adequacy_refuses_truncation_below_floor(
    config: hc.HarnessConfig, approval: hc.HarnessApproval
) -> None:
    # Given teresa's 30000-character cap against a 100000-character floor.
    grant = replace(approval, min_message_chars=100000)
    # When checking adequacy.
    result = hc.evaluate_adequacy(config, grant, None)
    # Then approval alone cannot make the cap adequate.
    assert not result.accepted and result.reason == Reason.HARNESS_CONFIG_INADEQUATE


@pytest.mark.parametrize("minimum,argument", [(168001, "declared"), (168000, "")])
def test_adequacy_refuses_headroom_below_minimum(
    config: hc.HarnessConfig, approval: hc.HarnessApproval, minimum: int, argument: str
) -> None:
    # Given insufficient headroom or a structurally absent headroom argument.
    declared = replace(config.configuration_adequacy, headroom_argument=argument)
    grant = replace(approval, min_headroom_tokens=minimum)
    # When checking adequacy.
    result = hc.evaluate_adequacy(replace(config, configuration_adequacy=declared), grant, None)
    # Then numerical headroom and its argument are independently required.
    assert not result.accepted and result.reason == Reason.HARNESS_CONFIG_INADEQUATE


@pytest.mark.parametrize("source", list(ApprovalSource))
def test_adequacy_accepts_fully_approved_config(
    config: hc.HarnessConfig, approval: hc.HarnessApproval, source: ApprovalSource
) -> None:
    # Given matching approval at the exact declared floors.
    declared = replace(config.configuration_adequacy, approval_source=source)
    grants = {source: replace(approval, source=source)}
    # When checking the selected independent source.
    result = hc.evaluate_adequacy(
        replace(config, configuration_adequacy=declared),
        grants.get(ApprovalSource.REQUIREMENTS),
        grants.get(ApprovalSource.TOUCHSTONES),
    )
    # Then the machine-checkable predicates pass.
    assert result.accepted and result.reason is None


@pytest.mark.parametrize("turns", [300, 1000])
def test_reconcile_refuses_drift(config: hc.HarnessConfig, turns: int) -> None:
    # Given either an unchanged or changed turn cap.
    observed = replace(config, max_turns=turns)
    digest = "a" * 64 if turns == 300 else "b" * 64
    # When reconciling the matching or differing digest.
    result = hc.reconcile("a" * 64, digest, config, observed)
    # Then only drift refuses release.
    assert result.accepted is (turns == 300)
    assert result.reason == (None if turns == 300 else Reason.HARNESS_CONFIG_DRIFT)


@pytest.mark.parametrize(
    "field,values",
    [
        ("maxTurns", (300, 1000)),
        ("modelId", ("anthropic/claude-opus-5", "provider/private-model")),
        ("contextWindowTokens", (200000, 400000)),
    ],
)
def test_drift_detail_names_fields_not_values(
    field: str, values: tuple[JSONValue, JSONValue]
) -> None:
    # Given one changed field, with distinct private values.
    bound = parse_harness_config(json.dumps(incident_configuration()))
    observed = parse_harness_config(json.dumps(incident_configuration() | {field: values[1]}))
    # When reconciling.
    result = hc.reconcile("a" * 64, "b" * 64, bound.config, observed.config)
    # Then only the field name is disclosed.
    assert result.detail == field
    assert all(str(value) not in result.detail for value in values)


@pytest.mark.parametrize("bound_absent", [True, False])
def test_reconcile_refuses_absent_side(config: hc.HarnessConfig, bound_absent: bool) -> None:
    # Given either missing configuration.
    bound, observed = (None, config) if bound_absent else (config, None)
    # When reconciling even equal digests.
    result = hc.reconcile("a" * 64, "a" * 64, bound, observed)
    # Then absence never passes as equality.
    assert not result.accepted and result.reason == Reason.HARNESS_CONFIG_MISSING


def test_mirror_matches_on_reordered_keys() -> None:
    # Given semantically identical documents.
    value = incident_configuration()
    reordered = json.dumps(dict(reversed(list(value.items()))), indent=2).encode()
    # When comparing reordered and pretty-printed bytes.
    result = hc.mirror_matches(json.dumps(value).encode(), reordered)
    # Then canonical identity matches.
    assert result


def test_mirror_rejects_single_value_change() -> None:
    # Given one changed turn cap.
    value = incident_configuration()
    changed = json.dumps(value | {"maxTurns": 1000}).encode()
    # When comparing mirrors.
    result = hc.mirror_matches(json.dumps(value).encode(), changed)
    # Then canonical identity differs.
    assert not result
