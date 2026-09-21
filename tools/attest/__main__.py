"""Command-line entry point for Trinity attestation verification.

Usage:
  python -m tools.attest verify ENVELOPE ARTIFACT TRUST_ROOT ALLOWED_SIGNERS
      COLLATERAL_MANIFEST [SUBJECT_NAME] [PRODUCER_PRINCIPAL]

The gate reads audience, trusted root version, candidate root, and replay-store path from canonical
JSON at ``./.trinity/attest-gate.json`` beneath the trusted invocation root. Every authored path in
the command and policy starts with ``./``. The policy and replay store must be owned by the gate
account and live outside the audited candidate tree. Verification time comes from the gate's system
clock and is printed with every decision.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from tools.project_paths import (
    ProjectPathError,
    invocation_root,
    redact_project_root,
    resolve_project_path,
)

from .backend_ssh import SshKeygenBackend
from .canonical import CanonicalizationError, parse_json
from .policies.execution import declared_execution_interval_failure
from .replay import ReplayGuard, load_gate_policy
from .verify import verify_attestation

MIN_VERIFY_ARGUMENTS = 7
MAX_VERIFY_ARGUMENTS = 9
MIN_COMMAND_ARGUMENTS = 2
SUBJECT_NAME_ARGUMENTS = 8
PRODUCER_PRINCIPAL_ARGUMENTS = 9


def _gate_evaluation_time() -> datetime:
    return datetime.now(UTC)


def _gate_policy_path(project_root: Path) -> Path:
    return resolve_project_path(
        "./.trinity/attest-gate.json",
        project_root=project_root,
        description="attestation gate policy",
        must_exist=True,
    )


def _format_instant(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _usage(message: str | None = None, *, exit_code: int = 2) -> int:
    print(__doc__)
    if message is not None:
        print(message)
    return exit_code


def _collateral(manifest_path: Path, *, project_root: Path) -> dict[str, bytes]:
    try:
        value = parse_json(manifest_path.read_bytes())
    except (CanonicalizationError, OSError) as error:
        raise ValueError(f"collateral manifest is unreadable: {error}") from error
    if not isinstance(value, dict):
        raise ValueError("collateral manifest must be a JSON object")
    collateral: dict[str, bytes] = {}
    for name, path_value in value.items():
        if not name or not isinstance(path_value, str) or not path_value:
            raise ValueError("collateral manifest entries must map non-empty names to paths")
        try:
            collateral_path = resolve_project_path(
                path_value,
                project_root=project_root,
                description=f"collateral {name!r}",
                must_exist=True,
            )
            collateral[name] = collateral_path.read_bytes()
        except (OSError, ProjectPathError) as error:
            raise ValueError(f"collateral {name!r} is unreadable: {error}") from error
    return collateral


def _verify(argv: list[str]) -> int:
    if not MIN_VERIFY_ARGUMENTS <= len(argv) <= MAX_VERIFY_ARGUMENTS:
        return _usage("verify received the wrong number of arguments")
    evaluation_time = _gate_evaluation_time()
    print(f"evaluated_at: {_format_instant(evaluation_time)}")
    try:
        project_root = invocation_root()
        envelope = resolve_project_path(
            argv[2], project_root=project_root, description="envelope", must_exist=True
        )
        artifact = resolve_project_path(
            argv[3], project_root=project_root, description="artifact", must_exist=True
        )
        trust_root = resolve_project_path(
            argv[4], project_root=project_root, description="trust root", must_exist=True
        )
        allowed_signers = resolve_project_path(
            argv[5], project_root=project_root, description="allowed signers", must_exist=True
        )
        manifest = resolve_project_path(
            argv[6],
            project_root=project_root,
            description="collateral manifest",
            must_exist=True,
        )
        policy = load_gate_policy(_gate_policy_path(project_root), authority_root=project_root)
        collateral = _collateral(manifest, project_root=project_root)
        replay_guard = ReplayGuard(
            policy.replay_store,
            expected_audience=policy.expected_audience,
        )
    except (OSError, ProjectPathError, ValueError) as error:
        root = locals().get("project_root")
        message = (
            str(error)
            if not isinstance(root, Path)
            else redact_project_root(str(error), project_root=root)
        )
        return _usage(f"gate configuration refused verification: {message}")

    interval_failure = declared_execution_interval_failure(envelope, evaluation_time)
    if interval_failure is not None:
        print(f"{interval_failure.reason_value}: {interval_failure.detail}")
        return 1

    outcome = verify_attestation(
        envelope_path=envelope,
        artifact_path=artifact,
        trust_root_path=trust_root,
        allowed_signers_path=allowed_signers,
        evaluation_time=evaluation_time,
        trusted_root_version=policy.trusted_root_version,
        backend=SshKeygenBackend(),
        replay_guard=replay_guard,
        collateral=collateral,
        subject_name=argv[7] if len(argv) >= SUBJECT_NAME_ARGUMENTS else None,
        producer_principal=(argv[8] if len(argv) >= PRODUCER_PRINCIPAL_ARGUMENTS else None),
    )
    if outcome.accepted:
        principals = ", ".join(outcome.principals)
        print(f"accepted: {principals}")
        return 0
    print(f"{outcome.reason_value}: {outcome.detail}")
    return 1


def main(argv: list[str]) -> int:
    if len(argv) < MIN_COMMAND_ARGUMENTS:
        return _usage()
    if len(argv) == MIN_COMMAND_ARGUMENTS and argv[1] in {"-h", "--help"}:
        return _usage(exit_code=0)
    if argv[1] == "verify":
        return _verify(argv)
    return _usage(f"unknown subcommand: {argv[1]}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
