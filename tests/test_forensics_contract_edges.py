import json
from dataclasses import replace

import pytest
from tools import forensics as f

from tests.test_forensics_contracts import NATIVE, complete_bundle, native_records, signal_outcome


@pytest.mark.parametrize("family", NATIVE)
@pytest.mark.parametrize("key", ["capture_profile", "session_id"])
def test_capture_header_missing_cannot_cover(family: str, key: str) -> None:
    # Given: otherwise complete records without a required capture-header field.
    records = native_records(family)
    del records[0][key]
    # When / Then: no global clean verdict is possible.
    assert f.analyze_trace(complete_bundle(family, records)).overall is (
        f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    )


@pytest.mark.parametrize("family", NATIVE)
def test_unknown_version_cannot_cover(family: str) -> None:
    # Given: full positive records but no reviewed vocabulary for this version.
    trace = replace(complete_bundle(family), harness_version="future")
    # When / Then: no nearest-version guessing.
    assert f.analyze_trace(trace).overall is f.FidelityOutcome.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("family", NATIVE)
@pytest.mark.parametrize(
    ("index", "signal"),
    [
        (1, f.SignalClass.SETUP_FAILURE),
        (2, f.SignalClass.PROVIDER_ERROR),
        (3, f.SignalClass.REFUSAL),
        (4, f.SignalClass.OBSERVATION_TRUNCATION),
    ],
)
def test_removed_record_with_renumbered_sequence_still_lacks_coverage(
    family: str, index: int, signal: f.SignalClass
) -> None:
    # Given: stripped native evidence, with the obvious sequence hole concealed.
    records = native_records(family)
    records.pop(index)
    key = "id" if family.startswith("openhands") else "index"
    for number, event in enumerate(records):
        event[key] = number
    # When / Then: terminal inventories still require the missing positive evidence.
    assert signal_outcome(f.analyze_trace(complete_bundle(family, records)), signal) is (
        f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    )


@pytest.mark.parametrize("family", NATIVE)
@pytest.mark.parametrize("marker", ["refusal", "aup", "policy_violation", "content_filter"])
def test_nested_refusal_marker_is_not_hidden_by_clean_stop(family: str, marker: str) -> None:
    # Given: a native assistant's nested stop marker contradicts its outer reason.
    records = native_records(family)
    records[3]["message"] = {"stop_reason": marker}
    # When / Then: any positive marker wins.
    assert signal_outcome(
        f.analyze_trace(complete_bundle(family, records)), f.SignalClass.REFUSAL
    ) is (f.FidelityOutcome.VIOLATION)


@pytest.mark.parametrize("family", NATIVE)
def test_authorized_truncation_needs_every_observation(family: str) -> None:
    # Given: approved truncation on one result cannot cover a second unmarked result.
    records = native_records(family)
    records[4].update({"truncated": True, "max_message_chars": 100})
    extra = dict(records[4])
    extra["tool_result_id"] = "other"
    del extra["truncated"]
    records.insert(5, extra)
    records[-1]["tool_result_ids"] = ["obs", "other"]
    key = "id" if family.startswith("openhands") else "index"
    for number, event in enumerate(records):
        event[key] = number
    # When / Then: the missing marker remains indeterminate.
    result = f.analyze_trace(complete_bundle(family, records))
    assert signal_outcome(result, f.SignalClass.OBSERVATION_TRUNCATION) is (
        f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    )


def test_approved_truncation_config_alone_does_not_cover_metrics() -> None:
    # Given: approved configuration, but the native observation record was stripped.
    trace = complete_bundle("openhands_native_metrics")
    trace = replace(
        trace,
        files={
            "run-metadata.json": json.dumps(
                {"condenser_config": {"type": "noop"}, "llm_config": {"max_message_chars": 100}}
            ).encode()
        },
    )
    # When / Then: a declaration cannot replace observed tool delivery.
    assert signal_outcome(f.analyze_trace(trace), f.SignalClass.OBSERVATION_TRUNCATION) is (
        f.FidelityOutcome.INSUFFICIENT_EVIDENCE
    )


@pytest.mark.parametrize("family", NATIVE)
def test_approved_truncation_stays_conforming(family: str) -> None:
    # Given: every observation is captured and truncation matches authorization.
    records = native_records(family)
    records[4].update({"truncated": True, "max_message_chars": 100})
    # When / Then: an approved transformation is not a violation.
    assert (
        f.analyze_trace(complete_bundle(family, records)).overall is f.FidelityOutcome.COVERED_CLEAN
    )


@pytest.mark.parametrize("family", NATIVE)
def test_submission_session_mismatch_is_violation(family: str) -> None:
    # Given: same digest, but a final-submission record from a different session.
    trace = complete_bundle(family)
    trace = replace(
        trace,
        files={
            **trace.files,
            "submission.json": json.dumps({"session_id": "different", "sha256": "a" * 64}).encode(),
        },
    )
    # When / Then: digest equality cannot repair a run-identity mismatch.
    assert signal_outcome(f.analyze_trace(trace), f.SignalClass.HANDOFF_FAILURE) is (
        f.FidelityOutcome.VIOLATION
    )


@pytest.mark.parametrize("family", NATIVE)
def test_accompanied_atif_can_reach_native_clean(family: str) -> None:
    # Given: ATIF is only an index to complete native capture.
    native = complete_bundle(family)
    trace = replace(
        native,
        family="atif_normalized",
        harness_version="1.8",
        accompaniment=frozenset({family}),
        files={
            **native.files,
            "agent/trajectory.json": json.dumps(
                {
                    "steps": [],
                    "agent": {"version": native.harness_version, "model_name": "synthetic"},
                }
            ).encode(),
        },
    )
    # When / Then: dispatch returns the native identity and native evidence verdict.
    result = f.analyze_trace(trace)
    assert (result.family, result.overall) == (family, f.FidelityOutcome.COVERED_CLEAN)
