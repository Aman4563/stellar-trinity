from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.bite_shared.registration import bite
from tests.harness_imports import load_harness

harbor = load_harness("harbor")

FIXTURES = Path(__file__).parent / "fixtures" / "harbor"
PASS_UUID = "1213efa9-10ca-4f0e-bb27-2f6012454212"
FAIL_UUID = "394d9d5c-357d-56c2-81e5-e0a2d32ab101"
STRING_UUID = "1b21d4ac-055a-52e7-b754-0620f337b0d4"
NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
LATEST = "0.23.0"
RELEASED = datetime(2026, 9, 12, tzinfo=UTC)


def codes(findings: list[Any]) -> list[str]:
    return sorted(finding.code for finding in findings)


def write_bundle(root: Path, uuid: str, fixture: str, lane: str = "samples") -> Path:
    bundle = root / lane / uuid
    bundle.mkdir(parents=True)
    shutil.copy(FIXTURES / fixture / "task.toml", bundle / "task.toml")
    return bundle


def write_contract(root: Path, version: str = LATEST, schema: str | None = "1.4") -> None:
    seed = root / ".seed"
    seed.mkdir(exist_ok=True)
    lines = ["archetype: sample", "delivery:", f"  harbor_release: {version}"]
    if schema is not None:
        lines.append(f'  schema_version: "{schema}"')
    lines.append("  other: value")
    (seed / "contract.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_lock(
    root: Path,
    latest: str = LATEST,
    released: datetime = RELEASED,
    resolved: datetime = NOW - timedelta(days=1),
) -> None:
    payload = {
        "latest_version": latest,
        "latest_released_at": released.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resolved_at": resolved.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "pypi",
    }
    (root / "harbor.lock").write_text(json.dumps(payload), encoding="utf-8")


def write_receipt(
    root: Path,
    uuid: str,
    *,
    version: str = LATEST,
    ok: bool = True,
    message: str = "",
    digest: str | None = None,
    validator: str | None = None,
) -> Path:
    manifest = root / "samples" / uuid / "task.toml"
    payload = {
        "harbor_version": version,
        "task_toml_sha256": digest or hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "ok": ok,
        "message": message,
        "validated_at": "2026-09-16T11:00:00Z",
        "validator_digest": validator or harbor.VALIDATOR_DIGEST,
    }
    path: Path = harbor.receipt_path(root, uuid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def clean_parent(root: Path) -> None:
    write_bundle(root, PASS_UUID, "pass-0.23.0")
    write_contract(root)
    write_lock(root)
    write_receipt(root, PASS_UUID)


@pytest.fixture
def _uv_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harbor.shutil, "which", lambda name: f"/usr/bin/{name}")


@pytest.fixture
def _uv_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harbor.shutil, "which", lambda _name: None)


# ---- currency: clean half ----------------------------------------------------


def test_currency_clean_parent_passes(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    assert harbor.check_harbor_currency(str(tmp_path), NOW) == []


def test_currency_no_bundles_is_empty_scope(tmp_path: Path) -> None:
    assert harbor.check_harbor_currency(str(tmp_path), NOW) == []


def test_currency_one_minor_behind_within_cadence_passes(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_contract(tmp_path, version="0.22.1")
    write_receipt(tmp_path, PASS_UUID, version="0.22.1")
    assert harbor.check_harbor_currency(str(tmp_path), NOW) == []


# ---- currency: planted halves -------------------------------------------------


@bite("shared.md:A15")
def test_currency_pin_missing(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    (tmp_path / ".seed" / "contract.yaml").write_text("delivery:\n  other: 1\n", encoding="utf-8")
    assert "HARBOR_PIN_MISSING" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_pin_missing_without_contract(tmp_path: Path) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    write_lock(tmp_path)
    assert "HARBOR_PIN_MISSING" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


@pytest.mark.parametrize("value", ["latest", ">=0.23", "0.23", "0.24.0.dev202609160000", "*"])
def test_currency_pin_malformed(tmp_path: Path, value: str) -> None:
    clean_parent(tmp_path)
    write_contract(tmp_path, version=value)
    assert "HARBOR_PIN_MALFORMED" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_retired_spelling_in_contract_is_malformed(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    (tmp_path / ".seed" / "contract.yaml").write_text(
        "delivery:\n  harbor_version: 0.23.0\n", encoding="utf-8"
    )
    assert "HARBOR_PIN_MALFORMED" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_retired_spelling_in_manifest_metadata_is_malformed(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_bundle(tmp_path, STRING_UUID, "fail-string-authors")
    write_receipt(tmp_path, STRING_UUID)
    found = harbor.check_harbor_currency(str(tmp_path), NOW)
    malformed = [f for f in found if f.code == "HARBOR_PIN_MALFORMED"]
    assert len(malformed) == 1
    assert malformed[0].path.endswith(f"{STRING_UUID}/task.toml")
    assert "metadata.harbor_version" in malformed[0].message


@bite("shared.md:A16")
def test_currency_pin_two_minors_behind_is_stale(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_contract(tmp_path, version="0.21.0")
    write_receipt(tmp_path, PASS_UUID, version="0.21.0")
    assert "HARBOR_PIN_STALE" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_pin_one_minor_behind_after_thirty_days_is_stale(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_contract(tmp_path, version="0.22.0")
    write_receipt(tmp_path, PASS_UUID, version="0.22.0")
    write_lock(tmp_path, released=NOW - timedelta(days=31))
    assert "HARBOR_PIN_STALE" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_pin_major_behind_is_stale(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_contract(tmp_path, version="0.23.0")
    write_lock(tmp_path, latest="1.0.0")
    assert "HARBOR_PIN_STALE" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_receipt_missing_is_untested(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    harbor.receipt_path(tmp_path, PASS_UUID).unlink()
    assert codes(harbor.check_harbor_currency(str(tmp_path), NOW)) == ["HARBOR_PIN_UNTESTED"]


def test_currency_receipt_for_other_release_is_untested(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_receipt(tmp_path, PASS_UUID, version="0.22.0")
    assert codes(harbor.check_harbor_currency(str(tmp_path), NOW)) == ["HARBOR_PIN_UNTESTED"]


def test_currency_lock_missing(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    (tmp_path / "harbor.lock").unlink()
    assert "HARBOR_LOCK_MISSING" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_lock_malformed(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    (tmp_path / "harbor.lock").write_text('{"latest_version": 3}', encoding="utf-8")
    assert "HARBOR_LOCK_MALFORMED" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


@bite("shared.md:A18")
def test_currency_lock_stale(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_lock(tmp_path, resolved=NOW - timedelta(days=45))
    assert "HARBOR_LOCK_STALE" in codes(harbor.check_harbor_currency(str(tmp_path), NOW))


def test_currency_lock_fresh_within_fourteen_days_passes(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_lock(tmp_path, resolved=NOW - timedelta(days=13))
    assert harbor.check_harbor_currency(str(tmp_path), NOW) == []


def test_currency_schema_drift(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_contract(tmp_path, schema="1.3")
    assert codes(harbor.check_harbor_currency(str(tmp_path), NOW)) == ["HARBOR_SCHEMA_DRIFT"]


def test_currency_no_contract_schema_pin_is_not_drift(tmp_path: Path) -> None:
    clean_parent(tmp_path)
    write_contract(tmp_path, schema=None)
    assert harbor.check_harbor_currency(str(tmp_path), NOW) == []


def test_currency_delivery_lane_is_covered(tmp_path: Path) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0", lane="delivery")
    write_contract(tmp_path)
    write_lock(tmp_path)
    assert codes(harbor.check_harbor_currency(str(tmp_path), NOW)) == ["HARBOR_PIN_UNTESTED"]


def test_currency_staging_lane_is_covered(tmp_path: Path) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0", lane="staging")
    write_contract(tmp_path)
    write_lock(tmp_path)
    assert codes(harbor.check_harbor_currency(str(tmp_path), NOW)) == ["HARBOR_PIN_UNTESTED"]


# ---- validate check ------------------------------------------------------------


def test_validate_clean_receipt_passes(tmp_path: Path, _uv_present: None) -> None:
    clean_parent(tmp_path)
    assert harbor.check_harbor_validate(str(tmp_path), NOW) == []


@bite("shared.md:A17")
def test_validate_rejected_manifest_carries_harbor_message(
    tmp_path: Path, _uv_present: None
) -> None:
    clean_parent(tmp_path)
    write_bundle(tmp_path, FAIL_UUID, "fail-authors-0.2.0-shape")
    write_receipt(tmp_path, FAIL_UUID, ok=False, message="task.authors.0.name: Field required")
    found = harbor.check_harbor_validate(str(tmp_path), NOW)
    assert codes(found) == ["HARBOR_SCHEMA_INVALID"]
    assert "task.authors.0.name: Field required" in found[0].message
    assert found[0].path.endswith(f"{FAIL_UUID}/task.toml")


def test_validate_receipt_bound_to_stale_manifest_is_invalid(
    tmp_path: Path, _uv_present: None
) -> None:
    clean_parent(tmp_path)
    manifest = tmp_path / "samples" / PASS_UUID / "task.toml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    found = harbor.check_harbor_validate(str(tmp_path), NOW)
    assert codes(found) == ["HARBOR_SCHEMA_INVALID"]
    assert "different task.toml" in found[0].message


def test_validate_receipt_from_other_validator_is_tampered(
    tmp_path: Path, _uv_present: None
) -> None:
    clean_parent(tmp_path)
    write_receipt(tmp_path, PASS_UUID, validator="0" * 64)
    assert codes(harbor.check_harbor_validate(str(tmp_path), NOW)) == ["HARBOR_RECEIPT_TAMPERED"]


def test_validate_malformed_receipt_is_tampered(tmp_path: Path, _uv_present: None) -> None:
    clean_parent(tmp_path)
    harbor.receipt_path(tmp_path, PASS_UUID).write_text("{}", encoding="utf-8")
    assert codes(harbor.check_harbor_validate(str(tmp_path), NOW)) == ["HARBOR_RECEIPT_TAMPERED"]


def test_validate_missing_receipt_with_uv_is_error(tmp_path: Path, _uv_present: None) -> None:
    clean_parent(tmp_path)
    harbor.receipt_path(tmp_path, PASS_UUID).unlink()
    found = harbor.check_harbor_validate(str(tmp_path), NOW)
    assert codes(found) == ["HARBOR_RECEIPT_MISSING"]
    assert found[0].severity is harbor.Severity.ERROR


def test_validate_missing_receipt_without_uv_is_advisory_gap(
    tmp_path: Path, _uv_absent: None
) -> None:
    clean_parent(tmp_path)
    harbor.receipt_path(tmp_path, PASS_UUID).unlink()
    found = harbor.check_harbor_validate(str(tmp_path), NOW)
    assert codes(found) == ["HARBOR_VALIDATOR_UNAVAILABLE"]
    assert found[0].severity is harbor.Severity.ADVISORY


def test_checks_registry_names_both_checks() -> None:
    assert [name for name, _ in harbor.CHECKS] == ["harbor_currency", "harbor_validate"]


# ---- validate runner (subprocess mocked) -------------------------------------------


def fake_runner(
    installed: str, verdicts: dict[str, tuple[bool, str]]
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert cmd[:2] == ["uv", "run"]
        assert "--no-project" in cmd
        assert f"harbor=={installed}" in cmd or "--with" in cmd
        assert kwargs["input"] == harbor.VALIDATOR_SCRIPT
        assert kwargs["shell"] is False
        lines = [json.dumps({"harbor": installed})]
        for path in cmd[cmd.index("-") + 1 :]:
            ok, message = verdicts.get(Path(path).parent.name, (True, ""))
            lines.append(json.dumps({"path": path, "ok": ok, "message": message}))
        return subprocess.CompletedProcess(cmd, 0, "\n".join(lines) + "\n", "")

    return run


def test_validate_writes_receipts_bound_to_manifest_digest(
    tmp_path: Path, _uv_present: None
) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    write_bundle(tmp_path, FAIL_UUID, "fail-authors-0.2.0-shape")
    verdicts = {FAIL_UUID: (False, "task.name: Field required")}
    run = harbor.validate(tmp_path, LATEST, runner=fake_runner(LATEST, verdicts), now=NOW)
    assert run.error is None
    assert run.receipts[PASS_UUID].ok is True
    assert run.receipts[FAIL_UUID].ok is False
    receipt = harbor.read_receipt(harbor.receipt_path(tmp_path, FAIL_UUID))
    assert receipt is not None
    assert receipt.message == "task.name: Field required"
    assert receipt.harbor_version == LATEST
    assert receipt.validator_digest == harbor.VALIDATOR_DIGEST
    manifest = tmp_path / "samples" / FAIL_UUID / "task.toml"
    assert receipt.task_toml_sha256 == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert harbor.check_harbor_validate(str(tmp_path), NOW)[0].code == "HARBOR_SCHEMA_INVALID"


def test_validate_refuses_when_installed_release_differs(tmp_path: Path, _uv_present: None) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    run = harbor.validate(tmp_path, LATEST, runner=fake_runner("0.22.0", {}), now=NOW)
    assert run.error is not None
    assert "harbor==0.23.0" in run.error
    assert not harbor.receipt_path(tmp_path, PASS_UUID).exists()


def test_validate_refuses_floating_version(tmp_path: Path, _uv_present: None) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    run = harbor.validate(tmp_path, "latest", runner=fake_runner(LATEST, {}), now=NOW)
    assert run.error is not None


def test_validate_reports_uv_absence(tmp_path: Path, _uv_absent: None) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    run = harbor.validate(tmp_path, LATEST, runner=fake_runner(LATEST, {}), now=NOW)
    assert run.error is not None
    assert "uv" in run.error


def test_validate_reports_timeout(tmp_path: Path, _uv_present: None) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")

    def run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, 1)

    result = harbor.validate(tmp_path, LATEST, runner=run, now=NOW)
    assert result.error is not None
    assert not harbor.receipt_path(tmp_path, PASS_UUID).exists()


def test_validate_uuid_filter_selects_one_bundle(tmp_path: Path, _uv_present: None) -> None:
    write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    write_bundle(tmp_path, FAIL_UUID, "fail-authors-0.2.0-shape")
    run = harbor.validate(tmp_path, LATEST, [PASS_UUID], runner=fake_runner(LATEST, {}), now=NOW)
    assert list(run.receipts) == [PASS_UUID]
    assert not harbor.receipt_path(tmp_path, FAIL_UUID).exists()


# ---- resolve (urllib mocked) ----------------------------------------------------------


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def pypi_document() -> dict[str, Any]:
    def files(stamp: str) -> list[dict[str, str]]:
        return [{"upload_time_iso_8601": stamp}]

    return {
        "releases": {
            "0.22.0": files("2026-08-22T10:00:00.000000Z"),
            "0.23.0": files("2026-09-12T09:30:00.000000Z"),
            "0.24.0.dev202609160000": files("2026-09-16T01:00:00.000000Z"),
            "0.9.0": files("2026-01-01T00:00:00.000000Z"),
            "1.0.0rc1": files("2026-09-15T00:00:00.000000Z"),
        }
    }


def test_resolve_writes_lock_from_latest_stable_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(harbor.request, "urlopen", lambda *_a, **_k: FakeResponse(pypi_document()))
    lock = harbor.resolve(tmp_path, now=NOW)
    assert lock.latest_version == "0.23.0"
    assert lock.latest_released_at == datetime(2026, 9, 12, 9, 30, tzinfo=UTC)
    written = json.loads((tmp_path / "harbor.lock").read_text(encoding="utf-8"))
    assert written["latest_version"] == "0.23.0"
    assert written["resolved_at"] == "2026-09-16T12:00:00Z"
    assert written["source"] == "pypi"


def test_resolve_offline_reads_existing_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_lock(tmp_path, latest="0.22.0")

    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("offline resolve must not touch the network")

    monkeypatch.setattr(harbor.request, "urlopen", boom)
    assert harbor.resolve(tmp_path, offline=True).latest_version == "0.22.0"


def test_resolve_network_failure_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise OSError("no route")

    monkeypatch.setattr(harbor.request, "urlopen", boom)
    with pytest.raises(harbor.HarborError):
        harbor.resolve(tmp_path, now=NOW)


def test_resolve_without_stable_release_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = {"releases": {"0.24.0.dev1": [{"upload_time_iso_8601": "2026-09-16T00:00:00Z"}]}}
    monkeypatch.setattr(harbor.request, "urlopen", lambda *_a, **_k: FakeResponse(document))
    with pytest.raises(harbor.HarborError):
        harbor.resolve(tmp_path, now=NOW)


# ---- pin resolution ------------------------------------------------------------------


def test_pin_reads_contract_first(tmp_path: Path) -> None:
    write_bundle(tmp_path, STRING_UUID, "fail-string-authors")
    write_contract(tmp_path, version="0.23.0")
    assert harbor.pin(tmp_path).version == "0.23.0"


def test_pin_ignores_unrelated_nested_keys(tmp_path: Path) -> None:
    (tmp_path / ".seed").mkdir()
    (tmp_path / ".seed" / "contract.yaml").write_text(
        "other:\n  harbor_release: 0.1.0\ndelivery:\n  nested:\n    harbor_release: 0.2.0\n"
        "  harbor_release: 0.23.0\n",
        encoding="utf-8",
    )
    assert harbor.pin(tmp_path).version == "0.23.0"


def test_pin_falls_back_to_manifest_metadata_release(tmp_path: Path) -> None:
    bundle = write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    manifest = bundle / "task.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "\n[metadata.extra]\nx = 1\n", encoding="utf-8"
    )
    text = manifest.read_text(encoding="utf-8").replace(
        "[metadata]\n", '[metadata]\nharbor_release = "0.22.0"\n', 1
    )
    manifest.write_text(text, encoding="utf-8")
    assert harbor.pin(tmp_path).version == "0.22.0"


# ---- migration ---------------------------------------------------------------------------


def test_migrate_delivered_argos_reaches_current_shape(tmp_path: Path) -> None:
    write_bundle(tmp_path, FAIL_UUID, "fail-authors-0.2.0-shape")
    diff = harbor.migrate(tmp_path, FAIL_UUID, dry_run=False)
    assert diff.startswith("---")
    document = tomllib.loads((tmp_path / "samples" / FAIL_UUID / "task.toml").read_text())
    assert document["schema_version"] == "1.4"
    assert document["task"]["name"] == f"{tmp_path.name}-{FAIL_UUID[:8]}".join(["ethara/", ""])
    assert document["task"]["version"] == "1.0.0"
    assert all("name" in author and "email" in author for author in document["task"]["authors"])
    assert document["task"]["authors"][0] == {
        "name": "gautam.dubey",
        "email": "gautam.dubey@ethara.ai",
    }
    assert document["verifier"]["network_mode"] == "no-network"
    assert document["agent"]["network_mode"] == "no-network"
    assert document["task"]["uuid_v5"] == FAIL_UUID or "uuid_v5" in document["task"]
    assert document["upstream_provenance"]["source"]["pull_request"] == 3461


def test_migrate_string_authors_and_retired_key(tmp_path: Path) -> None:
    write_bundle(tmp_path, STRING_UUID, "fail-string-authors")
    harbor.migrate(tmp_path, STRING_UUID, dry_run=False, org="deku")
    document = tomllib.loads((tmp_path / "samples" / STRING_UUID / "task.toml").read_text())
    assert document["task"]["authors"][0] == {
        "name": "utsav.jain",
        "email": "utsav.jain@ethara.ai",
    }
    assert document["task"]["name"] == "deku/talent-roster-reel"
    assert "harbor_version" not in document["metadata"]
    assert document["metadata"]["category"] == "Greenfield"


def test_migrate_dry_run_leaves_bytes_untouched(tmp_path: Path) -> None:
    bundle = write_bundle(tmp_path, FAIL_UUID, "fail-authors-0.2.0-shape")
    before = (bundle / "task.toml").read_bytes()
    diff = harbor.migrate(tmp_path, FAIL_UUID)
    assert "no-network" in diff
    assert (bundle / "task.toml").read_bytes() == before


def test_migrate_current_manifest_is_a_no_op(tmp_path: Path) -> None:
    bundle = write_bundle(tmp_path, PASS_UUID, "pass-0.23.0")
    before = (bundle / "task.toml").read_text(encoding="utf-8")
    assert harbor.migrate(tmp_path, PASS_UUID, dry_run=False) == ""
    assert (bundle / "task.toml").read_text(encoding="utf-8") == before


def test_migrate_unknown_bundle_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(harbor.HarborError):
        harbor.migrate(tmp_path, PASS_UUID)


# ---- CLI ------------------------------------------------------------------------------------


def test_cli_check_renders_findings_and_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    _uv_present: None,
) -> None:
    clean_parent(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert harbor.main(["check", "./"]) == 0
    harbor.receipt_path(tmp_path, PASS_UUID).unlink()
    assert harbor.main(["check", "./", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert {entry["code"] for entry in payload} == {
        "HARBOR_PIN_UNTESTED",
        "HARBOR_RECEIPT_MISSING",
    }


def test_cli_pin_prints_release(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    clean_parent(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert harbor.main(["pin", "./"]) == 0
    assert capsys.readouterr().out.strip() == LATEST


def test_cli_validate_uses_pin_and_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    clean_parent(tmp_path)
    write_bundle(tmp_path, FAIL_UUID, "fail-authors-0.2.0-shape")
    monkeypatch.setattr(harbor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        harbor.subprocess, "run", fake_runner(LATEST, {FAIL_UUID: (False, "task.name: required")})
    )
    monkeypatch.chdir(tmp_path)
    assert harbor.main(["validate", "./"]) == 1
    out = capsys.readouterr().out
    assert f"{FAIL_UUID}: INVALID" in out
    assert f"{PASS_UUID}: OK" in out
