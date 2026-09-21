# UNITED STATES NON-PROVISIONAL UTILITY PATENT APPLICATION

**Filed under 35 U.S.C. § 111(a)**

**Title:** Both-Halves Liveness of Deterministic Grounding Instruments, Three-Valued Execution-Fidelity Forensics, and Conformal Admission of Machine Judges for Evaluation-Task Audit

**Inventor:** Sarvex Jatasra

**Applicant / Assignee:** Ethara.AI

**Docket Reference:** Trinity/auditor-instruments

---

## 1. TITLE OF THE INVENTION

Both-Halves Liveness of Deterministic Grounding Instruments, Three-Valued Execution-Fidelity Forensics, and Conformal Admission of Machine Judges for Evaluation-Task Audit

## 2. CROSS-REFERENCE TO RELATED APPLICATIONS

The related parent disclosure is titled "Cryptographically Controlled Certification of Machine-Learning Evaluation Tasks Using Isolated Generation, Audit, and Evidence Domains." Its filing is prospective. This application is intended as a divisional or continuation of that disclosure, with the choice left to the human filing decision after review of support, priority, restriction, and consonance requirements. No application number, filing date, priority entitlement, or restriction requirement is asserted.

The parent describes instrument liveness, grounding families, screening, reward integrity, rubric isolation, and judge admission in sections 8.17 through 8.20, 8.23, and 8.24. Its claims 9, 10, 17, 27, and 28 carry corresponding dependent forms. This disclosure makes auditor-side evidence admissibility the independent combination, adds explicit execution-fidelity support, and does not delete or renumber any parent claim.

## 3. STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

## 4. FIELD OF THE INVENTION

The disclosure concerns verification infrastructure for executable machine-learning evaluation tasks. It concerns deterministic audit instruments, bounded native-trace readers, configuration reconciliation, and machine-enforced admission of statistical judging evidence. The controlled object is a certification state derived from executable task and execution-evidence bytes, not an abstract assessment of quality.

## 5. BACKGROUND OF THE INVENTION

A first deficiency is an audit instrument that always emits the same answer. A clean fixture alone cannot distinguish a working detector from one that never fires. A defective fixture alone cannot distinguish a discriminating detector from one that rejects everything. Treating either behavior as a reliable audit permits false-clean certification or makes legitimate evidence unusable.

A second deficiency is a negative conclusion inferred from absent telemetry. A normalized trajectory may omit native context-transformation events. A self-reported counter may remain zero while a different runtime layer transforms the solver's context. Missing markers then masquerade as evidence that the declared execution conditions hold.

A third deficiency is one-sided measurement control. A weakened execution harness can lower solver success and make an evaluation task appear harder. A release condition that rejects unexpectedly high success but ignores suppression rewards this defect. A pinned configuration alone cannot establish that its limits are adequate for the task horizon.

A fourth deficiency is treating repeated agreement by a machine judge as validity. A judge can repeat a biased answer, change verdict under neutral presentation changes, or return an ambiguous prediction set. Displaying reliability statistics without conditioning admission of the score leaves the certification path open.

A fifth deficiency is evidence selection after observation. Distributional bounds chosen after rewards arrive and rubric criteria chosen after trajectories arrive can fit the observed population. An auditor that receives an author's intended difficulty targets can similarly grade the intention rather than the committed artifact.

## 6. SUMMARY OF THE INVENTION

An audit computing system couples a liveness precondition, a coverage-sensitive forensic reader, and a conformal judge-admission gate to a disposition state. Before relying on a required deterministic instrument, the system requires a common-run result for a frozen planted-defect fixture and its corresponding clean twin. Failure of either required decision blocks reliance on the instrument and blocks the audit disposition.

The forensic reader distinguishes observed violation, demonstrated coverage without violation, and insufficient evidence. Absence alone never supplies a clean result. The reader reduces signal findings conservatively and refuses unsupported, incomplete, self-reported-only, unsafe, or over-limit evidence as a basis for cleanliness.

The judge gate uses a policy fixed before judgment admission and reference labels withheld from the judge during the reference exercise. It recomputes trial statistics and conformal prediction sets. Missing required coverage causes abstention or blocking rather than a point verdict accepted on trust. The complete deployment gate is a proposed architecture; the present repository validates declared judgment records, not every possible judge invocation.

Additional embodiments bind screening roots, reward statistics, rubric provenance, and harness configuration before their respective evidence is consumed. Deterministic instruments and admitted semantic judgments may lower or cap a disposition but cannot themselves raise it. Separate external acceptance remains necessary for release.

## 7. BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 depicts an audit processor receiving committed task bytes, a required-instrument registry, frozen twin fixtures, native execution evidence, and a predeclared judge policy, with their outcomes feeding a common disposition reducer.

FIG. 2 depicts the liveness sequence: resolve fixture digests, run the planted and clean fixtures in a common audit run, compare normalized decisions, and prevent reliance when either decision fails.

FIG. 3 depicts descriptor-relative traversal from a trusted project root to native evidence, format-specific coverage analysis, and reduction into violation, covered-clean, or insufficient-evidence standing.

FIG. 4 depicts configuration binding and separate adequacy approval alongside realized-population reconciliation, with suppressing or unverified execution causing a hold and an unprovable population causing a block.

FIG. 5 depicts blinded judge calibration, repeated randomized presentations, exact agreement diagnostics, conformal-set reconstruction, and an admission switch that remains closed without established coverage.

FIG. 6 depicts temporal separation of a reward-statistic commitment from observed rewards and of a rubric digest commitment from judged trajectories, followed by the auditor evidence citation check.

## 8. DETAILED DESCRIPTION OF THE INVENTION

### 8.1 Overview

The system comprises processors, non-transitory memory, a task-byte store, an instrument registry, a fixture manifest, a private audit evidence store, a native-trace reader, a judge-policy store, and a disposition reducer. The processor executes the verification relations described below. The architecture is PROSPECTIVE as a complete combination; each mechanism identifies the narrower present enforcement or contract support.

An audit begins by fixing task, instrument, fixture, sandbox, and policy identities. It determines required controls from in-scope surfaces rather than from a producer's assertion that nothing needs testing. It runs liveness checks before using substantive instrument outcomes and records findings and gaps without substituting model judgment for a missing deterministic relation. CONTRACT-ONLY (CRUCIBLE.md:117, 140-142, 178, 228, 234).

Implementation labels in this disclosure refer to one repository realization. ENFORCED means that the named code evaluates the identified predicate and a named test file exists with relevant assertions. It does not mean the test suite runs during this drafting pass or that an external execution authority exists. DOC-NORMATIVE identifies definitions, vocabulary, and rules in docs/measurement-fidelity.md, not executable enforcement. First-landed dates describe file-addition history, not the introduction date of every current function.

The source line references use the current unwrapped Markdown files. The supplied approximate offsets for the audit contract and author invariant differ from this tree: the operative verifier principles are at CRUCIBLE.md:234 and 236, and the author invariant is at FORGE.md:399. Semantic section identities control the cross-reference.

### 8.2 Definitions

A deterministic grounding instrument is executable verification logic over a declared input closure. Identical input bytes, pinned tool identities, and declared evaluation parameters determine identical normalized findings. Its clean result removes no independent release prerequisite. CONTRACT-ONLY (CRUCIBLE.md:140-142).

A planted-defect fixture contains a defect that the registered instrument is required to detect. A clean twin preserves the relevant structure while omitting that defect. A fixture manifest identifies the subject relation, both fixtures, their digests, and expected normalized decisions. CONTRACT-ONLY (CRUCIBLE.md:173, 234).

A common run is one audit invocation under a common bound instrument and fixture closure. Earlier fixture results under different bytes do not satisfy the current liveness precondition. A fail-closed instrument rejects unresolved or defective evidence while retaining a reachable valid branch. An inert instrument fails to discriminate on the required twin pair. CONTRACT-ONLY (CRUCIBLE.md:234; FORGE.md:399).

Demonstrated coverage is affirmative evidence that the required observation channel, supported native vocabulary, and complete event sequence cover the signal class without an observed violation. It is not a universal guarantee that an executing party tells the truth. The distinction between recorded coverage and independent custody remains explicit. CONTRACT-ONLY (CRUCIBLE.md:236); DOC-NORMATIVE (docs/measurement-fidelity.md:130-166).

A disposition is a machine-readable upper bound on reliance. A block dominates a hold; neither is release. A clean deterministic result or admitted judge result cannot lift an existing cap. Trial conformance is separate from solver success, and an approved limit firing as declared need not be a violation. CONTRACT-ONLY (CRUCIBLE.md:211-236).

### 8.3 Both-halves liveness and the inert-instrument block

For each required deterministic instrument, the processor resolves the frozen fixture pair and invokes the instrument on both members within the common run. It compares the resulting normalized finding identities with the manifest expectations. Detection of the planted defect and absence of that finding on the clean twin are conjunctive prerequisites to reliance. CONTRACT-ONLY (CRUCIBLE.md:173, 178, 234; parent section 8.17).

A present check that returns clean on both members is inert. A present check that reports the defect on both members also fails the required discrimination. The processor sets a blocking disposition on either failed half rather than labeling the instrument fail-closed. A detector that cannot fire otherwise certifies a clean result it never tested. CONTRACT-ONLY (CRUCIBLE.md:234; FORGE.md:399).

Missing liveness evidence differs from an observed failed fixture decision. Under the audit contract, a one-sided self-verification is a coverage gap capped at hold or below; an established inert required check blocks. The claimed embodiment requires the complete pair before reliance, while preserving this distinction in diagnostic records. CONTRACT-ONLY (CRUCIBLE.md:234).

In one implementation disk-backed fidelity fixtures enumerate reachable family-signal pairs, require planted violations, and compare clean fixtures with each format's strongest supported outcome. A conversion-only clean fixture correctly remains insufficient evidence; it is not promoted merely to make the test green. ENFORCED (tools/forensics/core.py, first landed 2026-09-18; tests/test_forensics_core.py; tests/test_forensics_fixtures.py).

In one implementation reward-distribution fixtures exercise matched and moved digests, ordered and unordered commitments, and in-bound and out-of-bound statistics. These tests provide executable twin branches for that module. ENFORCED (tools/reward_distribution.py, first landed 2026-09-20; tests/test_reward_distribution.py).

The requested fixture attribution needs a narrower statement: tests/test_fixtures.py constructs tracker and parent surfaces, not a universal instrument-liveness gate. No generic twin-fixture conformance function is identified in tools/integrity.py. Its audit citation checker has planted and clean tests, described in section 8.12. Universal same-run liveness across every required family therefore remains CONTRACT-ONLY (CRUCIBLE.md:234), not enforcement inferred from a test filename.

### 8.4 Grounding families, sandbox purity, and dual-host regeneration

The baseline registry contains delivery conformance, reference fidelity, calibration, verifier robustness, rubric compilation, contamination screening, reward integrity, and budget conformance. Execution fidelity, adversary probes, and optimization checks extend the registry without redefining those baseline families. Every registered deterministic relation has required conditions and an absence cap. CONTRACT-ONLY (CRUCIBLE.md:140, 147-165; parent section 8.18).

Delivery conformance resolves the delivered path set, task schema, image digest, network policy, reward output, and generated ground truth. It compares declared step identifiers with committed checker identifiers in both directions. It distinguishes a missing legacy binding from a present binding that fails. CONTRACT-ONLY (CRUCIBLE.md:147, 203).

Reference fidelity obtains a pinned upstream artifact and scores it through the recorded invocation contract. Calibration separately checks ordering against signed aggregate outcomes and portable rebuildability. Verifier robustness covers repeatability, perturbation invariance, raw-log replay, preserved baselines, flakiness, zero-score attribution, and patch-application parity. CONTRACT-ONLY (CRUCIBLE.md:149-151).

Rubric compilation validates item shape, compiled-test identity equality, compiled weight, semantic residue, deterministic regeneration, and rejection of known-wrong controls. Budget conformance compares manifest-bound limits and execution envelopes against attested durations; a standing requirement can withdraw an otherwise applicable absence exemption. CONTRACT-ONLY (CRUCIBLE.md:152, 163).

Each family runs in a hermetic sandbox with pinned image and network policy and consumes committed task bytes plus permitted audit inputs. An unavailable sandbox or required input caps the dependent result. A clean result cannot raise disposition or establish difficulty. CONTRACT-ONLY (CRUCIBLE.md:140, 148).

The generator exception executes committed producer code under sandbox identities that differ in hostname, working directory, user, and environment. Both outputs must equal each other and the committed ground-truth, oracle, and checker-fixture bytes. Host-dependent output remains a finding even if one host matches. Rubric regeneration uses the same discipline. CONTRACT-ONLY (CRUCIBLE.md:147, 152; parent section 8.18).

Optimization checks additionally re-derive bounded continuous reward, attempt and compute bindings, rubric-line shape, iteration history, and inspection plots. These checks only lower or cap. They do not turn optimization traces into difficulty evidence. CONTRACT-ONLY (CRUCIBLE.md:162); DEFERRED (DEFERRED.md: "Optimization plot filenames").

Reference acquisition and external confirmation retain a boundary: DEFERRED (DEFERRED.md: "`G-REF-OBTAIN`"; "Reference fidelity and verifier robustness are proven, never assumed"). No acquisition protocol or independent signed replay is inferred from the family name.

### 8.5 Three-valued execution-fidelity forensics

In one implementation each signal resolves to `VIOLATION`, `COVERED_CLEAN`, or `INSUFFICIENT_EVIDENCE`. A rollout reduces to violation if any finding is a violation; otherwise it reduces to insufficient evidence if any finding is insufficient or the covered signal set is incomplete; only the remaining case is covered-clean. Repeated entries for one signal cannot replace a missing signal. ENFORCED (tools/forensics/core.py, first landed 2026-09-18; tests/test_forensics_core.py).

In one implementation the signal vocabulary comprises compaction, observation truncation, turn cap, timeout, provider error, refusal, setup failure, and handoff failure. A native positive marker can establish violation without proving complete coverage. A missing marker cannot establish a negative conclusion. ENFORCED (tools/forensics/core.py, first landed 2026-09-18; tests/test_forensics_core.py; tests/test_forensics_fixtures.py).

In one implementation adapters recognize Claude Code JSONL, OpenHands event streams, OpenHands native metrics, CyberGym usage accompanied by a raw agent log, and normalized ATIF trajectories. Normalized ATIF alone has an insufficient-evidence ceiling; an accompanying native source supplies the evidence and its family identity. Usage alone cannot prove absence of compaction. ENFORCED (tools/forensics/family.py, first landed 2026-09-18; tests/test_forensics_family.py; tests/test_forensics_fixtures.py).

Coverage relations examine bootstrap and request inventories, terminal events, declared limits, and submission bindings. Unsupported native versions and incomplete sequences prevent clean inference. The reader does not treat a runtime's own zero counter as independent evidence of absence. ENFORCED (tools/forensics/coverage.py, first landed 2026-09-18; tests/test_forensics_fixtures.py).

In one implementation refusal classes are `FIDELITY_FAMILY_UNRECOGNIZED`, `FIDELITY_VERSION_UNSUPPORTED`, `FIDELITY_TRACE_CONVERSION_ONLY`, `FIDELITY_SEQUENCE_INCOMPLETE`, `FIDELITY_SELF_REPORTED_ONLY`, and `FIDELITY_TRACE_UNREADABLE`. In particular, a zero summarization count without a covering native channel resolves under the self-reported-only class. ENFORCED (tools/forensics/core.py, first landed 2026-09-18; tests/test_forensics_core.py).

The filesystem reader opens a trusted root directory and retains each parent descriptor while opening its child without following symbolic links. It rejects parent traversal and paths outside the trusted root. It opens the final file relative to the retained parent, checks the opened object's regular-file type and size, and reads only within a fixed budget. ENFORCED (tools/forensics/filesystem.py, first landed 2026-09-18; tests/test_forensics_security.py; tests/test_fidelity_ledger_reader.py).

In one implementation discovery limits are 8,192 entries, depth 16, 1,024 rollouts, and 64 MiB aggregate family bytes. The purpose is to reject an unbounded evidence tree rather than silently omit its difficult suffix. Exceeding a read limit cannot yield cleanliness. ENFORCED (tools/forensics/family.py, first landed 2026-09-18; tests/test_forensics_security.py).

The ledger writer permits only the actual audit root or its validated run namespace under a caller-supplied project root. A nested candidate directory merely named like the audit root is refused. In one implementation `emit_fidelity_ledger` stores canonical bytes under `.audit/fidelity.yaml` or `.audit/runs/<run>/fidelity.yaml`. ENFORCED (tools/forensics/ledger.py, first landed 2026-09-18; tests/test_forensics_security.py).

The bounded ledger reader reconstructs standing instead of trusting serialized trial labels. It rejects malformed, unknown-field, duplicate-key, symlinked, oversized, or inconsistent evidence; harmless formatting differences can reconstruct the same canonical bytes. In one implementation `project_for_pilot` exposes rollout tokens and a ledger digest, not detector explanations. ENFORCED (tools/forensics/ledger.py, first landed 2026-09-18; tests/test_fidelity_ledger_reader.py; tests/test_forensics_family.py).

Native logs remain statements by the executing party unless independent capture establishes more. DEFERRED (DEFERRED.md: "Observation capture precedes operator editing"; "Effective request and response capture"; "Provider-internal routing declared and verified"). No covered-clean local record proves those external duties. The requested tests/test_forensics_coverage.py is absent; coverage evidence here names existing fixture, core, family, and security tests instead.

### 8.6 Measurement taxonomy, symmetric cap, and configuration adequacy

The taxonomy keeps mechanism, statistical consequence, and missing control on separate axes. Mechanisms include context compaction, truncated observations, early stopping, retries masking provider errors, refusal, setup failure, handoff loss, service degradation, and shared execution state. Consequences include suppressed or inflated capability, destroyed independence, corrupted population definition, and an undefined estimand. Controls concern pinning, adequacy, capture, population commitment, classification, coverage, and independent execution authority. DOC-NORMATIVE (docs/measurement-fidelity.md:23-62).

In one implementation per-trial tokens are `conforming`, `nonconforming`, and `indeterminate`. They accompany success or failure rather than replace it. A faithfully applied approved timeout can be conforming even when the solver does not succeed. A suppressing violation is nonconforming; unproved coverage is indeterminate. ENFORCED (tools/forensics/core.py, first landed 2026-09-18; tests/test_forensics_core.py; tests/test_forensics_fixtures.py).

The audit family combines configuration, trace, population, and scoring-handoff standing. A suppressing violation or unproved coverage caps at a suppressed-measurement hold. An unprovable realized population blocks rather than becoming a smaller measured population. A disagreement between operator and derived status cannot supply clean evidence. ENFORCED (tools/forensics/family.py, first landed 2026-09-18; tests/test_forensics_family.py).

In one implementation the cap is `HOLD:SUPPRESSED_MEASUREMENT`, with private reasons ordered as configuration unpinned, drift, inadequate, handoff unverified, context uncovered, and remaining fidelity unverified. The invalid-population value is `BLOCK:INVALID_PILOT`. Reason detail stays on the auditor side. DOC-NORMATIVE (docs/measurement-fidelity.md:226-246) defines the vocabulary; ENFORCED (tools/forensics/family.py, first landed 2026-09-18; tests/test_forensics_family.py) evaluates family standing.

The configuration parser fixes effective model and runtime identity, context and output limits, truncation, turns, tool caps, timeout, sampling, prompt digest, sandbox, network, retries, and condenser settings. In one implementation its schema is `trinity.harness-config/v1`. Unknown fields, missing fields, unsupported versions, invalid values, ambiguous model identity, and nonpositive context headroom refuse parsing. ENFORCED (tools/harness_config.py, first landed 2026-09-18; tests/test_harness_config.py).

Approval, adequacy, and reconciliation are separate operations. The evaluator checks a human-source grant, explicit compaction authorization, minimum observation length, and minimum headroom, then compares bound and effective configuration. In one implementation refusal members include `HARNESS_CONFIG_MISSING`, `HARNESS_CONFIG_UNAPPROVED`, `HARNESS_CONFIG_INADEQUATE`, and `HARNESS_CONFIG_DRIFT`. ENFORCED (tools/harness_config.py, first landed 2026-09-18; tests/test_harness_config.py).

The parent configuration check qualifies present mirror and source configuration bytes. A parent carrying neither configuration is outside that check's scope; this exemption is not a route around a trajectory-bearing fidelity requirement. Whether a headroom grant fits the task remains a human judgment. DEFERRED (DEFERRED.md: "Configuration adequacy judged by a governance authority"). Adequacy is not decidable from disk merely because a signed block declares it.

In one implementation the pilot evaluator requires the auditor ledger digest and exact projected trial-status agreement before computing its bound. Nonconforming or indeterminate members contribute worst-case group indicators without removal from the fixed denominator. Refusals include `PILOT_FIDELITY_UNBOUND`, `PILOT_TRIAL_STATUS_DISAGREES`, `PILOT_GROUP_POPULATION_MUTATED`, and `PILOT_SUPPRESSION_FRACTION_EXCEEDED`. ENFORCED (tools/pilot.py, first landed 2026-09-03; tests/test_pilot.py).

The historical taxonomy's pre-change diagnosis is not a current enforcement map. Its statements that adapters and pins are unbuilt do not override the dated modules above. Conversely those modules cannot establish independent custody or a genuinely precommitted external population. DEFERRED (DEFERRED.md: "Precommitted population roster reconciled against realized groups"; "Independent execution authority controls admission, execution, observation, and custody").

### 8.7 Contamination screening and immutable roots

Every in-scope committed task undergoes exclusion, freeze, near-duplicate, sanitization, empty-submission, and provenance checks. There is no family-wide presence exemption. Only specified repository relations and freeze conditions can be deterministically non-applicable; the remaining atoms still run. CONTRACT-ONLY (CRUCIBLE.md:153-158, 205-207; FORGE.md:406).

Exclusion resolves stable repository identity, full fork ancestry, and base commit membership against immutable roots. A client extension may be replaced under an authorized mode, but an immutable baseline cannot be erased by that replacement. A clean direct parent cannot conceal an excluded ancestor. CONTRACT-ONLY (CRUCIBLE.md:153; parent section 8.19).

Freeze uses the task-generating event against every applicable versioned cutoff and reconciles independently signed source evidence. A rewritten commit date alone proves no qualifying event time. Unavailable attestation is a gap, and attestation-declaration disagreement is a blocking breach. CONTRACT-ONLY (CRUCIBLE.md:153, 155).

Near-duplicate screening compares each bound representation under each bound normalization. An operating-threshold hit blocks; a review-band hit requires recorded semantic adjudication that can only lower standing. The floor and its recall bind to a labelled adversarial duplicate set. Without that calibration the threshold has no demonstrated detection power. CONTRACT-ONLY (CRUCIBLE.md:154, 206).

Sanitization examines the agent-visible delivery closure, including image history and unpacked layers with whiteouts, runtime mounts, environment, credentials, and network policy. The specified closure is broader than a merged filesystem. DEFERRED (DEFERRED.md: "History-absence under `G-CON-STRIP`") retains the incomplete layer coverage; the full closure is CONTRACT-ONLY (CRUCIBLE.md:153; parent section 8.19).

Empty-submission validation requires no-change input to leave intended repair targets unresolved. Provenance uses a closed carrier, immutable root digests, and an independently recomputed binding block over the same normalized bundle domain as the leak gate. Unknown carrier fields or divergent bindings block rather than invite interpretation. CONTRACT-ONLY (CRUCIBLE.md:153, 169).

Each new invocation screens against effective roots and retains shipped-under measurements without rewriting them. Published expiry bounds permit independent standing calculations, but actual re-audit still requires invocation. No scheduler is implied. CONTRACT-ONLY (CRUCIBLE.md:156-158).

The family is partial at the portfolio level: schema and parser support do not establish access to complete external root corpora or execution of every atom. No complete tool-and-test pair for this screening family is established by the inspected files, so its substantive checks remain CONTRACT-ONLY (CRUCIBLE.md:153-158). DEFERRED (DEFERRED.md: "Platform attestation matches declaration"; "Near-duplicate ancestry or event attestation available") preserves the external dependency.

### 8.8 Reward integrity and statistics fixed before observation

Reward definition tests whether the committed checker encodes the stated objective through oracle, no-op, known-wrong, and feasibility controls. Reward provenance reconstructs components before scalarization and checks scorer closure and permitted influence channels. Rollout integrity checks cardinality, canonical-byte duplication, completeness, task binding, and trajectory-root agreement. CONTRACT-ONLY (CRUCIBLE.md:159-161; parent section 8.20).

In one implementation the reward-distribution gate recomputes reward cardinality, support cardinality, mass at or below the null floor, mass at full reward, median, and observed minimum-to-maximum range. Floor and ceiling masses are counts, not silently normalized probabilities. Exact rational arithmetic avoids a floating-point rounding step moving a bound. ENFORCED (tools/reward_distribution.py, first landed 2026-09-20; tests/test_reward_distribution.py).

The preregistration fixes the closed statistic set and inclusive bounds before any population is observed. The reader refuses an extra statistic, a missing statistic, malformed bounds, a commitment not earlier than the execution interval, or disagreement between committed and attested digests. A changed bound is not a new interpretation of an old commitment. ENFORCED (tools/reward_distribution.py, first landed 2026-09-20; tests/test_reward_distribution.py).

In one implementation an absent preregistration holds while the external-commitment deferral stands, whereas a moved or unordered commitment blocks. The absence branch becomes a block when that deferral no longer applies. An anomalous statistic opens investigation and caps as prescribed, but does not by itself prove exploitation. ENFORCED (tools/reward_distribution.py, first landed 2026-09-20; tests/test_reward_distribution.py); CONTRACT-ONLY (CRUCIBLE.md:159).

An external pre-run commitment must supply authentic temporal order. A local timestamp comparison is not proof of observation order by itself. DEFERRED (DEFERRED.md: "Preregistered exact statistics over the reward population"). The statistic module and its ordering comparator do not manufacture such a commitment.

The reward-claim taxonomy assigns each atomic violated obligation to definition, input, computation, attribution, population, reduction, evidence, or execution. Submission transport belongs to input, membership belongs to population, and capture or custody belongs to evidence. A multi-boundary incident produces separate findings, not one ambiguous owner. CONTRACT-ONLY (CRUCIBLE.md:161); DOC-NORMATIVE (docs/measurement-fidelity.md:184-208).

The current execution boundary supplements the parent's older seven-boundary example rather than importing its older vocabulary unchanged. The coverage ledger maps applicable threats to capability channels; agreement with an author claim never supplies a passing atom. CONTRACT-ONLY (CRUCIBLE.md:140, 161).

### 8.9 Adversary probes against the actual grading path

The adversary family submits probes through the stock delivery-framework path inside the pinned image, never through a special vendor wrapper. In one implementation every committed bundle carrying tests requires the probe matrix. An unrunnable probe blocks instead of disappearing as a benign gap. CONTRACT-ONLY (CRUCIBLE.md:164).

The matrix contains a null submission, negated gold answer, list of private identifiers and line numbers, oracle output with services stubbed, oracle-free workspace with a planted collection hook, per-deliverable garbage beside an oracle, schema-valid but wrong content, and a fabricated trajectory carrying rubric strings. CONTRACT-ONLY (CRUCIBLE.md:164).

In one implementation the null score equals zero, a declared null floor is at most 0.05 and agrees within 0.005 with measured null reward, and other probes remain at or below that floor. The per-deliverable garbage probe instead loses at least the declared discrimination weight. These are numeric acceptance rules, not qualitative reviewer impressions. CONTRACT-ONLY (CRUCIBLE.md:164).

The auditor keeps transform tables, generators, and nonces private and binds measured rows to its verdict. A probe that obtains reward by exploiting the test harness is a finding even if its output has a valid schema. CONTRACT-ONLY (CRUCIBLE.md:164).

The probe runner is not supplied by the inspected statistic or forensic modules. DEFERRED (DEFERRED.md: "Adversary probes run against every shipped verifier"; "Oracle receipts are produced by a deployed external execution service"). The proposed full matrix is not labeled as executed or deployed.

### 8.10 Conformal admission of machine judges

A judge is eligible for audit use only under a predeclared policy evaluated against blinded reference labels. The policy fixes judge identity, model and prompt bindings, reference population, calibration split, required perturbations, repeated presentations, risk level, and admission conditions. Missing empirical coverage produces abstention or blocking rather than an accepted point judgment. CONTRACT-ONLY (CRUCIBLE.md:223, 230; parent section 8.24).

In one implementation declared judgments bind a policy digest, a trial-registry head, every contributing evaluation trial, aggregate scores, a plurality verdict, and a conformal set. Trial rows bind sequence, previous digest, identity, seed, position permutation, output digest, and calibration or evaluation membership. ENFORCED (tools/judge_reliability.py, first landed 2026-09-03; tests/test_judge_reliability.py).

The implementation floor is eleven evaluation trials per declared item and may be tightened by policy. Reversed presentations and repeated case-variant presentations are also required, so reaching the floor alone does not qualify a record. Cohen's kappa compares calibration verdicts with reference labels, and an exact paired McNemar test diagnoses position bias. ENFORCED (tools/judge_reliability.py, first landed 2026-09-03; tests/test_judge_reliability.py).

For split conformal prediction, calibration nonconformity is one minus the score assigned to the reference label. The quantile rank is the ceiling of the calibration size plus one multiplied by one minus the declared error level. A rank beyond the calibration size includes every label rather than manufacturing certainty. The candidate prediction set must equal the singleton aggregate verdict. ENFORCED (tools/judge_reliability.py, first landed 2026-09-03; tests/test_judge_reliability.py).

In one implementation the refusal vocabulary is `JUDGE_TRIAL_REGISTRY_MISSING`, `JUDGE_TRIAL_REGISTRY_MALFORMED`, `JUDGE_TRIALS_UNDER_MINIMUM`, `JUDGE_POSITION_RANDOMIZATION_INVALID`, `JUDGE_RELIABILITY_BELOW_POLICY`, `JUDGE_CONFORMAL_CALIBRATION_INVALID`, `JUDGE_PREDICTION_SET_UNRESOLVED`, and `JUDGE_PERTURBATION_FAILED`. The present exact position-bias evaluator requires a binary label policy. ENFORCED (tools/judge_reliability.py, first landed 2026-09-03; tests/test_judge_reliability.py).

Conformal-set construction is not identical to every conformal risk-control method. The described split-conformal implementation is a concrete admission component; a general risk-control deployment policy must state its loss, calibration assumptions, and coverage criterion. Exchangeability and label blinding cannot be inferred from a valid local registry. PROSPECTIVE applies to that complete independently grounded admission boundary.

A further diagnostic records pairwise preference cycles over predeclared comparison triples and counts transitivity violations. It can refuse admission above a fixed policy tolerance but cannot promote a disposition. This extension is PROSPECTIVE: no transitivity evaluator or dedicated assertion appears in the inspected judge module and its test file.

DEFERRED (DEFERRED.md: "Judge reliability for judged scores not declared in `.audit/judgments.jsonl`"; "Conformal prediction sets for judged scores not declared in `.audit/judgments.jsonl`") preserves declaration completeness. A record checker returning no findings for an absent registry does not prove that no unregistered score exists.

DEFERRED (DEFERRED.md: "Independent judge replay covers every judged score") preserves the independently governed replay runner. Pinning model, prompt, reducer, temperature, seed, complete transcript, and trial rows is required support, not a claim that external replay occurs. Deterministic failure retains precedence over a rubric pass.

### 8.11 Rubric drafting-provenance isolation

A rubric compiler operates in an execution domain isolated from oracle-solution provenance. It receives committed task bytes and formal scoring criteria through an allowlisted interface, then commits the rubric digest before receiving solver trajectories to be judged. A rubric whose drafting provenance includes an oracle solution or excluded author explanation is refused. CONTRACT-ONLY (parent section 8.23; CRUCIBLE.md:152, 219).

The compiler partitions criteria into deterministic relations and semantic residue. A criterion reducible to an executable relation over committed evidence becomes a compiled test; a judged item records why it cannot be compiled. Compiled item and test identifiers reconcile in both directions. CONTRACT-ONLY (CRUCIBLE.md:152, 204; parent section 8.23).

In a proposed admission implementation, a provenance manifest binds input digests and the compiler identity, and a receipt binds the rubric digest before opening the trajectory input channel. Any rubric edit requires a new commitment and cannot retroactively grade trajectories already exposed to the drafting domain under the prior commitment. PROSPECTIVE.

Deterministic regeneration may read a frozen criterion literal, but cannot invoke a model, network, clock, or random source to choose a replacement at replay time. Reproducibility of a frozen literal does not prove that it is the first draft. CONTRACT-ONLY (parent section 8.23).

The inspected rubric family contract supports schema and replay obligations, not an implemented isolated drafting service. The full provenance reader and temporal input-channel enforcement remain PROSPECTIVE. This disclosure does not infer provenance isolation from a directory name or a digest alone.

### 8.12 Auditor evidence surface and hardness-citation refusal

The auditor's review consumes its committed evidence surface rather than author difficulty claims. In one implementation that surface is `.audit/evidence.yaml`. The hardness contract and generated hardness sheet are outside the permitted audit evidence sources because they reveal intended design targets. CONTRACT-ONLY (CRUCIBLE.md:166, 183, 219).

In one implementation `check_audit_forbidden_paths` in tools/integrity.py scans recognized evidence file types below the audit root and calls `forbidden_audit_citations` on searchable lines. It refuses citations to `.memory/hardness.yaml` or `HARDNESS.md` as `AUDIT_FORBIDDEN_PATH_CITATION`. ENFORCED (tools/integrity.py, first landed 2026-06-24; tests/test_barrier.py).

The scanner treats symbolic links and unreadable evidence as unscannable. Markdown search excludes fenced examples and comments; other recognized evidence formats are searched directly. Its clean and planted tests establish this narrower lexical policy, not complete prevention of all covert information transfer. ENFORCED (tools/integrity.py, first landed 2026-06-24; tests/test_barrier.py).

A citation refusal prevents reliance on the offending audit evidence. It does not prove that a human or runtime never reads the forbidden source, and the absence of a citation cannot prove confidentiality. DEFERRED (DEFERRED.md: "A full clone does not enforce the information barrier between humans").

The corresponding fidelity firewall exposes permitted conformance tokens and a ledger digest but withholds detector outcomes and reason-specific counts from the author. A reason that leaks through an identifier is also an output-channel concern. ENFORCED (tools/forensics/ledger.py, first landed 2026-09-18; tests/test_forensics_family.py); DOC-NORMATIVE (docs/measurement-fidelity.md:210-224) governs complete least-privilege routing.

### 8.13 Named prior art and novelty residue: OWASP Benchmark, conformal arXiv work, and related controls

For both-halves liveness, OWASP Benchmark's true-positive and false-positive twin corpus and muSE mutation-based soundness work in TOSEM 2021 already test detector behavior. Mutation adequacy alone is not asserted as new. The novelty residue proposed here is common-run twin-fixture liveness scoped to required grounding families, with failed discrimination blocking the audit and a coverage-sensitive forensic reader preventing false-clean certification.

For the grounding-family registry, OWASP Benchmark and StaAgent, arXiv 2507.15892, provide adjacent evaluation and agent-testing context. The novelty residue is the coupled no-uplift registry, required-family liveness, pinned hermetic input closure, and dual-host byte-identical regeneration, not the individual act of replaying a checker.

For execution fidelity, harness disclosure arXiv 2605.23950 and StaAgent arXiv 2507.15892 supply adjacent harness and execution context. The novelty residue is a native-format coverage reader with an explicit insufficient-evidence ceiling, where absence never proves clean and every required signal needs coverage, combined with bounded no-follow filesystem access and ledger confinement.

For the measurement taxonomy and symmetric cap, harness disclosure arXiv 2605.23950 and SLSA provenance assurance levels address related reproducibility and assurance concerns. The novelty residue is separating physical mechanism, statistical consequence, and missing control while coupling suppressing or unproved execution to a non-releasing state and separating configuration approval from substantive adequacy. SLSA levels are not an execution-validity taxonomy.

For contamination screening, OWASP Benchmark provides the twin-control comparison and the parent register identifies provenance frameworks including SLSA. The novelty residue is not generic similarity search; it is immutable baseline preservation, calibrated-floor screening without a family exemption, independent atom recomputation, and retained shipped-under evidence that never certifies permanent absence.

For reward integrity, muSE TOSEM 2021 and OWASP Benchmark supply mutation and control-testing comparisons. The novelty residue is a closed statistic set and its bounds committed before population observation, joined to same-run liveness and an audit cap; exact arithmetic or a distribution summary alone is not the proposed distinction.

For adversary probes, StaAgent arXiv 2507.15892 and OWASP Benchmark make broad adversarial testing a substantial obviousness consideration. The novelty residue is the fixed numeric discrimination rules applied through the delivered grading path, with an unrunnable required probe blocking and its transforms excluded from author feedback.

For judge admission, Angelopoulos et al., conformal risk control, arXiv 2208.02814, and Gupta and Kumar, arXiv 2604.15302, supply conformal and transitivity context. Reliability without Validity, arXiv 2606.19544, and Coin Flip Judge, arXiv 2606.13685, caution against agreement as validity. The novelty residue is predeclared conformal admission on blinded labels as an operational deployment gate rather than a diagnostic, coupled to deterministic liveness and coverage refusal.

For rubric provenance, Reliability without Validity, arXiv 2606.19544, and Coin Flip Judge, arXiv 2606.13685, provide the adjacent validity problem. The novelty residue is an input-isolated compiler that commits a rubric digest before trajectories are accessible and refuses oracle-solution or excluded-explanation provenance, not the generation of rubric prose by a model.

For auditor evidence isolation, the register's Fides information-flow work, arXiv 2505.23643, and SLSA provenance provide adjacent access and evidence models. The novelty residue is the named hardness-source citation refusal on the auditor's own evidence surface, joined to a private coverage ledger, rather than an assertion that a lexical scanner implements a complete information-flow system.

These comparisons rely on the supplied local prior-art register and are drafting positions, not novelty or freedom-to-operate opinions. No network retrieval occurs in this lane. The optional double-measurement-confound paper, arXiv 2609.09218, is not independently read here and supplies no novelty premise. Human claim-specific review must resolve dates, actual disclosures, combination motivation, and support before filing.

### 8.14 Scope, single-actor operation, and the permanently human acts

One audit-platform operator may perform or cause every recited computing operation through separately permissioned processes. External evidence and human adequacy grants are inputs to verification; the claims do not require the auditor to manufacture those inputs. Organizational separation can exist within one legal operator, but independence still requires actual authority and access restrictions rather than different labels.

File names, paths, refusal codes, family codes, schema identifiers, trial counts, vocabulary sizes, and numeric floors describe implementations only. The claims use functional relations and bound policies rather than those names or literal counts. A substitute hash, runtime, or sandbox can implement the same byte-binding and refusal relations.

The drafting party reconciles and never files. Filing is a human act; no auditor, model judge, conductor, or approval workflow discharges it. Publication outside the repository, operational acceptance against a cap, and admission into human-graded reference material also remain human decisions. No statement asserts any filing, deployment, or measured pass rate.

ENFORCED labels identify local predicates, CONTRACT-ONLY labels identify stated obligations, DOC-NORMATIVE labels identify normative document definitions and rules rather than executable enforcement, and DEFERRED labels retain their missing dependencies. PROSPECTIVE embodiments describe how the remaining mechanisms would operate. Their coexistence is not a representation that the complete claimed system is operational.

### 8.15 Prevention register and technical effects

| Claims | Prevention verb | Machine object and enforced relation in the claimed embodiment | Evidence boundary |
| --- | --- | --- | --- |
| 1, 22, 24 | Prevent reliance; block | Audit outcome cannot rely on an instrument failing its frozen twin pair | Complete universal gate is contract-only |
| 1, 22, 24 | Refuse; require | A clean execution record requires affirmative coverage for every signal | Local forensic reducer exists |
| 1, 16-18, 22, 24 | Abstain; prevent admission | A judged score cannot enter audit evidence without required conformal coverage | Declared registry checks exist; deployment and transitivity are not established |
| 4, 5, 26 | Reject; confine | Native evidence reads cannot follow untrusted links or escape the audit ledger boundary | Local descriptor and ledger checks exist |
| 6, 7, 23, 28 | Cap; reconcile | Suppression cannot create a clean trial or shrink the committed denominator | Local validation exists; independent execution remains external |
| 14 | Bind; refuse | Statistic bounds cannot change after observation under the accepted commitment | Arithmetic and comparisons exist; authentic commitment producer is deferred |
| 19 | Withhold; prevent use | Trajectories cannot inform a rubric digest committed earlier | Isolated compiler is prospective |
| 20, 25 | Refuse; withhold | Forbidden design citations and detector details cannot supply permitted author-facing evidence | Narrow citation and projection checks exist |

Under Alice Step 2A Prong Two, claims 1, 22, and 24 integrate statistical judging into specific byte-reading and certification-state operations. The claimed benefit is prevention of false-clean certification by changing which evidence can operate a machine gate. Under Step 2B, the proposed ordered combination is the argument, not generic processors, AI, or confidence calculations individually. Eligibility remains subject to legal review.

Under EPO Art. 52 and Guidelines G-II 3.3 and 3.3.1, deterministic verification of evaluation evidence and prevention of false-clean certification are the asserted technical purposes. Conformal calculations decide admission of machine-generated grading evidence; no-follow reads resist path substitution; twin execution tests whether required verification code can discriminate. No measured speed, accuracy, or deployment result is asserted.

For India s.3(k), independent claim 1 addresses the technical problem of false-clean execution evidence entering an automated certification path. Its technical solution couples live executable controls, coverage-sensitive reading, and conditional judge admission. The measurable technical benefit would be refusal of planted invalid or uncovered evidence while preserving the corresponding valid branch, in the technical-effect vocabulary of Ferid Allani and Microsoft v. Assistant Controller; no novel hardware is required and no numerical benefit is asserted.

For India s.3(k), independent claim 22 addresses the same technical problem through a processor-executed sequence that blocks instrument reliance, derives coverage standing, and denies unsupported judge admission. Its measurable technical benefit would be prevention of invalid certification-state transitions under matched defective and valid inputs, not improved subjective grading. The method requires no novel hardware; the Ferid Allani and Microsoft v. Assistant Controller analysis remains claim-specific.

For India s.3(k), independent claim 24 stores instructions that implement those controls over native evidence and audit state. The technical solution is the programmed evidence-admission path, and its measurable technical benefit would be a refusal when coverage or liveness is missing instead of a false clean record. Consistent with Ferid Allani and Microsoft v. Assistant Controller, the argument rests on technical effect rather than a novel storage device or algorithm in isolation.

## 9. CLAIMS

What is claimed is:

**1. A system for controlling audit certification of executable evaluation tasks, comprising:** one or more processors; one or more non-transitory memories storing instructions that cause the processors to receive committed task bytes, a required-instrument registry, frozen fixture pairs, execution traces, and a predeclared judge policy; execute each required deterministic grounding instrument against a planted-defect fixture and a corresponding clean twin during a common audit run, prevent reliance on the instrument unless it detects the planted defect and refrains from detecting that defect on the clean twin, and force a blocking disposition when either requirement fails; resolve each execution-fidelity detector to exactly one of observed violation, demonstrated coverage without violation, or insufficient evidence, prohibit treating absence of a marker as cleanliness, and permit a clean rollout determination only upon demonstrated coverage of every required signal class without a violation; evaluate a machine judge against blinded reference labels under a predeclared conformal risk-control procedure and admit its judgment to audit evidence only when the procedure establishes required empirical coverage, otherwise forcing abstention or a blocking disposition; and prevent audit certification based on an instrument, rollout determination, or judgment that fails the corresponding prerequisite.

**2.** The system of claim 1, wherein the registry includes delivery-conformance, reference-fidelity, calibration, verifier-robustness, rubric-compilation, contamination-screening, reward-integrity, and budget-conformance families whose instruments operate as deterministic functions of pinned input closures in a hermetic sandbox and can only lower or cap the disposition.

**3.** The system of claim 2, wherein a regeneration instrument executes a committed generator under differing host, working-directory, user, and environment identities, compares regenerated ground-truth and checker-fixture bytes with each other and committed bytes, and refuses reliance upon byte inequality.

**4.** The system of claim 1, wherein the execution traces are read by retaining a trusted directory descriptor and opening each successive path component relative to its retained parent without following symbolic links, rejecting traversal outside a trusted root and rejecting a nonregular final object.

**5.** The system of claim 4, wherein a fidelity ledger writer accepts only an audit-owned root or a validated run namespace beneath that root and refuses a candidate-selected directory merely bearing an audit-root name.

**6.** The system of claim 1, wherein a suppressing execution violation or absence of demonstrated fidelity coverage imposes a suppressed-measurement hold independently of solver success, and an unprovable measured population forces a blocking disposition.

**7.** The system of claim 6, wherein the processors reconcile a versioned configuration pin against effective configuration evidence, refuse an unpinned, unapproved, inadequate, or drifted configuration, and require an adequacy approval from a human governance source separate from configuration identity approval.

**8.** The system of claim 2, wherein contamination exclusion checks canonical repository identity, ancestor membership, and base-commit membership against an immutable exclusion baseline that a client extension cannot remove.

**9.** The system of claim 8, wherein freeze screening compares an independently attested task-generating event with each applicable versioned cutoff and refuses a declaration inconsistent with that attestation.

**10.** The system of claim 8, wherein near-duplicate screening compares bound representations under bound normalizations against a calibrated detection floor and routes a review-band match to recorded adjudication that cannot certify absence.

**11.** The system of claim 8, wherein sanitization checks an image-bound agent-visible closure including unpacked image layers and deletion markers rather than relying solely on a merged filesystem.

**12.** The system of claim 8, wherein empty-submission screening requires a no-change submission to leave intended repair targets unresolved.

**13.** The system of claim 8, wherein provenance screening refuses unknown carrier fields and recomputes a binding block over the same canonical bundle domain as an independent leak check, with no family-wide exemption from the contamination checks.

**14.** The system of claim 2, wherein a reward-distribution instrument requires a commitment before population observation to bounds for reward cardinality, support cardinality, null-floor mass, full-reward mass, median, and range, recomputes those statistics using exact rational arithmetic, and refuses a changed commitment or a missing or additional statistic.

**15.** The system of claim 2, wherein adversary probes exercise null, negated-answer, identifier-list, service-stubbed oracle, planted-hook, per-deliverable garbage, schema-valid wrong-content, and fabricated-trajectory submissions through the delivered grading path against bound numeric acceptance rules, and an unrunnable or over-rewarded required probe forces a blocking disposition.

**16.** The system of claim 1, wherein judge admission requires a policy-bound minimum repeated-trial count per item, randomized alternative positions, required perturbations, and a recomputed conformal prediction set equal to a singleton aggregate verdict.

**17.** The system of claim 16, wherein the processors compute Cohen's kappa against the blinded reference labels and an exact paired McNemar diagnostic over reversed presentations and refuse admission upon an undefined diagnostic or a policy-bound reliability failure.

**18.** The system of claim 16, wherein the processors record transitivity violations in predeclared pairwise-comparison triples and refuse admission when the violations exceed a predeclared tolerance without allowing the diagnostic to raise disposition.

**19.** The system of claim 1, wherein a rubric compiler isolated from oracle-solution provenance receives committed task bytes and formal scoring criteria, commits a rubric digest before receiving judged solver trajectories, and prevents use of a rubric whose drafting provenance includes an oracle solution or an excluded author explanation.

**20.** The system of claim 1, wherein an auditor evidence scanner refuses an evidence line citing an author hardness contract or a generated representation of that contract as a basis for an audit conclusion.

**21.** The system of claim 1, wherein an admitted machine judgment can lower or cap a disposition but cannot raise it above deterministic evidence or substitute for a missing required deterministic instrument.

**22. A computer-implemented method for controlling audit certification of executable evaluation tasks, comprising:** receiving, by processors, committed task bytes, a required-instrument registry, frozen fixture pairs, execution traces, and a predeclared judge policy; executing each required deterministic grounding instrument against a planted-defect fixture and a corresponding clean twin during a common audit run, preventing reliance unless the instrument detects the planted defect and refrains from detecting that defect on the clean twin, and forcing a blocking disposition when either requirement fails; resolving each execution-fidelity detector to exactly one of observed violation, demonstrated coverage without violation, or insufficient evidence, prohibiting a clean conclusion from absence of a marker, and determining a rollout clean only upon demonstrated coverage of every required signal class without a violation; evaluating a machine judge against blinded reference labels under a predeclared conformal risk-control procedure, admitting its judgment only when required empirical coverage is established, and otherwise forcing abstention or a blocking disposition; and preventing audit certification based on an instrument, rollout determination, or judgment that fails the corresponding prerequisite.

**23.** The method of claim 22, further comprising deriving trial conformance independently of success, retaining nonconforming and indeterminate trials in a fixed precommitted population, and assigning a worst-case group indicator rather than excluding such trials before a certification-bound calculation.

**24. A non-transitory computer-readable storage medium storing instructions that, when executed by processors, cause the processors to control audit certification of executable evaluation tasks by operations comprising:** receiving committed task bytes, a required-instrument registry, frozen fixture pairs, execution traces, and a predeclared judge policy; executing each required deterministic grounding instrument on a planted-defect fixture and a corresponding clean twin during a common audit run, preventing reliance unless the planted defect is detected and that defect is not detected on the clean twin, and forcing a blocking disposition when either requirement fails; resolving each execution-fidelity detector to exactly one of observed violation, demonstrated coverage without violation, or insufficient evidence, prohibiting cleanliness inferred from absence of a marker, and permitting a clean rollout determination only upon demonstrated coverage of every required signal class without a violation; evaluating a machine judge against blinded reference labels under a predeclared conformal risk-control procedure and admitting its judgment only upon established required empirical coverage, otherwise forcing abstention or a blocking disposition; and preventing audit certification based on an instrument, rollout determination, or judgment that fails the corresponding prerequisite.

**25.** The storage medium of claim 24, wherein the instructions cause a private fidelity ledger to retain detector reasons and cause an author-facing projection to disclose only permitted trial-conformance tokens and a binding digest while withholding detector outcomes and reason-specific counts.

**26.** The system of claim 4, wherein trace discovery and reading enforce predeclared entry, depth, rollout, and byte limits and resolve exceeded limits as unavailable evidence rather than silently omitting evidence and returning cleanliness.

**27.** The system of claim 1, wherein the frozen fixture manifest binds instrument identities, paired fixture digests, expected normalized outcomes, and a non-production designation, and a changed fixture invalidates the prior liveness qualification.

**28.** The system of claim 6, wherein faithful enforcement of an approved timeout or turn cap remains conforming independently of solver success, while an undeclared or unapproved suppressing transformation prevents a conforming determination.

## 10. ABSTRACT OF THE DISCLOSURE

A computing system controls audit certification of executable evaluation tasks using coupled instrument and evidence prerequisites. Each required deterministic grounding instrument must detect a planted-defect fixture and refrain from detecting the defect on a corresponding clean twin during a common run. A failed half blocks reliance. Native execution-trace readers distinguish observed violation, demonstrated coverage without violation, and insufficient evidence, and never infer cleanliness from an absent marker. A judge-admission gate evaluates a machine judge against blinded reference labels under a predeclared conformal procedure and abstains or blocks without required coverage. Further controls bind effective harness configuration, preserve a fixed measured population, preregister reward statistics, isolate rubric drafting before trajectory exposure, and refuse forbidden design-source citations in audit evidence. Bounded descriptor-relative reads protect evidence access, while deterministic and semantic findings may only lower or cap a disposition.
