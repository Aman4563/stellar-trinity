from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tools import release_evidence, runs, subject, tracker
from tools._findings import Severity

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
CLOSED = "2026-09-17T15:00:00Z"
RUN = "forge-ada-1"


def run_report(
    root: Path,
    instrument: str,
    run_id: str,
    disposition: str,
    *,
    principal: str = "ada",
) -> Path:
    """A run namespace shaped exactly like tests/test_reports.py builds one."""
    directory = runs.open_run(root, instrument, run_id, principal=principal, now=NOW)
    body = (
        "## Executive summary\n\nsummary of the run\n\n"
        f"## Disposition\n\n{disposition}\n\n"
        "## Findings\n\n- one finding\n\n"
        "## Coverage gaps\n\n- one gap\n\n"
        "## Escalations\n\nnone\n\n"
        "## Flag legend\n\nlegend\n"
    )
    (directory / "report.md").write_text(body, encoding="utf-8")
    (directory / "progress.yaml").write_text(
        "phase: Phase 2\nphases_done: 3\nphases_total: 6\ngates_done: 1\ngates_total: 3\n"
        "open_gates: [design, audit]\ngaps: 1\n",
        encoding="utf-8",
    )
    (directory / "disposition.json").write_text(
        json.dumps(
            {
                "schema": "trinity.qualification/v2",
                "instrument": instrument,
                "run_id": run_id,
                "disposition": disposition,
                "subject_digest": "a" * 64,
                "trinity_commit": "b" * 40,
                "generated_at": "2026-09-17T12:00:00Z",
                "producer": principal,
                "approver": "unsigned",
            }
        ),
        encoding="utf-8",
    )
    return directory


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def card_of(root: Path, instrument: str = "FORGE", run_id: str = RUN) -> Path:
    return runs.run_dir(root, instrument, run_id) / "tracker.json"


def emit(*argv: str) -> int:
    return tracker.main(["tracker.py", "card", "./", *argv])


def test_card_derives_fields_from_run_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = run_report(tmp_path, "FORGE", RUN, "HOLD:PILOT_REQUIRED")
    monkeypatch.chdir(tmp_path)

    code = emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED)

    assert code == 0
    payload = json.loads(card_of(tmp_path).read_text(encoding="utf-8"))
    assert payload == {
        "schema": "trinity.tracker-card/v1",
        "instrument": "FORGE",
        "run_id": RUN,
        "principal": "ada",
        "started_at": "2026-09-17T12:00:00Z",
        "closed_at": CLOSED,
        "disposition": "HOLD:PILOT_REQUIRED",
        "phase": "Phase 2",
        "phases_done": 3,
        "phases_total": 6,
        "gates_done": 1,
        "gates_total": 3,
        "open_gates": ["audit", "design"],
        "gaps": 1,
        "sources": {
            "run.json": digest(directory / "run.json"),
            "report.md": digest(directory / "report.md"),
            "progress.yaml": digest(directory / "progress.yaml"),
        },
        "parser_version": 1,
    }
    body = card_of(tmp_path).read_text(encoding="utf-8")
    assert body == json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def test_card_is_idempotent_and_preserves_closed_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_report(tmp_path, "FORGE", RUN, "SHIP_ELIGIBLE")
    monkeypatch.chdir(tmp_path)
    assert emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED) == 0
    frozen = card_of(tmp_path).read_bytes()

    later = emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", "2026-09-18T09:00:00Z")
    clockless = emit("--instrument", "FORGE", "--run-id", RUN)

    assert (later, clockless) == (0, 0)
    assert card_of(tmp_path).read_bytes() == frozen
    assert json.loads(frozen)["closed_at"] == CLOSED


def test_card_refuses_a_changed_source_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    directory = run_report(tmp_path, "FORGE", RUN, "SHIP_ELIGIBLE")
    monkeypatch.chdir(tmp_path)
    assert emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED) == 0
    frozen = card_of(tmp_path).read_bytes()
    (directory / "report.md").write_text("## Disposition\n\nBLOCK\n", encoding="utf-8")
    capsys.readouterr()

    code = emit("--instrument", "FORGE", "--run-id", RUN, "--json")

    assert code == 3
    assert json.loads(capsys.readouterr().out) == {
        "written": False,
        "path": f"./.seed/runs/{RUN}/tracker.json",
        "code": "TRACKER_CARD_CONFLICT",
    }
    assert card_of(tmp_path).read_bytes() == frozen


def test_card_refuses_an_identity_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_report(tmp_path, "CRUCIBLE", "crucible-ada-1", "HOLD")
    directory = run_report(tmp_path, "FORGE", RUN, "HOLD")
    monkeypatch.chdir(tmp_path)

    foreign = emit("--instrument", "FORGE", "--run-id", "crucible-ada-1")
    marker = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    marker["instrument"] = "CRUCIBLE"
    (directory / "run.json").write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    disowned = emit("--instrument", "FORGE", "--run-id", RUN)

    assert (foreign, disowned) == (3, 3)
    assert not card_of(tmp_path).exists()
    assert not card_of(tmp_path, "CRUCIBLE", "crucible-ada-1").exists()


def test_card_refuses_a_missing_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    directory = run_report(tmp_path, "FORGE", RUN, "HOLD")
    (directory / "progress.yaml").unlink()
    monkeypatch.chdir(tmp_path)

    assert emit("--instrument", "FORGE", "--run-id", RUN) == 3
    assert not card_of(tmp_path).exists()


def test_card_is_in_subject_output_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_report(tmp_path, "FORGE", RUN, "HOLD")
    (tmp_path / ".seed" / "runs" / RUN / "contract.yaml").write_text("a: 1\n", encoding="utf-8")
    before = subject.subject_digest(tmp_path, "FORGE", RUN)
    monkeypatch.chdir(tmp_path)

    assert emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED) == 0

    paths = {entry.path for entry in subject.subject_manifest(tmp_path, "FORGE", RUN)}
    assert f".seed/runs/{RUN}/tracker.json" not in paths
    assert f".seed/runs/{RUN}/contract.yaml" in paths
    assert subject.subject_digest(tmp_path, "FORGE", RUN) == before
    assert "tracker.json" in subject.OUTPUT_NAMES


def test_card_is_a_sealing_path() -> None:
    assert release_evidence.is_sealing_path(f".seed/runs/{RUN}/tracker.json")
    assert release_evidence.is_sealing_path(".memory/runs/engram-ada-1/tracker.json")
    assert release_evidence.is_sealing_path(".audit/runs/crucible-ada-1/tracker.json")
    assert not release_evidence.is_sealing_path(f".seed/runs/{RUN}/contract.yaml")
    assert not release_evidence.is_sealing_path(f".seed/runs/{RUN}/nested/tracker.json")


@pytest.mark.parametrize(
    "mutate",
    [
        "unreadable",
        "not-an-object",
        "wrong-schema",
        "missing-key",
        "extra-key",
        "foreign-run",
        "unclosed",
        "calendar-close",
        "parser-version",
        "bool-count",
        "negative-count",
        "empty-phase",
        "unsorted-gates",
        "invalid-sources",
    ],
)
def test_malformed_card_is_a_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutate: str
) -> None:
    run_report(tmp_path, "FORGE", RUN, "HOLD")
    monkeypatch.chdir(tmp_path)
    assert emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED) == 0
    assert tracker.check_tracker_cards("./") == []
    path = card_of(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    match mutate:
        case "unreadable":
            path.write_text("{not json", encoding="utf-8")
        case "not-an-object":
            path.write_text("[]", encoding="utf-8")
        case "wrong-schema":
            payload["schema"] = "trinity.tracker-card/v2"
        case "missing-key":
            del payload["gaps"]
        case "extra-key":
            payload["ended_at"] = CLOSED
        case "foreign-run":
            payload["run_id"] = "forge-bob-1"
        case "unclosed":
            payload["closed_at"] = None
        case "null-fields":
            payload.update(dict.fromkeys((*tracker.COUNT_NAMES, "sources", "disposition")))
        case "early-close":
            payload["closed_at"] = "2000-01-01T00:00:00Z"
        case "calendar-close":
            payload["closed_at"] = "2026-02-30T00:00:00Z"
        case "parser-version":
            payload["parser_version"] = True
        case "bool-count":
            payload["gaps"] = True
        case "negative-count":
            payload["gaps"] = -1
        case "empty-phase":
            payload["phase"] = " "
        case "unsorted-gates":
            payload["open_gates"] = ["z", "a"]
        case "invalid-sources":
            payload["sources"]["run.json"] = "A" * 64
        case _:
            raise AssertionError(mutate)
    if mutate not in {"unreadable", "not-an-object"}:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    frozen = path.read_bytes()

    findings = tracker.check_tracker_cards("./")

    assert [item.code for item in findings] == ["TRACKER_CARD_MALFORMED"]
    assert findings[0].severity is Severity.ERROR
    assert findings[0].path == f"./.seed/runs/{RUN}/tracker.json"
    assert path.read_bytes() == frozen
    with pytest.raises(tracker.TrackerError) as refused:
        tracker.write_card(tracker.Target(tmp_path, "FORGE", RUN))
    expected = tracker.IDENTITY_MISMATCH if mutate == "foreign-run" else tracker.CONFLICT
    assert refused.value.code == expected


def test_card_with_null_fields_is_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_malformed_card_is_a_finding(tmp_path, monkeypatch, "null-fields")


def test_card_closed_before_started_is_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_malformed_card_is_a_finding(tmp_path, monkeypatch, "early-close")


@pytest.mark.parametrize("source", ("report.md", "progress.yaml"))
def test_lawful_resume_supersedes_the_card_below_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    # Given a frozen run whose derived source was rewritten by a resume under the same run id.
    directory = run_report(tmp_path, "FORGE", RUN, "HOLD")
    monkeypatch.chdir(tmp_path)
    assert emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED) == 0
    frozen = card_of(tmp_path).read_bytes()
    path = directory / source
    path.write_bytes(path.read_bytes() + b"\n")
    # When the cards are scanned.
    findings = tracker.check_tracker_cards("./")
    # Then the card is superseded, not malformed, and the finding never reaches error severity.
    assert [(item.code, item.severity) for item in findings] == [
        (tracker.SUPERSEDED, Severity.ADVISORY)
    ]
    assert findings[0].message == f"the run continued after closure: {source} moved"
    assert card_of(tmp_path).read_bytes() == frozen
    # And re-emitting over the moved bytes is still the contract's conflict, never a repair.
    with pytest.raises(tracker.TrackerError) as refused:
        tracker.write_card(tracker.Target(tmp_path, "FORGE", RUN))
    assert refused.value.code == tracker.CONFLICT
    assert card_of(tmp_path).read_bytes() == frozen


def test_moved_run_json_is_malformed_not_superseded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a frozen run whose identity source moved while its identity fields still match.
    directory = run_report(tmp_path, "FORGE", RUN, "HOLD")
    monkeypatch.chdir(tmp_path)
    assert emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED) == 0
    marker = directory / "run.json"
    marker.write_bytes(marker.read_bytes() + b"\n")
    # When the cards are scanned.
    findings = tracker.check_tracker_cards("./")
    # Then the card no longer binds its identity and stays an error.
    assert [(item.code, item.severity) for item in findings] == [
        (tracker.MALFORMED, Severity.ERROR)
    ]
    assert findings[0].message == "the card does not bind the current run.json bytes"


@pytest.mark.parametrize("source", tracker.SOURCE_NAMES)
def test_absent_bound_source_is_input_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    # Given a frozen run whose bound source was removed after closure.
    directory = run_report(tmp_path, "FORGE", RUN, "HOLD")
    monkeypatch.chdir(tmp_path)
    assert emit("--instrument", "FORGE", "--run-id", RUN, "--closed-at", CLOSED) == 0
    (directory / source).unlink()
    # When the cards are scanned.
    findings = tracker.check_tracker_cards("./")
    # Then the absence is named as a missing input rather than an unreadable card.
    expected = tracker.MALFORMED if source == "run.json" else tracker.INPUT_MISSING
    assert [(item.code, item.severity) for item in findings] == [(expected, Severity.ERROR)]
    if source != "run.json":
        assert findings[0].message == f"the card binds {source}, which is absent or unreadable"
        with pytest.raises(tracker.TrackerError) as refused:
            tracker.write_card(tracker.Target(tmp_path, "FORGE", RUN))
        assert refused.value.code == tracker.INPUT_MISSING


def test_directory_valued_card_is_a_finding(tmp_path: Path) -> None:
    # Given a run whose tracker.json path is a directory rather than a file.
    directory = run_report(tmp_path, "FORGE", "forge-ada-1", "HOLD:PILOT_REQUIRED")
    (directory / "tracker.json").mkdir()
    # When the cards are checked.
    findings = tracker.check_tracker_cards(str(tmp_path))
    # Then the unreadable card is named rather than skipped.
    assert [item.code for item in findings] == ["TRACKER_CARD_MALFORMED"]
