from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tools import operations
from tools.attest.backend_ssh import SshKeygenBackend
from tools.operations import (
    CHAIN_GENESIS,
    OPERATION_CODES,
    Operation,
    SigningPolicy,
    Verb,
    chain_findings,
    entry_hash,
    sign_operation,
    verify_operation,
    write_operation,
)

from tests.bite_shared.registration import bite
from tests.sentinel_signing_fixtures import generate_key, write_trust

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
PROJECT = "EtharaOrion/argos"
RUN = "crucible-alice-20260918t120000z-cccccc"
ALICE = "alice@trinity.test"
MALLORY = "mallory@trinity.test"
ARTIFACT = "a" * 64


@pytest.fixture
def keys(tmp_path: Path) -> dict[str, tuple[Path, str]]:
    return {
        ALICE: generate_key(tmp_path / "secrets", "alice"),
        MALLORY: generate_key(tmp_path / "secrets", "mallory"),
    }


@pytest.fixture
def enrolled(tmp_path: Path, keys: dict[str, tuple[Path, str]]) -> Path:
    write_trust(
        tmp_path,
        entries=keys,
        roles={operations.ROLE: 1, "bystander": 1},
        bindings={ALICE: (operations.ROLE,), MALLORY: ("bystander",)},
    )
    return tmp_path


def policy(root: Path) -> SigningPolicy:
    return SigningPolicy(
        allowed_signers=root / ".memory" / "allowed_signers",
        trust_root=root / ".memory" / "roots.yaml",
        trusted_version=1,
        evaluation_time=NOW,
    )


def operation(
    *,
    seq: int = 1,
    previous: str = CHAIN_GENESIS,
    principal: str = ALICE,
    verb: Verb = Verb.CLAIM,
    artifact: str = ARTIFACT,
) -> Operation:
    return Operation(
        project=PROJECT,
        run_id=RUN,
        verb=verb,
        artifact_digest=artifact,
        seq=seq,
        previous=previous,
        principal=principal,
    )


def backend() -> SshKeygenBackend:
    return SshKeygenBackend()


# ---- the payload is the statement, and the hash chains it ------------------------------------


def test_the_entry_hash_covers_every_field() -> None:
    base = operation()
    for changed in (
        replace(base, verb=Verb.VERDICT),
        replace(base, artifact_digest="b" * 64),
        replace(base, seq=2),
        replace(base, previous="c" * 64),
        replace(base, principal=MALLORY),
        replace(base, run_id="crucible-bob-20260918t120000z-dddddd"),
        replace(base, project="other/repo"),
    ):
        assert entry_hash(changed) != entry_hash(base)


def test_the_entry_hash_is_stable_across_equal_operations() -> None:
    assert entry_hash(operation()) == entry_hash(operation())


# ---- verification binds the signer to the claimed principal ----------------------------------


def test_an_operation_signed_by_its_named_principal_verifies(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    envelope = sign_operation(backend(), operation(), key_path=keys[ALICE][0])
    verified, findings = verify_operation(backend(), envelope.to_json(), policy(enrolled))
    assert findings == []
    assert verified is not None
    assert verified.principal == ALICE
    assert verified.entry_hash == entry_hash(operation())


@bite("shared.md:A100")
def test_an_operation_naming_a_principal_other_than_its_signer_is_refused(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    claimed = operation(principal=MALLORY)
    envelope = sign_operation(backend(), claimed, key_path=keys[ALICE][0])
    verified, findings = verify_operation(backend(), envelope.to_json(), policy(enrolled))
    assert verified is None
    assert [item.code for item in findings] == ["OPERATION_PRINCIPAL_MISMATCH"]


def test_an_operation_by_a_principal_outside_the_role_is_refused(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    claimed = operation(principal=MALLORY)
    envelope = sign_operation(backend(), claimed, key_path=keys[MALLORY][0])
    verified, findings = verify_operation(backend(), envelope.to_json(), policy(enrolled))
    assert verified is None
    assert [item.code for item in findings] == ["OPERATION_UNAUTHORIZED"]


def test_a_payload_edited_after_signing_is_refused(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    envelope = sign_operation(backend(), operation(), key_path=keys[ALICE][0])
    document = json.loads(envelope.to_json())
    decoded = base64.b64decode(document["payload"])
    assert b'"seq":1' in decoded
    document["payload"] = base64.b64encode(decoded.replace(b'"seq":1', b'"seq":9')).decode()
    verified, findings = verify_operation(
        backend(), json.dumps(document).encode("utf-8"), policy(enrolled)
    )
    assert verified is None
    assert [item.code for item in findings] == ["OPERATION_ENVELOPE_INVALID"]


def test_an_unsigned_or_unparseable_envelope_is_refused(enrolled: Path) -> None:
    verified, findings = verify_operation(backend(), b"{}", policy(enrolled))
    assert verified is None
    assert [item.code for item in findings] == ["OPERATION_ENVELOPE_INVALID"]


def test_an_absent_trust_root_refuses_rather_than_passes(
    tmp_path: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    write_trust(
        tmp_path,
        entries=keys,
        roles={operations.ROLE: 1, "bystander": 1},
        bindings={ALICE: (operations.ROLE,), MALLORY: ("bystander",)},
    )
    (tmp_path / ".memory" / "roots.yaml").unlink()
    envelope = sign_operation(backend(), operation(), key_path=keys[ALICE][0])
    verified, findings = verify_operation(backend(), envelope.to_json(), policy(tmp_path))
    assert verified is None
    assert [item.code for item in findings] == ["OPERATION_UNAUTHORIZED"]


def test_a_revoked_trusted_version_refuses_a_rolled_back_root(
    tmp_path: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    write_trust(
        tmp_path,
        entries=keys,
        roles={operations.ROLE: 1, "bystander": 1},
        bindings={ALICE: (operations.ROLE,), MALLORY: ("bystander",)},
        version=1,
    )
    envelope = sign_operation(backend(), operation(), key_path=keys[ALICE][0])
    rolled_back = SigningPolicy(
        allowed_signers=tmp_path / ".memory" / "allowed_signers",
        trust_root=tmp_path / ".memory" / "roots.yaml",
        trusted_version=2,
        evaluation_time=NOW,
    )
    verified, findings = verify_operation(backend(), envelope.to_json(), rolled_back)
    assert verified is None
    assert [item.code for item in findings] == ["OPERATION_UNAUTHORIZED"]


# ---- the chain orders one run's operations ---------------------------------------------------


def test_a_well_formed_chain_passes(enrolled: Path, keys: dict[str, tuple[Path, str]]) -> None:
    first = operation(seq=1)
    second = operation(seq=2, previous=entry_hash(first), verb=Verb.VERDICT)
    assert chain_findings([verified(enrolled, keys, first), verified(enrolled, keys, second)]) == []


def verified(
    root: Path, keys: dict[str, tuple[Path, str]], item: Operation
) -> operations.VerifiedOperation:
    envelope = sign_operation(backend(), item, key_path=keys[item.principal][0])
    found, findings = verify_operation(backend(), envelope.to_json(), policy(root))
    assert found is not None, findings
    return found


def test_a_chain_that_does_not_start_at_one_is_refused(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    codes = [item.code for item in chain_findings([verified(enrolled, keys, operation(seq=2))])]
    assert codes == ["OPERATION_CHAIN_BROKEN"]


@bite("shared.md:A101")
def test_a_chain_whose_previous_does_not_link_is_refused(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    first = operation(seq=1)
    forged = operation(seq=2, previous="f" * 64, verb=Verb.VERDICT)
    codes = [
        item.code
        for item in chain_findings(
            [verified(enrolled, keys, first), verified(enrolled, keys, forged)]
        )
    ]
    assert codes == ["OPERATION_CHAIN_BROKEN"]


def test_a_chain_that_skips_a_sequence_number_is_refused(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    first = operation(seq=1)
    skipped = operation(seq=3, previous=entry_hash(first), verb=Verb.VERDICT)
    codes = [
        item.code
        for item in chain_findings(
            [verified(enrolled, keys, first), verified(enrolled, keys, skipped)]
        )
    ]
    assert codes == ["OPERATION_CHAIN_BROKEN"]


def test_two_runs_in_one_chain_are_refused(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    first = operation(seq=1)
    foreign = Operation(
        project=PROJECT,
        run_id="crucible-bob-20260918t120000z-dddddd",
        verb=Verb.VERDICT,
        artifact_digest=ARTIFACT,
        seq=2,
        previous=entry_hash(first),
        principal=ALICE,
    )
    codes = [
        item.code
        for item in chain_findings(
            [verified(enrolled, keys, first), verified(enrolled, keys, foreign)]
        )
    ]
    assert codes == ["OPERATION_CHAIN_BROKEN"]


# ---- operations live inside the run namespace they authorize ---------------------------------


def test_write_operation_places_the_envelope_under_the_run_namespace(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    envelope = sign_operation(backend(), operation(), key_path=keys[ALICE][0])
    path = write_operation(enrolled, operation(), envelope)
    assert path.is_file()
    assert path.parent == enrolled / ".audit" / "runs" / RUN / "operations"
    assert path.name == "0001.json"
    found, findings = verify_operation(backend(), path.read_bytes(), policy(enrolled))
    assert findings == []
    assert found is not None


def test_read_operations_returns_the_run_chain_in_sequence_order(
    enrolled: Path, keys: dict[str, tuple[Path, str]]
) -> None:
    first = operation(seq=1)
    second = operation(seq=2, previous=entry_hash(first), verb=Verb.VERDICT)
    for item in (second, first):
        write_operation(enrolled, item, sign_operation(backend(), item, key_path=keys[ALICE][0]))
    found, findings = operations.read_operations(enrolled, RUN, backend(), policy(enrolled))
    assert findings == []
    assert [item.operation.seq for item in found] == [1, 2]
    assert chain_findings(found) == []


def test_the_artifact_digest_names_the_record_the_operation_authorizes() -> None:
    record = b'{"uuid": "x", "outcome": "clean"}\n'
    digest = hashlib.sha256(record).hexdigest()
    assert operation(artifact=digest).artifact_digest == digest


def test_every_emitted_code_is_in_the_closed_vocabulary(enrolled: Path) -> None:
    _, findings = verify_operation(backend(), b"not an envelope", policy(enrolled))
    assert findings
    assert {item.code for item in findings} <= set(OPERATION_CODES)
