import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]


def test_corpus_self_check_still_passes() -> None:
    # Given: the existing paper corpus self-check entry point.
    script = ROOT / "paper" / "data" / "corpus.py"

    # When: the self-check runs with the current interpreter.
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )

    # Then: the original corpus remains valid with 21 anchors.
    assert completed.returncode == 0, completed.stderr
    assert "total_anchors = 21" in completed.stdout


def test_every_anchor_keys_on_a_bare_arxiv_id_as_its_paper_class_source_identity() -> None:
    # Given: the paper's checked-in anchor artifact, now source-classed.
    anchors = json.loads((ROOT / "paper" / "data" / "corpus.json").read_text(encoding="utf-8"))[
        "anchors"
    ]

    # When: every anchor's identifier is collected.
    ids: list[str] = [anchor["arxiv_id"] for anchor in anchors]

    # Then: arxiv_id remains the unique bare source identity of the paper class.
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"\d{4}\.\d{4,5}", value) for value in ids)
    assert {anchor["source_class"] for anchor in anchors} == {"paper"}


def test_every_anchor_carries_a_content_digest() -> None:
    # Given: the paper's checked-in anchor artifact.
    anchors = json.loads((ROOT / "paper" / "data" / "corpus.json").read_text(encoding="utf-8"))[
        "anchors"
    ]

    # When: every anchor's recorded content digest is read.
    # Then: each one is a bare lowercase SHA-256 hexadecimal digest.
    assert all(re.fullmatch(r"[0-9a-f]{64}", anchor["content_digest"]) for anchor in anchors)


def test_every_anchor_digest_matches_the_research_manifest() -> None:
    # Given: the paper's checked-in anchor artifact.
    anchors = json.loads((ROOT / "paper" / "data" / "corpus.json").read_text(encoding="utf-8"))[
        "anchors"
    ]

    # When: each anchor is joined to its research manifest by arXiv id to stem prefix.
    # Then: exactly one manifest resolves and it records the same content digest.
    for anchor in anchors:
        found = sorted((ROOT / "research" / "paper").glob(f"{anchor['arxiv_id']}-*.identity.json"))
        assert len(found) == 1, f"{anchor['arxiv_id']} resolves {len(found)} manifests"
        recorded = json.loads(found[0].read_text(encoding="utf-8"))
        assert recorded["content_digest"] == anchor["content_digest"]
