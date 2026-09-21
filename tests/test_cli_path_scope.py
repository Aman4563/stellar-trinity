from __future__ import annotations

import importlib
from pathlib import Path
from typing import NoReturn

import pytest
from tools import gate as gate_tool
from tools import harbor, incident_probe, incident_store, pipeline, probe, sabotage, sentinel
from tools import release as release_tool

from tests.harness_imports import integrity


def unexpected(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("path rejection must happen before operational reads or writes")


@pytest.mark.parametrize("bad", ["outside", "../outside", "./../outside"])
def test_parent_operational_clis_reject_traversal_before_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gate_tool, "run_gate", unexpected)
    monkeypatch.setattr(release_tool, "check_release", unexpected)
    monkeypatch.setattr(harbor, "pin", unexpected)
    monkeypatch.setattr(pipeline, "verify", unexpected)
    monkeypatch.setattr(sentinel, "check_sentinel_chain", unexpected)
    monkeypatch.setattr(sabotage, "run_checks", unexpected)
    monkeypatch.setattr(integrity, "_run_parent_at", unexpected)

    assert (
        gate_tool.main(["gate.py", bad, "--instrument", "FORGE", "--moment", "report", "--check"])
        == gate_tool.EXIT_USAGE
    )
    assert release_tool.main(["release.py", bad]) == 1
    assert harbor.main(["pin", bad]) == 2
    assert pipeline.main(["pipeline.py", "verify", bad]) == 2
    assert sentinel.main(["verify", bad]) == sentinel.EXIT_REFUSED
    assert sabotage.main([bad]) == 2
    assert integrity.main(["integrity.py", "parent", bad]) == 2


def test_parent_operational_clis_reject_absolute_before_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    absolute = str(tmp_path / "candidate")
    test_parent_operational_clis_reject_traversal_before_work(tmp_path, monkeypatch, absolute)


def test_parent_operational_clis_reject_symlink_before_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-parent"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    test_parent_operational_clis_reject_traversal_before_work(tmp_path, monkeypatch, "./link")


@pytest.mark.parametrize("bad", ["outside", "../outside", "./../outside"])
def test_incident_and_probe_clis_reject_traversal_before_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(incident_probe, "probe", unexpected)
    monkeypatch.setattr(incident_store, "load_config", unexpected)
    monkeypatch.setattr(probe, "prepare_manifest", unexpected)

    assert incident_probe.main([bad]) == 1
    assert incident_store.main(["status", "--config", bad]) == incident_store.EXIT_FAILURE
    assert probe.main(["probe.py", "prepare", bad, "./manifest.json", "--seed", "seed"]) == 1


def test_incident_and_probe_clis_reject_absolute_before_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    absolute = str(tmp_path / "candidate")
    test_incident_and_probe_clis_reject_traversal_before_work(tmp_path, monkeypatch, absolute)


def test_incident_and_probe_clis_reject_symlink_before_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-incident"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    test_incident_and_probe_clis_reject_traversal_before_work(tmp_path, monkeypatch, "./link")


@pytest.mark.parametrize("bad", ["outside", "../outside", "./../outside"])
def test_attest_cli_rejects_traversal_before_policy_or_artifact_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    attest_main = importlib.import_module("tools.attest.__main__")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(attest_main, "load_gate_policy", unexpected)

    result = attest_main.main(
        [
            "tools.attest",
            "verify",
            bad,
            "./artifact",
            "./trust-root",
            "./allowed-signers",
            "./collateral.json",
        ]
    )

    assert result == 2


def test_attest_cli_rejects_absolute_before_policy_or_artifact_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_attest_cli_rejects_traversal_before_policy_or_artifact_reads(
        tmp_path, monkeypatch, str(tmp_path / "envelope")
    )


def test_attest_cli_rejects_symlink_before_policy_or_artifact_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-attest"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    test_attest_cli_rejects_traversal_before_policy_or_artifact_reads(
        tmp_path, monkeypatch, "./link"
    )
