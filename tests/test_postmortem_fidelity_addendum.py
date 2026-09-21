"""POSTMORTEM.md carries the fidelity addendum and leaves sections 1 to 11 intact."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
POSTMORTEM: Final = REPO_ROOT / "POSTMORTEM.md"

ADDENDUM_HEADING: Final = "## 12."

REQUIRED_TOKENS: Final = (
    "compact_boundary",
    "summarization_count",
    "one pass@8 group",
    "HOLD:SUPPRESSED_MEASUREMENT",
    "never retroactive attestation",
)

PRESERVED_HEADINGS: Final = (
    "## 1. Verdict",
    "## 2. Timeline",
    "## 3. Disposition at delivery time",
    "## 4. Root causes, ranked",
    "## 5. Client finding, contract clause, enforcement",
    "## 6. Adversarial-operator threat model",
    "## 7. What landed today",
    "## 8. What is still owed",
    "## 9. Client Reviewer Playbook",
    "## 10. Resubmission plan",
    "## 11. Addendum, 2026-09-16: external authority and remaining rollout",
)

PROSE_CONTINUATION_PREFIXES: Final = ("|", "#", "-", "`", ">", "1.", "2.", "3.")


def _current_text() -> str:
    return POSTMORTEM.read_text(encoding="utf-8")


def _head_text() -> str:
    completed = subprocess.run(
        ("git", "show", "HEAD:POSTMORTEM.md"),
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    return completed.stdout.decode("utf-8")


def _sections_one_to_eleven(text: str) -> str:
    """The byte slice from the first heading up to the addendum, or to the end."""
    start = text.index(PRESERVED_HEADINGS[0])
    tail = text.find(f"\n{ADDENDUM_HEADING}", start)
    return text[start:] if tail == -1 else text[start:tail]


def test_addendum_states_the_five_required_findings() -> None:
    text = _current_text()
    missing = [token for token in REQUIRED_TOKENS if token not in text]
    assert missing == [], f"POSTMORTEM.md is missing required tokens: {missing}"


def test_addendum_is_appended_as_section_twelve() -> None:
    text = _current_text()
    assert f"\n{ADDENDUM_HEADING}" in text, "POSTMORTEM.md carries no `## 12.` section"
    assert "2026-09-18" in text, "the appended section is not dated 2026-09-18"
    assert text.index(f"\n{ADDENDUM_HEADING}") > text.index(PRESERVED_HEADINGS[-1]), (
        "the `## 12.` section does not follow section 11"
    )


def test_existing_headings_are_present_and_unrenumbered() -> None:
    text = _current_text()
    positions = []
    for heading in PRESERVED_HEADINGS:
        assert heading in text, f"POSTMORTEM.md lost the heading {heading!r}"
        positions.append(text.index(heading))
    assert positions == sorted(positions), "the existing headings were reordered"


def test_sections_one_to_eleven_are_byte_unchanged_against_head() -> None:
    assert _sections_one_to_eleven(_current_text()) == _sections_one_to_eleven(_head_text()), (
        "sections 1 to 11 of POSTMORTEM.md differ from `git show HEAD:POSTMORTEM.md`"
    )


def test_addendum_is_ascii_without_em_dashes_or_hard_wraps() -> None:
    text = _current_text()
    addendum = text[text.index(f"\n{ADDENDUM_HEADING}") :]
    assert addendum.isascii(), "the appended section carries non-ASCII bytes"
    assert "\u2014" not in addendum and " -- " not in addendum, (
        "the appended section carries an em-dash"
    )
    lines = addendum.split("\n")
    for index, line in enumerate(lines):
        if index == 0 or not line or line.startswith(PROSE_CONTINUATION_PREFIXES):
            continue
        assert lines[index - 1] == "", (
            f"hard-wrapped paragraph at appended line {index}: {line[:60]!r}"
        )
