Filing: US Non-Provisional utility application (35 U.S.C. § 111(a)). Inventor: Sarvex Jatasra. Assignee: Ethara.AI. This is a prospective filing strategy and a draft, not a filing assertion. The ladder contains an apex system claim 1, mirrored method claim 19, mirrored storage-medium claim 20, and dependent claims 2 through 18. No claim is deleted once numbered; revision or an express supersession preserves its number. The proposed divisional or continuation relationship requires human review of actual priority support and any restriction requirement.

## Title

Primary: Canary-Normalized Write-Once Task Identity, Structural Lane Routing, Sealed Queues, and Epoch-Published Multi-Runner Memory for Machine-Learning Evaluation Bundles.

Alternative: Content-Bound Evaluation Bundles with Immutable Routing Classifications and Manifest-Bound Memory Publication.

## Abstract (proposed)

Systems maintain integrity of machine-learning evaluation bundles across concurrent runs. A canonical hash domain replaces designated canary values with placeholders while retaining slot structure. A digest determines a write-once task identifier and derived canaries in an acyclic hash, derive, plant, and bind sequence. A single task home excludes separately governed rollout evidence from task identity. A digest-bound lane classification and byte-derived residency govern deterministic placement under a structural ceiling. Runs prepare memory proposals against a current epoch; publication checks conflicts and produces an immutable successor with manifest-bound projections. Qualification may bind a computed subject closure rather than a repository tip. Closed queue streams, format-validation receipts, frozen tracker cards, clock-free report rendering, contained paths, and authority-preserving migration provide additional integrity controls.

## Apex pillars in independent claims

1. Canary-normalized canonical identity retains slot structure, derives both identifier and canary values from a digest, and orders hash, derive, plant, bind without circularity.

2. Write-once identity names a single authoritative home, while separately keyed rollout evidence holds no task bytes and has distinct write authority.

3. A closed lane classification binds at a digest gate before authoring, remains immutable for the identifier's life, and participates in deterministic placement based on committed-byte residency under a structural ceiling.

4. Parallel run proposals precede serialized memory publication into an immutable epoch with manifest-bound projections; publication validates current bases and conflicts before exposing the successor as current.

Deliberately excluded from apex: exact hash and identifier algorithms, queue envelope details, accepted-prefix checks, delivery-format pin cadence, namespace grammar, anchor graduation, subject closure, tracker cards, print-time derivation, hooks, merge-driver settings, direct-child root checks, submodule roster, and migration recovery. Claims 2 through 18 preserve these fallback combinations; configured counts and implementation names stay specification-only.

Named surfaces must be described only generically in claims: in one implementation, UUID version 5, SHA-256, `starter`, `sample`, `delivery`, the thirty-bundle ceiling, `staging/`, `samples/`, `delivery/`, `trajectories/`, `.seed/contract.yaml`, `.podium/queue/`, `.audit/queue.claims/`, and `<harness>/runs/<run_id>/` are illustrative vocabulary. The same applies to `.memory/proposals/`, `.memory/epochs/`, `.memory/views/`, `current.json`, `anchor_standing.yaml`, `run.json`, `report.md`, `progress.yaml`, `trinity.tracker-card/v1`, `TRACKING.md`, `trinity-generated`, `harbor.lock`, canonical `./`, `.trinity/migrations/`, and all `PIPELINE_`, `HARBOR_`, `EPOCH_`, `TRACKER_CARD_`, and `PARENT_LAYOUT_` refusal codes. Instrument labels and the roster size are likewise examples rather than claim limitations.

The word lane requires care. The current implementation distinguishes immutable admission classification from current physical placement. A legacy closed three-value vocabulary remains readable, but current author-side routing accepts only starter and sample classifications and reconciliation decides overflow. A claim that fixes the physical root forever conflicts with the graduation fallback; this ladder fixes classification and constrains every relocation instead.

## Claims

**1. A system for maintaining integrity of machine-learning evaluation bundles, comprising:** one or more processors; one or more non-transitory memories storing instructions that cause the processors to bind a lane classification from a closed vocabulary at a digest-bound approval gate before authoring bundle bytes; compute a task digest over a canonical domain that replaces designated canary-slot values with fixed placeholders while retaining slot quantities and positions; derive a task identifier from the task digest and a namespace pinned in approved scope, derive canary values from the task digest by a pure key-derivation function, plant the derived values after hashing, and bind the task identifier to the resulting representation in an acyclic hash-derive-plant-bind order; refuse reassignment of the task identifier to different normalized task bytes; maintain a single authoritative bundle home and a separately keyed rollout-evidence subtree holding no task bytes and governed by an evidence-write authority distinct from task-write authority; retain the lane classification for the life of the task identifier, re-derive residency from committed bytes, and select current placement by a deterministic reconciliation function that refuses duplicate residency and enforces a structural residency ceiling that no requirements grant relaxes; and prepare run-specific memory proposals against a current epoch, then serialize publication by validating proposal bases and conflicts, materializing an immutable successor epoch with a manifest, and publishing projections bound to a digest of the manifest before designating the successor as current.

*Drafting note (1):* Preserve the ordering, slot representation, split authority, re-derived residency, and manifest-digest projection binding. Parent claims 6, 21, 32, and 36 support related fragments, not automatic priority for the epoch combination. Application sections 8.3, 8.4, and 8.8 distinguish contract support from code. The shared tree hasher does not implement canary normalization, and local epoch publication does not serialize competing remote clones. The complete apex is a proposed combination, not a representation that the repository enforces every limitation today.

**2.** The system of claim 1, wherein the instructions further cause the processors to bind a normalization-domain version, retain slot ordering and surrounding bytes in the canonical domain, re-derive expected canary values from the task digest, and refuse a planted value that differs from its expected value even when the normalized digest matches.

*Drafting note (2):* This fallback closes the free-hole objection to normalization. Preserve both the digest comparison and the derivation relation; neither independently proves a valid planted marker. Support is contract-only in application section 8.3, not the raw tree-digest tests.

**3.** The system of claim 1, wherein the instructions further cause the processors to append seals to producer-run-specific hash-chained streams whose application payload consists of an identifier, bundle digest, seal instant, and producer run identity, reject an additional application field, maintain run-specific claim files, and refuse work violating a pending-depth bound or claim lifetime.

*Drafting note (3):* Closed application fields do not exclude sequence and hash-chain envelope fields. Claim-file creation is locally exclusive, not a distributed ownership proof. Application section 8.5 preserves the deferred timestamp-arbitration and admission boundaries.

**4.** The system of claim 3, wherein the instructions further cause the processors to require every accepted stream to remain an exact byte prefix of its proposed successor, refuse an unresolvable accepted revision, and refuse a push offering a non-deletion commit other than the local commit whose tree satisfies reconciliation checking.

*Drafting note (4):* Keep exact byte-prefix comparison rather than generic non-fast-forward refusal. A new descendant commit can replace a file with a valid newly computed chain. The offered-commit comparison prevents checking one commit while pushing another. The claim concerns the refusing mechanism, not an unbypassable deployed remote.

**5.** The system of claim 1, wherein the instructions further cause the processors to record a current stable delivery-format release from a package index in a dated lock, execute that format's validator under an exact release pin in an isolated interpreter, bind a validation receipt to manifest bytes and the pin, and refuse a stale or untested pin, stale lock, drifted schema, or inconsistent receipt.

*Drafting note (5):* Currency uses recorded release and age bounds, not continuous equality with a live package index. The actual implementation permits a bounded minor-version lag. A schema receipt is not an execution attestation or difficulty certificate. Support: application section 8.6.

**6.** The system of claim 1, wherein the instructions further cause the processors to mint a run identity once within a closed grammar, confine mutable private run state to the namespace of that identity, refuse reopening under a different declared owner, and maintain independent run streams whose merge preserves each stream's existing bytes.

*Drafting note (6):* The limitation says private run state because proposals, queue streams, bundle outputs, and serialized publication have distinct protocol paths. A declared owner is not an authenticated human. Namespace separation prevents ordinary write collision and does not promise confidentiality on a full clone. Support: application section 8.7.

**7.** The system of claim 1, wherein the instructions further cause the processors to refuse publication on conflicting proposals to a file or a proposal against a superseded epoch, publish anchor standing with the projections under the manifest-digest binding, and refuse a compatibility copy or projection that differs from the current epoch.

*Drafting note (7):* Identify file-level conflict rather than suggesting an automatic semantic merge. The current tool binds and copies projection bytes when present; it does not establish completeness or semantic recomputation of every projection. Local checking is implemented; complete serialized admission remains prospective. Support: application section 8.8.

**8.** The system of claim 1, wherein the reconciliation function seats ungraduated anchor bundles before ordinary resident bundles ordered by seal order, retains eligible residents up to the structural residency ceiling, and relocates overflow to another root without changing their task identifiers or lane classifications.

*Drafting note (8):* Use up to the ceiling because a sparse project cannot hold more bundles than exist. Current legacy residents without seals are fixed and counted first. Do not generalize the sealed ordinary-bundle order into a claim that every historical object has a seal. Support: application section 8.9.

**9.** The system of claim 8, wherein the reconciliation function graduates an anchor only when published anchor standing indicates that its duration row is folded into memory, relocates the anchor to free a resident seat without reading the underlying duration ledger, and refuses to infer graduation from unreadable standing.

*Drafting note (9):* The reduced standing file is the mover's input, not a new measurement. An unchanged lane classification can govern a different current root under the specified reconciliation function. Parent section 8.32 lacks this graduation detail; the source includes the changelog entry dated 2026-09-18. Support: application section 8.9.

**10.** The system of claim 7, wherein the instructions further cause the processors to qualify a run against a computed subject closure comprising its namespace inputs, sealed or judged bundle identities, human input roots, a consumed projection checked against the epoch, and a governing-specification gitlink rather than a repository tip, such that an unrelated commit outside the closure does not invalidate qualification and a change to an included input does.

*Drafting note (10):* Depending on claim 7 couples closure qualification to checked epoch integrity. The current subject manifest binds the consumed projection bytes, not an explicit epoch-manifest field. Seal verification separately recomputes live bundle bytes. Do not broaden output exclusions to accommodate late feedback or phase-receipt writes. Support: application sections 8.8 and 8.10.

**11.** The system of claim 1, wherein the instructions further cause the processors to emit at terminal run closure a write-once tracker card whose state fields derive from the run's identity record, report, and progress record and whose source bindings comprise their digests, preserve a recorded closing instant upon identical re-emission, and refuse changed sources, missing inputs, identity mismatch, or a malformed card.

*Drafting note (11):* State fields derive from the source records; the initial closing instant is recorded once and is not itself derived from those files. The lifecycle ADR treats a human gate as a pause without card emission. Its coordinated timing integration is contract-only, while immutable card checks exist. Do not turn a conflict into permission to relabel a paused run. Support: application section 8.11.

**12.** The system of claim 11, wherein the instructions further cause the processors to render a complete tracker from run cards and run reports without a run editing the tracker, derive its print instant from recorded disk state rather than a render-time wall clock, and produce byte-identical renderings for identical inputs.

*Drafting note (12):* The technical fallback concerns bytes and deterministic time input, not the visual section count. Preserve the distinction between creation-time event timestamps and render-time clock reads. A malformed card remains visible as unknown closure rather than a guessed success. Support: application section 8.11.

**13.** The system of claim 12, wherein repository hooks render generated report bytes into a working tree, compare expected report bytes with staged report bytes before a commit, and name differing paths for human action without staging, committing, amending, or pushing any bytes.

*Drafting note (13):* This is an affirmative restriction on the hook's write capability. Hook-generated bytes are not automatically staged. The staged-input check matters because a correct worktree report can still describe bytes absent from the proposed commit. Support: application section 8.11.

**14.** The system of claim 13, wherein repository attributes bind the generated reports to a merge driver that retains a local generated representation during merge and causes a subsequent whole-file rendering from merged source records, with staged-byte comparison refusing an obsolete representation.

*Drafting note (14):* The driver does not semantically merge prose. It retains disposable local output pending regeneration; subsequent hooks and staged checks close the binding. Do not describe an ordinary keep-local merge driver alone as an integrity verifier. Support: application section 8.11.

**15.** The system of claim 1, wherein the instructions further cause the processors to anchor path resolution to a trusted startup root whose direct child is a vendored governing-specification checkout, prevent candidate bytes from selecting that root, require canonical explicitly relative authored, persisted, and printed paths, and use absolute resolution only internally to refuse traversal and symbolic-link escape.

*Drafting note (15):* Distinguish trust in the orchestrator's startup root from proving every arbitrary agent uses the correct root. The CLI helper enforces canonical contained paths relative to a supplied root; the universal agent-scaffolding guard remains deferred. Support: application section 8.12.

**16.** The system of claim 15, wherein the instructions further cause the processors to require a closed roster of governing, memory, public-bundle, private-bundle, and execution-harness roots registered as submodules against distinct remotes, refuse parent-tracked task bytes and crossed root boundaries, and hold a retired evidence-mirror root pending reconciliation.

*Drafting note (16):* Categories describe functional roots without reciting implementation directory names or a numeral. The optional staging root and the empty-retired-directory case remain specification details. Distinct repository histories prevent a parent-only clone from automatically carrying private memory; initializing that private submodule remains a separate access question. Support: application section 8.12.

**17.** The system of claim 15, wherein the instructions further cause the processors to migrate project structure only through a closed supported version matrix under an exclusive lock, preserve immutable content-addressed backups, perform atomic writes with a resumable journal, and hold on an unknown version, unsafe path, changed evidence, unproved seal, or required revalidation.

*Drafting note (17):* Reconstructing the original plan from verified backups is the recovery mechanism, not trusting a journal because its own hashes agree. The lock is local migration exclusion, not the cross-clone epoch admission service. Support: application section 8.13.

**18.** The system of claim 17, wherein the migration preserves existing signed bytes without transferring their authority to changed bytes, creates no key, edits no approval or trust policy, changes no role membership or threshold, and withholds current acceptance until affected bytes satisfy ordinary validation, audit, and signing requirements.

*Drafting note (18):* Compatibility never grants authority. A supported legacy queue conversion can still conflict with accepted-prefix preservation and immutable task identity; it does not waive either invariant. Existing signed history may remain readable without authorizing transformed content. Support: application section 8.13.

**19. A computer-implemented method for maintaining integrity of machine-learning evaluation bundles, comprising:** binding, by one or more processors, a lane classification from a closed vocabulary at a digest-bound approval gate before authoring bundle bytes; computing a task digest over a canonical domain that replaces designated canary-slot values with fixed placeholders while retaining slot quantities and positions; deriving a task identifier from the task digest and a namespace pinned in approved scope and deriving canary values from the task digest by a pure key-derivation function; planting the derived values after hashing and binding the identifier to the resulting representation in an acyclic hash-derive-plant-bind order; refusing reassignment to different normalized task bytes; maintaining a single authoritative bundle home and a separately keyed rollout-evidence subtree holding no task bytes under evidence-write authority distinct from task-write authority; retaining the lane classification for the life of the identifier, re-deriving residency from committed bytes, and selecting placement by deterministic reconciliation that refuses duplicate residency and enforces a structural residency ceiling that no requirements grant relaxes; and preparing run-specific memory proposals against a current epoch followed by serialized publication that validates proposal bases and conflicts, materializes an immutable successor epoch with a manifest, and publishes projections bound to the manifest digest before designating the successor as current.

*Drafting note (19):* Mirror every apex pillar rather than claiming only the identity algorithm. A single platform operator can cause the operations through distinct logical write authorities. The pre-byte gate, final content binding, and publication-current-pointer ordering have different temporal positions. Their implementation labels remain the same as for claim 1.

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by one or more processors, cause the processors to maintain integrity of machine-learning evaluation bundles by:** binding a lane classification from a closed vocabulary at a digest-bound approval gate before authoring bundle bytes; computing a task digest over a canonical domain that replaces designated canary-slot values with fixed placeholders while retaining slot quantities and positions; deriving a task identifier from the task digest and a namespace pinned in approved scope and deriving canary values from the task digest by a pure key-derivation function; planting the derived values after hashing and binding the identifier to the resulting representation in an acyclic hash-derive-plant-bind order; refusing reassignment to different normalized task bytes; maintaining a single authoritative bundle home and a separately keyed rollout-evidence subtree holding no task bytes under evidence-write authority distinct from task-write authority; retaining the lane classification for the life of the identifier, re-deriving residency from committed bytes, and selecting placement by deterministic reconciliation that refuses duplicate residency and enforces a structural residency ceiling that no requirements grant relaxes; and preparing run-specific memory proposals against a current epoch followed by serialized publication that validates proposal bases and conflicts, materializes an immutable successor epoch with a manifest, and publishes projections bound to the manifest digest before designating the successor as current.

*Drafting note (20):* Keep non-transitory storage and executable operations, not a claim to disembodied instructions or a desired result. This independent claim mirrors the system and method limitations and inherits their written-description and implementation cautions; the medium form creates no additional priority or eligibility entitlement.

## §101 Alice positioning

Step 2A Prong Two for claims 1, 19, and 20: normalize, derive, compare, and refuse reassignment change how a machine identifies executable task bytes. Re-derive residency and refuse duplicate placement change permitted filesystem writes. Validate proposal bases and bind projections prevent consumption of mixed memory states. These are the independent-claim anchors in application section 8.15's prevention register.

Claims 2 through 5 add concrete refused artifacts: an incorrectly planted token, an extra-field seal, a rewritten stream, an unreconciled offered commit, or a stale format receipt. Claim 10 ties qualification to verifier-computed inputs, not a candidate's assertion that a run remains valid. Each fallback controls machine behavior rather than merely informing a person.

Claims 11 through 14 freeze, compare, and regenerate named byte artifacts while withholding staging authority. Claims 15 through 18 resolve and refuse unsafe paths, verify immutable backups, and withhold inherited approval. The operative verbs should remain in both the claims and the prevention register.

Step 2B concerns the ordered combination, not an assertion that hashes, UUIDs, quotas, version control, or immutable snapshots are novel. The principal risk is an aggregation of known data-management practices. Tie the claims to the causal sequence: normalized identity survives derived canary planting, evidence accrual does not mutate task identity, merged residency controls placement, and coherent epochs support stable qualification.

The practical application is data integrity and reproducibility of an executable evaluation pipeline. Avoid replacing these machine constraints with abstract trust assignment, project status, human roles, or the statement that the system uses AI. No eligibility outcome is promised.

## EPO technical effect

Under Article 52 and Guidelines G-II 3.3 and 3.3.1, the specific technical purpose of normalization and hashing is eliminating a self-referential artifact identifier while preserving verifiable slot constraints. The specific purpose of ordered placement is preventing duplicate authoritative filesystem residency under concurrent preparation.

The specific purpose of epoch manifests and closure hashing is coherent, reproducible input consumption in a distributed pipeline. Disk-derived render instants remove nondeterministic output differences, and staged comparison connects those bytes to the proposed repository state. Migration checks preserve recoverable byte state without treating old signatures as current validation.

These mechanisms concern data integrity and deterministic reproducibility of the computing system. The draft does not rely on training a new model, improving an evaluation score, or displaying a more useful business dashboard as its technical effect. Known primitives and prospective integration still require an inventive-step analysis.

## India s.3(k) technical effect

Claim 1: the technical problem is circular identity derivation and divergent distributed artifact state. The technical solution combines placeholder-normalized hashing, deterministic marker derivation, restricted storage placement, and manifest-bound epoch publication. The proposed measurable technical benefit is stable valid task identity during evidence accrual, absence of admitted duplicate homes, and repeatable projection bindings. Under the Ferid Allani and Microsoft v. Assistant Controller technical-contribution framing, this is a change to computer operation, with no novel hardware required; no measured benefit is asserted by the draft.

Claim 19: the technical problem is inconsistent ordering of parallel artifact preparation and memory publication. The technical solution fixes derivation and publication order and refuses conflicts before current-state designation. The proposed measurable technical benefit is deterministic detection of changed protected bytes and stale proposals without invalidating a run merely because an unrelated repository tip changes. The Ferid Allani and Microsoft v. Assistant Controller vocabulary directs attention to the technical problem, technical solution, and technical benefit, not an algorithm label, and no novel hardware is required.

Claim 20: the technical problem is reproducing integrity enforcement across processor installations that consume the same artifacts. The technical solution stores executable instructions implementing the same identity, placement, and publication constraints as claims 1 and 19. The proposed measurable technical benefit is identical valid bindings and reproducible refusal behavior over identical inputs. Ferid Allani and Microsoft v. Assistant Controller support assessing that technical contribution; a storage-medium form alone does not avoid exclusion, and no novel hardware is required.

## Obviousness posture

vs BIG-bench canary + Thinkst Canarytokens: combination yields planted leakage markers but not the acyclic normalized digest, pure-KDF token verification, write-once task binding, and split-authority evidence subtree. Novelty residue is the ordered relation, not detection by a canary string.

vs RFC 9562 + RFC 8785 + US6367012B1 + Authenticode: combination yields deterministic names, canonical bytes, and a workable exclusion for embedded certification but not necessarily placeholder-preserved slot structure with exact derived-token verification and separate evidence authority. Novelty residue requires those constraints together; identifying signatures as canaries without more is weak.

vs Nix RFC 0062 + Guix (arXiv 1305.4584) + CAS patents US8560503B1 and US8335889: combination yields reproducible content-derived storage but not necessarily a digest-derived canary replanted into the normalized task. Novelty residue is the identity derivation's interaction with marker validity and evidence exclusion, not content addressing itself.

vs WO2015178944A1 + WORM patents US7487178, US9659029, US8200721B2, and EP1604260A4: combination yields retention, immutable content, and path restrictions but not the complete normalized identity and separately keyed evidence protocol. Novelty residue must survive their direct teachings of write-once storage; do not claim that immutability alone distinguishes the application.

vs US9201693B2 + US12602259 + US12309078 and US12068973: combination yields hard limits, proposed quota targets, and parent ceilings that children cannot override but not necessarily the digest-gated lifetime lane classification and committed-byte placement relation. Novelty residue is that relation together with deterministic reconciliation. Non-overridability is expressly conceded as taught by the quota art.

vs US11979336 + Merkle-CRDTs (US12719813 withdrawn as not found, 2026-09-21): combination yields distributed usage limits and convergence ordering but not necessarily ungraduated-anchor priority followed by published-standing graduation. Novelty residue concerns the precise residency transition and limited standing input, not the illustrative ceiling value.

vs Gerrit non-fast-forward refusal + git ancestor-check hooks: combination yields ancestry-preserving pushes but not exact preservation of a queue file's accepted bytes. Novelty residue is per-stream byte-prefix refusal combined with closed payloads, seal validation, and comparison of the offered commit to the reconciled commit.

vs TUF consistent snapshots + Bazel Remote Execution API action cache and CAS: combination yields immutable versioned artifacts and input-derived action keys but not necessarily run-specific memory proposals folded into an epoch with projection bindings and run qualification over the disclosed closure. Novelty residue is the composed publication-and-qualification protocol, not dependency hashing.

vs Dolt/Noms + IPLD + Merkle-CRDTs: combination yields content-addressed immutable state and mergeable histories but not the prescribed current-base conflict stop and serialized publication of the projection set. Novelty residue is that publication boundary coupled to subject qualification. The existing cross-clone serialization gap must remain visible in implementation statements.

vs TUF expiry + Nix RFC 0062: combination yields freshness checks and exact reproducible artifacts but not necessarily native delivery-schema validation in an isolated interpreter joined to manifest-bound receipts and a separately aging currency lock. Novelty residue is the gate combination rather than a version pin.

vs US8200721B2 + Dolt/Noms: combination yields immutable statements and deterministic content but not necessarily a source-bound terminal tracker card with disk-derived print instant, whole-file regeneration, non-staging hooks, and staged-byte binding. Novelty residue is that operational combination; the register's dashboard coverage is indirect and needs further human-led searching.

vs Guix + RFC 8785: combination yields reproducible store conventions and canonical serialization but not the trusted direct-child invocation-root relation with distinct-remote roster checks. Novelty residue is narrowly proposed for that combination; these references do not constitute an exhaustive confinement search, and no universal runtime guard is asserted.

vs TUF consistent snapshots + US7487178: combination yields versioned integrity and immutable retention but not necessarily a closed structure-migration matrix that reconstructs a resumable plan and prohibits carrying approval across changed bytes. Novelty residue lies in the constrained authority boundary, not journals or atomic rename.

The source is Groups 1 and 2 of the supplied register, not a new network search. Assignees were agent-verified on 2026-09-21 on Google Patents and US12719813 was withdrawn as not found; patent family scope beyond the cited numbers remains unchecked. These are examination positions rather than novelty, validity, or freedom-to-operate opinions.

## Design-around foreclosures

1. Hashing literal canary bytes recreates circularity; normalizing slots without checking derived values creates a free mutable region. Claims 1 and 2 require both the ordering and the validity relation.

2. Calling a second task copy evidence does not satisfy the no-task-bytes limitation. Evidence can share the bundle's physical container while remaining separately keyed and governed.

3. Reading a declared lane without counting actual committed residency misses claim 1's re-derivation. Raising the ceiling through a lower-authority grant also avoids the claimed constraint rather than satisfying it.

4. Preserve classification versus placement. A lawful relocation does not rewrite the registered classification, and a fixed-root formulation cannot cover the same identifier's graduation without contradiction.

5. A valid new chain after deletion is insufficient: claim 4 compares accepted stream bytes, not merely internal hash consistency or commit ancestry.

6. Namespaces alone do not serialize scarce claims or memory publication. Claims 1 and 7 require a publication boundary; the current implementation's remote-admission gap is not hidden by a directory name.

7. A candidate-selected dependency list does not satisfy computed closure qualification. Claim 10 fixes included input classes and uses the governing gitlink rather than the moving tip.

8. A mutable card or wall-clock print instant defeats claims 11 and 12. Idempotent re-emission preserves the original closing instant and source digests.

9. A keep-local merge driver without regeneration and staged comparison leaves stale bytes. Claims 13 and 14 couple those operations while preventing autonomous staging.

10. A contained path relative to an attacker-selected root does not meet claim 15. The trusted startup root and direct-child relation matter independently of lexical path validation.

11. An upgrade that re-signs or edits approvals as part of migration defeats claim 18's authority exclusion. Revalidation is fresh ordinary work, not a schema-string substitution.

12. The claims permit a single legal operator using distinct logical write authorities. Co-locating processes on shared hardware does not remove the specified byte bindings or authority distinctions.

## ENFORCED and PROSPECTIVE map

| Mechanism | Claims | Evidence class | Evidence (tools/tests or contract line or DEFERRED row) |
| --- | --- | --- | --- |
| Normalized hash, namespace identifier, pure KDF, and pre-byte approval | 1, 2, 19, 20 | CONTRACT-ONLY; integrated verifier PROSPECTIVE | FORGE.md:14, 185, 219; ENGRAM.md:180; parent sections 8.9 and 8.15 |
| Canonical tree identity and top-level evidence exclusion | 1, 19, 20 | ENFORCED | tools/bundle_identity.py, first landed 2026-09-16; tests/test_bundle_identity.py |
| Immutable lane registration and current claimable subset | 1, 8, 19, 20 | ENFORCED | tools/lanes.py, first landed 2026-09-17; tests/test_lanes.py; pre-byte timing remains FORGE.md:420 |
| Queue field closure, backpressure, claims, and prefix checks | 3, 4 | ENFORCED | tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py; tests/test_parallel.py |
| Unbypassable remote push admission | 4 | DEFERRED | DEFERRED.md: "Push admission is the local hook, and the rerun on `main` is detection" |
| Delivery-format pin, lock, and receipt checks | 5 | ENFORCED | tools/harbor.py, first landed 2026-09-16; tests/test_harbor.py |
| Run marker and namespace checks | 6 | ENFORCED | tools/runs.py, first landed 2026-09-18; tests/test_runs.py |
| Human identity enrollment for run authority | 6 | DEFERRED | DEFERRED.md: "Run ownership is authenticated only by `run.json` bytes" |
| Epoch proposal bases, conflicts, epoch files, and view bindings | 1, 7, 19, 20 | ENFORCED for local checks | tools/epochs.py, first landed 2026-09-18; tests/test_epochs.py |
| Cross-clone serialized publication | 1, 7, 19, 20 | DEFERRED; complete embodiment PROSPECTIVE | DEFERRED.md: "Epoch publication races between two clones" |
| Anchor-first residency and graduation | 8, 9 | ENFORCED | tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py; tools/lanes.py, first landed 2026-09-17; CHANGELOG.md entry 2026-09-18 |
| Computed subject closure | 10 | ENFORCED | tools/subject.py, first landed 2026-09-18; tests/test_subject.py; tests/test_parallel.py |
| Frozen card writer and strict reader | 11 | ENFORCED | tools/tracker.py and tools/tracker_card.py, first landed 2026-09-20; tests/test_tracker.py |
| Terminal-only card timing across callers | 11 | CONTRACT-ONLY; integration PROSPECTIVE | docs/adr/0005-run-lifecycle-closure.md:21-27, 45-51 |
| Clock-free snapshot and whole-file dashboard | 12 | ENFORCED | tools/tracker_snapshot.py and tools/dashboard.py, first landed 2026-09-20; tests/test_tracker_snapshot.py; tests/test_dashboard.py |
| Staged report checks, non-staging hooks, merge attributes | 13, 14 | ENFORCED | tools/report_staging.py, first landed 2026-09-20; tests/test_hooks.py; tests/test_report_binding.py covers signed report binding, not the merge driver |
| Tracker non-reading by agents | 12 | DEFERRED | DEFERRED.md: "What stays unenforced is the projection-leak check" |
| Canonical path and symlink checks in covered CLIs | 15 | ENFORCED | tools/project_paths.py, first landed 2026-09-16; tests/test_project_paths.py; tests/test_cli_path_scope.py |
| Direct-child root doctrine for all agent filesystem actions | 15 | CONTRACT-ONLY; runtime remainder DEFERRED | ENGRAM.md:1; DEFERRED.md: "A run that roots itself one directory above the project that vendors `trinity/` and scaffolds a harness there" |
| Distinct-remote roster and boundary checks | 16 | ENFORCED | tools/layout.py, first landed 2026-09-18; tests/test_layout.py; docs/adr/0004-parent-submodule-layout.md |
| Closed migration matrix and authority exclusion | 17, 18 | ENFORCED | tools/migrate.py, first landed 2026-09-16; tests/test_migrate.py; docs/migrations.md |

Evidence labels identify predicates, not a statement that the entire claim is implemented. No named test is represented as executed in this drafting pass. All tools and tests named in the map are present on disk; addition-history dates identify source provenance only.

## §112 / drafting cautions

Application section 8.2 defines canary slots, write-once identity, home, lane classification, structural ceiling, accepted prefix, run proposal, epoch, subject closure, and frozen card before claim use. Retain those objective definitions and explicit antecedents. A pure KDF needs a fixed input and slot-context rule; a free-text marker-generation instruction is insufficient enablement for the claimed deterministic relation.

Claims 1, 19, and 20 require a pre-authoring lane gate, but the task digest arises only after provisional construction. Keep the gate-bound normalization and classification rules separate from the final digest binding to avoid an impossible temporal dependency. The final identifier may instantiate the approved slot's classification without pretending the final digest exists before task construction.

The claims use processors, memory, and specified operations rather than a bare "controller configured to" achieve a desired result. Functional expressions still warrant analysis under section 112(f), including the Williamson concern. The disclosed algorithms, comparison inputs, refusal conditions, and data structures should remain in the specification even if counsel changes claim form.

An immutable lane classification does not make a physical location immutable. A root-fixed alternative and a graduating-anchor embodiment cannot both govern the same identifier without qualification. The three-value historical vocabulary and current two-value admission subset require explicit support review rather than silent harmonization.

The epoch publisher records a parent number, not a parent manifest digest, and current local writes do not establish crash-atomic distributed commit. Do not claim a fully implemented consensus protocol, lock, transactional pointer swap, or complete projection generator from that source alone. The claim's integrated serialization has prospective support and requires priority review.

The common tree identity binds exact bytes rather than normalized canary values. The specification must not conflate that existing helper's digest with the contract's normalized task digest. Likewise, evidence excluded from task identity still needs its own integrity and authorization binding.

Each dependent names its parent expressly. Claim 10 depends on claim 7 to acquire checked epoch and projection context; claim 9 depends on claim 8 to acquire anchor seating; claims 12 through 14 form the reporting ladder; claims 17 and 18 acquire path containment and migration context in order.

Claim numbers are references, not implementation numerals. The structural ceiling, namespace, grammar, vocabulary size, path spellings, predicate identifiers, refusal codes, and reporting section count remain examples. Claims stay single sentences even where a prose linter prefers shorter sentences.

The parent filing remains prospective. The human decision must assess new matter, continuation support, any actual restriction and divisional consonance, unity, and alternative claim groupings. No safe harbor, priority entitlement, filing, deployment, or measured pass rate follows from this draft.
