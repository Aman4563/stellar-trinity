"""Anti-sabotage checks over a parent project.

Every check here assumes the operator running Trinity is an adversary who wants a
fabricated ``SHIP``. A disposition is therefore never trusted as prose: it must be
bound to committed bytes, to the vendored Trinity commit, and to a signature from a
principal who is not the producer. Instruments that can never fire, reports that
cite uncommitted files, forked contract remotes, typed sign-offs, workflow edits
bundled with gate bypasses, and dirty trees at gate time are each refused under a
``SAB_`` code so the sentinel can count them as intent rather than sloppiness.

Run standalone as ``python3 tools/sabotage.py <parent-root>`` or register ``CHECKS``
inside the parent gate. The module imports nothing from ``integrity.py`` so the gate
can import it without a cycle.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import layout
    from tools._findings import Finding, Severity, render_finding, serialize_findings
    from tools.attest import SignatureBackend
    from tools.attest import dsse as attest_dsse
    from tools.attest import trustroot as attest_trustroot
    from tools.attest.backend_ssh import SshKeygenBackend
    from tools.incident_probe import bypasses_a_gate
    from tools.project_paths import (
        ProjectPathError,
        display_project_path,
        invocation_root,
        redact_project_root,
        resolve_project_path,
    )
    from tools.release_evidence import is_sealing_path, seals_only
else:
    try:
        from tools import layout
    except ModuleNotFoundError:
        import layout
    try:
        from tools._findings import Finding, Severity, render_finding, serialize_findings
    except ModuleNotFoundError:
        from _findings import Finding, Severity, render_finding, serialize_findings
    try:
        from tools.project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
    except ModuleNotFoundError:
        from project_paths import (
            ProjectPathError,
            display_project_path,
            invocation_root,
            redact_project_root,
            resolve_project_path,
        )
    try:
        from tools.attest import SignatureBackend
        from tools.attest import dsse as attest_dsse
        from tools.attest import trustroot as attest_trustroot
        from tools.attest.backend_ssh import SshKeygenBackend
    except ModuleNotFoundError:
        from attest import SignatureBackend
        from attest import dsse as attest_dsse
        from attest import trustroot as attest_trustroot
        from attest.backend_ssh import SshKeygenBackend
    try:
        from tools.incident_probe import bypasses_a_gate
        from tools.release_evidence import is_sealing_path, seals_only
    except ModuleNotFoundError:
        from incident_probe import bypasses_a_gate
        from release_evidence import is_sealing_path, seals_only

SabotageCheck = Callable[[str, datetime | None], list[Finding]]

# ---- refusal codes -------------------------------------------------------------

SAB_DISPOSITION_UNBOUND = "SAB_DISPOSITION_UNBOUND"
SAB_DISPOSITION_FORGED = "SAB_DISPOSITION_FORGED"
SAB_INERT_INSTRUMENT = "SAB_INERT_INSTRUMENT"
SAB_AUDIT_UNCOMMITTED = "SAB_AUDIT_UNCOMMITTED"
SAB_SUBMODULE_REMOTE = "SAB_SUBMODULE_REMOTE"
SAB_SUBMODULE_OFF_MAIN = "SAB_SUBMODULE_OFF_MAIN"
SAB_SUBMODULE_UNVERIFIED = "SAB_SUBMODULE_UNVERIFIED"
SAB_TYPED_SIGNOFF = "SAB_TYPED_SIGNOFF"
# The sentinel's typed-clearance refusal is a sibling of typed sign-off.
SAB_SENTINEL_CLEARANCE_UNSIGNED = "SAB_SENTINEL_CLEARANCE_UNSIGNED"
SAB_WORKFLOW_TAMPER = "SAB_WORKFLOW_TAMPER"
SAB_WORKFLOW_TAMPER_SUSPECT = "SAB_WORKFLOW_TAMPER_SUSPECT"
SAB_DIRTY_TREE = "SAB_DIRTY_TREE"
SAB_READ_ERROR = "SAB_READ_ERROR"

# Every SAB_WORKFLOW_TAMPER finding carries the forward-only recovery the contracts prescribe.
# History rewriting is never offered: force-pushing the flagged commit away is itself sabotage.
WORKFLOW_TAMPER_RECOVERY = (
    "this is suspicion the gate records, not proof of intent; recover forward, never by "
    "rewriting or force-pushing history: review the flagged diff, re-establish signing "
    "authority through the externally governed rotation ceremony, land corrective commits "
    "that touch governance and subject separately, rerun the gate, and submit a signed "
    "remediation record for a distinct principal group; the original commits stay as evidence"
)
# A co-edit with no bypass syntax and no SHIP flip is suspicion at the HOLD tier: the same
# actor closes it by landing the governance and the subject paths again in separate commits.
WORKFLOW_TAMPER_SUSPECT_RECOVERY = (
    "this is suspicion the gate records, not proof of intent; close it forward by landing the "
    "flagged governance paths and the flagged subject paths again in split commits, never by "
    "rewriting or force-pushing history; the original commit stays as evidence"
)

SABOTAGE_CODES: frozenset[str] = frozenset(
    {
        SAB_DISPOSITION_UNBOUND,
        SAB_DISPOSITION_FORGED,
        SAB_INERT_INSTRUMENT,
        SAB_AUDIT_UNCOMMITTED,
        SAB_SUBMODULE_REMOTE,
        SAB_SUBMODULE_OFF_MAIN,
        SAB_TYPED_SIGNOFF,
        SAB_WORKFLOW_TAMPER,
        SAB_WORKFLOW_TAMPER_SUSPECT,
        SAB_DIRTY_TREE,
    }
)

# ---- layout constants ----------------------------------------------------------

TRINITY_DIR = "trinity"
TRINITY_BRANCH = "main"
CANONICAL_TRINITY_REMOTE = "https://github.com/EtharaOrion/trinity.git"
CANONICAL_REMOTE_ENV = "TRINITY_CANONICAL_REMOTE"

# Root report to the machine directory that must carry its signed disposition record.
REPORT_HARNESS: dict[str, str] = {
    "VERDICT.md": ".audit",
    "EDICT.md": ".seed",
}
REPORT_INSTRUMENT: dict[str, str] = {"VERDICT.md": "CRUCIBLE", "EDICT.md": "FORGE"}
DISPOSITION_RECORD = "disposition.json"
DISPOSITION_ENVELOPE = "disposition.json.dsse"
DISPOSITION_SCHEMA = "trinity.release-disposition/v2"
DISPOSITION_PAYLOAD_TYPES = {
    "FORGE": "application/vnd.trinity.release-disposition.forge+json",
    "CRUCIBLE": "application/vnd.trinity.release-disposition.crucible+json",
}
DISPOSITION_ROLE = "gate_approver"
DISPOSITION_FIELDS: frozenset[str] = frozenset(
    {
        "disposition",
        "schema",
        "instrument",
        "project_id",
        "repository_id",
        "snapshot_digest",
        "bundle_set_digest",
        "candidate_commit",
        "verifier_sha",
        "issued_at",
        "expires_at",
        "producer",
        "approver",
    }
)
BOUND_DISPOSITIONS: frozenset[str] = frozenset({"SHIP", "SHIP:INFERRED", "CURRENT"})

TRUST_ROOT_PATH = ".memory/roots.yaml"
ALLOWED_SIGNERS_PATH = ".memory/allowed_signers"
TRUSTED_ROOT_VERSION_PATH = ".memory/trusted-root-version"

MACHINE_ROOTS: tuple[str, ...] = (".audit", ".seed", ".memory")
INSTRUMENT_PREFIXES: tuple[str, ...] = ("g_", "check_", "inst_", "instrument_")
SANDBOX_NAMES: frozenset[str] = frozenset({"sandbox_state", "sandbox_available", "hermetic"})
GAP_CALLEES: frozenset[str] = frozenset({"gap", "coverage_gap", "_gap"})
LIVE_MARKERS: tuple[str, ...] = ("finding", "fire")

SIGNOFF_FILE = "SIGNOFF.md"
SIGNOFF_SUFFIX = ".signoff"
SIGNOFF_LINE = re.compile(r"SIGNOFF", re.I)
SHIP_TOKEN = re.compile(r"\bSHIP\b")

WORKFLOW_HISTORY_DEPTH = 50

GIT_TIMEOUT_SECONDS = 30.0
GITLINK_MODE = "160000"
GIT_OBJECT_ID = re.compile(r"\A[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
H2 = re.compile(r"^##\s+(.+?)\s*$")
DISPOSITION_TOKEN = re.compile(r"[A-Z][A-Z_:]{2,}")
CITED_MACHINE_PATH = re.compile(r"`((?:\.audit|\.seed|\.memory)/[^`\s]*)`")


# ---- small helpers -------------------------------------------------------------


def finding(path: object, line: int, message: str, code: str) -> Finding:
    return Finding(code, Severity.ERROR, str(path), line, message)


def advisory(path: object, line: int, message: str, code: str) -> Finding:
    return Finding(code, Severity.ADVISORY, str(path), line, message)


@dataclass(frozen=True, slots=True)
class GitResult:
    returncode: int | None
    stdout: str
    stderr: str
    failure: str | None

    @property
    def ok(self) -> bool:
        return self.failure is None and self.returncode == 0


def run_git(argv: list[str], *, env: dict[str, str] | None = None) -> GitResult:
    try:
        completed = subprocess.run(
            ["git", *argv],
            capture_output=True,
            check=False,
            shell=False,
            timeout=GIT_TIMEOUT_SECONDS,
            env=env,
        )
    except FileNotFoundError:
        return GitResult(None, "", "", "git executable is absent")
    except subprocess.TimeoutExpired:
        return GitResult(None, "", "", f"git exceeded the {GIT_TIMEOUT_SECONDS:g} second timeout")
    except OSError as exc:
        return GitResult(None, "", "", f"could not execute git: {exc}")
    try:
        return GitResult(
            completed.returncode,
            completed.stdout.decode("utf-8"),
            completed.stderr.decode("utf-8"),
            None,
        )
    except UnicodeDecodeError:
        return GitResult(completed.returncode, "", "", "git emitted output that was not UTF-8")


def git_detail(result: GitResult) -> str:
    if result.failure is not None:
        return result.failure
    return result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"


def git_head(root_path: Path) -> str | None:
    result = run_git(["-C", str(root_path), "rev-parse", "--verify", "HEAD^{commit}"])
    if not result.ok:
        return None
    candidate = result.stdout.strip()
    return candidate if GIT_OBJECT_ID.fullmatch(candidate) else None


def git_head_author_email(root_path: Path) -> str | None:
    result = run_git(["-C", str(root_path), "log", "-1", "--format=%ae", "HEAD"])
    if not result.ok:
        return None
    return result.stdout.strip() or None


def git_gitlink(root_path: Path, name: str) -> str | None:
    """Return the commit recorded in the index for a submodule gitlink, or None."""

    result = run_git(["-C", str(root_path), "ls-files", "--stage", "--", name])
    if not result.ok:
        return None
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == GITLINK_MODE and parts[3] == name:  # noqa: PLR2004
            return parts[1]
    return None


def git_tracked_paths(root_path: Path) -> set[str] | None:
    result = run_git(["-C", str(root_path), "ls-tree", "-r", "HEAD", "--name-only"])
    if not result.ok:
        return None
    return {line for line in result.stdout.splitlines() if line}


def git_gitlinks(root_path: Path) -> set[str]:
    """Return every submodule path recorded at HEAD.

    ``ls-tree -r`` recurses through trees and stops at a gitlink, which is a commit object,
    so a submodule contributes its own name to the tracked set and nothing beneath it. A
    caller testing membership for a path inside a roster root therefore has to cross the
    boundary itself, and this is the roster it crosses on.
    """

    result = run_git(["-C", str(root_path), "ls-tree", "-r", "HEAD"])
    if not result.ok:
        return set()
    links: set[str] = set()
    for line in result.stdout.splitlines():
        metadata, _, name = line.partition("\t")
        if name and metadata.split()[:1] == [GITLINK_MODE]:
            links.add(name)
    return links


def git_submodule_tracked(root_path: Path, link: str) -> set[str] | None:
    """Return the paths committed at a submodule's own HEAD, or None when it is unlistable.

    Git ascends out of an uninitialized submodule directory and answers from the parent
    repository, so an unguarded listing would hand back the parent tree and refuse every
    citation inside the submodule. The working tree root is checked against the gitlink
    before the listing is trusted.
    """

    path = root_path / link
    toplevel = run_git(["-C", str(path), "rev-parse", "--show-toplevel"])
    if not toplevel.ok:
        return None
    try:
        answered = Path(toplevel.stdout.strip()).resolve()
        expected = path.resolve()
    except OSError:
        return None
    if answered != expected:
        return None
    return git_tracked_paths(path)


def owning_gitlink(path: str, gitlinks: set[str]) -> str | None:
    """Return the innermost submodule containing ``path``, or None when the parent owns it."""

    owner: str | None = None
    for link in gitlinks:
        if (path == link or path.startswith(link + "/")) and (
            owner is None or len(link) > len(owner)
        ):
            owner = link
    return owner


def tracked_contains(tracked: set[str], path: str) -> bool:
    """True when ``path`` names a committed file or a directory holding one."""

    if path.endswith("/"):
        return any(item.startswith(path) for item in tracked)
    return path in tracked or any(item.startswith(path + "/") for item in tracked)


def read_text(path: Path) -> str:
    with path.open(encoding="utf-8") as fh:
        return fh.read()


def disposition_of(text: str) -> str | None:
    """Return the first uppercase token on the first non-empty line under ``## Disposition``."""

    in_section = False
    for line in text.split("\n"):
        heading = H2.match(line)
        if heading is not None:
            in_section = heading.group(1).strip().lower() == "disposition"
            continue
        if not in_section or not line.strip():
            continue
        match = DISPOSITION_TOKEN.search(line)
        return match.group(0).rstrip(":") if match is not None else None
    return None


# ---- 1. disposition binding ----------------------------------------------------


def _load_record(record_path: Path) -> tuple[dict[str, str] | None, bytes | None, str | None]:
    try:
        document = record_path.read_bytes()
    except FileNotFoundError:
        return None, None, None
    except OSError as exc:
        return None, None, f"disposition record is unreadable: {exc}"
    try:
        value = json.loads(document.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return None, document, f"disposition record is not JSON: {exc}"
    if not isinstance(value, dict):
        return None, document, "disposition record must be a JSON object"
    keys = set(value)
    if keys != DISPOSITION_FIELDS:
        missing = sorted(DISPOSITION_FIELDS - keys)
        extra = sorted(keys - DISPOSITION_FIELDS)
        return None, document, f"disposition record fields differ: missing {missing}, extra {extra}"
    if not all(isinstance(item, str) and item for item in value.values()):
        return None, document, "every disposition record field must be a non-empty string"
    return {key: str(item) for key, item in value.items()}, document, None


def _verify_disposition_envelope(
    root_path: Path,
    *,
    envelope_path: Path,
    record_bytes: bytes,
    record: dict[str, str],
    evaluation_time: datetime,
    backend: SignatureBackend,
    instrument: str,
) -> str | None:
    """Return a refusal detail, or None when the envelope binds the record."""

    try:
        document = envelope_path.read_bytes()
    except OSError as exc:
        return f"disposition envelope is missing or unreadable: {exc}"
    parsed = attest_dsse.parse_envelope(document)
    if parsed.envelope is None:
        return f"disposition envelope is malformed: {parsed.detail}"
    envelope = parsed.envelope
    if envelope.payload != record_bytes:
        return "disposition envelope payload does not equal the disposition record bytes"
    allowed_signers = root_path / ALLOWED_SIGNERS_PATH
    if not allowed_signers.is_file():
        return f"{ALLOWED_SIGNERS_PATH} is absent, so no signer can be verified"
    outcome = attest_dsse.verify_envelope(
        backend,
        envelope,
        expected_payload_type=DISPOSITION_PAYLOAD_TYPES[instrument],
        allowed_signers_path=allowed_signers,
        evaluation_time=evaluation_time,
    )
    if not outcome.accepted:
        return f"disposition signature refused: {outcome.detail}"
    version_path = root_path / TRUSTED_ROOT_VERSION_PATH
    try:
        trusted_version = int(read_text(version_path).strip())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return f"trusted root version is unreadable or malformed: {exc}"
    authorization = attest_trustroot.authorize(
        root_path / TRUST_ROOT_PATH,
        role_name=DISPOSITION_ROLE,
        verified_principals=outcome.principals,
        evaluation_time=evaluation_time,
        trusted_version=trusted_version,
        producer_principal=record["producer"],
    )
    if not authorization.accepted:
        return f"disposition signer is not authorized: {authorization.detail}"
    if record["approver"] not in authorization.principals:
        return "disposition approver is not among the verified authorized signers"
    return None


def _binds_head(root_path: Path, tree_sha: str, head: str) -> bool:
    """Bind HEAD to an ancestor reached only through commits that seal gate artifacts."""

    if tree_sha == head:
        return True
    if GIT_OBJECT_ID.fullmatch(tree_sha) is None:
        return False
    ancestor = run_git(["-C", str(root_path), "merge-base", "--is-ancestor", tree_sha, head])
    if not ancestor.ok:
        return False
    changed = run_git(["-C", str(root_path), "diff", "--name-only", f"{tree_sha}..{head}"])
    if not changed.ok:
        return False
    return seals_only(line for line in changed.stdout.splitlines() if line)


def check_disposition_binding(
    root: str,
    evaluation_time: datetime | None = None,
    backend: SignatureBackend | None = None,
) -> list[Finding]:
    """A SHIP, SHIP:INFERRED, or CURRENT report must quote a signed disposition record."""

    root_path = Path(root)
    verifier = SshKeygenBackend() if backend is None else backend
    instant = datetime.now(UTC) if evaluation_time is None else evaluation_time
    out: list[Finding] = []
    head = git_head(root_path)
    head_author = git_head_author_email(root_path)
    for report, harness in REPORT_HARNESS.items():
        report_path = root_path / report
        if not report_path.is_file():
            continue
        try:
            text = read_text(report_path)
        except (OSError, UnicodeDecodeError) as exc:
            out.append(finding(report_path, 0, f"root report is unreadable: {exc}", SAB_READ_ERROR))
            continue
        disposition = disposition_of(text)
        if disposition not in BOUND_DISPOSITIONS:
            continue
        record_path = root_path / harness / DISPOSITION_RECORD
        record, record_bytes, detail = _load_record(record_path)
        if record is None and record_bytes is None and detail is None:
            out.append(
                finding(
                    report_path,
                    0,
                    f"{report} claims {disposition} with no {harness}/{DISPOSITION_RECORD}; "
                    "a disposition is a signed record, never prose",
                    SAB_DISPOSITION_UNBOUND,
                )
            )
            continue
        if record is None or record_bytes is None:
            out.append(finding(record_path, 0, detail or "malformed", SAB_DISPOSITION_FORGED))
            continue
        problems: list[str] = []
        instrument = REPORT_INSTRUMENT[report]
        if record["schema"] != DISPOSITION_SCHEMA or record["instrument"] != instrument:
            problems.append("disposition schema or instrument domain is wrong")
        if record["disposition"] != disposition:
            problems.append(
                f"report says {disposition} while the record says {record['disposition']}"
            )
        if head is None:
            problems.append("HEAD cannot be resolved, so candidate_commit cannot be bound")
        elif not _binds_head(root_path, record["candidate_commit"], head):
            problems.append(
                f"candidate_commit {record['candidate_commit'][:12]} is neither HEAD "
                f"{head[:12]} nor the "
                "parent of a sealing commit that adds only disposition records"
            )
        for digest_field in ("snapshot_digest", "bundle_set_digest"):
            if HEX64.fullmatch(record[digest_field]) is None:
                problems.append(f"{digest_field} is not a sha256 hex digest")
        verifier_commit = git_gitlink(root_path, TRINITY_DIR)
        if verifier_commit is None:
            problems.append("verifier_sha cannot be checked because the trinity gitlink is absent")
        elif record["verifier_sha"] != verifier_commit:
            problems.append(
                f"verifier_sha {record['verifier_sha'][:12]} does not match the trinity gitlink "
                f"{verifier_commit[:12]}"
            )
        try:
            issued = datetime.fromisoformat(record["issued_at"].removesuffix("Z") + "+00:00")
            expires = datetime.fromisoformat(record["expires_at"].removesuffix("Z") + "+00:00")
            if not record["issued_at"].endswith("Z") or not record["expires_at"].endswith("Z"):
                raise ValueError("timestamps are not UTC")
            if not issued <= instant < expires:
                problems.append("issued_at and expires_at do not contain the evaluation time")
        except (OverflowError, ValueError):
            problems.append("issued_at or expires_at is not a valid RFC 3339 UTC timestamp")
        if record["approver"] == record["producer"]:
            problems.append("approver equals producer")
        if head_author is not None and record["approver"] == head_author:
            problems.append(f"approver equals the HEAD author {head_author}")
        if not problems:
            envelope_detail = _verify_disposition_envelope(
                root_path,
                envelope_path=root_path / harness / DISPOSITION_ENVELOPE,
                record_bytes=record_bytes,
                record=record,
                evaluation_time=instant,
                backend=verifier,
                instrument=instrument,
            )
            if envelope_detail is not None:
                problems.append(envelope_detail)
        if problems:
            out.append(
                finding(
                    record_path,
                    0,
                    f"{report} {disposition} is forged: " + "; ".join(problems),
                    SAB_DISPOSITION_FORGED,
                )
            )
    return out


# ---- 2. instrument liveness ----------------------------------------------------


def _callee_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_inert_return(value: ast.expr | None) -> bool:
    if value is None or (isinstance(value, ast.Constant)):
        return True
    if isinstance(value, ast.List | ast.Tuple | ast.Dict) and not _container_items(value):
        return True
    if isinstance(value, ast.Call):
        callee = _callee_name(value.func)
        return callee is not None and callee in GAP_CALLEES
    return False


def _container_items(value: ast.List | ast.Tuple | ast.Dict) -> list[ast.expr]:
    if isinstance(value, ast.Dict):
        return [item for item in value.values if item is not None]
    return list(value.elts)


def _has_false_literal(value: ast.expr | None) -> bool:
    if isinstance(value, ast.Constant):
        return value.value is False
    if isinstance(value, ast.Dict):
        return any(_has_false_literal(item) for item in value.values if item is not None)
    return False


def _mentions_live_marker(node: ast.AST) -> bool:
    for child in ast.walk(node):
        name: str | None = None
        if isinstance(child, ast.Name):
            name = child.id
        elif isinstance(child, ast.Attribute):
            name = child.attr
        if name is not None and any(marker in name.lower() for marker in LIVE_MARKERS):
            return True
    return False


def _own_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    """Nodes belonging to this function's own scope, excluding nested definitions."""

    nodes: list[ast.AST] = []
    stack: list[ast.AST] = list(function.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef):
            continue
        nodes.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return nodes


def _own_returns(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Return]:
    return [node for node in _own_nodes(function) if isinstance(node, ast.Return)]


def _exercises_a_decision(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """A raise, an assert, or a call to anything but a gap helper can vary the outcome."""

    for node in _own_nodes(function):
        if isinstance(node, ast.Raise | ast.Assert):
            return True
        if isinstance(node, ast.Call) and _callee_name(node.func) not in GAP_CALLEES:
            return True
    return False


def inert_functions(tree: ast.AST) -> list[tuple[str, int, str]]:
    """Return (name, line, reason) for every function that can never produce a finding."""

    out: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        returns = _own_returns(node)
        if node.name in SANDBOX_NAMES:
            has_call = any(isinstance(child, ast.Call) for child in ast.walk(node))
            literal_false = any(_has_false_literal(item.value) for item in returns)
            if literal_false and not has_call:
                out.append(
                    (
                        node.name,
                        node.lineno,
                        "returns a literal unavailable state without probing anything",
                    )
                )
            continue
        if not node.name.startswith(INSTRUMENT_PREFIXES) or not returns:
            continue
        if (
            all(_is_inert_return(item.value) for item in returns)
            and not _mentions_live_marker(node)
            and not _exercises_a_decision(node)
        ):
            out.append(
                (
                    node.name,
                    node.lineno,
                    "every return is a gap, a constant, or nothing, and no finding can fire",
                )
            )
    return out


def check_instrument_liveness(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """An instrument whose every branch yields a coverage gap certifies nothing."""

    root_path = Path(root)
    out: list[Finding] = []
    for harness in (".audit", ".seed"):
        directory = root_path / harness
        if not directory.is_dir():
            continue
        for source in sorted(directory.rglob("*.py")):
            try:
                tree = ast.parse(read_text(source), filename=str(source))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                out.append(
                    finding(source, 0, f"instrument source cannot be parsed: {exc}", SAB_READ_ERROR)
                )
                continue
            for name, line, reason in inert_functions(tree):
                out.append(
                    finding(
                        source,
                        line,
                        f"instrument {name} is inert: {reason}",
                        SAB_INERT_INSTRUMENT,
                    )
                )
    return out


# ---- 3. reports cite committed files ------------------------------------------


def cited_machine_paths(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for number, line in enumerate(text.split("\n"), start=1):
        for raw in CITED_MACHINE_PATH.findall(line):
            path = re.sub(r":[0-9][0-9,-]*$", "", raw).rstrip(".,;")
            out.append((number, path))
    return out


def check_audit_cites_committed_files(
    root: str, _evaluation_time: datetime | None = None
) -> list[Finding]:
    """Every machine-root path a report cites must exist in HEAD, not only on disk.

    A machine root may itself be a roster submodule, and ``.memory/`` always is, so the
    parent HEAD carries the gitlink alone and never one byte beneath it. A citation inside
    a gitlink is resolved against that submodule's own HEAD rather than against the parent
    tree, because holding a parent to a tree that cannot contain the path would refuse every
    conforming project. A submodule the clone never initialized is unverifiable rather than
    uncommitted, and unverifiable is an advisory the ceiling does not read.
    """

    root_path = Path(root)
    out: list[Finding] = []
    tracked: set[str] | None = None
    gitlinks: set[str] = set()
    inner: dict[str, set[str] | None] = {}
    for report in REPORT_HARNESS:
        report_path = root_path / report
        if not report_path.is_file():
            continue
        try:
            text = read_text(report_path)
        except (OSError, UnicodeDecodeError) as exc:
            out.append(finding(report_path, 0, f"root report is unreadable: {exc}", SAB_READ_ERROR))
            continue
        cited = cited_machine_paths(text)
        if not cited:
            continue
        if tracked is None:
            tracked = git_tracked_paths(root_path)
            if tracked is None:
                return [
                    finding(
                        root_path,
                        0,
                        "HEAD tree cannot be listed, so cited paths cannot be verified",
                        SAB_READ_ERROR,
                    )
                ]
            gitlinks = git_gitlinks(root_path)
        for line, path in cited:
            link = owning_gitlink(path.rstrip("/"), gitlinks)
            if link is None:
                if not tracked_contains(tracked, path):
                    out.append(
                        finding(
                            report_path,
                            line,
                            f"{report} cites {path}, which is not committed at HEAD",
                            SAB_AUDIT_UNCOMMITTED,
                        )
                    )
                continue
            if path.rstrip("/") == link:
                continue
            if link not in inner:
                inner[link] = git_submodule_tracked(root_path, link)
            committed = inner[link]
            if committed is None:
                out.append(
                    advisory(
                        report_path,
                        line,
                        f"{report} cites {path}, and the {link} submodule has no listable HEAD "
                        "in this clone, so the citation cannot be verified",
                        SAB_SUBMODULE_UNVERIFIED,
                    )
                )
                continue
            if not tracked_contains(committed, path[len(link) + 1 :]):
                out.append(
                    finding(
                        report_path,
                        line,
                        f"{report} cites {path}, which is not committed at the HEAD of the "
                        f"{link} submodule",
                        SAB_AUDIT_UNCOMMITTED,
                    )
                )
    return out


# ---- 4. canonical submodule remote ---------------------------------------------


def normalize_remote(url: str) -> str:
    value = url.strip().lower()
    value = re.sub(r"^[a-z][a-z0-9+.-]*://", "", value)
    value = re.sub(r"^[^@/:]+@", "", value)
    if "://" not in url and re.match(r"^[^/]+:[^/]", value):
        value = value.replace(":", "/", 1)
    value = re.sub(r"\.git$", "", value.rstrip("/"))
    return value.rstrip("/")


def canonical_remote() -> str:
    return os.environ.get(CANONICAL_REMOTE_ENV) or CANONICAL_TRINITY_REMOTE


def gitmodules_section(text: str, wanted: str) -> dict[str, str]:
    section = layout.section_for(layout.parse_gitmodules(text)[0], wanted)
    return dict(section.keys) if section is not None else {}


def check_submodule_canonical_remote(
    root: str, _evaluation_time: datetime | None = None
) -> list[Finding]:
    """The vendored contracts must come from the canonical Trinity, at a commit on its main."""

    root_path = Path(root)
    gitmodules = root_path / ".gitmodules"
    try:
        text = read_text(gitmodules)
    except (OSError, UnicodeDecodeError) as exc:
        return [
            finding(gitmodules, 0, f".gitmodules is unreadable: {exc}", SAB_SUBMODULE_REMOTE),
        ]
    section = gitmodules_section(text, TRINITY_DIR)
    url = section.get("url", "")
    canonical = canonical_remote()
    if not url:
        return [
            finding(gitmodules, 0, ".gitmodules registers no url for trinity", SAB_SUBMODULE_REMOTE)
        ]
    if normalize_remote(url) != normalize_remote(canonical):
        return [
            finding(
                gitmodules,
                0,
                f"trinity submodule url {url!r} is not the canonical remote {canonical!r}",
                SAB_SUBMODULE_REMOTE,
            )
        ]
    submodule = root_path / TRINITY_DIR
    checked_out = git_head(submodule)
    if checked_out is None:
        return [
            finding(submodule, 0, "trinity checkout has no resolvable HEAD", SAB_SUBMODULE_REMOTE)
        ]
    fetched = run_git(
        [
            "-C",
            str(submodule),
            "fetch",
            "--no-tags",
            "--quiet",
            canonical,
            f"refs/heads/{TRINITY_BRANCH}",
        ]
    )
    if not fetched.ok:
        return [
            advisory(
                submodule,
                0,
                f"canonical trinity main could not be fetched, so ancestry is unverified: "
                f"{git_detail(fetched)}",
                SAB_SUBMODULE_UNVERIFIED,
            )
        ]
    tip = run_git(["-C", str(submodule), "rev-parse", "--verify", "FETCH_HEAD^{commit}"])
    tip_sha = tip.stdout.strip()
    if not tip.ok or GIT_OBJECT_ID.fullmatch(tip_sha) is None:
        return [
            advisory(
                submodule,
                0,
                f"fetched canonical tip is unparseable: {git_detail(tip)}",
                SAB_SUBMODULE_UNVERIFIED,
            )
        ]
    if checked_out == tip_sha:
        return []
    ancestry = run_git(["-C", str(submodule), "merge-base", "--is-ancestor", checked_out, tip_sha])
    if ancestry.failure is not None:
        return [advisory(submodule, 0, ancestry.failure, SAB_SUBMODULE_UNVERIFIED)]
    if ancestry.returncode == 0:
        return []
    if ancestry.returncode == 1:
        return [
            finding(
                submodule,
                0,
                f"vendored trinity commit {checked_out[:12]} is not on canonical "
                f"{TRINITY_BRANCH} (tip {tip_sha[:12]}); the contracts in force are forked",
                SAB_SUBMODULE_OFF_MAIN,
            )
        ]
    return [advisory(submodule, 0, git_detail(ancestry), SAB_SUBMODULE_UNVERIFIED)]


# ---- 5. typed sign-off ---------------------------------------------------------


def _has_envelope_sibling(path: Path) -> bool:
    return any(
        Path(f"{path}{suffix}").is_file() for suffix in (".dsse", ".dsse.json", ".json.dsse")
    )


def check_no_typed_signoff(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """A typed name in a sign-off file is not a signature and never raises a disposition."""

    root_path = Path(root)
    out: list[Finding] = []
    signoffs: list[Path] = []
    try:
        for entry in sorted(root_path.iterdir()):
            if entry.is_file() and (
                entry.name == SIGNOFF_FILE or entry.name.endswith(SIGNOFF_SUFFIX)
            ):
                signoffs.append(entry)
    except OSError as exc:
        return [finding(root_path, 0, f"root cannot be listed: {exc}", SAB_READ_ERROR)]
    unsigned = [path for path in signoffs if not _has_envelope_sibling(path)]
    for path in unsigned:
        out.append(
            finding(
                path,
                0,
                f"{path.name} carries acceptance without a DSSE envelope sibling; "
                "a typed name is not a signature",
                SAB_TYPED_SIGNOFF,
            )
        )
    if signoffs and not unsigned:
        return out
    for report in REPORT_HARNESS:
        report_path = root_path / report
        if not report_path.is_file():
            continue
        try:
            text = read_text(report_path)
        except (OSError, UnicodeDecodeError) as exc:
            out.append(finding(report_path, 0, f"root report is unreadable: {exc}", SAB_READ_ERROR))
            continue
        for number, line in enumerate(text.split("\n"), start=1):
            if SIGNOFF_LINE.search(line) and SHIP_TOKEN.search(line):
                out.append(
                    finding(
                        report_path,
                        number,
                        f"{report} rests SHIP on a sign-off that no DSSE envelope backs",
                        SAB_TYPED_SIGNOFF,
                    )
                )
    return out


# ---- 6. workflow tamper --------------------------------------------------------


def _is_governance_path(path: str) -> bool:
    exact = {
        ".github/CODEOWNERS",
        ".gitmodules",
        ".memory/allowed_signers",
        ".memory/roots.yaml",
        ".memory/trusted-root-version",
    }
    return (
        path in exact
        or path.startswith(".github/workflows/")
        or path == ".memory/root-rotation"
        or path.startswith(".memory/root-rotation/")
    )


GATE_RECEIPT_PREFIXES: tuple[str, ...] = (
    ".audit/gate-receipts/",
    ".seed/gate-receipts/",
    ".memory/gate-receipts/",
)


def _is_subject_path(path: str) -> bool:
    """A path a gate bypass would protect: a root report, a disposition record, or bundle bytes."""
    if _is_governance_path(path):
        return False
    if path in REPORT_HARNESS:
        return True
    if path.startswith(GATE_RECEIPT_PREFIXES):
        return False
    if path in {".audit/" + DISPOSITION_RECORD, ".seed/" + DISPOSITION_RECORD}:
        return True
    if path.endswith((".dsse", ".sig")) and path.startswith((".audit/", ".seed/", ".memory/")):
        return True
    if path.startswith((".audit/verdicts/", ".audit/attestations/", ".seed/contract.")):
        return True
    for lane in ("samples/", "delivery/", "staging/"):
        if path.startswith(lane) and path != lane + "README.md":
            return True
    return False


def _commit_shows_intent(root_path: Path, commit: str, paths: list[str]) -> bool:
    """Bypass syntax on a gate step, or a SHIP token entering a root report, is intent."""
    for path in paths:
        if not path.startswith(".github/workflows/") and path not in REPORT_HARNESS:
            continue
        shown = run_git(["-C", str(root_path), "show", f"{commit}:{path}"])
        if not shown.ok:
            continue
        if path.startswith(".github/workflows/"):
            if bypasses_a_gate(shown.stdout):
                return True
            continue
        added = run_git(["-C", str(root_path), "show", "--format=", "-U0", commit, "--", path])
        if added.ok and any(
            line.startswith("+") and not line.startswith("+++") and SHIP_TOKEN.search(line)
            for line in added.stdout.splitlines()
        ):
            return True
    return False


def _remediated_by_split_commits(
    governance: list[str], subjects: list[str], later: list[list[str]]
) -> bool:
    """Every flagged path landed again in a later commit that touched only its own class."""
    governance_only = {
        path for paths in later if not any(_is_subject_path(p) for p in paths) for path in paths
    }
    subject_only = {
        path for paths in later if not any(_is_governance_path(p) for p in paths) for path in paths
    }
    return all(path in governance_only for path in governance) and all(
        path in subject_only for path in subjects
    )


def check_workflow_tamper(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """A commit that edits CI and a gate subject together is suspicion; with a bypass, a block."""

    root_path = Path(root)
    log = run_git(
        ["-C", str(root_path), "log", f"-n{WORKFLOW_HISTORY_DEPTH}", "--format=%H", "HEAD"]
    )
    if not log.ok:
        return [finding(root_path, 0, f"history cannot be read: {git_detail(log)}", SAB_READ_ERROR)]
    out: list[Finding] = []
    changed_by_commit: list[tuple[str, list[str]]] = []
    for commit in log.stdout.split():
        changed = run_git(
            ["-C", str(root_path), "diff-tree", "--no-commit-id", "--name-only", "-r", commit]
        )
        if not changed.ok:
            out.append(
                finding(
                    root_path,
                    0,
                    f"commit {commit[:12]} cannot be inspected: {git_detail(changed)}",
                    SAB_READ_ERROR,
                )
            )
            continue
        changed_by_commit.append((commit, [line for line in changed.stdout.splitlines() if line]))
    for index, (commit, paths) in enumerate(changed_by_commit):
        governance = sorted(path for path in paths if _is_governance_path(path))
        subjects = sorted(path for path in paths if _is_subject_path(path))
        if not (governance and subjects):
            continue
        later = [later_paths for _later, later_paths in changed_by_commit[:index]]
        if _commit_shows_intent(root_path, commit, paths):
            code, recovery = SAB_WORKFLOW_TAMPER, WORKFLOW_TAMPER_RECOVERY
        elif _remediated_by_split_commits(governance, subjects, later):
            continue
        else:
            code, recovery = SAB_WORKFLOW_TAMPER_SUSPECT, WORKFLOW_TAMPER_SUSPECT_RECOVERY
        out.append(
            finding(
                root_path,
                0,
                f"commit {commit[:12]} edits {', '.join(governance)} together with "
                f"{', '.join(subjects[:5])}; {recovery}",
                code,
            )
        )
    return out


# ---- 7. dirty tree at gate -----------------------------------------------------


def check_dirty_tree_at_gate(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """Uncommitted bytes are unreviewable, except the gate's and the signers' own outputs."""

    root_path = Path(root)
    status = run_git(
        [
            "-C",
            str(root_path),
            "-c",
            "core.quotePath=true",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ]
    )
    if not status.ok:
        return [
            finding(
                root_path, 0, f"working tree state is unknown: {git_detail(status)}", SAB_READ_ERROR
            )
        ]
    entries = [line for line in status.stdout.splitlines() if line and line[3:].strip('"') != ""]
    entries = [line for line in entries if not is_sealing_path(line[3:].strip('"'))]
    if not entries:
        return []
    sample = ", ".join(line[3:] for line in entries[:5])
    return [
        finding(
            root_path,
            0,
            f"working tree is dirty at gate time ({len(entries)} entries: {sample}); "
            "commit the phase work before the gate runs; only root reports, receipts, "
            "disposition records, install receipts, and the sentinel ledger may stay uncommitted",
            SAB_DIRTY_TREE,
        )
    ]


# ---- registry and CLI ----------------------------------------------------------


CHECKS: list[tuple[str, SabotageCheck]] = [
    ("sabotage_disposition_binding", check_disposition_binding),
    ("sabotage_instrument_liveness", check_instrument_liveness),
    ("sabotage_audit_cites_committed_files", check_audit_cites_committed_files),
    ("sabotage_submodule_canonical_remote", check_submodule_canonical_remote),
    ("sabotage_no_typed_signoff", check_no_typed_signoff),
    ("sabotage_workflow_tamper", check_workflow_tamper),
    ("sabotage_dirty_tree_at_gate", check_dirty_tree_at_gate),
]


def run_checks(root: str, evaluation_time: datetime | None = None) -> list[Finding]:
    out: list[Finding] = []
    for _name, check in CHECKS:
        out.extend(check(root, evaluation_time))
    return out


def _has_errors(findings: Iterable[Finding]) -> bool:
    return any(item.severity is Severity.ERROR for item in findings)


def main(argv: list[str]) -> int:
    arguments = [item for item in argv if not item.startswith("--")]
    as_json = "--json" in argv
    if len(arguments) != 1:
        print("usage: sabotage.py [--json] <parent-root>", file=sys.stderr)
        return 2
    try:
        project_root = invocation_root()
        root = resolve_project_path(
            arguments[0],
            project_root=project_root,
            description="parent root",
            must_exist=True,
        )
    except ProjectPathError as exc:
        print(f"sabotage refused: {exc}", file=sys.stderr)
        return 2
    findings = run_checks(str(root), datetime.now(UTC))
    findings = [
        Finding(
            item.code,
            item.severity,
            display_project_path(item.path, project_root=project_root),
            item.line,
            redact_project_root(item.message, project_root=project_root),
        )
        for item in findings
    ]
    if as_json:
        print(serialize_findings(findings))
    else:
        for item in findings:
            print(f"{item.code}: {render_finding(item)}")
        if not findings:
            print("sabotage: clean")
    return 1 if _has_errors(findings) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
