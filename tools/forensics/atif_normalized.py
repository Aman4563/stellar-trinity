"""ATIF conversion can preserve positive evidence, never prove marker absence."""

from dataclasses import replace
from typing import Final, assert_never

from .bundle import NATIVE_FAMILIES, TraceBundle
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import RolloutFidelity, SignalFinding
from .core import SignalClass as S
from .guard import guarded, observed, refused
from .native import NATIVE_ADAPTERS, available_sources
from .reading import Json, TraceReadError, array, child, integer, json_file, record, text

CONTINUATION_MARKER: Final = (
    "This session is being continued from a previous conversation that ran out of context"
)


def contains_marker(value: Json) -> bool:
    pending = [value]
    while pending:
        item = pending.pop()
        match item:
            case str():
                if CONTINUATION_MARKER in item:
                    return True
            case dict():
                pending.extend(item.values())
            case list():
                pending.extend(item)
            case bool() | int() | float() | None:
                continue
            case unreachable:
                assert_never(unreachable)
    return False


@guarded("atif_normalized")
def atif_normalized(bundle: TraceBundle) -> RolloutFidelity:
    path = "agent/trajectory.json"
    if path not in bundle.files:
        return RolloutFidelity(bundle.rollout_id, bundle.family, ())
    trajectory = json_file(bundle, path)
    try:
        version = tuple(int(part) for part in bundle.harness_version.split("."))
    except ValueError:
        return refused(bundle, R.FIDELITY_VERSION_UNSUPPORTED)
    native_version = ""
    if version >= (1, 8):
        reference = text(trajectory, "continued_trajectory_ref")
        agent = child(trajectory, "agent")
        text(agent, "model_name")
        native_version = text(agent, "version") or ""
        for step in array(trajectory, "steps"):
            metrics = child(record(step), "metrics")
            for key in ("prompt_tokens", "completion_tokens", "cached_tokens"):
                integer(metrics, key)
        if reference is not None and (reference.startswith("/") or ".." in reference.split("/")):
            raise TraceReadError
    marker = any(contains_marker(value) for value in trajectory.values())
    finding = (
        observed(S.COMPACTION, bundle.authorization.compaction, f"./{path}:1")
        if marker
        else SignalFinding(
            S.COMPACTION,
            O.INSUFFICIENT_EVIDENCE,
            R.FIDELITY_TRACE_CONVERSION_ONLY,
            f"./{path}:1",
        )
    )
    sources = bundle.accompaniment & NATIVE_FAMILIES & available_sources(bundle)
    if len(sources) == 1:
        family = next(iter(sources))
        native = NATIVE_ADAPTERS[family](
            replace(bundle, family=family, harness_version=native_version)
        )
        return replace(native, findings=(*native.findings, finding)) if marker else native
    return RolloutFidelity(bundle.rollout_id, bundle.family, (finding,))
