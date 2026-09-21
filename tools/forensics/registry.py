"""Closed dispatch over guarded family adapters."""

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import Final

from .atif_normalized import atif_normalized
from .bundle import FamilyAdapter, TraceBundle
from .contracts import COVERAGE_CONTRACTS
from .core import FidelityOutcome, FidelityRefusal, RolloutFidelity, SignalClass
from .guard import refused
from .native import NATIVE_ADAPTERS
from .reading import TraceReadError, log_records, text

FIDELITY_FAMILIES: Final[Mapping[str, FamilyAdapter]] = MappingProxyType(
    {
        **NATIVE_ADAPTERS,
        "atif_normalized": atif_normalized,
    }
)


def analyze_trace(bundle: TraceBundle) -> RolloutFidelity:
    """Classify a trace through guarded adapters and reconcile clean rollout identity."""
    if bundle.family not in FIDELITY_FAMILIES:
        return refused(bundle, FidelityRefusal.FIDELITY_FAMILY_UNRECOGNIZED)
    result = FIDELITY_FAMILIES[bundle.family](bundle)
    if result.overall is not FidelityOutcome.COVERED_CLEAN:
        return result
    try:
        for path in COVERAGE_CONTRACTS[result.family][SignalClass.COMPACTION].native_paths:
            if path not in bundle.files:
                continue
            for line, event in enumerate(log_records(bundle.files[path]), 1):
                recorded = text(event, "rollout_id")
                if recorded is not None and recorded != bundle.rollout_id:
                    return replace(
                        result,
                        findings=tuple(
                            replace(
                                finding,
                                outcome=FidelityOutcome.INSUFFICIENT_EVIDENCE,
                                refusal=FidelityRefusal.FIDELITY_TRACE_UNREADABLE,
                                evidence_pointer=f"./rollout_identity_mismatch/{path}:{line}",
                            )
                            for finding in result.findings
                        ),
                    )
    except TraceReadError as error:
        return refused(bundle, error.refusal)
    return result
