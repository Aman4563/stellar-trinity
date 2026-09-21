# Trinity: an open contract suite for building evaluation tasks that current frontier models cannot solve

FOR IMMEDIATE RELEASE

Trinity is a suite of executable prompt contracts for producing adversarial reinforcement-learning environment families. It is released under the MIT License. The suite is not itself an evaluation benchmark and not an RL environment; it is the meta-tooling that decides what such environments must contain to stay hard, and the record-keeping discipline that decides when they have gone soft.

## The problem it addresses

Benchmark difficulty is normally asserted at authoring time and then treated as a fixed property of the artifact. It is not one. Difficulty is a relation between a task, a named population of solvers, and a moment in time. A task that defeats every solver today may be trivial against the solvers of next year with its bytes unchanged, and a task whose material has leaked into a training corpus measures recall rather than capability. Authored difficulty labels are predictions dressed as properties, and a benchmark card cannot certify a prediction about systems nobody has named.

Trinity's answer is a single operating rule: difficulty is measured, never claimed. An authored probability counts for nothing. A local pass counts for nothing. Only an external signed pilot, run over frozen task bytes against a frozen solver registry under the task's declared time budget, produces difficulty evidence, and that evidence carries a dated expiry because the solver frontier moves underneath it.

## Three instruments, disjoint ownership, one bridge

Trinity assigns authoring, audit, and memory to three peer instruments with disjoint ownership, as README.md's The three instruments section specifies. Contract separation does not establish externally independent governance or prove that every obligation has an executing check.

**ENGRAM** is the memory instrument. It remembers measured failure evidence across tasks, expires stale or frontier-caught techniques, reports the current front line, and scaffolds new knowledge repositories at genesis. It owns the `.memory/` harness, the append-only ledger of measured hardness, the hardness catalog, the publication surfaces `paper/`, `pitch/`, `media/`, `patent/`, and `study/`, and the root report `DIRECTIVE.md`. The case study under `study/` is a decision-forcing narrative grounded in measured evidence and in a recorded closed-ended human interview, and a fact resting on neither is a defect rather than colour.

**FORGE** is the authoring instrument. FORGE.md's Batch cadence rule fixes exactly one batch of `batch_size` ordinary task slots, fixed at thirty and equal to `sample_ceiling`, plus at most one anchor slot. These are contract constants, not measured results. It works the slots as parallel lanes and targets Frontier-defeat unless a human grant explicitly permits a lower target. It owns `.seed/`, authors and seals Harbor bundles under `staging/`, and places clean bundles under `samples/` or `delivery/` after audit. Anchors occupy the samples quota until ENGRAM records their duration as folded and they graduate into delivery. FORGE contributes its run report to the rendered `EDICT.md`. Anchor timing informs budget mapping, while task economics comes from human-granted rates and never proves hardness. Local verification without an external signed pilot caps at `HOLD:PILOT_REQUIRED`; a pilot supplies necessary difficulty evidence, not sufficient release authority. The local gate qualifies at most `SHIP_ELIGIBLE`; only the separate governance publisher can authorize terminal `SHIP` after the release checks pass.

**CRUCIBLE** is the independent auditor. Its gate is critical recall over what the author claimed: it does not prove correctness and it does not prove difficulty. It owns the `.audit/` harness and emits the root report `VERDICT.md`, and it never sees the hardness catalog, because an auditor holding the author's playbook grades intent instead of bytes.

FORGE and CRUCIBLE never speak to each other. A direct channel would let the author tune tasks toward whatever the auditor accepts, which is reward hacking by construction. ENGRAM is the sole bridge, and it exposes memory only through two computed projections, `FORGE_VIEW` and `CRUCIBLE_VIEW`, each a pure function of a recorded input closure that strips named forbidden fields. Auditor pass criteria never reach the author, and authored difficulty claims never reach the auditor.

## An adversarial gatekeeper outside the three

Every instrument halts at named human sign-off gates. Where the project authorizes it, GAUNTLET acts as an out-of-band approver and owns `.trial/`. It rejects by default, discharges an eligible gate only after a recorded attack run fails to break the bound artifact, and never edits that artifact. GAUNTLET.md's Judgment is a unanimous council rule requires three or more models of mutually distinct lineages; its Model-lineage diversity rule also excludes the producing model's lineage. Any dissent means rejection, and insufficient qualifying lineages require human sign-off. Rejection opens a bounded argument through signed feedback and rebuttal or revision. Its authority remains revocable. Publication beyond the repository, patent filing, operational acceptance, and admission into `touchstones/` remain human acts under its permanently human rule.

## A conductor outside the three

MAESTRO is a work order outside the three instruments, not an additional instrument. It conducts isolated ENGRAM, FORGE, and CRUCIBLE movements in that order toward thirty resident sample bundles, the structural `sample_ceiling` in MAESTRO.md's programme quota rule, with anchors counted inside it until graduation. It owns `.podium/` and `SCORE.md`, reads only the instrument root reports, its own harness, and the samples residency count, and never writes into an instrument harness. It consolidates pending human gates without discharging them. A gate holds the movements that depend on it: an ENGRAM gate holds both peers, while a FORGE gate does not hold CRUCIBLE. A new cycle waits for every closing-cycle gate and lane to finish; quota, steady state, pending gates, a terminal disposition, or a block can stop conduct.

## Everything fails closed

A missing instrument, an unverified trust root, an unrun control, or an uncomputable check caps the disposition rather than passing quietly. The contracts' Trinity freshness gate requires a clean `trinity/` checkout at the fetched upstream `main` tip; a behind, diverged, locally modified, or unverifiable checkout blocks phase work, including offline uncertainty. A coverage gap is a finding, never a silence. A proof without external signature verification births no evidence record. A stale record does not keep a technique active, and an unmeasured technique is not active. Instruments compare tracked input digests and reconcile changes; a changed binding input requires renewed sign-off.

FORGE.md's contract sign-off clause requires a SHA-256 digest over bound bytes; a typed name alone proves no approval. Signing is software-only. Sabotage checks refuse unbound or forged dispositions, inert instruments, forked `trinity/` remotes, typed sign-offs, and governance edits committed beside their subjects. The contracts' historical sabotage doctrine also forbids rewriting or force-pushing history to bury a finding and requires append-only signed remediation authorized by a distinct principal group. That doctrine does not imply that every remedy has an executing check. A finding is suspicion, never proof of intent.

## The delivery-integrity layer

The operator and the candidate workspace are untrusted. Local SHIP prose or a trust root issued inside the candidate never authorizes release. The local gate produces qualification only, minting `BLOCK`, `HOLD`, or `SHIP_ELIGIBLE` as a signed machine-readable disposition rather than as report prose, and final release lives in a separate governance publisher whose expected identities, verifier commit, trust roots, and release policy are fixed outside the candidate tree. That publisher runs an independently pinned verifier over immutable candidate and export snapshots, and the verifier never runs the benchmark; it validates externally signed observations of it. Missing external trust, missing acceptance evidence, or a missing final instrument disposition fails closed, and no waiver promotes operational acceptance to a release. Components that are not deployed are named plainly as not claimed deployed: this repository does not claim that the application bridge, allowlists, observer runner, durable storage, repository rulesets, or operational monitoring have been stood up, and the external quality-controls runner remains absent, which is why several controls are still blockers in `DEFERRED.md`.

## Prompts, not programs

The product comprises the five work orders named in README.md's Prompts, not programs section: `ENGRAM.md`, `FORGE.md`, `CRUCIBLE.md`, `GAUNTLET.md`, and `MAESTRO.md`. A contract is a complete work order pasted into a coding agent; the contract is the program and the coding agent is the runtime. OpenCode is the preferred runtime. `gate.py install` installs command doors under `.opencode/commands/` and gate skills under `.agents/skills/` from `templates/doors/`; these doors defer to the contracts rather than restating them. The Python validates evidence and contracts rather than executing the benchmark. Operational release requires separately governed services.

README.md's Roster root definition fixes the five submodule roots: `trinity/`, `.memory/`, `samples/`, `delivery/`, and `harness/`, each with its own distinct remote, `branch = main`, and `update = merge`. They are not the dotted harness roster. Under ENGRAM.md's run rule and MAESTRO.md's Tracker abstention rule, `pipeline.py render-reports` renders `TRACKING.md` from run reports and frozen per-run tracker cards. Instruments contribute cards, never tracker bytes; MAESTRO contributes no card.

The repository publishes its own unfinished edges. `DEFERRED.md` is a register of every obligation the contracts state that nothing currently enforces, including the external signed pilot that holds FORGE's terminal disposition at `HOLD:PILOT_REQUIRED` by construction. A rule leaves that register only when something lands that evaluates it. The project's own position paper states plainly that separation of author, auditor, and record keeper inside a single party leaves Trinity's own evidence inadmissible under the standard Trinity enforces, until the auditor and record keeper roles are held externally.

## Availability

The contracts, the sanity harness, the shared research corpus, and the documentation spine are available in the Trinity repository at <https://github.com/Ethara-Ai/trinity> under the MIT License. Benchmarks, data collections, and task bundles produced through the contracts keep their own licences. No release date, roadmap commitment, or performance figure is asserted here; measured claims live in the repository's evidence surfaces and expire on their own terms.

## About Trinity

Trinity is the meta-tooling behind adversarial RL environment families: three instruments that author, audit, and remember the hardness of evaluation tasks, one gatekeeper that argues with all three, and one conductor that runs them in order without touching what they own. Its operating stance is adversarial throughout. A task that a current frontier model handles cleanly is a failure of the instrument, never a success.

Byline: Trinity, Ethara AI. Repository: <https://github.com/Ethara-Ai/trinity>. Licence: MIT.

*Forge the metal, test the metal, remember what the metal cost.*
