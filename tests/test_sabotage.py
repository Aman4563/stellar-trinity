"""Both-halves fixtures for every anti-sabotage refusal in tools/sabotage.py."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tools import gate
from tools._findings import Severity
from tools.attest.backend import VerificationFailureReason, VerificationResult
from tools.attest.canonical import JSONValue, canonicalize
from tools.attest.dsse import Envelope, Signature

from tests.bite_shared.registration import bite
from tests.harness_imports import load_harness
from tests.parent_fixtures import write_clean_parent

sabotage = load_harness("sabotage")

EVALUATION_TIME = datetime(2027, 1, 1, tzinfo=UTC)
APPROVER = "approver@trinity.test"
PRODUCER = "producer@trinity.test"
HUMAN = "Human Operator"
HUMAN_EMAIL = "human@trinity.test"
SHA256_ZERO = "0" * 64


class StubBackend:
    keyid_scheme = "test-signature:v1"

    def __init__(self, principal: str = APPROVER) -> None:
        self.principal = principal

    def sign(self, payload: bytes, *, key_path: Path) -> bytes:
        del payload, key_path
        raise AssertionError("verification stub cannot sign")

    def verify(
        self,
        payload: bytes,
        *,
        signature_path: Path,
        allowed_signers_path: Path,
        evaluation_time: datetime | None = None,
    ) -> VerificationResult:
        del payload, allowed_signers_path, evaluation_time
        if signature_path.read_bytes() != b"test-signature":
            return VerificationResult.failure(
                VerificationFailureReason.SIGNATURE_INVALID,
                "stub signature mismatch",
            )
        return VerificationResult.success(self.principal)


def git(argv: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": HUMAN,
        "GIT_AUTHOR_EMAIL": HUMAN_EMAIL,
        "GIT_COMMITTER_NAME": HUMAN,
        "GIT_COMMITTER_EMAIL": HUMAN_EMAIL,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    if env:
        environment.update(env)
    completed = subprocess.run(
        ["git", *argv],
        cwd=cwd,
        capture_output=True,
        check=False,
        env=environment,
        shell=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return completed.stdout.strip()


def commit_all(root: Path, message: str = "commit") -> str:
    git(["add", "-A"], cwd=root)
    git(["-c", "commit.gpgsign=false", "commit", "-q", "-m", message], cwd=root)
    return git(["rev-parse", "HEAD"], cwd=root)


def make_canonical_trinity(tmp_path: Path) -> tuple[Path, Path]:
    """Return (bare canonical repo, working clone with one commit on main)."""

    bare = tmp_path / "canonical-trinity.git"
    git(["init", "-q", "--bare", "-b", "main", str(bare)], cwd=tmp_path)
    work = tmp_path / "trinity-work"
    git(["init", "-q", "-b", "main", str(work)], cwd=tmp_path)
    (work / "CRUCIBLE.md").write_text("contract\n", encoding="utf-8")
    commit_all(work, "trinity genesis")
    git(["remote", "add", "origin", str(bare)], cwd=work)
    git(["push", "-q", "origin", "main"], cwd=work)
    return bare, work


def make_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A committed, clean parent that vendors a local canonical trinity as a submodule."""

    bare, _work = make_canonical_trinity(tmp_path)
    monkeypatch.setenv(sabotage.CANONICAL_REMOTE_ENV, str(bare))
    root = tmp_path / "parent"
    write_clean_parent(root, lambda _: None)
    git(["init", "-q", "-b", "main"], cwd=root)
    git(
        ["-c", "protocol.file.allow=always", "submodule", "add", "-q", str(bare), "trinity"],
        cwd=root,
    )
    commit_all(root, "parent genesis")
    return root


def codes(findings: list[object]) -> set[str]:
    return {finding.code for finding in findings}  # type: ignore[attr-defined]


def trust_root(principal: str = APPROVER) -> dict[str, JSONValue]:
    return {
        "version": 7,
        "expires": "2030-01-01T00:00:00Z",
        "roles": [{"name": sabotage.DISPOSITION_ROLE, "threshold": 1}],
        "principals": [
            {
                "name": principal,
                "roles": [sabotage.DISPOSITION_ROLE],
                "expires": "2029-01-01T00:00:00Z",
            }
        ],
        "revocations": [],
    }


def write_trust(root: Path, principal: str = APPROVER) -> None:
    memory = root / ".memory"
    memory.mkdir(exist_ok=True)
    (memory / "roots.yaml").write_bytes(canonicalize(trust_root(principal)))
    (memory / "allowed_signers").write_text("test policy\n", encoding="utf-8")
    (memory / "trusted-root-version").write_text("7\n", encoding="utf-8")


def write_ship_report(root: Path, report: str = "VERDICT.md", token: str = "SHIP") -> None:
    (root / report).write_text(
        f"# Report\n\n## Executive summary\n\nText.\n\n## Disposition\n\n🟢 **{token}**\n\n"
        "## Findings\n\nNone.\n",
        encoding="utf-8",
    )


def disposition_record(root: Path, **overrides: str) -> dict[str, str]:
    record = {
        "schema": sabotage.DISPOSITION_SCHEMA,
        "instrument": "CRUCIBLE",
        "disposition": "SHIP",
        "project_id": "project-17",
        "repository_id": "424242",
        "snapshot_digest": SHA256_ZERO,
        "bundle_set_digest": SHA256_ZERO,
        "candidate_commit": git(["rev-parse", "HEAD"], cwd=root),
        "verifier_sha": git(["rev-parse", "HEAD"], cwd=root / "trinity"),
        "issued_at": "2026-09-16T00:00:00Z",
        "expires_at": "2028-09-16T00:00:00Z",
        "producer": PRODUCER,
        "approver": APPROVER,
    }
    record.update(overrides)
    return record


def seal(
    root: Path,
    record: dict[str, str],
    *,
    harness: str = ".audit",
    signature: bytes = b"test-signature",
    payload_override: bytes | None = None,
    extra_path: Path | None = None,
) -> None:
    directory = root / harness
    directory.mkdir(exist_ok=True)
    payload = json.dumps(record, sort_keys=True).encode("utf-8")
    (directory / sabotage.DISPOSITION_RECORD).write_bytes(payload)
    instrument = "FORGE" if harness == ".seed" else "CRUCIBLE"
    envelope = Envelope(
        payload_type=sabotage.DISPOSITION_PAYLOAD_TYPES[instrument],
        payload=payload if payload_override is None else payload_override,
        signatures=(Signature(sig=signature, keyid=StubBackend.keyid_scheme),),
    )
    (directory / sabotage.DISPOSITION_ENVELOPE).write_bytes(envelope.to_json())
    if extra_path is not None:
        extra_path.write_text("smuggled\n", encoding="utf-8")
    commit_all(root, "seal disposition")


def binding_codes(root: Path) -> set[str]:
    return codes(sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend()))


# ---- disposition binding -------------------------------------------------------


def test_clean_parent_has_no_sabotage_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)

    findings = sabotage.run_checks(str(root), EVALUATION_TIME)

    assert [finding.code for finding in findings] == []


def test_hold_disposition_needs_no_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_ship_report(root, token="HOLD:PILOT_REQUIRED")
    commit_all(root)

    assert binding_codes(root) == set()


@pytest.mark.parametrize(
    ("report", "token"),
    [("VERDICT.md", "SHIP"), ("EDICT.md", "SHIP:INFERRED")],
)
@bite("shared.md:A1")
def test_ship_prose_without_record_is_unbound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, report: str, token: str
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_ship_report(root, report, token)
    commit_all(root)

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_UNBOUND}
    assert report in findings[0].message


def test_signed_record_binding_head_parent_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root))

    assert binding_codes(root) == set()


def test_two_separate_instrument_sealing_commits_bind_same_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root, "VERDICT.md", "SHIP")
    write_ship_report(root, "EDICT.md", "SHIP")
    candidate = commit_all(root, "qualified candidate")
    forge = disposition_record(root, instrument="FORGE", candidate_commit=candidate)
    crucible = disposition_record(root, instrument="CRUCIBLE", candidate_commit=candidate)
    seal(root, forge, harness=".seed")
    seal(root, crucible, harness=".audit")

    assert binding_codes(root) == set()


def test_record_disposition_below_report_is_forged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root, disposition="HOLD"))

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "record says HOLD" in findings[0].message


def test_record_bound_to_a_stale_tree_is_forged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    record = disposition_record(root)
    (root / "samples").mkdir(exist_ok=True)
    (root / "samples" / "moved.txt").write_text("bytes moved after audit\n", encoding="utf-8")
    commit_all(root, "move the subject")
    seal(root, record)

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "candidate_commit" in findings[0].message


def test_record_binds_through_a_chain_of_gate_and_signing_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    record = disposition_record(root)
    receipts = root / ".audit" / "gate-receipts"
    receipts.mkdir(parents=True)
    (receipts / "run.json").write_text("{}\n", encoding="utf-8")
    (root / "TRACKING.md").write_text("tracker\n", encoding="utf-8")
    write_ship_report(root)
    commit_all(root, "report run output")
    (root / ".audit" / sabotage.DISPOSITION_RECORD).write_bytes(
        json.dumps(record, sort_keys=True).encode("utf-8")
    )
    commit_all(root, "promoted record")
    runtime = root / ".trinity-runtime"
    runtime.mkdir()
    (runtime / "producer.dsse").write_text("{}\n", encoding="utf-8")
    commit_all(root, "producer partial")
    seal(root, record)

    assert binding_codes(root) == set()
    assert sabotage.check_dirty_tree_at_gate(str(root)) == []


def test_sealing_commit_that_smuggles_other_bytes_is_forged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    # Root reports, the tracker, gate receipts, and the sentinel ledger may ride in a sealing
    # commit; any other byte, here a spine file, means the commit does not bind its parent.
    seal(root, disposition_record(root), extra_path=root / "README.md")

    assert binding_codes(root) == {sabotage.SAB_DISPOSITION_FORGED}


def test_record_naming_the_wrong_trinity_commit_is_forged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root, verifier_sha="f" * 40))

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "verifier_sha" in findings[0].message


@bite("shared.md:A2")
def test_self_approved_record_is_forged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root, principal=PRODUCER)
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root, approver=PRODUCER))

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "approver equals producer" in findings[0].message


def test_head_author_cannot_approve_own_disposition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root, principal=HUMAN_EMAIL)
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root, approver=HUMAN_EMAIL))

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "HEAD author" in findings[0].message


def test_bad_signature_is_forged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root), signature=b"forged-signature")

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "signature refused" in findings[0].message


def test_envelope_over_different_payload_is_forged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root)
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root), payload_override=b'{"disposition":"HOLD"}')

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "payload does not equal" in findings[0].message


def test_unauthorized_signer_is_forged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_trust(root, principal="someone-else@trinity.test")
    write_ship_report(root)
    commit_all(root, "audited state")
    seal(root, disposition_record(root))

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "not authorized" in findings[0].message


def test_malformed_record_is_forged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    write_ship_report(root)
    (root / ".audit").mkdir()
    (root / ".audit" / sabotage.DISPOSITION_RECORD).write_text(
        '{"disposition": "SHIP"}\n', encoding="utf-8"
    )
    commit_all(root)

    findings = sabotage.check_disposition_binding(str(root), EVALUATION_TIME, StubBackend())

    assert codes(findings) == {sabotage.SAB_DISPOSITION_FORGED}
    assert "fields differ" in findings[0].message


def test_disposition_token_parsing_matches_real_reports() -> None:
    cases = {
        "## Disposition\n\n🟢 **SHIP**\n": "SHIP",
        "## Disposition\n\n`BLOCK:INVALID_TASK` for the batch.\n": "BLOCK:INVALID_TASK",
        "## Disposition\n\n🟡 **`HOLD:PILOT_REQUIRED`**\n": "HOLD:PILOT_REQUIRED",
        "## Disposition\n\nThe disposition is now 🟡 `HOLD`.\n": "HOLD",
        "## Disposition\n\n🟢 **CURRENT.** The first envelope.\n": "CURRENT",
        "## Executive summary\n\nSHIP everywhere\n": None,
        "## Disposition\n\nSection content.\n": None,
    }
    for text, expected in cases.items():
        assert sabotage.disposition_of(text) == expected, text


# ---- instrument liveness -------------------------------------------------------


INERT_INSTRUMENT = """
def gap(reason):
    return {"gap": reason}

def g_con_empty(bundle):
    if not bundle:
        return gap("no bundle")
    return gap("sandbox unavailable")

def check_provenance(root):
    return None

def sandbox_state():
    return {"hermetic": False, "available": False}
"""

LIVE_INSTRUMENT = """
def gap(reason):
    return {"gap": reason}

def g_con_empty(bundle, sandbox):
    if not sandbox.available:
        return gap("sandbox unavailable")
    if bundle.empty_submission_reward() > 0:
        return Finding("G-CON-EMPTY", "empty submission earned reward")
    return None

def check_provenance(root):
    out = []
    if not (root / "provenance.sig").exists():
        out.append(fire("PROVENANCE_MISSING"))
    return out

def sandbox_state():
    probe = run(["docker", "info"])
    return {"hermetic": probe.ok, "available": probe.ok}
"""


@bite("shared.md:A3")
def test_inert_instruments_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".audit").mkdir()
    (root / ".audit" / "inst_screen.py").write_text(INERT_INSTRUMENT, encoding="utf-8")
    commit_all(root)

    findings = sabotage.check_instrument_liveness(str(root))

    assert codes(findings) == {sabotage.SAB_INERT_INSTRUMENT}
    names = {finding.message.split()[1] for finding in findings}
    assert names == {"g_con_empty", "check_provenance", "sandbox_state"}


BRANCHING_PREDICATES = """
def check_manifest(path):
    if not path.exists():
        return False
    return True

def check_digest(actual, expected):
    if actual != expected:
        raise ValueError("digest mismatch")
    return True

def check_schema(document):
    assert "schema" in document
    return True
"""


def test_branching_predicates_are_live(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".audit").mkdir()
    (root / ".audit" / "predicates.py").write_text(BRANCHING_PREDICATES, encoding="utf-8")
    commit_all(root)

    assert sabotage.check_instrument_liveness(str(root)) == []


def test_live_instruments_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".audit").mkdir()
    (root / ".audit" / "inst_screen.py").write_text(LIVE_INSTRUMENT, encoding="utf-8")
    commit_all(root)

    assert sabotage.check_instrument_liveness(str(root)) == []


def test_unparseable_instrument_source_is_a_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".seed").mkdir()
    (root / ".seed" / "broken.py").write_text("def (:\n", encoding="utf-8")
    commit_all(root)

    assert codes(sabotage.check_instrument_liveness(str(root))) == {sabotage.SAB_READ_ERROR}


# ---- cited files must be committed --------------------------------------------


@bite("shared.md:A7")
def test_report_citing_uncommitted_audit_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / "VERDICT.md").write_text(
        "## Disposition\n\nBLOCK\n\n## Findings\n\nSee `.audit/recon.py:86-103` and "
        "`.audit/inst_screen.py`.\n",
        encoding="utf-8",
    )
    commit_all(root)
    (root / ".audit").mkdir()
    (root / ".audit" / "recon.py").write_text("present on disk only\n", encoding="utf-8")

    findings = sabotage.check_audit_cites_committed_files(str(root))

    assert codes(findings) == {sabotage.SAB_AUDIT_UNCOMMITTED}
    cited = {finding.message.split(" cites ")[1].split(",")[0] for finding in findings}
    assert cited == {".audit/recon.py", ".audit/inst_screen.py"}


def test_report_citing_committed_audit_files_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".audit").mkdir()
    (root / ".audit" / "recon.py").write_text("committed\n", encoding="utf-8")
    (root / ".audit" / "evidence").mkdir()
    (root / ".audit" / "evidence" / "scan.yaml").write_text("ok\n", encoding="utf-8")
    (root / "VERDICT.md").write_text(
        "## Findings\n\nSee `.audit/recon.py:86-103`, `.audit/evidence/`, and `.audit/evidence`.\n",
        encoding="utf-8",
    )
    commit_all(root)

    assert sabotage.check_audit_cites_committed_files(str(root)) == []


def attach_memory_submodule(tmp_path: Path, root: Path, files: dict[str, str]) -> Path:
    """Register ``.memory`` as a roster submodule carrying ``files`` at its own HEAD."""

    origin = tmp_path / "canonical-memory.git"
    git(["init", "-q", "--bare", "-b", "main", str(origin)], cwd=tmp_path)
    work = tmp_path / "memory-work"
    git(["init", "-q", "-b", "main", str(work)], cwd=tmp_path)
    for name, body in files.items():
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    commit_all(work, "memory genesis")
    git(["remote", "add", "origin", str(origin)], cwd=work)
    git(["push", "-q", "origin", "main"], cwd=work)
    git(
        ["-c", "protocol.file.allow=always", "submodule", "add", "-q", str(origin), ".memory"],
        cwd=root,
    )
    return origin


def test_report_citing_file_absent_from_the_memory_submodule_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    attach_memory_submodule(tmp_path, root, {"roots.yaml": "roles: {}\n"})
    (root / "EDICT.md").write_text(
        "## Findings\n\nSee `.memory/cohorts/2026-q3.yaml` and `.memory/absent.md`.\n",
        encoding="utf-8",
    )
    commit_all(root)
    (root / ".memory" / "absent.md").write_text("present on disk only\n", encoding="utf-8")

    findings = sabotage.check_audit_cites_committed_files(str(root))

    assert codes(findings) == {sabotage.SAB_AUDIT_UNCOMMITTED}
    cited = {finding.message.split(" cites ")[1].split(",")[0] for finding in findings}
    assert cited == {".memory/cohorts/2026-q3.yaml", ".memory/absent.md"}


def test_report_citing_committed_memory_submodule_files_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    attach_memory_submodule(
        tmp_path,
        root,
        {"roots.yaml": "roles: {}\n", "cohorts/2026-q3.yaml": "models: []\n"},
    )
    (root / "EDICT.md").write_text(
        "## Findings\n\nSee `.memory/roots.yaml`, `.memory/cohorts/2026-q3.yaml`, "
        "`.memory/cohorts/`, and `.memory/`.\n",
        encoding="utf-8",
    )
    commit_all(root)

    assert sabotage.check_audit_cites_committed_files(str(root)) == []


def test_citation_into_an_uninitialized_submodule_is_advisory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    attach_memory_submodule(tmp_path, root, {"roots.yaml": "roles: {}\n"})
    (root / "EDICT.md").write_text("## Findings\n\nSee `.memory/roots.yaml`.\n", encoding="utf-8")
    commit_all(root)
    git(["-c", "protocol.file.allow=always", "submodule", "deinit", "-f", ".memory"], cwd=root)

    findings = sabotage.check_audit_cites_committed_files(str(root))

    assert codes(findings) == {sabotage.SAB_SUBMODULE_UNVERIFIED}
    assert [item.severity for item in findings] == [Severity.ADVISORY]
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


# ---- canonical submodule remote -----------------------------------------------


def test_canonical_submodule_at_tip_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)

    assert sabotage.check_submodule_canonical_remote(str(root)) == []


@bite("shared.md:A4")
def test_forked_submodule_url_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    text = (root / ".gitmodules").read_text(encoding="utf-8")
    fork = tmp_path / "fork.git"
    (root / ".gitmodules").write_text(
        text.replace(str(tmp_path / "canonical-trinity.git"), str(fork)), encoding="utf-8"
    )
    commit_all(root)

    findings = sabotage.check_submodule_canonical_remote(str(root))

    assert codes(findings) == {sabotage.SAB_SUBMODULE_REMOTE}


def test_vendored_commit_off_canonical_main_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    submodule = root / "trinity"
    (submodule / "tools.py").write_text("PARENT_CHECKS = []\n", encoding="utf-8")
    commit_all(submodule, "gut the harness locally")
    commit_all(root, "pin trinity to a local commit")

    findings = sabotage.check_submodule_canonical_remote(str(root))

    assert codes(findings) == {sabotage.SAB_SUBMODULE_OFF_MAIN}


def test_vendored_ancestor_of_canonical_main_is_not_off_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    work = tmp_path / "trinity-work"
    (work / "FORGE.md").write_text("newer contract\n", encoding="utf-8")
    commit_all(work, "advance canonical main")
    git(["push", "-q", "origin", "main"], cwd=work)

    assert sabotage.check_submodule_canonical_remote(str(root)) == []


def test_unreachable_canonical_remote_is_advisory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    text = (root / ".gitmodules").read_text(encoding="utf-8")
    missing = tmp_path / "missing.git"
    (root / ".gitmodules").write_text(
        text.replace(str(tmp_path / "canonical-trinity.git"), str(missing)), encoding="utf-8"
    )
    commit_all(root)
    monkeypatch.setenv(sabotage.CANONICAL_REMOTE_ENV, str(missing))

    findings = sabotage.check_submodule_canonical_remote(str(root))

    assert codes(findings) == {sabotage.SAB_SUBMODULE_UNVERIFIED}
    assert all(finding.severity.name == "ADVISORY" for finding in findings)


def test_remote_normalization_treats_transport_spellings_alike() -> None:
    spellings = [
        "https://github.com/EtharaOrion/trinity.git",
        "https://github.com/etharaorion/trinity",
        "git@github.com:EtharaOrion/trinity.git",
        "org-302118749@github.com:EtharaOrion/trinity.git",
        "ssh://git@github.com/EtharaOrion/trinity.git",
    ]
    assert {sabotage.normalize_remote(url) for url in spellings} == {
        "github.com/etharaorion/trinity"
    }
    assert sabotage.normalize_remote("https://github.com/Other/trinity.git") != (
        "github.com/etharaorion/trinity"
    )


# ---- typed sign-off -------------------------------------------------------------


@bite("shared.md:A5")
def test_typed_signoff_file_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / "SIGNOFF.md").write_text("Signature: Project Lead\n", encoding="utf-8")
    commit_all(root)

    findings = sabotage.check_no_typed_signoff(str(root))

    assert codes(findings) == {sabotage.SAB_TYPED_SIGNOFF}


def test_report_resting_ship_on_signoff_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / "VERDICT.md").write_text(
        "## Disposition\n\nThe released disposition is SHIP on the standing signed "
        "acceptance in SIGNOFF.md.\n",
        encoding="utf-8",
    )
    commit_all(root)

    findings = sabotage.check_no_typed_signoff(str(root))

    assert codes(findings) == {sabotage.SAB_TYPED_SIGNOFF}
    assert findings[0].line == 3


def test_signoff_with_envelope_sibling_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / "SIGNOFF.md").write_text("accepted\n", encoding="utf-8")
    (root / "SIGNOFF.md.dsse").write_text("{}\n", encoding="utf-8")
    commit_all(root)

    assert sabotage.check_no_typed_signoff(str(root)) == []


# ---- workflow tamper -----------------------------------------------------------

SUSPECT = sabotage.SAB_WORKFLOW_TAMPER_SUSPECT


@bite("shared.md:A6")
def test_workflow_edit_bundled_with_gate_subject_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "gate.yaml").write_text("on: []\n", encoding="utf-8")
    (root / "VERDICT.md").write_text("## Disposition\n\nSHIP\n", encoding="utf-8")
    commit_all(root, "disable the gate and flip the verdict")

    findings = sabotage.check_workflow_tamper(str(root))

    assert codes(findings) == {sabotage.SAB_WORKFLOW_TAMPER}
    assert ".github/workflows/gate.yaml" in findings[0].message
    assert "VERDICT.md" in findings[0].message


@pytest.mark.parametrize(
    ("governance_path", "subject_path"),
    [
        (".memory/roots.yaml", "VERDICT.md"),
        (".memory/allowed_signers", ".audit/disposition.json"),
        (".memory/trusted-root-version", ".seed/contract.yaml"),
        (".memory/root-rotation/new-signatures/approver.sig", "EDICT.md"),
    ],
)
def test_trust_governance_edit_bundled_with_subject_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    governance_path: str,
    subject_path: str,
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    governance = root / governance_path
    governance.parent.mkdir(parents=True, exist_ok=True)
    governance.write_text("rotated\n", encoding="utf-8")
    subject = root / subject_path
    subject.parent.mkdir(parents=True, exist_ok=True)
    subject.write_text("changed\n", encoding="utf-8")
    commit_all(root, "rotate trust and change its subject")

    findings = sabotage.check_workflow_tamper(str(root))

    assert codes(findings) == {SUSPECT}
    assert gate.ceiling(findings) == gate.HOLD
    assert governance_path in findings[0].message
    assert subject_path in findings[0].message


def test_workflow_tamper_finding_prescribes_forward_recovery_never_force_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    governance = root / ".memory" / "allowed_signers"
    governance.parent.mkdir(parents=True, exist_ok=True)
    governance.write_text("rotated\n", encoding="utf-8")
    (root / "VERDICT.md").write_text("## Disposition\n\nSHIP\n", encoding="utf-8")
    commit_all(root, "rotate signers beside the verdict")

    findings = sabotage.check_workflow_tamper(str(root))

    assert codes(findings) == {sabotage.SAB_WORKFLOW_TAMPER}
    message = findings[0].message.lower()
    assert "recover forward" in message
    assert "rotation ceremony" in message
    assert "remediation record" in message
    assert "original commits stay as evidence" in message
    assert "--force" not in message
    assert "rebase" not in message
    assert "rewrite" not in message.replace("never by rewriting", "")


def test_trust_governance_only_commit_is_not_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    rotation = root / ".memory" / "root-rotation" / "approval.json"
    rotation.parent.mkdir(parents=True, exist_ok=True)
    rotation.write_text("{}\n", encoding="utf-8")
    commit_all(root, "record trust rotation")

    assert sabotage.check_workflow_tamper(str(root)) == []


def test_install_commit_carrying_gate_receipts_is_not_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preflight installs the workflows and writes its receipt in one run."""

    root = make_parent(tmp_path, monkeypatch)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "sentinel.yaml").write_text("on: []\n", encoding="utf-8")
    receipts = root / ".audit" / "gate-receipts"
    receipts.mkdir(parents=True)
    (receipts / "run-1.json").write_text("{}\n", encoding="utf-8")
    commit_all(root, "install the gates")

    assert sabotage.check_workflow_tamper(str(root)) == []


def test_separate_workflow_and_subject_commits_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "gate.yaml").write_text("on: [push]\n", encoding="utf-8")
    commit_all(root, "add the gate")
    (root / "VERDICT.md").write_text("## Disposition\n\nHOLD\n", encoding="utf-8")
    commit_all(root, "record the verdict")

    assert sabotage.check_workflow_tamper(str(root)) == []


def gate_workflow(root: Path, body: str = "on: [push]\n") -> Path:
    workflow = root / ".github" / "workflows" / "gate.yaml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(body, encoding="utf-8")
    return workflow


@bite("shared.md:A68")
def test_solo_co_edit_is_suspicion_that_holds_not_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    gate_workflow(root)
    (root / "VERDICT.md").write_text("## Disposition\n\nHOLD\n", encoding="utf-8")
    commit_all(root, "touch the gate and the verdict together")

    findings = sabotage.check_workflow_tamper(str(root))

    assert codes(findings) == {sabotage.SAB_WORKFLOW_TAMPER_SUSPECT}
    assert gate.ceiling(findings) == gate.HOLD
    assert "split" in findings[0].message.lower()


@pytest.mark.parametrize(
    ("workflow_body", "verdict_body"),
    [
        (
            "jobs:\n  gate:\n    steps:\n"
            "      - run: python3 trinity/tools/gate.py check ./ || true\n",
            "## Disposition\n\nHOLD\n",
        ),
        ("on: [push]\n", "## Disposition\n\nSHIP\n"),
    ],
    ids=["bypass-syntax-on-gate-step", "forged-ship-beside-workflow"],
)
def test_co_edit_with_intent_signal_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workflow_body: str,
    verdict_body: str,
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    gate_workflow(root, workflow_body)
    (root / "VERDICT.md").write_text(verdict_body, encoding="utf-8")
    commit_all(root, "disable the gate and flip the verdict")

    findings = sabotage.check_workflow_tamper(str(root))

    assert codes(findings) == {sabotage.SAB_WORKFLOW_TAMPER}
    assert gate.ceiling(findings) == gate.BLOCK


@pytest.mark.parametrize(
    "housekeeping_path",
    ["samples/README.md", "delivery/README.md", ".seed/research/notes.md"],
)
@bite("shared.md:A70")
def test_workflow_edit_beside_housekeeping_is_not_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, housekeeping_path: str
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    gate_workflow(root)
    target = root / housekeeping_path
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(existing + "note\n", encoding="utf-8")
    commit_all(root, "tidy the workflow and a readme")

    assert sabotage.check_workflow_tamper(str(root)) == []


def test_gitmodules_edited_beside_a_subject_is_workflow_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    gitmodules = root / ".gitmodules"
    gitmodules.write_text(
        gitmodules.read_text(encoding="utf-8") + "\tbranch = side\n", encoding="utf-8"
    )
    (root / "VERDICT.md").write_text("## Disposition\n\nSHIP\n", encoding="utf-8")
    commit_all(root, "repoint the submodule and flip the verdict")

    findings = sabotage.check_workflow_tamper(str(root))

    assert codes(findings) == {sabotage.SAB_WORKFLOW_TAMPER}
    assert gate.ceiling(findings) == gate.BLOCK
    assert ".gitmodules" in findings[0].message
    assert "VERDICT.md" in findings[0].message


def test_gitmodules_edited_beside_a_lane_readme_is_housekeeping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    gitmodules = root / ".gitmodules"
    gitmodules.write_text(
        gitmodules.read_text(encoding="utf-8") + "\tupdate = merge\n", encoding="utf-8"
    )
    readme = root / "samples" / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("one sample\n", encoding="utf-8")
    commit_all(root, "register the lane and render its readme")

    assert sabotage.check_workflow_tamper(str(root)) == []


@bite("shared.md:A69")
def test_split_commits_close_a_suspect_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    gate_workflow(root)
    (root / "VERDICT.md").write_text("## Disposition\n\nHOLD\n", encoding="utf-8")
    commit_all(root, "touch the gate and the verdict together")
    assert codes(sabotage.check_workflow_tamper(str(root))) == {SUSPECT}

    gate_workflow(root, "on: [push, pull_request]\n")
    commit_all(root, "workflow alone")
    assert codes(sabotage.check_workflow_tamper(str(root))) == {SUSPECT}

    (root / "VERDICT.md").write_text("## Disposition\n\nHOLD\n\nreviewed\n", encoding="utf-8")
    commit_all(root, "verdict alone")
    assert sabotage.check_workflow_tamper(str(root)) == []


def test_split_commits_never_close_a_blocking_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    gate_workflow(root)
    (root / "VERDICT.md").write_text("## Disposition\n\nSHIP\n", encoding="utf-8")
    commit_all(root, "flip the verdict beside the gate")
    gate_workflow(root, "on: [push, pull_request]\n")
    commit_all(root, "workflow alone")
    (root / "VERDICT.md").write_text("## Disposition\n\nSHIP\n\nagain\n", encoding="utf-8")
    commit_all(root, "verdict alone")

    assert codes(sabotage.check_workflow_tamper(str(root))) == {sabotage.SAB_WORKFLOW_TAMPER}


def test_subject_paths_include_staging() -> None:
    assert sabotage._is_subject_path("staging/6ba7b810-9dad-51d1-80b4-00c04fd430c8/task.toml")
    assert not sabotage._is_subject_path("staging/README.md")
    assert not sabotage._is_subject_path("stagingx/a")
    assert not sabotage._is_subject_path("research/x")


# ---- dirty tree ----------------------------------------------------------------


@bite("shared.md:A8")
def test_dirty_tree_at_gate_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".audit").mkdir()
    (root / ".audit" / "recon.py").write_text("uncommitted\n", encoding="utf-8")

    findings = sabotage.check_dirty_tree_at_gate(str(root))

    assert codes(findings) == {sabotage.SAB_DIRTY_TREE}
    assert ".audit/recon.py" in findings[0].message


def test_sentinel_ledger_does_not_count_as_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".sentinel").mkdir()
    (root / ".sentinel" / "attempts.jsonl").write_text("{}\n", encoding="utf-8")

    assert sabotage.check_dirty_tree_at_gate(str(root)) == []


def test_uncommitted_gate_and_signing_outputs_do_not_count_as_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    for relative in (
        ".audit/disposition.json",
        ".audit/disposition.json.dsse",
        ".audit/gate-receipts/local-abc.json",
        ".seed/disposition.json",
        ".trinity-runtime/approver.dsse",
        "TRACKING.md",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")

    assert sabotage.check_dirty_tree_at_gate(str(root)) == []

    (root / ".audit" / "recon.py").write_text("uncommitted\n", encoding="utf-8")
    findings = sabotage.check_dirty_tree_at_gate(str(root))
    assert codes(findings) == {sabotage.SAB_DIRTY_TREE}
    assert "1 entries" in findings[0].message


def test_install_receipts_do_not_count_as_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    receipt = root / ".trinity-install" / "protection" / "acme-argos.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}\n", encoding="utf-8")

    assert sabotage.check_dirty_tree_at_gate(str(root)) == []


def test_dirty_tree_message_names_the_remedy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    (root / ".seed").mkdir()
    (root / ".seed" / "batch.yaml").write_text("slots: []\n", encoding="utf-8")

    findings = sabotage.check_dirty_tree_at_gate(str(root))

    assert codes(findings) == {sabotage.SAB_DIRTY_TREE}
    assert findings[0].message.endswith(
        "commit the phase work before the gate runs; only root reports, receipts, "
        "disposition records, install receipts, and the sentinel ledger may stay uncommitted"
    )


def test_non_repository_is_a_read_error(tmp_path: Path) -> None:
    root = tmp_path / "loose"
    root.mkdir()

    assert codes(sabotage.check_dirty_tree_at_gate(str(root))) == {sabotage.SAB_READ_ERROR}


# ---- registry and CLI ----------------------------------------------------------


def test_checks_registry_covers_every_sabotage_code() -> None:
    names = {name for name, _check in sabotage.CHECKS}
    assert len(names) == len(sabotage.CHECKS) == 7
    assert all(name.startswith("sabotage_") for name in names)


def test_cli_exit_status_follows_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    monkeypatch.chdir(tmp_path)

    assert sabotage.main(["./parent"]) == 0
    assert "sabotage: clean" in capsys.readouterr().out

    (root / "SIGNOFF.md").write_text("Signature: typed\n", encoding="utf-8")
    commit_all(root)

    assert sabotage.main(["--json", "./parent"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert {item["code"] for item in payload} == {sabotage.SAB_TYPED_SIGNOFF}
    assert sabotage.main([]) == 2


def test_run_scoped_gate_outputs_do_not_count_as_dirty_but_run_inputs_do(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_parent(tmp_path, monkeypatch)
    run = root / ".seed" / "runs" / "forge-ada-20260917t120000z-abcdef"
    (run / "gate-receipts").mkdir(parents=True)
    (run / "gate-receipts" / "report-0001.json").write_text("{}\n", encoding="utf-8")
    (run / "disposition.json").write_text("{}\n", encoding="utf-8")
    (run / "report.md").write_text("## Disposition\n\nHOLD\n", encoding="utf-8")

    assert sabotage.check_dirty_tree_at_gate(str(root)) == []

    (run / "contract.yaml").write_text("archetype: AR1\n", encoding="utf-8")
    findings = sabotage.check_dirty_tree_at_gate(str(root))
    assert codes(findings) == {sabotage.SAB_DIRTY_TREE}
    assert "contract.yaml" in findings[0].message
