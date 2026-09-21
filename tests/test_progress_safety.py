from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from tools import _phases, progress
from tools.attest.canonical import canonical_sha256, parse_json

from tests.test_progress import close, directory, rebuild, target

__all__ = ["target"]


def test_close_refuses_after_report_gate(target: Path) -> None:
    # Given an open invocation; when report qualification occurs; then close refuses.
    rebuild(target)
    receipts = directory(target) / "gate-receipts"
    receipts.mkdir()
    (receipts / "report-0001.json").write_text("{}\n")
    with pytest.raises(ValueError, match="PROGRESS_INPUTS_MOVED_DURING_RUN"):
        close(target)
    assert not (directory(target) / "phases").exists()


def test_signed_artifact_requires_at_generically(
    target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a signed artifact on any phase; when no instant is supplied; then it holds.
    rows = _phases.TABLE["ENGRAM"]
    monkeypatch.setitem(
        _phases.TABLE,
        "ENGRAM",
        tuple(
            replace(row, artifacts=("./.memory/proof.dsse",)) if row.id == "0" else row
            for row in rows
        ),
    )
    assert rebuild(target)["phases"]["0"] == "unverifiable:evaluation_time_missing"


def test_fingerprint_has_only_four_binding_components(target: Path) -> None:
    # Given a phase; when fingerprinted; then its schema has no extra binding dimensions.
    item = rebuild(target)["fingerprints"]["0"]
    assert set(item["fingerprint"]) == {
        "schema",
        "phase",
        "inputs",
        "approval_digest",
        "contract_sha256",
        "trinity_gitlink",
    }
    assert item["inputs_fp"] == canonical_sha256(item["fingerprint"])


def test_closed_at_is_recorded_outside_fingerprint(target: Path) -> None:
    # Given an opened phase; when closed; then its timestamp stays outside the fingerprint.
    before = rebuild(target)["fingerprints"]["0"]["inputs_fp"]
    close(target)
    record = parse_json((directory(target) / "phases/0.json").read_bytes())
    assert isinstance(record, dict)
    assert record["inputs_fp"] == before
    assert record["closed_at"]


def test_symlink_output_is_refused(target: Path, tmp_path: Path) -> None:
    # Given a symlinked output; when rebuilt; then its external target is untouched.
    external = tmp_path / "outside"
    external.write_text("keep")
    (directory(target) / "progress.yaml").symlink_to(external)
    with pytest.raises(ValueError, match="symbolic links"):
        rebuild(target)
    assert external.read_text() == "keep"


def test_cli_failed_check_holds_without_resume(
    target: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given a failed never-skip check; when the CLI runs; then it returns HOLD-class status.
    monkeypatch.chdir(target)
    code = progress.main(
        [
            "progress.py",
            "rebuild",
            "./",
            "--instrument",
            "ENGRAM",
            "--run",
            "engram-ada-1",
            "--principal",
            "ada",
            "--check-result",
            "2=ran:fail:FAILED",
            "--json",
        ]
    )
    assert code == 2
    result = parse_json(capsys.readouterr().out)
    assert isinstance(result, dict)
    decision = result["decision"]
    assert isinstance(decision, dict)
    assert decision["resume_at"] is None


def test_closing_another_branch_is_refused(target: Path) -> None:
    # Given a default invocation; when H is closed; then the branch boundary holds.
    rebuild(target)
    with pytest.raises(ValueError, match="PROGRESS_PHASE_UNKNOWN"):
        close(target, "H")


def test_rerun_invalidates_dependents_even_when_bytes_match(target: Path) -> None:
    # Given an approved gate; when its dependency closes again; then it must be revisited.
    rebuild(target)
    close(target)
    assert rebuild(target)["phases"]["0.5"] == "incomplete:dependency_moved"


def test_moved_phase_can_close_after_a_new_rebuild(target: Path) -> None:
    # Given moved read bytes; when a new invocation rebuilds; then its new baseline can close.
    rebuild(target)
    (target / "DEFERRED.md").write_text("moved")
    rebuild(target)
    close(target)
    assert rebuild(target)["phases"]["0"] == "complete"
