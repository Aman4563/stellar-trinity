"""Public fidelity API and native coverage contracts.

Capture profile trinity.native-capture/v1 is an explicit instrumentation contract,
not a claim that stock harnesses emit these fields. A collector must capture the
records during execution, before editing/conversion. Custody and authenticity
still require the independent execution authority; this parser grants neither.
Missing capture records stay indeterminate, never inferred from counters.

analyze_trace() is the public classification entry point, including rollout identity
reconciliation. Raw FIDELITY_FAMILIES dispatch is internal and omits that reconciliation.

The adapters check retained inconsistencies in supplied evidence; they do not
prove resistance to coherent fabrication. Execution authenticity is owned by the
DEFERRED rows for observation-before-editing, effective request capture, and the
independent execution authority.

Family carriers and version-keyed vocabulary:
* C = claude_code_jsonl, 2.1.158/2.1.159: agent.jsonl OR agent/agent.jsonl,
  index, system/init -> result.
* E = openhands_events, 1.8 capture adapter: events.jsonl, id,
  SessionStart -> Terminal, plus run-metadata.json condenser_config.
* M = openhands_native_metrics, 1.8 capture adapter: same native event stream
  alongside run-metadata.json and metrics.json. Aggregates alone cannot prove it.
* Y = cybergym_usage, Claude versions above: usage.json plus C's raw log.
  Missing raw bytes retain the self-report ceiling. Version 1.8 here names the
  supported OpenHands capture-adapter vocabulary, not arbitrary upstream releases.

Each cell is a per-(family, signal) positive evidence contract:
| Signal | C | E | M | Y |
| COMPACTION | init -> result contiguous | start -> terminal + noop | E | C |
| OBSERVATION_TRUNCATION | config + every tool_result | same | same | C |
| TURN_CAP | authorized cap + observed count | same | events or metrics count | C or usage count |
| TIMEOUT | authorized timeout + observed duration | same | same | C |
| PROVIDER_ERROR | every request id + HTTP status | same | same | C |
| REFUSAL | terminal + every assistant stop reason | same | same | C |
| SETUP_FAILURE | successful init + bootstrap inventory | successful start + bootstrap | E | C |
| HANDOFF_FAILURE | submission identity = result identity | identity = terminal | E | C |

For all NEW negative conclusions the stream must have contiguous indices from
0 or 1, exactly one terminal at the end, the profile on its opening record, and
the same nonempty session_id on every record. Terminal bootstrap_ids/request_ids/
tool_result_ids must exactly match nonempty, unique native record inventories.
An empty list is NOT evidence that no operation happened.

Bootstrap records: type=bootstrap, bootstrap_id, status=success; opening status
also success. error/failed on either is SETUP_FAILURE. Requests: type=
provider_request, request_id, status_code in 200..299. Any non-2xx is a violation;
later successful retries never erase it (a conservative unrecovered-error rule).
Refusal: assistant and terminal stop_reason (or message.stop_reason), vocabulary
for EVERY version above: refusal/aup/policy_violation/content_filter are positive
markers; end_turn/stop/completed/max_turns/timeout are covered non-refusal reasons.
Unknown or missing stop reasons do not cover the class. No free-text keyword scan.

Observation: opening max_message_chars > 0 plus type=tool_result with unique
tool_result_id and explicit truncated=false for EVERY result. truncated=true
needs per-result max_message_chars equal to bound authorization; otherwise it is
a violation. Missing flags/config/inventory cannot establish coverage. Limits:
observed caps must equal Authorization and include their matching captured count <= cap;
turn limits require turns and iteration limits require iterations, never the other counter;
non-fired timeout additionally requires
terminal timed_out=false, timeout_seconds and elapsed_seconds <= approved bound.
Fired timeout requires elapsed_seconds >= the approved horizon minus the one-second
TIMEOUT_TOLERANCE_SECONDS capture-rounding tolerance. Missing durations stay unknown;
earlier firing is a budget-starvation violation. Faithfully fired limits stay conforming.

Handoff: submission.json {session_id, sha256} and terminal submission_sha256,
both lowercase 64-hex digests in the same session. Mismatch is a violation;
missing/malformed identities cannot prove coverage. These are captured identities,
not proof of independent custody or receipt by a separately operated scorer.

Compaction markers remain compact_boundary/isCompactSummary for C/Y and
Condensation/non-noop condenser for E/M. Positives need no coverage proof.
COVERAGE_CONTRACTS provides these 32 rows as immutable data for fixture builders.
ATIF alone remains conversion-capped; accompanied ATIF delegates to native bytes.
"""

from .bundle import (
    MAX_TRACE_BYTES,
    MAX_TRACE_LINES,
    Authorization,
    FamilyAdapter,
    TraceBundle,
    strongest_supported_outcome,
)
from .contracts import COVERAGE_CONTRACTS, CoverageContract
from .core import (
    TRIAL_CONFORMANCE_RULE,
    TRIAL_STATUSES,
    EvidencePointerError,
    FidelityOutcome,
    FidelityRefusal,
    RolloutFidelity,
    SignalClass,
    SignalFinding,
    demonstrates_coverage,
    map_trial_status,
)
from .family import run_fidelity_family
from .family_config import FidelityConfig
from .family_models import FidelityLedger, FidelityRoster, ScorerReceipt
from .ledger import (
    FidelityLedgerPathError,
    FidelityProjectionError,
    emit_fidelity_ledger,
    project_for_pilot,
)
from .registry import FIDELITY_FAMILIES, analyze_trace

__all__ = [
    "COVERAGE_CONTRACTS",
    "FIDELITY_FAMILIES",
    "MAX_TRACE_BYTES",
    "MAX_TRACE_LINES",
    "TRIAL_CONFORMANCE_RULE",
    "TRIAL_STATUSES",
    "Authorization",
    "CoverageContract",
    "EvidencePointerError",
    "FamilyAdapter",
    "FidelityConfig",
    "FidelityLedger",
    "FidelityLedgerPathError",
    "FidelityOutcome",
    "FidelityProjectionError",
    "FidelityRefusal",
    "FidelityRoster",
    "RolloutFidelity",
    "ScorerReceipt",
    "SignalClass",
    "SignalFinding",
    "TraceBundle",
    "analyze_trace",
    "demonstrates_coverage",
    "emit_fidelity_ledger",
    "map_trial_status",
    "project_for_pilot",
    "run_fidelity_family",
    "strongest_supported_outcome",
]
