"""Who owns a bundle and what order memory advances in, decided by the accepted sequence.

A claim, a verdict, an epoch publication, and a seal all report an instant about themselves, and
none of those instants is evidence: the operator writing the record chooses it. These rules
therefore read ownership and order out of the accepted state alone. A claim wins because it was
accepted first; a verdict is lawful because an accepted claim already named its run; an epoch
advances by exactly one from the accepted current; and a seal that would sort ahead of the
accepted watermark is refused rather than believed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from tools._findings import Finding, Severity
from tools.accepted_state import (
    CURRENT_PATH,
    AcceptedState,
    Protected,
    json_object,
    read_blob,
    text_field,
)

EPOCHS_SEGMENTS: Final = (".memory", "epochs")


def _finding(code: str, path: str, message: str) -> Finding:
    return Finding(code, Severity.ERROR, path, None, message)


def _claim_index(root: Path, state: AcceptedState) -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}
    for path in sorted(state.kind(Protected.CLAIM)):
        body = json_object(read_blob(root, state.commit, path))
        key = (text_field(body, "uuid"), text_field(body, "bundle_digest"))
        if all(key):
            index[key] = text_field(body, "consumer_run_id")
    return index


def claim_findings(
    root: Path, before: AcceptedState, after: AcceptedState, owned: set[str]
) -> list[Finding]:
    accepted = _claim_index(root, before)
    out: list[Finding] = []
    seen: dict[tuple[str, str], str] = {}
    for path in sorted(set(after.kind(Protected.CLAIM)) - set(before.blobs)):
        body = json_object(read_blob(root, after.commit, path))
        key = (text_field(body, "uuid"), text_field(body, "bundle_digest"))
        consumer = text_field(body, "consumer_run_id")
        if not all(key):
            continue
        if key in accepted:
            message = (
                f"{consumer or 'this claim'} claims {key[0]} which {accepted[key]} already "
                "owns in the accepted state; ownership is the accepted sequence"
            )
            out.append(_finding("TRANSITION_CLAIM_CONTESTED", path, message))
        elif key in seen:
            message = (
                f"{consumer} and {seen[key]} both claim {key[0]} in one transition; "
                "a contested claim is refused rather than settled by an instant"
            )
            out.append(_finding("TRANSITION_CLAIM_CONTESTED", path, message))
        elif consumer not in owned:
            out.append(
                _finding(
                    "TRANSITION_FOREIGN_RUN",
                    path,
                    f"the claim names run {consumer or '(none)'} the operator does not own",
                )
            )
        seen[key] = consumer
    return out


def verdict_findings(root: Path, before: AcceptedState, after: AcceptedState) -> list[Finding]:
    accepted = _claim_index(root, before)
    out: list[Finding] = []
    for path in sorted(set(after.kind(Protected.VERDICT)) - set(before.blobs)):
        body = json_object(read_blob(root, after.commit, path))
        key = (text_field(body, "uuid"), text_field(body, "bundle_digest"))
        consumer = text_field(body, "consumer_run_id")
        owner = accepted.get(key)
        if consumer and owner == consumer:
            continue
        message = (
            f"the verdict names {consumer or 'no run'} while the accepted claim on {key[0]} "
            f"is held by {owner or 'nobody'}; a verdict follows an accepted claim"
        )
        out.append(_finding("TRANSITION_VERDICT_UNOWNED", path, message))
    return out


def _epoch_number(root: Path, state: AcceptedState) -> int:
    body = json_object(read_blob(root, state.commit, CURRENT_PATH))
    value = body.get("epoch")
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def _published_epochs(state: AcceptedState) -> set[str]:
    """The epoch directory names ``state`` publishes under ``.memory/epochs/<n>/``."""
    depth = len(EPOCHS_SEGMENTS)
    return {
        parts[depth]
        for path in state.kind(Protected.EPOCH)
        if len(parts := path.split("/")) > depth
    }


def epoch_findings(root: Path, before: AcceptedState, after: AcceptedState) -> list[Finding]:
    accepted = _epoch_number(root, before)
    proposed = _epoch_number(root, after)
    out: list[Finding] = []
    if proposed < accepted:
        message = f"current epoch moves from {accepted} back to {proposed}"
        out.append(_finding("TRANSITION_EPOCH_ROLLBACK", CURRENT_PATH, message))
    for name in sorted(_published_epochs(after) - _published_epochs(before)):
        if name.isdigit() and int(name) == accepted + 1:
            continue
        message = (
            f"epoch {name} is published against accepted epoch {accepted}; a publication "
            f"advances to {accepted + 1} or it forks the memory"
        )
        out.append(_finding("TRANSITION_EPOCH_FORK", f".memory/epochs/{name}", message))
    return out


def _seal_instants(data: bytes) -> list[str]:
    out: list[str] = []
    for line in data.decode("utf-8", "replace").splitlines():
        stamp = text_field(json_object(line.encode("utf-8")), "sealed_at")
        if stamp:
            out.append(stamp)
    return out


def backdated_findings(root: Path, before: AcceptedState, after: AcceptedState) -> list[Finding]:
    accepted: list[str] = []
    for path in before.kind(Protected.STREAM):
        accepted += _seal_instants(read_blob(root, before.commit, path) or b"")
    if not accepted:
        return []
    watermark = max(accepted)
    out: list[Finding] = []
    for path in sorted(after.kind(Protected.STREAM)):
        previous = read_blob(root, before.commit, path) or b""
        current = read_blob(root, after.commit, path) or b""
        if not current.startswith(previous):
            continue
        for stamp in _seal_instants(current[len(previous) :]):
            if stamp < watermark:
                message = (
                    f"a seal instant of {stamp} precedes the accepted watermark {watermark}; "
                    "a backdated seal would reorder the scarce-slot queue"
                )
                out.append(_finding("TRANSITION_BACKDATED", path, message))
    return out
