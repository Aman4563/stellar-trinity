"""Shared byte caps, self-report guard and non-promoting format ceiling."""

from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import replace
from functools import wraps
from typing import Final

from .bundle import (
    MAX_BUNDLE_FILES,
    MAX_TRACE_BYTES,
    MAX_TRACE_LINES,
    RAW_AGENT_PATHS,
    FamilyAdapter,
    TraceBundle,
    strongest_supported_outcome,
)
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import RolloutFidelity, SignalClass, SignalFinding
from .reading import TraceReadError, child, integer, json_file

_POSITIVE_SCOPES: Final[ContextVar[tuple[list[SignalFinding], ...]]] = ContextVar(
    "fidelity_positive_scopes", default=()
)


def refused(bundle: TraceBundle, refusal: R) -> RolloutFidelity:
    return RolloutFidelity(
        bundle.rollout_id,
        bundle.family,
        tuple(
            SignalFinding(signal, O.INSUFFICIENT_EVIDENCE, refusal, "./trace:1")
            for signal in SignalClass
        ),
    )


def observed(signal: SignalClass, authorized: bool, pointer: str) -> SignalFinding:
    finding = SignalFinding(signal, O.COVERED_CLEAN if authorized else O.VIOLATION, None, pointer)
    if not authorized:
        for scope in _POSITIVE_SCOPES.get():
            scope.append(finding)
    return finding


def guarded(family: str) -> Callable[[FamilyAdapter], FamilyAdapter]:
    """Every public adapter, including direct registry calls, uses this boundary."""

    def decorate(adapter: FamilyAdapter) -> FamilyAdapter:
        @wraps(adapter)
        def run(bundle: TraceBundle) -> RolloutFidelity:
            if bundle.family != family:
                return refused(bundle, R.FIDELITY_FAMILY_UNRECOGNIZED)
            if len(bundle.files) > MAX_BUNDLE_FILES or any(
                len(raw) > MAX_TRACE_BYTES or raw.count(b"\n") > MAX_TRACE_LINES
                for raw in bundle.files.values()
            ):
                return refused(bundle, R.FIDELITY_TRACE_UNREADABLE)
            accompaniment = bundle.accompaniment - {"raw_agent_jsonl"}
            if any(path in bundle.files for path in RAW_AGENT_PATHS):
                accompaniment |= {"raw_agent_jsonl"}
            damaged: list[SignalFinding] = []
            readable = dict(bundle.files)
            for path in bundle.files:
                if not path.endswith(".json"):
                    continue
                try:
                    json_file(bundle, path)
                except TraceReadError as error:
                    del readable[path]
                    damaged.extend(
                        replace(finding, evidence_pointer=f"./{path}:1")
                        for finding in refused(bundle, error.refusal).findings
                    )
            supplied = replace(bundle, files=readable, accompaniment=frozenset(accompaniment))
            counter = None
            try:
                metadata = child(
                    child(json_file(supplied, "result.json"), "agent_result"), "metadata"
                )
                counter = integer(metadata, "summarization_count")
            except TraceReadError as error:
                damaged.extend(
                    replace(finding, evidence_pointer="./result.json:1")
                    for finding in refused(supplied, error.refusal).findings
                )
            positives: list[SignalFinding] = []
            token = _POSITIVE_SCOPES.set((*_POSITIVE_SCOPES.get(), positives))
            try:
                result = adapter(supplied)
            except (TraceReadError, RecursionError, UnicodeEncodeError):
                result = refused(supplied, R.FIDELITY_TRACE_UNREADABLE)
                result = replace(result, findings=(*result.findings, *positives))
            finally:
                _POSITIVE_SCOPES.reset(token)
            findings = [
                replace(
                    finding,
                    outcome=O.INSUFFICIENT_EVIDENCE,
                    refusal=R.FIDELITY_SELF_REPORTED_ONLY,
                    evidence_pointer="./result.json:1",
                )
                if counter is not None
                and finding.signal is SignalClass.COMPACTION
                and not any(
                    path != "result.json" and finding.evidence_pointer.startswith(f"./{path}:")
                    for path in supplied.files
                )
                and finding.refusal in (None, R.FIDELITY_SELF_REPORTED_ONLY)
                else finding
                for finding in result.findings
            ]
            findings.extend(damaged)
            covered = {finding.signal for finding in findings}
            for signal in SignalClass:
                if signal not in covered:
                    pointer = "./result.json:1" if counter is not None else "./trace:1"
                    findings.append(
                        SignalFinding(
                            signal, O.INSUFFICIENT_EVIDENCE, R.FIDELITY_SELF_REPORTED_ONLY, pointer
                        )
                    )
            ceiling, refusal = strongest_supported_outcome(result.family, supplied.accompaniment)
            return replace(
                result,
                findings=tuple(
                    replace(finding, outcome=ceiling, refusal=refusal)
                    if finding.outcome is O.COVERED_CLEAN and refusal is not None
                    else finding
                    for finding in findings
                ),
            )

        return run

    return decorate
