"""Enrol the first human principal into a parent that has no trust root yet.

Every feedback checkpoint must be signed by a principal the trust root binds to
``feedback_checkpointer``, and there is no genesis exemption, so a parent with no
``.memory/roots.yaml`` cannot sign its chain head at ``seq`` 1 and every instrument halts
before Phase R. Nothing produced that root: the rotation ceremony in
``docs/trust-root.md`` presumes a root already exists. This door writes the initial root
for exactly one human and their software SSH public key, refuses to touch a parent that
already carries any trust-root byte, and re-reads what it wrote through the same parser
and authorization path the gate uses before it reports success. It mints no key and holds
no secret; the human keeps the private half. A second principal, a changed role, or a
threshold above one is a rotation and never a second enrolment.

Invoke by path: ``python3 ./trinity/tools/enrol.py ./ --principal LOGIN --public-key PATH``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Final

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.attest import canonical, trustroot
from tools.attest.backend_ssh import SOFTWARE_KEY_ALGORITHMS
from tools.project_paths import invocation_root, resolve_project_path

if TYPE_CHECKING:
    from tools.attest.canonical import JSONValue

__all__ = ["EnrolError", "enrol", "main"]

TRUST_ROOT: Final = "./.memory/roots.yaml"
ALLOWED_SIGNERS: Final = "./.memory/allowed_signers"
TRUSTED_VERSION: Final = "./.memory/trusted-root-version"
SURFACES: Final = (TRUST_ROOT, ALLOWED_SIGNERS, TRUSTED_VERSION)
# The roles one human needs to write a run: sign the feedback chain head and author the
# run operations that attribute every later write. Release and clearance roles stay
# unbound, because each of those needs a second distinct principal by construction.
ROLES: Final = ("feedback_checkpointer", "run_operator")
NAMESPACES: Final = "trinity.attestation.v1,git"
INITIAL_VERSION: Final = 1
DEFAULT_TERM: Final = timedelta(days=365)
PRINCIPAL: Final = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._@-]{0,62}[A-Za-z0-9])?\Z")
MAX_PUBLIC_KEY_BYTES: Final = 16 * 1024

ALREADY_ENROLLED: Final = "ENROL_ROOT_EXISTS"
PRINCIPAL_INVALID: Final = "ENROL_PRINCIPAL_INVALID"
KEY_INVALID: Final = "ENROL_PUBLIC_KEY_INVALID"
EXPIRY_INVALID: Final = "ENROL_EXPIRY_INVALID"
UNVERIFIED: Final = "ENROL_ROOT_UNVERIFIED"


class EnrolError(ValueError):
    """A refusal with a closed public code."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _instant(value: str, code: str) -> datetime:
    if not value.endswith("Z"):
        raise EnrolError(code, "instant must be an RFC 3339 UTC value ending in Z")
    try:
        return datetime.fromisoformat(value.removesuffix("Z")).replace(tzinfo=UTC)
    except ValueError as exc:
        raise EnrolError(code, "instant is not RFC 3339") from exc


def _format(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _public_key(path: Path) -> tuple[str, str]:
    try:
        if path.stat().st_size > MAX_PUBLIC_KEY_BYTES:
            raise EnrolError(KEY_INVALID, "public key file is larger than a public key")
        text = path.read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        raise EnrolError(KEY_INVALID, "public key file is unreadable") from exc
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise EnrolError(KEY_INVALID, "public key file must hold exactly one key line")
    parts = lines[0].split()
    if len(parts) < 2 or parts[0] not in SOFTWARE_KEY_ALGORITHMS:  # noqa: PLR2004
        raise EnrolError(KEY_INVALID, "public key is not a software key this backend accepts")
    if "PRIVATE KEY" in text:
        raise EnrolError(KEY_INVALID, "a private key was offered where a public key belongs")
    return parts[0], parts[1]


def _root_document(principal: str, expires: datetime) -> dict[str, JSONValue]:
    return {
        "version": INITIAL_VERSION,
        "expires": _format(expires),
        "roles": [{"name": role, "threshold": 1} for role in ROLES],
        "principals": [{"name": principal, "roles": list(ROLES)}],
        "revocations": [],
    }


def _verify(root_path: Path, principal: str, at: datetime) -> None:
    """Re-read the written root through the gate's own path and refuse if any role fails."""

    for role in ROLES:
        outcome = trustroot.authorize(
            root_path,
            role_name=role,
            verified_principals=(principal,),
            evaluation_time=at,
            trusted_version=INITIAL_VERSION,
        )
        if not outcome.accepted:
            raise EnrolError(UNVERIFIED, f"{role}: {outcome.reason_value}: {outcome.detail}")


def _write(path: Path, body: str) -> None:
    handle, name = tempfile.mkstemp(dir=str(path.parent), prefix=".enrol-")
    scratch = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(body)
        scratch.chmod(0o644)
        scratch.replace(path)
    except OSError:
        scratch.unlink(missing_ok=True)
        raise


def enrol(
    root: Path,
    *,
    principal: str,
    public_key: Path,
    at: datetime,
    expires: datetime | None = None,
) -> tuple[Path, ...]:
    """Write the three trust-root surfaces for one principal and return their paths."""

    root = root.resolve(strict=True)
    if not PRINCIPAL.fullmatch(principal):
        raise EnrolError(PRINCIPAL_INVALID, "principal must be a plain login or address")
    term = expires if expires is not None else at + DEFAULT_TERM
    if term <= at:
        raise EnrolError(EXPIRY_INVALID, "expiry must fall after the enrolment instant")
    algorithm, encoded = _public_key(public_key)
    targets = tuple(resolve_project_path(surface, project_root=root) for surface in SURFACES)
    for target in targets:
        if target.exists() or target.is_symlink():
            raise EnrolError(
                ALREADY_ENROLLED,
                f"{target.relative_to(root).as_posix()} exists; a change to an existing root "
                "is a rotation ceremony, never an enrolment",
            )
    root_target, signers_target, version_target = targets
    root_target.parent.mkdir(parents=True, exist_ok=True)
    _write(root_target, canonical.canonicalize(_root_document(principal, term)).decode())
    _write(signers_target, f'{principal} namespaces="{NAMESPACES}" {algorithm} {encoded}\n')
    _write(version_target, f"{INITIAL_VERSION}\n")
    _verify(root_target, principal, at)
    return targets


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("--principal", required=True)
    parser.add_argument("--public-key", required=True)
    parser.add_argument("--expires", help="RFC 3339 UTC; default is one year from --at")
    parser.add_argument("--at", help="RFC 3339 UTC enrolment instant; default is now")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv[1:])
    try:
        project_root = invocation_root()
        root = resolve_project_path(args.root, project_root=project_root, must_exist=True)
        key = resolve_project_path(args.public_key, project_root=project_root, must_exist=True)
        at = _instant(args.at, EXPIRY_INVALID) if args.at else datetime.now(UTC)
        expires = _instant(args.expires, EXPIRY_INVALID) if args.expires else None
        written = enrol(root, principal=args.principal, public_key=key, at=at, expires=expires)
    except (EnrolError, ValueError, OSError) as exc:
        code = exc.code if isinstance(exc, EnrolError) else KEY_INVALID
        print(json.dumps({"code": code, "written": False}) if args.as_json else f"refused: {exc}")
        return 3
    paths = [f"./{path.relative_to(root).as_posix()}" for path in written]
    if args.as_json:
        print(json.dumps({"principal": args.principal, "written": paths}, sort_keys=True))
    else:
        print(f"enrolled {args.principal}; commit these paths:")
        print("\n".join(f"  {path}" for path in paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
