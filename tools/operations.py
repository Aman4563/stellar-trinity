"""Signed run operations: what a principal states they did, bound to the bytes they wrote.

A run marker binds a namespace to a principal, but the marker is JSON the operator can edit and
the principal inside it is whatever ``GITHUB_ACTOR`` or the git identity said. Signing that one
file would still leave every later write unattributed, so authority here attaches to the
operation rather than to the namespace: each authoritative write is a statement naming the
project, the run, the verb, the SHA-256 of the record it authorizes, its position in the run's
chain, and the principal making it, carried in a DSSE envelope the ``allowed_signers`` file and
the versioned trust root decide on.

Two properties follow. The signer and the claimed principal must be the same identity, so a
valid signature never authorizes a statement attributed to someone else. And the operations of
one run form a hash chain from sequence one, so an operation cannot be removed, reordered, or
inserted without breaking the link that follows it.

Nothing here decides which of two signed operations arrived first. That is the admission
boundary's question, and ``tools/transition.py`` is what it runs to answer it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Final

from tools._findings import Finding, Severity
from tools.attest import canonical, dsse, trustroot
from tools.attest.backend import SignatureBackend

SCHEMA: Final = "trinity.run-operation/v1"
PAYLOAD_TYPE: Final = "application/vnd.trinity.run-operation+json"
ROLE: Final = "run_operator"
CHAIN_GENESIS: Final = "0" * 64
OPERATIONS_DIR: Final = "operations"
HARNESS: Final[dict[str, str]] = {
    "engram": ".memory",
    "forge": ".seed",
    "crucible": ".audit",
}
OPERATION_CODES: Final = (
    "OPERATION_ENVELOPE_INVALID",
    "OPERATION_PRINCIPAL_MISMATCH",
    "OPERATION_UNAUTHORIZED",
    "OPERATION_CHAIN_BROKEN",
)


class Verb(StrEnum):
    """The authoritative writes an operation may authorize."""

    OPEN = "open"
    SEAL = "seal"
    CLAIM = "claim"
    VERDICT = "verdict"
    PUBLISH = "publish"


@dataclass(frozen=True, slots=True)
class Operation:
    """One principal's statement that they wrote one record inside one run."""

    project: str
    run_id: str
    verb: Verb
    artifact_digest: str
    seq: int
    previous: str
    principal: str


@dataclass(frozen=True, slots=True)
class SigningPolicy:
    """Where the boundary's own trust material lives; never a path inside the candidate."""

    allowed_signers: Path
    trust_root: Path
    trusted_version: int
    evaluation_time: datetime


@dataclass(frozen=True, slots=True)
class VerifiedOperation:
    """An operation whose signature, claimed principal, and role authorization all held."""

    operation: Operation
    principal: str
    entry_hash: str


def _finding(code: str, path: str, message: str) -> Finding:
    return Finding(code, Severity.ERROR, path, None, message)


def _body(item: Operation) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "project": item.project,
        "run_id": item.run_id,
        "verb": str(item.verb),
        "artifact_digest": item.artifact_digest,
        "seq": item.seq,
        "previous": item.previous,
        "principal": item.principal,
    }


def payload(item: Operation) -> bytes:
    """The exact canonical bytes signed for ``item``."""
    return canonical.canonicalize(_body(item))


def entry_hash(item: Operation) -> str:
    """The chain identity of ``item``, covering every field of its signed payload."""
    return canonical.canonical_sha256(_body(item))


def sign_operation(backend: SignatureBackend, item: Operation, *, key_path: Path) -> dsse.Envelope:
    """Sign ``item`` with the principal's own software key."""
    return dsse.sign_envelope(backend, PAYLOAD_TYPE, payload(item), key_path=key_path)


def _parse_operation(raw: object) -> Operation | None:
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        return None
    fields = ("project", "run_id", "verb", "artifact_digest", "previous", "principal")
    if not all(isinstance(raw.get(name), str) and raw[name] for name in fields):
        return None
    seq = raw.get("seq")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        return None
    if str(raw["verb"]) not in set(Verb):
        return None
    return Operation(
        project=str(raw["project"]),
        run_id=str(raw["run_id"]),
        verb=Verb(str(raw["verb"])),
        artifact_digest=str(raw["artifact_digest"]),
        seq=seq,
        previous=str(raw["previous"]),
        principal=str(raw["principal"]),
    )


def verify_operation(
    backend: SignatureBackend, document: bytes, policy: SigningPolicy
) -> tuple[VerifiedOperation | None, list[Finding]]:
    """Verify one envelope's signature, its claimed principal, and that principal's role."""
    location = str(policy.trust_root)
    parsed = dsse.parse_envelope(document)
    if parsed.envelope is None:
        return None, [_finding("OPERATION_ENVELOPE_INVALID", location, parsed.detail)]
    signature = dsse.verify_envelope(
        backend,
        parsed.envelope,
        expected_payload_type=PAYLOAD_TYPE,
        allowed_signers_path=policy.allowed_signers,
        evaluation_time=policy.evaluation_time,
    )
    if not signature.accepted:
        return None, [_finding("OPERATION_ENVELOPE_INVALID", location, signature.detail)]
    try:
        item = _parse_operation(canonical.parse_json(parsed.envelope.payload))
    except canonical.CanonicalizationError as exc:
        return None, [_finding("OPERATION_ENVELOPE_INVALID", location, str(exc))]
    if item is None:
        message = "the payload is not a trinity.run-operation/v1 statement"
        return None, [_finding("OPERATION_ENVELOPE_INVALID", location, message)]
    if item.principal not in signature.principals:
        message = (
            f"the operation claims {item.principal!r} while the verified signers are "
            f"{sorted(signature.principals)}; a signature never speaks for another identity"
        )
        return None, [_finding("OPERATION_PRINCIPAL_MISMATCH", location, message)]
    authorization = trustroot.authorize(
        policy.trust_root,
        role_name=ROLE,
        verified_principals=(item.principal,),
        evaluation_time=policy.evaluation_time,
        trusted_version=policy.trusted_version,
    )
    if not authorization.accepted:
        message = f"{item.principal} is not authorized for role {ROLE}: {authorization.detail}"
        return None, [_finding("OPERATION_UNAUTHORIZED", location, message)]
    return VerifiedOperation(item, item.principal, entry_hash(item)), []


def chain_findings(found: list[VerifiedOperation]) -> list[Finding]:
    """One refusal per link that does not follow: a run's operations start at one and chain."""
    out: list[Finding] = []
    previous = CHAIN_GENESIS
    expected = 1
    run_id = found[0].operation.run_id if found else ""
    for item in found:
        location = f"{item.operation.run_id}/{OPERATIONS_DIR}/{item.operation.seq:04d}.json"
        if item.operation.run_id != run_id:
            message = (
                f"operation {item.operation.seq} belongs to run {item.operation.run_id} while "
                f"the chain is {run_id}; one chain carries one run"
            )
            out.append(_finding("OPERATION_CHAIN_BROKEN", location, message))
        elif item.operation.seq != expected:
            message = f"operation sequence reached {item.operation.seq}, expected {expected}"
            out.append(_finding("OPERATION_CHAIN_BROKEN", location, message))
        elif item.operation.previous != previous:
            message = (
                f"operation {item.operation.seq} links to {item.operation.previous[:12]} while "
                f"its predecessor hashes to {previous[:12]}"
            )
            out.append(_finding("OPERATION_CHAIN_BROKEN", location, message))
        previous = item.entry_hash
        expected = item.operation.seq + 1
    return out


def operations_dir(root: Path, run_id: str) -> Path:
    """The directory holding one run's signed operations, inside that run's namespace."""
    harness = HARNESS.get(run_id.split("-", 1)[0])
    if harness is None:
        raise ValueError(f"{run_id!r} names no instrument harness")
    return root / harness / "runs" / run_id / OPERATIONS_DIR


def write_operation(root: Path, item: Operation, envelope: dsse.Envelope) -> Path:
    """Place one signed operation at its sequence inside the run namespace it authorizes."""
    directory = operations_dir(root, item.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{item.seq:04d}.json"
    path.write_bytes(envelope.to_json())
    return path


def read_operations(
    root: Path, run_id: str, backend: SignatureBackend, policy: SigningPolicy
) -> tuple[list[VerifiedOperation], list[Finding]]:
    """Every verified operation of one run in sequence order, with each refusal it produced."""
    directory = operations_dir(root, run_id)
    if not directory.is_dir():
        return [], []
    found: list[VerifiedOperation] = []
    out: list[Finding] = []
    for path in sorted(directory.glob("*.json")):
        try:
            document = path.read_bytes()
        except OSError as exc:
            out.append(_finding("OPERATION_ENVELOPE_INVALID", str(path), str(exc)))
            continue
        item, findings = verify_operation(backend, document, policy)
        out += [
            Finding(entry.code, entry.severity, str(path), None, entry.message)
            for entry in findings
        ]
        if item is not None:
            found.append(item)
    return sorted(found, key=lambda item: item.operation.seq), out
