"""Typed, derived phase snapshots; no value here grants execution authority."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from tools.attest.canonical import JSONValue, canonical_sha256


class ProgressError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Target:
    root: Path
    instrument: str
    run_id: str
    principal: str
    branch: str = "default"
    at: str | None = None


class Entry(TypedDict):
    path: str
    mode: str
    sha256: str | None
    state: str


class Fingerprint(TypedDict):
    schema: str
    phase: str
    inputs: list[Entry]
    approval_digest: str | None
    contract_sha256: str | None
    trinity_gitlink: str | None


class Evidence(TypedDict):
    fingerprint: Fingerprint
    inputs_fp: str
    reads: list[Entry]
    reconciles: list[Entry]
    artifacts: list[Entry]
    approval_digest: str | None
    bound_digest: str | None
    codes: list[str]
    problem: str | None
    opened_contract: str | None
    opened_gitlink: str | None


class Decision(TypedDict):
    resume_at: str | None
    phases: dict[str, str]
    barriers: dict[str, str]
    fingerprints: dict[str, Evidence]


class Envelope(TypedDict):
    decision: Decision
    telemetry: dict[str, str | bool | list[str]]


def entries(value: JSONValue) -> list[Entry]:
    if not isinstance(value, list):
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "manifest must be a list")
    result: list[Entry] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"path", "mode", "sha256", "state"}:
            raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid manifest entry")
        path, mode, digest, state = (item[k] for k in ("path", "mode", "sha256", "state"))
        if not isinstance(path, str) or not path.startswith("./"):
            raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid manifest path")
        if not isinstance(mode, str) or state not in ("present", "missing", "unreadable"):
            raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid manifest metadata")
        if digest is not None and not isinstance(digest, str):
            raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid manifest digest")
        result.append(Entry(path=path, mode=mode, sha256=digest, state=str(state)))
    return result


def fingerprint(value: JSONValue) -> Fingerprint:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "phase",
        "inputs",
        "approval_digest",
        "contract_sha256",
        "trinity_gitlink",
    }:
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid fingerprint fields")
    if value["schema"] != "trinity.phase-fingerprint/v1" or not isinstance(value["phase"], str):
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid fingerprint schema")
    approval, contract, gitlink = (
        value[k] for k in ("approval_digest", "contract_sha256", "trinity_gitlink")
    )
    if any(v is not None and not isinstance(v, str) for v in (approval, contract, gitlink)):
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid fingerprint digests")
    return Fingerprint(
        schema="trinity.phase-fingerprint/v1",
        phase=value["phase"],
        inputs=entries(value["inputs"]),
        approval_digest=None if approval is None else str(approval),
        contract_sha256=None if contract is None else str(contract),
        trinity_gitlink=None if gitlink is None else str(gitlink),
    )


def evidence(value: JSONValue) -> Evidence:
    if not isinstance(value, dict):
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid phase snapshot")
    fp = fingerprint(value.get("fingerprint"))
    if value.get("inputs_fp") != canonical_sha256(fp):
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "fingerprint checksum differs")
    bound, problem, codes = value.get("bound_digest"), value.get("problem"), value.get("codes")
    if (bound is not None and not isinstance(bound, str)) or (
        problem is not None and not isinstance(problem, str)
    ):
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid snapshot metadata")
    if not isinstance(codes, list) or any(not isinstance(code, str) for code in codes):
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid snapshot codes")
    return Evidence(
        fingerprint=fp,
        inputs_fp=canonical_sha256(fp),
        reads=entries(value.get("reads")),
        reconciles=entries(value.get("reconciles")),
        artifacts=entries(value.get("artifacts")),
        approval_digest=fp["approval_digest"],
        bound_digest=bound,
        codes=[str(code) for code in codes],
        problem=problem,
        opened_contract=fp["contract_sha256"]
        if value.get("opened_contract") is None
        else str(value["opened_contract"]),
        opened_gitlink=fp["trinity_gitlink"]
        if value.get("opened_gitlink") is None
        else str(value["opened_gitlink"]),
    )
