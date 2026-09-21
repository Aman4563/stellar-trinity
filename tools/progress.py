"""Reconstruct derived run progress; invoke by path with rebuild, close, or explain.

Without --check-result, checks is empty and resume_at is computed, not certified.
Rebuild starts an invocation baseline. Close must precede its report-moment gate
per ADR 0005; a later paused invocation must rebuild before doing phase work.
No phase work, freshness check, human approval, or gate disposition is minted here.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING or __package__ is not None or __name__ == "__main__":
    from tools import _phases, runs, tracker
    from tools.attest.canonical import canonicalize
    from tools.progress_inputs import snapshot
    from tools.progress_render import (
        load_cache,
        namespace,
        output,
        projection,
        report_receipts,
        write_projection,
    )
    from tools.progress_state import evaluate, predicate
    from tools.progress_types import Envelope, ProgressError, Target
    from tools.project_paths import ProjectPathError, invocation_root, resolve_project_path

if TYPE_CHECKING:
    from collections.abc import Sequence


def rebuild(
    root: Path,
    instrument: str,
    run_id: str,
    *,
    principal: str,
    branch: str = "default",
    at: str | None = None,
    checks: dict[str, str] | None = None,
) -> Envelope:
    target = Target(root, instrument, run_id, principal, branch, at)
    if not _phases.phases(instrument, branch):
        raise ProgressError("PROGRESS_PHASE_UNKNOWN", "instrument has no such branch")
    current_checks = {} if checks is None else checks
    for name, value in current_checks.items():
        if (
            re.fullmatch(r"[A-Za-z0-9_.-]+", name) is None
            or re.fullmatch(r"ran:(?:pass|fail(?::[A-Z0-9_]+(?:,[A-Z0-9_]+)*)?)", value) is None
        ):
            raise ProgressError("PROGRESS_CACHE_MALFORMED", "invalid check outcome")
    directory = namespace(target)
    decision, baselines, codes = evaluate(target, directory, current_checks)
    for phase_id, baseline in baselines.items():
        baseline["reads"] = decision["fingerprints"][phase_id]["reads"]
        baseline["opened_contract"] = decision["fingerprints"][phase_id]["opened_contract"]
        baseline["opened_gitlink"] = decision["fingerprints"][phase_id]["opened_gitlink"]
    write_projection(
        directory,
        projection(target, decision, current_checks, baselines, report_receipts(directory)),
    )
    return Envelope(
        decision=decision,
        telemetry={
            "run_id": run_id,
            "codes": codes,
            "stopped": any(v.startswith("ran:fail") for v in current_checks.values()),
        },
    )


def close(
    root: Path,
    instrument: str,
    run_id: str,
    *,
    principal: str,
    phase_id: str,
    branch: str = "default",
    at: str | None = None,
) -> Envelope:
    target = Target(root, instrument, run_id, principal, branch, at)
    row = _phases.phase(instrument, phase_id)
    if branch not in row.branches:
        raise ProgressError("PROGRESS_PHASE_UNKNOWN", "phase is not on the invoked branch")
    directory = namespace(target)
    cached, reports, codes = load_cache(directory)
    if phase_id not in cached or codes:
        raise ProgressError("PROGRESS_CACHE_MALFORMED", "rebuild before opening phase work")
    if report_receipts(directory) != reports:
        raise ProgressError("PROGRESS_INPUTS_MOVED_DURING_RUN", "ADR 0005: report gate already ran")
    before = cached[phase_id]
    after = snapshot(target, row)
    if (
        before["reads"] != after["reads"]
        or before["opened_contract"] != after["opened_contract"]
        or before["opened_gitlink"] != after["opened_gitlink"]
    ):
        raise ProgressError("PROGRESS_INPUTS_MOVED_DURING_RUN", "phase read inputs moved")
    status = predicate(target, row, after)
    if status != "complete":
        raise ProgressError("PROGRESS_RECEIPT_MISMATCH", status)
    path = output(directory, f"phases/{phase_id}.json")
    body = dict(after["fingerprint"])
    body.update(
        schema="trinity.phase-receipt/v1",
        instrument=instrument,
        branch=branch,
        artifacts=after["artifacts"],
        inputs_fp=after["inputs_fp"],
        inputs={
            "manifest": after["fingerprint"]["inputs"],
            "reads": after["reads"],
            "reconciles_before": before["reconciles"],
            "reconciles_after": after["reconciles"],
        },
        closed_at=at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    tracker._atomic_write(path, canonicalize(body).decode())
    cached[phase_id] = after
    invalidated = {phase_id}
    for candidate in _phases.TABLE[instrument]:
        if invalidated.intersection(candidate.depends_on):
            invalidated.add(candidate.id)
            cached[candidate.id]["codes"] = ["PROGRESS_DEPENDENCY_RERAN"]
    decision, _, _ = evaluate(target, directory, {}, opened=cached)
    write_projection(directory, projection(target, decision, {}, cached, reports))
    return Envelope(
        decision=decision, telemetry={"run_id": run_id, "closed_at": str(body["closed_at"])}
    )


def explain(
    root: Path,
    instrument: str,
    run_id: str,
    *,
    principal: str,
    phase_id: str,
    branch: str = "default",
    at: str | None = None,
) -> dict[str, list[str]]:
    target = Target(root, instrument, run_id, principal, branch, at)
    row = _phases.phase(instrument, phase_id)
    cached, _, _ = load_cache(namespace(target))
    after = snapshot(target, row)["fingerprint"]["inputs"]
    prior = cached.get(phase_id)
    before = [] if prior is None else prior["fingerprint"]["inputs"]
    old = {x["path"]: x for x in before if x["state"] != "missing"}
    new = {x["path"]: x for x in after if x["state"] != "missing"}
    return {
        "added": sorted(new.keys() - old.keys()),
        "removed": sorted(old.keys() - new.keys()),
        "changed": sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verb", choices=("rebuild", "close", "explain"))
    parser.add_argument("root")
    parser.add_argument("--instrument", required=True, choices=tuple(runs.HARNESS))
    parser.add_argument("--run", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--branch", default="default", choices=_phases.BRANCHES)
    parser.add_argument("--phase")
    parser.add_argument("--at")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-result", action="append", default=[])
    try:
        args = parser.parse_args(list(argv)[1:] if argv is not None else None)
    except SystemExit as error:
        return 0 if error.code == 0 else 1
    try:
        root = resolve_project_path(args.root, project_root=invocation_root(), must_exist=True)
        if args.at is not None:
            if not args.at.endswith("Z"):
                return 1
            datetime.fromisoformat(args.at)
        if args.verb != "rebuild" and args.phase is None:
            return 1
        match args.verb:
            case "rebuild":
                checks: dict[str, str] = {}
                for item in args.check_result:
                    name, separator, outcome = item.partition("=")
                    if not separator or name in checks:
                        return 1
                    checks[name] = outcome
                result = rebuild(
                    root,
                    args.instrument,
                    args.run,
                    principal=args.principal,
                    branch=args.branch,
                    at=args.at,
                    checks=checks,
                )
            case "close":
                result = close(
                    root,
                    args.instrument,
                    args.run,
                    principal=args.principal,
                    phase_id=args.phase,
                    branch=args.branch,
                    at=args.at,
                )
            case "explain":
                changes = explain(
                    root,
                    args.instrument,
                    args.run,
                    principal=args.principal,
                    phase_id=args.phase,
                    branch=args.branch,
                    at=args.at,
                )
                print(canonicalize(changes).decode(), end="")
                return 0
            case _:
                return 1
        print(canonicalize(result).decode(), end="")
        decision = result["decision"]
        held = result["telemetry"].get("stopped") or result["telemetry"].get("codes")
        held = held or any(p.startswith("unverifiable:") for p in decision["phases"].values())
        held = held or any(item["codes"] for item in decision["fingerprints"].values())
        return 2 if held else 0
    except (ProgressError, _phases.PhaseError) as error:
        print(canonicalize({"code": error.code, "detail": str(error)}).decode(), end="")
        return 2
    except (runs.RunError, ProjectPathError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 3
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
