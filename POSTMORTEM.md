# Postmortem: the EtharaOrion sample delivery of 2026-09-07

How the delivery in `Ethara-Orion-Quality-Assessment.md` left the parent projects with every defect the client found, what Trinity now refuses that it did not refuse before, and what it still only describes. Every claim names a file, a contract line, a repository, or a date.

## 1. Verdict

The delivery did not fail Trinity's gates; it went around them, because publication of `samples/` is a human act no instrument could refuse and the machine gate never read a disposition line. Eight of the ten parent projects stood at BLOCK, HOLD, BROKEN, or STALE when their bundles were pushed, and the two SHIP verdicts rested on a typed sign-off and on an audit of a folder outside the contract layout. Every one of the client's findings maps to a clause already in `FORGE.md` or `CRUCIBLE.md`, and `DEFERRED.md` already stated that those clauses were prose an agent could choose to honor. No oracle was ever run through a shipped verifier, no judge was ever in scope, and the Harbor manifests targeted a schema three releases old. Five stdlib-only modules with 201 tests and a producer/consumer pipeline landed today; the remaining work is listed in section 8.

## 2. Timeline

| Date | Event |
| --- | --- |
| 2026-06-22 | `EtharaOrion/trinity` created; first commit |
| 2026-07-24 to 08-17 | Ten parent repos created under `EtharaOrion` |
| 2026-09-07 | All ten `<name>-samples` repos created and pushed between 13:47 and 23:17, thirty tasks, most commit messages "update readme" |
| 2026-09-12 | Harbor 0.23.0 released, the current schema |
| 2026-09-14 to 09-16 | Parent root reports `VERDICT.md`, `EDICT.md`, `DIRECTIVE.md` written or rewritten |
| 2026-09-15 11:05 | argos `VERDICT.md` records BLOCK: twelve required instruments inert |
| 2026-09-15 11:17 | argos-samples push "Add 10 task bundles with 8/8 measured rollouts" |
| 2026-09-15 11:34 | argos `verdict.md` hand-edited after the samples pointer moved |
| 2026-09-16 | Client assessment received: 30 tasks, 336 rollouts, ten repos |

## 3. Disposition at delivery time

| Parent | FORGE or CRUCIBLE disposition at last recorded run | What shipped anyway |
| --- | --- | --- |
| argos | CRUCIBLE BLOCK, twelve inert instruments, `sandbox_state()` hardcoded False; FORGE BLOCK:INVALID_TASK, "every authored bundle can be passed without solving it" | 3 tasks, then 10 more on 09-15 |
| teresa | HOLD:PILOT_REQUIRED; regeneration "unmeasured"; no rollout surface | 3 tasks |
| deku | STALE; no signed proof ever landed | 3 tasks |
| anubis | HOLD:PILOT_REQUIRED; 212 uncommitted paths under `samples/`; calibration check "reporting a false pass" | 3 tasks |
| yuji | BROKEN; BLOCK:INVALID_TASK provenance-invalid; "external pilot not run" | 3 tasks |
| kakashi | HOLD:PILOT_REQUIRED; forge view unresolvable | 3 tasks |
| kanao | BLOCK:INVALID_TASK, 36 coverage gaps | 3 tasks |
| thanatos | HOLD; 8 of 31 instruments built; no scanner ran; "vacuous" on all 24 runs | 3 tasks |
| levi | SHIP "on the standing signed project-lead acceptance in `SIGNOFF.md`" dated 09-07 | 3 tasks |
| envora | CRUCIBLE SHIP over `/Users/apple/envora/QCing`, outside the layout; FORGE BLOCK:INVALID_TASK | 3 tasks |

## 4. Root causes, ranked

First, the push was lawful. GAUNTLET rule 7 and FORGE rule 2f make publication of `samples/` a human act, and none of the twenty-seven parent checks in `tools/integrity.py` read a disposition line, compared the `samples` pointer to an audited digest, or ran on the `<name>-samples` repos, which had no workflows and no branch protection.

Second, enforcement was prose. `DEFERRED.md` states that "every refusal outside that set depends on an agent choosing to honor it", that 217 of 251 bite scenarios "have never been verified by anything, including by hand", that verifier robustness is "NOT DECIDABLE FROM DISK", that FORGE "imposes nothing on its three judge usages", and that no external pilot "has ever run", so SHIP was unreachable by construction. Where an agent built the harness, it was inert: argos's twelve instruments return a coverage gap on every branch, teresa's regeneration check "refuses to execute", thanatos built 8 of 31.

Third, no oracle ever ran through a shipped verifier. `FORGE.md:222` requires full reward through the Harbor oracle path; the only executing check, `check_bundle_truth_regeneration`, replays `recompute.py` on the host. Hence the thanatos gold that formats every status as `405 OK`, the envora oracle at 0 of 496 under its own cwd bug, deku's three missing grader modules, and teresa's `answer.md` at a path only OpenHands writes.

Fourth, the judge was never in scope. `check_judge_reliability` returns nothing when `.audit/judgments.jsonl` is absent, and no parent has that file; runner, prompt, and reducer live only in the private `<name>-harness` repos, unpinned.

Fifth, the manifests targeted an old Harbor. `FORGE.md:170` pins `schema_version` to "a tested value, never to floating latest" and nothing validated it; Harbor 0.3.0 of 2026-03-27 added the required `[task]` section, and 24 of 30 manifests fail on every release since, reproduced against 0.2.0, 0.3.0, and 0.23.0 wheels.

Sixth, this was known. `FEEDBACK.md` already catalogued private registries, self-report graders, silent passes, hidden-name grading, blank judge reasoning, "adversarially validated only in simulation", and single-party attestation.

Seventh, effort went to the meta-layer and the READMEs. Trinity carries 97 commits and five contracts; the samples repos average three commits each, and the thanatos README prints `status: "vacuous"` on all 24 runs and reports 34.98% anyway.

## 5. Client finding, contract clause, enforcement

Section 1, cannot be built or scored.

| Finding | Stated in | Enforced before | Enforced now, or still deferred |
| --- | --- | --- | --- |
| Private images (argos, levi, thanatos) | FORGE 170, 236; CRUCIBLE 133, 185 | digest syntax on `task.toml` only | deferred: `BUNDLE_IMAGE_PRIVATE`, anonymous pull (6 h) |
| MCP server missing (yuji) | FORGE 169, 199 | nothing | deferred: `BUNDLE_ENV_ESCAPES_BUNDLE` (4 h) |
| Grader modules missing (deku) | FORGE 218, 370 | `tests/test.sh` existence only | deferred: `VERIFIER_REFERENCES_MISSING_FILE` (5 h) |
| Test channel absent (thanatos) | FORGE 233, 370 | nothing | now: `RELEASE_TRIAL_STATUS_INVALID` in `tools/release.py`; deferred: `GRADED_TARGETS_EMPTY` (4 h) |
| Oracle fails shipped verifier (envora) | FORGE 222, 223; CRUCIBLE 145 | nothing | now: `RELEASE_ORACLE_RECEIPT_MISSING` and `RELEASE_ORACLE_RECEIPT_INVALID` require a stock-Harbor receipt at full reward; deferred: the runner that produces receipts (12 h) |
| Broken gold (thanatos 394d9d5c) | FORGE 223, 359 | nothing | same receipt requirement |
| Grader loses answer (teresa) | FORGE 169, 184 | nothing | deferred: `VERIFIER_READS_UNDECLARED_PATH` (4 h) |
| Model refuses (kakashi) | not stated | nothing | deferred: new FORGE Phase 2 obligation, `cohort-refuses` HOLD (3 h) |

Section 2, reward without doing the work.

| Finding | Stated in | Enforced before | Enforced now, or still deferred |
| --- | --- | --- | --- |
| Negated or keyword answer scores 1.0 (teresa) | FORGE 269 anti-shortcut lane | nothing; teresa `linked()` is a 400-char regex with no negation handling | deferred: `G-ADV-NEGATED`, `G-ADV-LISTALL` (1.5 d) |
| Fake trajectory plus junk files (yuji) | CRUCIBLE 145, 8q | nothing | deferred: `G-ADV-FAKETRAJ`, `check_scorer_input_closure` |
| Self-reported report files (anubis) | CRUCIBLE 145 | nothing; grader reads seven agent-written files under `/app/out/` | deferred: `G-ADV-SELFREPORT` (2.5 d) |
| `conftest.py` xfail flips 0 to 1 (envora) | not stated | nothing | deferred: `check_verifier_hook_surface` (1 d) |
| Garbage reproducer near full credit (kakashi) | not stated | nothing | deferred: `G-ADV-PARTIAL` (2 d) |
| Format floor 0.074 (kanao) | legal under contract | nothing | deferred: `G-ADV-FORMATONLY`, declared `null_floor` at most 0.05 |
| Null submission nonzero (teresa, argos, levi) | CRUCIBLE 139 `G-CON-EMPTY` exactly zero | argos built it inert | now: `SAB_INERT_INSTRUMENT` refuses the inert shape; deferred: `G-ADV-NULL` execution (1 d) |

Section 3, correct work scores poorly.

| Finding | Stated in | Enforced before | Enforced now, or still deferred |
| --- | --- | --- | --- |
| Hidden identifiers, strings, line numbers, key order (argos, levi, envora, teresa, anubis) | FORGE 10a.1 statement closure, invariant 22 | nothing | deferred: `G-STMT-GRADER-RECONCILE`, `GRADED_LITERAL_HIDDEN` and six sibling codes, decidable from disk (4.5 d) |
| One mocking strategy accepted (thanatos) | FORGE 10a | nothing | deferred: `G-ALT-SOLUTION` axis `mocking-strategy` (2.5 d plus authoring) |
| Out-of-scope PR #613 checks (levi) | FORGE 10d | nothing | deferred: `GRADED_OUT_OF_SCOPE` |
| Cliffs and negative partial credit (anubis, kakashi, kanao) | FORGE 233 robustness | nothing | deferred: `G-MUTANT-LADDER`, `MUTANT_SCORE_CLIFF`, `CHEAT_CHECK_FIRES_ON_GOLD_SUBSET` (3.5 d) |
| Instruction conflicts with grader (kanao, anubis) | FORGE 10a ambiguity | nothing | deferred: `ALLOWED_PATH_HASH_PINNED`, `INSTRUCTION_PATH_UNRESOLVED` |

Section 4, LLM judge.

| Finding | Stated in | Enforced before | Enforced now, or still deferred |
| --- | --- | --- | --- |
| Judge trusts claims over tests (argos, envora) | CRUCIBLE 5a | nothing | deferred: `JUDGE_CONTRADICTS_TESTS` |
| Inconsistent verdicts, unpinned (thanatos, levi) | CRUCIBLE 5a; `check_judge_reliability` | fires only when `.audit/judgments.jsonl` exists; no parent has it | deferred: `JUDGE_SAMPLING_UNPINNED`, `JUDGE_TRIALS_UNDER_MINIMUM` |
| Incomplete transcript (anubis) | not stated | nothing | deferred: `JUDGE_PACKET_TRUNCATED`, tool-call count equality |
| Hidden judge rules (envora, thanatos) | not stated | nothing | deferred: `JUDGE_HIDDEN_RULE` |
| Judge code absent (all 30) | not stated | nothing | deferred: `JUDGE_RUNNER_ABSENT`, `tests/judge/` becomes bundle content (about 1 week plus backfill) |

Section 5, environment and reproducibility.

| Finding | Stated in | Enforced before | Enforced now, or still deferred |
| --- | --- | --- | --- |
| Old Harbor schema (24 tasks) | FORGE 170, 218 | `schema_version` non-empty string | now: `HARBOR_PIN_STALE`, `HARBOR_SCHEMA_INVALID`, `HARBOR_PIN_UNTESTED` in `tools/harbor.py` |
| Invalid manifests (deku) | FORGE 218 | never run | now: `HARBOR_SCHEMA_INVALID` carries Harbor's message verbatim |
| Harness-specific output (teresa, envora) | FORGE 277; CRUCIBLE 146 | attestation check with no attestations | deferred: `ROLLOUT_HARNESS_UNSHIPPED` (6 h) |
| `\|\| true` builds (envora) | not stated | nothing | deferred: `BUILD_SWALLOWS_FAILURE` (3 h) |
| Network mismatch (anubis, kanao, levi) | FORGE 170, 171 | nothing | deferred: `NETWORK_POLICY_VIOLATED` (5 h) |
| Grading state leak (deku) | FORGE 233; CRUCIBLE 137 | nothing | deferred: `VERIFIER_PHASE_LEAK` (8 h) |
| Unpinned delivery | FORGE 174, 200 | signature checks, no carriers shipped | now: `RELEASE_EXPORT_MISMATCH` binds the samples pointer to `VERDICT.md` |

Section 6, rollouts and reporting.

| Finding | Stated in | Enforced before | Enforced now, or still deferred |
| --- | --- | --- | --- |
| Three meanings of reward (yuji) | not stated | nothing | now: `RELEASE_REWARD_SCHEMA_AMBIGUOUS` |
| Setup failures counted as model failures | not stated | nothing | now: `RELEASE_TRIAL_STATUS_INVALID`; deferred: runner-side classification |

## 6. Adversarial-operator threat model

Assuming the operators want a fabricated SHIP, twenty-three vectors were mapped; the three used between 09-07 and 09-15 were a hand-edited disposition, a subject moved after audit, and an unreviewed direct push to samples.

| Vector | Detected before | Detected now | Trust anchor |
| --- | --- | --- | --- |
| Hand-edit a root report to SHIP | no, headings only | `SAB_DISPOSITION_UNBOUND`, `SAB_DISPOSITION_FORGED`, `RELEASE_DISPOSITION_UNBOUND` | separate FORGE and CRUCIBLE v2 records co-signed by authenticated producer and independently authorized approver, with neither private key transferred |
| Inert instruments, hardcoded sandbox | no, `CRUCIBLE.md:217` is prose | `SAB_INERT_INSTRUMENT` by AST | CI re-runs the gate |
| Audit over uncommitted `.audit/` code | no | `SAB_AUDIT_UNCOMMITTED`, `SAB_DIRTY_TREE` | CI on the pushed commit |
| Self-signed or typed approval | string compare only | `SAB_TYPED_SIGNOFF`; approver must differ from HEAD author | org-held allowed-signers roster (deferred) |
| Replay stale approval digest | naive replay only | unchanged | CI-owned replay store (deferred) |
| Rewrite ledger, fake CFER or execution attestations | partial, against a self-minted root | unchanged | org root, Merkle recomputation (deferred, P1 and P2) |
| Pin `trinity/` to a fork or edit remote | behind or diverged against whatever `origin` is | `SAB_SUBMODULE_REMOTE`, `SAB_SUBMODULE_OFF_MAIN` against the canonical URL | CI clones canonical Trinity |
| Swap bundle bytes after audit | no | `RELEASE_EXPORT_MISMATCH`, `PIPELINE_SEALED_MUTATED` | signed record carries gitlink SHA |
| Audit subject outside the layout | no | unchanged | deferred: `SAB_SUBJECT_OUT_OF_ROOT` |
| Edit workflows alongside a bypass | no | `SAB_WORKFLOW_TAMPER` | CODEOWNERS on `.github/` (org config) |
| Direct push to `*-samples` | no | externally governed `templates/release-gate.yml` publisher evaluation | governance publisher deployment and org ruleset |
| Report README numbers never executed | no | `RELEASE_TRIAL_STATUS_INVALID` | CI regenerates from `reward.json` (deferred) |
| Repeated attempts go unnoticed | no | candidate static probe plus separately governed observer rerun and durable incident and repeat-alert state; local `SAB_REPEATED_ATTEMPT` remains a diagnostic BLOCK | GitHub App bridge, observer, durable state, rulesets, and monitoring deployment |

The honest limit: if the org admin is the adversary, every anchor above is theirs; the residual defenses are client-side re-execution and a transparency log outside the org, and `DEFERRED.md` should say so.

## 7. What landed today

Six stdlib-only modules under `tools/`, each registered in `PARENT_CHECKS` of `tools/integrity.py`; the suite passes at over eleven hundred tests, ruff and mypy clean.

| Module | Refusal codes | Tests |
| --- | --- | --- |
| `tools/release.py` | `RELEASE_VERDICT_NOT_SHIP`, `RELEASE_EDICT_NOT_SHIP`, `RELEASE_DISPOSITION_UNBOUND`, `RELEASE_EXPORT_MISMATCH`, `RELEASE_ORACLE_RECEIPT_MISSING`, `RELEASE_ORACLE_RECEIPT_INVALID`, `RELEASE_REWARD_SCHEMA_AMBIGUOUS`, `RELEASE_TRIAL_STATUS_INVALID`, `RELEASE_WAIVER_INVALID`, `RELEASE_DIRTY_TREE` | 60 |
| `tools/sabotage.py` | `SAB_DISPOSITION_UNBOUND`, `SAB_DISPOSITION_FORGED`, `SAB_INERT_INSTRUMENT`, `SAB_AUDIT_UNCOMMITTED`, `SAB_SUBMODULE_REMOTE`, `SAB_SUBMODULE_OFF_MAIN`, `SAB_SUBMODULE_UNVERIFIED`, `SAB_TYPED_SIGNOFF`, `SAB_WORKFLOW_TAMPER`, `SAB_DIRTY_TREE`, `SAB_READ_ERROR` | 38 |
| `tools/sentinel.py` | thirteen `SAB_` intent codes with weights including `SAB_REPEATED_ATTEMPT`, `SENTINEL_CHAIN_BROKEN`, `SENTINEL_CHAIN_ROLLBACK`; `record`, `verify`, `clear`, `status` | 37 |
| `tools/harbor.py` | `HARBOR_PIN_MISSING`, `HARBOR_PIN_MALFORMED`, `HARBOR_PIN_STALE`, `HARBOR_PIN_UNTESTED`, `HARBOR_LOCK_MISSING`, `HARBOR_LOCK_MALFORMED`, `HARBOR_LOCK_STALE`, `HARBOR_SCHEMA_DRIFT`, `HARBOR_SCHEMA_INVALID`, `HARBOR_RECEIPT_TAMPERED`, `HARBOR_RECEIPT_MISSING`, `HARBOR_VALIDATOR_UNAVAILABLE`; `resolve`, `validate`, `migrate` | 53 |
| `tools/pipeline.py` | `PIPELINE_CHAIN_BROKEN`, `PIPELINE_SEALED_MUTATED`, `PIPELINE_UNSEALED_AUDIT`, `PIPELINE_BACKPRESSURE`, `PIPELINE_STALE_CLAIM`, `PIPELINE_CONFIG_INVALID`; `seal`, `pending`, `claim`, `verify` | 22 |
| `tools/gate.py` | `GATE_PREFLIGHT_MISSING`, `GATE_DISPOSITION_MISMATCH`, `GATE_HOOK_MISSING`; ceiling `BLOCK`, `HOLD`, `SHIP_ELIGIBLE`; `promote` | 32 |

A sixth module answers how a pasted contract reaches candidate qualification. `tools/gate.py` is the command every ENGRAM, FORGE, or CRUCIBLE invocation runs at moment preflight before phase work and at moment report before the root report; it runs registered parent checks, records local sabotage-class refusals, writes a receipt under the instrument's harness, and mints a record at the closed ceiling `BLOCK`, `HOLD`, or `SHIP_ELIGIBLE`, never final SHIP. The root report copies that word. The earlier one-approver signing instruction is superseded: current final `trinity.release-disposition/v2` FORGE and CRUCIBLE records bind snapshot and candidate identity in separate payload domains, producer and approver independently create partial signatures with `gate.py sign-partial`, and `gate.py cosign-assemble` combines only exact matching payloads. Candidate qualification remains distinct from governance publisher authorization. See `docs/hostile-operator-hardening.md` for the current deployment and co-signing procedure.

At the historical stage recorded by this section, candidate installation covered both workflow claims and nothing was sent anywhere; an uncleared repeat was only a refusal. That statement is historical, not current deployment guidance. Today `tools/gate.py install` installs only candidate qualification surfaces: local static `sentinel.yml`, `pre-push`, CODEOWNERS, candidate branch protection, and receipts. It never installs `release-gate.yml` or `sentinel-observer.yml`. `check_gates_installed` compares the legacy candidate scaffold with source templates and cannot prove external installation. Governance must separately deploy the publisher workflow, GitHub App bridge, observer workflow, durable incident state, repository rulesets, and operational monitoring described in `docs/hostile-operator-hardening.md`.

Pipeline mode makes `.podium/queue.jsonl` the only FORGE-to-CRUCIBLE channel: FORGE seals each slot when its Phase 2 Bucket D passes, CRUCIBLE claims with an `O_EXCL` file and audits exactly the sealed digest, MAESTRO is the sole committer, and the closed queue schema admits no finding or pass criterion. First-verdict latency drops from one batch plus one audit to one slot plus one bundle audit; unaudited depth is bounded at eight.

## 8. What is still owed

| Priority | Item | Effort |
| --- | --- | --- |
| P0 | **SUPERSEDED:** do not install `release-gate.yml` in any parent or samples repository. Run candidate preflight only for local static `sentinel.yml`, hook, CODEOWNERS, candidate protection, and receipts; separately deploy the governance publisher and observer stack from `docs/hostile-operator-hardening.md` | Re-estimate after governance ownership, repository ids, pins, bridge, runners, and rulesets are assigned |
| P0 | **SUPERSEDED:** `trinity.oracle-run/v1` is invalid. Establish closed `trinity.release-policy/v2`, rerun every mandatory core control with the external quality-controls runner, emit newly signed `trinity.oracle-run/v3` receipts under one manifest closure, and create new domain-separated co-signed `trinity.release-disposition/v2` records as specified in `docs/hostile-operator-hardening.md` | Re-estimate after the absent quality-controls runner exists; the 12 unbuildable bundles still dominate execution effort |
| P0 | Harbor migration of the 24 manifests with `harbor.py migrate --write`, re-validate at 0.23.0, re-sign | 1 d |
| P1 | Cheap-adversary probe execution for the `G-ADV` family CRUCIBLE step 8t now states, private to `.audit/adversary/` | 8 d |
| P1 | `G-STMT-GRADER-RECONCILE`, then `G-ALT-SOLUTION` and `G-MUTANT-LADDER` | 4.5 d, then 6 d plus 2 to 6 h authoring per bundle |
| P1 | Judge discipline: `tests/judge/` in the bundle, ten checks in `tools/judge_discipline.py`, backfill across ten families | 1 week plus 1 to 2 d per family in parallel |
| P1 | Org trust root: allowed signers and role roster under research CODEOWNERS; genesis inside a parent refused | 3 d |
| P1 | Execution attestation blocking when SHIP or rollouts exist; CI re-executes a sampled rollout | 4 d |
| P2 | Section 1 and 5 static checks: image pull, compose closure, verifier file closure, build discipline, network enforcement, phase isolation | about 60 h |
| P2 | Ledger Merkle recomputation, signed-commit requirement on governed paths, sabotage ledger repo | 6 d |
| P3 | Timestamp anchoring, Trinity `main` ruleset, and the `DEFERRED.md` section 10 row exits as each check above lands; the contract sentences for every item in this table are already in place | 2 d |

## 9. Client Reviewer Playbook

CRUCIBLE runs forty steps on the exact bytes to be pushed, from a clean host holding only the `<name>-samples` commit, stock Harbor, and no credentials. Stage 1, builds and scores: anonymous pull, cold build on two architectures, Harbor validation, grader closure, non-empty test channel, oracle at full reward five times, base commit ten times, measured model three times. Stage 2, passable without work: no-op, known-wrong controls, negation, self-report, test tamper, garbage input, format floor, container leak sweep, public-corpus check. Stage 3, correct work scores: oracle mutants, partial-credit ladder, instruction obedience, test-scope trace, statement closure. Stage 4, judge: shipped, rerun five times, never outscoring a failing test, complete input, criteria traceable to the statement. Stage 5, provenance: pins, network use, phase isolation, resource ceilings, timeouts, secrets, trajectory forensics. Stage 6, reporting: one reward field, invalid trials classified, calibration, near-duplicates, pushed hash equals audited hash. Exit rule: one row per step per bundle bound to the delivery SHA; any FAIL in stages 1 to 4 or any GAP in stages 1 to 3 means no push. Stage 1 alone would have stopped nine bundles at its first step on 09-07.

## 10. Resubmission plan

1. Freeze: tag every parent and `<name>-samples` repo at the delivered commit so the client's citations stay resolvable.
2. **SUPERSEDED:** do not install both workflows in a parent. Vendor current `trinity/` and run candidate preflight only for local static `sentinel.yml`, the hook, CODEOWNERS, candidate branch protection, and receipts. Separately deploy `release-gate.yml` in the governance publisher repository and the current transport-free `sentinel-observer.yml` in the governance observer repository with the GitHub App bridge and identities required by `docs/hostile-operator-hardening.md`; `check_gates_installed` cannot prove those deployments.
3. Run `integrity.py parent` on each parent; the refusals are the work list, and every unsigned SHIP line is now `SAB_DISPOSITION_UNBOUND`, the correct state for all ten.
4. Migrate manifests: `harbor.py resolve`, `harbor.py migrate --write` on the 30 bundles, `harbor.py validate` at 0.23.0, commit receipts.
5. Make the twelve unbuildable bundles build: public digest-pinned images for argos, levi, thanatos; a build context for yuji's MCP server; deku's three grader modules; a non-empty test channel for thanatos; the cwd fix for envora xarray.
6. **SUPERSEDED:** three local runs are not release evidence. Under governance-owned `trinity.release-policy/v2`, use the external quality-controls runner to execute every required control, including all five mandatory core controls, and issue a newly signed `trinity.oracle-run/v3` receipt with exactly one acceptable outcome per control under the common manifest closure. The runner remains absent, so this step currently fails closed.
7. Run playbook stages 2 and 3 against each verifier; fix teresa's negation hole, anubis's self-report grader, envora's hook surface, kakashi's reproducer weight, kanao's floors and colinear tests, and the hidden-identifier tests in argos, levi, envora, and teresa.
8. Ship the judge inside each bundle under `tests/judge/` with pinned model, temperature, and seed, and re-run at eleven trials per item; move judged share under the cap or declare reliability.
9. Move rollouts and `solution/` out of the agent-visible export into `<name>-deliverables`, tag vacuous runs `trial_status: invalid`, declare one reward field, regenerate every README from `reward.json`.
10. **SUPERSEDED:** no signed or expiring waiver may release. After substantive FORGE and CRUCIBLE qualification, compute the complete export snapshot and candidate binding, create separate closed `trinity.release-disposition/v2` records, have producer and approver independently run `gate.py sign-partial`, assemble exact matching instrument-domain envelopes with `gate.py cosign-assemble`, and submit them with current v3 receipts to the separate governance publisher. Missing execution evidence remains HOLD or BLOCK. Follow `docs/hostile-operator-hardening.md`; any `.audit/release-waiver.json` is `RELEASE_WAIVER_INVALID`.
11. Deliver the parent `VERDICT.md`, `EDICT.md`, and the playbook result beside the bundles, so the next reviewer sees the disposition, not a README.

## 11. Addendum, 2026-09-16: external authority and remaining rollout

This addendum records the current repository after the events and implementation counts above; it does not rewrite what was true when the delivery occurred. Release validation now requires `release-gate.yml` deployed only in a separate governance publisher repository, immutable candidate and export snapshots, governance-owned repository identities and verifier and trust pins, closed `trinity.release-policy/v2`, complete export snapshot and immutable candidate binding, separate co-signed FORGE and CRUCIBLE `trinity.release-disposition/v2` domains, and authorized `trinity.oracle-run/v3` receipts. Release waivers are categorically refused, so the waiver route in section 10 step 10 is superseded: operational acceptance stays attached to the capped disposition and never becomes SHIP.

The v3 receipt verifier requires exactly one outcome for every policy-required control under a common manifest closure and makes all five core controls mandatory, with only trusted policy able to mark the judge control non-applicable. Missing, failed, skipped, deferred, waived, duplicate, or extra outcomes refuse release. The external execution signer is trusted to have observed those controls. The release verifier checks signed observations and does not run Harbor or independently prove execution. The external quality-controls runner remains absent, and the full cheap-adversary matrix, three alternate correct solutions, mutant ladder, graded-literal reconciliation, and independent judge replay described in sections 8 and 9 remain blocking until that runner and its genuine evidence exist.

**SUPERSEDED transport note:** the earlier addendum described a separate delivery job and queue. The active design removes that transport entirely. Candidate `sentinel.yml` remains a secretless static diagnostic and never runs candidate scripts. Repeated affirmative integrity findings are suspected tampering, not proof of intent. The authoritative observer requires an allowlisted GitHub App bridge, authenticates sender and observer-source identities and API-resolves target run identity, reruns `incident_probe.py` read-only before admission, and stores incidents, equivocations, and repeat alerts in durable external SQLite state with no delivery or reset command. No claim is made here that the bridge, App token, allowlists, repository rulesets, observer runner, durable volume, monitoring, external quality-controls runner, trust enrollment, or publisher service were configured in this session.

## 12. Addendum, 2026-09-18: measurement fidelity and the resubmission statement

This addendum reports one defect the client assessment did not name, which this repository found afterwards in the delivered bytes, and states what landed against it. It adds to sections 1 through 11 and rewrites none of them. The closed taxonomy, the arithmetic, and the per-family evidence rules behind every sentence here are in `docs/measurement-fidelity.md`.

The ground truth is one line of a raw agent log. `agent.jsonl:174` in the kakashi delivery carries a system event of subtype `compact_boundary` whose `compact_metadata` records `trigger:auto` and `pre_tokens 168780`. The vendor inference harness summarized and discarded the solver's earlier context mid-rollout, without the solver's consent and without a declaration anywhere in the bundle.

The scope is counted and not estimated. In the kakashi delivery 11 of 24 runs compacted across 18 events, every one of them at `trigger:auto`, with `pre_tokens` between 167,075 and 173,539. That band sits against 168,000 tokens of headroom, a declared `contextWindowTokens` of 200,000 less a `maxOutputTokens` of 32,000, so these are the harness meeting its own configured ceiling and not a stray incident. Across the anubis, envora, kakashi, and yuji deliveries the normalized marker "This session is being continued from a previous conversation that ran out of context" appears in 57 of 344 normalized trajectory files, a rate of 16.6 percent. Rollouts of glm-5.3 carry the same marker, inherited through the Claude-Code protocol bridge those deliveries reached by an ANTHROPIC_BASE_URL override, so the defect crosses model families and a reader keyed to one family misses it.

The decisive finding is a false negative, and it is why the delivered artifacts could not have surfaced this on their own. The field `result.json.agent_result.metadata.summarization_count` reads 0 in all 296 `result.json` files in the corpus, because `enable_summarize` is false. Any detector reading `result.json` therefore reports zero compaction, and that report is false while the raw agent log proves compaction happened. A self-reported zero is not evidence of absence.

The direction of harm runs opposite to the intuition, and it is the part that matters for this delivery. FORGE rule 2f releases a slot only when the Bonferroni-corrected Clopper-Pearson upper bound on every primary solver's pass-at-8 rate stays strictly below the measured pass ceiling, whose default is 0.40. Suppressed context lowers measured capability, lower measured capability lowers that upper bound, and a lower upper bound crosses below the ceiling and releases the task. The defect did not make tasks look easier and get caught. It made them look harder and pass. Suppression is therefore an adversarial vector with a free win rather than a quality nuisance, and this repository carried no symmetric refusal, because `HOLD:MISCALIBRATED` fires only when a task measures easier than declared.

An independent arithmetic finding sits underneath all of it and does not depend on compaction at all. Eight runs per configuration is one pass@8 group and not eight groups, so the delivered evidence fails FORGE's own group requirement before fidelity is considered. The contract's fixed eight-group minimum is itself infeasible. For a group tally with zero flagged groups the one-sided Clopper-Pearson upper bound is U(0, N) = 1 - alpha^(1/N), release requires U below the ceiling c, and that solves to N > ln(alpha) / ln(1 - c), where alpha is the per-comparison error rate and N is the group count. At a ceiling of 0.40 and a familywise alpha of 0.05 the required group count rises with the comparison family M.

| Comparison family M | Alpha per comparison | Required N | Eight groups sufficient |
| --- | --- | --- | --- |
| 1 | 0.05 | 6 | yes |
| 4 | 0.0125 | 9 | no |
| 7 | 0.00714 | 10 | no |
| 8 | 0.00625 | 10 | no |
| 16 | 0.003125 | 12 | no |

M is the attempt budget times the count of primary solvers, so any realistic pilot reaches an M of at least 4, and once M reaches 7 the requirement is 10 groups. Eight groups can never clear the ceiling, even on a flawless pilot in which every group fails. The hardcoded eight therefore becomes the computed `measured_group_floor`, the larger of eight and the count the ceiling and the corrected confidence require, landed in `tools/stats.py` at commit 58c2737.

What this repository now refuses, and did not refuse when the bundles were pushed on 2026-09-07, is the following. Commit e03cd25 registered `HOLD:SUPPRESSED_MEASUREMENT` and `BLOCK:INVALID_PILOT` in the closed disposition vocabulary and refused fidelity-detector reason vocabulary in the author contract, so an author can never write toward the detector. Commit 8a5ab04 added the execution-fidelity boundary to CRUCIBLE and registered the `G-FID` instrument family, and commit 9f97801 bound group-level release, symmetric suppression, and harness-configuration pinning into FORGE. `trinity.harness-config/v1` landed as a closed schema at 1716ec0 and gained drift refusal and a separated adequacy block at 4271b75, so a configuration that is missing, unbound, unapproved, contradicted by the attested effective one, or carrying no adequacy declaration is refused rather than assumed. `trinity.pilot-policy/v2` landed at 41b801b with fixed groups and a pre-execution feasibility precheck, and `trinity.pilot-attempt/v2` landed at a3bb81f with disjoint groups and a per-trial conformance token. `trinity.execution/v2` landed as a predicate carrying fidelity telemetry at c8f01d7 and became required for release, with the version 1 downgrade refused, at 3c5502d. The three-valued forensics core and its coverage predicate landed at 9fe4c4f, five per-family trace adapters at b2a9f3a, per-family evidence contracts at 034be9b, and both-halves fixtures with a reachability matrix at 4eb19ad, so a missing marker, an unsupported harness version, a conversion-only trace, or a self-reported zero resolves as INSUFFICIENT_EVIDENCE and never as clean. Commit a030beb moved the pilot evaluator onto worst-case group accounting, in which an invalid group counts against release instead of leaving the denominator.

Two schema bumps this work depends on are scheduled and are not in the repository on 2026-09-18. `trinity.oracle-run/v4` and `trinity.release-policy/v3` carry `execution_fidelity` as a sixth mandatory core control that trusted policy may never mark non-applicable, and both are specified in `docs/measurement-fidelity.md` and unimplemented. Until they land, execution fidelity binds the authoring and audit surfaces and does not yet bind the release receipt, and nothing in this section should be read as claiming otherwise.

Backfill is diagnosis and never retroactive attestation. `tools/backfill.py` landed at commit 509cb01 and reads historical rollouts to report exactly one of three dispositions per bundle, `confirmed_suppression`, `unknown_coverage`, or `insufficient_groups`, beside a fixed headline stating that eight rollouts per configuration form one pass@8 group. Every record it emits carries an `authority` field reading "diagnosis only; fresh independent pilots required, never retroactive attestation", and the module refuses to write under `.seed/` or `.audit/attestations/` at all. No historical bundle receives an attestation, no historical outcome is upgraded, and every claim the delivered history cannot support needs a fresh independent pilot. Its worst-case bounds impute every unverified historical outcome as a success, and the groups it derives are not a precommitted or independently verified population, so its numbers are a floor on the problem and never a certificate.

What remains outstanding is named in `DEFERRED.md`, which gained six rows at commit c29b4dc and retired one at a030beb. Three concern the capture of evidence: observation capture precedes operator editing, at CRUCIBLE step 8p; effective request and response capture, at CRUCIBLE step 8u and the `G-FID-TRACE` instrument; and provider-internal routing declared and verified. Three concern the pilot itself: a precommitted population roster reconciled against realized groups, at FORGE rule 2f; configuration adequacy judged by a governance authority, at FORGE Phase 4 item 3a; and an independent execution authority in effective control of admission, execution, observation, and custody, at FORGE Phase 4 item 2b. The retired row is the pilot evaluator that applies the exact binomial bound and the minimum rollout count, which left the register at a030beb because code now evaluates its predicate.

The client should read those six plainly. No independent execution authority exists. No component records the effective request as submitted or the response as returned, so every adapter reads a log the executing party wrote. No roster is committed by a principal outside this repository. Whether a declared headroom is adequate for the task it runs is not decidable from disk. Provider-internal routing stays a declared trust assumption and never a verified fact. Where no authority controls admission, execution, observation, and custody together, independent re-execution is the minimum replacement measurement, and that is what a resubmission has to buy.

2026-09-18 superseding note: the `trinity.oracle-run/v4` and `trinity.release-policy/v3` bumps described above as scheduled have now landed in this commit.
