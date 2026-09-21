from pathlib import Path

from tests.harness_imports import integrity

ROOT = Path(__file__).resolve().parents[1]

OPENHANDS_PIN = "405bae7140d7e961a75f4910a0b2e7069731db96"
PRISMA_S_DOI = "10.1186/s13643-020-01542-z"

RETIRED_CONFIDENCE = ("replicated", "single-source", "adjacent-anchored")
GRADE_LEVELS = ("high", "moderate", "low", "very_low")
GRADE_DOMAINS = (
    "risk of bias",
    "inconsistency",
    "indirectness",
    "imprecision",
    "publication bias",
    "large effect",
    "dose-response",
    "plausible confounding",
)

RECEIPT_ADDITIONS = (
    "substrate_kind",
    "filter_provenance",
    "strategy_provenance",
    "update_method",
    "peer_review",
    "deduplication",
)

RECEIPT_FIELDS = (
    "substrate",
    "substrate_tier",
    "canonical_identity_resolved",
    "transport",
    "endpoint",
    "query_verbatim",
    "filters",
    "date_bounds",
    "http_status",
    "records_returned",
    "records_admitted",
    "rung_answered",
    "result_set_digest",
    "instant_utc",
    "exhaustion",
    *RECEIPT_ADDITIONS,
)


def test_a_source_tier_token_is_closed_vocabulary() -> None:
    assert (
        integrity.check_disposition_vocab("ENGRAM.md", "A `T1` anchor outranks a `T7` lead.") == []
    )


def test_a_source_tier_is_never_another_state_class() -> None:
    for other in (
        integrity.LEDGER_STATES,
        integrity.LEVER_STATES,
        integrity.ROW_STATES,
        integrity.TASK_STATES,
        integrity.SPINE_MARKERS,
        integrity.BAND_STATES,
    ):
        assert not integrity.SOURCE_TIERS & other
    assert {"CANDIDATE", "ANCHORED", "SUPERSEDED"} == integrity.ROW_STATES


def test_engram_states_every_source_tier() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    for tier in sorted(integrity.SOURCE_TIERS):
        assert f"`{tier}`" in text, f"ENGRAM.md never names tier {tier}"
    assert "Search arXiv exhaustively" not in text
    assert "never descend on a failed lane" in text.lower()


def test_engram_closes_the_discovery_receipt_schema() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    assert "engram.receipt/v1" in text
    for field in RECEIPT_FIELDS:
        assert f"`{field}`" in text, f"ENGRAM.md never names receipt field {field}"
    assert "`exhausted`" in text and "`unexhausted`" in text


def test_the_receipt_cites_its_reporting_standard() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    assert PRISMA_S_DOI in text
    assert "PRISMA-S" in text
    assert "coverage gap" in text
    for field in RECEIPT_ADDITIONS:
        assert f"`{field}`" in text, f"ENGRAM.md never names receipt field {field}"


def test_engram_pins_the_target_harness_shape() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    assert OPENHANDS_PIN in text
    assert "mutable-data-alias" in text
    assert "tmdate" in text


def test_the_three_retired_confidence_tokens_are_gone() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    for token in RETIRED_CONFIDENCE:
        assert f"`{token}`" not in text, f"ENGRAM.md still carries retired confidence {token}"


def test_engram_states_the_grade_scale_and_its_domains() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    for level in GRADE_LEVELS:
        assert f"`{level}`" in text
    for domain in GRADE_DOMAINS:
        assert domain in text


def test_the_confidence_scale_names_its_sources() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    assert "Cochrane Handbook chapter 14" in text
    assert "Oxford Centre for Evidence-Based Medicine" in text
    assert "GRADE" in text


def test_supersession_is_an_edge_and_not_a_new_row_state() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    assert "engram.supersession/v1" in text
    assert "`superseded_kind`" in text
    assert "`revoked`" in text and "`deprecated`" in text and "revoked-by" in text
    assert "engram.hardness/v2" in text and "`row_version`" in text
    assert {"CANDIDATE", "ANCHORED", "SUPERSEDED"} == integrity.ROW_STATES


def test_the_two_arxiv_typed_schemas_have_versioned_successors() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    assert "engram.brief/v2" in text and "engram.next/v2" in text
    assert "engram.brief/v1" not in text and "engram.next/v1" not in text
    assert "engram.harvest/v1" in text
    assert "artifact stem" in text and "paper stem" not in text
    assert "bare arXiv identifier" not in text


def test_the_pdf_only_refusal_is_scoped_to_the_paper_class() -> None:
    text = (ROOT / "ENGRAM.md").read_text(encoding="utf-8")
    assert "other than derivation from the stored PDF is non-conformant" not in text
    assert "other than derivation from the retained source bytes is non-conformant" in text
    assert "for a `paper` artifact the retained source bytes are the stored PDF" in text
