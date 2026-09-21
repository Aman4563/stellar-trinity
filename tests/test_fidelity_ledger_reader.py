import json
from pathlib import Path

import pytest
from tools.forensics import ledger as storage
from tools.forensics.bundle import MAX_TRACE_BYTES

from tests.fidelity_binding_fixtures import fidelity_ledger


@pytest.mark.parametrize(
    "mode",
    [
        "clean",
        "malformed",
        "oversized",
        "symlink",
        "audit_symlink",
        "forged_status",
        "operator_disagreement",
        "duplicate_key",
        "unknown_field",
        "noncanonical",
    ],
)
def test_bounded_ledger_reader(tmp_path: Path, mode: str) -> None:
    # Given: emitted ledger bytes or an unsafe replacement of that private resource.
    ledger = fidelity_ledger(dict.fromkeys((f"r{i}" for i in range(8)), "conforming"))
    audit = tmp_path / ".audit"
    path = storage.emit_fidelity_ledger(ledger, audit, project_root=tmp_path)
    if mode == "malformed":
        path.write_bytes(b'{"private": "COMPACTION"}')
    if mode == "oversized":
        path.write_bytes(b" " * (MAX_TRACE_BYTES + 1))
    if mode == "symlink":
        path.rename(audit / "target")
        path.symlink_to(audit / "target")
    if mode == "audit_symlink":
        audit.rename(tmp_path / "elsewhere")
        audit.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    body = json.loads(storage.ledger_bytes(ledger))
    if mode == "forged_status":
        body["rollouts"][0]["trialStatus"] = "nonconforming"
        path.write_text(json.dumps(body))
    if mode == "operator_disagreement":
        body["rollouts"][0]["operatorStatus"] = "nonconforming"
        path.write_text(json.dumps(body))
    if mode == "duplicate_key":
        path.write_bytes(storage.ledger_bytes(ledger).replace(b"{", b'{"groupCount":1,', 1))
    if mode == "unknown_field":
        body["unknown"] = "private"
        path.write_text(json.dumps(body))
    if mode == "noncanonical":
        path.write_text(json.dumps(body, indent=2))
    # When: the shared reader opens the auditor resource with a fixed byte budget.
    if mode in {"clean", "noncanonical"}:
        result = storage.read_fidelity_ledger(audit)
        # Then: reconstruction preserves canonical bytes and derived status.
        assert storage.ledger_bytes(result) == storage.ledger_bytes(ledger)
    else:
        with pytest.raises(storage.FidelityLedgerReadError, match=r"^Fidelity ledger unavailable$"):
            storage.read_fidelity_ledger(audit)
        # Then: unsafe or malformed evidence cannot provide a projection.
