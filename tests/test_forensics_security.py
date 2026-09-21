"""Regression coverage for the robustness audit's filesystem and JSON boundaries."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from tools import forensics as f
from tools import harness_config as hc
from tools.attest import intoto
from tools.attest.merkle import TrajectoryDigest, TrajectoryManifest, TrajectoryManifestEntry
from tools.attest.policies import execution
from tools.attest.policies.execution import resolve_trajectory_documents
from tools.backfill_disk import children
from tools.backfill_models import BackfillError
from tools.forensics import family, family_config, reading
from tools.forensics.family_config import config_standing
from tools.forensics.ledger import ledger_bytes

from tests.test_attest_intoto import EXECUTION_COLLATERAL, valid_execution_v2
from tests.test_forensics_family import Inputs, inputs

__all__ = ["inputs"]


def test_foreign_audit_is_refused(inputs: Inputs) -> None:
    # Given a candidate-controlled audit directory.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # When publishing outside the project's auditor root, then refuse.
    with pytest.raises(f.FidelityLedgerPathError):
        f.emit_fidelity_ledger(
            ledger, root.parent / "deliverables/x/.audit", project_root=root.parent
        )


def test_run_audit_namespace_is_accepted(inputs: Inputs) -> None:
    # Given a project-owned run namespace.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    # When publishing, then preserve the canonical ledger bytes.
    path = f.emit_fidelity_ledger(
        ledger, root.parent / ".audit/runs/run-12345", project_root=root.parent
    )
    assert path.read_bytes() == ledger_bytes(ledger)


@pytest.mark.parametrize("raw", [b'"\\ud800"', b'{"\\udfff": 1}', b"[" * 100000])
def test_json_refuses_depth_and_surrogates(raw: bytes) -> None:
    # Given hostile JSON, when decoding, then emit the typed refusal.
    with pytest.raises(reading.TraceReadError):
        reading.document(b'{"value":' + raw + b"}")


def test_directory_only_expansion_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given more directories than the discovery entry budget.
    for index in range(5):
        (tmp_path / str(index)).mkdir()
    monkeypatch.setattr(family, "MAX_DISCOVERY_ENTRIES", 4, raising=False)
    # When discovering, then refuse without silently dropping directories.
    with pytest.raises(reading.TraceReadError):
        family._rollout_roots(tmp_path)


def test_oversized_config_is_refused_before_read(
    inputs: Inputs, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a valid config larger than the configured cap.
    _, config, _ = inputs
    monkeypatch.setattr(family_config, "MAX_CONFIG_BYTES", 8, raising=False)
    # When checking standing, then the oversized config cannot be pinned.
    assert not config_standing(config).pinned


def test_oversized_trajectory_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Given an oversized document with a manifest entry.
    (tmp_path / "trace.json").write_bytes(b" " * 9)
    monkeypatch.setattr(execution, "MAX_TRAJECTORY_BYTES", 8, raising=False)
    manifest = TrajectoryManifest(
        "test", (TrajectoryManifestEntry(0, "run", "./trace.json", TrajectoryDigest("a" * 64)),)
    )
    # When resolving, then no document bytes are admitted.
    documents, outcome = resolve_trajectory_documents(tmp_path, manifest)
    assert documents is None and not outcome.accepted


def test_backfill_refuses_symlinked_ancestor(tmp_path: Path) -> None:
    # Given an alias above the supplied bundle.
    (tmp_path / "real/bundle").mkdir(parents=True)
    (tmp_path / "alias").symlink_to(tmp_path / "real", target_is_directory=True)
    # When listing the bundle, then refuse the ancestor, not just the leaf.
    with pytest.raises(BackfillError):
        children(tmp_path / "alias/bundle")


@pytest.mark.parametrize("changed", [False, True])
def test_harness_collateral_uses_canonical_digest(changed: bool) -> None:
    # Given a signed canonical digest and differently formatted collateral.
    parsed = intoto.parse_statement(valid_execution_v2())
    assert parsed.statement is not None
    predicate = parsed.statement.predicate
    assert isinstance(predicate, intoto.ExecutionPredicateV2)
    raw = b'{"value":1}'
    descriptor = replace(
        predicate.harness_config, digest=intoto.DigestSet(hc.harness_config_digest(raw))
    )
    statement = replace(parsed.statement, predicate=replace(predicate, harness_config=descriptor))
    collateral = dict(EXECUTION_COLLATERAL)
    for resource in intoto.required_collateral(statement):
        if resource.name not in collateral:
            collateral[resource.name] = resource.name.encode()
    # Other added descriptors bind their actual raw bytes.
    predicate = statement.predicate
    assert isinstance(predicate, intoto.ExecutionPredicateV2)
    statement = replace(
        statement,
        predicate=replace(
            predicate,
            **{
                field: replace(
                    getattr(predicate, field),
                    digest=intoto.DigestSet(
                        hashlib.sha256(collateral[getattr(predicate, field).name]).hexdigest()
                    ),
                )
                for field in (
                    "effective_config_reconciliation",
                    "population_roster",
                    "observation_capture",
                )
            },
        ),
    )
    collateral[descriptor.name] = json.dumps({"value": 2 if changed else 1}, indent=2).encode()
    # When verifying collateral, then only a value change fails.
    assert intoto.validate_collateral(statement, collateral).accepted is not changed
