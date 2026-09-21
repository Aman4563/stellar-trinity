"""DEFERRED.md carries the six unenforced measurement-fidelity obligations.

The register is the honest counterpart of the contract prose Tasks 3 and 4 landed:
every fidelity clause that fails closed on paper but that nothing evaluates has to
appear here as a four-column row, and no row already standing may leave beside it.
These assertions pin both halves, located by row text rather than by line number,
because the register's line numbers move whenever a neighbouring section grows.
"""

from pathlib import Path

import pytest

REGISTER = Path(__file__).resolve().parents[1] / "DEFERRED.md"

REGISTER_COLUMNS = 4

ADDED_OBLIGATIONS: tuple[tuple[str, str], ...] = (
    (
        "Independent execution authority controls admission, execution, observation, and custody",
        "FORGE Phase 4 item 2b",
    ),
    ("Observation capture precedes operator editing", "CRUCIBLE step 8p"),
    ("Configuration adequacy judged by a governance authority", "FORGE Phase 4 item 3a"),
    ("Precommitted population roster reconciled against realized groups", "FORGE rule 2f"),
    ("Effective request and response capture", "CRUCIBLE step 8u"),
    ("Provider-internal routing declared and verified", "`docs/execution-authority.md`"),
)

RELEASE_BINDING_OBLIGATION: tuple[str, str] = (
    "Oracle execution-fidelity outcome binds the G-FID ledger and execution attestation",
    "CRUCIBLE step 8u",
)

PRESERVED_OBLIGATIONS: tuple[str, ...] = (
    "Execution attestation present, unexpired, and field-consistent",
    "Per-lane consumption metering",
    "External operator commits and selects each stratified sample after batch freeze",
    "External execution service produces accepted oracle receipts",
    "Every graded literal is in the statement, the base commit, or an accepted alternate",
    (
        "Judge runner, prompt, reducer, model id, temperature, seed, and trial rows ship "
        "inside the bundle and replay to the recorded score"
    ),
)


def register_text() -> str:
    return REGISTER.read_text(encoding="utf-8")


def register_rows() -> dict[str, list[str]]:
    """Return every register table row keyed by its first cell."""
    rows: dict[str, list[str]] = {}
    for raw in register_text().split("\n"):
        line = raw.strip()
        if not line.startswith("|") or set(line) <= set("| -:"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells and cells[0]:
            rows[cells[0]] = cells
    return rows


@pytest.mark.parametrize(("obligation", "citation"), ADDED_OBLIGATIONS)
def test_register_carries_the_added_obligation(obligation: str, citation: str) -> None:
    rows = register_rows()
    assert obligation in rows, f"DEFERRED.md never registers {obligation!r}"
    cells = rows[obligation]
    assert len(cells) == REGISTER_COLUMNS, cells
    assert all(cells), f"{obligation!r} leaves a register column empty"
    assert citation in cells[1], cells[1]


@pytest.mark.parametrize("obligation", PRESERVED_OBLIGATIONS)
def test_register_preserves_the_standing_obligation(obligation: str) -> None:
    assert obligation in register_rows(), f"DEFERRED.md dropped the standing row {obligation!r}"


def test_authority_row_names_both_pending_sources() -> None:
    cells = register_rows()[ADDED_OBLIGATIONS[0][0]]
    assert "`docs/execution-authority.md`" in cells[1], cells[1]
    assert "both pending" in cells[1], cells[1]


def test_trace_row_names_the_fidelity_instrument() -> None:
    cells = register_rows()["Effective request and response capture"]
    assert "G-FID-TRACE" in cells[1], cells[1]


def test_register_carries_the_release_binding_obligation() -> None:
    # Given: the row the mandatory sixth core control left behind, which no verifier discharges.
    obligation, citation = RELEASE_BINDING_OBLIGATION
    rows = register_rows()
    # When: reading it back from the register.
    assert obligation in rows, f"DEFERRED.md never registers {obligation!r}"
    cells = rows[obligation]
    # Then: it is a complete row naming the control and the contract that states it.
    assert len(cells) == REGISTER_COLUMNS, cells
    assert all(cells), f"{obligation!r} leaves a register column empty"
    assert citation in cells[1], cells[1]
    assert "execution_fidelity" in cells[2], cells[2]


def test_evaluator_row_exits_with_its_implementation() -> None:
    # Given: the machine-read obligation register.
    # When: reading the evaluator's former row identity.
    rows = register_rows()
    # Then: the implemented evaluator obligation cannot silently return.
    assert not any(
        row.startswith("Pilot evaluator applies the exact binomial bound") for row in rows
    )
