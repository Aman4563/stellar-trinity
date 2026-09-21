# UNITED STATES NON-PROVISIONAL UTILITY PATENT APPLICATION

**Filed under 35 U.S.C. § 111(a)**

**Title:** Isolated Batch Authoring of Evaluation Tasks with Adversarial Hardening, Shortcut Probes, Solution-Centric Mutation, and Discovery Asymmetry

**Inventor:** Sarvex Jatasra

**Applicant / Assignee:** Ethara.AI

**Docket Reference:** Trinity/author-hardening

---

## 1. TITLE OF THE INVENTION

Isolated Batch Authoring of Evaluation Tasks with Adversarial Hardening, Shortcut Probes, Solution-Centric Mutation, and Discovery Asymmetry

## 2. CROSS-REFERENCE TO RELATED APPLICATIONS

The related parent disclosure is titled "Cryptographically Controlled Certification of Machine-Learning Evaluation Tasks Using Isolated Generation, Audit, and Evidence Domains". Its filing is prospective. This application is intended as a divisional or continuation of that disclosure, with the choice left to the human filing decision and applicable support and procedural requirements.

No application number, priority date, restriction requirement, or benefit entitlement is asserted. The title-block filing legend identifies the proposed form only. This document remains a draft for human legal review.

The parent describes isolated slots in section 8.16, hardening and mutation in section 8.21, containment in section 8.22, and economics in section 8.34. Its claims 22, 23, 25, and 26 place related features in dependent form. This disclosure supplies a self-contained author-side combination without deleting or renumbering parent claims.

## 3. STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

## 4. FIELD OF THE INVENTION

The disclosure concerns computing pipelines that generate executable machine-learning evaluation tasks. It addresses process isolation, verifier repair, adversarial probe gates, reproducible generation, controlled mutation comparisons, and prevention of private-answer leakage into solver-visible inputs.

The technical object is an executable bundle and its advancement state. The disclosure does not claim the general goal of asking harder questions or training a more capable model.

## 5. BACKGROUND OF THE INVENTION

A first deficiency concerns cross-task interference. Parallel authors can reuse another task's oracle, checker output, or mutable environment. A batch-wide disposition can then hide a defective slot or prevent an unrelated valid slot from proceeding.

A second deficiency concerns verifier exploitation. A submission can earn reward without meeting the instruction. Repairing the verifier alone can create the opposite defect by rejecting legitimate solutions.

A third deficiency concerns incomplete shortcut review. An author can inspect examples informally without testing declared shortcut classes through the executable verifier. A clean narrative review does not show that a shortcut cannot obtain reward.

A fourth deficiency concerns selection during mutation. Selecting the least successful solver outcome from a pool of children confounds task changes with sampling variation. Reusing comparison seeds across adaptive proposals permits overfitting to a known evaluation block.

A fifth deficiency concerns statement leakage. Environment size does not establish that a solver needs the environment. Graded answers can remain available directly or by paraphrase in the initial statement.

A sixth deficiency concerns circular identity and hidden host dependencies. Hashing a token derived from that same hash creates a circular definition. Comparing only normalized bytes can also conceal different planted tokens or host-dependent final artifacts.

A seventh deficiency concerns conflation of design guidance and evidence. Elapsed duration, authoring cost, and requested price do not establish solver failure. A pipeline that admits these fields into difficulty decisions permits unsupported promotion.

Known techniques address parts of these problems. Section 8.13 identifies the closest named comparisons and the limited combination proposed here. It does not assert novelty for adversarial repair or solution-centric generation in isolation.

## 6. SUMMARY OF THE INVENTION

A computing system allocates isolated task slots and binds each slot to its own manifest, instruction, environment, tests, and executable reference solution. Each slot resolves its disposition independently, and another slot's artifact cannot satisfy its verifier.

Within a slot, an attacking process proposes a verifier exploit, a repair process modifies the verifier, and a solving process executes a legitimate solution against the modified verifier. Advancement requires rejection of the exploit and continued acceptance of the legitimate solution.

A versioned taxonomy supplies predeclared shortcut classes. The system executes class-specific probes and prevents submission while any probe obtains acceptance through a shortcut rather than the instructed work.

The system mutates an executable reference solution and derives child instructions and verifier bytes from it. Child acceptance requires executability, improved resistance against a common solver population, and diversity under a predeclared measure. A comparison uses a fresh seed block shared by parent and child and unavailable for reuse by later comparisons.

Dependent features add weighted discovery requirements, digest-derived canaries, private-boundary containment, independent-host regeneration, duration-only anchor learning, grant-bound economics, and design returns. Local authoring results never substitute for an external signed difficulty measurement.

## 7. BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 depicts an authoring coordinator, isolated task slots, per-slot artifact stores, and independent disposition records feeding a bounded-residency routing stage.

FIG. 2 depicts the attacking, repair, and legitimate-solving processes and the conjunctive advancement gate over the modified verifier.

FIG. 3 depicts a versioned shortcut taxonomy, class-specific probe executions, and a submission gate that refuses a successful shortcut.

FIG. 4 depicts a fixed-child mutation comparison, a lineage-wide proposal counter, fresh seed allocation, and terminal saturation standing.

FIG. 5 depicts the statement closure, environment-established discovery values, weighted grading dependencies, and verbatim and containment checks.

FIG. 6 depicts placeholder normalization, digest computation, token derivation, planting, binding, and independent-host final-byte comparison.

FIG. 7 depicts signed anchor-duration inputs and grant-bound economics as separate design-guidance paths, neither of which writes difficulty evidence.

FIG. 8 depicts a sealed task's design return and the record keeper's subsequent reconciliation of targets, budget mapping, and headroom.

## 8. DETAILED DESCRIPTION OF THE INVENTION

### 8.1 Overview

The system comprises processors, memories, an authoring coordinator, slot-specific execution contexts, a verifier execution interface, and a submission gate. A machine-learning model may propose task content, attacks, repairs, or solution mutations. Deterministic checks and recorded execution outcomes control advancement rather than a model's assertion of quality. PROSPECTIVE implementation of the complete combined system.

The disclosure distinguishes a required contract operation from an implemented repository check. An evidence label describes the cited component only, not operational deployment or the entire claimed combination. A test citation identifies repository test code and does not report a test execution in this drafting pass.

Source reconciliation date is 2026-09-21. The current FORGE contract has 434 lines, so several supplied legacy ranges exceed its length. References below use current phase and item names with current line numbers: batch rule 10 at line 16, construction at 180-225, proof at 227-266, hardening at 268-289, and hardness at 339-358.

The local corpus and prior-art register supply the comparisons. No network retrieval supports this draft. The repository contains no signed task-measurement ledger supporting a measured-hardness statement here.

### 8.2 Definitions

A task slot is a batch member with its own artifact namespace and execution context. A bundle comprises a manifest, instruction representation, executable environment representation, tests, and a private reference solution.

A disposition is the slot's machine-readable advancement state. A blocking state prevents that slot's advancement. A batch summary reports individual states without replacing them with an average.

A verifier is executable grading logic that maps submitted artifacts or resulting environment state to outcomes. A legitimate solution meets the instruction through the intended outcome checks. A shortcut produces verifier acceptance without that satisfaction.

A frozen artifact has a digest under a declared byte domain. An operation relying on the artifact recomputes its digest and refuses changed bytes. A comparison configuration fixes solver identities, execution settings, and outcome reduction before comparison outcomes are available.

A seed block is a recorded collection of group and attempt seeds for a comparison. Freshness means no earlier comparison in the same lineage consumes that block. Parent and child share the block within that comparison, not the execution state or outcome records.

A lineage comprises a seed task and its proposed descendants, including rejected proposals. A new content identity does not restart its proposal allowance. Saturation is a terminal design-search state, not proof of measured hardness.

A statement closure enumerates the exact initial bytes available to a solver before environment interaction. A discovery value is an environment-established value absent from that closure under the bound literal and containment tests.

An author projection and an auditor projection are distinct computed views of record-keeper state. A forbidden-field policy rejects or excludes named fields from a view. A design return is an author declaration of composition, never an execution attestation.

### 8.3 Isolated batch slots and independent dispositions

In one implementation, an invocation opens thirty ordinary parallel slots plus at most one anchor slot. The anchor does not count toward the ordinary-slot floor. An unbuilt designated anchor requires the extra slot; otherwise the invocation opens none. CONTRACT-ONLY (FORGE.md:16).

Each slot owns its manifest, instruction, environment, tests, oracle, and per-slot instruments. No slot reads, writes, or depends on another slot's bundle, checker, or evidence bytes. A slot's blocking disposition never caps a sibling's disposition. CONTRACT-ONLY (FORGE.md:16, 194, 266).

A prospective runtime realizes the rule with separate process identities and allowlisted mounts. It gives each verifier only its own task inputs and the submission bound to that slot. The dispatch interface refuses a submission binding that names a different slot before executing grading code. PROSPECTIVE realization of cross-slot non-satisfaction.

In one implementation, slot registration carries task identity, lane, slot position, batch identity, and run identity. The queue binds each seal to its bundle digest. Placement requires a clean verdict for the same identity and digest; copying a sibling's verdict cannot authorize placement of different bytes.

ENFORCED (tools/lanes.py, first landed 2026-09-17; tests/test_lanes.py) covers immutable slot-associated registration and staged-only residency checks. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py) covers digest-bound seals, verdicts, placement, and reconciliation, not execution sandbox confidentiality.

The batch floor concerns authoring work; the sample ceiling concerns physical residency. In one implementation, authors register starter or sample lanes, place clean bundles, and then reconcile overflow into delivery. Reconciliation seats ungraduated anchors first and ordinary bundles by seal order. Lane registration does not itself count capacity.

Thus a full batch need not shrink when the sample root is full. The structural ceiling remains thirty resident sample bundles, with anchors included, while overflow retains its own bundle identity and disposition in the delivery root. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py).

The queue's default outstanding-seal bound is thirty-one, which accommodates a full invocation but does not prove its composition. The ordinary-slot count and one-anchor rule remain DEFERRED (DEFERRED.md: "Batch cardinality and the one-anchor rule"). Global preflight or queue backpressure may pause work without converting one slot's defect into another slot's verdict.

### 8.4 Attacking, repair, and legitimate-solving sequence

In one implementation, the processes carry the labels Hacker, Fixer, and Solver. These names identify functions, not required model families. The attacker attempts verifier acceptance without instruction satisfaction; the fixer modifies verifier bytes in response; the solver executes a legitimate solution against those modified bytes. CONTRACT-ONLY (FORGE.md:270-273).

The advancement predicate is conjunctive. The repaired verifier must reject the attack and accept the legitimate solution. Rejecting both is not successful repair, and accepting both leaves the exploit undefeated. CONTRACT-ONLY (FORGE.md:270-273, 399; parent application section 8.21).

Each iteration binds attack input, verifier revision, and legitimate execution result to the task's current digest. A verifier change invalidates earlier approval and the dependent checks. The next iteration tests the new verifier rather than carrying a previous accepting result across changed bytes. CONTRACT-ONLY (FORGE.md:178, 271).

A surviving exploit blocks the slot. A successful repair merely removes that local defect and never establishes difficulty. The attack log and defense pool remain author-private and cannot import auditor findings. CONTRACT-ONLY (FORGE.md:272-273, 288).

The implementation posture is partial at the contract-lane level only. No cited repository module executes this complete sequence. Refusing all inputs is also insufficient: both accepting and rejecting controls must work under the same frozen revision. CONTRACT-ONLY (FORGE.md:399).

### 8.5 Versioned shortcut taxonomy as a submission gate

The taxonomy binds a version, class definitions, probe inputs, and outcome criteria before review. In one implementation, its classes are lexical overlap, subsequence leakage, negation or polarity handling, positional artifact, and style cue. CONTRACT-ONLY (FORGE.md:288; parent application section 8.21).

For every graded outcome, the author executes probes that attempt acceptance through each applicable class. A lexical probe repeats rewarded terms without producing the required state. A positional probe changes ordering without doing the requested work. These examples illustrate probe construction, not reports of executed attacks. PROSPECTIVE examples.

A successful shortcut prevents submission until repair and replay reject it while legitimate solutions remain accepted. Missing probe execution is unresolved coverage, not evidence of absence. A clean probe may remove a known defect but cannot certify shortcut freedom. CONTRACT-ONLY (FORGE.md:288, 337, 399).

In one implementation, the author stores defeated probes and fixes in its private defense pool. Inputs come only from its own adversarial passes and permitted signed failure aggregates through the author projection. Auditor trajectories, heuristics, and failure explanations are forbidden inputs. CONTRACT-ONLY (FORGE.md:288).

Version binding prevents an author from deleting a troublesome class after observing outcomes while presenting the same gate as complete. A taxonomy change requires new approval and affected probes. CONTRACT-ONLY (FORGE.md:178; parent application section 8.21); PROSPECTIVE version-record enforcement.

### 8.6 Solution-centric mutation and lineage ratchet

The author starts from an executable reference solution, mutates that solution, and re-derives instructions and verifier bytes. Acceptance requires end-to-end executability, a harder comparison outcome against a common solver population, and diversity under a predeclared measure. CONTRACT-ONLY (FORGE.md:289; parent application section 8.21).

Before probing, the author fixes a child rather than selecting retrospectively from a probed sibling pool. It freezes parent and child and draws a fresh block of group seeds. Both execute over that identical block under the identical solver configuration. CONTRACT-ONLY (FORGE.md:289).

Let the parent and child statistics be the respective maximum observed group-success rates across the required solver population. The child clears comparison only when its maximum is at or below the parent maximum less the predeclared improvement margin. Unavailable members or incomplete groups do not silently disappear. CONTRACT-ONLY (FORGE.md:274, 289).

The lineage-wide proposal allowance counts every attempted child, including rejected children. A new identifier from changed bytes does not reset the allowance. When a child first clears the authoring ceiling, a child-only confirmation uses a further fresh block and requires every required solver member to remain below that ceiling. CONTRACT-ONLY (FORGE.md:289).

In one implementation, lineage nodes carry seed, evolved, or saturated tags. Failed confirmation, exhausted allowance, or attempted reuse of a spent block ends the family at saturation. The author retains all attempted child hashes, seed blocks, and outcomes, not only successful descendants. CONTRACT-ONLY (FORGE.md:289).

The diversity measure must identify its representation, comparison set, and threshold before proposals. A prospective implementation compares bound solution-structure features and rejects a child inside the forbidden similarity band. This example requires support review before a priority claim and asserts no implemented feature extractor. PROSPECTIVE.

ENFORCED (tools/pilot.py, first landed 2026-09-03; tests/test_pilot.py) covers closed pilot records, disjoint group and rollout identities, attempt limits, and refusal of reused observations. It does not establish lineage-wide seed freshness: the current module's seed matches are path names, not seed-block fields.

The specific mutation rule remains DEFERRED (DEFERRED.md: "Mutation ratchet bounded by `mutation_cap`, fresh seed blocks, and `mutation_margin`"). The requested seed-block bookkeeping attribution cannot support a broader implemented label. A spent-seed ledger and proposal registry are still required.

A proposed ledger reserves a fresh block against the lineage before either execution and records consumption even when a child fails. Concurrent allocation requires serialized reservation. A duplicate block causes refusal rather than another draw under the same comparison record. PROSPECTIVE implementation detail.

Mutation may consume only the author projection and that bundle's private feasibility artifacts. Missing projection inputs or detected auditor-derived inputs prevent mutation. Comparative author probes remain design screens, not certified hardness evidence. CONTRACT-ONLY (FORGE.md:289, 337).

### 8.7 Discovery asymmetry over the statement closure

The author binds the exact initial statement closure before review. In one implementation, it comprises instruction bytes and statement-embedded assets, excluding environment state, tests, and the private solution. An initial byte omitted from the enumeration creates unresolved coverage. CONTRACT-ONLY (FORGE.md:206).

Each declared discovery value must occur in the private grounding source, exist in the built environment, and derive from that source rather than a statement literal. It must be absent from the statement closure verbatim and under the bound paraphrase-containment rule. CONTRACT-ONLY (FORGE.md:206, 240).

The discovery share is the sum of weights of graded outcomes depending on at least one qualifying discovery value, divided by total graded weight. An outcome with several qualifying values contributes its weight only once. The gate requires that share to reach the predeclared discovery floor. CONTRACT-ONLY (FORGE.md:206, 240); the no-double-count accounting is a PROSPECTIVE explicit implementation.

The local proof rejects a planted statement leak, a below-floor composition, and derivation from a statement literal, while accepting a clean fixture. An empty discovery set blocks absent an explicit scoped human exemption. A generic environment does not cure a statement-only answer. CONTRACT-ONLY (FORGE.md:240).

The deterministic paraphrase control uses normalized token n-gram containment at a bound width and threshold. It is a reproducible overlap test, not complete semantic equivalence detection. A subordinate semantic reviewer may block further leakage but cannot certify absence. CONTRACT-ONLY (FORGE.md:220-221).

ENFORCED (tools/probe.py, first landed 2026-09-03; tests/test_probe.py) covers an advisory offline minimal-context localization probe. It masks source-line suffixes and scores recorded completions by normalized exact match; it calls no model and modifies no bundle. It is not the discovery-weight or paraphrase proof and never counts as difficulty evidence.

The complete closure proof remains DEFERRED (DEFERRED.md: "Discovery asymmetry proved over frozen bytes"; "Statement-only leak probe against the no-op control threshold"). The statement-only execution screen and the static discovery-weight proof are distinct obligations.

### 8.8 Canary planting and private-boundary containment

In one implementation, the provisional bundle carries designated token placeholders. The author computes a canary-normalized content hash while preserving slot counts, order, positions, and surrounding bytes. The normalization version and resulting hash bind in the author contract. CONTRACT-ONLY (FORGE.md:185, 219).

The order is hash, derive, plant, bind. A pure derivation function consumes the hash and produces the ordered token set. Only designated slot values normalize away; a token-shaped string elsewhere remains ordinary identity-bearing content. CONTRACT-ONLY (FORGE.md:185, 219; parent application sections 8.9 and 8.22).

The private extension tree contains the oracle, derivations, generated truth, rubric, checker secrets, and provenance. In one implementation, the solution and trajectory trees remain unavailable to the solving agent. The delivery boundary means the assembled agent-facing export, not the entire archival bundle or its publication status. CONTRACT-ONLY (FORGE.md:194, 218-221).

The leak gate scans assembled visible bytes rather than trusting framework mount behavior. It rejects derived canaries on that surface, malformed private token blocks, and private-answer containment reaching the threshold. Every token slot must hold its exact derived value even though normalization removes that value from the preimage. CONTRACT-ONLY (FORGE.md:219-221, 260).

Provenance binding follows planting. In one implementation, the provenance payload excludes its later binding block and signature, while the binding authenticates payload, bundle, and image digests. These separate domains avoid a self-containing signature or hash. CONTRACT-ONLY (FORGE.md:217).

ENFORCED (tools/bundle_identity.py, first landed 2026-09-16; tests/test_bundle_identity.py) covers path, content, and executable-bit identity, unsafe-object refusal, and top-level trajectory exclusion. Its current digest hashes raw file payloads. It does not implement placeholder normalization, token derivation, or paraphrase containment; those remain CONTRACT-ONLY (FORGE.md:185, 219-221).

### 8.9 Dual-host ground-truth regeneration and recomputation

A private grounding source and deterministic recomputation procedure derive the oracle, golden trajectory, checker fixtures, ground truth, rubric, and compiled tests. The generator reads frozen literals instead of invoking a model during regeneration. CONTRACT-ONLY (FORGE.md:204, 210-211).

Independent execution hosts differ in hostname, working directory, user identity, and environment. Each regenerates the artifacts, computes normalized identity, derives and plants tokens, and produces final bytes. Advancement requires equality of the final planted artifacts, not merely equal normalized hashes. CONTRACT-ONLY (FORGE.md:238, 250).

The proof also compares generated artifacts to committed bytes and reconciles checker, truth-step, and deliverable identifiers in both directions. The oracle must obtain the declared full reward through the actual grading path. A host-local dependency or an unexplained byte difference blocks. CONTRACT-ONLY (FORGE.md:238-239).

The recompute discipline prohibits hand-editing a generated truth artifact to repair a discrepancy. The author changes its source, regenerates dependents, recomputes bindings, and obtains renewed approval where required. CONTRACT-ONLY (FORGE.md:178, 204, 238, 403).

Parent section 8.25 supplies the general determinism discipline and parent claim 17 supplies the independent-host comparison. These are required operations, not evidence that any task regeneration runs in this draft. The full external control runner remains DEFERRED (DEFERRED.md: "External execution service produces accepted oracle receipts").

### 8.10 Anchor-task duration learning and budget orthogonality

In one implementation, human requirements designate at least three and at most five starter anchors spanning at least two axes. Every anchor is a starter and every starter an anchor. Each invocation authors at most one alongside its ordinary batch, and anchors enter pilot execution first. CONTRACT-ONLY (FORGE.md:189-190, 303, 418).

The record keeper admits a duration row to the fitted mapping only when a signed duration outcome resolves for that designated anchor. In one implementation, unresolved rows remain CANDIDATE, qualifying rows become ANCHORED, and stale or cohort-uncovered rows become SUPERSEDED without deletion. CONTRACT-ONLY (ENGRAM.md:247).

The fit requires enough current anchored rows across distinct axes. It describes elapsed cost of lever composition and projects the upper endpoint of a fitted interval as the design ceiling. Wider uncertainty raises that ceiling, making a proposed composition harder to fit within a fixed completion budget. CONTRACT-ONLY (ENGRAM.md:247; FORGE.md:242).

An ordinary slot whose predicted ceiling exceeds its granted budget returns to composition. An anchor is exempt from the mapping check it exists to seed. The mapping cannot set a budget, promote difficulty, create a certificate, or replace signed budget-conformance evidence. CONTRACT-ONLY (FORGE.md:242, 348, 417-418).

No tier derives a completion bound and no completion bound derives a tier. Duration evidence identifies the bound and execution envelope under which it arises; incompatible budget stamps cannot support a common conformance claim. CONTRACT-ONLY (FORGE.md:302, 348, 417; ENGRAM.md:246-247).

ENFORCED (tools/stats.py, first landed 2026-09-02; tests/test_stats.py) supplies pilot probability and finite-lot arithmetic. ENFORCED (tools/pilot.py, first landed 2026-09-03; tests/test_pilot.py) supplies pilot schemas and group-bound checks. Neither cited module fits an anchor-duration mapping or authenticates a duration group as an anchor fit.

The overall posture is partial infrastructure, not an implemented learning loop. The gaps remain DEFERRED (DEFERRED.md: "Starter anchor cardinality and identity"; "Anchoring design-fit check"; "Fitted time-anchor mapping"). Signed duration production remains an external dependency.

In one implementation, a published anchor-standing view carries only identity and standing. Reconciliation graduates an anchor once its duration fold supports that standing, without reading the private mapping. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py) covers the movement, not the validity of the signed-duration fold.

### 8.11 Task economics from granted rates

Economics applies only when human requirements declare a rate card and pricing policy. The author carries their names and digest bindings rather than inventing monetary values. Missing enabled rates, margin, metering sources, or effort attestation create a gap; an unpriced project gets no default economics obligation. CONTRACT-ONLY (FORGE.md:189, 419).

The author records aggregate token and compute consumption per authoring lane and human-attested effort. The authoring stage resolves only known authoring components. A separately signed pilot-consumption receipt supplies the missing pilot component before the complete stage resolves. CONTRACT-ONLY (FORGE.md:244, 304).

That receipt carries aggregate consumption rather than per-rollout entries, duration, or execution instants. The resulting cost outcome binds stage, rate-card identity, pricing-policy identity, cost, and price. It is separate from the execution attestation and cannot replace duration evidence. CONTRACT-ONLY (FORGE.md:304).

The difficulty catalog contains no cost or price field. Both projections forbid per-task costs, prices, lane totals, resolved rate values, effort counts, and identifying receipt detail. The auditor projection carries no economics field. A sufficiently aggregated average pair may enter the author projection only as non-certifying design guidance. CONTRACT-ONLY (ENGRAM.md:248; FORGE.md:244, 348; parent application section 8.34).

The record keeper folds complete signed outcomes into a running aggregate with one revision per reconciliation pass. The aggregate records fold count, dispersion, grant stamps, and consumed-envelope digests, but no per-task row. A changed rate-card digest starts a new aggregate, and a below-minimum fold projects no pair. CONTRACT-ONLY (ENGRAM.md:248).

This exclusion does not promise statistical anonymity: successive aggregate revisions can reveal an individual value by arithmetic. The narrower property is that no per-task economics field enters either projection or the difficulty decision inputs. CONTRACT-ONLY (ENGRAM.md:248).

The economics path remains CONTRACT-ONLY (FORGE.md:419; ENGRAM.md:248). Its gaps include DEFERRED (DEFERRED.md: "Per-lane consumption metering"; "Signed cost predicate"; "Pilot consumption receipt"; "Aggregate economics fold"). No existing pilot schema is represented as a cost-receipt implementation.

### 8.12 Design-return fold

Every sealed task leaves a design return under the author harness. In one implementation, the return names task and bundle identity, batch, run, lane, anchor designation, archetype, emission instant, lever composition, projection epoch, targets, budget, predicted ceiling, and composition headroom. CONTRACT-ONLY (FORGE.md:257).

The return binds the sealed bundle digest but contains no measured pass rate, checker bytes, or rollout detail. A missing return or mismatched digest creates a named gap. The return describes what the author composes against; it never proves the resulting task difficult. CONTRACT-ONLY (FORGE.md:257).

The record keeper folds returns on each invocation. It compares targets and the referenced projection epoch with current hardness standing, compares budget predictions with the anchor mapping, and compares headroom and levers with current floors and freshness. CONTRACT-ONLY (ENGRAM.md:257).

An anchor return registers the composition identity that its eventual duration outcome must name. Stale targets, unsupported budget predictions, and insufficient headroom narrow guidance or open gaps. They do not create difficulty evidence or raise a disposition. CONTRACT-ONLY (ENGRAM.md:257).

Returns are author-projection inputs only and never auditor-projection inputs. Per-batch counts make omitted returns visible without conveying private checker or trajectory content. The fold re-reads design targets against actual sealed compositions rather than only at project genesis. CONTRACT-ONLY (FORGE.md:257; ENGRAM.md:257).

The entire return reader and fold remain DEFERRED (DEFERRED.md: "Design returns and the return lane"). A queue seal alone does not establish that a return exists or that any record keeper consumes it.

### 8.13 Named prior art and novelty residue: arXiv and register comparisons

For slot isolation, SWE-bench Verified and DeepSWE fresh-container grading provide the register's comparison for clean execution environments. BenchEvolver, arXiv 2606.01286, supplies generated executable tasks. The proposed novelty residue is the closed per-slot artifact boundary combined with independent dispositions and non-substitution across verifiers, not containerization or batch generation alone.

For adversarial repair, Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops, arXiv 2606.08960, expressly describes an attacker, fixer, and legitimate solver. The three-process condition is therefore not asserted as individually new. The proposed novelty residue is its binding to isolated-slot advancement together with versioned shortcut refusal and the constrained mutation lineage; obviousness risk remains substantial.

For the shortcut gate, Do LLMs Overcome Shortcut Learning?, arXiv 2410.13343, describes Shortcut Suite with six shortcut types, not this implementation's five-class roster. FoRT-Searcher, arXiv 2606.12087, addresses shortcut-resistant synthesis. The proposed novelty residue is a version-bound class roster controlling submission through executed verifier probes and a refusal condition, rather than a descriptive robustness score.

For mutation, BenchEvolver, arXiv 2606.01286, derives statements and tests from evolved executable solutions; PROPEL, arXiv 2606.18284, optimizes generation using an amortized solve-rate proxy. The proposed novelty residue is the fixed-child, lineage-capped, margin-separated comparison using fresh unreused seed blocks, followed by fresh confirmation and terminal saturation, without treating an author probe as certified difficulty.

For discovery asymmetry, FoRT-Searcher, arXiv 2606.12087, distinguishes apparent complexity from necessary evidence acquisition. GRACE-DS, arXiv 2606.16000, supplies the register's hidden-checklist comparison. The proposed novelty residue is a bound minimum graded-weight share dependent on environment values absent from an enumerated statement closure both verbatim and under the declared paraphrase-containment rule.

For containment, BIG-bench canary GUID and Thinkst Canarytokens supply known planted markers. The proposed novelty residue is the acyclic normalized-hash, derive, plant, bind order together with slot validation and a separate private-answer containment gate over assembled visible bytes. Neither planted markers nor n-gram overlap alone is asserted as new or complete leakage detection.

For regeneration, SWE-bench Verified, DeepSWE fresh-container grading, and Nix RFC 0062 content-addressed derivations supply adjacent reproducibility techniques. The proposed novelty residue is regeneration of a common-source oracle, truth, fixtures, and verifier artifacts across distinct host identities with equality of final planted bytes as an advancement prerequisite, not a digest equality report alone.

For anchors, PROPEL, arXiv 2606.18284, provides a predicted solve-rate design signal. The proposed novelty residue is a duration-only fit restricted to signed qualifying anchor rows, with an upper-interval design ceiling that cannot set a budget or become difficulty evidence. Predictions remain guidance even when they influence composition.

For economics, the register's Trillian Verifiable Log-Derived Map supplies a comparison for derived aggregate state, while PROPEL, arXiv 2606.18284, motivates reducing generation-evaluation cost. The proposed novelty residue is grant-bound costing whose per-task fields cannot enter either projection or the hardness computation, together with stage-complete-only aggregate folding and no per-task aggregate row.

For design returns, BenchEvolver, arXiv 2606.01286, and PROPEL, arXiv 2606.18284, provide adaptive generation comparisons. The proposed novelty residue is a seal-bound declaration folded against current targets, a separate duration mapping, and headroom floors, with stale returns narrowing guidance and never becoming measurements.

Adversarial Reward Auditing, arXiv 2602.01750, and the Scale Labs verifier-design publication dated 2026-09-04 are additional register-based verifier comparisons. Their exact limitation coverage requires human review of retained primary material before filing. This draft does not infer that they lack a limitation merely because the register summary omits it.

Lost in Compaction, arXiv 2608.11242, is locally retrieved this lane from the admitted rendering. It concerns side-constraint loss under compaction and motivates preserving a bound configuration during comparisons. It does not supply a measured result for this pipeline or permission to weaken a solver's execution conditions.

The Hacker-Fixer, FoRT-Searcher, Shortcut Suite, and Lost in Compaction renderings are retrieved this lane from the local admitted corpus. The first eighty lines of each specified rendering ground the comparisons; no numerical result from those papers is adopted as this system's result.

Jia and Harman's mutation-testing survey and Kaplan and Cooper's activity-based costing are user-supplied comparison leads, verification pending. No matching retained source or register entry establishes their text in this lane. They identify conventional mutant adequacy and activity-cost attribution to investigate, not verified citations supporting a patentability conclusion.

### 8.14 Prevention register and technical effect

| Claims | Prevention or comparison operation | Concrete technical object and intended effect |
| --- | --- | --- |
| 1, 18, 20 | Prevent cross-slot reads and artifact substitution | Task namespaces and verifier inputs remain slot-bound |
| 1, 18, 20 | Prevent advancement unless attack rejection and legitimate acceptance coexist | Modified executable verifier rejects an exploit without becoming inert |
| 1, 3, 18, 20 | Prevent submission on successful taxonomy probes | A known shortcut cannot cross the submission gate |
| 1, 4, 5, 18, 20 | Refuse child acceptance on reused comparison blocks or failed predicates | Adaptive search cannot silently reuse its comparison population |
| 6, 8 | Reject literal or containment-positive private values | Agent-facing closure cannot include the specified private answer carriers |
| 7, 9 | Recompute identity and compare final bytes | Circular identity and host-dependent generation are detectable |
| 10-14 | Exclude duration and economics from hardness decisions | Guidance and accounting cannot substitute for execution-derived evidence |
| 15, 19 | Refuse missing returns and prohibited mutation inputs | Sealed design feedback cannot import auditor-private criteria |

Under Alice Step 2A Prong Two, claims 1, 18, and 20 connect generation to constrained data access and denied machine transitions. The relevant objects are verifier revisions, bound submissions, lineage records, and task bytes. Step 2B consideration concerns the ordered combination, not the mere use of a language model.

Recentive Analytics v. Fox identifies risk where generic machine learning merely automates an abstract objective. Here mutation and probe steps are recited as concrete pipeline gates rather than generic model training. That framing does not settle eligibility; runtime isolation and the complete gate implementation remain prospective where identified.

For EPO Art. 52 and Guidelines G-II 3.3 and 3.3.1, the specific technical purposes are verifier robustness and reproducible executable-task generation. The comparison arithmetic operates a lineage-acceptance gate, containment controls byte exposure, and regeneration detects host-dependent artifacts. Better educational content or commercial pricing alone is not the proposed technical effect.

For India s.3(k), claim 1 addresses cross-slot data substitution and verifier exploitation as technical problems. Its technical solution configures isolated execution contexts and conjunctive executable gates. A measurable technical benefit would be rejection of foreign-slot submissions and exploits while accepting legitimate solutions, assessed with paired fixtures; no novel hardware is required under the Ferid Allani and Microsoft v. Assistant Controller framing.

For India s.3(k), claim 18 addresses unstable task generation and adaptive comparison reuse. Its method freezes a child, controls comparison seeds, tests verifier behavior, and prevents invalid advancement. A measurable technical benefit would be reproducible refusal of reused comparisons and preservation of instruction-satisfying execution; no novel hardware is required, and no measured benefit is asserted.

For India s.3(k), claim 20 concerns processor instructions that otherwise permit unbound artifacts and invalid verifier revisions to advance. The stored program configures the same slot-specific access restrictions and acceptance gates. A measurable technical benefit would be fewer admissible invalid state transitions under planted counterexamples; the claim ties the medium to machine operation rather than an algorithm per se, without requiring novel hardware.

### 8.15 Scope, single-actor operation, and the permanently human acts

File names, paths, role labels, predicate strings, refusal tokens, and numerical examples are illustrative implementation vocabulary. Claims use functional artifact and process descriptions instead. In one implementation, the author harness is `.seed/`, the return store is `.seed/returns/`, and the normalized hash binds in `.seed/contract.yaml`; none is a claim limitation.

A single platform operator can perform or cause all claimed authoring and verification steps through separate processes. Distinct technical identities and access rights do not require distinct legal entities. Signed duration and consumption sources remain external to author-controlled authority where specified, even if a separate organizational unit operates them.

The drafting party reconciles this disclosure and never files it. Filing is a permanently human act. External publication, operational acceptance against a capped disposition, and admission into a human-graded calibration collection also remain human acts. No statement asserts a filing, deployment, or measured pass rate.

The combined claims are proposed, not conclusions of validity, priority, or freedom to operate. Human counsel should review written-description support for each added implementation detail, the parent relationship, actual restriction history, double-patenting issues, and the art combinations before any filing decision.

## 9. CLAIMS

What is claimed is:

**1. A system for controlling authoring of executable evaluation tasks, comprising:** one or more processors; one or more non-transitory memories storing instructions that configure the processors to allocate a batch of parallel task slots, each with a respective manifest, instruction representation, execution environment, verifier, and executable reference solution; prevent a slot from reading another slot's bundle bytes and prevent an artifact of a slot from satisfying another slot's verifier; resolve respective slot dispositions independently such that a blocking disposition of a slot does not cap a sibling slot; for a candidate task in a slot, execute an attacking process that attempts verifier acceptance without instruction satisfaction, a repair process that modifies the verifier in response, and a solving process that executes a legitimate solution against the modified verifier, preventing advancement unless the attempt is rejected and the legitimate solution remains accepted; execute probes corresponding to predeclared classes of a versioned shortcut taxonomy and prevent submission while a probe obtains verifier acceptance through a shortcut; and generate a child task by mutating an executable reference solution and deriving child instructions and verifier bytes from the mutated solution, accepting the child into a lineage only upon executability, an empirically harder comparison outcome against its parent under a common solver population, and diversity under a predeclared measure, wherein each comparison uses an identical seed block for parent and child that no earlier comparison in the lineage consumes, and reuse of a spent block prevents child acceptance.

**2.** The system of claim 1, wherein the batch comprises ordinary task slots and a separately designated anchor slot excluded from an ordinary-slot floor, and the processors refuse an anchor-slot allocation exceeding a bound per-invocation allowance.

**3.** The system of claim 1, wherein the shortcut classes comprise lexical overlap, subsequence leakage, negation or polarity handling, positional artifact, and style cue, and the processors execute class-specific probes against each graded outcome under a bound taxonomy version.

**4.** The system of claim 1, wherein the processors fix the child before probing rather than selecting among a pool of probed children, count every proposal against a lineage-wide cap that persists across changed task identifiers, and accept the comparison only when the child's maximum solver success rate is at or below the parent's maximum solver success rate less a predeclared margin under a common frozen configuration.

**5.** The system of claim 4, wherein the processors retain attempted descendants with respective tags identifying an initial task, an accepted descendant, or a saturated branch, require a child-only confirmation on a further fresh seed block after an accepted child first clears an authoring ceiling, and terminate the branch upon failed confirmation, exhaustion of the cap, or reuse of a spent seed block.

**6.** The system of claim 1, wherein the processors bind an agent-visible statement closure and a discovery floor, verify that declared discovery values derive from a private grounding source and exist in the execution environment while remaining absent from the closure verbatim and under a bound paraphrase-containment rule, and prevent advancement unless a share of total graded weight dependent on those values reaches the discovery floor.

**7.** The system of claim 1, wherein the processors compute a content hash after replacing values in designated canary-token slots with fixed placeholders while retaining slot positions and surrounding bytes, derive tokens from the content hash, plant the tokens in the designated slots after hashing, and then apply a binding that associates the content hash and a normalization-domain version with an author contract.

**8.** The system of claim 7, wherein the processors prevent a private extension tree containing oracle material from crossing an agent-facing delivery boundary, validate each designated slot against its derived token, scan assembled agent-visible bytes for the tokens, and refuse advancement when private-answer n-gram containment reaches a bound threshold under a bound normalization and n-gram width.

**9.** The system of claim 7, wherein the processors regenerate ground truth, the reference solution, checker fixtures, and derived verifier artifacts from a common private source on independent execution hosts having different host identities, compare final planted artifact bytes with each other and with committed bytes, and prevent advancement upon any inequality.

**10.** The system of claim 2, wherein human-authored requirements designate starter anchors within lower and upper cardinality bounds and across distinct composition axes, each starter is a designated anchor and each designated anchor is a starter, and the processors cause pilot execution of the anchors before ordinary tasks.

**11.** The system of claim 10, wherein the processors fit an elapsed-duration mapping only from qualifying anchor rows bound to signed duration outcomes, project an upper endpoint of a fitted interval as a design ceiling, and prevent the mapping or design ceiling from creating difficulty evidence or raising a task disposition.

**12.** The system of claim 11, wherein the processors bind a completion bound and execution envelope from human-authored requirements independently of a difficulty tier, prevent derivation of the bound from the tier and derivation of the tier from the bound, and require duration evidence to carry the bound and envelope under which the duration arises.

**13.** The system of claim 1, wherein the processors resolve a rate card and pricing policy by name from a human-authored requirements corpus, meter authoring-lane consumption, compute an authoring-stage cost from that consumption under the granted rates, and compute a complete-stage cost and price only after resolving a separately signed pilot-consumption receipt.

**14.** The system of claim 13, wherein the processors exclude cost and price from a difficulty computation, designate per-task cost, price, consumption, effort, and resolved-rate fields as forbidden in both an author projection and an auditor projection, and fold complete signed cost outcomes into a revisioned aggregate that stores no per-task row and projects no average pair below a bound fold count.

**15.** The system of claim 1, wherein the processors require each sealed task to leave a design return bound to its sealed digest, cause a record-keeper process to fold the return against current hardness targets, an anchor-duration budget mapping, and composition headroom floors, and permit the fold to narrow guidance or open a gap but not create difficulty evidence or raise a disposition.

**16.** The system of claim 2, wherein the processors maintain slot-specific routing independently of the ordinary-slot floor, seat ungraduated anchors within a structural sample-residency ceiling, route overflow by seal order to a separate delivery root without reducing the floor, and prevent a task identifier from residing under both roots.

**17.** The system of claim 1, wherein the processors require each mandatory local verifier control to reject a targeted invalid submission and accept a legitimate submission under the same frozen bytes, and prevent advancement when the control demonstrates only rejection or only acceptance.

**18. A computer-implemented method for controlling authoring of executable evaluation tasks, comprising:** allocating, by processors, a batch of parallel task slots, each with a respective manifest, instruction representation, execution environment, verifier, and executable reference solution; preventing a slot from reading another slot's bundle bytes and preventing an artifact of a slot from satisfying another slot's verifier; resolving respective slot dispositions independently such that a blocking disposition of a slot does not cap a sibling slot; for a candidate task in a slot, executing an attacking process that attempts verifier acceptance without instruction satisfaction, a repair process that modifies the verifier in response, and a solving process that executes a legitimate solution against the modified verifier, and preventing advancement unless the attempt is rejected and the legitimate solution remains accepted; executing probes corresponding to predeclared classes of a versioned shortcut taxonomy and preventing submission while a probe obtains verifier acceptance through a shortcut; and generating a child task by mutating an executable reference solution and deriving child instructions and verifier bytes from the mutated solution, accepting the child into a lineage only upon executability, an empirically harder comparison outcome against its parent under a common solver population, and diversity under a predeclared measure, wherein each comparison uses an identical seed block for parent and child that no earlier comparison in the lineage consumes, and reuse of a spent block prevents child acceptance.

**19.** The method of claim 18, further comprising restricting mutation inputs to a permitted author projection and the candidate task's private feasibility artifacts, refusing mutation upon absence of a required projected input or detection of non-projected auditor-derived input, and preventing author-side probe outcomes from substituting for external signed difficulty evidence.

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by processors, cause the processors to perform operations for controlling authoring of executable evaluation tasks, the operations comprising:** allocating a batch of parallel task slots, each with a respective manifest, instruction representation, execution environment, verifier, and executable reference solution; preventing a slot from reading another slot's bundle bytes and preventing an artifact of a slot from satisfying another slot's verifier; resolving respective slot dispositions independently such that a blocking disposition of a slot does not cap a sibling slot; for a candidate task in a slot, executing an attacking process that attempts verifier acceptance without instruction satisfaction, a repair process that modifies the verifier in response, and a solving process that executes a legitimate solution against the modified verifier, and preventing advancement unless the attempt is rejected and the legitimate solution remains accepted; executing probes corresponding to predeclared classes of a versioned shortcut taxonomy and preventing submission while a probe obtains verifier acceptance through a shortcut; and generating a child task by mutating an executable reference solution and deriving child instructions and verifier bytes from the mutated solution, accepting the child into a lineage only upon executability, an empirically harder comparison outcome against its parent under a common solver population, and diversity under a predeclared measure, wherein each comparison uses an identical seed block for parent and child that no earlier comparison in the lineage consumes, and reuse of a spent block prevents child acceptance.

## 10. ABSTRACT OF THE DISCLOSURE

A computing system authors executable evaluation tasks in isolated parallel slots with independent dispositions. An attacking process attempts verifier acceptance without instruction satisfaction, a repair process modifies the verifier, and a solving process confirms legitimate acceptance. Advancement requires attack rejection and legitimate acceptance. Versioned shortcut-class probes prevent submission when a shortcut succeeds. Solution-centric mutation derives child instructions and verifiers from an executable solution and admits a child only upon executability, comparative hardness, and declared diversity. Parent and child share a fresh comparison seed block that subsequent comparisons cannot reuse. Further controls require environment-dependent discovery weight, digest-derived canaries, private-answer containment, and byte-identical ground-truth regeneration across hosts. Signed anchor durations inform design without evidencing difficulty. Grant-bound accounting remains outside difficulty decisions. Seal-bound design returns reconcile targets, budget predictions, and headroom without becoming measurement evidence.
