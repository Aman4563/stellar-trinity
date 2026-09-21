from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from .bundle import RAW_AGENT_PATHS, FamilyAdapter, TraceBundle
from .claude_code_jsonl import claude_code_jsonl
from .cybergym_usage import cybergym_usage
from .openhands_events import openhands_events
from .openhands_native_metrics import openhands_native_metrics

NATIVE_ADAPTERS: Final[Mapping[str, FamilyAdapter]] = MappingProxyType(
    {
        "claude_code_jsonl": claude_code_jsonl,
        "openhands_events": openhands_events,
        "cybergym_usage": cybergym_usage,
        "openhands_native_metrics": openhands_native_metrics,
    }
)


def available_sources(bundle: TraceBundle) -> frozenset[str]:
    sources: set[str] = set()
    if any(path in bundle.files for path in RAW_AGENT_PATHS):
        sources.add("claude_code_jsonl")
        if "usage.json" in bundle.files:
            sources.add("cybergym_usage")
    if "events.jsonl" in bundle.files:
        sources.add("openhands_events")
    if {"run-metadata.json", "metrics.json"} <= bundle.files.keys():
        sources.add("openhands_native_metrics")
    return frozenset(sources)
