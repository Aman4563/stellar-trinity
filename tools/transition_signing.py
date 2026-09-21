"""The trust material a transition answers to, and the signed operations that attribute it.

Two questions live here. Whether the candidate still carries the trust policy the admission
boundary pinned, because a transition that ships its own trust root has authorized itself. And
whether each record the transition introduces is covered by a run operation some enrolled
principal actually signed, because an unsigned claim or verdict is a byte an operator wrote
about themselves.

Coverage is by content digest: an operation names the SHA-256 of the record it authorizes, so
the record on disk and the statement about it cannot drift apart. A transition offered without
a signing policy is judged on its structure alone and these rules stay silent, which is the
state every parent is in until enrolment exists.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tools._findings import Finding, Severity
from tools.accepted_state import (
    TRUST_POLICY_PATH,
    AcceptedState,
    Protected,
    read_blob,
    run_namespace,
)
from tools.attest.backend import SignatureBackend
from tools.operations import OPERATIONS_DIR, SigningPolicy, verify_operation

SIGNED_KINDS = (Protected.CLAIM, Protected.VERDICT)


def _finding(code: str, path: str, message: str) -> Finding:
    return Finding(code, Severity.ERROR, path, None, message)


def trust_findings(root: Path, after: AcceptedState, pinned_digest: str) -> list[Finding]:
    """The candidate must carry the exact trust policy the boundary pinned, or none at all."""
    data = read_blob(root, after.commit, TRUST_POLICY_PATH)
    if data is None:
        return []
    digest = hashlib.sha256(data).hexdigest()
    if digest == pinned_digest:
        return []
    message = (
        f"the candidate carries trust policy {digest[:12]} while the boundary pins "
        f"{pinned_digest[:12]}; a trust change is an out-of-band ceremony, never a payload "
        "of the transition it would authorize"
    )
    return [_finding("TRANSITION_TRUST_DRIFT", TRUST_POLICY_PATH, message)]


def _operation_paths(after: AcceptedState) -> list[str]:
    return sorted(
        path
        for path in after.kind(Protected.RUN)
        if f"/{OPERATIONS_DIR}/" in path and path.endswith(".json")
    )


def authorized_digests(
    root: Path, after: AcceptedState, verification: tuple[SignatureBackend, SigningPolicy, str]
) -> tuple[set[str], list[Finding]]:
    """Every artifact digest the operator signed for in this candidate, and each refusal."""
    backend, policy, operator = verification
    covered: set[str] = set()
    out: list[Finding] = []
    for path in _operation_paths(after):
        document = read_blob(root, after.commit, path)
        if document is None:
            continue
        item, findings = verify_operation(backend, document, policy)
        out += [
            Finding(entry.code, entry.severity, path, None, entry.message) for entry in findings
        ]
        if item is None:
            continue
        if item.principal != operator:
            message = (
                f"the operation is signed by {item.principal} while the transition is offered "
                f"by {operator}; one transition carries one operator's work"
            )
            out.append(_finding("OPERATION_PRINCIPAL_MISMATCH", path, message))
            continue
        if run_namespace(path) != item.operation.run_id:
            message = (
                f"the operation names run {item.operation.run_id} from inside the namespace of "
                f"{run_namespace(path)}; an operation lives in the run it authorizes"
            )
            out.append(_finding("OPERATION_CHAIN_BROKEN", path, message))
            continue
        covered.add(item.operation.artifact_digest)
    return covered, out


def unsigned_record_findings(
    root: Path, states: tuple[AcceptedState, AcceptedState], covered: set[str]
) -> list[Finding]:
    """Every new claim or verdict whose bytes no verified operation names."""
    before, after = states
    out: list[Finding] = []
    for kind in SIGNED_KINDS:
        for path in sorted(set(after.kind(kind)) - set(before.blobs)):
            data = read_blob(root, after.commit, path)
            if data is None:
                continue
            digest = hashlib.sha256(data).hexdigest()
            if digest in covered:
                continue
            message = (
                f"the record hashes to {digest[:12]} and no verified operation in this "
                "transition authorizes those bytes"
            )
            out.append(_finding("TRANSITION_UNSIGNED_OPERATION", path, message))
    return out
