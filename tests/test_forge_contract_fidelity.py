"""FORGE.md must carry the group-level release rule and the suppression dispositions.

The author contract is the only surface a pasting operator reads, so a clause that
lives in `docs/` and not in `FORGE.md` binds nobody. These assertions pin the
literal tokens the measurement-fidelity work order requires and pin the removal of
the arithmetically infeasible hardcoded group floor it replaces.
"""

from pathlib import Path

import pytest

from tests.harness_imports import integrity

FORGE = Path(__file__).resolve().parents[1] / "FORGE.md"

REQUIRED_TOKENS: tuple[str, ...] = (
    "HOLD:SUPPRESSED_MEASUREMENT",
    "BLOCK:INVALID_PILOT",
    "trinity.harness-config/v1",
    "trinity.trial-conformance/v1",
    "conforming",
    "nonconforming",
    "indeterminate",
    "minimum_groups",
)

REQUIRED_VOCAB: tuple[str, ...] = (
    "harness_config_digest",
    "measured_group_floor",
    "max_affected_group_fraction",
)

SUPPRESSION_REASONS: tuple[str, ...] = (
    "context-uncovered",
    "fidelity-unverified",
    "config-unpinned",
    "config-drift",
    "config-inadequate",
    "handoff-unverified",
)

RELEASE_RULE_CLAUSES: tuple[str, ...] = (
    "predeclared disjoint groups",
    "Z*_g",
    "never removed from the fixed",
    "U(0, N) < c",
    "never authorizes release",
    ".seed/harness-config.json",
)

ORDERED_REASONS: tuple[str, ...] = (
    "config-unpinned for a missing, unbound, or unapproved configuration",
    "config-drift for an attested effective configuration contradicting the binding",
    "config-inadequate for missing adequacy approval or demonstrated inadequacy",
    "handoff-unverified for a failed or unprovable submission handoff",
    "context-uncovered for insufficient context-handling evidence",
    "fidelity-unverified for every remaining observed suppressing violation",
)

RETIRED_CLAUSE: str = "at least eight independent pass-at-8 groups"

RETIRED_TRANSMISSION: str = "and its reason"

PHASE_FOUR_OPEN: str = "### Phase 4: external pilot evaluation, out-of-band only"

PHASE_FOUR_CLOSE: str = "### Phase 4.5: release evidence sign-off"

AUTHORITY_TOKENS: tuple[str, ...] = (
    "docs/execution-authority.md",
    "admission",
    "execution",
    "observation",
    "custody",
    "BLOCK:INVALID_PILOT",
)

AUTHORITY_ROUTING: tuple[str, ...] = (
    "population that cannot be proven against that roster",
    "privately classifies as `fidelity-unverified`",
    "privately classifies as `config-drift`",
)

FALLBACK_PHRASE: str = "independent re-execution"


@pytest.fixture(scope="module")
def forge() -> str:
    return FORGE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def phase_four(forge: str) -> str:
    open_at = forge.index(PHASE_FOUR_OPEN)
    close_at = forge.index(PHASE_FOUR_CLOSE)
    assert open_at < close_at, "Phase 4.5 precedes Phase 4"
    return forge[open_at:close_at]


@pytest.mark.parametrize("token", REQUIRED_TOKENS)
def test_forge_names_fidelity_token(forge: str, token: str) -> None:
    assert token in forge, f"FORGE.md never names {token!r}"


@pytest.mark.parametrize("token", REQUIRED_VOCAB)
def test_forge_names_declared_vocabulary(forge: str, token: str) -> None:
    assert token in integrity.CONTRACT_VOCAB["FORGE.md"], f"{token!r} is undeclared"
    assert token in forge, f"FORGE.md never names required vocabulary {token!r}"


@pytest.mark.parametrize("reason", SUPPRESSION_REASONS)
def test_forge_names_suppression_reason(forge: str, reason: str) -> None:
    assert reason in forge, f"FORGE.md never names suppression reason {reason!r}"


@pytest.mark.parametrize("clause", RELEASE_RULE_CLAUSES)
def test_forge_states_group_release_clause(forge: str, clause: str) -> None:
    assert clause in forge, f"FORGE.md never states {clause!r}"


def test_forge_drops_the_infeasible_group_floor(forge: str) -> None:
    assert RETIRED_CLAUSE not in forge, f"FORGE.md still hardcodes {RETIRED_CLAUSE!r}"


@pytest.mark.parametrize("reason", ORDERED_REASONS)
def test_forge_orders_the_suppression_reasons(forge: str, reason: str) -> None:
    assert reason in forge, f"FORGE.md never states the ordered reason clause {reason!r}"


def test_forge_closes_the_reason_order(forge: str) -> None:
    assert "every finding privately" in forge
    assert "with no closed reason recorded" in forge
    assert "Earlier matches exclude later reasons" in forge
    assert "Other governing `BLOCK` conditions retain precedence" in forge


def test_forge_never_receives_the_selected_code(forge: str) -> None:
    assert "These six codes are private audit-side classifications" in forge
    assert "never the selected code, any instrument's finding, or the underlying evidence" in forge
    assert "the permitted three-token trial statuses" in forge
    assert RETIRED_TRANSMISSION not in forge, f"FORGE.md still transmits {RETIRED_TRANSMISSION!r}"


def test_forge_registers_both_new_dispositions() -> None:
    assert "HOLD:SUPPRESSED_MEASUREMENT" in integrity.DISPOSITIONS
    assert "BLOCK:INVALID_PILOT" in integrity.DISPOSITIONS


@pytest.mark.parametrize("token", AUTHORITY_TOKENS)
def test_phase_four_binds_the_authority_duties(phase_four: str, token: str) -> None:
    assert token in phase_four, f"FORGE.md Phase 4 never names {token!r}"


@pytest.mark.parametrize("clause", AUTHORITY_ROUTING)
def test_phase_four_routes_every_unmet_duty(phase_four: str, clause: str) -> None:
    assert clause in phase_four, f"FORGE.md Phase 4 never routes {clause!r}"


def test_phase_four_states_the_independent_re_execution_fallback(phase_four: str) -> None:
    fallback = [
        sentence for _, sentence in integrity.sentences(phase_four) if FALLBACK_PHRASE in sentence
    ]
    assert fallback, f"FORGE.md Phase 4 never names the {FALLBACK_PHRASE!r} fallback"
    assert any("neither this agent nor the auditor" in sentence for sentence in fallback), (
        "the fallback sentence never names the party controlling neither side"
    )
    assert "never erases the original groups" in phase_four
    assert "stay in the fixed N" in phase_four


def test_phase_four_keeps_provider_routing_a_declared_assumption(phase_four: str) -> None:
    assert "Provider-internal routing stays a declared trust assumption" in phase_four
    assert "narrows the assumption set and never empties it" in phase_four


def test_phase_r_states_the_content_addressed_stem(forge: str) -> None:
    assert "<source-class>/<canonical-id>-<slug>" in forge
    assert "the SHA-256 of the retained bytes rather than the stem" in forge
    assert "<arxiv-id>-<slug>" not in forge


def test_forge_passes_every_contract_check(forge: str) -> None:
    for check in integrity.CONTRACT_CHECKS:
        assert check("FORGE.md", forge) == [], check.__name__
