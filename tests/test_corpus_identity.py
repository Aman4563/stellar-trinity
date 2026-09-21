"""The shared research corpus is held to ENGRAM invariant E10 by shipped code.

E10 at `ENGRAM.md:486` and Phase H step 2d at `ENGRAM.md:238` state that every
`research/` entry is a side-by-side pair under one `<source-class>/<canonical-id>-<slug>`
stem, that the rendering is derived from the retained bytes by a named tool at a pinned
version, and that the deriving tool identity, its version, and the ENGRAM-computed
`content_digest` are recorded beside the pair. These assertions hold `tools/corpus_identity.py`
to that rule: one test per refusal code, one happy path over `tmp_path`, and one over the
real corpus this repository ships.
"""

import json
from pathlib import Path

from tools import corpus_identity
from tools.corpus_identity_manifest import write_manifest

from tests.bite_shared.registration import bite
from tests.test_research_fidelity_citations import SOURCE_CLASSES


def seed(root: Path, *, tool: str = "pdftotext", version: str = "26.09.0") -> Path:
    paper = root / "research" / "paper"
    paper.mkdir(parents=True)
    retained = paper / "1234.56789-a-slug.pdf"
    retained.write_bytes(b"retained bytes")
    rendering = paper / "1234.56789-a-slug.md"
    rendering.write_text("rendering\n", encoding="utf-8")
    write_manifest(retained, rendering, tool, version)
    return paper


def codes(root: Path) -> list[str]:
    return [problem.code for problem in corpus_identity.inspect(root)]


def test_a_conforming_pair_is_admitted(tmp_path: Path) -> None:
    seed(tmp_path)
    assert codes(tmp_path) == []


def test_a_loose_artifact_is_refused(tmp_path: Path) -> None:
    seed(tmp_path)
    (tmp_path / "research" / "stray.pdf").write_bytes(b"stray")
    assert "CORPUS_LOOSE_ARTIFACT" in codes(tmp_path)


def test_an_unknown_source_class_is_refused(tmp_path: Path) -> None:
    seed(tmp_path)
    (tmp_path / "research" / "gossip").mkdir()
    assert "CORPUS_UNKNOWN_CLASS" in codes(tmp_path)


def test_a_retained_file_without_its_rendering_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    (paper / "1234.56789-a-slug.md").unlink()
    assert "CORPUS_RENDERING_MISSING" in codes(tmp_path)


@bite("engram.md:E3")
def test_a_rendering_without_its_retained_bytes_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    (paper / "1234.56789-a-slug.pdf").unlink()
    assert "CORPUS_RETAINED_MISSING" in codes(tmp_path)


def test_a_missing_manifest_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    (paper / "1234.56789-a-slug.identity.json").unlink()
    assert "CORPUS_MANIFEST_MISSING" in codes(tmp_path)


def test_an_unrecognized_manifest_field_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    manifest = paper / "1234.56789-a-slug.identity.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["provenance"] = "invented"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert "CORPUS_MANIFEST_MALFORMED" in codes(tmp_path)


def test_an_absent_manifest_field_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    manifest = paper / "1234.56789-a-slug.identity.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    del payload["rendering_digest"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert "CORPUS_MANIFEST_MALFORMED" in codes(tmp_path)


@bite("engram.md:E5")
def test_a_retained_digest_mismatch_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    (paper / "1234.56789-a-slug.pdf").write_bytes(b"different bytes")
    assert "CORPUS_DIGEST_MISMATCH" in codes(tmp_path)


def test_a_rendering_digest_mismatch_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    (paper / "1234.56789-a-slug.md").write_text("edited\n", encoding="utf-8")
    assert "CORPUS_RENDERING_DIGEST_MISMATCH" in codes(tmp_path)


def test_an_unrecorded_deriving_tool_is_refused(tmp_path: Path) -> None:
    seed(tmp_path, tool="", version="")
    assert "CORPUS_TOOL_UNRECORDED" in codes(tmp_path)


def test_a_manifest_naming_another_stem_is_refused(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    manifest = paper / "1234.56789-a-slug.identity.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["stem"] = "9999.99999-another-slug"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert "CORPUS_STEM_MISMATCH" in codes(tmp_path)


def test_record_refuses_to_overwrite_an_existing_manifest(tmp_path: Path) -> None:
    paper = seed(tmp_path)
    again = corpus_identity.main(
        [
            "corpus_identity.py",
            "record",
            "--root",
            str(tmp_path),
            "--tool",
            "other",
            "--tool-version",
            "1",
        ]
    )
    payload = json.loads((paper / "1234.56789-a-slug.identity.json").read_text(encoding="utf-8"))
    assert again == 1
    assert payload["deriving_tool"] == "pdftotext"


def test_the_source_class_set_matches_the_research_fidelity_lock() -> None:
    # Given: two closed source-class sets, one in the tool and one in the fidelity suite.
    # When: they are compared.
    # Then: they are the same set, so neither can drift away from the other unnoticed.
    assert corpus_identity.SOURCE_CLASSES == SOURCE_CLASSES


def test_the_real_research_corpus_conforms() -> None:
    assert corpus_identity.inspect(Path(__file__).resolve().parents[1]) == []
