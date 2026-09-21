Filing: US Non-Provisional utility application (35 U.S.C. § 111(a)). Inventor: Sarvex Jatasra. Assignee: Ethara.AI. The proposed strategy combines isolated-slot authoring, adversarial verifier repair, taxonomy-gated submission, and controlled solution mutation in system claim 1, mirrored method claim 18, and mirrored storage-medium claim 20. Claims 2-17 and 19 preserve distinct fallbacks. No claim is deleted once numbered; a later revision preserves its number or identifies its successor. This description identifies an intended form, not an act of filing.

## Title

Primary: Isolated Batch Authoring of Evaluation Tasks with Adversarial Hardening, Shortcut Probes, Solution-Centric Mutation, and Discovery Asymmetry.

Alternative: Slot-Isolated Generation and Gated Adversarial Repair of Executable Evaluation Tasks.

## Abstract (proposed)

A computing system authors executable evaluation tasks in isolated parallel slots with independent dispositions. An attacking process attempts verifier acceptance without instruction satisfaction, a repair process modifies the verifier, and a solving process confirms legitimate acceptance. Advancement requires attack rejection and legitimate acceptance. Versioned shortcut-class probes prevent submission when a shortcut succeeds. Solution-centric mutation derives child instructions and verifiers from an executable solution and admits a child only upon executability, comparative hardness, and declared diversity. Parent and child share a fresh comparison seed block that subsequent comparisons cannot reuse. Further controls require environment-dependent discovery weight, digest-derived canaries, private-answer containment, and byte-identical ground-truth regeneration across hosts. Signed anchor durations inform design without evidencing difficulty. Grant-bound accounting remains outside difficulty decisions. Seal-bound design returns reconcile targets, budget predictions, and headroom without becoming measurement evidence.

## Apex pillars in independent claims

1. Claims 1, 18, and 20 allocate artifact-complete parallel slots, prevent cross-slot reads and artifact substitution, and resolve dispositions independently.

2. The same claims make verifier repair conditional on rejection of the attack and continued acceptance of a legitimate solution under the modified verifier.

3. The same claims execute probes against a versioned, predeclared shortcut taxonomy and prevent submission upon shortcut acceptance.

4. The same claims require executable, comparatively harder, diverse children from solution-centric mutation, with fresh comparison blocks shared within a parent-child comparison and never reused across comparisons.

Deliberately excluded from apex: particular batch and anchor counts, named process roles, the individual shortcut classes, a particular statistical estimator, the mutation cap and margin, confirmation and lineage tags, discovery-weight accounting, canary derivation, private-boundary containment, dual-host regeneration, duration learning, budget orthogonality, task economics, and the design-return fold. These remain dependent or specification support rather than alternative assertions of an abstract invention.

Named surfaces must be described only generically in claims. In one implementation, the vocabulary includes FORGE, ENGRAM, CRUCIBLE, Hacker, Fixer, Solver, `task.toml`, `instruction.md`, `solution/solve.sh`, `.seed/contract.yaml`, `.seed/probe.yaml`, `.seed/lineage.yaml`, `.seed/returns/`, `.memory/anchor_standing.yaml`, `tools/pipeline.py`, `tools/lanes.py`, `tools/pilot.py`, `tools/probe.py`, `tools/stats.py`, and `tools/bundle_identity.py`.

In one implementation, additional illustrative vocabulary includes `mutation_cap`, `mutation_margin`, `discovery_floor`, `anchor_ceiling`, `rate_card`, `pricing_policy`, `duration_outcome`, `cost_outcome`, `trinity.pilot-policy/v2`, `trinity.pilot-attempt/v2`, `seed`, `evolved`, `saturated`, `ANCHORED`, `RETURN_MISSING`, and `BLOCK:INVALID_TASK`. Counts such as thirty ordinary slots, an optional anchor, and the bounded starter roster illustrate contracts; neither these numerals nor these strings are claim limitations.

## Claims

**1. A system for controlling authoring of executable evaluation tasks, comprising:** one or more processors; one or more non-transitory memories storing instructions that configure the processors to allocate a batch of parallel task slots, each with a respective manifest, instruction representation, execution environment, verifier, and executable reference solution; prevent a slot from reading another slot's bundle bytes and prevent an artifact of a slot from satisfying another slot's verifier; resolve respective slot dispositions independently such that a blocking disposition of a slot does not cap a sibling slot; for a candidate task in a slot, execute an attacking process that attempts verifier acceptance without instruction satisfaction, a repair process that modifies the verifier in response, and a solving process that executes a legitimate solution against the modified verifier, preventing advancement unless the attempt is rejected and the legitimate solution remains accepted; execute probes corresponding to predeclared classes of a versioned shortcut taxonomy and prevent submission while a probe obtains verifier acceptance through a shortcut; and generate a child task by mutating an executable reference solution and deriving child instructions and verifier bytes from the mutated solution, accepting the child into a lineage only upon executability, an empirically harder comparison outcome against its parent under a common solver population, and diversity under a predeclared measure, wherein each comparison uses an identical seed block for parent and child that no earlier comparison in the lineage consumes, and reuse of a spent block prevents child acceptance.

*Drafting note (1):* Application sections 8.3-8.6 support the combination. Preserve independent slot dispositions and both repaired-verifier outcomes. The Hacker-Fixer paper already describes the process sequence; do not rest novelty on role labels. Fresh block allocation concerns distinct comparisons, while matched seeds within a comparison are intentional. Runtime isolation and lineage-wide seed tracking are not established by the existing queue and pilot parsers.

**2.** The system of claim 1, wherein the batch comprises ordinary task slots and a separately designated anchor slot excluded from an ordinary-slot floor, and the processors refuse an anchor-slot allocation exceeding a bound per-invocation allowance.

*Drafting note (2):* Section 8.3 supports an anchor outside the ordinary floor. Claim the bounded allocation rather than the current implementation count. The outstanding-seal limit does not prove ordinary-slot or anchor cardinality.

**3.** The system of claim 1, wherein the shortcut classes comprise lexical overlap, subsequence leakage, negation or polarity handling, positional artifact, and style cue, and the processors execute class-specific probes against each graded outcome under a bound taxonomy version.

*Drafting note (3):* Section 8.5 enumerates the classes without imposing a numerical claim limit. The application roster must not be attributed to Shortcut Suite's different roster. Preserve executed probes rather than merely storing category names.

**4.** The system of claim 1, wherein the processors fix the child before probing rather than selecting among a pool of probed children, count every proposal against a lineage-wide cap that persists across changed task identifiers, and accept the comparison only when the child's maximum solver success rate is at or below the parent's maximum solver success rate less a predeclared margin under a common frozen configuration.

*Drafting note (4):* Section 8.6 supplies the fixed-child restriction, lineage-wide proposal accounting, common configuration, and margin. All attempted children count, not just accepted descendants. A new task digest cannot reset the cap.

**5.** The system of claim 4, wherein the processors retain attempted descendants with respective tags identifying an initial task, an accepted descendant, or a saturated branch, require a child-only confirmation on a further fresh seed block after an accepted child first clears an authoring ceiling, and terminate the branch upon failed confirmation, exhaustion of the cap, or reuse of a spent seed block.

*Drafting note (5):* Section 8.6 describes terminal saturation and fresh confirmation. The tags have functional meanings rather than required literal spellings. Termination concerns the lineage's design search and does not certify the retained parent.

**6.** The system of claim 1, wherein the processors bind an agent-visible statement closure and a discovery floor, verify that declared discovery values derive from a private grounding source and exist in the execution environment while remaining absent from the closure verbatim and under a bound paraphrase-containment rule, and prevent advancement unless a share of total graded weight dependent on those values reaches the discovery floor.

*Drafting note (6):* Section 8.7 defines the numerator and denominator and avoids double-counting an outcome with several discovery dependencies. Preserve both literal absence and the operational containment rule. Do not describe n-gram containment as a complete semantic-leak detector. The advisory localization probe does not implement this gate.

**7.** The system of claim 1, wherein the processors compute a content hash after replacing values in designated canary-token slots with fixed placeholders while retaining slot positions and surrounding bytes, derive tokens from the content hash, plant the tokens in the designated slots after hashing, and then apply a binding that associates the content hash and a normalization-domain version with an author contract.

*Drafting note (7):* Section 8.8 and parent sections 8.9 and 8.22 support hash, derive, plant, bind. Preserve ordering to avoid circular identity. Current raw bundle hashing is narrower and cannot be cited as implementation of normalization.

**8.** The system of claim 7, wherein the processors prevent a private extension tree containing oracle material from crossing an agent-facing delivery boundary, validate each designated slot against its derived token, scan assembled agent-visible bytes for the tokens, and refuse advancement when private-answer n-gram containment reaches a bound threshold under a bound normalization and n-gram width.

*Drafting note (8):* Section 8.8 distinguishes an agent-facing export from the complete archival task bundle. Private artifacts may remain inside that archival bundle without becoming agent-visible. Mount conventions alone cannot satisfy the claimed scan.

**9.** The system of claim 7, wherein the processors regenerate ground truth, the reference solution, checker fixtures, and derived verifier artifacts from a common private source on independent execution hosts having different host identities, compare final planted artifact bytes with each other and with committed bytes, and prevent advancement upon any inequality.

*Drafting note (9):* Section 8.9 and parent claim 17 supply the host comparison. Compare final planted bytes, not only normalized digests. The dependency on claim 7 gives antecedent support for planting and avoids assuming an unstated canary operation.

**10.** The system of claim 2, wherein human-authored requirements designate starter anchors within lower and upper cardinality bounds and across distinct composition axes, each starter is a designated anchor and each designated anchor is a starter, and the processors cause pilot execution of the anchors before ordinary tasks.

*Drafting note (10):* Section 8.10 supports bounded designation, spread, and ordering. The numerical examples belong only in the specification. Registration of a starter is not proof of a valid human designation or signed pilot.

**11.** The system of claim 10, wherein the processors fit an elapsed-duration mapping only from qualifying anchor rows bound to signed duration outcomes, project an upper endpoint of a fitted interval as a design ceiling, and prevent the mapping or design ceiling from creating difficulty evidence or raising a task disposition.

*Drafting note (11):* Section 8.10 confines learning to qualifying duration rows. Wider uncertainty makes the design ceiling more restrictive against a fixed budget. The current probability-bound arithmetic neither fits this interval nor establishes its signatures.

**12.** The system of claim 11, wherein the processors bind a completion bound and execution envelope from human-authored requirements independently of a difficulty tier, prevent derivation of the bound from the tier and derivation of the tier from the bound, and require duration evidence to carry the bound and envelope under which the duration arises.

*Drafting note (12):* Section 8.10 and parent claim 33 support bidirectional orthogonality and budget stamps. Keep both non-derivation directions; an ordinary timeout does not supply them. A ceiling used for composition never authorizes extra execution time.

**13.** The system of claim 1, wherein the processors resolve a rate card and pricing policy by name from a human-authored requirements corpus, meter authoring-lane consumption, compute an authoring-stage cost from that consumption under the granted rates, and compute a complete-stage cost and price only after resolving a separately signed pilot-consumption receipt.

*Drafting note (13):* Section 8.11 and parent section 8.34 support staged resolution. The authoring stage does not estimate an unavailable pilot total. Monetary policy alone is a weak eligibility basis; retain this as a dependent implementation, not the apex.

**14.** The system of claim 13, wherein the processors exclude cost and price from a difficulty computation, designate per-task cost, price, consumption, effort, and resolved-rate fields as forbidden in both an author projection and an auditor projection, and fold complete signed cost outcomes into a revisioned aggregate that stores no per-task row and projects no average pair below a bound fold count.

*Drafting note (14):* Section 8.11 permits only an aggregated design-guidance pair in the author view and no economics in the auditor view. Per-task fields remain forbidden in both. Do not claim anonymity from aggregation: successive revisions can disclose an individual value arithmetically.

**15.** The system of claim 1, wherein the processors require each sealed task to leave a design return bound to its sealed digest, cause a record-keeper process to fold the return against current hardness targets, an anchor-duration budget mapping, and composition headroom floors, and permit the fold to narrow guidance or open a gap but not create difficulty evidence or raise a disposition.

*Drafting note (15):* Section 8.12 states the closed return and fold. The relevant current source is FORGE Phase 2 item 7i.1 and ENGRAM Phase H item 14, not a claim that Phase 4.5 implements the reader. A return is a declaration with a seal binding, never an attested execution result.

**16.** The system of claim 2, wherein the processors maintain slot-specific routing independently of the ordinary-slot floor, seat ungraduated anchors within a structural sample-residency ceiling, route overflow by seal order to a separate delivery root without reducing the floor, and prevent a task identifier from residing under both roots.

*Drafting note (16):* Section 8.3 separates registration from physical reconciliation. The immutable registered lane can remain unchanged when lawful overflow or anchor graduation moves residency. Avoid the obsolete assertion that the author directly allocates a delivery lane or that placement itself counts capacity.

**17.** The system of claim 1, wherein the processors require each mandatory local verifier control to reject a targeted invalid submission and accept a legitimate submission under the same frozen bytes, and prevent advancement when the control demonstrates only rejection or only acceptance.

*Drafting note (17):* Sections 8.4 and 8.9 reflect FORGE invariant 17. An always-rejecting checker is inert, not proof of robust failure closure. The pair of outcomes must bind to the same artifact revision.

**18. A computer-implemented method for controlling authoring of executable evaluation tasks, comprising:** allocating, by processors, a batch of parallel task slots, each with a respective manifest, instruction representation, execution environment, verifier, and executable reference solution; preventing a slot from reading another slot's bundle bytes and preventing an artifact of a slot from satisfying another slot's verifier; resolving respective slot dispositions independently such that a blocking disposition of a slot does not cap a sibling slot; for a candidate task in a slot, executing an attacking process that attempts verifier acceptance without instruction satisfaction, a repair process that modifies the verifier in response, and a solving process that executes a legitimate solution against the modified verifier, and preventing advancement unless the attempt is rejected and the legitimate solution remains accepted; executing probes corresponding to predeclared classes of a versioned shortcut taxonomy and preventing submission while a probe obtains verifier acceptance through a shortcut; and generating a child task by mutating an executable reference solution and deriving child instructions and verifier bytes from the mutated solution, accepting the child into a lineage only upon executability, an empirically harder comparison outcome against its parent under a common solver population, and diversity under a predeclared measure, wherein each comparison uses an identical seed block for parent and child that no earlier comparison in the lineage consumes, and reuse of a spent block prevents child acceptance.

*Drafting note (18):* Mirror every apex operation of claim 1 rather than referring to that system claim. Sections 8.3-8.6 support the sequence; section 8.15 supplies single-operator operation. An empirical comparison is a local acceptance predicate, not a declaration of externally measured hardness.

**19.** The method of claim 18, further comprising restricting mutation inputs to a permitted author projection and the candidate task's private feasibility artifacts, refusing mutation upon absence of a required projected input or detection of non-projected auditor-derived input, and preventing author-side probe outcomes from substituting for external signed difficulty evidence.

*Drafting note (19):* Section 8.6 supports the input restriction. Keep auditor findings and trajectories out of mutation inputs even if renamed or summarized. The architecture does not permit a fresh seed block to launder prohibited source information.

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by processors, cause the processors to perform operations for controlling authoring of executable evaluation tasks, the operations comprising:** allocating a batch of parallel task slots, each with a respective manifest, instruction representation, execution environment, verifier, and executable reference solution; preventing a slot from reading another slot's bundle bytes and preventing an artifact of a slot from satisfying another slot's verifier; resolving respective slot dispositions independently such that a blocking disposition of a slot does not cap a sibling slot; for a candidate task in a slot, executing an attacking process that attempts verifier acceptance without instruction satisfaction, a repair process that modifies the verifier in response, and a solving process that executes a legitimate solution against the modified verifier, and preventing advancement unless the attempt is rejected and the legitimate solution remains accepted; executing probes corresponding to predeclared classes of a versioned shortcut taxonomy and preventing submission while a probe obtains verifier acceptance through a shortcut; and generating a child task by mutating an executable reference solution and deriving child instructions and verifier bytes from the mutated solution, accepting the child into a lineage only upon executability, an empirically harder comparison outcome against its parent under a common solver population, and diversity under a predeclared measure, wherein each comparison uses an identical seed block for parent and child that no earlier comparison in the lineage consumes, and reuse of a spent block prevents child acceptance.

*Drafting note (20):* The storage-medium claim mirrors claim 18 without relying on intended use alone. Its instructions configure denied reads and advancement transitions. Preserve the non-transitory limitation and avoid suggesting a signal or disembodied algorithm.

## §101 Alice positioning

Application section 8.14 contains the prevention register. For claims 1, 18, and 20, Step 2A Prong Two anchors are preventing cross-slot reads, preventing artifact substitution, preventing repaired-verifier advancement without paired outcomes, preventing submission on a shortcut, and refusing reused comparison blocks. Each verb controls access to or advancement of executable task bytes.

Claims 6-9 add closure scanning, ordered derivation, and final-byte comparison. Claims 11-14 exclude guidance and accounting from difficulty inputs. Claims 15 and 19 refuse unbound returns and prohibited mutation inputs. These are specific machine operations rather than instructions to exercise judgment more carefully.

Recentive Analytics v. Fox presents risk for generic model-training claims. Mutation and probe steps here operate as concrete pipeline gates rather than generic model training or an instruction to improve a benchmark. Step 2B analysis concerns their ordered coupling to isolated slots and denied transitions, not any assertion that language models, hashing, or statistics are themselves inventive.

The economic calculation is not an independent technical contribution merely because processors perform it. The defensible dependent position concerns structural exclusion from evidence inputs and stage-bound receipt processing. No eligibility conclusion follows from this drafting posture.

## EPO technical effect

For Art. 52 and Guidelines G-II 3.3 and 3.3.1, claims 1, 18, and 20 use models and mathematical comparisons for the specific technical purpose of controlling executable-verifier robustness. Attack rejection paired with legitimate acceptance addresses defective grading behavior rather than a subjective quality score.

Claims 4-5 constrain adaptive comparison reuse; claim 6 tests whether live environment interaction carries graded dependencies. Claims 7-9 make identity derivation acyclic and generation reproducible across execution hosts. These operations act on task bytes, solver inputs, and advancement records, not abstract question difficulty alone.

Claims 10-12 use elapsed-duration learning for composition planning without treating it as difficulty evidence. Claims 13-14 include nontechnical pricing rules, whose technical relevance is limited to the field exclusions and receipt-controlled data path. Intended effects remain testable propositions, not asserted measurements.

## India s.3(k) technical effect

Claim 1: under the Ferid Allani and Microsoft v. Assistant Controller framing, the technical problem is cross-slot interference and verifier exploitation. The technical solution configures artifact-complete isolated contexts and gates advancement on executable attack, repair, and legitimate-solution outcomes. A measurable technical benefit would be rejection of foreign-slot artifacts and exploits while preserving valid acceptance, measurable with paired fixtures; no novel hardware is required.

Claim 18: the technical problem is adaptive task evolution that reuses comparison inputs or advances an invalid verifier. The technical solution freezes executable candidates, applies matched fresh seed blocks, and refuses advancement on failed repair or shortcut predicates. A measurable technical benefit would be reproducible rejection of invalid transitions and reused comparisons, not an improved business metric; no novel hardware is required.

Claim 20: the technical problem is a processor workflow that otherwise admits unbound submissions and unreproducible task revisions. The technical solution stores instructions that enforce slot-specific reads, executable grading controls, and lineage acceptance conditions. A measurable technical benefit would be deterministic refusal of the specified counterexamples across runs; no novel hardware is required, and no benefit measurement or deployment is asserted.

## Obviousness posture

vs Hacker-Fixer Loops, arXiv 2606.08960, + BenchEvolver, arXiv 2606.01286: combination yields the disclosed attacker, fixer, legitimate solver, and solution-derived tasks but not necessarily closed slot isolation with independent dispositions, a versioned taxonomy submission gate, and lineage-wide fresh-block refusal. The process trio is expressly present in the paper, so it cannot stand alone as the distinction.

vs BenchEvolver + PROPEL, arXiv 2606.18284: combination yields adaptive task generation guided by execution or predicted solve rate but not the fixed-child comparison, preserved proposal cap, margin, fresh confirmation, and saturation termination of claims 4-5. Compare exact disclosures before assuming those constraints absent.

vs Shortcut Suite, arXiv 2410.13343, + FoRT-Searcher, arXiv 2606.12087: combination yields shortcut diagnosis and resistant synthesis but not necessarily the version-bound submission refusal over each graded outcome or the closure-bound discovery-weight floor of claims 3 and 6. Their respective taxonomies are not identical to this application's roster.

vs GRACE-DS, arXiv 2606.16000, + Adversarial Reward Auditing, arXiv 2602.01750: combination yields hidden evaluation structure and adversarial reward inspection but not necessarily independent slot transitions coupled to solution mutation with unreused blocks. These comparisons rest on the register, not a fresh full-text review in this lane.

vs SWE-bench Verified and DeepSWE fresh-container grading + the Scale Labs verifier-design publication dated 2026-09-04: combination yields clean execution and improved grading practice but not necessarily the complete slot-scoped acceptance conjunction. Claims 9 and 16 add final planted-byte equality and per-slot routing independent of batch size; publication details and exact disclosure require counsel verification.

vs BIG-bench canary GUID + Thinkst Canarytokens: combination yields planted leakage indicators but not necessarily normalized content identity followed by deterministic token derivation, planting, and binding while validating every designated slot. Claims 7-8 retain the containment control because marker presence alone misses reworded answers.

vs Nix RFC 0062 content-addressed derivations + SWE-bench Verified: combination yields content identity and reproducible environment concerns but not necessarily generation of the oracle, truth, fixtures, and verifier from a shared private source with final planted-byte equality as an advancement gate. Claim 9 is a narrowing fallback, not a claim to invent reproducible builds.

vs PROPEL + the register's Trillian Verifiable Log-Derived Map: combination yields generation guidance and derived state but not duration-only anchor learning or economics fields structurally excluded from hardness. Claims 11-15 keep estimates, commercial values, and author returns incapable of creating measured difficulty evidence.

The admitted Lost in Compaction rendering, arXiv 2608.11242, is retrieved this lane locally. It provides context for preserving solver-side constraints and configuration, not a novelty assertion for controlling compaction. The locally read Hacker-Fixer, FoRT-Searcher, and Shortcut Suite renderings likewise supplement the register without a network search.

Jia and Harman's mutation-testing survey and Kaplan and Cooper's activity-based costing are user-supplied comparison leads, verification pending. No locally retained matching source or register entry establishes their text here. Conventional mutation adequacy and activity costing are conceded concepts; obtain and verify those named works before relying on a limitation-level distinction.

The likely combination challenge is substantial. The proposed distinction is the conjunction of specific refusals across task identity, repair, probes, and mutation, not new labels for known techniques. Counsel should consider unity, double patenting, written description, and the parent's actual prosecution posture before selecting a continuation or divisional route.

## Design-around foreclosures

1. Renaming directories does not remove a slot boundary because the claims identify resources and prohibited reads, not filesystem spellings.

2. Keeping a batch-wide report does not satisfy independent disposition unless one slot's block leaves a sibling's disposition uncapped.

3. Repair that rejects every submission fails the legitimate-acceptance condition; a successful attack cannot become harmless through a verifier that stops working.

4. Storing a shortcut taxonomy without executing its probes does not satisfy the submission gate, and changing its version requires reevaluation of bound work.

5. Giving each mutation a new identity does not reset the lineage cap, and keeping only accepted children does not satisfy attempted-descendant retention.

6. Parent-child seed matching is required within comparison; recycling that block in a later comparison is forbidden even when task bytes change.

7. Normalized hashes alone do not satisfy final-byte regeneration, and hiding private files by mount convention alone does not satisfy the assembled-closure scan.

8. A large environment cannot satisfy discovery asymmetry when the graded values remain in the initial statement closure by literal or bound containment matching.

9. A duration prediction cannot set a budget or evidence hardness; a cost figure cannot enter hardness through either an explicit per-task field or a renamed forbidden field.

10. A queue record is not a design return, and a design return cannot replace a signed measurement merely because its bundle digest matches.

## ENFORCED and PROSPECTIVE map

Evidence labels apply only to the named component. All named tools and tests below exist in the inspected tree; dates identify first file additions, not implementation dates for every later feature. The whole combined runtime remains proposed.

| Mechanism | Claims | Evidence class | Evidence (tools/tests or contract line or DEFERRED row) |
| --- | --- | --- | --- |
| Slot registration and single staged home | 1, 2, 16, 18, 20 | ENFORCED | tools/lanes.py, first landed 2026-09-17; tests/test_lanes.py |
| Digest-bound seal, verdict, placement, overflow, anchor movement | 1, 16, 18, 20 | ENFORCED | tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py |
| Runtime cross-slot reads and verifier non-substitution | 1, 18, 20 | CONTRACT-ONLY and PROSPECTIVE | FORGE.md:16, 194, 266; application section 8.3 runtime embodiment |
| Ordinary and anchor counts | 2, 10 | DEFERRED | DEFERRED.md: "Batch cardinality and the one-anchor rule"; "Starter anchor cardinality and identity" |
| Attack, repair, legitimate solve and paired control outcomes | 1, 17, 18, 20 | CONTRACT-ONLY | FORGE.md:270-273, 399 |
| Taxonomy-based submission refusal | 1, 3, 18, 20 | CONTRACT-ONLY | FORGE.md:288; parent section 8.21 |
| Pilot group and rollout non-reuse, closed schemas, attempt budget | Adjacent to 1, 4, 18, 20 | ENFORCED | tools/pilot.py, first landed 2026-09-03; tests/test_pilot.py |
| Fresh lineage seed blocks, cap, margin, diversity, saturation | 1, 4, 5, 18, 20 | CONTRACT-ONLY and DEFERRED | FORGE.md:289; DEFERRED.md: "Mutation ratchet bounded by `mutation_cap`, fresh seed blocks, and `mutation_margin`" |
| Advisory localization probe | Adjacent to 6 | ENFORCED | tools/probe.py, first landed 2026-09-03; tests/test_probe.py; never difficulty evidence |
| Discovery-weight and paraphrase proof | 6 | CONTRACT-ONLY and DEFERRED | FORGE.md:206, 240; DEFERRED.md: "Discovery asymmetry proved over frozen bytes" |
| Safe raw bundle identity and trajectory exclusion | Adjacent to 7, 9 | ENFORCED | tools/bundle_identity.py, first landed 2026-09-16; tests/test_bundle_identity.py |
| Normalized hash, derive, plant, bind and containment | 7, 8 | CONTRACT-ONLY | FORGE.md:185, 217-221, 260; parent sections 8.9 and 8.22 |
| Common-source dual-host final-byte regeneration | 9 | CONTRACT-ONLY | FORGE.md:204, 238, 250; parent section 8.25 and claim 17 |
| Pilot statistical arithmetic | Adjacent to 11, 12 | ENFORCED | tools/stats.py, first landed 2026-09-02; tests/test_stats.py |
| Duration-only anchor fit and budget orthogonality | 10-12 | CONTRACT-ONLY and DEFERRED | FORGE.md:242, 303, 417-418; ENGRAM.md:246-247; DEFERRED.md: "Fitted time-anchor mapping" |
| Granted rates, consumption receipt, aggregate and forbidden fields | 13, 14 | CONTRACT-ONLY and DEFERRED | FORGE.md:244, 304, 419; ENGRAM.md:248; DEFERRED.md: "Pilot consumption receipt"; "Aggregate economics fold" |
| Design return and record-keeper fold | 15 | CONTRACT-ONLY and DEFERRED | FORGE.md:257; ENGRAM.md:257; DEFERRED.md: "Design returns and the return lane" |
| Mutation input barrier | 19 | CONTRACT-ONLY | FORGE.md:289, 399; parent section 8.21 |

The supplied source offsets predate the current compact FORGE file. Current rule 10 is line 16; construction starts at 180, local proofs at 227, hardening at 268, and hardness rules at 339. The draft cites these current positions instead of nonexistent legacy line ranges.

The requested pilot seed-bookkeeping label overstates current code. Its actual checks reject duplicate group and rollout identities and bind realized membership; they do not reserve mutation seeds across a lineage. Likewise, raw bundle identity is not canary normalization, and probability-bound arithmetic is not anchor-duration fitting. These distinctions are express disclosure limits, not claims that the requested mechanisms cannot be implemented.

## §112 / drafting cautions

Claims 1, 18, and 20 are single sentences by legal form. Their semicolon-separated operations remain on single Markdown lines. Keep the mirrored operations consistent and preserve every expressly recited dependency when revising a fallback.

Functional language such as "controller configured to" can raise Williamson v. Citrix and section 112(f) issues if it supplies no identifiable structure or algorithm. The draft instead recites processors, memories, executable artifacts, defined inputs, comparisons, and prevented transitions. A formal filing still needs counsel review of corresponding disclosure and claim construction.

"Empirically harder" means the disclosed comparison result under a common solver population, not an unqualified property of a task. Claim 4 narrows it to a maximum-rate margin. State the fixed configuration and outcome reduction when prosecuting that term, and do not turn local comparison into an externally certified outcome.

"Diversity" requires a predeclared measure with a defined representation and comparison set. The prospective solution-structure example illustrates an implementation but is not established parent support for every possible feature extractor. Counsel must assess enablement, breadth, and priority for any selected narrowing.

"Paraphrase" here has an operational bound through normalized n-gram containment. Do not promise complete semantic equivalence detection or zero contamination. A clean test proves only the bound method over its enumerated closure.

Freshness of seed blocks differs from uniqueness of rollout identifiers. Parent and child deliberately use matching seeds while producing distinct executions. A prospective lineage allocator requires serialized reservation to prevent concurrent reuse; current repository checks do not provide that allocator.

No raw private tree crosses the agent-facing export, but the complete task bundle can retain it for privileged verification. Claims must not accidentally prohibit the private oracle from reaching its authorized execution host.

Economic averages may disclose an individual contribution by differences between revisions. Claim 14 excludes named fields and per-task aggregate rows, not all possible inference. The cost receipt and anchor-duration evidence are separate carriers with separate authority.

The parent filing, related-application benefit, and divisional eligibility remain prospective. A genuine divisional requires the appropriate actual prosecution circumstances; no section 121 safe-harbor entitlement follows from the folder name. Human counsel decides the filing route and any new-matter treatment.

The drafting party reconciles and never files. No statement asserts filing, deployment, a benchmark result, or measured hardness. First-addition dates and existing tests ground narrow code attributions only, and nothing here converts a required contract operation into an executed result.
