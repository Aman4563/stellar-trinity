"""Run deterministic preflight without changing the frozen gate CLI.

Invoke: python3 tools/preflight.py ./ --instrument X --run ID --principal P
--moment preflight|report [--check] [--at RFC3339Z] [--json].

Side effects, relative to the parent project:
Both modes may create <harness>/runs/<run>/run.json and append
.sentinel/streams/<run>/{attempts.jsonl,head.json,ledger.lock} through the gate.
Freshness may fetch Git metadata.
Check mode writes nothing else: progress uses rebuild's read-only evaluator;
FORGE checks pending placement (no rename) then reconciles with check=True.
Default additionally writes <harness>/runs/<run>/progress.yaml and
<harness>/runs/<run>/gate-receipts/{preflight,report}-*.json; the report gate
writes <harness>/runs/<run>/disposition.json. Preflight gate installation owns
.githooks/*, .gitattributes, .github/CODEOWNERS, .github/workflows/sentinel.yaml,
.opencode/commands/*, .agents/skills/*, .git/config and
.trinity-install/protection/*.json (plus remote branch-protection settings);
migration owns its existing closed roster and .trinity/migrations/*.
FORGE placement/reconciliation may move staging/<uuid> to samples/ or delivery/,
rebalance those roots, and render their README.md and root reports/TRACKING.md.
No mode stages, commits, amends, pushes, appends feedback, or writes phase receipts.
ADR 0005 decision 3 requires continuation feedback before this invocation.
The gate's ceiling is retained unchanged, never minted by this wrapper.
--at governs progress only: the frozen gate and feedback walk use their own clocks.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from time import perf_counter_ns
from typing import TYPE_CHECKING


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    # integrity's frozen import path expects this legacy alias even for package callers.
    sys.modules.setdefault("_findings", importlib.import_module("tools._findings"))


_bootstrap_direct_execution(__name__, __package__)

if TYPE_CHECKING or __package__ is not None or __name__ == "__main__":
    from tools import _phases, feedback, gate, integrity, migrate, pipeline, progress
    from tools.attest.canonical import JSONValue, parse_json
    from tools.preflight_receipt import (
        feedback_summary,
        invoke_json,
        placement,
        preconditions,
        write_receipt,
    )
    from tools.progress_render import namespace
    from tools.progress_state import evaluate
    from tools.progress_types import Target
    from tools.project_paths import invocation_root, redact_project_root, resolve_project_path


def execute(target: Target, *, moment: str, check: bool) -> tuple[int, dict[str, JSONValue]]:
    start = perf_counter_ns()
    directory = namespace(target)
    resolve_project_path("./gate-receipts", project_root=directory)
    relative = "./" + target.root.relative_to(invocation_root()).as_posix()
    common = [relative, "--instrument", target.instrument, "--run", target.run_id]
    migration = migrate.compatibility_check(target.root, apply=not check)
    walked = invoke_json(feedback.main, ["feedback.py", "walk", *common, "--json"])
    checks = {
        "migrate": "ran:fail"
        if migration.status in {"hold", "planned"} or migration.needs_revalidation
        else "ran:pass",
        "feedback_walk": "ran:pass" if walked.status == 0 else "ran:fail",
    }
    if "place_reconcile" in _phases.never_skip(target.instrument):
        checks["pipeline_place"] = "ran:pass" if placement(target.root, check=check) else "ran:fail"
        try:
            reconciled = pipeline.reconcile(target.root, check=check)
            checks["pipeline_reconcile"] = "ran:fail" if reconciled.findings else "ran:pass"
        except (pipeline.PipelineError, OSError, ValueError):
            checks["pipeline_reconcile"] = "ran:fail"
    gate_args = ["gate.py", *common, "--moment", moment, "--json"]
    if check:
        gate_args.append("--check")
    gated = invoke_json(gate.main, gate_args)
    codes = gated.body.get("codes", [])
    freshness_failed = gated.status not in {0, 2, 3} or "ceiling" not in gated.body
    if isinstance(codes, list):
        freshness_failed |= any(str(code).startswith("TRINITY_FRESHNESS_") for code in codes)
    checks["freshness"] = "ran:fail" if freshness_failed else "ran:pass"
    checks["gate"] = "ran:pass" if gated.status == 0 else "ran:fail"
    # The gate executes the complete qualification registry, including Phase 2 instruments.
    checks["phase_2_instruments"] = checks["gate"]
    try:
        digests = integrity.check_work_differential_digests(str(target.root))
        checks["differential_digests"] = "ran:fail" if gate.error_codes(digests) else "ran:pass"
    except (OSError, ValueError):
        checks["differential_digests"] = "ran:fail"
    checks["progress_rebuild"] = "ran:pass"
    decision, _, progress_codes = evaluate(target, directory, checks)
    failed = (
        bool(progress_codes)
        or any(value.startswith("unverifiable:") for value in decision["phases"].values())
        or any(item["codes"] for item in decision["fingerprints"].values())
    )
    checks["progress_rebuild"] = "ran:fail" if failed else "ran:pass"
    if check:
        decision, _, _ = evaluate(target, directory, checks)
    else:
        progress_args = [
            "progress.py",
            "rebuild",
            *common,
            "--principal",
            target.principal,
            "--json",
        ]
        if target.at is not None:
            progress_args += ["--at", target.at]
        for name, outcome in checks.items():
            progress_args += ["--check-result", f"{name}={outcome}"]
        rebuilt = invoke_json(progress.main, progress_args)
        if "decision" not in rebuilt.body:
            checks["progress_rebuild"] = "ran:fail"
            decision["resume_at"] = None
    summary = feedback_summary(target, walked)
    present = preconditions(target, summary)
    for name, value in present.items():
        if value == "absent":
            print(f"PRECONDITION_ABSENT:{name}", file=sys.stderr)
    receipt: dict[str, JSONValue] = {
        "schema": "trinity.preflight/v1",
        "instrument": target.instrument,
        "run_id": target.run_id,
        "freshness": checks["freshness"],
        "migration": parse_json(json.dumps(migration.to_json())),
        "gate": gated.body,
        "feedback": summary,
        "preconditions": dict(present),
        "progress": parse_json(json.dumps(decision)) if check else rebuilt.body.get("decision", {}),
        "never_skip": dict(checks),
        "meter": {"preflight_ms": (perf_counter_ns() - start) // 1_000_000},
    }
    if not check:
        write_receipt(directory, receipt)
    status = 2 if "ran:fail" in checks.values() or "absent" in present.values() else 0
    return (3 if gated.status not in {0, 2} else status), receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--instrument", required=True, choices=("ENGRAM", "FORGE", "CRUCIBLE"))
    parser.add_argument("--run", required=True)
    parser.add_argument("--principal", required=True)
    parser.add_argument("--moment", required=True, choices=("preflight", "report"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--at")
    parser.add_argument("--json", action="store_true")
    try:
        args = parser.parse_args(argv[1:] if argv is not None else None)
    except SystemExit as error:
        return 0 if error.code == 0 else 1
    root = invocation_root()
    actor = os.environ.get("GITHUB_ACTOR")
    try:
        parent = resolve_project_path(args.root, project_root=root, must_exist=True)
        if not parent.is_dir() or not args.principal.strip():
            return 1
        if args.at is not None:
            try:
                integrity.parse_evaluation_time(args.at)
            except ValueError:
                return 1
            if not args.at.endswith("Z"):
                return 1
        target = Target(parent, args.instrument, args.run, args.principal, at=args.at)
        os.environ["GITHUB_ACTOR"] = args.principal
        status, receipt = execute(target, moment=args.moment, check=args.check)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return status
    except (OSError, ValueError) as error:
        print(redact_project_root(str(error), project_root=root), file=sys.stderr)
        return 3
    finally:
        if actor is None:
            os.environ.pop("GITHUB_ACTOR", None)
        else:
            os.environ["GITHUB_ACTOR"] = actor


if __name__ == "__main__":
    raise SystemExit(main())
