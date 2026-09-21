"""The harness-effects literature is recorded in this repository's research surface.

`docs/measurement-fidelity.md` grounds its taxonomy in five arXiv papers and four
engineering sources. A document that cites what the repository never stored is a
bibliography rather than a corpus, so these assertions hold the research surface,
the `research/` pair convention plus the dated Phase S scribe block in
`CHANGELOG.md`, to the full cited set, and hold the document's own citation set to
a subset of it. A divergence between the two is itself a finding.
"""

import re
from pathlib import Path

import pytest
from tools.corpus_identity_manifest import digest as content_digest

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
PAPERS = RESEARCH / "paper"
CHANGELOG = ROOT / "CHANGELOG.md"
FIDELITY_DOC = ROOT / "docs" / "measurement-fidelity.md"

SOURCE_CLASSES = frozenset(
    {
        "paper",
        "institute",
        "board",
        "lab",
        "aggregator",
        "engineering",
        "hosted",
        "lead",
    }
)

SCRIBE_DATE = "2026-09-18"
SCRIBE_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}): ENGRAM Phase S scribe block\b")
BARE_ARXIV_ID = re.compile(r"\b(\d{4}\.\d{4,5})\b")
CITED_ARXIV_ID = re.compile(r"arXiv (\d{4}\.\d{4,5})")

HARNESS_EFFECT_PAPERS: tuple[tuple[str, str], ...] = (
    ("2107.03374", "unbiased"),
    ("2602.07150", "temperature zero"),
    ("2605.23950", "7.8"),
    ("2608.11242", "17 percent"),
    ("2609.09218", "double measurement confound"),
)

ENGINEERING_SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "claude-code context compaction",
        (
            "compact_boundary",
            "isCompactSummary",
            "DISABLE_AUTO_COMPACT",
            "anthropics/claude-code",
            "#42817",
            "#57490",
            "v2.1.159",
            "#64520",
        ),
    ),
    ("OpenHands condenser", ("Condensation", "condenser_config")),
    (
        "Harbor ATIF version 1.8",
        (
            "ATIF version 1.8",
            "continued_trajectory_ref",
            "Metrics",
            "Agent.model_name",
            "Agent.version",
        ),
    ),
    ("Harbor terminal-bench-science", ("terminal-bench-science", "deef067")),
)

ENGINEERING_TOKENS: tuple[str, ...] = tuple(
    token for _, tokens in ENGINEERING_SOURCES for token in tokens
)


def research_stems() -> dict[str, set[str]]:
    """Return every `paper/<arxiv-id>-<slug>` stem in `research/` keyed by its arXiv id."""
    stems: dict[str, set[str]] = {}
    for entry in sorted(PAPERS.iterdir()):
        if entry.suffix not in {".pdf", ".md"}:
            continue
        found = BARE_ARXIV_ID.match(entry.stem)
        if found is None:
            continue
        stems.setdefault(found.group(1), set()).add(entry.stem)
    return stems


def research_suffixes(stem: str) -> set[str]:
    return {entry.suffix for entry in PAPERS.iterdir() if entry.stem == stem}


def scribe_blocks() -> dict[str, str]:
    """Return every dated Phase S scribe block in `CHANGELOG.md` keyed by its date."""
    blocks: dict[str, str] = {}
    for raw in CHANGELOG.read_text(encoding="utf-8").split("\n"):
        found = SCRIBE_LINE.match(raw.strip())
        if found is not None:
            blocks[found.group(1)] = raw.strip()
    return blocks


def research_surface() -> str:
    """Return the research surface: every source class's file names plus every scribe block."""
    names = sorted(
        entry.name
        for source_class in RESEARCH.iterdir()
        if source_class.is_dir()
        for entry in source_class.iterdir()
    )
    return "\n".join([*names, *scribe_blocks().values()])


def conforms(retained: Path, recorded: str) -> bool:
    """Return whether retained bytes carry a rendering and hash to the recorded digest."""
    return retained.with_suffix(".md").is_file() and content_digest(retained) == recorded


def fidelity_doc() -> str:
    return FIDELITY_DOC.read_text(encoding="utf-8")


@pytest.mark.parametrize(("arxiv_id", "claim"), HARNESS_EFFECT_PAPERS)
def test_research_carries_the_paper_pair(arxiv_id: str, claim: str) -> None:
    assert claim
    stems = research_stems().get(arxiv_id, set())
    assert stems, f"research/ carries no stem for arXiv {arxiv_id}"
    assert len(stems) == 1, f"arXiv {arxiv_id} resolves more than one stem: {sorted(stems)}"
    stem = stems.pop()
    assert research_suffixes(stem) == {".pdf", ".md"}, (
        f"research/{stem} is not a side-by-side .pdf and .md pair"
    )


@pytest.mark.parametrize(("arxiv_id", "claim"), HARNESS_EFFECT_PAPERS)
def test_research_surface_names_the_paper(arxiv_id: str, claim: str) -> None:
    assert arxiv_id in research_surface(), f"the research surface never names arXiv {arxiv_id}"
    block = scribe_blocks().get(SCRIBE_DATE, "")
    assert arxiv_id in block, f"the {SCRIBE_DATE} scribe block never names arXiv {arxiv_id}"
    assert claim in block, f"the {SCRIBE_DATE} scribe block never states why {arxiv_id} is cited"


@pytest.mark.parametrize(("source", "tokens"), ENGINEERING_SOURCES)
def test_scribe_block_records_the_engineering_source(source: str, tokens: tuple[str, ...]) -> None:
    block = scribe_blocks().get(SCRIBE_DATE, "")
    assert block, f"CHANGELOG.md carries no {SCRIBE_DATE} Phase S scribe block"
    missing = [token for token in tokens if token not in block]
    assert not missing, f"the {SCRIBE_DATE} scribe block records {source} without {missing}"


def test_document_arxiv_citations_are_a_subset_of_the_research_surface() -> None:
    cited = set(CITED_ARXIV_ID.findall(fidelity_doc()))
    assert cited, "docs/measurement-fidelity.md cites no arXiv paper"
    recorded = set(BARE_ARXIV_ID.findall(research_surface()))
    assert cited <= recorded, f"cited but never recorded: {sorted(cited - recorded)}"


def test_document_engineering_citations_are_a_subset_of_the_research_surface() -> None:
    document = fidelity_doc()
    surface = research_surface()
    cited = {token for token in ENGINEERING_TOKENS if token in document}
    assert cited, "docs/measurement-fidelity.md cites no engineering source"
    recorded = {token for token in ENGINEERING_TOKENS if token in surface}
    assert cited <= recorded, f"cited but never recorded: {sorted(cited - recorded)}"


def test_every_research_artifact_is_source_class_qualified() -> None:
    loose = [entry for entry in RESEARCH.iterdir() if entry.is_file()]
    assert not loose, f"research/ still carries unclassed artifacts: {[e.name for e in loose]}"
    classes = {entry.name for entry in RESEARCH.iterdir() if entry.is_dir()}
    assert classes and classes <= SOURCE_CLASSES


def test_a_matching_digest_is_admitted(tmp_path: Path) -> None:
    retained = tmp_path / "x-slug.pdf"
    retained.write_bytes(b"bytes")
    (tmp_path / "x-slug.md").write_text("rendering", encoding="utf-8")
    assert conforms(retained, content_digest(retained))


def test_a_digest_mismatch_is_refused(tmp_path: Path) -> None:
    retained = tmp_path / "x-slug.pdf"
    retained.write_bytes(b"bytes")
    (tmp_path / "x-slug.md").write_text("rendering", encoding="utf-8")
    assert not conforms(retained, "0" * 64)


def test_a_rendering_without_its_retained_source_is_refused(tmp_path: Path) -> None:
    retained = tmp_path / "x-slug.pdf"
    retained.write_bytes(b"bytes")
    assert not conforms(retained, content_digest(retained))
