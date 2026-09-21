"""Positive coverage for instrumented native streams; no counter supplies coverage."""

import re
from collections.abc import Mapping
from http import HTTPStatus

from .bundle import TraceBundle
from .capture import NativeCapture, capture
from .contracts import CAPTURE_VERSIONS, CLEAN_STOPS, REFUSAL_MARKERS
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import SignalClass as S
from .core import SignalFinding
from .guard import observed
from .reading import Json, boolean, child, integer, json_file, text


def contract_findings(
    bundle: TraceBundle, records: tuple[Mapping[str, Json], ...], path: str
) -> tuple[SignalFinding, ...]:
    stream = capture(records, path)
    findings: list[SignalFinding] = []
    for check in (_setup, _refusal, _handoff, _provider, _observations, _timeout):
        findings.extend(check(bundle, stream))
    supported = bundle.harness_version in CAPTURE_VERSIONS[bundle.family]
    return tuple(
        SignalFinding(
            finding.signal,
            O.INSUFFICIENT_EVIDENCE,
            R.FIDELITY_VERSION_UNSUPPORTED if not supported else R.FIDELITY_SEQUENCE_INCOMPLETE,
            finding.evidence_pointer,
        )
        if finding.outcome is O.COVERED_CLEAN and (not supported or not stream.complete)
        else finding
        for finding in findings
    )


def _setup(bundle: TraceBundle, stream: NativeCapture) -> tuple[SignalFinding, ...]:
    del bundle
    boot = stream.of_type("bootstrap")
    statuses = tuple(text(event, "status") for event in (stream.start, *boot))
    if any(status in {"error", "failed"} for status in statuses):
        return (observed(S.SETUP_FAILURE, False, stream.pointer),)
    if stream.inventoried("bootstrap", "bootstrap_id") and all(s == "success" for s in statuses):
        return (observed(S.SETUP_FAILURE, True, stream.pointer),)
    return ()


def _refusal(bundle: TraceBundle, stream: NativeCapture) -> tuple[SignalFinding, ...]:
    del bundle
    assistant = stream.of_type("assistant")
    reasons = tuple(
        text(event, "stop_reason") or text(child(event, "message"), "stop_reason")
        for event in (*assistant, stream.terminal)
    )
    markers = tuple(
        text(source, "stop_reason")
        for event in stream.records
        for source in (event, child(event, "message"))
    )
    if any(marker in REFUSAL_MARKERS for marker in markers):
        return (observed(S.REFUSAL, False, stream.pointer),)
    if stream.inventoried("assistant", "request_id") and all(r in CLEAN_STOPS for r in reasons):
        return (observed(S.REFUSAL, True, stream.pointer),)
    return ()


def _handoff(bundle: TraceBundle, stream: NativeCapture) -> tuple[SignalFinding, ...]:
    submission = json_file(bundle, "submission.json")
    submitted = text(submission, "sha256")
    received = text(stream.terminal, "submission_sha256")
    session = text(submission, "session_id")
    if (
        not all(
            value is not None and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in (submitted, received)
        )
        or not session
        or not stream.session_id
    ):
        return ()
    return (
        observed(
            S.HANDOFF_FAILURE,
            submitted == received and session == stream.session_id,
            stream.pointer,
        ),
    )


def _provider(bundle: TraceBundle, stream: NativeCapture) -> tuple[SignalFinding, ...]:
    del bundle
    statuses = tuple(integer(event, "status_code") for event in stream.of_type("provider_request"))
    if any(
        status is not None and not HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES
        for status in statuses
    ):
        return (observed(S.PROVIDER_ERROR, False, stream.pointer),)
    if stream.inventoried("provider_request", "request_id") and all(
        s is not None for s in statuses
    ):
        return (observed(S.PROVIDER_ERROR, True, stream.pointer),)
    return ()


def _observations(bundle: TraceBundle, stream: NativeCapture) -> tuple[SignalFinding, ...]:
    limit = integer(stream.start, "max_message_chars")
    results = stream.of_type("tool_result")
    flags = tuple(boolean(event, "truncated") for event in results)
    findings: list[SignalFinding] = []
    for event, flag in zip(results, flags, strict=True):
        if flag:
            effective = integer(event, "max_message_chars")
            approved = effective is not None and effective == bundle.authorization.max_message_chars
            findings.append(observed(S.OBSERVATION_TRUNCATION, approved, stream.pointer))
    if (
        limit is not None
        and limit > 0
        and stream.inventoried("tool_result", "tool_result_id")
        and all(flag is not None for flag in flags)
    ):
        findings.append(observed(S.OBSERVATION_TRUNCATION, True, stream.pointer))
    elif findings and all(f.outcome is O.COVERED_CLEAN for f in findings):
        findings.append(
            SignalFinding(
                S.OBSERVATION_TRUNCATION,
                O.INSUFFICIENT_EVIDENCE,
                R.FIDELITY_SELF_REPORTED_ONLY,
                stream.pointer,
            )
        )
    return tuple(findings)


def _timeout(bundle: TraceBundle, stream: NativeCapture) -> tuple[SignalFinding, ...]:
    terminal = stream.terminal
    timed_out = boolean(terminal, "timed_out")
    timeout = integer(terminal, "timeout_seconds")
    elapsed = integer(terminal, "elapsed_seconds")
    if timed_out is False and timeout is not None and elapsed is not None:
        return (
            observed(
                S.TIMEOUT,
                timeout == bundle.authorization.timeout_seconds and elapsed <= timeout,
                stream.pointer,
            ),
        )
    return ()
