"""Disk-derived completion, independent of receipt claims and invocation telemetry."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tools import _phases, integrity
from tools.attest.canonical import canonical_sha256, parse_json
from tools.progress_inputs import snapshot
from tools.progress_render import load_cache, output
from tools.progress_types import Decision, Evidence, Target, entries, fingerprint


def receipt(directory: Path, row: _phases.Phase, current: Evidence) -> Evidence | None:
    path = output(directory, f"phases/{row.id}.json")
    if not path.exists():
        return None
    try:
        raw = parse_json(path.read_bytes())
        if not isinstance(raw, dict) or raw.get("schema") != "trinity.phase-receipt/v1":
            raise ValueError
        if raw.get("instrument") != row.instrument or raw.get("phase") != row.id:
            raise ValueError
        recorded_inputs = raw.get("inputs")
        if not isinstance(recorded_inputs, dict):
            raise ValueError
        fp = fingerprint(
            {
                k: raw.get(k)
                for k in ("phase", "approval_digest", "contract_sha256", "trinity_gitlink")
            }
            | {"schema": "trinity.phase-fingerprint/v1", "inputs": recorded_inputs.get("manifest")}
        )
        if raw.get("inputs_fp") != canonical_sha256(fp):
            raise ValueError
        artifacts = entries(raw.get("artifacts"))
        if artifacts != current["artifacts"] or fp != current["fingerprint"]:
            current["codes"].append("PROGRESS_RECEIPT_MISMATCH")
        return Evidence(
            fingerprint=fp,
            inputs_fp=canonical_sha256(fp),
            reads=[],
            reconciles=[],
            artifacts=artifacts,
            approval_digest=fp["approval_digest"],
            bound_digest=None,
            codes=[],
            problem=None,
            opened_contract=fp["contract_sha256"],
            opened_gitlink=fp["trinity_gitlink"],
        )
    except (OSError, UnicodeError, ValueError):
        current["codes"].append("PROGRESS_RECEIPT_MISMATCH")
        return None


def predicate(target: Target, row: _phases.Phase, item: Evidence) -> str:
    if item["problem"]:
        return f"unverifiable:{item['problem']}"
    signed = [p for p in row.artifacts + row.reads if "attestation" in p or ".dsse" in p]
    if signed:
        if target.at is None:
            item["codes"].append("ATTESTATION_EVALUATION_TIME_MISSING")
            return "unverifiable:evaluation_time_missing"
        if not all(p.startswith("./.audit/attestations/execution/") for p in signed):
            return "unverifiable:signed_evidence_verifier_unavailable"
        findings = integrity.check_execution_attestations(
            str(target.root), evaluation_time=datetime.fromisoformat(target.at)
        )
        if findings:
            item["codes"].extend(finding.code for finding in findings)
            return "unverifiable:signed_evidence_refused"
    if row.kind == "barrier":
        return "incomplete:human_barrier"
    if any(a["state"] == "unreadable" for a in item["artifacts"]):
        return "unverifiable:artifact_unreadable"
    if any(a["state"] != "present" for a in item["artifacts"]):
        return "incomplete:artifact_missing"
    if row.kind == "gate":
        if item["approval_digest"] is None:
            return "incomplete:approval_missing"
        if item["bound_digest"] is None or item["approval_digest"] != item["bound_digest"]:
            return "incomplete:approval_stale"
    if not row.artifacts and row.kind != "gate":
        return "not_started"
    return "complete"


def evaluate(
    target: Target,
    directory: Path,
    checks: dict[str, str],
    *,
    opened: dict[str, Evidence] | None = None,
) -> tuple[Decision, dict[str, Evidence], list[str]]:
    cached, _, codes = load_cache(directory)
    if opened is not None:
        cached = opened
    rows = _phases.TABLE[target.instrument]
    current = {row.id: snapshot(target, row) for row in rows}
    standings: dict[str, str] = {}
    moved: set[str] = set()
    baselines: dict[str, Evidence] = {}
    for row in rows:
        item = current[row.id]
        prior = receipt(directory, row, item) or cached.get(row.id)
        baselines[row.id] = cached.get(row.id, item)
        status = predicate(target, row, item)
        if "PROGRESS_DEPENDENCY_RERAN" in baselines[row.id]["codes"]:
            moved.add(row.id)
            status = "incomplete:dependency_moved"
        if prior and item["problem"] is None:
            before, after = prior["fingerprint"], item["fingerprint"]
            coarse = any(before[k] != after[k] for k in ("contract_sha256", "trinity_gitlink"))
            changed = before["inputs"] != after["inputs"]
            if coarse or (changed and status != "incomplete:approval_stale"):
                moved.add(row.id)
                lost_artifact = (
                    status == "incomplete:artifact_missing"
                    and prior["artifacts"] != item["artifacts"]
                )
                if coarse or not lost_artifact:
                    status = "incomplete:inputs_moved"
        standings[row.id] = status
    pending = set(moved)
    while pending:
        dependency = pending.pop()
        for row in rows:
            if dependency in row.depends_on and row.id not in moved:
                moved.add(row.id)
                pending.add(row.id)
                if standings[row.id] != "incomplete:approval_stale":
                    standings[row.id] = "incomplete:dependency_moved"
    invoked = _phases.phases(target.instrument, target.branch)
    resume = next((row.id for row in invoked if standings[row.id] != "complete"), None)
    if any(value.startswith("ran:fail") for value in checks.values()):
        resume = None
    barriers = {
        row.id: standings[row.id]
        for row in rows
        if row.kind in ("gate", "barrier") and standings[row.id] != "complete"
    }
    decision = Decision(resume_at=resume, phases=standings, barriers=barriers, fingerprints=current)
    return decision, baselines, codes
