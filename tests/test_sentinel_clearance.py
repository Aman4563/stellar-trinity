from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

import pytest
from tools import gate, sabotage, sentinel
from tools._findings import Finding, Severity, finding_to_json
from tools.attest import canonical, dsse

from tests.bite_shared.registration import bite
from tests.parent_fixtures import git
from tests.sentinel_signing_fixtures import (
    ACTOR,
    AUTHOR,
    CLEARER,
    NOW,
    PAYLOAD_TYPE,
    REFUSAL,
    ROLE,
    SCHEMA,
    SigningRoot,
    cli,
    forge_head,
    generate_key,
    plant,
    plant_repeat,
    sign_head,
    verified_actor,
    write_v1,
)
from tests.sentinel_signing_fixtures import (
    ClearanceCase as SigningClearanceCase,
)
from tests.test_sentinel import _superseded_alert


class ClearanceCase(SigningClearanceCase):
    def envelope(
        self,
        key: Path | None = None,
        *,
        payload_type: str = PAYLOAD_TYPE,
        changes: Mapping[str, canonical.JSONValue] | None = None,
    ) -> Path:
        evidence: dict[str, canonical.JSONValue] = {
            "repo": self.alert.repo,
            "attempts": list(self.alert.attempts),
        }
        evidence.update(changes or {})
        return super().envelope(key, payload_type=payload_type, changes=evidence)


@pytest.fixture
def signing(tmp_path: Path) -> SigningRoot:
    entries = {
        name: generate_key(tmp_path / ".secrets", name.split("@", 1)[0])
        for name in (ACTOR, CLEARER, "observer@trinity.test")
    }
    git(["init", "-q"], cwd=tmp_path)
    result = SigningRoot(tmp_path, entries)
    result.trust()
    return result


@pytest.fixture
def case(signing: SigningRoot) -> ClearanceCase:
    return ClearanceCase(signing, plant_repeat(signing.root, verified_actor()))


def test_old_ledger_records_parse_as_a_claimed_identity(tmp_path: Path) -> None:
    write_v1(tmp_path)
    attempts, defect = sentinel.read_ledger(tmp_path / sentinel.LEDGER_PATH)
    assert defect is None and len(attempts) == 5
    assert all(a.actor.identity == "claimed" for a in attempts)
    assert all(a.actor.principal == f"unverified:{AUTHOR}" for a in attempts)
    assert all(a.schema_version == sentinel.ATTEMPT_SCHEMA_V1 for a in attempts)


def test_a_v2_record_appends_onto_a_v1_chain_without_breaking_it(tmp_path: Path) -> None:
    write_v1(tmp_path)
    original = (tmp_path / sentinel.LEDGER_PATH).read_bytes()
    appended = plant(tmp_path, verified_actor(), run_id="run-6")
    attempts, defect = sentinel.read_ledger(tmp_path / sentinel.LEDGER_PATH)
    assert defect is None and len(attempts) == 6 and sentinel.verify_chain(tmp_path) == []
    assert (tmp_path / sentinel.LEDGER_PATH).read_bytes().startswith(original)
    assert appended.schema_version == sentinel.ATTEMPT_SCHEMA_V2
    assert appended.previous_hash == attempts[-2].entry_hash
    alerts, defect = sentinel.read_alerts(tmp_path / sentinel.ALERTS_PATH)
    assert defect is None and alerts[-1].schema_version == sentinel.ALERT_SCHEMA_V2


def test_old_alert_records_parse_as_claimed_and_still_require_a_signed_clearance(
    tmp_path: Path,
) -> None:
    alert = write_v1(tmp_path)
    assert alert.actor.identity == "claimed" and alert.actor.principal == f"unverified:{AUTHOR}"
    status = sentinel.clearance_status(tmp_path, alert, evaluation_time=NOW)
    assert not status.cleared and not status.principals and not status.unsigned
    assert "no signed clearance" in status.detail


def test_an_actor_dict_with_an_unknown_field_is_refused(tmp_path: Path) -> None:
    attempt = plant(tmp_path, verified_actor())
    body = canonical.parse_json(sentinel.render_record(attempt))
    assert isinstance(body, dict) and isinstance(body["actor"], dict)
    body["actor"]["admin"] = True
    body.pop("entry_hash")
    body["entry_hash"] = sentinel.entry_hash_for(body)
    attempts, defect = sentinel.read_ledger_document(canonical.canonicalize(body))
    assert not attempts and defect is not None and "actor" in defect


def test_a_verified_ssh_signed_commit_yields_the_signer_principal(signing: SigningRoot) -> None:
    sign_head(signing.root, signing.key(ACTOR), name="Colleague", email="colleague@trinity.test")
    assert sentinel.verify_head_principal(signing.root, evaluation_time=NOW) == ACTOR
    actor = sentinel.resolve_actor(signing.root, ci=False, environ={}, evaluation_time=NOW)
    assert (actor.identity, actor.principal, actor.source) == ("verified", ACTOR, "local")


def test_an_unsigned_head_yields_a_claimed_identity_named_unverified(tmp_path: Path) -> None:
    git(["init", "-q"], cwd=tmp_path)
    forge_head(tmp_path, name="Actor", email=ACTOR)
    actor = sentinel.resolve_actor(tmp_path, ci=False, environ={"GITHUB_ACTOR": "colleague"})
    assert (actor.identity, actor.principal) == ("claimed", f"unverified:{AUTHOR}")
    assert actor.source == "local"


@bite("shared.md:A93")
def test_a_forged_author_never_counts_toward_the_impersonated_principal(
    signing: SigningRoot,
) -> None:
    forge_head(signing.root, name="Actor", email=ACTOR)
    claimed = sentinel.resolve_actor(signing.root, ci=False, environ={})
    assert claimed.identity == "claimed"
    verified = verified_actor()
    assert not claimed.shares_identity(verified) and not verified.shares_identity(claimed)
    alert = plant_repeat(signing.root, claimed)
    assert sentinel.alert_excluded_principals(alert) == ()
    plant(signing.root, claimed, run_id="run-6")
    folded, defect = sentinel.read_alerts(signing.root / sentinel.ALERTS_PATH)
    assert defect is None and len(folded) == 1
    plant(signing.root, verified, run_id="run-7")
    alerts, defect = sentinel.read_alerts(signing.root / sentinel.ALERTS_PATH)
    assert defect is None and len(alerts) == 2


def test_a_signature_by_a_key_outside_allowed_signers_yields_a_claimed_identity(
    signing: SigningRoot,
) -> None:
    key, _ = generate_key(signing.root / ".secrets", "outsider")
    sign_head(signing.root, key, name="Actor", email=ACTOR)
    assert sentinel.verify_head_principal(signing.root, evaluation_time=NOW) is None
    actor = sentinel.resolve_actor(signing.root, ci=False, environ={}, evaluation_time=NOW)
    assert (actor.identity, actor.principal) == ("claimed", f"unverified:{AUTHOR}")


def test_head_bytes_that_do_not_rehash_to_the_head_object_id_yield_a_claimed_identity(
    signing: SigningRoot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_head(signing.root, signing.key(ACTOR), name="Actor", email=ACTOR)
    assert sentinel.verify_head_principal(signing.root, evaluation_time=NOW) == ACTOR
    original = sentinel._git_bytes
    signed_body = original(signing.root, "cat-file", "commit", "HEAD")
    assert signed_body is not None
    sign_head(signing.root, signing.key(ACTOR), name="Actor", email=ACTOR)

    def substituted(root: Path, *argv: str) -> bytes | None:
        return signed_body if argv == ("cat-file", "commit", "HEAD") else original(root, *argv)

    monkeypatch.setattr(sentinel, "_git_bytes", substituted)
    actor = sentinel.resolve_actor(signing.root, ci=False, environ={}, evaluation_time=NOW)
    assert (actor.identity, actor.principal) == ("claimed", f"unverified:{AUTHOR}")


def test_ci_actor_carries_the_ci_identity_and_a_github_principal(tmp_path: Path) -> None:
    actor = sentinel.resolve_actor(tmp_path, ci=True, environ={"GITHUB_ACTOR": "runner"})
    assert (actor.identity, actor.principal, actor.source) == ("ci", "github:runner", "ci")
    peer = sentinel.Actor.for_ci(git_author="Other <other@trinity.test>", github_login="runner")
    assert actor.shares_identity(peer)
    fallback = sentinel.Actor.for_ci(git_author=AUTHOR, github_login=None)
    assert (fallback.identity, fallback.principal) == ("claimed", f"unverified:{AUTHOR}")


def test_clearance_signed_by_a_sentinel_clearer_clears_the_refusal(case: ClearanceCase) -> None:
    path = case.clear()
    status = case.status()
    assert path.name == f"{case.alert.entry_hash}.json.dsse"
    assert status.cleared and status.principals == (CLEARER,) and not status.unsigned
    assert sentinel.check_sentinel_chain(str(case.signing.root), NOW) == []
    parsed = dsse.parse_envelope(path.read_bytes())
    assert parsed.envelope is not None and parsed.envelope.payload_type == PAYLOAD_TYPE
    assert sentinel.SENTINEL_CLEARER_ROLE == ROLE and sentinel.CLEARANCE_SCHEMA == SCHEMA
    assert sentinel.CLEARANCE_PAYLOAD_TYPE == PAYLOAD_TYPE


@bite("shared.md:A92")
def test_clearance_signed_by_the_alerted_actor_is_refused_before_a_byte_is_written(
    case: ClearanceCase,
) -> None:
    directory = sentinel.clearance_path(case.signing.root, case.alert).parent
    directory.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="self_approval"):
        case.clear(ACTOR)
    assert list(directory.iterdir()) == []


def test_a_planted_self_signed_clearance_is_refused_at_the_gate(case: ClearanceCase) -> None:
    case.envelope(case.signing.key(ACTOR))
    case.refused("self_approval")


def test_clearance_signed_by_a_key_outside_allowed_signers_is_refused(case: ClearanceCase) -> None:
    key, _ = generate_key(case.signing.root / ".secrets", "outsider")
    case.envelope(key)
    case.refused("principal")


def test_clearance_by_a_principal_without_the_sentinel_clearer_role_is_refused(
    case: ClearanceCase,
) -> None:
    case.envelope(case.signing.key("observer@trinity.test"))
    case.refused("not authorized")


@bite("shared.md:A91")
def test_typed_json_clearance_is_refused_and_recorded_as_a_sabotage_attempt(
    case: ClearanceCase,
) -> None:
    case.clear()
    path = sentinel.legacy_clearance_path(case.signing.root, case.alert)
    path.write_bytes(
        canonical.canonicalize(
            {
                "alert_entry_hash": case.alert.entry_hash,
                "approver": CLEARER,
                "cleared_at": "2026-09-16T12:00:00Z",
                "reason": "typed",
            }
        )
    )
    status = case.status()
    assert not status.cleared and status.unsigned and not status.principals
    findings = sentinel.check_sentinel_chain(str(case.signing.root), NOW)
    code = sabotage.SAB_SENTINEL_CLEARANCE_UNSIGNED
    assert {code, "SAB_REPEATED_ATTEMPT"} <= {item.code for item in findings}
    unsigned = next(item for item in findings if item.code == code)
    assert unsigned.path == f"./.sentinel/clearances/{case.alert.entry_hash}.json"
    assert case.alert.entry_hash in unsigned.message and ".json.dsse" in unsigned.message
    assert gate.ceiling(findings) == "BLOCK"
    recorded, _ = sentinel.record(
        case.signing.root,
        [finding_to_json(item) for item in findings],
        actor=verified_actor(),
        run_id="typed-clearance",
        git_sha="b" * 40,
        repo="test",
        now=NOW,
    )
    assert [item.code for item in recorded] == [sentinel.SabotageCode.SAB_SELF_APPROVAL]


@bite("shared.md:A94")
def test_absent_allowed_signers_refuses_every_clearance_with_a_named_remedy(
    case: ClearanceCase,
) -> None:
    case.envelope()
    (case.signing.root / ".memory/allowed_signers").unlink()
    case.refused(".memory/allowed_signers")
    assert "enrol" in case.status().detail and "rotation" in case.status().detail
    result = cli(case.signing.root, "verify", "./")
    assert result.returncode == 1 and ".memory/allowed_signers" in result.stdout


def test_absent_trust_root_refuses_every_clearance(case: ClearanceCase) -> None:
    case.envelope()
    (case.signing.root / ".memory/roots.yaml").unlink()
    case.refused("trust_root")


def test_expired_trust_root_refuses_the_clearance_at_the_evaluation_instant(
    case: ClearanceCase,
) -> None:
    case.envelope()
    case.signing.trust(expires="2026-09-16T12:00:00Z")
    case.refused("trust_root_expired")


def test_clearance_naming_a_different_alert_is_refused(case: ClearanceCase) -> None:
    case.envelope(changes={"alert_entry_hash": "a" * 64})
    case.refused("alert")


def test_clearance_naming_a_different_stream_is_refused(case: ClearanceCase) -> None:
    case.envelope(changes={"stream": "other-run"})
    case.refused("stream")


def test_clearance_signed_under_another_payload_type_is_refused(case: ClearanceCase) -> None:
    case.envelope(payload_type="application/vnd.trinity.other+json")
    case.refused("payloadType")


def test_a_claimed_identity_never_excludes_anyone_from_clearing(signing: SigningRoot) -> None:
    actor = sentinel.Actor.claimed(git_author=AUTHOR, github_login=ACTOR)
    alert = plant_repeat(signing.root, actor)
    assert sentinel.alert_excluded_principals(alert) == ()
    case = ClearanceCase(signing, alert)
    case.clear(ACTOR)
    status = case.status()
    assert status.cleared and status.principals == (ACTOR,)


def test_a_symlinked_clearance_envelope_fails_closed(case: ClearanceCase) -> None:
    path = case.envelope()
    target = path.with_name("target.dsse")
    path.rename(target)
    path.symlink_to(target)
    case.refused("unreadable")


def test_clear_requires_a_key_and_rejects_the_retired_approver_flag(tmp_path: Path) -> None:
    missing = cli(tmp_path, "clear", "./", "--alert", "a" * 64)
    retired = cli(
        tmp_path, "clear", "./", "--alert", "a" * 64, "--key", "./key", "--approver", "Reviewer"
    )
    assert missing.returncode == 2 and "required: --key" in missing.stderr
    assert retired.returncode == 2 and "unrecognized arguments: --approver" in retired.stderr


def test_status_and_verify_name_the_verified_clearing_principal(case: ClearanceCase) -> None:
    cleared = cli(
        case.signing.root,
        "clear",
        "./",
        "--alert",
        case.alert.entry_hash,
        "--key",
        "./.secrets/clearer",
        "--reason",
        "reviewed",
    )
    assert cleared.returncode == 0 and CLEARER in cleared.stdout
    status, verify = (cli(case.signing.root, command, "./") for command in ("status", "verify"))
    assert status.returncode == verify.returncode == 0
    assert f"cleared by {CLEARER}" in status.stdout and CLEARER in verify.stdout


def test_status_names_a_claimed_attempt_as_unverified(tmp_path: Path) -> None:
    write_v1(tmp_path)
    status = cli(tmp_path, "status", "./")
    assert status.returncode == 1 and f"claimed:unverified:{AUTHOR}" in status.stdout


def test_unsigned_clearance_error_alone_caps_the_gate_at_block() -> None:
    # Given an unsigned-clearance refusal without a repeated-attempt finding.
    finding = Finding(
        sabotage.SAB_SENTINEL_CLEARANCE_UNSIGNED,
        Severity.ERROR,
        "./.sentinel/clearances/alert.json",
        None,
        "typed clearance",
    )
    # When the gate derives its ceiling, then the refusal independently blocks.
    assert gate.ceiling([finding]) == "BLOCK"


def test_clearance_from_another_parent_with_a_colliding_alert_hash_is_refused(
    signing: SigningRoot,
) -> None:
    cases: list[ClearanceCase] = []
    for name, sha in (("parent-a", "a" * 40), ("parent-b", "b" * 40)):
        root = signing.root / name
        root.mkdir()
        parent = SigningRoot(root, signing.entries)
        parent.trust()
        for number in range(1, 6):
            sentinel.record(
                root,
                [{**REFUSAL, "message": f"{name} refusal {number}"}],
                actor=verified_actor(),
                run_id=f"run-{number}",
                git_sha=sha,
                repo=name,
                now=NOW,
            )
        alerts, defect = sentinel.read_alerts(root / sentinel.ALERTS_PATH)
        assert defect is None and len(alerts) == 1
        cases.append(ClearanceCase(parent, alerts[0]))
    first, second = cases
    document = first.clear().read_bytes()
    target = sentinel.clearance_path(second.signing.root, second.alert)
    target.parent.mkdir(parents=True)
    target.write_bytes(document)

    status = second.status()

    assert not status.cleared
    assert first.alert.entry_hash != second.alert.entry_hash
    assert cli(second.signing.root, "verify", "./").returncode == 1


def test_alert_v2_body_binds_repo_and_attempt_hashes(case: ClearanceCase) -> None:
    attempts = sentinel.all_attempts(case.signing.root)

    body = canonical.parse_json(sentinel.render_alert(case.alert))

    assert isinstance(body, dict)
    assert body.get("repo") == attempts[-1].repo
    assert body.get("attempts") == sorted(item.entry_hash for item in attempts)


def test_typed_clearance_on_a_superseded_alert_is_still_a_block(signing: SigningRoot) -> None:
    alert = _superseded_alert(signing.root)
    case = ClearanceCase(signing, alert)
    case.clear()
    sentinel.legacy_clearance_path(signing.root, alert).write_text("{}", encoding="utf-8")

    findings = sentinel.check_sentinel_chain(str(signing.root), NOW)

    assert any(
        item.code == sabotage.SAB_SENTINEL_CLEARANCE_UNSIGNED and item.severity is Severity.ERROR
        for item in findings
    )
    assert gate.ceiling(findings) == "BLOCK"


def test_clearance_for_a_v1_alert_binds_the_ledger_evidence_and_refuses_a_colliding_parent(
    signing: SigningRoot,
) -> None:
    cases: list[ClearanceCase] = []
    for name, sha in (("parent-a", "a" * 40), ("parent-b", "b" * 40)):
        root = signing.root / name
        root.mkdir()
        parent = SigningRoot(root, signing.entries)
        parent.trust()
        alert = write_v1(root)
        paths = sentinel.layout(root)
        attempts, defect = sentinel.read_ledger(paths.ledger)
        assert defect is None
        previous = sentinel.CHAIN_GENESIS
        rebound: list[sentinel.Attempt] = []
        for attempt in attempts:
            draft = replace(attempt, repo=name, git_sha=sha, previous_hash=previous)
            previous = sentinel.entry_hash_for(sentinel._record_body(draft))
            rebound.append(replace(draft, entry_hash=previous))
        paths.ledger.write_text("", encoding="utf-8")
        sentinel.append(paths.ledger, rebound)
        sentinel.write_head(paths.head, rebound[-1].seq, previous)
        assert sentinel.verify_chain(root) == []
        cases.append(ClearanceCase(parent, alert))
    first, second = cases
    original = (first.signing.root / sentinel.ALERTS_PATH).read_bytes()
    assert original == (second.signing.root / sentinel.ALERTS_PATH).read_bytes()
    assert first.alert.entry_hash == second.alert.entry_hash

    document = first.clear().read_bytes()
    parsed = dsse.parse_envelope(document)
    assert parsed.envelope is not None
    payload = canonical.parse_json(parsed.envelope.payload)
    assert isinstance(payload, dict)
    assert payload["repo"] == "parent-a"
    assert payload["attempts"] == sorted(
        item.entry_hash for item in sentinel.all_attempts(first.signing.root)
    )
    assert payload["attempts"]
    assert first.status().cleared
    target = sentinel.clearance_path(second.signing.root, second.alert)
    target.parent.mkdir(parents=True)
    target.write_bytes(document)

    assert not second.status().cleared
    assert cli(second.signing.root, "verify", "./").returncode == 1
    assert (first.signing.root / sentinel.ALERTS_PATH).read_bytes() == original
    assert (second.signing.root / sentinel.ALERTS_PATH).read_bytes() == original


@pytest.mark.parametrize("damage", ["missing", "defect", "range"])
def test_v1_clearance_refuses_unavailable_ledger_evidence(
    signing: SigningRoot, damage: str
) -> None:
    alert = write_v1(signing.root)
    case = ClearanceCase(signing, alert)
    path = case.clear()
    original = path.read_bytes()
    ledger = signing.root / sentinel.LEDGER_PATH
    if damage == "missing":
        ledger.unlink()
    elif damage == "defect":
        ledger.write_text("{}\n", encoding="utf-8")
    else:
        lines = ledger.read_text(encoding="utf-8").splitlines()
        ledger.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    status = case.status()

    assert not status.cleared and "alert evidence unavailable" in status.detail
    with pytest.raises(ValueError, match="alert evidence unavailable"):
        case.clear()
    assert path.read_bytes() == original
