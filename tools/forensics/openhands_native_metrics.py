"""Configuration transformations and native per-attempt OpenHands accounting."""

from dataclasses import replace
from http import HTTPStatus

from .bundle import TraceBundle
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import RolloutFidelity, SignalFinding
from .core import SignalClass as S
from .guard import guarded, observed
from .limits import limit_findings
from .openhands_events import openhands_events
from .reading import array, child, integer, json_file, record, text


@guarded("openhands_native_metrics")
def openhands_native_metrics(bundle: TraceBundle) -> RolloutFidelity:
    metadata = json_file(bundle, "run-metadata.json")
    metrics = json_file(bundle, "metrics.json")
    llm = child(metadata, "llm_config")
    findings = list(limit_findings(metadata, bundle.authorization, "./run-metadata.json:1"))
    findings.extend(limit_findings(metrics, bundle.authorization, "./metrics.json:1"))
    message_chars = integer(llm, "max_message_chars")
    retries = integer(llm, "num_retries")
    if message_chars is not None and message_chars != bundle.authorization.max_message_chars:
        findings.append(
            observed(
                S.OBSERVATION_TRUNCATION,
                False,
                "./run-metadata.json:1",
            )
        )
    if retries is not None and retries > 0:
        attempts = array(metrics, "attempts")
        statuses = tuple(integer(record(attempt), "status_code") for attempt in attempts)
        complete = len(statuses) == retries + 1 and all(status is not None for status in statuses)
        if complete:
            findings.append(
                observed(
                    S.PROVIDER_ERROR,
                    all(
                        status is not None and HTTPStatus.OK <= status < HTTPStatus.MULTIPLE_CHOICES
                        for status in statuses
                    ),
                    "./metrics.json:1",
                )
            )
        else:
            findings.append(
                SignalFinding(
                    S.PROVIDER_ERROR,
                    O.INSUFFICIENT_EVIDENCE,
                    R.FIDELITY_SELF_REPORTED_ONLY,
                    "./run-metadata.json:1",
                )
            )
    condenser = text(child(metadata, "condenser_config"), "type")
    if condenser is not None and condenser != "noop":
        findings.append(
            observed(S.COMPACTION, bundle.authorization.compaction, "./run-metadata.json:1")
        )
    if "events.jsonl" in bundle.files:
        native = openhands_events(replace(bundle, family="openhands_events"))
        findings.extend(native.findings)
    return RolloutFidelity(bundle.rollout_id, bundle.family, tuple(findings))
