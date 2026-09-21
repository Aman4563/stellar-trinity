"""Boundary tests distinguish pre-decode and descriptor-relative guarantees."""

import json
import os
from collections.abc import Callable

import pytest
from tools import _bounded_json as bounded
from tools import forensics as f
from tools.forensics.reading import TraceReadError

from tests.test_forensics_family import Inputs, inputs

__all__ = ["inputs"]


def test_deep_json_is_refused_before_decoder(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given a decoder that must never receive an excessive document.
    def unexpected_decode(
        data: str,
        *,
        object_pairs_hook: Callable[[list[tuple[str, bounded.Json]]], dict[str, bounded.Json]],
    ) -> None:
        del data, object_pairs_hook
        pytest.fail("json.loads reached for a pre-scan refusal")

    monkeypatch.setattr(json, "loads", unexpected_decode)
    # When scanning 100k nested containers, then refuse before decoding.
    with pytest.raises(bounded.BoundedJsonError):
        bounded.load_bounded_json(b"[" * 100000)


def test_decoder_recursion_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given a decoder exhausting its implementation recursion budget.
    def recursive_decode(
        data: str,
        *,
        object_pairs_hook: Callable[[list[tuple[str, bounded.Json]]], dict[str, bounded.Json]],
    ) -> None:
        del data, object_pairs_hook
        raise RecursionError

    monkeypatch.setattr(json, "loads", recursive_decode)
    # When decoding a shallow document, then RecursionError never escapes.
    with pytest.raises(bounded.BoundedJsonError):
        bounded.load_bounded_json(b"{}")


@pytest.mark.parametrize("raw", [b"[1,2,3]", b'{"a":1,"b":2,"c":3}'])
def test_container_item_limit(raw: bytes) -> None:
    # Given an excessive container, when decoded, then refuse its item count.
    with pytest.raises(bounded.BoundedJsonError):
        bounded.load_bounded_json(raw, max_items=2)


def test_quoted_delimiters_do_not_count_as_depth() -> None:
    # Given delimiters and escapes inside a string, when decoded, then retain it.
    assert bounded.load_bounded_json(b'["[{\\"}"]', max_depth=1) == ['[{"}']


def test_ledger_refuses_symlinked_run_ancestor(inputs: Inputs) -> None:
    # Given an alias in the allowed namespace.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    audit = root.parent / ".audit"
    audit.mkdir()
    target = root.parent / "outside"
    target.mkdir()
    (audit / "runs").symlink_to(target, target_is_directory=True)
    # When publishing, then refuse the intermediate symlink.
    with pytest.raises(f.FidelityLedgerPathError):
        f.emit_fidelity_ledger(ledger, audit / "runs/run-12345", project_root=root.parent)


def test_ledger_retains_destination_descriptor(
    inputs: Inputs, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given an ancestor swapped for a symlink just before atomic publication.
    root, config, roster = inputs
    ledger = f.run_fidelity_family(root, "claude_code_jsonl", config, roster)
    audit = root.parent / ".audit"
    outside = root.parent / "outside"
    outside.mkdir()
    sentinel = outside / "fidelity.yaml"
    sentinel.write_bytes(b"untouched")
    original_replace = os.replace

    def swap(source: str, destination: str, *, src_dir_fd: int, dst_dir_fd: int) -> None:
        audit.rename(root.parent / "retained")
        audit.symlink_to(outside, target_is_directory=True)
        original_replace(source, destination, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr("tools.forensics.ledger.os.replace", swap)
    # When publishing, then the replacement cannot redirect writes to the alias target.
    f.emit_fidelity_ledger(ledger, audit, project_root=root.parent)
    assert sentinel.read_bytes() == b"untouched"
    assert (root.parent / "retained/fidelity.yaml").is_file()


def test_family_refuses_symlinked_ancestor(inputs: Inputs) -> None:
    # Given an alias above the supplied trajectory root.
    root, config, roster = inputs
    alias = root.parent / "alias"
    alias.symlink_to(root.parent, target_is_directory=True)
    # When discovering rollouts, then refuse instead of following the alias.
    with pytest.raises(TraceReadError):
        f.run_fidelity_family(
            alias / root.name, "claude_code_jsonl", config, roster, project_root=root.parent
        )
