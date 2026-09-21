from __future__ import annotations

import importlib
import json
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from tools import _phases

from tests.parent_fixtures import write_resume_parent

if TYPE_CHECKING:
    from tools.progress_types import Decision


@pytest.fixture
def target(tmp_path: Path) -> Path:
    root = tmp_path / "parent"
    write_resume_parent(root, "ENGRAM", "engram-ada-1", approved=True)
    (root / "trinity").mkdir()
    (root / "trinity/ENGRAM.md").write_text("contract\n")
    importlib.import_module("tools.progress")
    return root


def rebuild(root: Path) -> Decision:
    result: Decision = importlib.import_module("tools.progress").rebuild(
        root, "ENGRAM", "engram-ada-1", principal="ada"
    )["decision"]
    return result


def directory(root: Path) -> Path:
    return root / ".memory/runs/engram-ada-1"


def close(root: Path, phase: str = "0") -> None:
    importlib.import_module("tools.progress").close(
        root, "ENGRAM", "engram-ada-1", principal="ada", phase_id=phase
    )


def test_rebuild_is_byte_identical_on_an_unchanged_tree(target: Path) -> None:
    # Given a reconstructed tree; when rebuilt; then both projections are stable.
    first = rebuild(target)
    before = (directory(target) / "progress.yaml").read_bytes()
    assert rebuild(target) == first
    assert (directory(target) / "progress.yaml").read_bytes() == before


def test_rebuild_reconstructs_after_the_cache_is_deleted(target: Path) -> None:
    # Given a cache; when deleted and reconstructed; then decision bytes agree.
    first = rebuild(target)
    before = (directory(target) / "progress.yaml").read_bytes()
    (directory(target) / "progress.yaml").unlink()
    assert rebuild(target) == first
    assert (directory(target) / "progress.yaml").read_bytes() == before


def test_a_hand_edited_cache_is_overwritten_not_trusted(target: Path) -> None:
    # Given invented completion; when reconstructed; then absent artifacts still fail.
    (directory(target) / "progress.yaml").write_text("phases:\n  1: complete\n")
    assert rebuild(target)["phases"]["1"] == "incomplete:artifact_missing"


def test_a_receipt_is_never_required_for_complete(target: Path) -> None:
    # Given a closed phase; when its receipt disappears; then evidence suffices.
    rebuild(target)
    close(target)
    (directory(target) / "phases/0.json").unlink()
    assert rebuild(target)["phases"]["0"] == "complete"


def test_a_receipt_is_never_sufficient_for_complete(target: Path) -> None:
    # Given a receipt; when an artifact disappears; then the receipt cannot approve it.
    rebuild(target)
    close(target)
    (target / ".memory/scope.yaml").unlink()
    result = rebuild(target)
    assert result["phases"]["0"] == "incomplete:artifact_missing"
    assert "PROGRESS_RECEIPT_MISMATCH" in result["fingerprints"]["0"]["codes"]


def test_one_moved_input_invalidates_the_phase_and_its_dependents(target: Path) -> None:
    # Given Phase 0's declared reads; when one changes; then dependent work invalidates.
    rebuild(target)
    close(target)
    (target / "DEFERRED.md").write_text("changed\n")
    result = rebuild(target)
    assert result["phases"]["0"] == "incomplete:inputs_moved"
    assert result["phases"]["1"] == "incomplete:dependency_moved"
    assert result["phases"]["2"] == "incomplete:dependency_moved"


def test_a_moved_gate_artifact_makes_the_gate_stale(target: Path) -> None:
    # Given approval; when bound bytes change; then the gate exposes both digests.
    rebuild(target)
    (target / ".memory/scope.yaml").write_text("changed\n")
    result = rebuild(target)
    assert result["phases"]["0.5"] == "incomplete:approval_stale"
    pair = result["fingerprints"]["0.5"]
    assert pair["approval_digest"] != pair["bound_digest"]


def test_a_contract_edit_invalidates_every_phase_of_that_instrument(target: Path) -> None:
    # Given a baseline; when the whole contract changes; then every row invalidates.
    rebuild(target)
    (target / "trinity/ENGRAM.md").write_text("changed\n")
    assert set(rebuild(target)["phases"].values()) == {"incomplete:inputs_moved"}


def test_a_trinity_gitlink_move_invalidates_every_phase(
    target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given one gitlink; when the index changes; then every row invalidates.
    state = importlib.import_module("tools.progress_inputs")
    monkeypatch.setattr(state, "gitlinks", lambda _: {"trinity": "a" * 40})
    monkeypatch.setattr(state, "submodule_clean", lambda *_: True)
    rebuild(target)
    monkeypatch.setattr(state, "gitlinks", lambda _: {"trinity": "b" * 40})
    assert set(rebuild(target)["phases"].values()) == {"incomplete:inputs_moved"}


def test_a_dirty_submodule_input_is_unverifiable_and_refuses_reuse(
    target: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a dirty input checkout; when evaluated; then no reusable fingerprint exists.
    state = importlib.import_module("tools.progress_inputs")
    monkeypatch.setattr(state, "gitlinks", lambda _: {"samples": "a" * 40})
    monkeypatch.setattr(state, "submodule_clean", lambda *_: False)
    assert rebuild(target)["phases"]["0"] == "unverifiable:submodule_dirty"


def test_every_branch_is_evaluated_and_only_the_invoked_branch_executes(target: Path) -> None:
    # Given default execution; when H inputs move; then H is evaluated but not closed.
    rebuild(target)
    (target / "requirements/change.md").write_text("changed\n")
    assert rebuild(target)["phases"]["H"] == "incomplete:inputs_moved"
    assert not (directory(target) / "phases/H.json").exists()


def test_reconciles_do_not_trip_the_moved_during_run_refusal(target: Path) -> None:
    # Given an open phase; when a reconciled artifact changes; then closing is lawful.
    rebuild(target)
    (target / ".memory/scope.yaml").write_text("updated\n")
    close(target)
    assert (directory(target) / "phases/0.json").is_file()


def test_reads_do_trip_it(target: Path) -> None:
    # Given an open phase; when a read changes; then closing refuses.
    rebuild(target)
    (target / "DEFERRED.md").write_text("changed\n")
    with pytest.raises(ValueError, match="PROGRESS_INPUTS_MOVED_DURING_RUN"):
        close(target)


def test_resume_at_is_withheld_until_the_never_skip_checks_pass(target: Path) -> None:
    # Given a failed current check; when rebuilt; then no phase resume is offered.
    progress = importlib.import_module("tools.progress")
    result = progress.rebuild(
        target, "ENGRAM", "engram-ada-1", principal="ada", checks={"2": "ran:fail:FAIL"}
    )
    assert result["decision"]["resume_at"] is None
    assert result["telemetry"]["stopped"] is True


def test_a_gate_name_with_a_comma_is_refused(target: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given an unrepresentable gate heading; when rebuilt; then the writer refuses.
    rows = _phases.TABLE["ENGRAM"]
    monkeypatch.setitem(
        _phases.TABLE,
        "ENGRAM",
        tuple(replace(p, contract_heading="### bad, gate") if p.id == "0.5" else p for p in rows),
    )
    with pytest.raises(ValueError, match="PROGRESS_GATE_NAME_INVALID"):
        rebuild(target)


def test_explain_lists_exactly_the_changed_paths(target: Path) -> None:
    # Given a baseline; when files are added, removed and changed; then paths are exact.
    (target / "requirements/removed.md").write_text("old")
    rebuild(target)
    (target / "requirements/removed.md").unlink()
    (target / "requirements/new.md").write_text("new")
    (target / ".memory/capabilities.yaml").write_text("changed")
    result = importlib.import_module("tools.progress").explain(
        target, "ENGRAM", "engram-ada-1", principal="ada", phase_id="H"
    )
    assert result == {
        "added": ["./requirements/new.md"],
        "removed": ["./requirements/removed.md"],
        "changed": ["./.memory/capabilities.yaml"],
    }


def test_decision_block_excludes_run_id_and_timestamps(target: Path) -> None:
    # Given a run; when rendered; then deterministic data contains no clock or run id.
    decision = rebuild(target)
    assert set(decision) == {"resume_at", "phases", "barriers", "fingerprints"}
    assert "engram-ada-1" not in json.dumps(decision)
    assert "closed_at" not in json.dumps(decision)


def test_progress_refuses_a_foreign_run(target: Path) -> None:
    # Given another owner; when writing; then ownership refusal propagates.
    progress = importlib.import_module("tools.progress")
    with pytest.raises(ValueError, match="run-owned"):
        progress.rebuild(target, "ENGRAM", "engram-ada-1", principal="other")


def test_progress_writes_only_inside_its_run_namespace(target: Path) -> None:
    # Given a parent; when rebuilt and closed; then every new file is run-private.
    before = set(target.rglob("*"))
    rebuild(target)
    close(target)
    assert all(p.is_relative_to(directory(target)) for p in set(target.rglob("*")) - before)
