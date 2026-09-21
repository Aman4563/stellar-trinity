from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from tools import epochs, operations, runs
from tools.attest.backend_ssh import SshKeygenBackend
from tools.operations import SigningPolicy
from tools.transition import (
    TRANSITION_CODES,
    TransitionContextError,
    TrustedContext,
    validate_transition,
)

from tests.bite_shared.registration import bite
from tests.sentinel_signing_fixtures import generate_key, write_trust

ALICE = "alice"
BOB = "bob"
FORGE_RUN = "forge-alice-20260918t120000z-aaaaaa"
BOB_RUN = "forge-bob-20260918t120000z-bbbbbb"
AUDIT_RUN = "crucible-alice-20260918t120000z-cccccc"
RIVAL_RUN = "crucible-bob-20260918t120000z-dddddd"
UUID = "3f1d7d0c-5a2b-5c3d-8e4f-6a7b8c9d0e1f"
DIGEST = "a" * 64
POLICY = "roots-digest-pin"


def git(root: Path, *argv: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", "-c", "commit.gpgsign=false", *argv],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise AssertionError(f"git {' '.join(argv)} failed: {done.stderr}")
    return done.stdout.strip()


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(root: Path, relative: str, body: dict[str, object]) -> None:
    write(root, relative, json.dumps(body, indent=2, sort_keys=True) + "\n")


def run_marker(root: Path, run_id: str, principal: str) -> None:
    instrument = "FORGE" if run_id.startswith("forge-") else "CRUCIBLE"
    harness = runs.HARNESS[instrument]
    write_json(
        root,
        f"{harness}/runs/{run_id}/run.json",
        {
            "schema": runs.SCHEMA,
            "instrument": instrument,
            "run_id": run_id,
            "principal": principal,
            "started_at": "2026-09-18T12:00:00Z",
        },
    )


def seal_entry(uuid: str, run_id: str, sealed_at: str, seq: int = 1) -> str:
    body = {
        "uuid": uuid,
        "bundle_digest": DIGEST,
        "producer_run_id": run_id,
        "sealed_at": sealed_at,
        "seq": seq,
    }
    return json.dumps(body, sort_keys=True) + "\n"


def claim_body(uuid: str, run_id: str, claimed_at: str) -> dict[str, object]:
    return {
        "uuid": uuid,
        "bundle_digest": DIGEST,
        "consumer_run_id": run_id,
        "claimed_at": claimed_at,
    }


def verdict_body(uuid: str, run_id: str) -> dict[str, object]:
    return {
        "uuid": uuid,
        "bundle_digest": DIGEST,
        "consumer_run_id": run_id,
        "outcome": "clean",
        "recorded_at": "2026-09-18T13:00:00Z",
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "--initial-branch=main")
    write(tmp_path, ".memory/roots.yaml", "version: 1\n")
    run_marker(tmp_path, FORGE_RUN, ALICE)
    run_marker(tmp_path, AUDIT_RUN, ALICE)
    write(
        tmp_path,
        f".podium/queue/{FORGE_RUN}.jsonl",
        seal_entry(UUID, FORGE_RUN, "2026-09-18T12:00:00Z"),
    )
    commit(tmp_path, "accepted base")
    return tmp_path


def context(repo: Path, operator: str = ALICE, policy: str = POLICY) -> TrustedContext:
    return TrustedContext(
        project="EtharaOrion/argos",
        operator=operator,
        base_commit=git(repo, "rev-parse", "HEAD"),
        trust_policy_digest=policy,
        enrolled_principals=frozenset({ALICE, BOB}),
    )


def codes(repo: Path, ctx: TrustedContext, candidate: str = "HEAD") -> list[str]:
    return [item.code for item in validate_transition(repo, candidate, ctx)]


def pinned(repo: Path) -> str:
    return hashlib.sha256((repo / ".memory/roots.yaml").read_bytes()).hexdigest()


# ---- T1: the base is supplied, never chosen by the candidate --------------------------------


def test_a_transition_whose_sole_parent_is_the_accepted_base_passes(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    write(
        repo,
        f".podium/queue/{FORGE_RUN}.jsonl",
        seal_entry(UUID, FORGE_RUN, "2026-09-18T12:00:00Z")
        + seal_entry(
            "b" * 8 + "-5a2b-5c3d-8e4f-6a7b8c9d0e1f", FORGE_RUN, "2026-09-18T14:00:00Z", 2
        ),
    )
    commit(repo, "append one seal")
    assert codes(repo, ctx) == []


def test_a_candidate_that_does_not_name_the_accepted_base_as_its_parent_is_refused(
    repo: Path,
) -> None:
    ctx = context(repo, policy=pinned(repo))
    commit(repo, "one")
    commit(repo, "two")
    assert "TRANSITION_BASE_MISMATCH" in codes(repo, ctx)


@bite("shared.md:A95")
def test_a_merge_that_buries_the_accepted_base_as_a_second_parent_is_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "side", f"{base}~0")
    git(repo, "checkout", "-q", "--orphan", "rogue")
    git(repo, "rm", "-rq", "--cached", ".")
    write(repo, "rogue.txt", "x\n")
    rogue = commit(repo, "rogue root")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "--allow-unrelated-histories", "-m", "merge", rogue)
    assert "TRANSITION_BASE_MISMATCH" in codes(repo, ctx)


def test_an_unresolvable_base_is_refused_rather_than_skipped(repo: Path) -> None:
    ctx = TrustedContext(
        project="EtharaOrion/argos",
        operator=ALICE,
        base_commit="0" * 40,
        trust_policy_digest=pinned(repo),
        enrolled_principals=frozenset({ALICE}),
    )
    commit(repo, "next")
    assert "TRANSITION_BASE_MISMATCH" in codes(repo, ctx)


# ---- T2, T3: accepted records are append-only or immutable ----------------------------------


def test_a_rewritten_queue_stream_is_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    write(
        repo,
        f".podium/queue/{FORGE_RUN}.jsonl",
        seal_entry(UUID, FORGE_RUN, "2026-09-18T15:00:00Z"),
    )
    commit(repo, "rewrite the stream")
    assert "TRANSITION_STREAM_REWRITTEN" in codes(repo, ctx)


def test_a_truncated_queue_stream_is_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    write(repo, f".podium/queue/{FORGE_RUN}.jsonl", "")
    commit(repo, "truncate the stream")
    assert "TRANSITION_STREAM_REWRITTEN" in codes(repo, ctx)


@bite("shared.md:A96")
def test_an_edited_accepted_claim_is_refused(repo: Path) -> None:
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{AUDIT_RUN}.json",
        claim_body(UUID, AUDIT_RUN, "2026-09-18T12:30:00Z"),
    )
    commit(repo, "accept a claim")
    ctx = context(repo, policy=pinned(repo))
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{AUDIT_RUN}.json",
        claim_body(UUID, AUDIT_RUN, "2026-09-18T11:00:00Z"),
    )
    commit(repo, "backdate the accepted claim")
    assert "TRANSITION_RECORD_MUTATED" in codes(repo, ctx)


def test_a_deleted_accepted_sentinel_entry_is_refused(repo: Path) -> None:
    write(repo, ".sentinel/attempts.jsonl", '{"seq": 1}\n')
    commit(repo, "accept a sentinel entry")
    ctx = context(repo, policy=pinned(repo))
    (repo / ".sentinel/attempts.jsonl").unlink()
    commit(repo, "delete the ledger")
    assert "TRANSITION_RECORD_DELETED" in codes(repo, ctx)


# ---- T4: a run namespace is written only by the principal that owns it ----------------------


@bite("shared.md:A97")
def test_writing_into_another_principals_run_namespace_is_refused(repo: Path) -> None:
    ctx = context(repo, operator=BOB, policy=pinned(repo))
    run_marker(repo, BOB_RUN, BOB)
    write(repo, f".seed/runs/{FORGE_RUN}/note.txt", "bob was here\n")
    commit(repo, "bob writes into alice's run")
    assert "TRANSITION_FOREIGN_RUN" in codes(repo, ctx)


def test_a_new_run_marker_naming_another_principal_is_refused(repo: Path) -> None:
    ctx = context(repo, operator=BOB, policy=pinned(repo))
    run_marker(repo, BOB_RUN, ALICE)
    commit(repo, "bob mints a run owned by alice")
    assert "TRANSITION_FOREIGN_RUN" in codes(repo, ctx)


def test_an_unenrolled_operator_is_refused_before_any_record_rule(repo: Path) -> None:
    ctx = context(repo, operator="mallory", policy=pinned(repo))
    commit(repo, "empty")
    assert codes(repo, ctx) == ["TRANSITION_UNENROLLED_OPERATOR"]


# ---- T5, T6: ownership is the accepted sequence, never a self-reported instant --------------


@bite("shared.md:A98")
def test_a_second_claim_on_an_already_accepted_bundle_is_refused(repo: Path) -> None:
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{AUDIT_RUN}.json",
        claim_body(UUID, AUDIT_RUN, "2026-09-18T12:30:00Z"),
    )
    commit(repo, "alice's claim is accepted")
    ctx = context(repo, operator=BOB, policy=pinned(repo))
    run_marker(repo, RIVAL_RUN, BOB)
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{RIVAL_RUN}.json",
        claim_body(UUID, RIVAL_RUN, "2026-09-18T11:00:00Z"),
    )
    commit(repo, "bob backdates a rival claim")
    assert "TRANSITION_CLAIM_CONTESTED" in codes(repo, ctx)


def test_two_claims_on_one_bundle_inside_one_transition_are_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    run_marker(repo, RIVAL_RUN, ALICE)
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{AUDIT_RUN}.json",
        claim_body(UUID, AUDIT_RUN, "2026-09-18T12:30:00Z"),
    )
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{RIVAL_RUN}.json",
        claim_body(UUID, RIVAL_RUN, "2026-09-18T12:31:00Z"),
    )
    commit(repo, "two claims in one transition")
    assert "TRANSITION_CLAIM_CONTESTED" in codes(repo, ctx)


def test_a_verdict_without_an_accepted_claim_is_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    write_json(repo, f".audit/verdicts/{UUID}/{DIGEST}.json", verdict_body(UUID, AUDIT_RUN))
    commit(repo, "verdict with no accepted claim")
    assert "TRANSITION_VERDICT_UNOWNED" in codes(repo, ctx)


def test_a_verdict_claimed_and_written_in_one_transition_is_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{AUDIT_RUN}.json",
        claim_body(UUID, AUDIT_RUN, "2026-09-18T12:30:00Z"),
    )
    write_json(repo, f".audit/verdicts/{UUID}/{DIGEST}.json", verdict_body(UUID, AUDIT_RUN))
    commit(repo, "claim and judge in one step")
    assert "TRANSITION_VERDICT_UNOWNED" in codes(repo, ctx)


def test_a_verdict_by_the_accepted_owner_passes(repo: Path) -> None:
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{AUDIT_RUN}.json",
        claim_body(UUID, AUDIT_RUN, "2026-09-18T12:30:00Z"),
    )
    commit(repo, "alice's claim is accepted")
    ctx = context(repo, policy=pinned(repo))
    write_json(repo, f".audit/verdicts/{UUID}/{DIGEST}.json", verdict_body(UUID, AUDIT_RUN))
    commit(repo, "the owner judges")
    assert codes(repo, ctx) == []


def test_a_verdict_by_a_non_owner_is_refused(repo: Path) -> None:
    write_json(
        repo,
        f".audit/queue.claims/{UUID}/{AUDIT_RUN}.json",
        claim_body(UUID, AUDIT_RUN, "2026-09-18T12:30:00Z"),
    )
    commit(repo, "alice's claim is accepted")
    ctx = context(repo, operator=BOB, policy=pinned(repo))
    run_marker(repo, RIVAL_RUN, BOB)
    write_json(repo, f".audit/verdicts/{UUID}/{DIGEST}.json", verdict_body(UUID, RIVAL_RUN))
    commit(repo, "bob judges a bundle alice owns")
    assert "TRANSITION_VERDICT_UNOWNED" in codes(repo, ctx)


# ---- T7: epochs advance by one against the accepted current ---------------------------------


def accept_epoch(root: Path, number: int) -> None:
    write_json(
        root,
        f"{epochs.EPOCHS_DIR}/{number}/manifest.json",
        {
            "schema": epochs.MANIFEST_SCHEMA,
            "epoch": number,
            "parent_epoch": number - 1,
            "published_by": FORGE_RUN,
            "published_at": "2026-09-18T12:00:00Z",
            "files": {},
            "proposals": [],
        },
    )
    write_json(
        root,
        str(epochs.CURRENT_PATH),
        {"schema": epochs.CURRENT_SCHEMA, "epoch": number, "manifest_digest": "d" * 64},
    )


def test_publishing_the_next_epoch_passes(repo: Path) -> None:
    accept_epoch(repo, 1)
    commit(repo, "epoch 1 accepted")
    ctx = context(repo, policy=pinned(repo))
    accept_epoch(repo, 2)
    commit(repo, "publish epoch 2")
    assert codes(repo, ctx) == []


def test_republishing_the_accepted_epoch_with_different_bytes_is_refused(repo: Path) -> None:
    accept_epoch(repo, 1)
    accept_epoch(repo, 2)
    commit(repo, "epoch 2 accepted")
    ctx = context(repo, policy=pinned(repo))
    write_json(
        repo,
        f"{epochs.EPOCHS_DIR}/2/manifest.json",
        {
            "schema": epochs.MANIFEST_SCHEMA,
            "epoch": 2,
            "parent_epoch": 1,
            "published_by": BOB_RUN,
            "published_at": "2026-09-18T13:00:00Z",
            "files": {},
            "proposals": [],
        },
    )
    commit(repo, "fork epoch 2")
    assert "TRANSITION_RECORD_MUTATED" in codes(repo, ctx)


def test_skipping_an_epoch_number_is_refused(repo: Path) -> None:
    accept_epoch(repo, 1)
    commit(repo, "epoch 1 accepted")
    ctx = context(repo, policy=pinned(repo))
    accept_epoch(repo, 3)
    commit(repo, "publish epoch 3")
    assert "TRANSITION_EPOCH_FORK" in codes(repo, ctx)


def test_moving_current_backwards_is_refused(repo: Path) -> None:
    accept_epoch(repo, 1)
    accept_epoch(repo, 2)
    commit(repo, "epoch 2 accepted")
    ctx = context(repo, policy=pinned(repo))
    write_json(
        repo,
        str(epochs.CURRENT_PATH),
        {"schema": epochs.CURRENT_SCHEMA, "epoch": 1, "manifest_digest": "d" * 64},
    )
    commit(repo, "roll current back")
    assert "TRANSITION_EPOCH_ROLLBACK" in codes(repo, ctx)


# ---- T8: a seal instant never reorders the accepted scarce-slot queue -----------------------


@bite("shared.md:A99")
def test_a_backdated_seal_that_would_jump_the_scarce_queue_is_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    write(
        repo,
        f".podium/queue/{FORGE_RUN}.jsonl",
        seal_entry(UUID, FORGE_RUN, "2026-09-18T12:00:00Z")
        + seal_entry(
            "c" * 8 + "-5a2b-5c3d-8e4f-6a7b8c9d0e1f", FORGE_RUN, "2026-09-17T09:00:00Z", 2
        ),
    )
    commit(repo, "append a backdated seal")
    assert "TRANSITION_BACKDATED" in codes(repo, ctx)


# ---- T9: trust policy is pinned outside the candidate ---------------------------------------


def test_a_trust_policy_edited_inside_the_transition_is_refused(repo: Path) -> None:
    ctx = context(repo, policy=pinned(repo))
    write(repo, ".memory/roots.yaml", "version: 2\n")
    commit(repo, "swap the trust root")
    assert "TRANSITION_TRUST_DRIFT" in codes(repo, ctx)


def test_a_context_pin_that_never_matched_the_base_is_refused(repo: Path) -> None:
    ctx = context(repo, policy="not-the-pinned-digest")
    commit(repo, "empty")
    assert "TRANSITION_TRUST_DRIFT" in codes(repo, ctx)


# ---- the closed vocabulary and the refusal to self-configure --------------------------------


def test_every_emitted_code_is_in_the_closed_vocabulary(repo: Path) -> None:
    ctx = context(repo, operator=BOB)
    run_marker(repo, BOB_RUN, ALICE)
    write(repo, f".seed/runs/{FORGE_RUN}/note.txt", "x\n")
    write(repo, f".podium/queue/{FORGE_RUN}.jsonl", "rewritten\n")
    commit(repo, "many refusals at once")
    emitted = set(codes(repo, ctx))
    assert emitted
    assert emitted <= set(TRANSITION_CODES)


def test_a_context_missing_its_base_commit_is_a_configuration_error() -> None:
    with pytest.raises(TransitionContextError):
        TrustedContext(
            project="EtharaOrion/argos",
            operator=ALICE,
            base_commit="",
            trust_policy_digest=POLICY,
            enrolled_principals=frozenset({ALICE}),
        )


def test_a_context_with_no_enrolled_principal_is_a_configuration_error() -> None:
    with pytest.raises(TransitionContextError):
        TrustedContext(
            project="EtharaOrion/argos",
            operator=ALICE,
            base_commit="a" * 40,
            trust_policy_digest=POLICY,
            enrolled_principals=frozenset(),
        )


# ---- the CLI an admission boundary invokes ---------------------------------------------------


def cli(
    repo: Path, context_path: Path, candidate: str = "HEAD"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "tools" / "transition.py"),
            str(repo),
            "--candidate",
            candidate,
            "--context",
            str(context_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def context_file(tmp: Path, ctx: TrustedContext) -> Path:
    path = tmp / "admission-context.json"
    path.write_text(
        json.dumps(
            {
                "project": ctx.project,
                "operator": ctx.operator,
                "base_commit": ctx.base_commit,
                "trust_policy_digest": ctx.trust_policy_digest,
                "enrolled_principals": sorted(ctx.enrolled_principals),
            }
        ),
        encoding="utf-8",
    )
    return path


def test_the_cli_admits_a_lawful_successor(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    ctx = context(repo, policy=pinned(repo))
    commit(repo, "empty but lawful")
    done = cli(repo, context_file(tmp_path_factory.mktemp("ctx"), ctx))
    assert done.returncode == 0
    assert "admit:" in done.stdout


def test_the_cli_refuses_and_names_the_code(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    ctx = context(repo, policy=pinned(repo))
    write(repo, f".podium/queue/{FORGE_RUN}.jsonl", "rewritten\n")
    commit(repo, "rewrite")
    done = cli(repo, context_file(tmp_path_factory.mktemp("ctx"), ctx))
    assert done.returncode == 1
    assert "rewritten rather than extended" in done.stdout


def test_the_cli_refuses_an_unusable_context(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    path = tmp_path_factory.mktemp("ctx") / "context.json"
    path.write_text('{"project": "x"}', encoding="utf-8")
    done = cli(repo, path)
    assert done.returncode == 2
    assert "context is unusable" in done.stderr


# ---- attribution: a record is covered by an operation its operator signed --------------------

OPERATOR = "alice@trinity.test"
OUTSIDER = "mallory@trinity.test"


def signing_repo(repo: Path, tmp: Path) -> tuple[SigningPolicy, dict[str, tuple[Path, str]]]:
    keys = {
        OPERATOR: generate_key(tmp / "secrets", "alice"),
        OUTSIDER: generate_key(tmp / "secrets", "mallory"),
    }
    write_trust(
        repo,
        entries=keys,
        roles={operations.ROLE: 1, "bystander": 1},
        bindings={OPERATOR: (operations.ROLE,), OUTSIDER: ("bystander",)},
    )
    policy = SigningPolicy(
        allowed_signers=repo / ".memory" / "allowed_signers",
        trust_root=repo / ".memory" / "roots.yaml",
        trusted_version=1,
        evaluation_time=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
    )
    return policy, keys


def signing_context(repo: Path, policy: SigningPolicy, operator: str = OPERATOR) -> TrustedContext:
    return TrustedContext(
        project="EtharaOrion/argos",
        operator=operator,
        base_commit=git(repo, "rev-parse", "HEAD"),
        trust_policy_digest=pinned(repo),
        enrolled_principals=frozenset({OPERATOR, OUTSIDER}),
        signing=policy,
    )


def put_claim(repo: Path, run_id: str) -> bytes:
    relative = f".audit/queue.claims/{UUID}/{run_id}.json"
    write_json(repo, relative, claim_body(UUID, run_id, "2026-09-18T12:30:00Z"))
    return (repo / relative).read_bytes()


def put_operation(
    repo: Path,
    record: bytes,
    *,
    run_id: str,
    principal: str,
    keys: dict[str, tuple[Path, str]],
    namespace: str | None = None,
) -> None:
    item = operations.Operation(
        project="EtharaOrion/argos",
        run_id=run_id,
        verb=operations.Verb.CLAIM,
        artifact_digest=hashlib.sha256(record).hexdigest(),
        seq=1,
        previous=operations.CHAIN_GENESIS,
        principal=principal,
    )
    envelope = operations.sign_operation(SshKeygenBackend(), item, key_path=keys[principal][0])
    target = operations.operations_dir(repo, namespace or run_id) / "0001.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(envelope.to_json())


def test_a_claim_covered_by_an_operation_its_operator_signed_passes(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    policy, keys = signing_repo(repo, tmp_path_factory.mktemp("keys"))
    run_marker(repo, AUDIT_RUN, OPERATOR)
    commit(repo, "enrol the operator")
    ctx = signing_context(repo, policy)
    record = put_claim(repo, AUDIT_RUN)
    put_operation(repo, record, run_id=AUDIT_RUN, principal=OPERATOR, keys=keys)
    commit(repo, "claim with its signed operation")
    assert codes(repo, ctx) == []


@bite("shared.md:A102")
def test_a_claim_with_no_signed_operation_is_refused(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    policy, _keys = signing_repo(repo, tmp_path_factory.mktemp("keys"))
    run_marker(repo, AUDIT_RUN, OPERATOR)
    commit(repo, "enrol the operator")
    ctx = signing_context(repo, policy)
    put_claim(repo, AUDIT_RUN)
    commit(repo, "claim with no operation")
    assert "TRANSITION_UNSIGNED_OPERATION" in codes(repo, ctx)


def test_an_operation_whose_bytes_do_not_match_the_record_leaves_it_unsigned(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    policy, keys = signing_repo(repo, tmp_path_factory.mktemp("keys"))
    run_marker(repo, AUDIT_RUN, OPERATOR)
    commit(repo, "enrol the operator")
    ctx = signing_context(repo, policy)
    put_operation(repo, b"other bytes entirely\n", run_id=AUDIT_RUN, principal=OPERATOR, keys=keys)
    put_claim(repo, AUDIT_RUN)
    commit(repo, "operation names other bytes")
    assert "TRANSITION_UNSIGNED_OPERATION" in codes(repo, ctx)


def test_an_operation_signed_by_someone_other_than_the_operator_is_refused(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    policy, keys = signing_repo(repo, tmp_path_factory.mktemp("keys"))
    run_marker(repo, AUDIT_RUN, OPERATOR)
    commit(repo, "enrol the operator")
    ctx = signing_context(repo, policy)
    record = put_claim(repo, AUDIT_RUN)
    put_operation(repo, record, run_id=AUDIT_RUN, principal=OUTSIDER, keys=keys)
    commit(repo, "an outsider signs the operation")
    emitted = codes(repo, ctx)
    assert "OPERATION_UNAUTHORIZED" in emitted or "OPERATION_PRINCIPAL_MISMATCH" in emitted


def test_an_operation_planted_in_another_runs_namespace_is_refused(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    policy, keys = signing_repo(repo, tmp_path_factory.mktemp("keys"))
    run_marker(repo, AUDIT_RUN, OPERATOR)
    run_marker(repo, RIVAL_RUN, OPERATOR)
    commit(repo, "enrol the operator")
    ctx = signing_context(repo, policy)
    record = put_claim(repo, AUDIT_RUN)
    put_operation(
        repo, record, run_id=AUDIT_RUN, principal=OPERATOR, keys=keys, namespace=RIVAL_RUN
    )
    commit(repo, "operation planted in another namespace")
    assert "OPERATION_CHAIN_BROKEN" in codes(repo, ctx)


def test_a_transition_without_a_signing_policy_is_judged_on_structure_alone(
    repo: Path,
) -> None:
    ctx = context(repo, policy=pinned(repo))
    assert ctx.signing is None
    put_claim(repo, AUDIT_RUN)
    commit(repo, "unsigned claim, no policy")
    assert "TRANSITION_UNSIGNED_OPERATION" not in codes(repo, ctx)
