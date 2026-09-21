import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CITATIONS = ROOT / "tools" / "citations.py"

CONTRACT = "".join(f"rule {number}\n" for number in range(1, 21))
ROW = "| C1 | A scenario. | `BLOCK`. | CRUCIBLE.md:5 | no |\n"


def build(root: Path, contract: str = CONTRACT, row: str = ROW) -> Path:
    (root / "CRUCIBLE.md").write_text(contract, encoding="utf-8")
    bite = root / "tests" / "bite"
    bite.mkdir(parents=True)
    source = bite / "crucible.md"
    source.write_text(row, encoding="utf-8")
    return source


def run(root: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CITATIONS), mode, "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_update_bootstraps_the_lock_and_check_passes(tmp_path: Path) -> None:
    build(tmp_path)
    updated = run(tmp_path, "update")
    checked = run(tmp_path, "check")
    lock = json.loads((tmp_path / "tests" / "bite" / "citations.lock").read_text(encoding="utf-8"))
    assert updated.returncode == 0 and checked.returncode == 0
    assert "clean:" in checked.stdout
    assert lock["version"] == 1 and len(lock["anchors"]) == 1


def test_update_is_idempotent(tmp_path: Path) -> None:
    source = build(tmp_path)
    run(tmp_path, "update")
    once = source.read_text(encoding="utf-8")
    run(tmp_path, "update")
    assert source.read_text(encoding="utf-8") == once


def test_drift_is_reported_then_repaired(tmp_path: Path) -> None:
    source = build(tmp_path)
    run(tmp_path, "update")
    (tmp_path / "CRUCIBLE.md").write_text("preamble\npreamble\n" + CONTRACT, encoding="utf-8")
    drifted = run(tmp_path, "check")
    run(tmp_path, "update")
    repaired = run(tmp_path, "check")
    assert drifted.returncode == 1
    assert "drifted; the cited rule now sits at line 7" in drifted.stdout
    assert "CRUCIBLE.md:7" in source.read_text(encoding="utf-8")
    assert repaired.returncode == 0


def test_a_deleted_rule_is_reported_rather_than_renumbered(tmp_path: Path) -> None:
    build(tmp_path)
    run(tmp_path, "update")
    (tmp_path / "CRUCIBLE.md").write_text(CONTRACT.replace("rule 5\n", ""), encoding="utf-8")
    gone = run(tmp_path, "check")
    assert gone.returncode == 1
    assert "the cited rule is gone from CRUCIBLE.md" in gone.stdout


@pytest.mark.parametrize(
    ("contract", "row", "message"),
    [
        (CONTRACT, ROW, "has no recorded anchor; run citations.py update"),
        (
            CONTRACT,
            "| C1 | A scenario. | `BLOCK`. | CRUCIBLE.md:99 | no |\n",
            "points past the end",
        ),
        (CONTRACT.replace("rule 5", ""), ROW, "points at a blank line"),
    ],
    ids=["missing-anchor", "past-end-of-file", "blank-line-target"],
)
def test_unusable_citations_are_findings(
    tmp_path: Path,
    contract: str,
    row: str,
    message: str,
) -> None:
    build(tmp_path, contract, row)
    findings = run(tmp_path, "check")
    assert findings.returncode == 1
    assert message in findings.stdout


def test_unknown_mode_is_a_usage_error(tmp_path: Path) -> None:
    build(tmp_path)
    assert run(tmp_path, "rewrite").returncode == 2


def run_args(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CITATIONS), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_corrected_source_number_is_ignored_while_its_anchor_stands(tmp_path: Path) -> None:
    # Given: a bootstrapped anchor bound to CRUCIBLE.md:5.
    source = build(tmp_path)
    run(tmp_path, "update")

    # When: the Source cell is corrected by hand and update runs.
    source.write_text(ROW.replace("CRUCIBLE.md:5", "CRUCIBLE.md:7"), encoding="utf-8")
    run(tmp_path, "update")

    # Then: the recorded digest wins and the correction is discarded.
    assert "CRUCIBLE.md:5" in source.read_text(encoding="utf-8")


def test_rekey_lets_a_corrected_source_number_bind(tmp_path: Path) -> None:
    # Given: a bootstrapped anchor whose recorded line does not carry the rule.
    source = build(tmp_path)
    run(tmp_path, "update")

    # When: that source line is rekeyed and the correction is written again.
    rekeyed = run_args(tmp_path, ["rekey", "crucible.md:1"])
    source.write_text(ROW.replace("CRUCIBLE.md:5", "CRUCIBLE.md:7"), encoding="utf-8")
    updated = run(tmp_path, "update")
    checked = run(tmp_path, "check")

    # Then: the corrected number is the one that binds, and check is clean.
    assert rekeyed.returncode == 0
    assert updated.returncode == 0
    assert checked.returncode == 0
    assert "CRUCIBLE.md:7" in source.read_text(encoding="utf-8")


def test_rekey_refuses_a_line_with_no_recorded_anchor(tmp_path: Path) -> None:
    # Given: a bootstrapped corpus.
    build(tmp_path)
    run(tmp_path, "update")

    # When: a line carrying no citation is rekeyed.
    refused = run_args(tmp_path, ["rekey", "crucible.md:99"])

    # Then: the tool refuses rather than writing an unchanged lockfile silently.
    assert refused.returncode == 1
    assert "no recorded anchor to drop" in refused.stdout


def test_the_readme_restates_the_bound_citation_count() -> None:
    # Given: the committed lockfile and the suite README that restates its size.
    lock = json.loads((ROOT / "tests" / "bite" / "citations.lock").read_text(encoding="utf-8"))
    readme = (ROOT / "tests" / "bite" / "README.md").read_text(encoding="utf-8")

    # When: the restated count is read out of the counts table.
    bound = len(lock["anchors"])

    # Then: the restatement matches the corpus it claims to describe.
    assert f"| Line-anchored contract citations bound in `citations.lock` | {bound} |" in readme
