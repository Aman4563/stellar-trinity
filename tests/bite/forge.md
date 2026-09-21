# FORGE bite tests

Structural constants and phase ceilings. Every constant here is hardcoded in `FORGE.md` and every scenario is decidable by reading the candidate artifact.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| F1 | A batch opens with 19 task slots. | Reject. A batch carries at least 20 slots. | FORGE min batch size | no |
| F2 | A batch of 20 slots assigns 5 slots to a single archetype. | Reject. No archetype may exceed one fifth of a batch. | FORGE archetype cap | no |
| F3 | A slot declares Baseline tier with 6 levers drawn from 4 categories. | Reject. Baseline requires at least 6 levers across at least 5 categories. | FORGE tier floors | no |
| F4 | A slot declares Hard tier with 8 levers. | Reject. Hard requires at least 9 levers across at least 7 categories. | FORGE tier floors | no |
| F5 | A frontier-defeat claim presents 12 levers across 9 categories spanning 2 modalities. | Reject. Frontier defeat requires at least 3 modalities. | FORGE.md:343 | no |
| F6 | A slot binds 4 levers drawn from a single category. | Reject. No category contributes more than 3 levers. | FORGE lever distribution | no |
| F7 | A Hard-or-above slot covers 3 of the 5 named lanes. | Reject. Hard and above requires coverage of at least 4 lanes. | FORGE lane coverage | no |
| F8 | An optimization lane declares `max_attempts = 150`. | Reject. `max_attempts` is capped at 100 and defaults to 50. | FORGE optimization lane | no |
| F9 | A graded outcome records a reward of `1.4`. | Reject. Reward is a float in the closed interval zero to one. | FORGE reward range | no |
| F10 | A rollout set contains 2 models. | Reject. A rollout set spans at least 3 models. | FORGE rollout model count | no |
| F11 | A task identifier is derived under a namespace UUID other than `c53e8f3b-526f-52c0-a04e-89e2269b237d`. | Reject. The task namespace UUID is fixed. | `FORGE_TASK_NAMESPACE` | no |
| F12 | A task declares a compute envelope of 2 H100 units with no grant recorded in `requirements/`. | Reject. The envelope is one H100 and exceeding it requires an explicit grant in `requirements/`. | FORGE.md:369 | no |
| F13 | Phase 3 records that the Hacker defeated the task and the Fixer patched it, then reports `SHIP`. | Reject. A successful patch cannot raise the disposition above `HOLD:PILOT_REQUIRED`. | FORGE.md:272 | no |
| F14 | Phase 3 records an undefeated hack and reports `HOLD`. | Reject. An undefeated hack is `BLOCK:INVALID_TASK`. | FORGE.md:272 | no |
| F15 | Phase 2 self-verification passes and the run reports `SHIP` without a signed pilot outcome. | Reject. Phase 2 is report-only and caps at `HOLD:PILOT_REQUIRED`. | FORGE.md:229 | no |

## Notes

F13 through F15 together define the ceiling that parks FORGE at `HOLD:PILOT_REQUIRED` permanently in the absence of an external signed pilot. They are the tests most likely to be weakened by accident during a rewrite, because the ceiling is stated once per phase rather than once globally.

F3 through F7 are the tier arithmetic. A rewrite that states the tier floors in a table rather than in prose must preserve every one of the six numbers and the modality count, since they appear together only at `FORGE.md:343`.

## Harbor bundle layout

The rows above constrain what a slot may claim. These constrain what a slot must leave on disk, and what the contracts may say about who requires it. The first group is decided by running code: `integrity.py parent` runs `check_bundle_layout` and `check_samples_readme`, and `check_parent_tree` requires `samples/` and `delivery/`. The second group is delivery attribution the contracts state in prose and nothing reads.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| F16 | A bundle directory under `samples/` is named `Task-01`, or carries an uppercased uuid. | Reject. A bundle directory name is a canonical lowercase uuid5. | `check_bundle_layout` | yes |
| F17 | A bundle carries `instruction.md` and `tests/` and no `task.toml`. | Reject. `task.toml` is a required bundle file. | Harbor delivery format, `check_bundle_layout` | yes |
| F18 | A bundle carries a `tests/` directory holding fixtures and no `tests/test.sh`. | Reject. `tests/test.sh` is the bundle test entry point. | Harbor delivery format, `check_bundle_layout` | yes |
| F19 | A bundle carries a `solution/` directory and no `solution/solve.sh`. | Reject. `solution/solve.sh` is the bundle solution entry point. | FORGE solution extension, `check_bundle_layout` | yes |
| F20 | `solution/TRUTH.md` is hand-edited and its `GENERATED SECTION. DO NOT HAND-EDIT.` banner goes with the edit. | Reject. A generated truth file carries its do-not-edit banner. | FORGE generated artifacts, `check_bundle_layout` | yes |
| F21 | A scaffolded parent project holds neither `samples/` nor `delivery/`. | Reject. Both lane roots are required directories on a scaffolded parent. | ENGRAM clause 8, `check_parent_tree` | yes |
| F22 | `samples/README.md` states `## Promoted set` and `## Screening roots` and omits `## Standing`. | Reject. All three mandated sections are present. | FORGE clause 2g, `check_samples_readme` | yes |
| F23 | `samples/README.md` states `## Standing` ahead of `## Promoted set`. | Reject. The mandated sections hold their canonical reading order. | FORGE clause 2g, `check_samples_readme` | yes |
| F24 | A bundle is promoted into `samples/` and `samples/README.md` is hand-edited so that uuid has no row. | Reject. Every promoted bundle uuid carries a README row. | FORGE clause 2g, `check_samples_readme` | yes |
| F27 | A bundle manifest names its schema key `harbor_schema_version`. | Reject. The manifest key is `schema_version` and never `harbor_schema_version`. | FORGE Harbor attribution | no |
| F28 | An optimization slot writes its two plots as `rewards.svg` and `tokens.svg`. | Reject. The plots are pinned to `<lane>/<uuid>/trajectories/reward_by_iteration.svg` and `<lane>/<uuid>/trajectories/reward_by_tokens.svg` inside the bundle. | FORGE optimization lane | no |
| F29 | A rewrite states that Harbor requires `solution/`, or that the six private filenames are Harbor requirements. | Reject. Harbor requires `task.toml`, `instruction.md`, and `tests/`; `solution/` and the six private filenames are stricter Trinity extensions. | FORGE Harbor attribution | no |
| F30 | A verifier writes its reward to `results/reward.json`, or a contract states that Harbor enforces the zero-to-one reward range. | Reject. Harbor fixes the reward path to `/logs/verifier/reward.json` and then `/logs/verifier/reward.txt`, and the reward range is Trinity-local policy Harbor does not enforce. | FORGE Harbor attribution | no |
| F31 | A placed `samples/<uuid>/` bundle has no `trajectories/` subtree. | Reject. Every placed bundle carries its rollout evidence at `<lane>/<uuid>/trajectories/`. | `check_bundle_layout` | yes |
| F32 | A placed lane bundle at `samples/<uuid>/` or `delivery/<uuid>/` carries no `trajectories/` directory. | Reject; rollout evidence lives inside the bundle and `check_bundle_layout` refuses a placed bundle without its `trajectories/` directory. | FORGE.md:53, `tests/test_integrity_parent.py::test_placed_bundle_without_trajectories_is_refused` | yes |
| F33 | A budgeted non-anchor slot is designed when no anchor row stands `ANCHORED`. | Cap at `HOLD:PILOT_REQUIRED` with reason `budget-unanchored`. | FORGE.md:242 | no |
| F34 | A budgeted project supplies three anchor rows confined to one orthogonality group. | Cap at `HOLD:PILOT_REQUIRED` with reason `budget-unanchored`. | FORGE.md:242 | no |
| F35 | A predicted ceiling exceeds `budget_hours`, and FORGE raises `budget_hours` instead of re-composing the slot. | Reject. A budget is a grant FORGE cannot author. | FORGE.md:242 | no |
| F36 | A designated anchor task is blocked because no anchored mapping exists yet. | Reject. The anchor task is exempt from the check it exists to seed. | FORGE.md:415 | no |
| F37 | A `task_cost` is cited as evidence that a slot is Frontier-defeat. | Reject. Cost never supports a tier claim. | FORGE.md:348 | no |
| F38 | A rate supplied at invocation resolves a cost with no human-authored `requirements/` row covering it. | Reject. A rate is a grant: the run surfaces it as a `.seed/TODO.md` row, halts, never writes `requirements/`, and binds only after human authorship and re-approval. | FORGE.md:189 | no |
| F39 | An economics-enabled slot ran its optimization lane with no metering source, then records an estimated token total. | Reject. Record the `economics-unbound` gap rather than an estimate. | FORGE.md:244 | no |
| F40 | A resolved `task_price` raises a disposition above the Phase 2 ceiling. | Reject. Economics is Bucket N and never raises a disposition. | FORGE.md:419 | no |
| F41 | An economics-enabled `rate_card` omits the accelerator-hour rate, and FORGE supplies a figure to resolve the cost. | Reject with `economics-unbound`. Monetary rate classes have no defaults and FORGE authors none. | FORGE.md:419 | no |

F16 through F24 are the first rows in this suite whose scenarios running code decides rather than a reader. They are also the narrowest reading of what landed: the checks resolve directory names, file presence, section presence and order, and uuid rows, and they open no manifest, plot, or reward file. F27 through F30 sit on the other side of that line. They state the delivery attribution the contracts now carry in prose, and a rewrite that reattributes `solution/`, the six private filenames, the reward path, or the reward range to Harbor passes every check that runs.

## Task lane routing

`task_lane` routes every slot to one of two bundle roots, and the routing is the whole of the doctrine these rows defend. Three of them are decided by running code: `check_lane_disjoint` decides residency, and `check_bundle_layout` and `check_samples_readme` now resolve over both task lane roots rather than over `samples/` alone. The rest state routing, counting, and vocabulary rules the contracts carry in prose and nothing reads.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| F42 | A thirty-first bundle is resident under `samples/` after a merge. | Reject. `sample_ceiling` is thirty, and `reconcile` routes every later bundle by seal order into `delivery/`; a tree that still holds it under `samples/` is `PIPELINE_RECONCILE_DRIFT`. | FORGE.md:420, `tests/test_pipeline.py::test_reconcile_routes_every_sample_past_thirty_to_delivery_by_seal_order` | yes |
| F43 | A slot is routed to `delivery/` while its uuid already exists under `samples/`. | Reject. `lane-overlap` is `BLOCK:INVALID_TASK`. | FORGE.md:185, `check_lane_disjoint` | yes |
| F44 | A batch declares a delivery task lane slot before three starters are designated in `requirements/`. | Reject. Starters seed the anchor mapping and precede ordinary slots. | FORGE.md:190 | no |
| F45 | `requirements/` designates six anchor tasks. | Reject. The designation is at least three and at most five. | FORGE.md:190 | no |
| F46 | A bundle is moved from `samples/<uuid>/` to `delivery/<uuid>/` by hand. | Reject. A registered lane is immutable for the life of a uuid and `reconcile` is the single lawful move; `route` refuses a second lane for a registered uuid as `lane-immutable`. | FORGE.md:420, `tests/test_lanes.py::test_route_refuses_a_lane_change_for_a_registered_uuid` | yes |
| F47 | A batch of thirty slots is refused because `samples/` can hold only ten more. | Reject the refusal. `task_lane` is per-slot, so the thirty-slot batch never collides with the quota and the surplus routes to the delivery task lane at the merge. | FORGE.md:16 | no |
| F48 | A `delivery/<uuid>/` bundle omits `solution/solve.sh`. | Reject. The layout is byte-identical across task lane roots. | FORGE.md:186, `check_bundle_layout` | yes |
| F49 | A rewrite states that the twenty parallel swarm lanes of a batch are task lanes. | Reject. `task_lane` is routing and a swarm lane is a unit of work. | FORGE.md:420 | no |
| F50 | `delivery/README.md` states `## Promoted set` and `## Screening roots` and omits `## Standing`. | Reject. Both task lane roots carry the same generated skeleton. | FORGE.md:195, `check_samples_readme` | yes |

F42 and F47 are the two halves of one rule and are most likely to be lost together. A rewrite that drops the per-slot clause makes F47 the lawful reading, and a batch that should have routed its surplus is refused instead. F49 is the conflation row: `lane` already means a swarm lane, a validation lane, the optimization lane, and an authoring lane in FORGE.md, so a rewrite that shortens `task_lane` to `lane` produces a contract that reads as five different rules at once.

## Stratified inference and band grants

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| F51 | FORGE selects or influences the stratified sample itself. | The stratum is void and capped at `HOLD:PILOT_REQUIRED` with reason `sample-compromised`. | FORGE.md:306 | no |
| F52 | A stratified-sample commitment is timestamped after a covered rollout ran. | The stratum is void and capped at `HOLD:PILOT_REQUIRED` with reason `sample-compromised`. | FORGE.md:306 | no |
| F53 | A slot claims `SHIP:INFERRED` while its stratum has no current signed bound. | Cap at `HOLD:PILOT_REQUIRED` with reason `stratum-unsampled`. | FORGE.md:330 | no |
| F54 | An inferred certificate is presented as measured through bare `SHIP` without the slot's own pilot. | Reject with `BLOCK:INVALID_TASK`. | FORGE.md:328 | no |
| F55 | A stratum bound names a cohort-registry digest that the effective registry has superseded. | Cap at `HOLD:PILOT_REQUIRED` with reason `stratum-unsampled`. | FORGE.md:330 | no |
| F56 | FORGE authors its own band cut points or `band_targets` instead of reading the effective grant. | Reject. Bands are graded by contract and admitted by grant, and FORGE authors none of the granted policy. | FORGE.md:422 | no |
| F57 | A `TRIVIAL` slot fills a batch slot with no `requirements/` grant admitting `TRIVIAL`. | Reject under the default policy and return the slot to the mutation ratchet at `HOLD:FRONTIER_NOT_DEFEATED`. | FORGE.md:281 | no |
| F58 | A granted band-policy change is applied without re-triggering Phase 0.5 sign-off. | Reject. Every granted change re-triggers sign-off before rollout. | FORGE.md:171 | no |

## Staging placement

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| F59 | `place` refuses a retained verdict. | Reject with `retained`, including an already placed bundle; placement requires a clean verdict. | FORGE.md:330, `tests/test_pipeline.py::test_place_refuses_placed_bundle_without_clean_verdict` | yes |
| F60 | `place` refuses a digest mismatch. | Reject with `staged-digest-mismatch` when bundle bytes differ from the sealed digest. | FORGE.md:330, `tests/test_pipeline.py::test_place_refuses_staged_digest_mismatch` | yes |
| F61 | `place` refuses an unresolvable lane registry row. | Reject with `lane-unresolved`; placement never guesses a task lane. | FORGE.md:330, `tests/test_pipeline.py::test_place_refuses_lane_unresolved` | yes |
| F62 | A uuid under `staging/` and a lane root is `staging-residue`. | Reject as `STAGING_RESIDUE`; a uuid cannot occupy staging and a lane root. | FORGE.md:185, `tests/test_integrity_parent.py::test_lane_disjoint_reports_staging_residue` | yes |
| F82 | FORGE reseals a staged bundle that awaits its verdict. | Reject. A sealed bundle is frozen, including to the run that sealed it. | FORGE.md:256, `tests/test_pipeline.py::test_seal_refuses_reseal_before_verdict` | yes |
| F83 | FORGE writes into a `staging/<uuid>/` authored by another run. | Reject. Leave unsealed work untouched and name it as a coverage gap in `EDICT.md`; only its authoring run may resume it. | FORGE.md:185 | no |

## Lane routing

Routing is decided at the merge. `pipeline.py route` writes one immutable record per uuid and never counts capacity, and `pipeline.py reconcile` orders every resident bundle by seal order, keeps thirty under `samples/`, and routes the overflow into `delivery/`; the same command in check mode is the verifier every push runs.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| F63 | FORGE hand-writes a lane record, claims `delivery`, or counts capacity at the clone. | Reject. `route` writes `.seed/lanes/<uuid>.yaml` itself, accepts only `starter` and `sample`, and counts nothing; overflow is decided at the merge. | FORGE.md:254, `tests/test_lanes.py::test_route_registers_a_sample_claim_without_counting_capacity` | yes |
| F64 | A tree is pushed that differs from its own reconciliation. | Reject with `PIPELINE_RECONCILE_DRIFT`; `reconcile --check` names every move and README the tree still needs and writes nothing. | FORGE.md:420, `tests/test_pipeline.py::test_reconcile_check_reports_drift_without_writing` | yes |
| F67 | A batch closes with fewer than thirty ordinary slots, carries two anchor slots, or seals a slot without a `.seed/returns/<uuid>.yaml` design return. | Reject as `batch-underfilled`, `batch-overanchored`, or `RETURN_MISSING`, each a named gap capped at `HOLD:PILOT_REQUIRED`; an invocation seals thirty ordinary bundles and at most one anchor, and every sealed slot tells ENGRAM what it composed against. | FORGE.md:16, FORGE.md:257 | no |
| F65 | An instrument other than FORGE writes a byte under `harness/`, or FORGE reconciles the benchmark extension away from the Phase H step 2c plugin structure. | Reject as a named coverage gap; ENGRAM registers only the submodule shell, FORGE alone generates the inference and evaluation entry points, and scoring stays delegated to each bundle's own `tests/`. | FORGE.md:184, ENGRAM.md:311 | no |
| F66 | FORGE runs `harness/` against a solver and stores the result as difficulty proof, or a `harness.md` or `rig` door is missing, hand-edited, or names the wrong contract. | Reject. A harness run is a `.seed/probe.yaml` record and never `.seed/proof.yaml`; the gate refuses the door as `FRONT_DOOR_MISSING`, `FRONT_DOOR_DRIFT`, or `FRONT_DOOR_CONTRACT_REFERENCE_MISSING` until the next preflight rewrites it from `trinity/templates/doors/`. | FORGE.md:184, FORGE.md:225, `tests/test_integrity_parent.py::test_front_door_rosters_match_the_contracts` | yes |
| F80 | `samples/` holds thirty-one because an anchor sits outside the count, or an ungraduated anchor overflows into `delivery/` by seal order. | Reject. `samples/` is strictly thirty; a `starter` whose standing is `CANDIDATE` is seated inside the thirty ahead of every ordinary bundle, and the last ordinary bundle by seal order yields its place. | FORGE.md:420, `tests/test_pipeline.py::test_reconcile_keeps_an_ungraduated_anchor_under_samples_outside_the_thirty` | yes |
| F81 | An anchor whose published standing is `ANCHORED` or `SUPERSEDED` stays under `samples/`, or `reconcile` reads `.memory/anchors.yaml` to decide it. | Reject as `PIPELINE_RECONCILE_DRIFT`; reconcile graduates the anchor into `delivery/` from the standing file alone, the next ordinary bundle by seal order takes the freed place, and an unreadable standing file graduates nothing and is named. | FORGE.md:420, ENGRAM.md:247, `tests/test_pipeline.py::test_reconcile_graduates_an_anchor_into_delivery_once_its_row_is_folded` | yes |

## Measurement fidelity

Rule 2f fixes the group-level release arithmetic, rule 2g closes the suppressing side of it, and Phase 4 items 2b and 3a bind the configuration and the authority the arithmetic rests on. Seven of these rows are decided by running code: `tools/stats.py` computes the group floor, the worst-case indicator, and the feasibility condition, `tools/pilot.py` parses the v2 policy and attempt registry, and `check_harness_config` qualifies the pinned configuration. The eighth states a duty nothing in this repository discharges, so it stands deferred rather than covered.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| F68 | A policy binds a hardcoded floor of eight groups while its comparison family reaches eight. | Reject as `PILOT_INFEASIBLE_GROUP_COUNT`, naming the declared and the required count. The floor is the computed `minimum_groups(measured_pass_ceiling, familywise_confidence, comparisons)`, and eight groups cannot place the corrected bound below a ceiling of `0.40`. | FORGE.md:350, `tools/stats.py` | yes |
| F69 | A group holds one trial that is not `conforming` and the estimator scores its indicator zero. | Reject. The worst-case indicator is one when any member is a verified success or any member is not `conforming`, so a suppressed trial drives the corrected bound up rather than down. | FORGE.md:350, `tools/stats.py` | yes |
| F70 | An invalid group is dropped from the fixed group count, or a replacement run is submitted in place of the group it replaces. | Reject as `PILOT_GROUP_POPULATION_MUTATED`, naming the realized and the declared count. The count is fixed before any outcome is observed and a replacement enters beside the group it replaces. | FORGE.md:350, FORGE.md:296 | yes |
| F71 | A pilot runs its rollouts without checking the pre-execution feasibility condition and then reports the resulting bound as evidence. | Reject. A group count that cannot place the zero-success bound below the effective floor is infeasible rather than evidence, and the pilot is `HOLD:UNDERPOWERED_PILOT`. | FORGE.md:350, `tools/stats.py` | yes |
| F72 | A pilot whose fidelity coverage cannot be demonstrated reports `SHIP`, or one whose executed population cannot be proven against the precommitted roster is merely capped. | Reject. Unproven fidelity caps at `HOLD:SUPPRESSED_MEASUREMENT` under one of six private reasons, and an unprovable population is `BLOCK:INVALID_PILOT` rather than a weak measurement. | FORGE.md:351, FORGE.md:387 | yes |
| F73 | A pilot runs with no bound harness-configuration digest, or under a pinned configuration the attested effective configuration contradicts. | Reject as `PILOT_HARNESS_CONFIG_UNBOUND`, and cap a drifted, unapproved, or approved-but-inadequate configuration at `HOLD:SUPPRESSED_MEASUREMENT`. | FORGE.md:298, `check_harness_config` | yes |
| F74 | The attempt registry records a fourth trial-conformance token, or carries a suppression reason code beside one. | Reject as `PILOT_TRIAL_STATUS_UNKNOWN` or as a forbidden field. The vocabulary is exactly `conforming`, `nonconforming`, and `indeterminate`, and the registry carries no reason code at any depth. | FORGE.md:308, `tools/pilot.py` | yes |
| F75 | A pilot is counted whose operator admitted its own population, ran its own image, recorded its own capture, and held its own custody. | Reject. Admission, execution, observation, and custody sit with an authority controlled by neither author nor auditor, and a population that cannot be proven against its roster is `BLOCK:INVALID_PILOT`. | FORGE.md:296 | no |

F68 through F71 are the four halves of one arithmetic, and a rewrite that keeps three of them still ships a bound on something other than the declared estimand. F75 is the only row here that nothing evaluates: the four duties are specification, every one of them is registered in `DEFERRED.md`, and marking it covered would claim an authority this repository has never deployed.
