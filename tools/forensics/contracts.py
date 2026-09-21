"""Machine-readable capture obligations, not assertions about stock harness output."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from .core import SignalClass as S

CAPTURE_PROFILE: Final = "trinity.native-capture/v1"
REFUSAL_MARKERS: Final = ("refusal", "aup", "policy_violation", "content_filter")
CLEAN_STOPS: Final = ("end_turn", "stop", "completed", "max_turns", "timeout")
CAPTURE_VERSIONS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "claude_code_jsonl": ("2.1.158", "2.1.159"),
        "cybergym_usage": ("2.1.158", "2.1.159"),
        "openhands_events": ("1.8",),
        "openhands_native_metrics": ("1.8",),
    }
)


@dataclass(frozen=True, slots=True)
class CoverageContract:
    """A row supplies fixture builders with carriers, vocabulary and obligations."""

    versions: tuple[str, ...]
    native_paths: tuple[str, ...]
    required_records: tuple[str, ...]
    positive_evidence: str
    violation_markers: tuple[str, ...]
    profile: str = CAPTURE_PROFILE


_ROWS: Final = {
    S.COMPACTION: (
        ("start", "terminal"),
        "Contiguous start-to-terminal native stream; "
        "OpenHands also needs condenser_config.type=noop.",
        ("compact_boundary", "isCompactSummary", "Condensation", "non-noop condenser"),
    ),
    S.OBSERVATION_TRUNCATION: (
        ("start.max_message_chars", "tool_result", "terminal.tool_result_ids"),
        "Declared positive limit; nonempty exact tool-result inventory; each truncated=false, "
        "or truncated=true with a per-result limit equal to bound authorization.",
        ("truncated=true with unapproved max_message_chars",),
    ),
    S.TURN_CAP: (
        ("terminal.max_turns", "terminal.turns"),
        "Observed max_turns/maxTurns/max_iterations equals authorization; "
        "captured turns must be present and must not exceed it.",
        ("unapproved cap", "turns beyond cap"),
    ),
    S.TIMEOUT: (
        ("terminal.timed_out", "terminal.timeout_seconds", "terminal.elapsed_seconds"),
        "Fired timeout equals authorization and captured elapsed_seconds reaches the approved "
        "horizon within TIMEOUT_TOLERANCE_SECONDS (1 second), "
        "or completed capture has timed_out=false and "
        "elapsed_seconds <= authorized timeout_seconds.",
        (
            "unapproved timeout",
            "early fired timeout beyond tolerance",
            "elapsed_seconds beyond timeout",
        ),
    ),
    S.PROVIDER_ERROR: (
        ("provider_request", "terminal.request_ids"),
        "Nonempty exact request-id inventory; every captured request has an HTTP 2xx status. "
        "Retries remain conservative: any captured non-2xx is a violation, not erased by success.",
        ("non-2xx status_code",),
    ),
    S.REFUSAL: (
        ("assistant.stop_reason", "terminal.stop_reason", "terminal.request_ids"),
        "Nonempty assistant/request inventory; every assistant and terminal stop_reason is "
        "end_turn/stop/completed/max_turns/timeout; scan top-level and message.stop_reason.",
        REFUSAL_MARKERS,
    ),
    S.SETUP_FAILURE: (
        ("start.status", "bootstrap", "terminal.bootstrap_ids"),
        "Opening init/SessionStart status=success; nonempty exact bootstrap-id inventory "
        "with every status=success.",
        ("status=error", "status=failed"),
    ),
    S.HANDOFF_FAILURE: (
        ("submission.json", "terminal.submission_sha256"),
        "submission.json {session_id,sha256} and terminal have the same session and lowercase "
        "64-hex SHA-256 identity; both digests agree.",
        ("submission digest mismatch", "submission session mismatch"),
    ),
}

COVERAGE_CONTRACTS: Final[Mapping[str, Mapping[S, CoverageContract]]] = MappingProxyType(
    {
        family: MappingProxyType(
            {
                signal: CoverageContract(
                    versions,
                    ("agent.jsonl", "agent/agent.jsonl")
                    if family in {"claude_code_jsonl", "cybergym_usage"}
                    else ("events.jsonl",),
                    records,
                    evidence,
                    markers,
                )
                for signal, (records, evidence, markers) in _ROWS.items()
            }
        )
        for family, versions in CAPTURE_VERSIONS.items()
    }
)
