# Shared bite tests

Firewall separation, repository structure, rules promoted out of consequence-free musts, and the merged disposition vocabulary.

## Firewall separation

The separation of duties between author and auditor is the project's founding claim. These are the only tests that check it.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| W1 | `FORGE.md` names `CRUCIBLE_VIEW` outside a negation. | Reject. FORGE names its own view and never the auditor's. | firewall projection rule | yes |
| W2 | `CRUCIBLE.md` names `FORGE_VIEW` outside a negation. | Reject. | firewall projection rule | yes |
| W3 | `CRUCIBLE.md` names a cohort-currency term outside a negation. | Reject. Cohort currency is not the auditor's concern. | firewall vocabulary rule | yes |
| W4 | `FORGE.md` names a per-rollout timing term outside a negation. | Reject. Per-rollout timing is not the author's concern. | firewall vocabulary rule | yes |
| W10 | `FORGE.md` names a fidelity-detector term outside a negation. | Reject. Fidelity detection is not the author's concern. | firewall vocabulary rule | yes |
| W5 | FORGE reads `.memory/ledger.yaml` or the proof store. | Reject. FORGE reads its projection and never the raw memory. | FORGE.md:5 | no |
| W6 | FORGE reads `.memory/hardness.yaml` or root `HARDNESS.md` directly. | Reject. | FORGE invariant 23, FORGE.md:404 | no |
| W7 | CRUCIBLE reads the hardness contract. | Reject. | README.md:33, CRUCIBLE.md:219 | no |
| W8 | ENGRAM reads ground-truth, checker-fixture, or oracle bytes. | Reject. | E25 | no |
| W9 | ENGRAM reads a rollout transcript, inspection page, or reward plot, or recomputes a reward series. | Reject. | E31 | no |

## Repository structure

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| R1 | The document spine names 9 files. | Reject. The spine is exactly ten files. | `tools/integrity.py` | yes |
| R2 | The spine names ten files out of canonical order by first mention. | Reject. Order is fixed. | `tools/integrity.py` | yes |
| R3 | A backticked path opens with a segment outside the known roots. | Reject. | `tools/integrity.py` | yes |
| R4 | A retired name such as `EXECUTIVE.md` reappears outside a retire, supersede, collapse, or fold sentence. | Reject. | `tools/integrity.py` | yes |
| R5 | `CODEOWNERS` names an individual, or does not open with a `*` catch-all owned by the `research` team of the organization that owns the repository, such as `* @EtharaOrion/research` under EtharaOrion and `* @Ethara-Ai/research` under Ethara-Ai. | Reject. Ownership is by team, and a team resolves only inside its own organization, so a sibling organization's slug is ignored exactly like a team that does not exist. | repository convention | no |
| R6 | An approval records the same identity as producer and approver. | Reject. Never self-approve. | CRUCIBLE.md:78, E33 | yes |
| R7 | An emoji outside the six-symbol legend appears, or any emoji appears inside YAML or hashed bytes. | Reject. | house rules | partial |
| R8 | A generated section lacks its `GENERATED SECTION` banner. | Reject. | house rules | yes |
| R9 | The license text lacks `Copyright (c) 2026 Ethara.AI`. | Reject. | repository convention | no |
| R10 | The vendored `trinity/` checkout sits behind the upstream `main` tip, or diverges from it, and a run proceeds into a phase. | Reject. A stale checkout hard-blocks every instrument before any phase work. | Trinity freshness gate | no |
| R11 | The freshness comparison cannot run because the submodule, its remote, or the network is unavailable, and the run treats the checkout as fresh. | Reject. Freshness that cannot be established is staleness. | Trinity freshness gate | no |
| R12 | A parent `.gitmodules` registers `trinity` without `branch = main`, without `update = merge`, or pinned to a tag. | Reject. The parent must be wired to track the tip. | `tools/integrity.py` | yes |
| R13 | A prior sign-off, a cached freshness record, or a council approval is cited to waive the freshness gate. | Reject. The gate fails closed and nothing discharges it. | Trinity freshness gate, GAUNTLET rule 11 | no |
| R14 | A `deliverables/` root, as a gitlink or a directory holding any entry, survives at the parent root. | Hold at PARENT_LAYOUT_RETIRED_ROOT until each `deliverables/<uuid>/trajectories/` moves into `<lane>/<uuid>/trajectories/` and the root is deregistered. | `check_parent_layout` | yes |
| R15 | An instrument roots itself one directory above the project that vendors `trinity/`, or scaffolds a harness outside the directory whose direct child is `trinity/`. | Reject. Path containment is absolute and no path resolves above or outside the parent project root. | path containment doctrine, all three contracts | no |

## Rules promoted from consequence-free musts

Each row below states a rule the contracts already assert as a `MUST` while naming no consequence. Every one is decidable from files on disk today. None has ever been enforced by anything.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| M1 | CRUCIBLE authors a task or holds cross-task memory. | `BLOCK`. Role boundary breach. | CRUCIBLE.md:6 | no |
| M2 | CRUCIBLE writes a byte into `samples/` or `deliverables/`. | `BLOCK`. Both are read-only to the auditor. | CRUCIBLE.md:6 | no |
| M3 | A finding, gate internal, or pass criterion is fed to FORGE. | `BLOCK`. Firewall leak. | CRUCIBLE.md:7 | no |
| M4 | CRUCIBLE writes into `research/`. | `BLOCK`. ENGRAM is the sole writer. | CRUCIBLE.md:8, E27 | no |
| M5 | Harness-private staging reaches the author or enters either projection. | `BLOCK`. Firewall leak. | CRUCIBLE.md:8 | no |
| M6 | CRUCIBLE writes `paper/` directly rather than feeding it through ENGRAM. | `BLOCK`. | CRUCIBLE.md:8 | no |
| M7 | CRUCIBLE scaffolds, writes, or reconciles `playbooks/`. | `BLOCK`. ENGRAM alone owns it. | CRUCIBLE.md:9 | no |
| M8 | A resume skips a preflight step. | `BLOCK`. Resume never skips them. | CRUCIBLE.md:65 | no |
| M9 | Progress state is folded into `.audit/scope.yaml`. | `BLOCK`. Progress stays outside sign-off-bound bytes. | CRUCIBLE.md:68 | no |
| M10 | Feedback alone re-opens a satisfied gate. | `BLOCK`. Only changed bound bytes re-open a gate. | CRUCIBLE.md:80 | no |
| M11 | An approval digest is fabricated. | `BLOCK`. | CRUCIBLE.md:78 | no |
| M12 | A failed lane is dropped rather than surfaced as a named finding. | Cap. | CRUCIBLE.md:79 | no |
| M13 | A parallel lane reads a FORGE surface, writes outside its own outputs, or discharges the Phase 0.5 gate. | `BLOCK`. | CRUCIBLE.md:81 | no |
| M14 | A runtime without the parallelism layer skips units rather than running them sequentially. | `BLOCK`. Degradation is to sequential execution, never to skipped units. | CRUCIBLE.md:81 | no |
| M15 | Consultant or critique output raises a disposition. | `BLOCK`. Bucket N may lower or narrow, never raise. | CRUCIBLE.md:81 | no |
| M16 | A feedback entry is cited in `VERDICT.md` as evidence for a finding. | `BLOCK`. | CRUCIBLE.md:106 | no |
| M17 | Discovery alone raises a disposition. | `BLOCK`. | CRUCIBLE.md:107 | no |
| M18 | A required negative control is absent for one of the nine named categories. | Cap. | CRUCIBLE.md:168 | no |
| M19 | A fixture is edited without retriggering sign-off. | `BLOCK`. A fixture edit cannot silently retune the gate. | CRUCIBLE.md:172 | no |
| M20 | A bundle-shaped fixture appears under `samples/` or `deliverables/` rather than under `.audit/fixtures/`. | `BLOCK`. | CRUCIBLE.md:172 | no |
| M21 | Normalized fingerprints are not proven to survive formatting and source line drift. | Cap. | CRUCIBLE.md:180 | no |
| M22 | A finding cites a raw file, a guess, or live code outside `.audit/evidence.yaml`. | Cap. | CRUCIBLE.md:182 | no |
| M23 | A historical result retained under its digest is rewritten. | `BLOCK`. | CRUCIBLE.md:206 | no |
| M24 | A harness uses a glue language other than a Python script or a prompt. | Cap. | CRUCIBLE.md:242 | no |
| M25 | A retired artifact such as `REVIEW.md`, `findings.yaml`, `AUDIT.md` or a root `SCOPE.md` reappears. | `BLOCK`. | CRUCIBLE.md:244 | no |
| M26 | A required tool lives outside `.audit/`. | Cap. | CRUCIBLE.md:247 | no |
| M27 | A Markdown file CRUCIBLE emits, such as `VERDICT.md` or `.audit/review.md`, contains a hard line break inside a paragraph. | Cap. | CRUCIBLE.md:250 | no |

## Orchestration obligations

Rule 6 was split so that these hold on every runtime. Before the split each was scoped by a runtime conditional with no else branch, so on any runtime other than opencode the obligation had no force. These tests exist to prove the split held.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| O1 | A run reports results while a launched lane is still outstanding. | Reject. The orchestrating run collects every launched lane before reporting. | rule 6, all three contracts | no |
| O2 | A lane writes outside its own unit's outputs, or two lanes share mutable state. | Reject. | rule 4 and rule 6 | no |
| O3 | A lane other than the orchestrating run merges results into the batch singletons, `.audit/findings.yaml`, or the memory ledger. | Reject. The orchestrating run alone merges. | rule 6 | no |
| O4 | A lane discharges a human gate, a sign-off, an adjudication, or an election. | Reject. Gates stay with the orchestrating run. | rule 6 | no |
| O5 | A third failed attempt is made at the same unit with no consultant escalation between the second and third. | Reject. Escalation is required after two failed attempts. | rule 6 | no |
| O6 | An architecture-shaping decision, such as a schema, firewall, checker-reduction, mutation-binding, or instrument-registry change, is made with no consultant escalation. | Reject. | rule 6 | no |
| O7 | The Phase 0.5 gate is presented with no plan-critique lane fired over the scope artifact. | Reject. | rule 6 | no |
| O8 | Consultant or critique output raises a disposition, or discharges a gate. | Reject. It is Bucket N advisory and may only lower or narrow. | rule 6 | no |
| O9 | A runtime with no parallelism skips a unit rather than executing the same units in the same order. | Reject. Degradation is to sequential execution, never to skipped units. | rule 6 | no |
| O10 | A contract states an orchestration obligation scoped by a runtime conditional with no unconditional form. | Reject. Only the runtime realization clause names a runtime. | rule 6 split | no |
| O11 | One contract reworded a sentence the other two still state in the original words. | Reject. Shared doctrine is duplicated on purpose, so drift in any copy is drift in the rule. | `SHARED_BLOCKS` | yes |

## Deferred register

The register is read during Phase 0 by all three contracts. These tests cover the reading of it and the discipline that keeps it honest. The last two guard the register against its own incentive, which is the pressure to shrink a count rather than build a check.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| V1 | A required instrument rests on a deferred obligation and the scope artifact does not record the deferral. | Reject. The dependency is recorded before sign-off, never discovered at disposition. | ENGRAM 7c, FORGE 8a, CRUCIBLE 7g | no |
| V2 | A scope artifact records a deferred obligation citing a register row that does not exist. | Reject. The citation resolves or the entry is a coverage gap. | ENGRAM 7c, FORGE 8a, CRUCIBLE 7g | no |
| V3 | A required instrument with no register row and no implementation is recorded as deferred. | Reject. That is a coverage gap, because nobody deferred it. | ENGRAM 7c, FORGE 8a, CRUCIBLE 7g | no |
| V4 | A deferred obligation is recorded and the run raises its disposition above the cap the matching coverage gap would impose. | Reject. A deferral caps exactly as its coverage gap would. | ENGRAM 7c, FORGE 8a, CRUCIBLE 7g | no |
| V5 | A register row is deleted in a commit that lands no code evaluating its predicate. | Reject. A row leaves only beside the check that replaces it. | `DEFERRED.md` exit rule | no |
| V6 | A register row is reworded until it describes less than the obligation its contract still states. | Reject. Narrowing the disclosure is deletion at a slower speed. | `DEFERRED.md` exit rule | no |

## Prompt capture and chain integrity

All three contracts capture every human turn into their feedback ledger and attest each record with a line on a machine-written, human-read-only hash chain. These tests cover the capture obligation and the tamper evidence that guards it.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| P1 | A human turn is received and no ledger record is appended for it. | Reject. Capture is unconditional, and an omission is a broken capture path recorded as a named coverage gap. | feedback capture step 1, all three contracts | no |
| P2 | A turn is judged routine, trivial, or redundant and suppressed rather than captured. | Reject. Classification never gates capture and an unclassifiable turn is captured as `other`. | feedback capture step 1, all three contracts | no |
| P3 | A ledger record is appended with no line appended to the feedback chain in the same act. | Reject. The record and its attesting line are written together. | feedback capture step 4, all three contracts | no |
| P4 | A chain line is edited, reordered, re-signed, or removed by the human operator. | Hard block. A chain that fails its walk is tampering, no phase work proceeds, and the run resumes only after a signed reconciliation entry. | feedback capture step 5, all three contracts | yes |
| P5 | A chain head is published in the root report and no signed checkpoint covers it. | Hard block. An uncovered head fails closed as tampering. | feedback capture step 5, all three contracts | no |
| P6 | A feedback ledger holds records and the chain beside it is absent or unreadable. | Hard block. A missing or unreadable chain is tampering, never an empty history. | feedback capture step 5, all three contracts | yes |
| P7 | A chain line omits `github_id` or carries an empty one, detaching the record from the human it attributes. | Hard block. The chain field set is closed, a missing field and an empty login both fail the walk, and attribution is part of the attested bytes. | feedback capture steps 1a and 4, all three contracts | yes |
| P8 | An identity is guessed from a git config name, an email address, or a filesystem owner instead of the resolution ladder. | Reject. Resolution walks the fixed ladder, and an identity neither rung answers is recorded as `unattributed` with a named coverage gap, never invented. | feedback capture step 1a, all three contracts | no |

## Adversarial operator and delivery integrity

The operator is untrusted. These scenarios are the ones actually used to move bundles past open gates on 2026-09-07, plus the delivery-format, pipeline, and sentinel refusals landed beside them. Rows marked `yes` name a registered test in `tests/test_sabotage.py`, `tests/test_release.py`, `tests/test_harbor.py`, `tests/test_pipeline.py`, or `tests/test_sentinel.py`.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| A1 | `VERDICT.md` says `SHIP` and no `.audit/disposition.json` exists. | Reject as SAB_DISPOSITION_UNBOUND. A disposition is a record, never prose. | CRUCIBLE.md:45, ENGRAM.md:69, FORGE.md:74 | yes |
| A2 | The disposition record's approver equals its producer or the HEAD author. | Reject as SAB_DISPOSITION_FORGED. | CRUCIBLE.md:45 | yes |
| A3 | A required instrument under `.audit/` returns a coverage gap on every branch. | Reject as SAB_INERT_INSTRUMENT. | CRUCIBLE.md:45, CRUCIBLE.md:234 | yes |
| A4 | `.gitmodules` points `trinity/` at a fork of the canonical remote. | Reject as SAB_SUBMODULE_REMOTE. | CRUCIBLE.md:45 | yes |
| A5 | A root `SIGNOFF.md` with no envelope sibling, or a report resting `SHIP` on it. | Reject as SAB_TYPED_SIGNOFF. | CRUCIBLE.md:6, GAUNTLET.md:11 | yes |
| A6 | One commit edits a gate workflow or signing authority together with a root report, disposition record, verdict, attestation, bound contract, or bundle bytes, and the workflow carries bypass syntax on a gate step or the report gains a SHIP token. | Reject as SAB_WORKFLOW_TAMPER at BLOCK. | `tools/sabotage.py` | yes |
| A7 | A root report cites an `.audit/` file absent from `HEAD`. | Reject as SAB_AUDIT_UNCOMMITTED. | `tools/sabotage.py` | yes |
| A8 | The working tree is dirty when the parent gate runs. | Reject as SAB_DIRTY_TREE. | `tools/sabotage.py` | yes |
| A9 | `VERDICT.md` resolves to `HOLD` or `BLOCK` at export time. | Reject as RELEASE_VERDICT_NOT_SHIP. | FORGE.md:332 | yes |
| A10 | A FORGE or CRUCIBLE v2 SHIP record carries no bundle-set or complete snapshot digest, or a digest does not match the exported bytes. | Reject as RELEASE_DISPOSITION_UNBOUND. | CRUCIBLE.md:6, FORGE.md:332 | yes |
| A11 | One byte of the export differs from the audited `samples/` tree. | Reject as RELEASE_EXPORT_MISMATCH. | FORGE.md:332 | yes |
| A12 | An exported uuid has no authorized v4 receipt covering every mandatory control under one manifest closure. | Reject as RELEASE_ORACLE_RECEIPT_MISSING. | FORGE.md:332 | yes |
| A13 | One run directory carries three different values named `reward`. | Reject as RELEASE_REWARD_SCHEMA_AMBIGUOUS. | FORGE.md:332 | yes |
| A14 | A rollout whose verifier status is vacuous is scored rather than tagged invalid. | Reject as RELEASE_TRIAL_STATUS_INVALID. | FORGE.md:332 | yes |
| A15 | `.seed/contract.yaml` binds no `harbor_release`. | Reject as HARBOR_PIN_MISSING. | FORGE.md:187 | yes |
| A16 | The pinned Harbor release is two minor releases behind `harbor.lock`. | Reject as HARBOR_PIN_STALE. | FORGE.md:187 | yes |
| A17 | Harbor's own validator rejects a `task.toml` under the pinned release. | Reject as HARBOR_SCHEMA_INVALID, carrying Harbor's message verbatim. | FORGE.md:234 | yes |
| A18 | `harbor.lock` was resolved more than fourteen days ago. | Reject as HARBOR_LOCK_STALE. | ENGRAM.md:239 | yes |
| A19 | A line of `.podium/queue.jsonl` is rewritten after sealing. | Reject as PIPELINE_CHAIN_BROKEN. | MAESTRO.md:32 | yes |
| A20 | Bundle bytes change after the seal and before the audit. | Reject as PIPELINE_SEALED_MUTATED; the claim is refused. | CRUCIBLE.md:11, FORGE.md:254 | yes |
| A21 | A verdict row exists for a uuid that was never sealed. | Reject as PIPELINE_UNSEALED_AUDIT. | CRUCIBLE.md:11 | yes |
| A22 | Thirty-two sealed bundles await audit against the default depth cap of thirty-one, one batch of thirty ordinary slots and its anchor. | Reject the thirty-second seal as PIPELINE_BACKPRESSURE. | FORGE.md:254 | yes |
| A23 | Two consumers claim the same sealed uuid. | Reject the second claim. | CRUCIBLE.md:11 | yes |
| A24 | The same SAB refusal recurs on the fifth distinct run inside the rolling window. | Raise SAB_REPEATED_ATTEMPT; the disposition caps at BLOCK until a sentinel_clearer principal the alerted actor's signature does not name records a signed clearance. | ENGRAM.md:69 | yes |
| A25 | A line of the sentinel ledger is rewritten. | Reject as SENTINEL_CHAIN_BROKEN and record SAB_LEDGER_ROLLBACK. | `tools/sentinel.py` | yes |
| A26 | A `SHIP` headline stands over a parent gate that returns error findings. | Record SAB_DISPOSITION_FORGED in the sentinel ledger. | CRUCIBLE.md:45 | yes |
| A27 | The null probe scores above zero against the shipped verifier. | Cap at `BLOCK`. | CRUCIBLE.md:164 | no |
| A28 | The bundle declares no null floor, or a floor above 0.05. | Cap at `BLOCK`. | CRUCIBLE.md:164 | no |
| A29 | Fewer than three independent correct solutions reach full reward. | `BLOCK:INVALID_TASK`. | FORGE.md:258 | no |
| A30 | A one-fault mutant of the gold patch scores below zero or trips a cheat check. | `BLOCK:INVALID_TASK`. | FORGE.md:258 | no |
| A31 | A graded literal appears in no statement, base commit, or accepted alternate. | `BLOCK:INVALID_TASK`. | FORGE.md:258 | no |
| A32 | An operational acceptance is used to raise a capped disposition. | Reject. Acceptance never raises a disposition. | GAUNTLET.md:11, CRUCIBLE.md:13 | no |
| A33 | A root report exists with no report-moment gate receipt binding `HEAD`. | Reject as GATE_PREFLIGHT_MISSING. The report was written by hand around the gate. | CRUCIBLE.md:55 | yes |
| A34 | A root report states `SHIP` over a minted record that says `HOLD`. | Reject as GATE_DISPOSITION_MISMATCH. The line is copied, never raised. | CRUCIBLE.md:55 | yes |
| A35 | A parent has no pre-push hook invoking `trinity/tools/gate.py`. | Reject as GATE_HOOK_MISSING. | ENGRAM.md:337 | yes |
| A36 | An agent writes `SHIP` into a disposition record it minted itself. | Impossible by construction: the candidate gate mints `BLOCK`, `HOLD`, or `SHIP_ELIGIBLE`, and final release needs domain-separated producer and approver partial signatures accepted by the external publisher. | CRUCIBLE.md:45, CRUCIBLE.md:47 | yes |
| A37 | A parent's installed local sentinel workflow differs from the candidate template, or the preflight never ran the qualification install. | Reject as GATE_WORKFLOW_MISSING; this local scaffold check does not prove publisher or observer installation. | CRUCIBLE.md:55 | yes |
| A38 | Branch protection could not be applied to the parent or a gated submodule repository. | Write a receipt with `applied: false`, exit 2, and reject as GATE_PROTECTION_MISSING capping at HOLD. | CRUCIBLE.md:55 | yes |
| A39 | The alerted actor writes their own clearance. | Refuse before a byte is written when the alerted actor's own enrolled key signs the clearance, and treat a typed or self-signed clearance as uncleared. | ENGRAM.md:69 | yes |
| A40 | A run, root report, or lane answers a historical SAB_WORKFLOW_TAMPER finding by recommending a rewrite, force-push, replacement, or padding of published history so the flagged commit leaves the scan window. | Reject. History rewriting is itself a sabotage attempt; the only remedy for the BLOCK tier is an append-only signed remediation record authorized by a distinct externally enrolled principal group, and the finding holds at BLOCK until a registered check reads that record. | CRUCIBLE.md:45, ENGRAM.md:69, FORGE.md:74 | no |
| A41 | A run, root report, lane, or the scaffolded hook itself recommends bypassing a gate surface: a verification-skipping push flag, unsetting or redirecting `core.hooksPath`, editing the installed hook, or disabling a registered check, including the case where the hook refuses only because it drifted from its template. | Reject. Bypass is the same class of attempt as history rewriting; the hook passes the canonical `./` root the gate demands, names the finding or the preflight refresh as the only recovery, and never offers a bypass. | CRUCIBLE.md:45, ENGRAM.md:69, FORGE.md:74 | yes |
| A42 | `verdict` refuses moved bytes or a stale claim. | Refuse a verdict whose bundle bytes or claim digest differ from the seal; sealed bundles are frozen and there is no reseal. | CRUCIBLE.md:11, `tests/test_pipeline.py::test_verdict_refuses_stale_claim_after_reseal` | yes |
| A43 | `verify` flags a placed bundle without a clean verdict. | Reject as `PIPELINE_PLACED_UNCLEAN` when the verdict is missing, retained, or bound to an older digest. | FORGE.md:330, `tests/test_pipeline.py::test_verify_flags_placed_bundle_without_clean_verdict` | yes |
| A56 | Two queue streams seal one uuid at different digests. | Reject as `PIPELINE_STREAM_CONFLICT`; the same bytes dedupe and different bytes are a merge-time refusal a human reconciles. | FORGE.md:254, `tests/test_pipeline.py::test_same_uuid_in_two_streams_with_different_bytes_is_a_conflict` | yes |
| A57 | A queue stream the remote already holds is rewritten rather than extended. | Reject as `PIPELINE_STREAM_REWRITTEN`; every stream at the accepted ref is a byte prefix of the stream on disk. | FORGE.md:84, `tests/test_pipeline.py::test_verify_accepted_refuses_a_rewritten_stream` | yes |
| A58 | Two auditors claim one sealed bundle on separate clones. | The earliest claim at the sealed digest owns it; a verdict by any other run is `PIPELINE_VERDICT_UNOWNED` once the trees merge. | CRUCIBLE.md:11, `tests/test_pipeline.py::test_earliest_claim_owns_and_a_later_clone_verdict_is_unowned` | yes |
| A59 | Another runner's commit lands beside a run's qualification. | The qualification stays current while its subject closure holds; a change inside the closure, whoever made it, requires the report moment again. | FORGE.md:84, `tests/test_subject.py::test_another_runs_commit_does_not_change_the_closure` | yes |
| A60 | A root report is written by hand beside run reports. | Reject as `REPORT_NOT_RENDERED`; the root report is rendered from every run report and its disposition is the worst run disposition, never SHIP. | FORGE.md:64, `tests/test_reports.py::test_root_report_is_rendered_from_every_run_and_states_the_worst_disposition` | yes |
| A61 | Two clones append sabotage refusals at once. | Each run appends to its own sentinel stream under `.sentinel/streams/<run_id>/`; both chains verify after the merge. | FORGE.md:84, `tests/test_sentinel.py::test_streams_chain_independently_and_both_verify` | yes |
| A62 | A repeat attempt is spread across freshly minted run streams to reset the count. | Reject as `SAB_REPEATED_ATTEMPT`; repeat detection reads every stream, so run rotation never evades the threshold. | FORGE.md:84, `tests/test_sentinel.py::test_repeats_aggregate_across_streams_so_run_rotation_cannot_evade` | yes |
| A63 | A run namespace carries an empty or broken feedback chain. | Reject; every run's feedback chain is walked under the same rule as the harness-root chain. | FORGE.md:64, `tests/test_integrity_parent.py::test_feedback_chain_walks_every_run_namespace` | yes |
| A64 | A release is signed against a moving `main` rather than a frozen candidate. | Promotion into `<harness>/releases/<id>/` freezes the candidate commit and snapshot; later movement of `main` neither invalidates nor extends it. | FORGE.md:84, `tests/test_gate.py::test_promote_into_a_release_candidate_leaves_the_qualified_record_and_later_main_alone` | yes |
| A65 | Two ENGRAM runs propose disjoint memory files against the current epoch. | Both fold into one immutable epoch with both projections published together and bound to its manifest. | ENGRAM.md:177, `tests/test_epochs.py::test_publish_folds_disjoint_proposals_from_two_runs_into_one_epoch` | yes |
| A66 | Two ENGRAM runs propose one memory file, or a proposal names a superseded epoch. | Reject as `proposal-conflict` or `proposal-stale`; nothing is published until a human reconciles. | ENGRAM.md:177, `tests/test_epochs.py::test_publish_refuses_conflicting_proposals_and_stale_bases` | yes |
| A67 | Two clones each place sixteen clean bundles and push. | The merged tree holds thirty under `samples/` and the overflow under `delivery/`, decided by seal order and verified by `reconcile --check` on the merged tree. | FORGE.md:420, `tests/test_parallel.py::test_two_clones_placing_past_thirty_route_the_overflow_at_merge` | yes |
| A68 | One commit edits a gate workflow or signing authority beside a governed subject with no bypass syntax and no SHIP token entering a report. | Record SAB_WORKFLOW_TAMPER_SUSPECT and cap at HOLD, never BLOCK; the message names the split-commit closure and never a rewrite. | `tools/sabotage.py`, CRUCIBLE.md:45, ENGRAM.md:69, FORGE.md:74 | yes |
| A69 | After a SAB_WORKFLOW_TAMPER_SUSPECT finding the same actor lands the flagged governance paths and the flagged subject paths again in separate commits inside the scan window. | The suspect finding closes and the parent gate is clean; a SAB_WORKFLOW_TAMPER finding never closes this way. | `tools/sabotage.py` | yes |
| A70 | One commit edits a gate workflow beside a lane README or a roster gitlink. | Housekeeping, not a subject; no tamper finding. | `tools/sabotage.py`, `tests/test_sabotage.py::test_workflow_edit_beside_housekeeping_is_not_tamper` | yes |
| A71 | One commit edits `.gitmodules` beside a governed subject. | Reject as SAB_WORKFLOW_TAMPER; `.gitmodules` is a governance path and the co-edit caps at BLOCK. | `tests/test_sabotage.py::test_gitmodules_edited_beside_a_subject_is_workflow_tamper` | yes |
| A72 | The parent `.gitmodules` is absent or unreadable, or a roster section lacks `path` or `url`. | Hold at PARENT_LAYOUT_GITMODULES_INVALID; a roster declaration nothing can read is an unfinished scaffold and caps at HOLD. | ENGRAM.md:311, `tests/test_layout.py::test_missing_gitmodules_is_refused` | yes |
| A73 | A required roster root has no declared `[submodule]` section. | Hold at PARENT_LAYOUT_SUBMODULE_MISSING; every one of the five roster roots is registered or the scaffold is unfinished. | ENGRAM.md:311, `tests/test_layout.py::test_missing_submodule_registration_is_refused` | yes |
| A74 | A declared roster root carries no mode `160000` index entry. | Hold at PARENT_LAYOUT_PLAIN_DIRECTORY; the parent records each roster root by gitlink alone. | FORGE.md:420, `tests/test_layout.py::test_plain_directory_lane_root_is_refused` | yes |
| A75 | A roster section declares a branch other than `main` or an update policy other than `merge`. | Hold at PARENT_LAYOUT_BRANCH_INVALID; every roster root is wired to track the tip with `branch = main` and `update = merge`. | ENGRAM.md:311, `tests/test_layout.py::test_branch_or_update_drift_is_refused` | yes |
| A76 | `deliverables` is a gitlink at the parent root, or a directory holding any entry. | Hold at PARENT_LAYOUT_RETIRED_ROOT; the retired mirror is a migration state and caps at HOLD until its evidence moves inside each bundle. | README.md:119, `tests/test_layout.py::test_deliverables_at_parent_root_is_retired_not_a_leak` | yes |
| A77 | The parent `.gitignore` omits `.secrets/` or `.trinity-runtime/`. | Hold at PARENT_LAYOUT_RUNTIME_UNIGNORED; no secret or runtime byte under either root is ever tracked in the parent. | ENGRAM.md:311, `tests/test_layout.py::test_unignored_runtime_roots_are_refused` | yes |
| A78 | The boundary scan reaches `SCAN_MAX_ENTRIES`, or the index or a checkout is unreadable. | Hold at PARENT_LAYOUT_SCAN_TRUNCATED; a scan that stopped short reports the bound it hit and never returns a clean result. | `tools/layout.py`, `tests/test_layout.py::test_scan_bound_is_reported_not_silently_truncated` | yes |
| A79 | The parent index holds a gitlink outside `KNOWN_ROOTS`. | Reject as PARENT_LAYOUT_UNKNOWN_SUBMODULE at BLOCK; the roster is closed and an unnamed submodule is a collapsed boundary. | README.md:162, `tests/test_layout.py::test_unknown_gitlink_is_refused` | yes |
| A80 | Two roster roots normalize to one remote. | Reject as PARENT_LAYOUT_SHARED_REMOTE at BLOCK; each roster root stands against a remote distinct from every other roster root's. | ENGRAM.md:311, `tests/test_layout.py::test_two_roster_roots_sharing_one_remote_are_refused` | yes |
| A81 | The parent index holds a non-gitlink entry under `samples/` or `delivery/`. | Reject as PARENT_LAYOUT_PARENT_TRACKS_BUNDLE at BLOCK; the parent tracks no bundle byte of its own. | FORGE.md:420, `tests/test_layout.py::test_parent_tracked_bundle_bytes_are_refused` | yes |
| A82 | A forbidden path is resident in a roster checkout, or the parent index tracks a `.secrets/` or `.trinity-runtime/` entry. | Reject as PARENT_LAYOUT_BOUNDARY_LEAK at BLOCK; a crossed need-to-know boundary is evidence, never an unfinished scaffold. The one checkout the scan does not enter is a `harness/` root that is itself a trinity project, recognized by its own registered and checked-out `trinity/` submodule carrying the gate and never by root reports alone; its `.audit/` belongs to its own CRUCIBLE, while the same shape under `samples/`, `delivery/`, `.memory/`, or `staging/` still leaks. | README.md:59, `tests/test_layout.py::test_hardness_contract_inside_samples_is_a_boundary_leak` | yes |
| A83 | A roster root is a symlink, or a symlink is met inside a checkout. | Reject as PARENT_LAYOUT_SYMLINK at BLOCK; the scan refuses the link and never follows it out of the parent. | `tools/layout.py`, `tests/test_layout.py::test_symlinked_roster_root_is_refused` | yes |
| A84 | Five or more gate runs inside the rolling window each record SAB_INERT_INSTRUMENT over the same unbuilt instruments under `.audit/` or `.seed/`. | Append every occurrence to the attempts ledger and keep refusing the gate on the inert instrument itself, but never raise SAB_REPEATED_ATTEMPT: the code names a state of the tree every run re-observes, not an act an operator repeats, and an alert already raised over it re-derives as a superseded advisory that needs no clearance. | `tools/sentinel.py`, `tests/test_sentinel.py::test_inert_instrument_reaches_the_ledger_but_never_repeats` | yes |
| A90 | A run issues `git add`, `git commit`, a submodule commit, a gitlink update, or a push on its own, or a MAESTRO boundary commits or pushes for a lane. | Reject as the sabotage class the hostile-operator paragraph names; the run halts at the commit gate with its written paths grouped by repository and a suggested message, and only the human commits and pushes. | FORGE.md:420, ENGRAM.md:79, CRUCIBLE.md:55 | no |
| A91 | A clearance is a typed JSON file naming an approver. | Reject as SAB_SENTINEL_CLEARANCE_UNSIGNED; the alert stands and the typed clearance is itself appended to the ledger as a self-approval attempt. | ENGRAM.md:69 | yes |
| A92 | A clearance envelope is signed by the alerted actor's own enrolled key. | Refuse before a byte is written and refuse a planted one at the gate; the alerted actor's verified principal is excluded from the sentinel_clearer threshold. | ENGRAM.md:69 | yes |
| A93 | An operator commits under a colleague's name on a commit carrying no verifiable signature. | Attribute the attempt to the claimed identity unverified:<author>; it never counts toward the colleague's verified principal and never excludes the colleague from clearing. | ENGRAM.md:69 | yes |
| A94 | .memory/allowed_signers is absent when a clearance is read. | Refuse the clearance naming the absent policy and its remedy, leave the alert standing, and exit 1 from verify. | ENGRAM.md:69 | yes |
| A95 | A candidate transition is offered to the admission boundary whose sole parent is not the accepted base it was validated against, or which buries that base as the second parent of a merge. | Refuse as TRANSITION_BASE_MISMATCH before any record rule runs; the baseline is the one the boundary holds, never the one the candidate names. | `tools/transition.py`, `tests/test_transition.py::test_a_merge_that_buries_the_accepted_base_as_a_second_parent_is_refused` | yes |
| A96 | A transition rewrites, truncates, or deletes a queue stream, claim, verdict, sentinel entry, or published epoch the accepted state already carries. | Refuse as TRANSITION_STREAM_REWRITTEN, TRANSITION_RECORD_MUTATED, or TRANSITION_RECORD_DELETED; accepted history extends and is never rewritten, and a run's own workspace under its namespace stays freely mutable. | `tools/transition.py`, `tests/test_transition.py::test_an_edited_accepted_claim_is_refused` | yes |
| A97 | A transition writes into a run namespace whose accepted marker binds another principal, or mints a run marker naming a principal other than the authenticated operator. | Refuse as TRANSITION_FOREIGN_RUN; a run namespace is written only by the principal the accepted marker binds, and an operator outside the enrolled set is refused as TRANSITION_UNENROLLED_OPERATOR before any other rule. | `tools/transition.py`, `tests/test_transition.py::test_writing_into_another_principals_run_namespace_is_refused` | yes |
| A98 | A transition claims a bundle another run already owns in the accepted state, carries two claims on one bundle at once, or records a verdict with no accepted claim, with no consumer run, or by a run other than the accepted owner. | Refuse as TRANSITION_CLAIM_CONTESTED or TRANSITION_VERDICT_UNOWNED; ownership is the accepted sequence, a backdated `claimed_at` buys nothing, and a contested claim is refused rather than settled by an instant. | `tools/transition_records.py`, `tests/test_transition.py::test_a_second_claim_on_an_already_accepted_bundle_is_refused` | yes |
| A99 | A transition publishes an epoch that is not one past the accepted current, moves `.memory/current.json` backwards, appends a seal instant earlier than the accepted watermark, or carries trust-policy bytes other than the ones the boundary pins. | Refuse as TRANSITION_EPOCH_FORK, TRANSITION_EPOCH_ROLLBACK, TRANSITION_BACKDATED, or TRANSITION_TRUST_DRIFT; memory advances by one against the accepted state, a backdated seal never reorders the scarce-slot queue, and a trust change is an out-of-band ceremony rather than a payload of the transition it would authorize. | `tools/transition_records.py`, `tests/test_transition.py::test_a_backdated_seal_that_would_jump_the_scarce_queue_is_refused` | yes |
| A100 | A run operation envelope is signed by one key while its payload names a different principal, or by a principal the trust root binds to no `run_operator` role, against an absent trust root, or against a rolled-back trusted version. | Refuse as OPERATION_PRINCIPAL_MISMATCH or OPERATION_UNAUTHORIZED; a valid signature never speaks for another identity, and an unreadable or superseded trust root refuses rather than passes. | `tools/operations.py`, `tests/test_operations.py::test_an_operation_naming_a_principal_other_than_its_signer_is_refused` | yes |
| A101 | A run's signed operations do not start at sequence one, skip a sequence number, link to a predecessor hash that is not the prior entry, or carry two run ids in one chain. | Refuse as OPERATION_CHAIN_BROKEN; one chain carries one run, and an operation cannot be removed, reordered, or inserted without breaking the link that follows it. | `tools/operations.py`, `tests/test_operations.py::test_a_chain_whose_previous_does_not_link_is_refused` | yes |
| A102 | A transition offered under a signing policy introduces a claim or verdict whose bytes no verified operation names, or carries an operation signed by someone other than the offering operator, or plants an operation inside a run namespace other than the one it authorizes. | Refuse as TRANSITION_UNSIGNED_OPERATION, OPERATION_PRINCIPAL_MISMATCH, or OPERATION_CHAIN_BROKEN; coverage is by content digest, so the record on disk and the statement about it cannot drift apart. A transition offered without a signing policy is judged on structure alone. | `tools/transition_signing.py`, `tests/test_transition.py::test_a_claim_with_no_signed_operation_is_refused` | yes |
| A44 | An uncleared SAB_REPEATED_ATTEMPT alert stands in `.sentinel/alerts.jsonl` that the attempts ledger no longer supports under the repeat rule in force, because it was raised under a superseded rule that related attempts by shared author or fired at a lower threshold. | Re-derive the refusal from the ledger, never restate the alert: the alert stays in the append-only ledger as history, surfaces as an advisory naming it superseded, caps nothing, needs no clearance, and never folds a later genuine repeat by the same actor into itself. | ENGRAM.md:69 | yes |
| A45 | An administrator has already protected `main` of the parent or a gated submodule repository, through classic protection or through an active ruleset with no bypass actors, and the principal running the preflight cannot write branch protection. | Read the protection back and receipt it as applied without a write; never require the operator to hold administrative rights over a branch that is already protected, and never report a ruleset-protected branch as unprotected. A ruleset any actor may bypass is not protection. | CRUCIBLE.md:55 | yes |

## Disposition vocabulary

These tests exist only if the merged Axis plus Reason encoding is adopted. They are listed here so the decision has visible consequences.

| ID | Scenario | Expected refusal | CI |
| --- | --- | --- | --- |
| D1 | A verdict carries a reason code outside the closed list. | Reject. | no |
| D2 | A `HOLD` or `BLOCK` carries no reason code. | Reject. | no |
| D3 | A `SHIP` carries a reason code. | Reject. | no |
| D4 | A role emits a reason code outside its allowlist, for example CRUCIBLE emitting `PILOT-REQUIRED`. | Reject. | no |
| D5 | A `VIEW-INPUT-UNPROJECTED` names an input absent from the projection allowlist. | Reject. | no |

## The one clause that must not become a test

`CRUCIBLE.md:215` states that a finding citing a hardness target rather than an artifact is out of scope and never moves a disposition. This is an exclusion, not a refusal. It is the only one in the corpus. Deleting it as apparent boilerplate would silently widen what CRUCIBLE refuses, letting the auditor act on hardness grounds and crossing the firewall that keeps it out of the hardness contract. A regression that makes a system stricter is still a regression, and it is the kind that passes every test.
