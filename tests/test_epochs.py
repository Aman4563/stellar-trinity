from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tools import epochs

from tests.bite_shared.registration import bite

RUN_A = "engram-ada-20260917t120000z-aaaaaa"
RUN_B = "engram-bob-20260917t120000z-bbbbbb"


def memory(root: Path) -> None:
    (root / ".memory").mkdir()
    (root / ".memory" / "ledger.yaml").write_text("records: []\n", encoding="utf-8")
    (root / ".memory" / "hardness.yaml").write_text("levers: []\n", encoding="utf-8")
    (root / ".memory" / "forge_view.yaml").write_text("view: forge\n", encoding="utf-8")
    (root / ".memory" / "crucible_view.yaml").write_text("view: crucible\n", encoding="utf-8")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- genesis epoch and proposals -----------------------------------------------------------


def test_genesis_epoch_snapshots_the_authoritative_files(tmp_path: Path) -> None:
    memory(tmp_path)

    published = epochs.publish(tmp_path, RUN_A)

    assert published.epoch == 1
    assert epochs.current(tmp_path) == 1
    manifest = json.loads((tmp_path / epochs.EPOCHS_DIR / "1" / "manifest.json").read_text())
    assert manifest["schema"] == epochs.MANIFEST_SCHEMA
    assert manifest["parent_epoch"] == 0
    assert manifest["files"]["ledger.yaml"] == sha("records: []\n")
    assert (tmp_path / epochs.EPOCHS_DIR / "1" / "ledger.yaml").read_text() == "records: []\n"
    views = tmp_path / epochs.VIEWS_DIR / "1"
    assert (views / "forge_view.yaml").read_text() == "view: forge\n"
    assert json.loads((views / "manifest-digest.json").read_text())["manifest_digest"] == (
        epochs.manifest_digest(tmp_path, 1)
    )
    assert epochs.check_epochs(str(tmp_path)) == []


def test_propose_records_bytes_against_the_current_epoch(tmp_path: Path) -> None:
    memory(tmp_path)
    epochs.publish(tmp_path, RUN_A)

    proposal = epochs.propose(tmp_path, RUN_B, "ledger.yaml", b"records:\n  - one\n")

    body = json.loads(proposal.read_text())
    assert body["base_epoch"] == 1 and body["path"] == "ledger.yaml"
    assert body["sha256"] == sha("records:\n  - one\n")
    stored = tmp_path / epochs.PROPOSALS_DIR / RUN_B / "files" / "ledger.yaml"
    assert stored.read_bytes() == b"records:\n  - one\n"
    assert (tmp_path / ".memory" / "ledger.yaml").read_text() == "records: []\n"


@bite("shared.md:A65")
def test_publish_folds_disjoint_proposals_from_two_runs_into_one_epoch(tmp_path: Path) -> None:
    memory(tmp_path)
    epochs.publish(tmp_path, RUN_A)
    epochs.propose(tmp_path, RUN_A, "ledger.yaml", b"records:\n  - a\n")
    epochs.propose(tmp_path, RUN_B, "hardness.yaml", b"levers:\n  - b\n")
    epochs.propose(tmp_path, RUN_B, "forge_view.yaml", b"view: forge-2\n")

    published = epochs.publish(tmp_path, RUN_A)

    assert published.epoch == 2
    assert sorted(published.applied) == sorted([f"{RUN_A}/0001", f"{RUN_B}/0001", f"{RUN_B}/0002"])
    assert (tmp_path / ".memory" / "ledger.yaml").read_text() == "records:\n  - a\n"
    assert (tmp_path / ".memory" / "hardness.yaml").read_text() == "levers:\n  - b\n"
    assert (tmp_path / ".memory" / "forge_view.yaml").read_text() == "view: forge-2\n"
    assert (tmp_path / ".memory" / "crucible_view.yaml").read_text() == "view: crucible\n"
    assert (tmp_path / epochs.VIEWS_DIR / "2" / "forge_view.yaml").read_text() == "view: forge-2\n"
    assert epochs.check_epochs(str(tmp_path)) == []
    assert epochs.pending_proposals(tmp_path) == []


@bite("shared.md:A66")
def test_publish_refuses_conflicting_proposals_and_stale_bases(tmp_path: Path) -> None:
    memory(tmp_path)
    epochs.publish(tmp_path, RUN_A)
    epochs.propose(tmp_path, RUN_A, "ledger.yaml", b"records:\n  - a\n")
    epochs.propose(tmp_path, RUN_B, "ledger.yaml", b"records:\n  - b\n")

    with pytest.raises(epochs.EpochError) as conflict:
        epochs.publish(tmp_path, RUN_A)
    assert conflict.value.code == "proposal-conflict"
    assert (tmp_path / ".memory" / "ledger.yaml").read_text() == "records: []\n"
    assert epochs.current(tmp_path) == 1

    (tmp_path / epochs.PROPOSALS_DIR / RUN_B / "0001.json").unlink()
    epochs.publish(tmp_path, RUN_A)
    epochs.propose(tmp_path, RUN_B, "hardness.yaml", b"levers:\n  - late\n")
    stale = tmp_path / epochs.PROPOSALS_DIR / RUN_B / "0001.json"
    body = json.loads(stale.read_text())
    body["base_epoch"] = 1
    stale.write_text(json.dumps(body))

    with pytest.raises(epochs.EpochError) as refused:
        epochs.publish(tmp_path, RUN_A)
    assert refused.value.code == "proposal-stale"


def test_check_epochs_refuses_drift_between_root_copies_and_the_current_epoch(
    tmp_path: Path,
) -> None:
    memory(tmp_path)
    epochs.publish(tmp_path, RUN_A)
    (tmp_path / ".memory" / "ledger.yaml").write_text("records:\n  - edited by hand\n")

    findings = epochs.check_epochs(str(tmp_path))

    assert [item.code for item in findings] == ["EPOCH_DRIFT"]
    assert "ledger.yaml" in findings[0].message


def test_check_epochs_refuses_a_tampered_epoch_or_view(tmp_path: Path) -> None:
    memory(tmp_path)
    epochs.publish(tmp_path, RUN_A)
    (tmp_path / epochs.EPOCHS_DIR / "1" / "hardness.yaml").write_text("levers:\n  - x\n")
    (tmp_path / ".memory" / "hardness.yaml").write_text("levers:\n  - x\n")

    codes = {item.code for item in epochs.check_epochs(str(tmp_path))}
    assert codes == {"EPOCH_TAMPERED"}

    (tmp_path / epochs.EPOCHS_DIR / "1" / "hardness.yaml").write_text("levers: []\n")
    (tmp_path / ".memory" / "hardness.yaml").write_text("levers: []\n")
    (tmp_path / epochs.VIEWS_DIR / "1" / "crucible_view.yaml").write_text("view: leak\n")
    codes = {item.code for item in epochs.check_epochs(str(tmp_path))}
    assert codes == {"EPOCH_TAMPERED"}


def test_check_epochs_is_silent_before_the_first_epoch(tmp_path: Path) -> None:
    memory(tmp_path)

    assert epochs.check_epochs(str(tmp_path)) == []


@pytest.mark.parametrize("path", ["../x", "runs/x.yaml", "epochs/1/ledger.yaml", "", "a/b"])
def test_propose_refuses_paths_outside_the_authoritative_set(tmp_path: Path, path: str) -> None:
    memory(tmp_path)
    epochs.publish(tmp_path, RUN_A)

    with pytest.raises(epochs.EpochError) as refused:
        epochs.propose(tmp_path, RUN_B, path, b"x\n")
    assert refused.value.code == "invalid-path"


def test_cli_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    memory(tmp_path)
    monkeypatch.chdir(tmp_path)

    assert epochs.main(["epochs.py", "publish", "./", "--run", RUN_A]) == 0
    assert epochs.main(["epochs.py", "check", "./"]) == 0
    (tmp_path / ".memory" / "ledger.yaml").write_text("records:\n  - hand\n")
    assert epochs.main(["epochs.py", "check", "./"]) == 1
