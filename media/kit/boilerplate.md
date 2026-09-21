# Trinity media kit: boilerplate and style

Approved descriptions, naming rules, and key art references for anyone writing about Trinity. Copy these verbatim rather than paraphrasing. Every claim here traces to `ENGRAM.md`, `FORGE.md`, `CRUCIBLE.md`, `GAUNTLET.md`, `MAESTRO.md`, or `README.md`; when this file and a contract disagree, the contract wins. Byline for every piece of copy is Trinity, Ethara AI, the repository is <https://github.com/Ethara-Ai/trinity>, and the licence is MIT.

## Motto

Forge the metal, test the metal, remember what the metal cost.

## Short description

Trinity is an open, MIT-licensed suite of executable prompt contracts for producing adversarial RL environment families, built on one rule: difficulty is measured, never claimed.

## Medium description

Trinity is an open, MIT-licensed suite of executable prompt contracts for producing adversarial reinforcement-learning environment families. It is not itself an RL environment; it specifies what those environments must contain to stay hard. ENGRAM remembers measured failure evidence and expires stale techniques, FORGE authors and hardens task batches, and CRUCIBLE audits producer claims against artifacts. FORGE.md's Batch cadence rule fixes thirty ordinary slots plus at most one anchor per invocation, a contract constant rather than a result. Frontier-defeat is the authoring target unless a human grant permits a lower target. ENGRAM bridges author and auditor through the `FORGE_VIEW` and `CRUCIBLE_VIEW` projections, withholding forbidden fields. Only an external signed pilot supplies difficulty evidence; it carries an expiry. A pilot alone does not authorize release. The local gate qualifies at most `SHIP_ELIGIBLE`, while a separate governance publisher authorizes terminal `SHIP` after release verification.

## Long description

Trinity is an open, MIT-licensed suite of executable prompt contracts for producing adversarial reinforcement-learning environment families. The contract is the program and the coding agent is the runtime. OpenCode is the preferred runtime; `gate.py install` generates command doors under `.opencode/commands/` and gate skills under `.agents/skills/` from `templates/doors/`, as README.md's Front doors section specifies. Operational release requires separately governed verifier, trust, publisher, execution, and observer services. The shipped Python validates contracts and signed evidence; it never runs the benchmark. Difficulty relates a task to named solvers at a recorded time, and only an external signed pilot supplies difficulty evidence. Anchor timing informs budget mapping. Human-granted rates determine task economics, which never proves hardness.

The peer instruments own disjoint surfaces. ENGRAM owns `.memory/`, remembers measured evidence, expires stale techniques, scaffolds repositories, and maintains publication surfaces. FORGE owns `.seed/` and, under FORGE.md's Batch cadence rule, opens exactly one batch of `batch_size` ordinary task slots, fixed at thirty and equal to `sample_ceiling`, plus at most one anchor slot. It authors and seals Harbor bundles under `staging/`, then places clean bundles under `samples/` or `delivery/` after audit. CRUCIBLE owns `.audit/` and audits claims against artifacts without seeing the hardness catalog. Their root reports are `DIRECTIVE.md`, `EDICT.md`, and `VERDICT.md`. ENGRAM.md's run rule requires rendered root reports and a `TRACKING.md` rendered from run reports and frozen tracker cards, not instrument-authored tracker bytes. Contract separation inside the producer does not establish externally independent governance.

GAUNTLET and MAESTRO stand outside the instruments, as README.md's Prompts, not programs section specifies. Where authorized, GAUNTLET owns `.trial/` and attacks bound artifacts without editing them. Its Judgment is a unanimous council and Model-lineage diversity rules require three or more mutually distinct model lineages, each distinct from the producing model; disagreement means rejection, and insufficient qualifying seats require human sign-off. Its permanently human rule excludes publication, patent filing, operational acceptance, and touchstone admission. MAESTRO owns `.podium/` and `SCORE.md`. Its programme quota rule fixes thirty resident sample bundles, counting anchors until graduation. It conducts isolated ENGRAM, FORGE, and CRUCIBLE lanes in that order, reading only their root reports, its harness, and samples residency counts. It presents gates without signing them, holds dependent movements, and waits for every closing-cycle gate and lane before a new cycle. Its Tracker abstention rule forbids tracker cards and tracker edits.

The contracts fail closed: missing evidence or controls cap the disposition, and the Trinity freshness gate requires a clean checkout at the fetched upstream `main` tip. Behind, diverged, locally modified, and unverifiable checkouts block phase work. Human gates bind a SHA-256 digest under the contracts' Gate binding clause; a typed name alone is not approval. Software signatures bind machine-readable dispositions, and the separate governance publisher checks immutable snapshots through an independently pinned verifier. The verifier validates externally signed observations and never executes the benchmark. Sabotage checks refuse forged dispositions, inert instruments, and governance edits beside their subjects. Historical sabotage doctrine forbids rewriting history to bury a finding; a finding is suspicion, not proof of intent. Case facts trace to paper data, dated ledger evidence, or dated interview answers. `DEFERRED.md` names unenforced obligations rather than implying deployment.

## Naming and style rules

**The suite.** Written **Trinity** in ordinary prose, initial capital only. The all-caps form **TRINITY** is reserved for contract-internal use, where the suite is named as a peer of the wider **MATRIX** project alongside the prospective **NEO** gatekeeper trinity. Never write "the Trinity suite" as if Trinity were a vendor prefix; the project name stands alone. Never abbreviate it and never hyphenate it.

**The instruments.** **ENGRAM**, **FORGE**, and **CRUCIBLE** are always full capitals, never title case, never lowercase, never quoted. They are peers, so name them in that order when listing all three: ENGRAM, FORGE, CRUCIBLE. Describe them as instruments, not as agents, services, modules, or products. Each owns exactly one harness directory, and every harness is a hidden sibling at the parent project root: ENGRAM owns `.memory/`, FORGE owns `.seed/`, CRUCIBLE owns `.audit/`.

**The gatekeeper.** **GAUNTLET** is always full capitals and is never called a fourth instrument. It stands outside the trinity as an out-of-band adversarial gatekeeper, and its contract is transient by design. It owns `.trial/`.

**The conductor.** **MAESTRO** is always full capitals and is not an additional instrument. Its programme quota rule fixes thirty resident sample bundles under `samples/`, with anchors counted until graduation. It conducts ENGRAM, FORGE, and CRUCIBLE in order, reads only their root reports, its `.podium/` harness, and samples residency counts, and consolidates gates in `SCORE.md` without signing them. Open gates hold dependent movements, not unrelated lanes. Never write that MAESTRO authors, audits, or remembers anything.

**The contracts.** Refer to contract files by their exact filenames in code style: `ENGRAM.md`, `FORGE.md`, `CRUCIBLE.md`, `GAUNTLET.md`, `MAESTRO.md`. The root reports are `DIRECTIVE.md` for ENGRAM, `EDICT.md` for FORGE, `VERDICT.md` for CRUCIBLE, and `SCORE.md` for MAESTRO. Set every path, filename, disposition, and view name in code style: `samples/<uuid>/`, `FORGE_VIEW`, `CRUCIBLE_VIEW`, `SHIP`, `HOLD:PILOT_REQUIRED`, `BLOCK:INVALID_TASK`.

**Paths.** The harness directories are hidden siblings of the vendored `trinity/` submodule at the parent project root, so write `.memory/`, `.seed/`, `.audit/`, `.trial/`, and `.podium/` with the leading dot every time. The shared surfaces beside them carry no dot: `samples/`, `delivery/`, `requirements/`, `touchstones/`, `paper/`, `pitch/`, `media/`, `patent/`, and `study/`. A harness name written without its leading dot is wrong copy, so check each one before publishing.

**Vocabulary.** Use the closed vocabulary in README.md's Speak Trinity section and the contracts. A *contract* is the pasted work order; an *instrument* authors, audits, or remembers; a *harness* is its owned working directory. A *lever* hardens a task, a *tier* names a difficulty band, and a *pilot* supplies external signed difficulty evidence. A *task lane* routes a staged bundle into `samples/` or `delivery/` after a clean verdict, never bypassing `staging/`. An *anchor task* seeds budget mapping and later graduates from samples to delivery after ENGRAM folds its duration. *Task economics* derives cost and price from granted rates and never measures hardness. A *disposition* is a signed machine-readable outcome, not report prose. FORGE.md's contract sign-off clause requires a SHA-256 digest; a typed name alone is not approval. A *case study* forces a decision using grounded data, dated ledger evidence, and labelled human attestation. *Fails closed* means a missing piece stops the line.

**Claims discipline.** Say "difficulty is measured, never claimed" rather than claiming measured hardness without evidence. Quantitative media claims must trace to `paper/data/corpus.json`, or name the clause fixing a contract constant. FORGE.md's Batch cadence rule fixes thirty ordinary slots plus at most one anchor per invocation; MAESTRO.md's programme quota rule fixes thirty resident sample bundles, counting anchors until graduation. Neither constant is a result. Avoid unmeasured superlatives, availability dates, roadmap commitments, adoption claims, and endorsements. Preserve the paper header's byline and repository URL exactly; it carries no contact email, so invent none. Label undeployed components as not claimed deployed.

**Tone.** Understated, confident, technical. Declarative sentences. No emoji anywhere. No em-dashes; use a comma or a spaced hyphen. No hard line breaks inside a paragraph: every paragraph is one continuous line that the renderer soft-wraps.

## Licence line

Trinity is released under the MIT License. The contracts are tooling; any benchmarks, data collections, or task bundles produced through them keep their own licences.

## Key art

The project banner is `banner.jpg` at the repository root. README.md embeds the work-order portraits under `images/`: `engram.jpg`, `forge.jpg`, `crucible.jpg`, `gauntlet.jpg`, and `maestro.jpg`. Use each image unmodified at its native aspect ratio, without overlaid text, recolouring, or cropping that removes the mark.

ENGRAM's hero-art clause and Phase S media clause require a complexity floor: a mythic figure amid a layered scene of domain artifacts, painterly depth, directional light, and a restrained accent palette, with the project's work orders as attendants. Review assets against that requirement rather than treating this kit as certification. Flat typographic cards, bare geometric diagrams, and clip-art minimalism do not satisfy it.

README.md's Roster root definition names five submodule roots, distinct from the dotted harnesses: `trinity/`, `.memory/`, `samples/`, `delivery/`, and `harness/`. Each uses its own distinct remote with `branch = main` and `update = merge`.

This kit ships no binary assets of its own; reference each image at its repository path rather than copying it here. Where a project scaffolded by Trinity carries its own mascot hero art under `images/`, that art belongs to the parent project and is never substituted for Trinity's own.
