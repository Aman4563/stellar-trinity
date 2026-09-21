# Trinity measurement fidelity

## Purpose and scope

This document fixes the closed taxonomy of measurement slippage: the ways a pilot reports a number that is not the number it claims to report. It keeps three questions apart. Axis A asks what physically happened to the solver. Axis B asks what that does to the estimate. Axis C asks which control would have caught it. Collapsing the three axes into one list is the defect this taxonomy exists to prevent, because a mechanism is not a consequence and neither one is a control.

The document is normative for spelling and silent on authority. Every closed vocabulary below is the single source that FORGE.md, CRUCIBLE.md, and the pilot, harness-configuration, and forensics modules copy byte for byte. Nothing here asserts that a fidelity detector, an independent execution authority, or an independent runner exists. Each one remains an obligation stated and unenforced. A control this document names as missing stays missing until code evaluates its predicate.

## The incident restated as a measurement defect

A vendor inference harness auto-compacted agent context mid-rollout. The ground truth is one line of a raw agent log, `agent.jsonl:174`, carrying `{"type":"system","subtype":"compact_boundary","compact_metadata":{"trigger":"auto","pre_tokens":168780}}`. In the kakashi delivery, 11 of 24 runs compacted across 18 events, every one at `trigger:auto`, with `pre_tokens` between 167,075 and 173,539. That band matches a declared `contextWindowTokens` of 200,000 less a `maxOutputTokens` of 32,000, which leaves 168,000 tokens of headroom.

The normalized marker "This session is being continued from a previous conversation that ran out of context" appears in 57 of 344 normalized trajectory files, 16.6 percent, across the anubis, envora, kakashi, and yuji deliveries. Rollouts of glm-5.3 inherit that marker through a Claude-Code protocol bridge, reached by an ANTHROPIC_BASE_URL override pointing at cc-bridge-internal on port 8765. The marker therefore crosses model families, and a reader keyed to one family misses it.

The decisive observation is a false negative. The field `result.json.agent_result.metadata.summarization_count` is 0 in all 296 result files, because `enable_summarize` is false. A detector reading the result file reports zero compaction, and that report is wrong while the raw log proves compaction happened. A self-reported zero is not evidence of absence. Absence of a record is not a record of absence. That single rule is what this taxonomy encodes, and every three-valued outcome below exists to hold it.

## Direction of harm

FORGE rule 2f releases a slot only when the Bonferroni-corrected Clopper-Pearson upper bound on every primary solver's pass-at-8 rate stays strictly below the measured pass ceiling, whose default is 0.40. The pilot evaluator today sums solver outcomes unconditionally and refuses on a headroom breach. That gate is one-sided. Harness-suppressed capability lowers measured success, which lowers the upper bound, which crosses below the ceiling, which releases the task.

Suppression is therefore an adversarial vector with a free win and not a quality nuisance. The symmetric counterpart does not exist yet. `HOLD:MISCALIBRATED` fires only when a task measures easier than declared, and no disposition fires when a task measures harder than it truly is. Making a task look harder is what earns release, so a refusal keyed on suppression has to be mandatory and never advisory.

## Axis A, the mechanism

Every row names what physically happens, the evidence for it, its Axis B consequence, and the Axis C control that would have caught it. A row whose evidence column says no corpus instance is named for closure and carries no observation behind it.

| Id | Mechanism | What physically happens | Evidence | Axis B | Axis C |
| --- | --- | --- | --- | --- | --- |
| A1 | Auto context compaction | The harness summarizes and discards earlier context mid-rollout without the solver's consent | `compact_boundary` at `agent.jsonl:174` with `trigger:auto` and `pre_tokens` 168780; 11 of 24 kakashi runs across 18 events at `pre_tokens` 167,075 to 173,539; 168,000 tokens of headroom from 200,000 less 32,000; the normalized marker in 57 of 344 trajectory files | B1 | C1, C3, C6 |
| A2 | Per-message observation truncation | Each tool observation is cut to a byte ceiling before the solver reads it | teresa `llm_config.max_message_chars` of 30000, with no per-message record of what was cut | B1 | C1, C2 |
| A3 | Turn or iteration cap | The rollout halts at a step ceiling before the solver finishes | `max_turns` of 300 to 1000 and `max_iterations` of 200 across the corpus, none reconciled against a declared turn horizon | B1 | C2, C5 |
| A4 | Wall-clock timeout | The rollout halts at a time ceiling | Harbor terminal-bench-science commit `deef067` excludes timeout trials, so the field already treats a timeout as its own class and not a failure | B1, B4 | C2, C4 |
| A5 | Provider error masked by retry | A rate-limit or server error is retried until it leaves no trace in the record | `num_retries` of 4 with no per-attempt record, which masks 429 responses | B1, B5 | C1, C5 |
| A6 | Safety-classifier refusal or session latch | A policy classifier refuses, and the refusal latches for the remainder of the session | the client feedback register at lines 151 and 277 | B1, B3 | C5, C7 |
| A7 | Setup or environment failure | The task environment never reaches a runnable state and the rollout is scored anyway | setup failures scored as failures, delivery QA review section 6.3 | B4, B5 | C5, C7 |
| A8 | Submission or scoring handoff loss | The solver's final answer is altered or lost between the solver and the scorer | no family in the corpus records the submitted bytes on the wire; the four on-disk families record only the agent's own log, and one of them is a conversion product | B5 | C3, C7 |
| A9 | Reasoning-effort or fallback-routing degradation | The provider serves a weaker model, a lower effort setting, or a fallback route than the declared one | model-id inconsistencies such as anthropic/glm-5/3; Harbor and claude-code version drift, delivery QA review section 5.2; judge temperature and seed unpinned, `DEFERRED.md:164` | B1, B2 | C1, C7 |
| A10 | Cross-rollout state contamination | State from one rollout survives into the next, so two trials share one cause | the session latch that outlives a single rollout, client feedback register lines 151 and 277 | B3, B4 | C4, C7 |

The corpus carries four distinct on-disk schema families, which is why Axis A needs a per-family reader and not one global grep: Harbor ATIF version 1.7 with `config.json` and `result.json`; deku with `usage.json` beside a normalized trajectory directory; kakashi cybergym with `usage.json` beside a raw agent log; and teresa native OpenHands with `run-metadata.json`, `metrics.json`, and `condenser_config`.

## Axis B, the statistical consequence

| Id | Consequence | Effect on the estimate | Direction |
| --- | --- | --- | --- |
| B1 | Suppresses measured capability | Measured success falls below true capability, so the Clopper-Pearson upper bound moves down | Toward release, which is what makes this axis adversarial |
| B2 | Inflates measured capability | Measured success rises above true capability, so the upper bound moves up | Away from release, and already covered by `HOLD:MISCALIBRATED` |
| B3 | Destroys trial independence | Trials share a cause, so the binomial model behind the bound no longer holds | The bound stops being a bound |
| B4 | Corrupts the population definition | Which rollouts belong to the measured set is settled after outcomes are visible | Unprovable population, which is `BLOCK:INVALID_PILOT` |
| B5 | Makes the estimand undefined | No quantity is being estimated, because the trial never measured the declared task | No measurement at all |

## Axis C, the missing control

| Id | Control | What it would have caught | Carrier | Standing |
| --- | --- | --- | --- | --- |
| C1 | Effective-configuration pinning | A configuration that was never declared, drifted after approval, or differed from the attested effective one | `trinity.harness-config/v1` bound in `harness/` and mirrored to `.seed/harness-config.json`, reconciled into `trinity.execution/v2` | schema is mechanizable; the pin is unenforced today |
| C2 | Configuration adequacy approval | An approved, pinned, reproducible configuration that is still too small for the declared horizon, such as 168,000 tokens of headroom for a 300-turn task | a `configurationAdequacy` block naming an approving authority in `requirements/` or a recorded `touchstones/` disposition | not machine-decidable; the judgment stays human |
| C3 | Native-trace observation before operator editing | A trace the operator could have edited, stripped, converted, or swapped before it was captured | the observation duty of an independent execution authority | no such authority exists |
| C4 | Precommitted population roster | A group set chosen after outcomes were visible, and a replacement run that erased an original group | the admission duty of the same authority, reconciled against the realized groups | no such authority exists |
| C5 | Per-trial conformance classification | A trial counted as a clean observation when the approved policy was violated or unproven | `trialStatus` on every rollout, derived by CRUCIBLE under `trinity.trial-conformance/v1` | vocabulary fixed here; derivation unbuilt |
| C6 | Three-valued coverage refusal | A missing marker, an unsupported harness version, or a conversion-only trace resolving as clean | the forensics adapters, their coverage predicate, and the private `.audit/fidelity.yaml` | vocabulary fixed here; adapters unbuilt |
| C7 | Independent execution authority | A pilot whose population, configuration, capture, and custody are all operator-asserted | admission, execution, observation, and custody duties held by neither author nor auditor | absent, and the minimum replacement is independent re-execution |

## Verified structural gaps

This table preserves the pre-change diagnosis rather than asserting that every gap remains present. The line numbers below are advisory. Each one is re-derived by grepping the cited text before any edit, because the surrounding contracts move. Status as of 2026-09-18: G1, G5, G7, and G12 are resolved by the commits named below. The other rows remain in the register and are not closed by this context sweep; retained diagnosis is not a claim that subsequent code or contract changes never occurred.

| Id | Gap | Evidence | Status as of 2026-09-18 |
| --- | --- | --- | --- |
| G1 | Historical diagnosis: zero mentions of compaction, compress, condens, context window, max turns, tool error, rate limit, system prompt, invalid trial, or trial status in any contract or anywhere under the tools tree | `8a5ab04` (execution-fidelity boundary) and `9fe4c4f` (three-valued fidelity core); original evidence was repository-wide grep | Resolved |
| G2 | Harness configuration is prose with no schema and nothing that verifies it | `FORGE.md:163` item 9l, an author probe only; `FORGE.md:293` Phase 4 item 3, naming fixed adapters, model list, budgets, temperatures, retry policy, rollout count, and health checks; `FORGE.md:344`, temperature matched between probe and pilot | Retained diagnosis, not closed by this sweep |
| G3 | Exactly one suppression rule exists and it covers only budget | `FORGE.md:297` item 4c: a pilot run under a budget smaller than the declared budget hours starved the frontier of its horizon and measured a weaker frontier, capping at `HOLD:PILOT_REQUIRED` with reason `budget-uncovered` | Retained diagnosis, not closed by this sweep |
| G4 | The harness tree is the natural home for a declared execution policy and carries none | `FORGE.md:182` item 1b: FORGE alone generates every byte, the agent under test sits behind a pinned vendored interface, every dependency is pinned, and the image digest is bound at Phase 4.5 | Retained diagnosis, not closed by this sweep |
| G5 | Historical diagnosis: the execution predicate version 1 carries no harness configuration and no per-rollout telemetry, and its parser uses closed field-set equality, so any addition needs a new predicate version | `c8f01d7` (execution/v2 telemetry) and `3c5502d` (v1 release refusal); original evidence: `trinity/tools/attest/intoto.py:111-121`, `:44`, `:614` | Resolved |
| G6 | No pass-at-k function exists anywhere, so pass-at-8 is a label and not a computation | `trinity/tools/stats.py` exposes only Clopper-Pearson, its upper bound, Bonferroni correction, a lot-defective bound, and a per-rollout minimum | Retained diagnosis, not closed by this sweep |
| G7 | Historical diagnosis: the pilot policy and pilot attempt predicates at version 1 have no per-trial validity and no group structure | `41b801b` (pilot-policy/v2 fixed groups) and `a3bb81f` (pilot-attempt/v2 conformance); original evidence: `trinity/tools/pilot.py:28-29`, `:37-67` | Resolved |
| G8 | Trajectory bytes are opaque and only digests are checked | `trinity/tools/attest/policies/execution.py:167-201`; `trinity/docs/trajectory-merkle.md:7` and `:86` disclaim trajectory semantics and execution validity, and the fixture rollout body is a two-token stub | Retained diagnosis, not closed by this sweep |
| G9 | The rollout-integrity instrument recomputes cardinality, deduplication, completeness, schema, binding, and the Merkle root, and nothing about execution validity | `CRUCIBLE.md:159` | Retained diagnosis, not closed by this sweep |
| G10 | The 22-entry reward-hacking taxonomy already names failure coercion, temporal or stochastic manipulation, cross-rollout interference, selective inclusion, and metric distortion; what is missing is a boundary that operationally establishes faithful solver exposure | `CRUCIBLE.md:161`; `FORGE.md:183` capability channels are read, write, execute, network, environment, timing, ipc, and resource, with no context channel | Retained diagnosis, not closed by this sweep |
| G11 | One clause reads as a conflict with the auditor's retention surface and is not one; it binds the FORGE lane and the `.seed/` surface, never the auditor | `FORGE.md:307`, `CRUCIBLE.md:160`, `CRUCIBLE.md:165` | Retained diagnosis, not closed by this sweep |
| G12 | Historical diagnosis: five mandatory core controls existed and none covered execution fidelity | `2b4d209`: oracle-run/v4 and release-policy/v3 require six core controls including execution_fidelity; original evidence: `trinity/tools/release_evidence.py:70-78`, `:47-48`, `:444-449` | Resolved |
| G13 | A firewall check that refuses per-rollout timing terms in the author contract exists and works; the equivalent for detector outcomes did not | `trinity/tools/integrity.py:693-698`, `:1561-1583`, `:1544-1559` as the mirror-image precedent | Retained diagnosis, not closed by this sweep |

## The arithmetic finding

For a group tally with zero flagged groups, the one-sided Clopper-Pearson upper bound is closed form. Write alpha for the per-comparison error rate, c for the ceiling, and N for the group count.

```text
U(0, N) = 1 - alpha^(1/N).

Release requires U < c, which solves to N > ln(alpha) / ln(1 - c).
```

At a ceiling of 0.40 and familywise alpha of 0.05, the required group count rises with the comparison family.

| Comparison family M | Alpha per comparison | Required N | Eight groups sufficient |
| --- | --- | --- | --- |
| 1 | 0.05 | 6 | yes |
| 4 | 0.0125 | 9 | no |
| 7 | 0.00714 | 10 | no |
| 8 | 0.00625 | 10 | no |
| 16 | 0.003125 | 12 | no |

M is the attempt budget times the count of primary solvers, so any realistic pilot reaches an M of at least 4. Eight groups can never clear the ceiling, even on a flawless pilot where every group fails. The contract's hardcoded eight therefore becomes a computed floor, `minimum_groups(ceiling, familywise_confidence, comparisons)`, and never fewer than eight. This defect is independent of compaction and is load-bearing for the release rule on its own.

## The exact release rule

Fix the population before any outcome is observed: predeclared disjoint groups of exactly eight independent rollouts, the group count N, the permitted looks, and the comparison family M. Classify conformance independently of success.

```text
Z*_g = 1 when any member of group g is a verified success or any member is not conforming, else 0.

X* = the sum of Z*_g over the fixed N groups.

U = Beta^-1(1 - alpha / M; X* + 1, N - X*), and U = 1 when X* = N.

Release iff U < c for every required solver, with c at most the measured pass ceiling.
```

- Invalid groups are never removed from N. The worst-case indicator makes suppression push the bound up, which reverses the incentive that made suppression profitable.
- Integrity failures block independently of U. A bound computed over unprovable bytes is arithmetic and not evidence.
- A governance-owned maximum affected-group fraction classifies excess as suppressed or unverified, never as underpowered.
- Pre-execution feasibility is the condition U(0, N) < c, checked at parse time before any outcome is read.
- Replacement runs never erase original groups. Both the original and the replacement stay in the fixed population.
- Exclude-then-impute is forbidden. A descriptive valid-only rate may be reported and never authorizes release, and no code path lets it reach the ceiling comparison.
- Eight runs per configuration in the vendor delivery is one pass-at-8 group and not eight groups, so the historical evidence already fails this rule before compaction is considered.

The unbiased combinatorial estimator behind pass-at-k is the one from arXiv 2107.03374, computed in exact rationals so a float rounding step cannot move a release decision.

## Three-valued detector standing

Detector acceptance is three-valued and never two-valued, because native logs are operator assertions. An operator can strip markers, run a marker-less harness, submit logs from another execution, lose fidelity in conversion, or self-report zeros. The three values are VIOLATION for an observed violation, COVERED_CLEAN for demonstrated coverage with no violation, and INSUFFICIENT_EVIDENCE for everything else.

A positive observation needs no coverage proof, so a detected marker is a VIOLATION on its own. A negative conclusion needs coverage proof, so COVERED_CLEAN is reachable only when all eight signal classes independently demonstrated coverage. The reduction over one rollout is fixed and total: any VIOLATION gives VIOLATION; otherwise any INSUFFICIENT_EVIDENCE gives INSUFFICIENT_EVIDENCE; otherwise COVERED_CLEAN.

The INSUFFICIENT_EVIDENCE predicate is a disjunction evaluated in this fixed order, so the reported reason is deterministic.

| Order | Condition | Refusal |
| --- | --- | --- |
| 1 | the trace family is unrecognized | FIDELITY_FAMILY_UNRECOGNIZED |
| 2 | the declared harness version is outside the supported set | FIDELITY_VERSION_UNSUPPORTED |
| 3 | the trace is a conversion product and not native | FIDELITY_TRACE_CONVERSION_ONLY |
| 4 | the marker vocabulary for that version is unknown, which is a version fact because the vocabulary is version-keyed | FIDELITY_VERSION_UNSUPPORTED |
| 5 | the event sequence is non-contiguous | FIDELITY_SEQUENCE_INCOMPLETE |
| 6 | the only support for a clean reading is the harness reporting on itself | FIDELITY_SELF_REPORTED_ONLY |
| 7 | the trace exceeds the bounded-read cap and is not read | FIDELITY_TRACE_UNREADABLE |

Two consequences follow and both are load-bearing. An approved timeout or turn cap that fired exactly as declared is COVERED_CLEAN and not a violation, because faithfully enforcing an approved limit is conforming behaviour, and only an unapproved or undeclared transformation is a violation. A `summarization_count` of 0 under an `enable_summarize` of false is FIDELITY_SELF_REPORTED_ONLY and therefore INSUFFICIENT_EVIDENCE, never COVERED_CLEAN, and that is the incident case itself.

The minimum non-self-attested anchor is an independent execution authority in effective control of admission, execution, observation, and custody. Where no such authority controls all four, independent re-execution is the minimum replacement measurement. Provider-internal routing stays a declared trust assumption and is never a verified one.

## Per-family strongest supported outcome

A family's strongest supported outcome is the best verdict its on-disk form can ever justify. It is a property of the format and not of the trace, so an adapter clamps its own return through this rule and cannot exceed the ceiling by construction.

| Family | Native | Strongest supported outcome | Ceiling refusal | Dispatch |
| --- | --- | --- | --- | --- |
| claude_code_jsonl | yes | COVERED_CLEAN | none | none |
| openhands_events | yes | COVERED_CLEAN | none | none |
| openhands_native_metrics | yes | COVERED_CLEAN | none | none |
| cybergym_usage with its raw agent log present | yes | COVERED_CLEAN | none | delegates the agent log to claude_code_jsonl |
| cybergym_usage without its raw agent log | no | INSUFFICIENT_EVIDENCE | FIDELITY_SELF_REPORTED_ONLY | none |
| atif_normalized standing alone | no | INSUFFICIENT_EVIDENCE | FIDELITY_TRACE_CONVERSION_ONLY | none |
| atif_normalized accompanied by its native source trace | no | COVERED_CLEAN | none | dispatches to the native source family and returns that family's identity |

A marker the conversion could have dropped cannot be proven absent, which is why a normalized trajectory standing alone tops out at INSUFFICIENT_EVIDENCE. The marker's presence in that same normalized trajectory is still a COMPACTION VIOLATION, because a positive observation needs no coverage proof. Where the normalized form is accompanied by its native source, the normalized form is an index and never the evidence.

## Closed vocabularies

These are spelled here once and copied byte for byte by every later surface. A token absent from this table is outside the vocabulary.

| Vocabulary | Carrier | Members |
| --- | --- | --- |
| `trialStatus` | one per rollout in the authoring attempt registry at `.seed/pilot-attempts.jsonl` | conforming, nonconforming, indeterminate |
| `FidelityOutcome` | the forensics module | VIOLATION, COVERED_CLEAN, INSUFFICIENT_EVIDENCE |
| `SignalClass` | the forensics module | COMPACTION, OBSERVATION_TRUNCATION, TURN_CAP, TIMEOUT, PROVIDER_ERROR, REFUSAL, SETUP_FAILURE, HANDOFF_FAILURE |
| `FidelityRefusal` | the forensics module | FIDELITY_FAMILY_UNRECOGNIZED, FIDELITY_VERSION_UNSUPPORTED, FIDELITY_TRACE_CONVERSION_ONLY, FIDELITY_SEQUENCE_INCOMPLETE, FIDELITY_SELF_REPORTED_ONLY, FIDELITY_TRACE_UNREADABLE |
| dispositions | the FORGE and CRUCIBLE root reports | `HOLD:SUPPRESSED_MEASUREMENT`, `BLOCK:INVALID_PILOT` |

Conformance is orthogonal to success, so every rollout carries an outcome of success or failure and a `trialStatus` alongside it. A status of conforming means the trial ran under the approved, faithfully-enforced configuration, which includes an approved timeout or turn cap that fired as declared and an ordinary refusal under approved policy. A status of nonconforming means the approved policy was violated in a suppressing direction: a shortened budget, an unexpected context transformation, a masked provider error, a setup failure, or a handoff failure. A status of indeterminate means the evidence could not resolve it. Only conforming counts as a clean observation.

The versioned rule that derives a status from a rollout's fidelity outcome is `trinity.trial-conformance/v1`. A VIOLATION in a suppressing direction gives nonconforming, an INSUFFICIENT_EVIDENCE gives indeterminate, and a COVERED_CLEAN gives conforming. CRUCIBLE derives the status under that rule and refuses when the operator's own declaration disagrees. Reason codes live only on the audit side, in the private `.audit/fidelity.yaml`, and the authoring registry carries the three tokens and never a reason.

## Threat and capability vocabulary growth

The reward-claim model gains an eighth causal boundary, execution, and sharpens two existing ones so that every obligation sits on exactly one boundary.

- input, whether the scorer received the intended task state and exactly the solver-produced deliverable set, including submission transport and scoring handoff.
- population, whether the committed rollout and group membership equals the precommitted measurement universe, including admission, replacement, and outcome-dependent selection.
- execution, whether the solver received the intended task and service under an approved configuration adequate for the declared horizon, with faithful request construction, context, tool and environment interactions, and isolation between rollouts, ending when the solver produces its final submission.

Submission transport belongs to input, population membership belongs to population, and evidence capture and custody belong to evidence. Boundary ownership attaches to an atomic violated obligation, not to an incident, instrument family, capability channel, or downstream consequence. An incident violating several obligations produces separate findings; each finding has exactly one owning boundary. The five untouched boundaries are definition, computation, attribution, reduction, and evidence.

The threat vocabulary grows from twenty-two entries to twenty-nine with these seven classes, each carrying the one boundary that owns it.

| Id | Added threat class | Owning boundary | What it names |
| --- | --- | --- | --- |
| 23 | approved-but-inadequate configuration | execution | A configuration that is signed, pinned, and reproducible while still too small for the declared horizon |
| 24 | solver-input or tool-interface corruption | execution | The prompt, observation, or tool surface the solver saw differed from the declared one |
| 25 | submission or scoring handoff failure | input | The final answer was altered or lost between the solver and the scorer |
| 26 | execution-state contamination | execution | State carried between rollouts, so two trials shared one cause |
| 27 | effective service degradation | execution | The served model, effort setting, or route was weaker than the declared one |
| 28 | population or scheduling manipulation | population | Which trials counted, or the order they ran in, was settled with outcomes visible |
| 29 | post-solver measurement suppression | evidence | Evidence of a suppressing event was removed or never captured after the solver finished |

The primary boundary assignments for added threat classes 23 through 29 are, respectively, execution, execution, input, execution, execution, population, and evidence. Population or scheduling manipulation names scheduling that changes admission or membership in the measured population; ordering that instead changes a solver's execution state belongs to execution-state contamination. Post-solver measurement suppression names suppression of capture or custody evidence, not omission of rollout or group membership, which belongs to population.

The capability vocabulary grows from eight channels to nine by adding `context`. The eight existing channels are read, write, execute, network, environment, timing, ipc, and resource. A context transformation the policy manifest does not declare is an undeclared influence channel. Both version numbers move to version 2, because the coverage ledger already records which versions it was computed against.

## Least-privilege routing

Routing is least-privilege by principal and surface, because a detector's reason vocabulary is an adaptation channel.

| Principal | Receives | Never receives |
| --- | --- | --- |
| Independent execution authority | the effective configuration, the raw capture, and the population records | nothing withheld, since this principal is the origin of all three |
| CRUCIBLE | full evidence and derived findings, retained under `.audit/attestations/execution/` and reduced into `.audit/fidelity.yaml` | the hardness contract, which its projection withholds entirely |
| Trusted pilot and release verifier | authenticated group eligibility and outcomes, enough to recompute U privately | raw trace bytes and detector reasoning |
| ENGRAM | existing projections, receipt references, and an explicitly authorized coarse disposition | reason-specific trial-status counts |
| FORGE | the same coarse disposition, plus the three conformance tokens on its own rollouts | any reason code, any detector outcome, and any reason-specific trial-status count |

An author who learns why a pilot was refused writes toward the detector, which is reward hacking by construction, so reason-specific counts never cross to FORGE. The execution receipt binds observed artifacts and the effective configuration, while audit conclusions stay on a separate surface. The six suppression reason codes are private audit-side classifications, never dispositions of their own, and FORGE receives only the capped disposition and the permitted three-token trial statuses, never the selected code, any instrument's finding, or the underlying evidence.

The clause that keeps this repository away from duration records, decoy values, access telemetry, blinding results, and detector outcomes binds the FORGE lane and the `.seed/` surface. The auditor's retention at `CRUCIBLE.md:160` and its evidence ledger at `CRUCIBLE.md:165` are a different principal on a different surface and were always lawful. There is no conflict, so that clause is clarified and never weakened.

## Dispositions

| Disposition | Fires when | Closed reasons |
| --- | --- | --- |
| `HOLD:SUPPRESSED_MEASUREMENT` | execution fidelity is violated in the suppressing direction, or fidelity coverage cannot be demonstrated | `context-uncovered`, `fidelity-unverified`, `config-unpinned`, `config-drift`, `config-inadequate`, `handoff-unverified` |
| `BLOCK:INVALID_PILOT` | population integrity cannot be proven against the precommitted roster | none; an unprovable population is no measurement and not a weak one |

`HOLD:SUPPRESSED_MEASUREMENT` is the symmetric twin of `HOLD:MISCALIBRATED`. It generalizes the one existing suppression rule, the `budget-uncovered` refusal, which today covers only a pilot run under a budget smaller than the declared budget hours. Absent adequacy is `config-inadequate` and stays distinct from absent binding, which is `config-unpinned`.

Every finding stays private on the audit side. If population integrity cannot be proven, the auditor emits `BLOCK` and the author lane records `BLOCK:INVALID_PILOT`, with no closed reason recorded. Otherwise, for a `G-FID` `HOLD`, the auditor selects the first applicable reason in this order.

1. config-unpinned, for a missing, unbound, or unapproved configuration.
2. config-drift, for an attested effective configuration contradicting the binding.
3. config-inadequate, for missing adequacy approval or demonstrated inadequacy.
4. handoff-unverified, for a failed or unprovable submission handoff.
5. context-uncovered, for insufficient context-handling evidence.
6. fidelity-unverified, for every remaining observed suppressing violation, insufficient fidelity evidence, missing required fidelity instrument, or operator-versus-derived status disagreement.

Earlier matches exclude later reasons. Other governing `BLOCK` conditions retain precedence. An operator-versus-derived status disagreement caps at `HOLD` unless a governing `BLOCK` condition applies. Missing adequacy approval caps at `HOLD` independently of configuration approval.

Execution fidelity also becomes a sixth mandatory core control, `execution_fidelity`, under `trinity.oracle-run/v4` and `trinity.release-policy/v3`, reconciled against `trinity.execution/v2`. It is never markable non-applicable. On the audit side the four grounding instruments are `G-FID-CONFIG`, `G-FID-TRACE`, `G-FID-POPULATION`, and `G-FID-HANDOFF`, registered as the `G-FID` family.

## External grounding

- claude-code emits `compact_boundary` system events and marks resumed context with `isCompactSummary`. The DISABLE_AUTO_COMPACT control is reported unreliable in anthropics/claude-code issues #42817 and #57490, and release v2.1.159 changed the default silently per issue #64520. A supported-version set is therefore mandatory and never optional.
- OpenHands emits a `Condensation` event carrying `forgotten_event_ids`, `summary`, and `summary_offset`, and declares its condenser in `condenser_config`. Any condenser other than a no-op is a declared transformation that still needs authorization.
- Harbor ATIF version 1.8 adds `continued_trajectory_ref`, per-step `Metrics` token counts, and `Agent.model_name` with `Agent.version`, which is what lets a normalized trajectory point at its native source.
- Harbor terminal-bench-science commit `deef067` excludes timeout trials, which is prior art for treating a timeout as its own class and not a failure.
- arXiv 2107.03374 gives the unbiased combinatorial pass-at-k estimator the release rule computes.
- arXiv 2602.07150, arXiv 2605.23950, arXiv 2608.11242, and arXiv 2609.09218 are the measurement-validity and harness-effect grounding behind this taxonomy.

## Non-guarantees

This document defines vocabulary, arithmetic, and refusal shape. It deploys no detector, no execution authority, no independent runner, and no provider attestation, and it grants authority to none of them. It blesses no historical run: the existing vendor rollouts get a diagnosis and never a certificate, and a diagnosis runner writes nothing under `.seed/` or `.audit/attestations/`. No control this document names as missing is enforced by this document, and the register of stated-but-unenforced obligations stays the authority on what bites.
