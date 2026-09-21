"""Preflight boundary adapters and the closed, run-private receipt writer."""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from tools import _phases, feedback, integrity, pipeline, runs
from tools.attest.canonical import JSONValue, parse_json
from tools.feedback_chain import FeedbackError
from tools.progress_types import Target
from tools.project_paths import resolve_project_path

Entry: TypeAlias = Callable[[list[str]], int]


@dataclass(frozen=True, slots=True)
class ToolResult:
    status: int
    body: dict[str, JSONValue]


def invoke_json(entry: Entry, argv: list[str]) -> ToolResult:
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            status = entry(argv)
    except (OSError, ValueError):
        return ToolResult(3, {"code": "PREFLIGHT_TOOL_FAILED"})
    try:
        body = parse_json(output.getvalue())
    except ValueError:
        return ToolResult(3, {"code": "PREFLIGHT_TOOL_OUTPUT_INVALID"})
    if not isinstance(body, dict):
        return ToolResult(3, {"code": "PREFLIGHT_TOOL_OUTPUT_INVALID"})
    return ToolResult(status, body)


def placement(root: Path, *, check: bool) -> bool:
    """Check queued clean candidates; check mode refuses pending moves without renaming."""
    passed = True
    try:
        sealed = pipeline.sealed_records(root)
        for uuid, record in sorted(sealed.items()):
            verdict = pipeline.verdict_records(root, uuid).get(str(record["bundle_digest"]))
            if verdict is None or verdict.get("outcome") != "clean":
                continue
            if check and (root / "staging" / uuid).exists():
                passed = False
                continue
            pipeline.place(root, uuid)
    except (pipeline.PipelineError, OSError, ValueError):
        return False
    return passed


def feedback_summary(target: Target, result: ToolResult) -> dict[str, JSONValue]:
    checkpoint = "absent"
    seq: JSONValue = result.body.get("seq")
    head: JSONValue = result.body.get("entry_hash")
    directory = runs.run_dir(target.root, target.instrument, target.run_id)
    harness = runs.HARNESS[target.instrument].removeprefix(".")
    log = resolve_project_path(
        "./" + integrity.FEEDBACK_CHECKPOINTS[harness], project_root=directory
    )
    if log.is_file():
        checkpoint = "signed" if result.status == 0 else "unsigned"
    if result.status != 0:
        try:
            walked = feedback._head(feedback.Target(target.root, target.instrument, target.run_id))
            seq, head = walked.seq, walked.entry_hash
        except (FeedbackError, OSError, ValueError):
            seq, head = None, None
    return {
        "chain_walk": "ran:pass" if result.status == 0 else "ran:fail",
        "head_seq": seq,
        "head_entry_hash": head,
        "checkpoint": checkpoint,
        "pending_records": 0 if checkpoint == "signed" else seq,
    }


def preconditions(target: Target, summary: dict[str, JSONValue]) -> dict[str, str]:
    approval = _phases.phase(target.instrument, "0.5").approval_file
    paths = {
        "requirements": "./requirements",
        "touchstones": "./touchstones",
        "forge_view": "./.memory/forge_view.yaml",
        "crucible_view": "./.memory/crucible_view.yaml",
        "approval": approval or "./" + runs.HARNESS[target.instrument] + "/approval",
        "harness": "./harness",
        "samples": "./samples",
        "delivery": "./delivery",
    }
    found: dict[str, str] = {}
    for name, relative in paths.items():
        path = resolve_project_path(relative, project_root=target.root)
        present = (
            path.is_file() if name in {"forge_view", "crucible_view", "approval"} else path.is_dir()
        )
        found[name] = "present" if present else "absent"
    found["signed_checkpoint"] = "present" if summary["checkpoint"] == "signed" else "absent"
    return found


def write_receipt(directory: Path, receipt: dict[str, JSONValue]) -> None:
    base = resolve_project_path("./gate-receipts", project_root=directory)
    base.mkdir(exist_ok=True)
    number = 1
    while True:
        path = resolve_project_path(f"./preflight-{number:04d}.json", project_root=base)
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            return
        except FileExistsError:
            number += 1
