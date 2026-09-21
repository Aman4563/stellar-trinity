from pathlib import Path

import pytest

from tests.bite_shared.registration import bite
from tests.harness_imports import integrity, load_harness
from tests.parent_fixtures import commit_all
from tests.parent_fixtures import write_bundle as build_bundle
from tests.test_integrity_parent import (
    EVALUATION_TIME,
    approval_codes,
    approval_statement,
    build_chain,
    build_parent,
    write_approval_gate,
    write_chain,
)
from tests.test_sabotage import make_parent as make_sabotage_parent

sabotage = load_harness("sabotage")


@bite("shared.md:W1")
def test_forge_rejects_the_auditor_projection() -> None:
    findings = integrity.check_projection_closure("FORGE.md", "Read FORGE_VIEW and CRUCIBLE_VIEW.")
    assert any("names the sibling projection" in item.message for item in findings)


@bite("shared.md:W2")
def test_crucible_rejects_the_author_projection() -> None:
    findings = integrity.check_projection_closure(
        "CRUCIBLE.md", "Read CRUCIBLE_VIEW and FORGE_VIEW."
    )
    assert any("names the sibling projection" in item.message for item in findings)


@bite("shared.md:W3")
def test_crucible_rejects_cohort_currency_vocabulary() -> None:
    findings = integrity.check_cohort_closure(
        "CRUCIBLE.md", "Resolve the required_cohort before grading."
    )
    assert any("cohort-currency term" in item.message for item in findings)


@bite("shared.md:W4")
def test_forge_rejects_per_rollout_timing_vocabulary() -> None:
    findings = integrity.check_timing_closure(
        "FORGE.md", "Record the rollout duration for each attempt."
    )
    assert any("per-rollout timing term" in item.message for item in findings)


@bite("shared.md:R1")
def test_spine_rejects_nine_files() -> None:
    planted = " ".join(integrity.SPINE[:-1])
    findings = integrity.check_spine_complete("corpus", planted)
    assert any("doc-spine file" in item.message for item in findings)


@bite("shared.md:R2")
def test_spine_rejects_noncanonical_first_mention_order() -> None:
    planted = " ".join([integrity.SPINE[1], integrity.SPINE[0], *integrity.SPINE[2:]])
    findings = integrity.check_spine_order("corpus", planted)
    assert any("first-mention order" in item.message for item in findings)


@bite("shared.md:R3")
def test_contract_rejects_an_unknown_backtick_path_root() -> None:
    findings = integrity.check_unknown_paths("FORGE.md", "Read `mystery/file.md`.")
    assert any("unknown root" in item.message for item in findings)


@bite("shared.md:R4")
def test_contract_rejects_a_retired_document_name() -> None:
    findings = integrity.check_retired_names("FORGE.md", "Use EXECUTIVE.md now.")
    assert any("retired doc-spine name" in item.message for item in findings)


@bite("shared.md:R6")
def test_approval_rejects_equal_producer_and_approver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "parent"
    root.mkdir()
    artifact, _, _ = write_approval_gate(root)
    statement = approval_statement(artifact, producer="approver@trinity.test")
    write_approval_gate(root, statement=statement)
    assert "APPROVAL_PRODUCER_IS_APPROVER" in approval_codes(root)


@bite("shared.md:R8")
def test_generated_truth_rejects_a_missing_banner(tmp_path: Path) -> None:
    root = tmp_path / "parent"
    bundle = build_bundle(root, "6ba7b810-9dad-51d1-80b4-00c04fd430c8")
    (bundle / "solution" / integrity.TRUTH_FILE).write_text("hand edited\n", encoding="utf-8")
    findings = integrity.check_bundle_layout(str(root))
    assert any(
        "generated truth file lacks its do-not-edit banner" in item.message for item in findings
    )


@bite("shared.md:R12")
@pytest.mark.parametrize(
    "content",
    [
        '[submodule "trinity"]\npath = trinity\nupdate = merge\n',
        '[submodule "trinity"]\npath = trinity\nbranch = v0.8\nupdate = merge\n',
        '[submodule "trinity"]\npath = trinity\nbranch = main\n',
    ],
)
def test_parent_submodule_rejects_nontracking_configuration(tmp_path: Path, content: str) -> None:
    root = tmp_path / "parent"
    root.mkdir()
    (root / ".gitmodules").write_text(content, encoding="utf-8")
    assert integrity.check_parent_submodule(str(root))


@bite("shared.md:O11")
def test_shared_doctrine_rejects_a_reworded_copy() -> None:
    block = integrity.SHARED_BLOCKS[0]
    planted = "\n".join(integrity.SHARED_BLOCKS).replace(block, "Reworded doctrine.", 1)
    findings = integrity.check_shared_blocks("FORGE.md", planted)
    assert any("shared doctrine drifted" in item.message for item in findings)


@bite("shared.md:P4")
def test_feedback_chain_rejects_an_edited_line(tmp_path: Path) -> None:
    root = tmp_path / "parent"
    build_parent(root)
    entries = build_chain()
    entries[1]["kind"] = "question"
    write_chain(root, entries)
    findings = integrity.check_feedback_chain(str(root), EVALUATION_TIME)
    assert any("entry_hash does not cover this line" in item.message for item in findings)


@bite("shared.md:P7")
def test_feedback_chain_rejects_a_missing_or_empty_github_id(tmp_path: Path) -> None:
    dropped = tmp_path / "dropped"
    build_parent(dropped)
    entries = build_chain()
    entries[-1].pop("github_id")
    write_chain(dropped, entries)
    findings = integrity.check_feedback_chain(str(dropped), EVALUATION_TIME)
    assert any("missing the field github_id" in item.message for item in findings)

    emptied = tmp_path / "emptied"
    build_parent(emptied)
    entries = build_chain()
    last = entries[-1]
    last.pop("entry_hash")
    last["github_id"] = ""
    last["entry_hash"] = integrity.chain_digest(last)
    write_chain(emptied, entries)
    findings = integrity.check_feedback_chain(str(emptied), EVALUATION_TIME)
    assert any("github_id is not a non-empty string" in item.message for item in findings)


@bite("shared.md:P6")
def test_feedback_ledger_rejects_a_missing_chain(tmp_path: Path) -> None:
    root = tmp_path / "parent"
    build_parent(root)
    harness = root / ".memory"
    harness.mkdir(parents=True, exist_ok=True)
    (harness / integrity.FEEDBACK_LEDGER).write_text("records: []\n", encoding="utf-8")
    findings = integrity.check_feedback_chain(str(root), EVALUATION_TIME)
    assert any("attesting chain is missing" in item.message for item in findings)


@bite("shared.md:A71")
def test_gitmodules_edited_beside_a_governed_subject_is_workflow_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_sabotage_parent(tmp_path, monkeypatch)
    gitmodules = root / ".gitmodules"
    gitmodules.write_text(
        gitmodules.read_text(encoding="utf-8") + "\tbranch = side\n", encoding="utf-8"
    )
    (root / "VERDICT.md").write_text("## Disposition\n\nSHIP\n", encoding="utf-8")
    commit_all(root, "repoint the submodule and flip the verdict")

    findings = sabotage.check_workflow_tamper(str(root))

    assert {item.code for item in findings} == {sabotage.SAB_WORKFLOW_TAMPER}
    assert ".gitmodules" in findings[0].message
