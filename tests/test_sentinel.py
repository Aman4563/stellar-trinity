from __future__ import annotations

import json
import re
import subprocess
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from tools import layout, sentinel
from tools._findings import FindingJson, Severity
from tools.sentinel import (
    ALERTS_PATH,
    CHAIN_GENESIS,
    DEFAULT_THRESHOLD,
    EXIT_RECORDED,
    HEAD_PATH,
    LEDGER_PATH,
    WEIGHTS,
    Actor,
    Alert,
    Attempt,
    SabotageCode,
    SentinelFailureReason,
    check_sentinel_chain,
    classify,
    is_repeat,
    read_alerts,
    read_ledger,
    record,
    verify_chain,
)

from tests.bite_shared.registration import bite
from tests.sentinel_signing_fixtures import (
    ACTOR,
    CLEARER,
    ClearanceCase,
    SigningRoot,
    generate_key,
    plant_repeat,
    verified_actor,
)

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
SHA = "b" * 40
ALICE = Actor.for_ci(git_author="Alice <alice@example.test>", github_login="alice")
BOB = Actor.for_ci(git_author="Bob <bob@example.test>", github_login="bob")
ROOT = Path(__file__).parents[1]


@pytest.fixture
def clearance_case(tmp_path: Path) -> ClearanceCase:
    entries = {
        name: generate_key(tmp_path / ".secrets", name.split("@", 1)[0])
        for name in (ACTOR, CLEARER, "observer@trinity.test")
    }
    signing = SigningRoot(tmp_path, entries)
    signing.trust()
    return ClearanceCase(signing, plant_repeat(tmp_path, verified_actor()))


def error(code: str, path: str = "VERDICT.md", message: str = "refused") -> FindingJson:
    return {"code": code, "severity": "error", "path": path, "line": None, "message": message}


def plant(
    root: Path,
    code: str,
    *,
    actor: Actor = ALICE,
    at: datetime = NOW,
    run_id: str = "run-1",
) -> Attempt:
    new, _chain = record(
        root,
        [error(code)],
        actor=actor,
        run_id=run_id,
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=at,
    )
    assert len(new) == 1
    return new[0]


def ledger(root: Path) -> list[Attempt]:
    attempts, defect = read_ledger(root / LEDGER_PATH)
    assert defect is None
    return attempts


# ---- S1, S2: repeat predicate ---------------------------------------------------------------


def test_single_attempt_is_not_a_repeat(tmp_path: Path) -> None:
    first = plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    assert is_repeat(ledger(tmp_path), first) is False
    assert read_alerts(tmp_path / ALERTS_PATH) == ([], None)


def test_second_attempt_inside_window_is_a_repeat(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", at=NOW - timedelta(days=10))
    second = plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", at=NOW, run_id="run-2")
    assert is_repeat(ledger(tmp_path), second, threshold=2) is True
    assert is_repeat(ledger(tmp_path), second) is False


def test_second_attempt_outside_window_is_not_a_repeat(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", at=NOW - timedelta(days=45))
    second = plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", at=NOW, run_id="run-2")
    assert is_repeat(ledger(tmp_path), second) is False


def test_same_code_by_different_actors_repeats_on_the_code_axis(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_DIGEST_MISMATCH", actor=ALICE, at=NOW - timedelta(days=3))
    plant(
        tmp_path,
        "APPROVAL_DIGEST_MISMATCH",
        actor=BOB,
        at=NOW - timedelta(days=2),
        run_id="run-2",
    )
    third = plant(tmp_path, "APPROVAL_DIGEST_MISMATCH", actor=ALICE, at=NOW, run_id="run-3")
    assert is_repeat(ledger(tmp_path), third, threshold=3) is True


def test_same_actor_with_distinct_codes_does_not_repeat(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", actor=ALICE, at=NOW - timedelta(days=3))
    second = plant(tmp_path, "TRINITY_FRESHNESS_DIVERGED", actor=ALICE, at=NOW, run_id="run-2")
    assert is_repeat(ledger(tmp_path), second) is False
    assert alerts(tmp_path) == []


def test_distinct_codes_and_actors_do_not_repeat(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", actor=ALICE, at=NOW - timedelta(days=3))
    second = plant(tmp_path, "TRINITY_FRESHNESS_DIVERGED", actor=BOB, at=NOW, run_id="run-2")
    assert is_repeat(ledger(tmp_path), second) is False


def test_multiple_codes_in_one_run_count_as_one_attempt(tmp_path: Path) -> None:
    first, _chain = record(
        tmp_path,
        [error("APPROVAL_PRODUCER_IS_APPROVER"), error("APPROVAL_DIGEST_MISMATCH")],
        actor=ALICE,
        run_id="run-1",
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=NOW - timedelta(days=3),
    )
    assert len(first) == 2
    assert alerts(tmp_path) == []
    second = plant(tmp_path, "TRINITY_FRESHNESS_DIVERGED", actor=BOB, at=NOW, run_id="run-2")
    assert is_repeat(ledger(tmp_path), second) is False


def test_same_run_retry_is_deduplicated_and_never_repeats(tmp_path: Path) -> None:
    first = plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", run_id="run-1")
    repeated, chain = record(
        tmp_path,
        [error("APPROVAL_PRODUCER_IS_APPROVER")],
        actor=ALICE,
        run_id="run-1",
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=NOW + timedelta(minutes=1),
    )
    assert repeated == []
    assert chain == []
    assert ledger(tmp_path) == [first]
    assert alerts(tmp_path) == []


# ---- S3, S4: chain integrity --------------------------------------------------------------


def test_untouched_chain_verifies(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    plant(tmp_path, "APPROVAL_DIGEST_MISMATCH", actor=BOB, run_id="run-2")
    assert verify_chain(tmp_path) == []
    assert check_sentinel_chain(str(tmp_path)) == []


def test_broken_chain_findings_use_project_relative_paths(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    (tmp_path / LEDGER_PATH).write_text("broken\n", encoding="utf-8")

    findings = check_sentinel_chain(str(tmp_path))

    assert [item.path for item in findings] == ["./.sentinel/attempts.jsonl"]


def test_repeated_attempt_findings_use_project_relative_paths(tmp_path: Path) -> None:
    for index in range(DEFAULT_THRESHOLD):
        plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", run_id=f"run-{index}")

    findings = sentinel.repeated_attempt_findings(tmp_path)

    assert [item.path for item in findings] == ["./.sentinel/alerts.jsonl"]


def test_absent_ledger_is_empty_scope(tmp_path: Path) -> None:
    assert check_sentinel_chain(str(tmp_path)) == []


@bite("shared.md:A25")
def test_rewritten_line_breaks_the_chain(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    plant(tmp_path, "APPROVAL_DIGEST_MISMATCH", run_id="run-2")
    plant(tmp_path, "TRINITY_FRESHNESS_DIVERGED", run_id="run-3")
    path = tmp_path / LEDGER_PATH
    lines = path.read_text(encoding="utf-8").split("\n")
    lines[2] = lines[2].replace('"refused"', '"nothing happened"')
    path.write_text("\n".join(lines), encoding="utf-8")
    findings = verify_chain(tmp_path)
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]
    assert "line 3" in findings[0].message


def test_deleted_tail_after_head_is_a_rollback(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    plant(tmp_path, "APPROVAL_DIGEST_MISMATCH", run_id="run-2")
    path = tmp_path / LEDGER_PATH
    lines = path.read_text(encoding="utf-8").split("\n")
    path.write_text(lines[0] + "\n", encoding="utf-8")
    findings = verify_chain(tmp_path)
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_ROLLBACK]


@pytest.mark.parametrize(
    "head",
    [
        b"not-json",
        b'{"entry_hash":"bad","seq":1}\n',
        b'{"entry_hash":"' + (b"a" * 64) + b'","seq":-1}\n',
        b'{"entry_hash":"' + (b"a" * 64) + b'","extra":1,"seq":1}\n',
    ],
)
def test_malformed_attempt_head_is_chain_broken_and_preserved(tmp_path: Path, head: bytes) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    (tmp_path / HEAD_PATH).write_bytes(head)
    findings = verify_chain(tmp_path)
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]
    record(
        tmp_path,
        [],
        actor=BOB,
        run_id="run-2",
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=NOW,
    )
    preserved = list((tmp_path / sentinel.QUARANTINE_DIRECTORY).glob("head.json.*.corrupt"))
    assert len(preserved) == 1
    assert preserved[0].read_bytes() == head


def test_present_head_with_missing_ledger_is_rollback(tmp_path: Path) -> None:
    sentinel.write_head(tmp_path / HEAD_PATH, 1, "a" * 64)
    findings = verify_chain(tmp_path)
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_ROLLBACK]


@pytest.mark.parametrize("alert_head", [False, True])
@pytest.mark.parametrize("with_ledger", [False, True])
def test_zero_sequence_head_is_chain_broken(
    tmp_path: Path, alert_head: bool, with_ledger: bool
) -> None:
    if with_ledger:
        if alert_head:
            _repeat_ledger(tmp_path)
        else:
            plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    state = tmp_path / sentinel.SENTINEL_DIRECTORY
    state.mkdir(exist_ok=True)
    path = tmp_path / (sentinel.ALERTS_HEAD_PATH if alert_head else HEAD_PATH)
    path.write_text(json.dumps({"entry_hash": "a" * 64, "seq": 0}), encoding="utf-8")

    findings = verify_chain(tmp_path)

    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]


def test_rollback_is_recorded_on_the_next_record(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    plant(tmp_path, "APPROVAL_DIGEST_MISMATCH", run_id="run-2")
    path = tmp_path / LEDGER_PATH
    lines = path.read_text(encoding="utf-8").split("\n")
    path.write_text(lines[0] + "\n", encoding="utf-8")
    new, chain = record(
        tmp_path, [], actor=BOB, run_id="run-3", git_sha=SHA, repo="EtharaOrion/argos", now=NOW
    )
    assert [item.code for item in chain] == [SentinelFailureReason.SENTINEL_CHAIN_ROLLBACK]
    assert [item.code for item in new] == [SabotageCode.SAB_LEDGER_ROLLBACK]
    assert verify_chain(tmp_path) == []
    assert ledger(tmp_path)[-1].previous_hash == ledger(tmp_path)[0].entry_hash


def test_broken_chain_starts_a_new_segment_that_names_the_break(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    corrupt = b"{not json\n"
    (tmp_path / LEDGER_PATH).write_bytes(corrupt)
    new, _chain = record(
        tmp_path, [], actor=BOB, run_id="run-2", git_sha=SHA, repo="EtharaOrion/argos", now=NOW
    )
    assert [item.code for item in new] == [SabotageCode.SAB_LEDGER_ROLLBACK]
    assert new[0].previous_hash == CHAIN_GENESIS
    assert verify_chain(tmp_path) == []
    quarantined = list((tmp_path / sentinel.QUARANTINE_DIRECTORY).glob("attempts.jsonl.*.corrupt"))
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes() == corrupt


def test_corrupt_alert_bytes_are_quarantined_not_erased(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    corrupt = b"not-json\n"
    (tmp_path / ALERTS_PATH).write_bytes(corrupt)
    record(
        tmp_path,
        [error("APPROVAL_DIGEST_MISMATCH")],
        actor=ALICE,
        run_id="run-3",
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=NOW + timedelta(hours=1),
    )
    quarantined = list((tmp_path / sentinel.QUARANTINE_DIRECTORY).glob("alerts.jsonl.*.corrupt"))
    assert len(quarantined) == 1
    assert quarantined[0].read_bytes() == corrupt


def test_malformed_alert_head_is_chain_broken(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    (tmp_path / sentinel.ALERTS_HEAD_PATH).write_text('{"seq":1}', encoding="utf-8")
    findings = verify_chain(tmp_path)
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]


def test_unknown_attempt_fields_invalid_seq_and_hash_are_rejected(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    path = tmp_path / LEDGER_PATH
    original = json.loads(path.read_text(encoding="utf-8"))
    for mutation in (
        {**original, "unknown": 1},
        {**original, "seq": 0},
        {**original, "entry_hash": "z" * 64},
    ):
        path.write_text(
            json.dumps(mutation, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        assert read_ledger(path)[1] is not None


def test_unknown_alert_fields_are_rejected(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    path = tmp_path / ALERTS_PATH
    alert = json.loads(path.read_text(encoding="utf-8"))
    alert["unknown"] = True
    path.write_text(
        json.dumps(alert, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    assert read_alerts(path)[1] is not None


def test_symlinked_sentinel_directory_cannot_write_outside_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / sentinel.SENTINEL_DIRECTORY).symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match=r"unsafe|symbolic"):
        record(
            tmp_path,
            [error("APPROVAL_PRODUCER_IS_APPROVER")],
            actor=ALICE,
            run_id="run-1",
            git_sha=SHA,
            repo="EtharaOrion/argos",
            now=NOW,
        )
    assert list(outside.iterdir()) == []


def test_nonregular_and_symlinked_state_files_fail_closed(tmp_path: Path) -> None:
    state = tmp_path / sentinel.SENTINEL_DIRECTORY
    state.mkdir()
    (tmp_path / LEDGER_PATH).mkdir()
    findings = verify_chain(tmp_path)
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]
    (tmp_path / LEDGER_PATH).rmdir()
    outside = tmp_path / "outside-ledger"
    outside.write_text("secret", encoding="utf-8")
    (tmp_path / LEDGER_PATH).symlink_to(outside)
    findings = verify_chain(tmp_path)
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]
    assert outside.read_text(encoding="utf-8") == "secret"


def test_sloppiness_codes_never_count(tmp_path: Path) -> None:
    new, chain = record(
        tmp_path,
        [error("INTEGRITY_READ_ERROR"), error("FEEDBACK_CHAIN_EMPTY")],
        actor=ALICE,
        run_id="run-1",
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=NOW,
    )
    assert new == []
    assert chain == []
    assert not (tmp_path / LEDGER_PATH).exists()


# ---- S5, S6, S7: predicates ----------------------------------------------------------------


def write_report(root: Path, name: str, headline: str) -> None:
    text = (
        f"# {name}\n\n## Executive summary\n\nwords\n\n## Disposition\n\n"
        f"{headline}\n\n## Findings\n"
    )
    (root / name).write_text(text, encoding="utf-8")


@bite("shared.md:A26")
def test_ship_headline_over_a_failing_gate_is_forged(tmp_path: Path) -> None:
    write_report(tmp_path, "VERDICT.md", "🟢 **SHIP**")
    classified = classify([error("BUNDLE_LAYOUT_MISSING")], root=tmp_path)
    assert [item.code for item in classified] == [SabotageCode.SAB_DISPOSITION_FORGED]
    assert classified[0].findings[0]["code"] == "DISPOSITION_CONTRADICTS_GATE"
    assert classified[0].findings[0]["path"] == "./VERDICT.md"


def test_inert_instrument_witness_carries_a_project_relative_path(tmp_path: Path) -> None:
    (tmp_path / ".audit").mkdir()
    (tmp_path / ".audit" / "g_scan.py").write_text(
        "def g_scan(target):\n    return []\n", encoding="utf-8"
    )
    classified = sentinel.inert_instruments(tmp_path)
    assert classified, "an instrument returning a constant must be witnessed"
    witness = classified[0].findings[0]
    assert witness["path"] == "./.audit/g_scan.py"
    assert str(tmp_path) not in witness["path"]


def test_block_headline_over_a_failing_gate_is_honest(tmp_path: Path) -> None:
    write_report(tmp_path, "VERDICT.md", "🔴 BLOCK.")
    assert classify([error("BUNDLE_LAYOUT_MISSING")], root=tmp_path) == []


def test_absent_or_empty_checkpoint_log_is_not_a_ledger_rollback(tmp_path: Path) -> None:
    assert classify([error("LEDGER_CHECKPOINT_CHAIN_INVALID")], root=tmp_path) == []
    rolled = classify([error("CHECKPOINT_HEAD_ROLLED_BACK")], root=tmp_path)
    assert [item.code for item in rolled] == [SabotageCode.SAB_LEDGER_ROLLBACK]


def test_ship_headline_over_a_clean_gate_is_not_forged(tmp_path: Path) -> None:
    write_report(tmp_path, "VERDICT.md", "🟢 **SHIP**")
    assert classify([], root=tmp_path) == []


def test_ship_mentioned_inside_a_hold_line_is_not_a_ship_claim(tmp_path: Path) -> None:
    write_report(tmp_path, "EDICT.md", "`HOLD:PILOT_REQUIRED`; SHIP is unreachable")
    write_report(tmp_path, "DIRECTIVE.md", "🟡 STALE, CURRENT-unreachable")
    assert classify([error("BUNDLE_LAYOUT_MISSING")], root=tmp_path) == []


def test_current_headline_over_a_failing_gate_is_forged(tmp_path: Path) -> None:
    write_report(tmp_path, "DIRECTIVE.md", "🟢 **CURRENT.** The first envelope was admitted.")
    write_report(tmp_path, "EDICT.md", "`SHIP:INFERRED` for the batch")
    classified = classify([error("BUNDLE_LAYOUT_MISSING")], root=tmp_path)
    paths = sorted(Path(item.findings[0]["path"]).name for item in classified)
    assert paths == ["DIRECTIVE.md", "EDICT.md"]


def test_inert_instrument_is_detected(tmp_path: Path) -> None:
    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "recon.py").write_text(
        "def sandbox_state():\n    return {'hermetic': False, 'available': False}\n\n"
        "def g_con_empty(bundle):\n    if bundle:\n        return gap('no sandbox')\n"
        "    return gap('no bundle')\n",
        encoding="utf-8",
    )
    classified = classify([], root=tmp_path)
    assert [item.code for item in classified] == [SabotageCode.SAB_INERT_INSTRUMENT]
    names = sorted(item["message"].split("(")[0] for item in classified[0].findings)
    assert names == ["g_con_empty", "sandbox_state"]


def test_live_instrument_is_not_inert(tmp_path: Path) -> None:
    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "recon.py").write_text(
        "import shutil\n\ndef sandbox_state():\n"
        "    return {'available': shutil.which('docker') is not None}\n\n"
        "def helper():\n    return 3\n",
        encoding="utf-8",
    )
    assert classify([], root=tmp_path) == []


def test_branching_predicate_is_not_inert(tmp_path: Path) -> None:
    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "predicates.py").write_text(
        "def check_manifest(path):\n    if not path.exists():\n        return False\n"
        "    return True\n\n"
        "def check_digest(actual, expected):\n    if actual != expected:\n"
        "        raise ValueError('mismatch')\n    return True\n",
        encoding="utf-8",
    )
    assert classify([], root=tmp_path) == []


def write_workflow(root: Path, name: str, run: str) -> str:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / name).write_text(
        f"jobs:\n  job:\n    steps:\n      - run: {run}\n", encoding="utf-8"
    )
    return f".github/workflows/{name}"


def test_gate_surface_edit_with_bypass_adds_the_compound_code(tmp_path: Path) -> None:
    gate = write_workflow(tmp_path, "sentinel.yaml", "python3 trinity/tools/sentinel.py record .")
    changed = [gate, "samples/x/task.toml"]
    classified = classify([error("APPROVAL_DIGEST_MISMATCH")], root=tmp_path, changed_paths=changed)
    codes = sorted(str(item.code) for item in classified)
    assert codes == [
        SabotageCode.SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS,
        SabotageCode.SAB_STALE_DIGEST_REUSE,
    ]


def test_codeowners_edit_beside_a_refusal_adds_the_compound_code(tmp_path: Path) -> None:
    classified = classify(
        [error("APPROVAL_DIGEST_MISMATCH")], root=tmp_path, changed_paths=[".github/CODEOWNERS"]
    )
    assert SabotageCode.SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS in {item.code for item in classified}


def test_unrelated_workflow_edit_beside_a_refusal_is_plain(tmp_path: Path) -> None:
    lint = write_workflow(tmp_path, "lint.yaml", "ruff check .")
    changed = [lint, "tools/helper.py", ".github/workflows/missing.yaml"]
    classified = classify([error("APPROVAL_DIGEST_MISMATCH")], root=tmp_path, changed_paths=changed)
    assert [item.code for item in classified] == [SabotageCode.SAB_STALE_DIGEST_REUSE]


def test_gate_surface_edit_without_bypass_is_plain(tmp_path: Path) -> None:
    gate = write_workflow(tmp_path, "sentinel.yaml", "python3 trinity/tools/sentinel.py record .")
    assert classify([], root=tmp_path, changed_paths=[gate]) == []


def test_bypass_without_gate_surface_edit_is_single(tmp_path: Path) -> None:
    classified = classify(
        [error("APPROVAL_DIGEST_MISMATCH")], root=tmp_path, changed_paths=["samples/x/task.toml"]
    )
    assert [item.code for item in classified] == [SabotageCode.SAB_STALE_DIGEST_REUSE]


# ---- S8: alerts and clearances --------------------------------------------------------------


def _repeat_ledger(root: Path) -> None:
    for index in range(1, DEFAULT_THRESHOLD + 1):
        days_ago = DEFAULT_THRESHOLD - index
        plant(
            root,
            "APPROVAL_PRODUCER_IS_APPROVER",
            at=NOW - timedelta(days=days_ago),
            run_id=f"run-{index}",
        )


def alerts(root: Path) -> list[Alert]:
    found, defect = read_alerts(root / ALERTS_PATH)
    assert defect is None, defect
    return found


def test_single_attempt_raises_no_alert(tmp_path: Path) -> None:
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER")
    assert alerts(tmp_path) == []
    assert check_sentinel_chain(str(tmp_path)) == []


def test_attempts_below_the_threshold_raise_no_alert(tmp_path: Path) -> None:
    for index in range(1, DEFAULT_THRESHOLD):
        plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", at=NOW, run_id=f"run-{index}")
    assert len(ledger(tmp_path)) == DEFAULT_THRESHOLD - 1
    assert alerts(tmp_path) == []
    assert check_sentinel_chain(str(tmp_path)) == []


@bite("shared.md:A24")
def test_repeat_raises_an_alert_and_the_gate_refuses_it(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    raised = alerts(tmp_path)
    assert len(raised) == 1
    alert = raised[0]
    assert alert.codes == ("SAB_SELF_APPROVAL",)
    assert (alert.first_seq, alert.last_seq) == (1, DEFAULT_THRESHOLD)
    assert alert.threshold == DEFAULT_THRESHOLD
    assert alert.actor == ALICE
    assert alert.previous_hash == CHAIN_GENESIS
    line = json.loads((tmp_path / ALERTS_PATH).read_text(encoding="utf-8").splitlines()[0])
    assert set(line) == sentinel.ALERT_FIELDS
    findings = check_sentinel_chain(str(tmp_path))
    assert [item.code for item in findings] == [SabotageCode.SAB_REPEATED_ATTEMPT]
    assert "uncleared" in findings[0].message


def test_repeated_attempt_carries_the_highest_weight() -> None:
    assert WEIGHTS[SabotageCode.SAB_REPEATED_ATTEMPT] == max(WEIGHTS.values())
    assert sentinel.FINDING_CODE_MAP["SAB_REPEATED_ATTEMPT"] is SabotageCode.SAB_REPEATED_ATTEMPT


def test_an_uncleared_alert_never_re_enters_the_attempt_ledger(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    before = len(ledger(tmp_path))
    new, _chain = record(
        tmp_path,
        [error("SAB_REPEATED_ATTEMPT")],
        actor=ALICE,
        run_id="run-next",
        git_sha=SHA,
        repo="parent",
        now=NOW + timedelta(hours=1),
    )
    assert new == []
    assert len(ledger(tmp_path)) == before


def test_third_attempt_folds_into_the_standing_alert(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    plant(tmp_path, "APPROVAL_PRODUCER_IS_APPROVER", at=NOW + timedelta(hours=1), run_id="run-next")
    assert len(alerts(tmp_path)) == 1


def _superseded_alert(root: Path) -> Alert:
    """Plant the alert the 2026-09-16 rule raised: one run, one actor, three codes, threshold 2."""
    new, _chain = record(
        root,
        [
            error("APPROVAL_PRODUCER_IS_APPROVER"),
            error("WORK_DIFFERENTIAL_DIGEST_MISMATCH"),
            error("BUNDLE_TRUTH_REGEN_MISMATCH"),
        ],
        actor=ALICE,
        run_id="run-1",
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=NOW,
    )
    assert len(new) == 3
    assert alerts(root) == []
    draft = Alert(
        seq=1,
        actor=ALICE,
        codes=tuple(sorted(str(item.code) for item in new)),
        window_days=30,
        threshold=2,
        first_seq=1,
        last_seq=3,
        repo=new[-1].repo,
        attempts=tuple(sorted(item.entry_hash for item in new)),
        raised_at=NOW,
        previous_hash=CHAIN_GENESIS,
        entry_hash="",
    )
    alert = replace(draft, entry_hash=sentinel.entry_hash_for(sentinel._alert_body(draft)))
    sentinel.append_alerts(root / ALERTS_PATH, [alert])
    sentinel.write_head(root / sentinel.ALERTS_HEAD_PATH, alert.seq, alert.entry_hash)
    return alert


@bite("shared.md:A44")
def test_alert_raised_under_a_superseded_rule_is_re_derived_and_no_longer_blocks(
    tmp_path: Path,
) -> None:
    alert = _superseded_alert(tmp_path)
    assert not sentinel.alert_stands(ledger(tmp_path), alert)
    findings = check_sentinel_chain(str(tmp_path))
    assert [item.code for item in findings] == [SabotageCode.SAB_REPEATED_ATTEMPT]
    assert findings[0].severity is Severity.ADVISORY
    assert "superseded repeat rule" in findings[0].message
    assert "needs no clearance" in findings[0].message
    assert (tmp_path / ALERTS_PATH).read_text(encoding="utf-8").count("\n") == 1


def test_a_standing_alert_is_re_derived_and_still_blocks(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    alert = alerts(tmp_path)[0]
    assert sentinel.alert_stands(ledger(tmp_path), alert)
    findings = check_sentinel_chain(str(tmp_path))
    assert [item.severity for item in findings] == [Severity.ERROR]


def test_a_genuine_repeat_after_a_superseded_alert_raises_a_fresh_alert(tmp_path: Path) -> None:
    _superseded_alert(tmp_path)
    for index in range(2, DEFAULT_THRESHOLD + 1):
        plant(
            tmp_path,
            "APPROVAL_PRODUCER_IS_APPROVER",
            at=NOW + timedelta(hours=index),
            run_id=f"run-{index}",
        )
    raised = alerts(tmp_path)
    assert len(raised) == 2
    assert raised[1].codes == ("SAB_SELF_APPROVAL",)
    severities = [item.severity for item in check_sentinel_chain(str(tmp_path))]
    assert severities == [Severity.ADVISORY, Severity.ERROR]


# ---- a standing refusal carries its arithmetic and its way out -----------------------------


def test_standing_refusal_names_the_counted_runs_and_the_rotation_remedy(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    [finding] = check_sentinel_chain(str(tmp_path))
    assert finding.severity is Severity.ERROR
    assert f"counted {DEFAULT_THRESHOLD} distinct runs at threshold {DEFAULT_THRESHOLD}" in (
        finding.message
    )
    for index in range(1, DEFAULT_THRESHOLD + 1):
        assert f"run-{index}@{SHA[:12]}" in finding.message
    assert "nobody can clear it" in finding.message
    assert ".memory/allowed_signers is absent" in finding.message
    assert sentinel.ROTATION_REMEDY in finding.message
    assert str(tmp_path) not in finding.message


def test_standing_refusal_names_who_can_clear_it(clearance_case: ClearanceCase) -> None:
    root = clearance_case.signing.root
    [finding] = check_sentinel_chain(str(root), NOW)
    assert finding.severity is Severity.ERROR
    assert "clearable now by a signed clearance from 1 of the 1 eligible" in finding.message
    assert finding.message.endswith(f": {CLEARER}")
    assert ACTOR not in finding.message.split("eligible", 1)[1]
    assert sentinel.ROTATION_REMEDY not in finding.message


def test_remedy_names_a_role_nobody_eligible_can_meet(clearance_case: ClearanceCase) -> None:
    root = clearance_case.signing.root
    trust = json.loads((root / ".memory" / "roots.yaml").read_text(encoding="utf-8"))
    trust["revocations"] = [{"principal": CLEARER, "revoked_at": "2026-09-01T00:00:00Z"}]
    (root / ".memory" / "roots.yaml").write_text(json.dumps(trust), encoding="utf-8")
    remedy = sentinel.clearer_remedy(root, clearance_case.alert, evaluation_time=NOW)
    assert remedy.startswith("nobody can clear it under .memory/roots.yaml version 1")
    assert "principal_revoked" in remedy
    assert remedy.endswith(sentinel.ROTATION_REMEDY)
    [finding] = check_sentinel_chain(str(root), NOW)
    assert remedy in finding.message


def test_remedy_names_a_role_bound_only_to_the_alerted_actor(
    clearance_case: ClearanceCase,
) -> None:
    root = clearance_case.signing.root
    trust = json.loads((root / ".memory" / "roots.yaml").read_text(encoding="utf-8"))
    trust["principals"] = [
        {"name": ACTOR, "roles": ["sentinel_clearer"]},
        {"name": "observer@trinity.test", "roles": ["gate_approver"]},
    ]
    (root / ".memory" / "roots.yaml").write_text(json.dumps(trust), encoding="utf-8")
    remedy = sentinel.clearer_remedy(root, clearance_case.alert, evaluation_time=NOW)
    assert f"the only principals bound to sentinel_clearer are the alerted actor ({ACTOR})" in (
        remedy
    )
    assert remedy.endswith(sentinel.ROTATION_REMEDY)


def test_remedy_names_a_root_that_defines_no_clearer_role(clearance_case: ClearanceCase) -> None:
    root = clearance_case.signing.root
    trust = json.loads((root / ".memory" / "roots.yaml").read_text(encoding="utf-8"))
    trust["roles"] = [{"name": "gate_approver", "threshold": 1}]
    trust["principals"] = [{"name": "observer@trinity.test", "roles": ["gate_approver"]}]
    (root / ".memory" / "roots.yaml").write_text(json.dumps(trust), encoding="utf-8")
    remedy = sentinel.clearer_remedy(root, clearance_case.alert, evaluation_time=NOW)
    assert "role_unknown" in remedy
    assert remedy.endswith(sentinel.ROTATION_REMEDY)


def test_superseded_alert_carries_no_remedy_and_standing_alerts_omit_it(tmp_path: Path) -> None:
    _superseded_alert(tmp_path)
    [standing] = sentinel.alert_standings(tmp_path)
    assert standing.superseded and not standing.stands and standing.remedy == ""
    assert sentinel.standing_alerts(tmp_path) == []


def test_verify_and_status_agree_with_the_gate_on_a_superseded_alert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _superseded_alert(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert sentinel.main(["verify", "./"]) == 0
    out = capsys.readouterr().out
    assert "advisory SAB_REPEATED_ATTEMPT" in out
    assert "no standing alert" in out
    assert sentinel.main(["status", "./"]) == 0
    out = capsys.readouterr().out
    assert "alerts: 1 raised, 0 standing, 1 superseded, 0 cleared" in out
    assert "superseded alert seq 1" in out


def test_verify_and_status_refuse_a_standing_alert_and_name_the_remedy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _repeat_ledger(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert sentinel.main(["verify", "./"]) == sentinel.EXIT_REFUSED
    assert "error SAB_REPEATED_ATTEMPT" in capsys.readouterr().out
    assert sentinel.main(["status", "./"]) == sentinel.EXIT_REFUSED
    out = capsys.readouterr().out
    assert "alerts: 1 raised, 1 standing, 0 superseded, 0 cleared" in out
    assert "standing alert seq 1" in out
    assert f"counted {DEFAULT_THRESHOLD} distinct runs" in out
    assert sentinel.ROTATION_REMEDY in out


def _inert_ledger(root: Path, runs: int) -> Attempt:
    last: Attempt | None = None
    for index in range(1, runs + 1):
        last = plant(
            root,
            "SAB_INERT_INSTRUMENT",
            at=NOW + timedelta(hours=index),
            run_id=f"run-{index}",
        )
    assert last is not None
    return last


@bite("shared.md:A84")
def test_inert_instrument_reaches_the_ledger_but_never_repeats(tmp_path: Path) -> None:
    last = _inert_ledger(tmp_path, DEFAULT_THRESHOLD * 2)
    assert len(ledger(tmp_path)) == DEFAULT_THRESHOLD * 2
    assert all(item.code is SabotageCode.SAB_INERT_INSTRUMENT for item in ledger(tmp_path))
    assert is_repeat(ledger(tmp_path), last, threshold=2) is False
    assert alerts(tmp_path) == []
    assert check_sentinel_chain(str(tmp_path)) == []


def test_alert_raised_over_an_inert_instrument_is_superseded_and_no_longer_blocks(
    tmp_path: Path,
) -> None:
    last = _inert_ledger(tmp_path, DEFAULT_THRESHOLD)
    draft = Alert(
        seq=1,
        actor=ALICE,
        codes=(str(SabotageCode.SAB_INERT_INSTRUMENT),),
        window_days=30,
        threshold=DEFAULT_THRESHOLD,
        first_seq=1,
        last_seq=last.seq,
        repo=last.repo,
        attempts=tuple(sorted(item.entry_hash for item in ledger(tmp_path))),
        raised_at=last.captured_at,
        previous_hash=CHAIN_GENESIS,
        entry_hash="",
    )
    alert = replace(draft, entry_hash=sentinel.entry_hash_for(sentinel._alert_body(draft)))
    sentinel.append_alerts(tmp_path / ALERTS_PATH, [alert])
    sentinel.write_head(tmp_path / sentinel.ALERTS_HEAD_PATH, alert.seq, alert.entry_hash)
    assert not sentinel.alert_stands(ledger(tmp_path), alert)
    findings = check_sentinel_chain(str(tmp_path))
    assert [item.code for item in findings] == [SabotageCode.SAB_REPEATED_ATTEMPT]
    assert findings[0].severity is Severity.ADVISORY
    assert "needs no clearance" in findings[0].message
    plant(tmp_path, "SAB_INERT_INSTRUMENT", at=NOW + timedelta(days=1), run_id="run-later")
    assert len(alerts(tmp_path)) == 1


def test_state_codes_are_a_closed_subset_of_the_vocabulary() -> None:
    assert set(sentinel.STATE_CODES) == {SabotageCode.SAB_INERT_INSTRUMENT}
    assert SabotageCode.SAB_REPEATED_ATTEMPT not in sentinel.STATE_CODES
    assert SabotageCode.SAB_SELF_APPROVAL not in sentinel.STATE_CODES


def test_clearance_by_a_distinct_principal_clears_the_refusal(
    clearance_case: ClearanceCase,
) -> None:
    root = clearance_case.signing.root
    before = ledger(root)
    clearance_case.clear()
    assert ledger(root) == before
    assert alerts(root) == [clearance_case.alert]
    assert check_sentinel_chain(str(root), NOW) == []


def test_repeat_after_clearance_raises_a_fresh_alert(clearance_case: ClearanceCase) -> None:
    tmp_path = clearance_case.signing.root
    clearance_case.clear()
    plant(
        tmp_path,
        "APPROVAL_PRODUCER_IS_APPROVER",
        actor=verified_actor(),
        at=NOW + timedelta(days=1),
        run_id="run-next",
    )
    raised = alerts(tmp_path)
    assert len(raised) == 2
    assert raised[1].previous_hash == raised[0].entry_hash
    assert [item.code for item in check_sentinel_chain(str(tmp_path))] == [
        SabotageCode.SAB_REPEATED_ATTEMPT
    ]


@bite("shared.md:A39")
def test_self_clearance_is_refused(clearance_case: ClearanceCase) -> None:
    root = clearance_case.signing.root
    before = ledger(root)
    with pytest.raises(ValueError, match="self_approval"):
        clearance_case.clear(ACTOR)
    assert ledger(root) == before and verify_chain(root) == []
    assert alerts(root) == [clearance_case.alert]
    findings = check_sentinel_chain(str(root), NOW)
    assert [item.code for item in findings] == [SabotageCode.SAB_REPEATED_ATTEMPT]


def test_clearance_naming_another_alert_is_refused(clearance_case: ClearanceCase) -> None:
    root = clearance_case.signing.root
    clearance_case.envelope(
        changes={
            "alert_entry_hash": "f" * 64,
            "repo": clearance_case.alert.repo,
            "attempts": list(clearance_case.alert.attempts),
        }
    )
    assert verify_chain(root) == []
    assert alerts(root) == [clearance_case.alert]
    assert [item.code for item in check_sentinel_chain(str(root), NOW)] == [
        SabotageCode.SAB_REPEATED_ATTEMPT
    ]


def test_rewritten_alert_line_breaks_the_alert_chain(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    path = tmp_path / ALERTS_PATH
    text = path.read_text(encoding="utf-8").replace(
        f'"threshold":{DEFAULT_THRESHOLD}', '"threshold":9'
    )
    path.write_text(text, encoding="utf-8")
    findings = check_sentinel_chain(str(tmp_path))
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]
    assert findings[0].path == "./.sentinel/alerts.jsonl"


def test_deleted_alert_ledger_is_a_rollback(tmp_path: Path) -> None:
    _repeat_ledger(tmp_path)
    (tmp_path / ALERTS_PATH).unlink()
    findings = check_sentinel_chain(str(tmp_path))
    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_ROLLBACK]


def test_cli_clear_round_trip(
    clearance_case: ClearanceCase,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = clearance_case.signing.root
    monkeypatch.chdir(tmp_path)
    alert = alerts(tmp_path)[0]
    assert sentinel.main(["verify", "./"]) == sentinel.EXIT_REFUSED
    assert (
        sentinel.main(["clear", "./", "--alert", alert.entry_hash, "--key", "./.secrets/actor"])
        == sentinel.EXIT_REFUSED
    )
    assert "clear refused:" in capsys.readouterr().err
    assert (
        sentinel.main(["clear", "./", "--alert", alert.entry_hash, "--key", "./.secrets/clearer"])
        == 0
    )
    assert sentinel.main(["verify", "./"]) == 0
    assert sentinel.main(["status", "./"]) == 0
    assert (
        sentinel.main(["clear", "./", "--alert", "0" * 64, "--key", "./.secrets/clearer"])
        == sentinel.EXIT_REFUSED
    )


# ---- CLI --------------------------------------------------------------------------------------


def test_cli_record_verify_status_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps([error("APPROVAL_PRODUCER_IS_APPROVER")]), encoding="utf-8")
    monkeypatch.delenv("GITHUB_ACTOR", raising=False)
    monkeypatch.chdir(tmp_path)
    code = sentinel.main(
        ["record", "./", "--findings", "./findings.json", "--run-id", "run-1", "--ci"]
    )
    assert code == EXIT_RECORDED
    assert sentinel.main(["verify", "./"]) == 0
    assert sentinel.main(["status", "./"]) == 0
    attempts = ledger(tmp_path)
    assert attempts[0].actor.source == "ci"
    assert attempts[0].git_sha == "0" * 40
    head = json.loads((tmp_path / HEAD_PATH).read_text(encoding="utf-8"))
    assert head == {"entry_hash": attempts[0].entry_hash, "seq": 1}
    clean = tmp_path / "clean.json"
    clean.write_text("[]", encoding="utf-8")
    assert sentinel.main(["record", "./", "--findings", "./clean.json"]) == 0


def test_layout_boundary_codes_map_to_submodule_tampering() -> None:
    """A crossed boundary is evidence; an unfinished scaffold never is."""
    for code in layout.BLOCKING_CODES:
        assert sentinel.FINDING_CODE_MAP[code] is SabotageCode.SAB_SUBMODULE_TAMPERED
    for code in layout.LAYOUT_CODES - layout.BLOCKING_CODES:
        assert code not in sentinel.FINDING_CODE_MAP


def test_every_sabotage_and_pipeline_refusal_reaches_the_ledger() -> None:
    """A SAB_ or sealed-bundle refusal that the map does not know never reaches the ledger."""
    emitted: set[str] = set()
    for name in ("sabotage", "pipeline"):
        text = (ROOT / "tools" / f"{name}.py").read_text(encoding="utf-8")
        emitted |= set(
            re.findall(r'"(SAB_[A-Z_]+|PIPELINE_(?:SEALED_MUTATED|UNSEALED_AUDIT))"', text)
        )
    emitted -= {"SAB_READ_ERROR", "SAB_SUBMODULE_UNVERIFIED", "SAB_WORKFLOW_TAMPER_SUSPECT"}
    missing = sorted(code for code in emitted if code not in sentinel.FINDING_CODE_MAP)
    assert missing == []


# ---- streams: one chain per run, repeats aggregated across streams ------------------------


def plant_in(root: Path, stream: str, code: str, *, run_id: str, at: datetime) -> Attempt:
    new, _chain = record(
        root,
        [error(code)],
        actor=ALICE,
        run_id=run_id,
        git_sha=SHA,
        repo="EtharaOrion/argos",
        now=at,
        stream=stream,
    )
    assert len(new) == 1
    return new[0]


@bite("shared.md:A61")
def test_streams_chain_independently_and_both_verify(tmp_path: Path) -> None:
    ada = plant_in(tmp_path, "forge-ada", "SAB_DIRTY_TREE", run_id="forge-ada", at=NOW)
    bob = plant_in(tmp_path, "forge-bob", "SAB_DIRTY_TREE", run_id="forge-bob", at=NOW)

    assert ada.seq == bob.seq == 1
    assert ada.previous_hash == bob.previous_hash == CHAIN_GENESIS
    layout_ada = sentinel.layout(tmp_path, "forge-ada")
    assert layout_ada.ledger == tmp_path / ".sentinel" / "streams" / "forge-ada" / "attempts.jsonl"
    assert layout_ada.ledger.is_file() and layout_ada.head.is_file()
    assert not (tmp_path / LEDGER_PATH).exists()
    assert check_sentinel_chain(str(tmp_path)) == []
    assert sentinel.stream_names(tmp_path) == ["forge-ada", "forge-bob"]


def test_a_broken_stream_is_named_and_the_other_still_verifies(tmp_path: Path) -> None:
    plant_in(tmp_path, "forge-ada", "SAB_DIRTY_TREE", run_id="forge-ada", at=NOW)
    plant_in(tmp_path, "forge-bob", "SAB_DIRTY_TREE", run_id="forge-bob", at=NOW)
    ledger_path = sentinel.layout(tmp_path, "forge-bob").ledger
    ledger_path.write_bytes(ledger_path.read_bytes().replace(b"forge-bob", b"forge-bib", 1))

    findings = check_sentinel_chain(str(tmp_path))

    assert [item.code for item in findings] == [SentinelFailureReason.SENTINEL_CHAIN_BROKEN]
    assert "streams/forge-bob" in findings[0].path
    assert verify_chain(tmp_path, stream="forge-ada") == []


@bite("shared.md:A62")
def test_repeats_aggregate_across_streams_so_run_rotation_cannot_evade(tmp_path: Path) -> None:
    for index in range(DEFAULT_THRESHOLD - 1):
        plant_in(
            tmp_path,
            f"forge-run-{index}",
            "SAB_DIRTY_TREE",
            run_id=f"forge-run-{index}",
            at=NOW + timedelta(minutes=index),
        )
    assert check_sentinel_chain(str(tmp_path)) == []

    last = plant_in(
        tmp_path,
        "forge-run-last",
        "SAB_DIRTY_TREE",
        run_id="forge-run-last",
        at=NOW + timedelta(minutes=DEFAULT_THRESHOLD),
    )

    assert is_repeat(sentinel.all_attempts(tmp_path), last)
    findings = check_sentinel_chain(str(tmp_path))
    assert [item.code for item in findings] == [SabotageCode.SAB_REPEATED_ATTEMPT]
    assert findings[0].severity is Severity.ERROR
    alerts, defect = read_alerts(sentinel.layout(tmp_path, "forge-run-last").alerts)
    assert defect is None and len(alerts) == 1


def test_legacy_ledger_and_streams_share_the_repeat_window(tmp_path: Path) -> None:
    for index in range(DEFAULT_THRESHOLD - 1):
        plant(
            tmp_path, "SAB_DIRTY_TREE", run_id=f"legacy-{index}", at=NOW + timedelta(minutes=index)
        )
    plant_in(
        tmp_path,
        "forge-new",
        "SAB_DIRTY_TREE",
        run_id="forge-new",
        at=NOW + timedelta(minutes=DEFAULT_THRESHOLD),
    )

    codes = [item.code for item in check_sentinel_chain(str(tmp_path))]

    assert codes == [SabotageCode.SAB_REPEATED_ATTEMPT]


def test_stream_names_are_closed_and_never_escape(tmp_path: Path) -> None:
    for bad in ("../x", "a/b", "", ".hidden", "x" * 81):
        with pytest.raises(ValueError, match="stream"):
            sentinel.layout(tmp_path, bad)
