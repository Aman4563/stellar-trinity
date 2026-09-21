"""Run-private feedback capture. Finish all writes before qualification (ADR 0005 §3).

No checkpoint is exempt from enrolled signing, including genesis. Invoke by path:
``python3 ./trinity/tools/feedback.py append|checkpoint|walk ./ --help``.

A chain captured before run namespaces existed lives at the harness root rather than under
``<harness>/runs/<run_id>/``. It is frozen, because every new turn lands in a run, but the
gate still walks it and still requires its head to be signed. ``checkpoint`` and ``walk``
accept ``--legacy-root`` in place of ``--run`` to address that chain; ``append`` never does,
because a new turn always belongs to a run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import runs
from tools.attest import canonical, trustroot
from tools.attest.backend_ssh import SignatureBackendError, SshKeygenBackend
from tools.feedback_chain import BROKEN, ROLLED_BACK, FeedbackError, Head, integrity, walk_documents
from tools.project_paths import invocation_root, resolve_project_path
from tools.tracker import _atomic_write

if TYPE_CHECKING:
    from tools.attest.canonical import JSONValue

__all__ = ["integrity", "main"]

UNENROLLED: Final = "FEEDBACK_CHECKPOINT_UNENROLLED"
LOGIN: Final = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")


@dataclass(frozen=True, slots=True)
class Target:
    root: Path
    instrument: str
    run_id: str | None

    @property
    def harness(self) -> str:
        return runs.HARNESS[self.instrument].removeprefix(".")

    def path(self, name: str) -> Path:
        if self.run_id is None:
            return resolve_project_path(
                f"./{runs.HARNESS[self.instrument]}/{name}", project_root=self.root
            )
        directory = runs.run_dir(self.root, self.instrument, self.run_id)
        return resolve_project_path(
            f"./{directory.relative_to(self.root).as_posix()}/{name}", project_root=self.root
        )


def _text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except FileNotFoundError:
        return ""


def _head(target: Target, *, genesis: bool = False) -> Head:
    chain_path = target.path(integrity.FEEDBACK_CHAIN)
    ledger = None if target.run_id is None else _text(target.path(integrity.FEEDBACK_LEDGER))
    log = _text(target.path(integrity.FEEDBACK_CHECKPOINTS[target.harness]))
    signature = target.path("feedback-head.sig")
    if not chain_path.exists():
        if genesis and not ledger and not log and not signature.exists():
            return Head(0, integrity.CHAIN_GENESIS, "", "")
        raise FeedbackError(BROKEN, "feedback chain is missing")
    return walk_documents(_text(chain_path), ledger, log)


def _append(target: Target, args: argparse.Namespace) -> Head:
    if target.run_id is None:
        raise FeedbackError("FEEDBACK_IDENTITY_UNRESOLVED", "a new turn always belongs to a run")
    if args.kind not in integrity.CHAIN_KINDS:
        raise FeedbackError("FEEDBACK_KIND_UNKNOWN", "kind is outside the closed vocabulary")
    if (
        not LOGIN.fullmatch(args.github_id)
        or args.github_id == "unattributed"
        or not args.principal
    ):
        raise FeedbackError("FEEDBACK_IDENTITY_UNRESOLVED", "principal and GitHub login required")
    marker = target.path("run.json")
    run = runs._read_run(marker)
    stamp = args.received_at or (run.started_at if run else None)
    if stamp is None or not stamp.endswith("Z"):
        raise ValueError("--received-at must supply an RFC 3339 UTC instant for a new run")
    integrity.parse_evaluation_time(stamp)
    reasoning_path = resolve_project_path(
        args.reasoning_file, project_root=target.root, must_exist=True
    )
    reasoning = canonical.parse_json(reasoning_path.read_bytes())
    if not isinstance(reasoning, list) or not reasoning:
        raise ValueError("reasoning file must contain a nonempty JSON list")
    head = _head(target, genesis=True)
    raw = sys.stdin.buffer.read()
    seq = head.seq + 1
    record: dict[str, JSONValue] = {
        "feedback_id": seq,
        "received_at": stamp,
        "kind": args.kind,
        "verbatim": raw.decode("utf-8"),
        "github_id": args.github_id,
        "invocation_context": {"run_id": target.run_id, "principal": args.principal},
        "probable_reasoning": reasoning,
        "targets": [],
        "chain_seq": seq,
        "disposition": "pending",
    }
    entry: dict[str, JSONValue] = {
        "seq": seq,
        "captured_at": stamp,
        "feedback_id": seq,
        "kind": args.kind,
        "verbatim_sha256": hashlib.sha256(raw).hexdigest(),
        "record_sha256": canonical.canonical_sha256(record),
        "writer": args.principal,
        "github_id": args.github_id,
        "prev_hash": head.entry_hash,
    }
    digest = integrity.chain_digest(dict(entry))
    entry["entry_hash"] = digest
    runs.open_run(
        target.root,
        target.instrument,
        target.run_id,
        principal=args.principal,
        now=integrity.parse_evaluation_time(stamp),
    )
    _atomic_write(
        target.path(integrity.FEEDBACK_LEDGER),
        head.ledger + "- " + canonical.canonicalize(record).decode(),
    )
    separator = "\n" if head.chain and not head.chain.endswith("\n") else ""
    _atomic_write(
        target.path(integrity.FEEDBACK_CHAIN),
        head.chain + separator + canonical.canonicalize(entry).decode(),
    )
    return Head(seq, digest, "", "")


def _checkpoint(target: Target, args: argparse.Namespace) -> Head:
    head = _head(target)
    at = integrity.parse_evaluation_time(args.at) if args.at else datetime.now(UTC)
    try:
        root_path = resolve_project_path(
            "./" + integrity.TRUST_ROOT_PATH, project_root=target.root, must_exist=True
        )
        signers = resolve_project_path(
            "./" + integrity.ALLOWED_SIGNERS_PATH, project_root=target.root, must_exist=True
        )
        version = resolve_project_path(
            "./" + integrity.TRUSTED_ROOT_VERSION_PATH, project_root=target.root, must_exist=True
        )
        authorized = trustroot.authorize(
            root_path,
            role_name=integrity.CHECKPOINT_ROLE,
            verified_principals=(args.principal,),
            evaluation_time=at,
            trusted_version=int(version.read_text()),
        )
        if not authorized.accepted:
            raise FeedbackError(UNENROLLED, "principal is not an enrolled checkpointer")
        key = resolve_project_path(args.key, project_root=target.root, must_exist=True)
        payload = integrity.checkpoint_signature_payload(
            target.root, target.harness, head.seq, head.entry_hash
        )
        backend = SshKeygenBackend()
        signature = backend.sign(payload, key_path=key)
        with tempfile.TemporaryDirectory(prefix="trinity-feedback-") as temporary:
            staged = Path(temporary) / "head.sig"
            staged.write_bytes(signature)
            verified = backend.verify(
                payload, signature_path=staged, allowed_signers_path=signers, evaluation_time=at
            )
        if not verified.verified or verified.principal != args.principal:
            raise FeedbackError(UNENROLLED, "key does not authenticate the enrolled principal")
    except (OSError, ValueError, SignatureBackendError) as exc:
        raise FeedbackError(UNENROLLED, "checkpoint signing or enrollment refused") from exc
    if target.run_id is not None:
        runs.open_run(target.root, target.instrument, target.run_id, principal=args.principal)
    signature_path = target.path("feedback-head.sig")
    log = target.path(integrity.FEEDBACK_CHECKPOINTS[target.harness])
    prior = _text(log)
    separator = "\n" if prior and not prior.endswith("\n") else ""
    relative = signature_path.relative_to(target.root).as_posix()
    block = f"- root: {head.entry_hash}\n  seq: {head.seq}\n  signature: {relative}\n"
    _atomic_write(signature_path, signature.decode("ascii"))
    _atomic_write(log, prior + separator + block)
    return head


def _walk(target: Target) -> Head:
    head = _head(target)
    findings = integrity.chain_checkpoint_findings(
        target.root,
        target.path(integrity.FEEDBACK_CHECKPOINTS[target.harness]),
        head.entry_hash,
        seq=head.seq,
        harness=target.harness,
        evaluation_time=datetime.now(UTC),
        backend=SshKeygenBackend(),
    )
    if findings:
        code = (
            ROLLED_BACK
            if any(item.code == "CHECKPOINT_HEAD_ROLLED_BACK" for item in findings)
            else BROKEN
        )
        raise FeedbackError(code, "checkpoint verification refused")
    return head


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for verb in ("append", "checkpoint", "walk"):
        sub = commands.add_parser(verb)
        sub.add_argument("root")
        sub.add_argument("--instrument", required=True, choices=tuple(runs.HARNESS))
        if verb == "append":
            sub.add_argument("--run", required=True)
        else:
            namespace = sub.add_mutually_exclusive_group(required=True)
            namespace.add_argument("--run")
            namespace.add_argument(
                "--legacy-root",
                action="store_true",
                help="address the frozen pre-namespace chain at the harness root",
            )
        sub.add_argument("--json", action="store_true", dest="as_json")
        if verb != "walk":
            sub.add_argument("--principal", required=True)
        if verb == "append":
            for name in ("kind", "github-id", "reasoning-file"):
                sub.add_argument(f"--{name}", required=True)
            sub.add_argument("--received-at")
        if verb == "checkpoint":
            sub.add_argument("--key", required=True)
            sub.add_argument("--at")
    try:
        args = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1
    try:
        root = resolve_project_path(args.root, project_root=invocation_root(), must_exist=True)
        target = Target(root, args.instrument, getattr(args, "run", None))
        match args.command:
            case "append":
                head = _append(target, args)
            case "checkpoint":
                head = _checkpoint(target, args)
            case "walk":
                head = _walk(target)
            case _:
                return 1
    except (FeedbackError, runs.RunError) as exc:
        print(
            json.dumps({"code": exc.code, "written": False}) if args.as_json else f"refused: {exc}"
        )
        return 3
    except (OSError, canonical.CanonicalizationError, UnicodeError) as exc:
        print(
            json.dumps({"code": BROKEN, "written": False})
            if args.as_json
            else f"refused: {type(exc).__name__}"
        )
        return 3
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps({"seq": head.seq, "entry_hash": head.entry_hash}, sort_keys=True)
        if args.as_json
        else f"{head.seq} {head.entry_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
