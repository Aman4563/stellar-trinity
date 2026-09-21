from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import TypeAlias

import pytest
from tools import forensics as f
from tools import harness_config as hc
from tools._harness_config_schema import ApprovalSource

from tests.fidelity_fixtures import load_fixture
from tests.test_harness_config import incident_configuration

Inputs: TypeAlias = tuple[Path, f.FidelityConfig, f.FidelityRoster]


@pytest.fixture
def inputs(tmp_path: Path) -> Inputs:
    raw = json.dumps(
        incident_configuration()
        | {
            "harnessVersion": "2.1.158",
            "maxTurns": 4,
            "wallClockTimeoutSeconds": 60,
            "compactionPolicy": {"enabled": False, "trigger": "none", "thresholdTokens": 168000},
            "observationTruncation": {"maxMessageChars": 100, "maxObservationChars": 100},
        }
    ).encode()
    source = tmp_path / "harness-config.json"
    source.write_bytes(raw)
    digest = hc.harness_config_digest(raw)
    config = f.FidelityConfig(
        source,
        raw,
        digest,
        raw,
        digest,
        hc.HarnessApproval(False, 100, 168000, ApprovalSource.REQUIREMENTS, "operator"),
    )
    root = tmp_path / "trajectories"
    ids = tuple(f"run_{i}" for i in range(8))
    for identity in ids:
        write_trace(root / identity, "clean/claude_code_jsonl")
    roster = f.FidelityRoster(
        1,
        (ids,),
        tuple(f.ScorerReceipt(identity, "synthetic-session", "a" * 64) for identity in ids),
    )
    return root, config, roster


def write_trace(directory: Path, fixture: str) -> None:
    for name, raw in load_fixture(fixture).files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def test_g_fid_config_reports_drift(inputs: Inputs) -> None:
    # Given a changed effective config, distinct from the bound bytes.
    root, config, roster = inputs
    changed = json.loads(config.effective or b"{}") | {"maxTurns": 3}
    # When reconciling the family.
    ledger = f.run_fidelity_family(
        root, "claude_code_jsonl", replace(config, effective=json.dumps(changed).encode()), roster
    )
    # Then drift is retained, not mistaken for clean native evidence.
    assert ledger.config.reconciliation.reason == hc.HarnessConfigFailureReason.HARNESS_CONFIG_DRIFT
    assert ledger.selected_reason == "config-drift"
    assert {row.trial_status for row in ledger.rows} == {"nonconforming"}


@pytest.mark.parametrize(
    "fixture,family,resolved",
    [
        ("clean/claude_code_jsonl", "claude_code_jsonl", "claude_code_jsonl"),
        ("clean/atif_normalized_with_native", "atif_normalized", "claude_code_jsonl"),
        ("planted/claude_code_jsonl/compaction", "claude_code_jsonl", "claude_code_jsonl"),
    ],
)
def test_g_fid_trace_collects_every_rollout(
    inputs: Inputs,
    fixture: str,
    family: str,
    resolved: str,
) -> None:
    # Given eight actual traces, including native accompaniment or a planted violation.
    root, config, roster = inputs
    for identity in roster.groups[0]:
        write_trace(root / identity, fixture)
    # When dispatching every rollout.
    ledger = f.run_fidelity_family(root, family, config, roster)
    # Then all identities survive and native accompaniment resolves natively.
    assert {row.trace.rollout_id for row in ledger.rows} == set(roster.groups[0])
    assert {row.trace.family for row in ledger.rows} == {resolved}
    assert {row.trial_status for row in ledger.rows} == (
        {"nonconforming"} if fixture.startswith("planted") else {"conforming"}
    )


@pytest.mark.parametrize("extra,missing", [(True, False), (False, True), (True, True)])
def test_g_fid_population_refuses_roster_mismatch(
    inputs: Inputs, extra: bool, missing: bool
) -> None:
    # Given an extra, missing, or substituted identity at the same fixed N.
    root, config, roster = inputs
    if extra:
        write_trace(root / "extra", "clean/claude_code_jsonl")
    if missing:
        (root / "run_0").rename(root.parent / "withheld")
    # When comparing against the precommitment.
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # Then population failure blocks independently, with no suppression reason.
    assert ledger.blocked and ledger.group_count == 1
    assert ledger.population.extra == (("extra",) if extra else ())
    assert ledger.population.missing == (("run_0",) if missing else ())
    assert ledger.selected_reason is None
    assert all(row.selected_reason is None for row in ledger.rows)


@pytest.mark.parametrize("receipts", [(), ("b" * 64,)])
def test_g_fid_handoff_refuses_unverifiable_submission(
    inputs: Inputs, receipts: tuple[str, ...]
) -> None:
    # Given missing or contradictory independently received scorer identities.
    root, config, roster = inputs
    roster = replace(
        roster,
        scorer_receipts=tuple(
            f.ScorerReceipt(i, "synthetic-session", d) for i in roster.groups[0] for d in receipts
        ),
    )
    # When checking the native final submission against the scorer.
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # Then a native self-assertion alone cannot establish scorer delivery.
    assert {row.handoff.outcome for row in ledger.rows} == {
        f.FidelityOutcome.INSUFFICIENT_EVIDENCE if not receipts else f.FidelityOutcome.VIOLATION
    }
    assert ledger.selected_reason == "handoff-unverified"


def test_ledger_header_records_rule_and_adapter_versions(inputs: Inputs, tmp_path: Path) -> None:
    # Given a complete corpus and a private test-only audit surface.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # When emitting the JSON-compatible YAML document.
    path = f.emit_fidelity_ledger(ledger, tmp_path / ".audit", project_root=tmp_path)
    body = json.loads(path.read_bytes())
    # Then versions and all per-signal evidence are committed into the digest.
    assert body["trialConformanceRule"] == f.TRIAL_CONFORMANCE_RULE
    assert set(body["adapterVersions"]) == set(f.FIDELITY_FAMILIES)
    assert all(body["adapterVersions"].values())
    assert len(body["rollouts"]) == 8
    assert {item["signal"] for item in body["rollouts"][0]["signals"]} == set(f.SignalClass)
    assert (
        f.project_for_pilot(ledger)["fidelityLedgerDigest"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_ledger_write_is_atomic_and_confined(
    inputs: Inputs,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given an existing private ledger and paths outside its allowed root.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    audit = tmp_path / ".audit"
    path = f.emit_fidelity_ledger(ledger, audit, project_root=tmp_path)
    before = path.read_bytes()
    with pytest.raises(f.FidelityLedgerPathError):
        f.emit_fidelity_ledger(ledger, tmp_path / "public", project_root=tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (audit / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(f.FidelityLedgerPathError):
        f.emit_fidelity_ledger(ledger, audit / "escape", project_root=tmp_path)

    def interrupt(source: str, destination: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
        assert src_dir_fd == dst_dir_fd
        assert destination == "fidelity.yaml"
        assert (audit / source).read_bytes() == before
        raise OSError("interrupted publication")

    monkeypatch.setattr("tools.forensics.ledger.os.replace", interrupt)
    # When publication is interrupted at the atomic seam.
    with pytest.raises(OSError, match="interrupted publication"):
        f.emit_fidelity_ledger(ledger, audit, project_root=tmp_path)
    # Then neither a partial replacement nor a temporary file survives.
    assert path.read_bytes() == before
    assert sorted(p.name for p in audit.iterdir()) == ["escape", "fidelity.yaml"]


def test_projection_carries_only_three_tokens(inputs: Inputs) -> None:
    # Given a derived ledger.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # When projecting through an explicit allowlist.
    projection = f.project_for_pilot(ledger)
    digest = projection.pop("fidelityLedgerDigest")
    # Then the sole metadata entry is a digest; all rollout values are closed tokens.
    assert len(digest) == 64 and int(digest, 16) >= 0
    assert set(projection) == set(roster.groups[0])
    assert set(projection.values()) <= f.TRIAL_STATUSES


@pytest.mark.parametrize(
    "private",
    [
        *(x.value for x in f.FidelityRefusal),
        *(x.value for x in f.SignalClass),
        "./private/evidence.jsonl:174#pre_tokens=168780",
    ],
)
def test_projection_leaks_no_refusal_or_pointer(inputs: Inputs, private: str) -> None:
    # Given private findings carrying each refusal, signal, and a colon-bearing locator.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    finding = f.SignalFinding(
        f.SignalClass(private)
        if private in f.SignalClass.__members__
        else f.SignalClass.COMPACTION,
        f.FidelityOutcome.INSUFFICIENT_EVIDENCE,
        f.FidelityRefusal(private) if private in f.FidelityRefusal.__members__ else None,
        private if ":" in private else "./private:1",
    )
    row = ledger.rows[0]
    ledger = replace(
        ledger, rows=(replace(row, trace=replace(row.trace, findings=(finding,))), *ledger.rows[1:])
    )
    # When serializing only the public projection.
    serialized = json.dumps(f.project_for_pilot(ledger))
    # Then private content never traverses the one-way boundary.
    assert private not in serialized
    assert "./private:1" not in serialized


@pytest.mark.parametrize(
    "fixture,family",
    [
        ("clean/atif_normalized", "atif_normalized"),
        ("adversarial/self_reported_clean", "cybergym_usage"),
    ],
)
def test_g_fid_trace_reports_conversion_only_corpus_as_insufficient(
    inputs: Inputs, fixture: str, family: str
) -> None:
    # Given only ATIF conversion files, not the native fixture's source files.
    original, config, roster = inputs
    root = original.parent / "converted"
    for identity in roster.groups[0]:
        write_trace(root / identity, fixture)
    # When running the complete family.
    ledger = f.run_fidelity_family(root, family, config, roster)
    f.emit_fidelity_ledger(ledger, original.parent / ".audit", project_root=original.parent)
    # Then every row and every projected status remains indeterminate.
    assert {row.trace.overall for row in ledger.rows} == {f.FidelityOutcome.INSUFFICIENT_EVIDENCE}
    assert {row.trial_status for row in ledger.rows} == {"indeterminate"}
    assert {v for k, v in f.project_for_pilot(ledger).items() if k != "fidelityLedgerDigest"} == {
        "indeterminate"
    }
    print(
        "QA private:", ledger.rows[0].trace.findings[0], "projection:", f.project_for_pilot(ledger)
    )


@pytest.mark.parametrize(
    "case,expected",
    [
        ("unapproved", "config-unpinned"),
        ("drift", "config-drift"),
        ("adequacy", "config-inadequate"),
        ("handoff", "handoff-unverified"),
        ("context", "context-uncovered"),
        ("violation", "fidelity-unverified"),
    ],
)
def test_selected_reason_follows_8u_order(inputs: Inputs, case: str, expected: str) -> None:
    # Given overlapping lower-priority findings, plus one earlier reason.
    root, config, roster = inputs
    for identity in roster.groups[0]:
        path = root / identity / "agent.jsonl"
        path.write_bytes(path.read_bytes().replace(b'"status_code":200', b'"status_code":429'))
    if case in {"unapproved", "drift", "adequacy", "handoff"}:
        roster = replace(roster, scorer_receipts=())
    if case in {"unapproved", "drift", "adequacy"}:
        config = replace(config, adequacy=None)
    if case in {"unapproved", "drift"}:
        config = replace(
            config,
            effective=json.dumps(json.loads(config.effective or b"{}") | {"maxTurns": 2}).encode(),
        )
    if case == "unapproved":
        config = replace(config, approved_digest=None)
    if case == "context":
        config = replace(config, trace_version="unsupported")
    # When selecting one private reason from all retained findings.
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # Then the first applicable 8u reason wins for bundle and rollout.
    assert ledger.selected_reason == expected
    assert {row.selected_reason for row in ledger.rows} == {expected}
