"""Phase obligations: the contract's named work, checks, and human stops.

A row names evidence to reconstruct, never evidence that work is complete. Paths
retain the contract's logical spelling; the caller resolves run and slot scope.
ADR 0005 makes a human or commit barrier a pause of the same run, not a card close.
The report barrier marks the terminal report boundary, after subject-bearing
receipts stop changing and fresh qualification binds them. Nothing here writes,
approves, qualifies, or freezes a run, and an empty artifact set proves nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools.attest import canonical as attest_canonical
else:
    try:
        from tools.attest import canonical as attest_canonical
    except ModuleNotFoundError:
        from attest import canonical as attest_canonical

SCHEMA: Final = "trinity.phase-table/v1"
KINDS: Final = ("work", "gate", "always", "barrier")
BRANCHES: Final = ("default", "G", "H", "N", "S")
CONTRACT: Final[dict[str, str]] = {
    "ENGRAM": "./trinity/ENGRAM.md",
    "FORGE": "./trinity/FORGE.md",
    "CRUCIBLE": "./trinity/CRUCIBLE.md",
}


@dataclass(frozen=True, slots=True)
class Phase:
    id: str
    instrument: str
    kind: str
    contract_heading: str
    branches: tuple[str, ...] = ("default",)
    reads: tuple[str, ...] = ()
    reconciles: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    approval_file: str | None = None
    approval_binds: str | None = None
    depends_on: tuple[str, ...] = ()


# allow: SIZE_OK - the phase table is pure transcription data, kept beside its headings.
TABLE: Final[dict[str, tuple[Phase, ...]]] = {
    "ENGRAM": (
        Phase(
            "0",
            "ENGRAM",
            "work",
            "### Phase 0: scope and discover, read-only except scope file",
            reads=(
                "./.memory/ledger.yaml",
                "./.memory/roots.yaml",
                "./DEFERRED.md",
                "./staging/**",
                "./samples/**",
                "./delivery/**",
                "./.audit/verdicts/**",
            ),
            reconciles=("./.memory/scope.yaml", "./.memory/capabilities.yaml"),
            artifacts=("./.memory/scope.yaml", "./.memory/capabilities.yaml"),
        ),
        Phase(
            "0.5",
            "ENGRAM",
            "gate",
            "### Phase 0.5: scope sign-off gate",
            reads=("./.memory/scope.yaml", "./.memory/roots.yaml", "./.memory/capabilities.yaml"),
            approval_file="./.memory/approval",
            approval_binds="./.memory/scope.yaml",
            depends_on=("0",),
        ),
        Phase(
            "1",
            "ENGRAM",
            "work",
            "### Phase 1: scaffold or reconcile the ledger",
            reads=("./.memory/approval", "./.memory/proofs/**", "./.memory/cohorts/**"),
            reconciles=(
                "./.memory/seed.yaml",
                "./.memory/hardness.yaml",
                "./HARDNESS.md",
                "./.memory/ledger.yaml",
                "./.memory/sequence.yaml",
                "./.memory/checkpoints.yaml",
                "./.memory/canary.yaml",
                "./.memory/fidelity.yaml",
                "./.memory/freshness.yaml",
                "./.memory/roots.yaml",
                "./.memory/forge_view.yaml",
                "./.memory/crucible_view.yaml",
                "./.memory/anchor_standing.yaml",
                "./.memory/current.json",
                "./.memory/TODO.md",
                "./DIRECTIVE.md",
            ),
            artifacts=(
                "./.memory/seed.yaml",
                "./.memory/hardness.yaml",
                "./HARDNESS.md",
                "./.memory/ledger.yaml",
                "./.memory/sequence.yaml",
                "./.memory/checkpoints.yaml",
                "./.memory/forge_view.yaml",
                "./.memory/crucible_view.yaml",
                "./.memory/current.json",
            ),
            depends_on=("0.5",),
        ),
        Phase(
            "2",
            "ENGRAM",
            "always",
            "### Phase 2: prove the ledger deterministically",
            reads=(
                "./.memory/fidelity.yaml",
                "./.memory/hardness.yaml",
                "./.memory/roots.yaml",
                "./.memory/capabilities.yaml",
                "./research/**",
                "./staging/**",
                "./samples/**",
                "./delivery/**",
            ),
            reconciles=(
                "./.memory/supersessions.yaml",
                "./.memory/canary.yaml",
                "./HARDNESS.md",
                "./.memory/freshness.yaml",
                "./.memory/TODO.md",
                "./DIRECTIVE.md",
            ),
            artifacts=("./.memory/freshness.yaml", "./.memory/TODO.md", "./DIRECTIVE.md"),
            depends_on=("1",),
        ),
        Phase(
            "S",
            "ENGRAM",
            "work",
            "### Phase S: scribe the publication surfaces",
            branches=("default", "S"),
            reads=("./.memory/works.yaml", "./.memory/ledger.yaml", "./research/**"),
            reconciles=("./paper/**", "./pitch/**", "./media/**", "./patent/**", "./study/**"),
            artifacts=("./paper/**", "./pitch/**", "./media/**", "./patent/**", "./study/**"),
            depends_on=("2",),
        ),
        Phase(
            "commit",
            "ENGRAM",
            "barrier",
            "### Invocation model: one paste, full flow, swarm lanes",
            depends_on=("2",),
        ),
        Phase(
            "report",
            "ENGRAM",
            "barrier",
            "### Invocation model: one paste, full flow, swarm lanes",
            artifacts=("./DIRECTIVE.md",),
            depends_on=("2",),
        ),
        Phase(
            "H",
            "ENGRAM",
            "work",
            "### Phase H: research and reconcile the hardness contract",
            branches=("H",),
            reads=(
                "./requirements/**",
                "./touchstones/**",
                "./samples/**",
                "./.seed/returns/**",
                "./.memory/anchors.yaml",
                "./.memory/capabilities.yaml",
            ),
            reconciles=(
                "./research/**",
                "./brief/**",
                "./.memory/staging/touchstones/**",
                "./.memory/hardness.yaml",
                "./HARDNESS.md",
                "./harbor.lock",
                "./.memory/anchor_standing.yaml",
                "./.memory/strata.yaml",
            ),
            artifacts=("./.memory/hardness.yaml", "./HARDNESS.md", "./harbor.lock"),
        ),
        Phase(
            "H.adjudication",
            "ENGRAM",
            "barrier",
            "### Phase H: research and reconcile the hardness contract",
            branches=("H",),
            reads=("./.memory/staging/touchstones/**",),
            depends_on=("H",),
        ),
        Phase(
            "N",
            "ENGRAM",
            "work",
            "### Phase N: propose the successor benchmark",
            branches=("N",),
            reads=("./requirements/**",),
            reconciles=("./brief/**", "./research/**", "./.memory/hardness.yaml", "./HARDNESS.md"),
            artifacts=("./brief/*/*-next/brief.md", "./.memory/hardness.yaml", "./HARDNESS.md"),
        ),
        Phase(
            "G.election",
            "ENGRAM",
            "barrier",
            "### Phase G: genesis for a new knowledge repository project",
            branches=("G",),
            reads=("./project.md",),
        ),
        # G is the pre-approval scope (steps 1-5); later scaffold work stays gated.
        Phase(
            "G",
            "ENGRAM",
            "work",
            "### Phase G: genesis for a new knowledge repository project",
            branches=("G",),
            reads=("./project.md",),
            reconciles=("./.memory/genesis.yaml",),
            artifacts=("./.memory/genesis.yaml",),
            depends_on=("G.election",),
        ),
        Phase(
            "G.0.5",
            "ENGRAM",
            "gate",
            "### Phase G: genesis for a new knowledge repository project",
            branches=("G",),
            reads=("./.memory/genesis.yaml",),
            approval_file="./.memory/genesis.approval",
            approval_binds="./.memory/genesis.yaml",
            depends_on=("G",),
        ),
        Phase(
            "G.scaffold",
            "ENGRAM",
            "work",
            "### Phase G: genesis for a new knowledge repository project",
            branches=("G",),
            reads=(
                "./.memory/genesis.yaml",
                "./.memory/genesis.approval",
                "./requirements/**",
                "./touchstones/**",
                "./.trinity-install/protection/**",
            ),
            reconciles=(
                "./.memory/capabilities.yaml",
                "./.memory/TODO.md",
                "./.memory/hardness.yaml",
                "./HARDNESS.md",
                "./research/**",
                "./.memory/implementations/**",
                "./INDEX.md",
                "./CHARTER.md",
                "./ARCHITECTURE.md",
                "./PIPELINE.md",
                "./TAXONOMY.md",
                "./GLOSSARY.md",
                "./RESEARCH.md",
                "./GROUNDING.md",
                "./ASSURANCE.md",
                "./OPERATIONS.md",
                "./README.md",
                "./CODE_OF_CONDUCT.md",
                "./CONTRIBUTING.md",
                "./LICENSE",
                "./SECURITY.md",
                "./.github/CODEOWNERS",
                "./.gitignore",
                "./images/hero.svg",
                "./paper/**",
                "./pitch/**",
                "./media/**",
                "./patent/**",
                "./study/**",
                "./playbooks/**",
            ),
            artifacts=(
                "./.memory/capabilities.yaml",
                "./.memory/TODO.md",
                "./.memory/hardness.yaml",
                "./HARDNESS.md",
                "./INDEX.md",
                "./CHARTER.md",
                "./ARCHITECTURE.md",
                "./PIPELINE.md",
                "./TAXONOMY.md",
                "./GLOSSARY.md",
                "./RESEARCH.md",
                "./GROUNDING.md",
                "./ASSURANCE.md",
                "./OPERATIONS.md",
                "./README.md",
                "./CODE_OF_CONDUCT.md",
                "./CONTRIBUTING.md",
                "./LICENSE",
                "./SECURITY.md",
                "./.github/CODEOWNERS",
                "./.gitignore",
                "./images/hero.svg",
            ),
            depends_on=("G.0.5",),
        ),
    ),
    "FORGE": (
        Phase(
            "place_reconcile",
            "FORGE",
            "always",
            "### Resume preflight: rebuild phase state from disk",
            reconciles=("./staging/**", "./samples/**", "./delivery/**", "./EDICT.md"),
        ),
        Phase(
            "R",
            "FORGE",
            "work",
            "### Phase R: research on invocation",
            reads=("./research/**",),
            reconciles=("./.seed/research/**", "./.seed/implementations/**"),
            depends_on=("place_reconcile",),
        ),
        Phase(
            "0",
            "FORGE",
            "work",
            "### Phase 0: scope the scenario and harness, read-only except candidate contract",
            reads=(
                "./requirements/**",
                "./brief/**",
                "./touchstones/**",
                "./samples/**",
                "./delivery/**",
                "./DEFERRED.md",
            ),
            reconciles=(
                "./.seed/contract.yaml",
                "./.seed/capabilities.yaml",
                "./.seed/batch.yaml",
                "./.seed/pilot.yaml",
                "./.seed/lineage.yaml",
            ),
            artifacts=("./.seed/contract.yaml", "./.seed/capabilities.yaml", "./.seed/batch.yaml"),
            depends_on=("R",),
        ),
        Phase(
            "0.5",
            "FORGE",
            "gate",
            "### Phase 0.5: design sign-off gate",
            reads=("./.seed/contract.yaml", "./.seed/capabilities.yaml"),
            approval_file="./.seed/contract.approved",
            approval_binds="./.seed/contract.yaml",
            depends_on=("0",),
        ),
        Phase(
            "1",
            "FORGE",
            "work",
            "### Phase 1: construct or reconcile the task bundle",
            reads=(
                "./.seed/contract.approved",
                "./harbor.lock",
                "./requirements/**",
                "./touchstones/**",
                "./.memory/forge_view.yaml",
            ),
            reconciles=(
                "./.seed/contract.yaml",
                "./.seed/hardness.md",
                "./.seed/pilot.yaml",
                "./.seed/feasibility.yaml",
                "./.seed/budget.yaml",
                "./.seed/TODO.md",
                "./harness/**",
                "./staging/**",
            ),
            artifacts=(
                "./.seed/hardness.md",
                "./.seed/pilot.yaml",
                "./.seed/feasibility.yaml",
                "./harness/README.md",
                "./staging/**",
            ),
            depends_on=("0.5",),
        ),
        Phase(
            "2",
            "FORGE",
            "always",
            "### Phase 2: prove local design validity, report-only",
            reads=(
                "./.seed/contract.yaml",
                "./.seed/capabilities.yaml",
                "./.seed/hardness.md",
                "./requirements/**",
                "./.memory/forge_view.yaml",
                "./staging/**",
            ),
            reconciles=(
                "./.seed/economics.yaml",
                "./.seed/lanes/**",
                "./.podium/queue/**",
                "./.seed/returns/**",
                "./.seed/TODO.md",
                "./.seed/evidence.yaml",
                "./EDICT.md",
                "./.seed/results/rubric.md",
            ),
            artifacts=("./.seed/evidence.yaml", "./.seed/TODO.md", "./EDICT.md"),
            depends_on=("1",),
        ),
        Phase(
            "3",
            "FORGE",
            "work",
            "### Phase 3: adversarial validity review",
            reads=("./requirements/**",),
            reconciles=(
                "./.seed/adversarial.yaml",
                "./.seed/probe.yaml",
                "./.seed/batch.yaml",
                "./.seed/defense.yaml",
                "./EDICT.md",
            ),
            artifacts=("./.seed/adversarial.yaml", "./.seed/probe.yaml", "./.seed/batch.yaml"),
            depends_on=("2",),
        ),
        Phase(
            "4",
            "FORGE",
            "barrier",
            "### Phase 4: external pilot evaluation, out-of-band only",
            reads=(
                "./.seed/pilot.yaml",
                "./harness/**",
                "./requirements/**",
                "./touchstones/**",
                "./.seed/proof.yaml",
            ),
            reconciles=("./.seed/harness-config.json", "./.seed/economics.yaml"),
            artifacts=("./.seed/proof.yaml", "./.seed/harness-config.json"),
            depends_on=("3",),
        ),
        # Step 1 binds a release set, not one file. Never substitute evidence.yaml
        # for that set: v1's single approval_binds cannot discharge this barrier.
        Phase(
            "4.5",
            "FORGE",
            "barrier",
            "### Phase 4.5: release evidence sign-off",
            reads=(
                "./.seed/release.approved",
                "./.seed/evidence.yaml",
                "./.seed/proof.yaml",
                "./.seed/capabilities.yaml",
            ),
            reconciles=("./staging/**", "./samples/**", "./delivery/**", "./EDICT.md"),
            artifacts=("./.seed/release.approved",),
            depends_on=("4",),
        ),
    ),
    "CRUCIBLE": (
        Phase(
            "R",
            "CRUCIBLE",
            "work",
            "### Phase R: research on invocation",
            reads=("./research/**",),
            reconciles=("./.audit/research/**", "./.audit/implementations/**"),
        ),
        Phase(
            "0",
            "CRUCIBLE",
            "work",
            "### Phase 0: identify and scope the project, read-only except scope file",
            reads=(
                "./requirements/**",
                "./brief/**",
                "./touchstones/**",
                "./samples/**",
                "./delivery/**",
                "./DEFERRED.md",
            ),
            reconciles=("./.audit/scope.yaml", "./.audit/capabilities.yaml"),
            artifacts=("./.audit/scope.yaml", "./.audit/capabilities.yaml"),
            depends_on=("R",),
        ),
        Phase(
            "0.5",
            "CRUCIBLE",
            "gate",
            "### Phase 0.5: scope sign-off gate",
            reads=("./.audit/scope.yaml", "./.audit/capabilities.yaml"),
            approval_file="./.audit/scope.approved",
            approval_binds="./.audit/scope.yaml",
            depends_on=("0",),
        ),
        Phase(
            "1",
            "CRUCIBLE",
            "work",
            "### Phase 1: scaffold or reconcile the audit gate",
            reads=(
                "./.audit/scope.yaml",
                "./.audit/scope.approved",
                "./staging/**",
                "./samples/**",
                "./delivery/**",
                "./.audit/attestations/execution/**",
            ),
            reconciles=(
                "./.audit/evidence.yaml",
                "./.audit/budget.yaml",
                "./.audit/fidelity.yaml",
                "./.audit/crucible.py",
                "./.audit/adversary/**",
                "./.audit/fixtures/**",
            ),
            artifacts=("./.audit/evidence.yaml", "./.audit/crucible.py"),
            depends_on=("0.5",),
        ),
        Phase(
            "2",
            "CRUCIBLE",
            "always",
            "### Phase 2: self-verify the scaffold and review findings",
            reads=("./.audit/scope.approved", "./.audit/capabilities.yaml"),
            reconciles=(
                "./.audit/evidence.yaml",
                "./.audit/review.md",
                "./.audit/findings.yaml",
                "./.audit/TODO.md",
                "./VERDICT.md",
            ),
            artifacts=(
                "./.audit/evidence.yaml",
                "./.audit/review.md",
                "./.audit/findings.yaml",
                "./.audit/TODO.md",
                "./VERDICT.md",
            ),
            depends_on=("1",),
        ),
    ),
}


class PhaseError(ValueError):
    """A phase lookup refusal with a public code, never an empty fallback."""

    code: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


def _rows(instrument: str) -> tuple[Phase, ...]:
    try:
        return TABLE[instrument]
    except KeyError as error:
        raise PhaseError("invalid-instrument", f"{instrument} owns no phase table") from error


def phases(instrument: str, branch: str = "default") -> tuple[Phase, ...]:
    """Select a branch without expanding dependencies into independently invoked work."""
    rows = _rows(instrument)
    if branch not in BRANCHES:
        raise PhaseError("invalid-branch", f"{branch} is outside the branch vocabulary")
    return tuple(row for row in rows if branch in row.branches)


def phase(instrument: str, phase_id: str) -> Phase:
    for row in _rows(instrument):
        if row.id == phase_id:
            return row
    raise PhaseError("PROGRESS_PHASE_UNKNOWN", f"{instrument} has no phase {phase_id}")


def never_skip(instrument: str) -> tuple[str, ...]:
    """Return invocation checks across every branch, not cached work standing."""
    return tuple(row.id for row in _rows(instrument) if row.kind == "always")


def table_digest() -> str:
    """Bind every row field using ADR 0003 canonical JSON arrays for tuple fields."""
    return attest_canonical.canonical_sha256(
        {
            instrument: [
                {
                    "id": row.id,
                    "instrument": row.instrument,
                    "kind": row.kind,
                    "contract_heading": row.contract_heading,
                    "branches": list(row.branches),
                    "reads": list(row.reads),
                    "reconciles": list(row.reconciles),
                    "artifacts": list(row.artifacts),
                    "approval_file": row.approval_file,
                    "approval_binds": row.approval_binds,
                    "depends_on": list(row.depends_on),
                }
                for row in rows
            ]
            for instrument, rows in TABLE.items()
        }
    )
