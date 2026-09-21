"""Claude Code native vocabulary pinned by reviewed versions.

DISABLE_AUTO_COMPACT is unreliable per anthropics/claude-code #42817 and #57490;
#64520 reports the v2.1.159 silent default change. Never infer version support
from semver proximity or from an operator's claim that auto-compaction is off.
"""

from typing import Final

from .bundle import RAW_AGENT_PATHS, TraceBundle
from .core import FidelityOutcome as O
from .core import FidelityRefusal as R
from .core import RolloutFidelity, SignalFinding
from .core import SignalClass as S
from .coverage import contract_findings
from .guard import guarded, observed, refused
from .limits import limit_findings
from .reading import boolean, child, contiguous, integer, log_records, text

SUPPORTED_VERSIONS: Final = frozenset({"2.1.158", "2.1.159"})


@guarded("claude_code_jsonl")
def claude_code_jsonl(bundle: TraceBundle) -> RolloutFidelity:
    if bundle.harness_version not in SUPPORTED_VERSIONS:
        return refused(bundle, R.FIDELITY_VERSION_UNSUPPORTED)
    paths = tuple(path for path in RAW_AGENT_PATHS if path in bundle.files)
    if len(paths) != 1:
        return refused(bundle, R.FIDELITY_SELF_REPORTED_ONLY)
    path = paths[0]
    records = log_records(bundle.files[path])
    findings: list[SignalFinding] = []
    indices = tuple(integer(event, "index") for event in records)
    sequence = tuple(index for index in indices if index is not None)
    complete = (
        bool(sequence)
        and sequence[0] in (0, 1)
        and len(sequence) == len(records)
        and contiguous(sequence)
        and text(records[0], "subtype") == "init"
    )
    for line, event in enumerate(records, 1):
        findings.extend(limit_findings(event, bundle.authorization, f"./{path}:{line}"))
        boundary = text(event, "type") == "system" and text(event, "subtype") == "compact_boundary"
        summary = boolean(event, "isCompactSummary") is True
        if boundary or summary:
            pointer = f"./{path}:{line}"
            if boundary:
                metadata = child(event, "compact_metadata")
                trigger = text(metadata, "trigger")
                tokens = integer(metadata, "pre_tokens")
                if trigger is None or tokens is None:
                    findings.append(
                        SignalFinding(
                            S.COMPACTION,
                            O.INSUFFICIENT_EVIDENCE,
                            R.FIDELITY_TRACE_UNREADABLE,
                            pointer,
                        )
                    )
                    continue
                pointer += f"#pre_tokens={tokens}"
            findings.append(observed(S.COMPACTION, bundle.authorization.compaction, pointer))
    if sequence and (len(sequence) != len(records) or not contiguous(sequence)):
        findings.append(
            SignalFinding(
                S.COMPACTION, O.INSUFFICIENT_EVIDENCE, R.FIDELITY_SEQUENCE_INCOMPLETE, f"./{path}:1"
            )
        )
    if not any(finding.signal is S.COMPACTION for finding in findings):
        terminated = complete and text(records[-1], "type") == "result"
        findings.append(
            SignalFinding(
                S.COMPACTION,
                O.COVERED_CLEAN if terminated else O.INSUFFICIENT_EVIDENCE,
                None if terminated else R.FIDELITY_SEQUENCE_INCOMPLETE,
                f"./{path}:1",
            )
        )
    findings.extend(contract_findings(bundle, records, path))
    return RolloutFidelity(bundle.rollout_id, bundle.family, tuple(findings))
