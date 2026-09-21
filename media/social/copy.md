# Trinity social copy

Platform-agnostic short-form copy. Every line is grounded in `ENGRAM.md`, `FORGE.md`, `CRUCIBLE.md`, `GAUNTLET.md`, `MAESTRO.md`, and `README.md`. No metrics, no dates, no endorsements, no emoji. Byline is Trinity, Ethara AI, and the repository link is <https://github.com/Ethara-Ai/trinity>. Adapt length to the surface you are posting on; do not add claims that are not here.

## Launch post

Trinity is open under the MIT License: executable prompt contracts for producing adversarial RL environment families, not a benchmark or an RL environment. Difficulty is measured, never claimed. Only an external signed pilot over frozen task bytes against frozen solvers supplies difficulty evidence, and that evidence expires. ENGRAM remembers, FORGE authors, and CRUCIBLE audits. FORGE.md's Batch cadence rule fixes thirty ordinary slots plus at most one anchor per invocation, a contract constant rather than a measured result. Frontier-defeat is the authoring target unless a human grant permits a lower target. ENGRAM bridges author and auditor through filtered projections. GAUNTLET gates eligible acts where authorized; MAESTRO conducts isolated lanes and presents human gates without signing them. The local gate qualifies at most `SHIP_ELIGIBLE`; a separate governance publisher authorizes terminal `SHIP` after release verification. Paste the contracts into a coding agent, or use the OpenCode command and skill doors that `gate.py install` generates. Operational release also requires separately governed services.

## Thread outline

**The premise.** We say "this benchmark is hard" the way we say "this rock is heavy," as though difficulty were stamped onto an artifact at creation time. It is not. Difficulty is a relation between a task, a named solver population, and a moment in time. Same bytes, different year, different answer. Trinity is built on that correction.

**The rule.** Difficulty is measured, never claimed. No authored probability, no self-solve, and no local green run produces a shippable difficulty statement. Only an external signed pilot, executed over frozen task bytes against a frozen solver registry under the task's declared time budget, counts. The result is dated and it perishes.

**ENGRAM, the memory.** ENGRAM owns `.memory/` and the append-only ledger of measured hardness. It remembers which techniques have gone soft, expires stale or frontier-caught evidence, publishes the current front line in `DIRECTIVE.md`, scaffolds a whole knowledge repository at genesis, and writes every publication surface including the case study under `study/`, which is grounded in a recorded closed-ended human interview. A stale record does not keep a technique active. An unmeasured technique was never active.

**FORGE, the author.** FORGE.md's Batch cadence rule fixes exactly one batch of `batch_size` ordinary task slots, fixed at thirty and equal to `sample_ceiling`, plus at most one anchor slot. It owns `.seed/`, works parallel lanes against Frontier-defeat unless a human grant permits a lower target, and authors Harbor bundles under `staging/`. Audit precedes placement under `samples/` or `delivery/`. Anchors inform budget mapping and occupy the samples quota until graduation. FORGE contributes its run report to rendered `EDICT.md`. Without an external signed pilot, local verification caps at `HOLD:PILOT_REQUIRED`. The pilot supplies necessary evidence, not sufficient authority for terminal `SHIP`.

**CRUCIBLE, the auditor.** CRUCIBLE owns `.audit/` and runs a critical-recall gate over producer claims and raw artifacts. It does not prove correctness and it does not prove difficulty; it looks for what the author missed, and reports in `VERDICT.md`. It never sees the hardness catalog, because an auditor holding the author's playbook grades intent instead of bytes.

**The firewall.** FORGE and CRUCIBLE share no direct feedback channel. ENGRAM supplies standing direction through `FORGE_VIEW` and `CRUCIBLE_VIEW`, the projections specified in the contracts' information-barrier rules. These strip forbidden fields from a recorded input closure. Auditor pass criteria never reach the author, and authored difficulty claims never reach the auditor. The sealed-bundle queue carries identities and digests, not findings or pass criteria.

**The gatekeeper.** Where authorized, GAUNTLET owns `.trial/` and attacks eligible gate artifacts without editing them. Its Judgment is a unanimous council and Model-lineage diversity rules require three or more mutually distinct model lineages, each distinct from the producing model. Dissent means rejection; insufficient qualifying seats require human sign-off. Publication, patent filing, operational acceptance, and touchstone admission remain human under its permanently human rule.

**The conductor.** MAESTRO conducts isolated ENGRAM, FORGE, and CRUCIBLE lanes in that order. Its programme quota rule fixes thirty resident sample bundles under `samples/`, counting anchors until graduation. It owns `.podium/` and `SCORE.md`, reads only instrument root reports, its harness, and samples residency counts, and never writes into instrument harnesses. Gates hold dependent movements; every closing-cycle gate and lane must finish before a new cycle. MAESTRO presents approvals without signing them and contributes no tracker card under its Tracker abstention rule.

**Gates and dispositions.** The contracts' Gate binding clause binds human approval to a SHA-256 digest; a typed name alone is not approval. The local gate mints `BLOCK`, `HOLD`, or `SHIP_ELIGIBLE`, never terminal `SHIP`. A separate governance publisher authorizes release through an independently pinned verifier of signed observations, not benchmark execution. Signing is software-only.

**Fail closed, everywhere.** Missing evidence or controls cap the disposition. The contracts' Trinity freshness gate requires a clean checkout at the fetched upstream `main` tip; behind, diverged, locally modified, and unverifiable checkouts block phase work. Sabotage checks refuse forged dispositions, inert instruments, and governance edits beside their subjects. Historical sabotage doctrine forbids force-pushing history to bury a finding. `DEFERRED.md` records obligations that lack executing checks, including the absent external quality-controls runner.

**How you run it.** Paste the contract into a coding agent, or use OpenCode doors generated by `gate.py install` under `.opencode/commands/` and `.agents/skills/`, as README.md's Front doors section specifies. A run stops at named human gates, including the commit gate, a terminal disposition, or a blocking gap. Re-pasting resumes rather than restarts. Agents never stage, commit, amend, or push.

README.md's Roster root definition names five submodule roots: `trinity/`, `.memory/`, `samples/`, `delivery/`, and `harness/`, each with its own distinct remote, `branch = main`, and `update = merge`. These differ from the dotted harness roots. ENGRAM.md's run rule assigns tracker rendering to `pipeline.py render-reports`, using frozen per-run cards and run reports rather than instrument-authored `TRACKING.md` bytes.

## One-liners

Difficulty is measured, never claimed.

A task a current frontier model handles cleanly is a failure of the instrument, never a success.

Authored difficulty labels are predictions dressed up as properties.

The author and the auditor never speak. That is not an oversight, it is the design.

Same bytes, next year, different difficulty. Evidence with no expiry date is not evidence.

An auditor holding the author's playbook grades intent instead of bytes.

A signed pilot of a contaminated benchmark yields a signed contaminated number. Attestation repairs accountability, not validity.

A coverage gap is a finding, never a silence.

The contract is the program. Your coding agent is the runtime. The installer supplies OpenCode doors; separate governance supplies release authority.

Reject by default: a gate stays shut until the attack run fails to break what it binds.

A conductor who whispers to a performer becomes exactly the channel the firewall forbids.

A gate is signed with a digest over the bytes it binds. A typed name proves nothing, so a typed sign-off is refused.

Force-pushing a finding out of the scan window is not a fix. It is the next finding.

Forge the metal, test the metal, remember what the metal cost.
