"""Usage accounting supplements native logs; it never proves compaction absence."""

from dataclasses import replace

from .bundle import RAW_AGENT_PATHS, TraceBundle
from .claude_code_jsonl import claude_code_jsonl
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import RolloutFidelity, SignalFinding
from .core import SignalClass as S
from .guard import guarded, observed
from .reading import integer, json_file


@guarded("cybergym_usage")
def cybergym_usage(bundle: TraceBundle) -> RolloutFidelity:
    usage = json_file(bundle, "usage.json")
    turns = integer(usage, "turns")
    tokens = integer(usage, "tokens")
    max_turns = integer(usage, "maxTurns")
    context_window = integer(usage, "contextWindowTokens")
    findings: list[SignalFinding] = []
    if any(path in bundle.files for path in RAW_AGENT_PATHS):
        native = claude_code_jsonl(replace(bundle, family="claude_code_jsonl"))
        findings.extend(native.findings)
    if max_turns is not None and turns is not None and turns >= max_turns:
        findings.append(
            observed(
                S.TURN_CAP, turns == max_turns == bundle.authorization.max_turns, "./usage.json:1"
            )
        )
    approved_context = bundle.authorization.context_window_tokens
    if (
        context_window is not None
        and approved_context is not None
        and context_window < approved_context
    ):
        findings.append(observed(S.OBSERVATION_TRUNCATION, False, "./usage.json:1"))
    if tokens is not None and approved_context is not None and tokens > approved_context:
        # Cumulative usage cannot establish per-request context occupancy.
        findings.append(
            SignalFinding(
                S.OBSERVATION_TRUNCATION,
                O.INSUFFICIENT_EVIDENCE,
                R.FIDELITY_SELF_REPORTED_ONLY,
                "./usage.json:1",
            )
        )
    return RolloutFidelity(bundle.rollout_id, bundle.family, tuple(findings))
