"""Shim-compatible projection and safe, non-authoritative cache loading."""

from __future__ import annotations

import json
from pathlib import Path

from tools import _phases, runs, tracker
from tools.attest.canonical import canonicalize, parse_json
from tools.progress_types import Decision, Evidence, ProgressError, Target, evidence
from tools.project_paths import resolve_project_path


def namespace(target: Target) -> Path:
    directory = runs.run_dir(target.root, target.instrument, target.run_id)
    relative = f"./{directory.relative_to(target.root).as_posix()}"
    resolve_project_path(relative + "/run.json", project_root=target.root)
    return runs.open_run(target.root, target.instrument, target.run_id, principal=target.principal)


def output(directory: Path, name: str) -> Path:
    return resolve_project_path(f"./{name}", project_root=directory)


def report_receipts(directory: Path) -> list[str]:
    base = output(directory, "gate-receipts")
    return sorted(path.name for path in base.glob("report-*.json"))


def load_cache(directory: Path) -> tuple[dict[str, Evidence], list[str], list[str]]:
    path = output(directory, "progress.yaml")
    if not path.exists():
        return {}, [], []
    try:
        text = path.read_text(encoding="utf-8")
        if "schema: trinity.progress/v1\n" not in text:
            raise ProgressError("PROGRESS_CACHE_MALFORMED", "cache schema differs")
        snapshots: dict[str, Evidence] = {}
        reports: list[str] = []
        for line in text.splitlines():
            if line.startswith("    snapshot: "):
                item = evidence(parse_json(line.removeprefix("    snapshot: ")))
                snapshots[item["fingerprint"]["phase"]] = item
            if line.startswith("    report_baseline: "):
                raw = parse_json(line.removeprefix("    report_baseline: "))
                if not isinstance(raw, list) or any(not isinstance(x, str) for x in raw):
                    raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid report baseline")
                reports = [str(x) for x in raw]
        if not snapshots:
            raise ProgressError("PROGRESS_CACHE_MALFORMED", "cache has no snapshots")
        return snapshots, reports, []
    except (OSError, UnicodeError, ValueError):
        return {}, [], ["PROGRESS_CACHE_MALFORMED"]


def gate_name(row: _phases.Phase) -> str:
    name = (
        row.id
        if row.kind == "barrier"
        else row.contract_heading.removeprefix("### ").split(": ", 1)[-1]
    )
    if any(c in name for c in ",[]\r\n"):
        raise ProgressError("PROGRESS_GATE_NAME_INVALID", "gate name cannot enter the flat shim")
    return name


def projection(
    target: Target,
    decision: Decision,
    checks: dict[str, str],
    baselines: dict[str, Evidence],
    reports: list[str],
) -> str:
    rows = _phases.phases(target.instrument, target.branch)
    standing = decision["phases"]
    work = [p for p in rows if p.kind not in ("gate", "barrier")]
    gates = [p for p in rows if p.kind in ("gate", "barrier")]
    named = [(p, gate_name(p)) for p in gates]
    names = [name for p, name in named if standing[p.id] != "complete"]
    phase = decision["resume_at"]
    label = phase or ("checks" if any("ran:fail" in v for v in checks.values()) else "complete")
    lines = [
        f"phase: {label}",
        f"phases_done: {sum(standing[p.id] == 'complete' for p in work)}",
        f"phases_total: {len(work)}",
        f"gates_done: {sum(standing[p.id] == 'complete' for p in gates)}",
        f"gates_total: {len(gates)}",
        f"open_gates: [{', '.join(sorted(set(names)))}]",
        f"gaps: {sum(s.startswith('unverifiable:') for s in standing.values())}",
        "schema: trinity.progress/v1",
        "authority: derived",
        f"resume_at: {phase or 'null'}",
        "phases:",
    ]
    for phase_id, status in standing.items():
        lines.extend(
            [
                f"  {json.dumps(phase_id)}:",
                f"    status: {status}",
                "    snapshot: " + canonicalize(baselines[phase_id]).decode().strip(),
                "    report_baseline: " + json.dumps(reports),
            ]
        )
    lines.append("checks:")
    lines.extend(f"  {json.dumps(k)}: {json.dumps(v)}" for k, v in sorted(checks.items()))
    lines.append("barriers:")
    lines.extend(f"  {json.dumps(k)}: {json.dumps(v)}" for k, v in decision["barriers"].items())
    return "\n".join(lines) + "\n"


def write_projection(directory: Path, body: str) -> None:
    tracker._atomic_write(output(directory, "progress.yaml"), body)
