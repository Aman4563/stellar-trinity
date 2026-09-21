"""Which state transitions an admission boundary may accept, decided against a pinned base.

Trinity's runners sync through git, and git carries no authenticated principal, no trustworthy
clock, and no arbiter. This module supplies the part of that gap deterministic code can close:
given the last accepted commit and one candidate, it decides whether the candidate is a lawful
successor. It decides nothing about which candidate arrives first. That serialization belongs to
whatever process holds exclusive write on the accepted ref, and this validator is what that
process runs before it advances one.

The baseline, the trust pin, the enrolment set, and the authenticated operator all arrive in a
``TrustedContext`` the caller supplies. None of them is read out of the candidate, because a
candidate that names its own baseline or its own trust policy has authorized itself. Ownership
is likewise decided by the accepted sequence rather than by any instant a record reports about
itself: a claim wins because it was accepted first, never because it says it was earlier.

Every refusal carries a ``TRANSITION_`` code from the closed vocabulary in ``TRANSITION_CODES``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final


def _bootstrap_direct_execution(module_name: str, package: str | None) -> None:
    if module_name == "__main__" and package is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


_bootstrap_direct_execution(__name__, __package__)

from tools._findings import Finding, Severity, render_finding, serialize_findings  # noqa: E402
from tools.accepted_state import (  # noqa: E402
    AcceptedState,
    Protected,
    classify,
    json_object,
    parents,
    read_blob,
    read_state,
    resolve,
    run_namespace,
    text_field,
)
from tools.attest.backend_ssh import SshKeygenBackend  # noqa: E402
from tools.operations import SigningPolicy  # noqa: E402
from tools.transition_records import (  # noqa: E402
    backdated_findings,
    claim_findings,
    epoch_findings,
    verdict_findings,
)
from tools.transition_signing import (  # noqa: E402
    authorized_digests,
    trust_findings,
    unsigned_record_findings,
)

TRANSITION_CODES: Final = (
    "TRANSITION_UNENROLLED_OPERATOR",
    "TRANSITION_BASE_MISMATCH",
    "TRANSITION_STREAM_REWRITTEN",
    "TRANSITION_RECORD_MUTATED",
    "TRANSITION_RECORD_DELETED",
    "TRANSITION_FOREIGN_RUN",
    "TRANSITION_CLAIM_CONTESTED",
    "TRANSITION_VERDICT_UNOWNED",
    "TRANSITION_EPOCH_FORK",
    "TRANSITION_EPOCH_ROLLBACK",
    "TRANSITION_BACKDATED",
    "TRANSITION_TRUST_DRIFT",
    "TRANSITION_UNSIGNED_OPERATION",
)
RUN_MARKER: Final = "run.json"


class TransitionContextError(ValueError):
    """The caller supplied a context that cannot decide anything."""


@dataclass(frozen=True, slots=True)
class TrustedContext:
    """What the admission boundary knows independently of the candidate it is judging."""

    project: str
    operator: str
    base_commit: str
    trust_policy_digest: str
    enrolled_principals: frozenset[str]
    signing: SigningPolicy | None = None

    def __post_init__(self) -> None:
        for name in ("project", "operator", "base_commit", "trust_policy_digest"):
            if not str(getattr(self, name)).strip():
                raise TransitionContextError(f"a trusted context needs a {name}")
        if not self.enrolled_principals:
            raise TransitionContextError("a trusted context needs at least one enrolled principal")


def _finding(code: str, path: str, message: str) -> Finding:
    return Finding(code, Severity.ERROR, path, None, message)


def _appends_only(path: str) -> bool:
    return path.endswith(".jsonl")


def _run_workspace(path: str) -> bool:
    return classify(path) is Protected.RUN and path.rsplit("/", 1)[-1] != RUN_MARKER


def _base_findings(
    root: Path, candidate: str, context: TrustedContext
) -> tuple[str | None, str | None, list[Finding]]:
    head = resolve(root, candidate)
    base = resolve(root, context.base_commit)
    if base is None:
        message = f"the accepted base {context.base_commit!r} does not resolve to a commit"
        return None, None, [_finding("TRANSITION_BASE_MISMATCH", str(root), message)]
    if head is None:
        message = f"the candidate {candidate!r} does not resolve to a commit"
        return None, None, [_finding("TRANSITION_BASE_MISMATCH", str(root), message)]
    if head == base:
        return head, base, []
    lineage = parents(root, head)
    if lineage != [base]:
        message = (
            f"candidate {head[:12]} declares parents {[item[:12] for item in lineage]} "
            f"while the accepted base is {base[:12]}; a transition names exactly one parent "
            "and it is the base the admission boundary holds"
        )
        return head, base, [_finding("TRANSITION_BASE_MISMATCH", str(root), message)]
    return head, base, []


def _record_findings(root: Path, before: AcceptedState, after: AcceptedState) -> list[Finding]:
    out: list[Finding] = []
    for path, oid in sorted(before.blobs.items()):
        if _run_workspace(path) or classify(path) is None:
            continue
        if not after.holds(path):
            out.append(_finding("TRANSITION_RECORD_DELETED", path, "the accepted record is gone"))
            continue
        if after.blobs[path] == oid:
            continue
        if not _appends_only(path):
            out.append(
                _finding(
                    "TRANSITION_RECORD_MUTATED",
                    path,
                    "the accepted record changed; accepted history is written once",
                )
            )
            continue
        previous = read_blob(root, before.commit, path) or b""
        current = read_blob(root, after.commit, path) or b""
        if not current.startswith(previous):
            out.append(
                _finding(
                    "TRANSITION_STREAM_REWRITTEN",
                    path,
                    "the accepted stream was rewritten rather than extended",
                )
            )
    return out


def _owned_runs(root: Path, before: AcceptedState, after: AcceptedState, operator: str) -> set[str]:
    owned: set[str] = set()
    for state in (before, after):
        for path in state.kind(Protected.RUN):
            if path.rsplit("/", 1)[-1] != RUN_MARKER:
                continue
            marker = json_object(read_blob(root, state.commit, path))
            if text_field(marker, "principal") == operator:
                owned.add(text_field(marker, "run_id"))
    owned.discard("")
    return owned


def _run_findings(
    root: Path, before: AcceptedState, after: AcceptedState, context: TrustedContext
) -> list[Finding]:
    out: list[Finding] = []
    for path in sorted(set(after.blobs) - set(before.blobs)):
        if classify(path) is not Protected.RUN:
            continue
        run_id = run_namespace(path)
        if run_id is None:
            continue
        marker = f"{path.rsplit('/' + run_id, 1)[0]}/{run_id}/{RUN_MARKER}"
        recorded = json_object(read_blob(root, before.commit, marker)) or json_object(
            read_blob(root, after.commit, marker)
        )
        principal = text_field(recorded, "principal")
        if principal == context.operator:
            continue
        message = (
            f"{context.operator} writes into run {run_id} whose marker binds "
            f"{principal or 'no principal'}"
        )
        out.append(_finding("TRANSITION_FOREIGN_RUN", path, message))
    return out


def validate_transition(root: Path, candidate: str, context: TrustedContext) -> list[Finding]:
    """Every reason ``candidate`` may not succeed the accepted state ``context.base_commit``."""
    if context.operator not in context.enrolled_principals:
        message = f"{context.operator} is not enrolled; no transition is attributable to them"
        return [_finding("TRANSITION_UNENROLLED_OPERATOR", str(root), message)]
    head, base, lineage = _base_findings(root, candidate, context)
    if head is None or base is None or lineage:
        return lineage
    before = read_state(root, base)
    after = read_state(root, head)
    owned = _owned_runs(root, before, after, context.operator)
    return [
        *_record_findings(root, before, after),
        *_run_findings(root, before, after, context),
        *claim_findings(root, before, after, owned),
        *verdict_findings(root, before, after),
        *epoch_findings(root, before, after),
        *backdated_findings(root, before, after),
        *trust_findings(root, after, context.trust_policy_digest),
        *_attribution_findings(root, before, after, context),
    ]


def _attribution_findings(
    root: Path, before: AcceptedState, after: AcceptedState, context: TrustedContext
) -> list[Finding]:
    if context.signing is None:
        return []
    covered, findings = authorized_digests(
        root, after, (SshKeygenBackend(), context.signing, context.operator)
    )
    return [*findings, *unsigned_record_findings(root, (before, after), covered)]


def context_from_mapping(body: dict[str, object]) -> TrustedContext:
    """Build a context from bytes the CALLER owns; never from the candidate being judged."""
    enrolled = body.get("enrolled_principals")
    if not isinstance(enrolled, list) or not all(isinstance(item, str) for item in enrolled):
        raise TransitionContextError("enrolled_principals must be a list of principal strings")
    return TrustedContext(
        project=text_field(body, "project"),
        operator=text_field(body, "operator"),
        base_commit=text_field(body, "base_commit"),
        trust_policy_digest=text_field(body, "trust_policy_digest"),
        enrolled_principals=frozenset(str(item) for item in enrolled),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 tools/transition.py", description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--candidate", required=True, help="the proposed successor commit or ref")
    parser.add_argument(
        "--context",
        required=True,
        help="path to the admission boundary's own context JSON, outside the candidate tree",
    )
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        body = json.loads(Path(args.context).read_text(encoding="utf-8"))
        context = context_from_mapping(body if isinstance(body, dict) else {})
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TransitionContextError) as exc:
        sys.stderr.write(f"context is unusable: {exc}\n")
        return 2
    findings = validate_transition(Path(args.root), args.candidate, context)
    if args.json:
        sys.stdout.write(serialize_findings(findings) + "\n")
    else:
        for item in findings:
            sys.stdout.write(render_finding(item) + "\n")
    if findings:
        return 1
    sys.stdout.write(f"admit: {args.candidate} is a lawful successor to {context.base_commit}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
