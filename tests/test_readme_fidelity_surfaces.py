"""README.md names every measurement-fidelity surface and refuses the superseded schemas."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
README: Final = REPO_ROOT / "README.md"

NEW_MODULES: Final = (
    "tools/harness_config.py",
    "tools/forensics",
    "tools/backfill.py",
)

NEW_DOCUMENTS: Final = (
    "docs/measurement-fidelity.md",
    "docs/execution-authority.md",
)

SCHEMA_INVENTORY: Final = (
    "trinity.harness-config/v1",
    "trinity.pilot-policy/v2",
    "trinity.pilot-attempt/v2",
    "trinity.execution/v2",
    "trinity.oracle-run/v4",
    "trinity.release-policy/v3",
)

FIDELITY_VOCABULARY: Final = (
    "execution_fidelity",
    "G-FID",
    "HOLD:SUPPRESSED_MEASUREMENT",
    "BLOCK:INVALID_PILOT",
)

SUPERSEDED_SCHEMAS: Final = (
    "trinity.oracle-run/v3",
    "trinity.release-policy/v2",
)

REFUSAL_PHRASE: Final = "no legacy acceptance route"

DISPOSITION_COMPATIBILITY: Final = (
    "trinity.release-disposition/v3",
    "Existing valid signed v2 bytes remain accepted",
    "named-v2 compatibility path",
)

ABSENT_RUNNER: Final = "the external quality-controls runner remains absent"

SENTENCE_BOUNDARY: Final = re.compile(r"(?<=[a-z0-9`)\]])\.\s+(?=[A-Z`\[])")


def _readme_text() -> str:
    return README.read_text(encoding="utf-8")


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in SENTENCE_BOUNDARY.split(text) if part.strip()]


def test_readme_names_the_new_modules() -> None:
    text = _readme_text()
    missing = [module for module in NEW_MODULES if module not in text]
    assert not missing, f"README.md omits the landed modules: {missing}"


def test_readme_names_the_new_documents() -> None:
    text = _readme_text()
    missing = [document for document in NEW_DOCUMENTS if document not in text]
    assert not missing, f"README.md omits the landed documents: {missing}"


def test_readme_names_the_bumped_schema_inventory() -> None:
    text = _readme_text()
    missing = [schema for schema in SCHEMA_INVENTORY if schema not in text]
    assert not missing, f"README.md omits the schema inventory entries: {missing}"


def test_readme_names_the_fidelity_vocabulary() -> None:
    text = _readme_text()
    missing = [token for token in FIDELITY_VOCABULARY if token not in text]
    assert not missing, f"README.md omits the fidelity vocabulary: {missing}"


def test_readme_counts_six_core_controls() -> None:
    text = _readme_text()
    assert "six core controls" in text, "README.md still counts five core controls"
    assert "five core controls" not in text, "README.md still counts five core controls"


def test_readme_refuses_the_superseded_schemas() -> None:
    text = _readme_text()
    assert REFUSAL_PHRASE in text, f"README.md omits the literal phrase {REFUSAL_PHRASE!r}"
    unrefused = [
        (schema, sentence)
        for sentence in _sentences(text)
        for schema in SUPERSEDED_SCHEMAS
        if schema in sentence and "refus" not in sentence
    ]
    assert not unrefused, f"README.md names a superseded schema outside a refusal: {unrefused}"


def test_readme_preserves_the_named_v2_disposition_compatibility() -> None:
    text = _readme_text()
    missing = [phrase for phrase in DISPOSITION_COMPATIBILITY if phrase not in text]
    assert not missing, f"README.md dropped the disposition compatibility wording: {missing}"


def test_readme_never_claims_an_execution_runner_exists() -> None:
    text = _readme_text()
    assert ABSENT_RUNNER in text, "README.md dropped the absent external runner disclaimer"
