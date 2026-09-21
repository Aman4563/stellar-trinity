"""Synthetic historical trees only; no vendor corpus or shared fidelity fixtures."""

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest
from tools import backfill, forensics
from tools.attest.canonical import JSONValue
from tools.attest.intoto import StatementParseResult
from tools.attest.policies import execution_fidelity


def _bundle(root: Path, family: str = "harbor", count: int = 8) -> Path:
    bundle = root / "synthetic-bundle"
    for number in range(1, count + 1):
        run = bundle / "trajectories" / "synthetic-model" / f"run_{number}"
        run.mkdir(parents=True)
        match family:
            case "harbor":
                (run / "config.json").write_text('{"enable_summarize":false}')
                (run / "result.json").write_text(
                    '{"agent_result":{"metadata":{"summarization_count":0}}}'
                )
            case "deku":
                (run / "usage.json").write_text("{}")
                (run / "trajectory").mkdir()
                (run / "trajectory" / "trajectory.json").write_text('{"schema_version":"1.7"}')
            case "cybergym":
                (run / "usage.json").write_text('{"harness_version":"2.1.159"}')
                (run / "agent.jsonl").write_text(
                    '{"type":"system","subtype":"init","index":0,"version":"2.1.159"}\n'
                )
            case "openhands":
                (run / "run-metadata.json").write_text(
                    '{"harness_version":"1.8","condenser_config":{"type":"noop"}}'
                )
                (run / "metrics.json").write_text("{}")
            case _:
                raise AssertionError(family)
    return bundle


def _plant(bundle: Path) -> None:
    run = bundle / "trajectories" / "synthetic-model" / "run_1"
    (run / "agent").mkdir()
    (run / "agent" / "agent.jsonl").write_text(
        '{"type":"system","subtype":"init","index":0,"version":"2.1.159"}\n'
        '{"type":"system","subtype":"compact_boundary","index":1,'
        '"compact_metadata":{"trigger":"auto","pre_tokens":168780}}\n'
    )


def test_diagnoses_confirmed_suppression(tmp_path: Path) -> None:
    # Given native positive evidence beside misleading counters.
    bundle = _bundle(tmp_path)
    _plant(bundle)
    # When diagnosed through the real adapters.
    report = backfill.diagnose_bundle(bundle)
    # Then suppression wins, without erasing missing coverage.
    assert report.disposition == "confirmed_suppression"
    assert report.confirmed_suppression
    assert report.unknown_coverage


@pytest.mark.parametrize("family", ["harbor", "deku", "cybergym", "openhands", "unrecognized"])
def test_diagnoses_unknown_coverage(tmp_path: Path, family: str) -> None:
    # Given one of the four historical disk layouts, or an unknown layout.
    bundle = _bundle(tmp_path, "harbor" if family == "unrecognized" else family)
    if family == "unrecognized":
        (bundle / "trajectories" / "synthetic-model" / "run_1" / "config.json").unlink()
        # When no known family can explain the run, then refuse explicitly.
        with pytest.raises(backfill.BackfillError, match="FIDELITY_FAMILY_UNRECOGNIZED"):
            backfill.diagnose_bundle(bundle)
        return
    # When diagnosed, then counters and partial native logs never prove clean.
    report = backfill.diagnose_bundle(bundle)
    assert report.disposition == "unknown_coverage"
    assert not report.confirmed_suppression
    assert report.unknown_coverage


def test_diagnoses_insufficient_groups(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given eight runs and controlled full coverage, isolate disposition reduction.
    # Actual historical declarations must never be promoted to authorization.
    bundle = _bundle(tmp_path)

    def covered(trace: forensics.TraceBundle) -> forensics.RolloutFidelity:
        return forensics.RolloutFidelity(
            trace.rollout_id,
            trace.family,
            tuple(
                forensics.SignalFinding(
                    signal, forensics.FidelityOutcome.COVERED_CLEAN, None, "./trace:1"
                )
                for signal in forensics.SignalClass
            ),
        )

    monkeypatch.setattr(forensics, "analyze_trace", covered)
    # When coverage is complete, then sample insufficiency remains independent.
    report = backfill.diagnose_bundle(bundle)
    assert report.disposition == "insufficient_groups"
    assert report.group_count == 1
    assert report.minimum_groups == 6
    assert report.required_groups == 8
    assert report.insufficient_groups
    assert not report.unknown_coverage


@pytest.mark.parametrize("counts", [(8,), (7, 1), (8, 8, 8, 8), (9,)])
def test_eight_rollouts_form_one_group_not_eight(tmp_path: Path, counts: tuple[int, ...]) -> None:
    # Given model configurations whose runs must never be pooled.
    bundle = _bundle(tmp_path, count=counts[0])
    for index, count in enumerate(counts[1:], 1):
        other = _bundle(tmp_path / f"source-{index}", count=count)
        (other / "trajectories" / "synthetic-model").rename(
            bundle / "trajectories" / f"synthetic-model-{index}"
        )
    # When grouped, then only disjoint sets of eight within each model count.
    report = backfill.diagnose_bundle(bundle)
    assert report.rollout_count == sum(counts)
    assert report.group_count == sum(count // 8 for count in counts)
    assert report.comparisons == len(counts)
    assert report.minimum_groups == (9 if len(counts) == 4 else 8 if len(counts) == 2 else 6)
    assert report.insufficient_groups


def test_disposition_precedence_is_fixed(tmp_path: Path) -> None:
    # Given all three independent defects.
    bundle = _bundle(tmp_path)
    _plant(bundle)
    # When reduced, then only the highest-precedence disposition is emitted.
    report = backfill.diagnose_bundle(bundle)
    assert report.disposition == "confirmed_suppression"
    assert all((report.confirmed_suppression, report.unknown_coverage, report.insufficient_groups))


def test_three_reasons_stay_distinct(tmp_path: Path) -> None:
    # Given a complete synthetic CLI corpus.
    assert callable(backfill.main)
    _plant(_bundle(tmp_path))
    # When the real direct-script entry point runs.
    result = subprocess.run(
        [sys.executable, "tools/backfill.py", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    # Then each JSONL bundle carries three separate reasons and one disposition.
    assert result.returncode == 0, result.stderr
    report, summary = [json.loads(line) for line in result.stdout.splitlines()]
    assert report["disposition"] == "confirmed_suppression"
    assert all(
        report[key] for key in ("confirmed_suppression", "unknown_coverage", "insufficient_groups")
    )
    assert summary["bundle_count"] == 1


@pytest.mark.parametrize("relative", [".seed/x.json", "nested/.seed/x.json", "alias/x.json"])
def test_refuses_write_under_seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    # Given lexical and symlink aliases for forbidden output.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".seed").mkdir()
    (tmp_path / "alias").symlink_to(tmp_path / ".seed", target_is_directory=True)
    # When output is requested, then refusal precedes every write.
    with pytest.raises(backfill.BackfillError, match="BACKFILL_FORBIDDEN_WRITE"):
        backfill.write_report((), Path(relative))


def test_refuses_write_under_audit_attestations(tmp_path: Path) -> None:
    # Given an absolute forbidden destination.
    destination = tmp_path / ".audit" / "attestations" / "x.json"
    # When writing, then a named refusal is raised without creating parents.
    with pytest.raises(backfill.BackfillError, match="BACKFILL_FORBIDDEN_WRITE"):
        backfill.write_report((), destination)


def test_module_exposes_no_signing_callable() -> None:
    # Given the public module; when inspecting callables; then no authority surface exists.
    forbidden = ("sign", "attest", "envelope", "dsse")
    assert not [
        name
        for name in dir(backfill)
        if callable(getattr(backfill, name)) and any(word in name.lower() for word in forbidden)
    ]
    assert backfill.BACKFILL_FORBIDDEN_PREFIXES == (".seed/", ".audit/attestations/")


def test_release_mode_is_unreachable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given historical bytes and a release route that must never execute.
    bundle = _bundle(tmp_path)
    (bundle / "execution.json").write_text(
        json.dumps(
            {
                "payloadType": "application/vnd.in-toto+json",
                "payload": base64.b64encode(b"{}").decode(),
                "signatures": [{"keyid": "synthetic-key", "sig": "eA=="}],
            }
        )
    )
    calls: list[bool] = []
    original = execution_fidelity.ExecutionRequirements.parse

    def release(_value: JSONValue) -> None:
        raise AssertionError("release path is unreachable")

    def diagnosis(
        self: execution_fidelity.ExecutionRequirements, value: JSONValue
    ) -> StatementParseResult:
        calls.append(self.release_required)
        return original(self, value)

    monkeypatch.setattr(execution_fidelity, "release_version_failure", release)
    monkeypatch.setattr(execution_fidelity.ExecutionRequirements, "parse", diagnosis)
    # When history is read, then the policy refuses authority in diagnosis mode only.
    report = backfill.diagnose_bundle(bundle)
    assert calls == [False]
    assert report.historical_execution == "EXECUTION_DIAGNOSIS_ONLY"


def test_refuses_oversized_input(tmp_path: Path) -> None:
    # Given a sparse oversized input, never materialized in memory by the reader.
    bundle = _bundle(tmp_path)
    path = bundle / "trajectories" / "synthetic-model" / "run_1" / "result.json"
    with path.open("wb") as stream:
        stream.truncate(forensics.MAX_TRACE_BYTES + 1)
    # When diagnosed, then size is refused rather than reported as clean.
    with pytest.raises(backfill.BackfillError, match="BACKFILL_INPUT_TOO_LARGE"):
        backfill.diagnose_bundle(bundle)
