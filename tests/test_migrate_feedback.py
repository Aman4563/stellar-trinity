"""Both halves of the legacy feedback-chain rewrite in tools/migrate_feedback.py."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import pytest
from tools import migrate, migrate_feedback
from tools.attest.canonical import canonicalize
from tools.feedback import integrity

NOW: Final = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
SHA: Final = "c2cfc6d395215ee4e3ccd2b3c744310748d473cb"


def legacy_line(seq: int, prev_hash: str, writer: object) -> dict[str, object]:
    body: dict[str, object] = {
        "captured_at": f"2026-09-07T11:{seq:02d}:00Z",
        "feedback_id": seq,
        "kind": "contract_paste",
        "prev_hash": prev_hash,
        "record_sha256": "8b" * 32,
        "seq": seq,
        "verbatim_sha256": "27" * 32,
        "writer": writer,
    }
    body["entry_hash"] = integrity.chain_digest(body)
    return body


def legacy_chain(writers: list[object]) -> bytes:
    prev = integrity.CHAIN_GENESIS
    lines: list[str] = []
    for seq, writer in enumerate(writers, start=1):
        entry = legacy_line(seq, prev, writer)
        prev = str(entry["entry_hash"])
        lines.append(canonicalize(entry).decode().removesuffix("\n"))
    return ("\n".join(lines) + "\n").encode()


OBJECT_WRITER: Final = {
    "git_sha": SHA,
    "model_lineage": "anthropic/claude-opus-5",
    "runtime": "opencode",
}
STRING_WRITER: Final = f"opencode/gpt-5.6-sol@{SHA}"


def write_chain(root: Path, harness: str, document: bytes) -> Path:
    path = root / harness / integrity.FEEDBACK_CHAIN
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(document)
    return path


def shape_findings(root: Path) -> list[str]:
    return [
        item.message
        for item in integrity.check_feedback_chain(str(root), evaluation_time=NOW)
        if "chain line" in item.message or "does not link" in item.message
    ]


def test_legacy_object_and_string_writers_are_rewritten_into_the_closed_schema(
    tmp_path: Path,
) -> None:
    # Given a harness-root chain from before github_id joined the schema, mixing both
    # legacy writer shapes, that the walker refuses at line 1.
    document = legacy_chain([OBJECT_WRITER, STRING_WRITER, OBJECT_WRITER])
    chain = write_chain(tmp_path, ".memory", document)
    assert any("missing the field github_id" in item for item in shape_findings(tmp_path))
    # When migrated under the operator's login.
    report = migrate.migrate(tmp_path, feedback_github_id="ada")
    # Then every line carries the closed field set, links, and the walker's shape pass is clean.
    assert report.status == "complete"
    assert "./.memory/feedback.chain.jsonl" in report.changed
    lines = [json.loads(raw) for raw in chain.read_bytes().splitlines()]
    assert all(set(line) == integrity.CHAIN_FIELDS for line in lines)
    writers = [line["writer"] for line in lines]
    assert writers == [
        f"opencode/anthropic/claude-opus-5@{SHA}",
        STRING_WRITER,
        f"opencode/anthropic/claude-opus-5@{SHA}",
    ]
    assert all(line["github_id"] == "ada" for line in lines)
    walked, head = integrity.walk_chain_document(chain, chain.read_bytes())
    assert walked == []
    assert head == (3, lines[-1]["entry_hash"])
    assert not shape_findings(tmp_path)
    # And the original bytes survive as an immutable backup with a revalidation row.
    backup = tmp_path / ".trinity" / "migrations" / "backups" / migrate._digest(document)
    assert backup.read_bytes() == document
    assert any("sign a fresh checkpoint" in row for row in report.needs_revalidation)


def test_migration_without_a_login_holds_and_names_the_flag(tmp_path: Path) -> None:
    chain = write_chain(tmp_path, ".seed", legacy_chain([STRING_WRITER]))
    before = chain.read_bytes()
    report = migrate.migrate(tmp_path)
    assert report.status == "hold"
    assert any("--feedback-github-id" in item for item in report.blocked)
    assert chain.read_bytes() == before


@pytest.mark.parametrize("login", ["unattributed", "not a login", "-lead", ""])
def test_an_unusable_login_holds(tmp_path: Path, login: str) -> None:
    write_chain(tmp_path, ".audit", legacy_chain([STRING_WRITER]))
    report = migrate.migrate(tmp_path, feedback_github_id=login)
    assert report.status == "hold"


def test_a_published_checkpoint_over_the_legacy_head_holds(tmp_path: Path) -> None:
    document = legacy_chain([OBJECT_WRITER])
    chain = write_chain(tmp_path, ".memory", document)
    head = json.loads(document.splitlines()[-1])["entry_hash"]
    (tmp_path / ".memory" / "checkpoints.yaml").write_text(
        f"- root: {head}\n  seq: 1\n  signature: .memory/feedback-head.sig\n"
    )
    report = migrate.migrate(tmp_path, feedback_github_id="ada")
    assert report.status == "hold"
    assert any("rollback" in item for item in report.blocked)
    assert chain.read_bytes() == document


def test_a_legacy_chain_that_does_not_link_is_never_laundered(tmp_path: Path) -> None:
    document = legacy_chain([STRING_WRITER, STRING_WRITER])
    tampered = document.replace(b'"seq":2', b'"seq":3')
    chain = write_chain(tmp_path, ".memory", tampered)
    report = migrate.migrate(tmp_path, feedback_github_id="ada")
    assert report.status == "hold"
    assert any("does not link" in item or "carries seq" in item for item in report.blocked)
    assert chain.read_bytes() == tampered


def test_an_unrecognized_writer_shape_holds(tmp_path: Path) -> None:
    write_chain(tmp_path, ".memory", legacy_chain([{"runtime": "opencode"}]))
    report = migrate.migrate(tmp_path, feedback_github_id="ada")
    assert report.status == "hold"
    assert any("writer shape" in item for item in report.blocked)


def test_a_current_chain_is_untouched_and_needs_no_login(tmp_path: Path) -> None:
    body: dict[str, object] = {
        **{
            key: value
            for key, value in legacy_line(1, integrity.CHAIN_GENESIS, "ada").items()
            if key != "entry_hash"
        },
        "github_id": "ada",
    }
    body["entry_hash"] = integrity.chain_digest(body)
    document = canonicalize(body)
    chain = write_chain(tmp_path, ".memory", document)
    report = migrate.migrate(tmp_path)
    assert report.status == "complete"
    assert "./.memory/feedback.chain.jsonl" not in report.changed
    assert chain.read_bytes() == document


def test_rewrite_is_a_pure_function_of_bytes() -> None:
    assert migrate_feedback.rewrite_legacy_chain(b"", "ada") == (None, None)
    assert migrate_feedback.rewrite_legacy_chain(b"[]\n", "ada")[1] is not None
    assert migrate_feedback.rewrite_legacy_chain(b"\xff", "ada")[1] is not None
    first, _ = migrate_feedback.rewrite_legacy_chain(legacy_chain([STRING_WRITER]), "ada")
    second, _ = migrate_feedback.rewrite_legacy_chain(legacy_chain([STRING_WRITER]), "ada")
    assert first == second
