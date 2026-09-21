"""Native OpenHands condensation evidence, including forgotten-span continuity."""

from .bundle import TraceBundle
from .capture import capture
from .contracts import CAPTURE_VERSIONS
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import RolloutFidelity, SignalFinding
from .core import SignalClass as S
from .coverage import contract_findings
from .guard import guarded, observed
from .limits import limit_findings
from .reading import (
    TraceReadError,
    array,
    child,
    contiguous,
    integer,
    json_file,
    log_records,
    text,
)


@guarded("openhands_events")
def openhands_events(bundle: TraceBundle) -> RolloutFidelity:
    findings: list[SignalFinding] = []
    metadata = json_file(bundle, "run-metadata.json")
    condenser = text(child(metadata, "condenser_config"), "type")
    if condenser is not None and condenser != "noop":
        findings.append(
            observed(S.COMPACTION, bundle.authorization.compaction, "./run-metadata.json:1")
        )
    if "events.jsonl" not in bundle.files:
        return RolloutFidelity(bundle.rollout_id, bundle.family, tuple(findings))
    events = log_records(bundle.files["events.jsonl"])
    stream = capture(events, "events.jsonl")
    indices: list[int] = []
    for line, event in enumerate(events, 1):
        findings.extend(limit_findings(event, bundle.authorization, f"./events.jsonl:{line}"))
        index = integer(event, "id")
        if index is not None:
            indices.append(index)
        if text(event, "type") != "Condensation":
            continue
        forgotten: list[int] = []
        for value in array(event, "forgotten_event_ids"):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise TraceReadError
            forgotten.append(value)
        if text(event, "summary") is None or integer(event, "summary_offset") is None:
            raise TraceReadError
        pointer = f"./events.jsonl:{line}"
        if not forgotten or not contiguous(tuple(forgotten)):
            findings.append(
                SignalFinding(
                    S.COMPACTION, O.INSUFFICIENT_EVIDENCE, R.FIDELITY_SEQUENCE_INCOMPLETE, pointer
                )
            )
        else:
            findings.append(observed(S.COMPACTION, bundle.authorization.compaction, pointer))
    if indices and (len(indices) != len(events) or not contiguous(tuple(indices))):
        findings.append(
            SignalFinding(
                S.COMPACTION,
                O.INSUFFICIENT_EVIDENCE,
                R.FIDELITY_SEQUENCE_INCOMPLETE,
                "./events.jsonl:1",
            )
        )
    if (
        not any(f.signal is S.COMPACTION for f in findings)
        and stream.complete
        and condenser == "noop"
    ):
        supported = bundle.harness_version in CAPTURE_VERSIONS[bundle.family]
        findings.append(
            SignalFinding(
                S.COMPACTION,
                O.COVERED_CLEAN if supported else O.INSUFFICIENT_EVIDENCE,
                None if supported else R.FIDELITY_VERSION_UNSUPPORTED,
                "./events.jsonl:1",
            )
        )
    if not findings and events:
        findings.append(
            SignalFinding(
                S.COMPACTION,
                O.INSUFFICIENT_EVIDENCE,
                R.FIDELITY_SEQUENCE_INCOMPLETE,
                "./events.jsonl:1",
            )
        )
    findings.extend(contract_findings(bundle, events, "events.jsonl"))
    return RolloutFidelity(bundle.rollout_id, bundle.family, tuple(findings))
