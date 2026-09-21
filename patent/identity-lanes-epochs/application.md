# UNITED STATES NON-PROVISIONAL UTILITY PATENT APPLICATION

**Filed under 35 U.S.C. § 111(a)**

**Title:** Canary-Normalized Write-Once Task Identity, Structural Lane Routing, Sealed Queues, and Epoch-Published Multi-Runner Memory for Machine-Learning Evaluation Bundles

**Inventor:** Sarvex Jatasra

**Applicant / Assignee:** Ethara.AI

**Docket Reference:** Trinity/identity-lanes-epochs

---

## 1. TITLE OF THE INVENTION

Canary-Normalized Write-Once Task Identity, Structural Lane Routing, Sealed Queues, and Epoch-Published Multi-Runner Memory for Machine-Learning Evaluation Bundles

This is an application draft dated 2026-09-21. The statutory heading identifies the proposed application form, not a filing event. Implementation evidence below identifies source code and test definitions, not an executed test result or operational deployment.

## 2. CROSS-REFERENCE TO RELATED APPLICATIONS

The related parent disclosure is titled "Cryptographically Controlled Certification of Machine-Learning Evaluation Tasks Using Isolated Generation, Audit, and Evidence Domains." Its filing is prospective. This application is intended as a divisional or continuation of that disclosure, with the choice left to the human filing decision. No application number, filing date, priority entitlement, restriction requirement, or statutory safe harbor is asserted here.

Parent sections 8.9, 8.15, 8.16, 8.32, 8.40, 8.41, 8.43, and 8.44 and claims 6, 21, 32, and 36 supply related subject matter. The present draft distinguishes that disclosure from newer run namespaces, memory epochs, subject closures, and frozen tracker cards. Counsel must assess written-description support and priority for each limitation before choosing a continuation route; a family label does not establish support for later matter.

The neighboring release-authority and tamper-evident-governance disclosures concern release permission and authenticated operations. This application addresses artifact identity, placement, concurrent preparation, coherent memory publication, and deterministic derived reporting. It does not equate a valid local artifact with authorization to release that artifact.

## 3. STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

## 4. FIELD OF THE INVENTION

The disclosure concerns distributed computing pipelines that produce executable machine-learning evaluation bundles. It concerns content identity across evidence accrual, deterministic allocation of filesystem residency, mergeable run-local streams, snapshot publication, and qualification tied to computed input closures. It also concerns fail-closed validation of format revisions, contained path resolution, and migrations that preserve evidence without transferring approval to changed bytes.

## 5. BACKGROUND OF THE INVENTION

A first deficiency arises when an artifact hash includes a marker whose value derives from that hash. Direct evaluation creates a circular dependency. Omitting arbitrary marker regions instead creates unbound mutable bytes. Static benchmark canaries and generic signature-region exclusions do not by themselves define a complete derivation-and-verification relation for those regions.

A second deficiency arises when working and delivered copies both act as authoritative task bytes. Evidence may bind one copy while execution consumes another. Content addressing helps detect changes but does not alone prohibit duplicate authority, define excluded evidence, or prove that a marker occupying an excluded slot is the uniquely derived marker.

A third deficiency concerns scarce placement under concurrent writers. Two clones may each observe available capacity and allocate it. A mutable counter or a declared lane can then disagree with merged disk residency. Parent-compartment quotas already restrict child overrides; the problem here includes determining which immutable evaluation bundles occupy the limited root after merging independently prepared work.

A fourth deficiency concerns concurrent memory updates. Shared mutable files invite lost updates, while independent immutable histories still require a rule for publishing a coherent projection pair. A reader that combines a new ledger with an old projection receives no single reproducible memory state.

A fifth deficiency arises when qualification binds the repository tip rather than the inputs of the qualified operation. An unrelated commit invalidates useful qualification, while an incomplete input list may preserve qualification across a relevant change. The closure must come from a verifier's fixed enumeration, not a candidate-supplied list.

A sixth deficiency concerns reports and upgrades. Render-time clocks make otherwise identical reports differ, mutable close cards erase prior source bindings, and automatic migration may silently treat historical signatures as approval of transformed bytes. These are byte-integrity and reproducibility failures in the pipeline, not merely deficiencies in human record keeping.

## 6. SUMMARY OF THE INVENTION

The disclosed architecture normalizes designated canary slots before hashing, derives task identity and canary values from the resulting digest, plants the derived values, and binds the result. It maintains a single authoritative task home and a separately keyed evidence subtree outside the task-identity hash domain. Separate evidence integrity checks govern that subtree.

A digest-bound gate fixes a lane classification before task authoring. A deterministic placement function combines that immutable classification with merged residency, seal order, and published anchor standing. It refuses duplicate homes and enforces a structural residency ceiling that a requirements grant cannot raise. Classification remains immutable even when the specified reconciliation operation relocates the single home.

Independent runs prepare changes in disjoint namespaces. A publish operation checks proposals against the current memory epoch and materializes a successor snapshot, a manifest, and projections bound to the manifest digest. A qualification binds a computed subject closure, allowing unrelated commits without accepting changes to the qualified inputs.

Dependent mechanisms constrain queue fields, verify accepted stream prefixes, require currency-qualified format validation, freeze per-run close cards, derive report print instants from recorded disk state, and confine migration to a closed transformation matrix. The claimed combination includes contract-supported and prospective aspects as expressly identified below; the repository is not presented as a complete deployed instance.

## 7. BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 depicts a normalization and binding pipeline: provisional task bytes, designated placeholder slots, a canonical digest, parallel identifier and canary derivations, token planting, and a write-once identity binding beside a separately governed evidence subtree.

FIG. 2 depicts lane registration and residency reconciliation: a digest-bound classification, run-local seals, merged resident directories, anchor standing, deterministic seating, a capped sample root, and an overflow root holding mutually disjoint identifiers.

FIG. 3 depicts concurrent preparation followed by memory publication: run-specific proposal directories, current-base validation, a conflict stop, an immutable successor epoch, its manifest, manifest-bound projections, and a current-epoch pointer.

FIG. 4 depicts qualification closure computation: run inputs, sealed or judged task identities, human input roots, a consumed projection, and a governing-specification gitlink entering an ordered manifest while derived outputs and unrelated commits do not enter it.

FIG. 5 depicts report derivation: frozen run cards and reports enter a clock-free snapshot reader, which supplies a whole-file renderer, staged-byte comparison, and a generated-report merge driver without permitting a hook to stage a file.

FIG. 6 depicts structure migration: trusted-root path resolution, a closed version matrix, an exclusive local lock, immutable backups, atomic replacement, resumable journal checks, and a revalidation hold that prevents old approval from authorizing new bytes.

## 8. DETAILED DESCRIPTION OF THE INVENTION

### 8.1 Overview

The system uses processors, non-transitory memories, ordinary file storage, and version-control repositories. An operator may distribute runs across clones without distributing ownership of a mutable singleton. Independent preparation is parallel; scarce placement and publication use explicit reconciliation operations.

The identity plane names task content. The evidence plane records observations about that content. The placement plane chooses its single current home. The memory plane publishes consistent derived knowledge, and the reporting plane renders human-readable state without becoming a source of qualification authority.

Evidence labels have narrow scope. ENFORCED identifies an implementation predicate and a corresponding test file available for inspection. CONTRACT-ONLY identifies a specification obligation not established by the cited implementation. DEFERRED identifies an open register row. PROSPECTIVE identifies an embodiment or integration not asserted as implemented.

The source files and named tests exist on disk at drafting. First-landed dates come from addition history, not from an inference about when a feature becomes complete. Nothing in a first-landed date supplies a patent priority date.

### 8.2 Definitions

A task bundle is a tree of executable environment, instruction, and verifier bytes together with the private extensions that define an evaluation task. Relative member paths and execution-relevant file modes can participate in its identity even though its enclosing lane-root location does not.

A canary slot is a location designated by a versioned normalization grammar. Normalization substitutes a fixed placeholder for its token value while retaining the slot's count, position, ordering, and surrounding bytes. A region that the grammar does not designate remains identity-bearing.

A write-once identifier is a deterministic name whose accepted binding cannot change to another normalized task representation. Changed task content requires another identifier. A planted token is valid only if it satisfies its derivation relation; normalization is not permission to alter token values arbitrarily.

A single authoritative home is the sole resident location from which the task bytes are canonical. A relocation changes the location without creating a concurrently authoritative copy. An evidence subtree has a separate logical key and integrity binding; its physical containment beneath the home does not make evidence bytes task bytes.

A task lane is an immutable admission classification from a closed vocabulary, not a parallel worker or an audit pass. A placement root is the current location selected by the classification and the prescribed reconciliation function. A structural residency ceiling is a bound built into that function that a requirements grant cannot relax.

A seal is a digest-bound queue record identifying a frozen bundle, its producer run, and its seal instant. An accepted stream prefix is the exact byte prefix of that stream at an identified accepted revision. A valid current hash chain alone does not prove preservation of that prefix.

A run namespace is the owned subtree for one run's mutable private state. A memory proposal is a run-attributed proposed file body with its digest and base epoch. An epoch is an immutable published snapshot with a manifest naming constituent file digests.

A two-phase memory publication comprises parallel proposal preparation followed by serialized validation and publication. It does not mean a conventional distributed two-phase-commit protocol. Global serialization is an admission requirement distinct from local detection of stale proposals.

A subject closure is a verifier-enumerated manifest of the inputs and task identities relevant to a run's qualification. A frozen tracker card is a write-once derived terminal statement bound to its run's source digests. A disk-derived print instant is computed from recorded input instants, not the renderer's wall clock.

### 8.3 Canary-normalized identity and split evidence authority

The normalization procedure enumerates runtime-relevant members in canonical order, replaces each designated canary value with its fixed placeholder, and hashes the normalized representation. A normalization version distinguishes incompatible domains. Slot deletion, slot insertion, slot relocation, and surrounding-byte edits change the represented domain rather than disappear under normalization. CONTRACT-ONLY (FORGE.md:185; parent application section 8.9).

In one implementation, a namespace pinned in approved scope supplies the namespace argument to UUID version 5 and the normalized digest supplies its name input. The namespace remains read-only for task production. The complete digest remains a binding value; the shorter identifier does not replace digest comparison. CONTRACT-ONLY (FORGE.md:14, 185; ENGRAM.md:13).

The ordered operations are hash, derive, plant, bind. A pure key-derivation function consumes the normalized digest and fixed slot context to derive the canary set. The producer plants only those derived values and then records the identity binding. Reverification normalizes the frozen task and re-derives the expected tokens, refusing an inconsistent token even when normalization yields the expected digest. CONTRACT-ONLY (FORGE.md:185, 219; ENGRAM.md:180).

In one implementation, the author contract file `.seed/contract.yaml` binds the canary-normalized content hash and normalization domain version. The approval gate binds the normalization rules before construction; the final content binding follows construction. The content binding must not become an additional self-referential input to its own digest. CONTRACT-ONLY (FORGE.md:185; parent application sections 8.9 and 8.15).

Changed normalized bytes require a new identifier and a successor relation rather than reuse of the earlier identifier. A clean sealed bundle remains frozen; a retained verdict permits successor authoring, not an in-place edit that silently inherits the predecessor's identity. CONTRACT-ONLY (FORGE.md:185, 393).

In one implementation, the current physical home is `samples/<uuid>/` or `delivery/<uuid>/`, with separately keyed rollout evidence in its own `trajectories/` subtree. The evidence key joins task identity to execution evidence and holds no second set of task bytes. The retired sibling mirror root is not the current implementation. CONTRACT-ONLY (FORGE.md:186; docs/adr/0004-parent-submodule-layout.md:59-71).

The shared tree hasher binds relative file paths, regular-file bytes, and executable bits, excludes only the top-level evidence subtree, and refuses symlinks and nonregular objects. A nested directory with the same evidence name remains identity-bearing. The release snapshot digest includes exported evidence even when task identity excludes it. ENFORCED (tools/bundle_identity.py, first landed 2026-09-16; tests/test_bundle_identity.py).

The shared hasher does not itself replace canary slots, derive a namespace identifier, or implement a canary KDF. Those steps remain contract-supported here. Split authority requires evidence authentication separate from task identity; a digest exclusion alone supplies no access-control boundary. A combined normalizer, derivation verifier, and authority-separated evidence writer is PROSPECTIVE as an integrated implementation.

### 8.4 Task lanes and structural residency

The earlier parent embodiment defines a closed three-value vocabulary and binds the selected value at a digest-bound gate before bundle bytes exist. In one implementation, the vocabulary is `starter`, `sample`, and `delivery`. Lifetime immutability prevents reclassifying the identifier merely to obtain a different quota treatment. CONTRACT-ONLY (parent application section 8.32 and claim 36).

The current contract narrows author-side admission to the first two values and reserves overflow decisions for reconciliation. In one implementation, `route` registers only `starter` or `sample`; it rejects a new `delivery` claim, while readers retain compatibility with a historical delivery record. Thus the historical three-value embodiment is disclosed without falsely describing all three values as current author-selectable inputs. CONTRACT-ONLY (FORGE.md:420).

Registration creates a per-identifier record exclusively and refuses a different value for an existing identifier. It requires a staged bundle, so the registration tool alone does not prove the earlier approval or pre-byte timing. Those timing requirements belong to the contract-supported gate. ENFORCED (tools/lanes.py, first landed 2026-09-17; tests/test_lanes.py).

In one implementation, the sample ceiling is thirty resident bundles, starters included, and no requirements grant relaxes it. Registration does not count capacity on a clone. The merge-time placement function counts merged residency and routes overflow, avoiding independent clone-local capacity promises. ENFORCED (tools/lanes.py, first landed 2026-09-17; tests/test_lanes.py); ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py).

The delivery-conformance embodiment re-derives residency from committed bytes and compares it with the placement the immutable classification permits. It refuses duplicate residency across staging and lane roots rather than trusting the registry's assertion. Committed-tree qualification requires the surrounding gate and human commit sequence; a scan of a dirty worktree is not independently proof of commitment. CONTRACT-ONLY (ENGRAM.md:221, 514; FORGE.md:420).

The pipeline verifies sealed digests and detects multiple homes. Placement renames a clean staged bundle instead of copying it. A declared immutable lane and a current physical root are separate facts: reconciliation can move the home without editing the lane record. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py, tests/test_parallel.py).

A stricter fixed-root-for-life embodiment can retain the historical parent rule, but cannot simultaneously promise anchor graduation between roots for that identifier. The claims below use immutable classification plus deterministic current placement, avoiding that contradiction. Combining the pre-byte digest gate with the complete current routing implementation remains PROSPECTIVE to the extent not evaluated by the cited tools.

### 8.5 Sealed per-run queues and accepted-prefix refusal

In one implementation, each producer appends to `.podium/queue/<run_id>.jsonl`. The application payload contains only identifier, bundle digest, seal instant, and producer run identity. Sequence and predecessor/current hashes are integrity-envelope fields rather than additional application messages. An unknown field fails the closed parser, so private findings cannot enter as an extra payload field. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py).

In one implementation, the field-closure refusal is `PIPELINE_CHAIN_BROKEN`. Other refusals include `PIPELINE_SEALED_MUTATED`, `PIPELINE_UNSEALED_AUDIT`, `PIPELINE_BACKPRESSURE`, `PIPELINE_STALE_CLAIM`, and `PIPELINE_CONFIG_INVALID`. The verifier checks current bundle bytes against the seal and refuses resealing a frozen identifier instead of using a later seal to erase mutation. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py).

Claims use per-run files beneath a per-bundle claim directory. Exclusive creation protects a local claim-file write, claim lifetime bounds stale ownership, and a verdict must name its owning consumer and sealed digest. A merged inventory counts pending work across streams for backpressure. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py, tests/test_parallel.py).

In one implementation, `verify --accepted` reads each stream at the accepted revision and requires those exact bytes to remain a prefix of its current stream. Deletion, truncation, or a fully rehashed replacement produces `PIPELINE_STREAM_REWRITTEN`. An unresolvable accepted reference also refuses because historical extension cannot be established. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py, tests/test_parallel.py).

The pre-push hook combines reconciliation checking and accepted-prefix checking with a comparison of the offered commit to the reconciled local HEAD. A push of another non-deletion commit does not pass merely because HEAD is clean. In one implementation, the installed hook implements that comparison for the target branch. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_hooks.py); supporting source: templates/pre-push and CHANGELOG.md:15.

These checks do not create exclusive server-side push admission. A bypassable local hook and a later continuous-integration finding cannot prevent all invalid commits from reaching a remote. Claim timestamps also do not authenticate ownership against a hostile backdating writer. DEFERRED (DEFERRED.md: "Push admission is the local hook, and the rerun on `main` is detection"; "Verdict arbitration by claim instant").

### 8.6 Delivery-format currency pin

The resolver records the current stable delivery-format release from its package index, with the release date, resolution instant, and source. In one implementation, the lock is `harbor.lock`, the source is the Harbor package index, and validation invokes the pinned package's manifest validator in an isolated interpreter rather than importing it into the governance tool. ENFORCED (tools/harbor.py, first landed 2026-09-16; tests/test_harbor.py).

The receipt binds the manifest bytes and validation release. The currency check joins the author-side exact pin to the lock and the receipt; the schema check compares the manifest to its declared schema and receipt. This is a concrete gate on parser compatibility and current validation, not a statement that any exact dependency pin remains acceptable indefinitely. ENFORCED (tools/harbor.py, first landed 2026-09-16; tests/test_harbor.py).

In one implementation, refusals include `HARBOR_PIN_MISSING`, `HARBOR_PIN_MALFORMED`, `HARBOR_PIN_STALE`, `HARBOR_PIN_UNTESTED`, and missing, malformed, or stale lock findings. Schema drift and receipt disagreement also prevent a clean conformance result. A manifest edit requires another receipt under the applicable pin. ENFORCED (tools/harbor.py, first landed 2026-09-16; tests/test_harbor.py).

Currency is bounded rather than a permanent claim of equality with a live service. In one implementation, the lock ages after fourteen days, while pin staleness uses major-version lag, more than one minor-version lag, or an aged release comparison. A one-minor lag within the cadence can pass. No network resolution or package validation is performed by this drafting pass. ENFORCED (tools/harbor.py, first landed 2026-09-16; tests/test_harbor.py).

### 8.7 Run namespaces and mergeable preparation

In one implementation, private mutable invocation state resolves under `<harness>/runs/<run_id>/`. A newly minted identifier combines instrument, principal token, UTC stamp, and entropy within a closed grammar. Resumption reuses that identity rather than creating another chain for the same unfinished work. ENFORCED (tools/runs.py, first landed 2026-09-18; tests/test_runs.py).

The namespace marker binds the declared instrument and principal. Reopening an existing namespace with a different declaration refuses; the marker is not a cryptographic enrollment proof. Input parsing prevents traversal-shaped run identifiers and instrument-prefix mismatches. ENFORCED (tools/runs.py, first landed 2026-09-18; tests/test_runs.py).

The ownership rule applies to private mutable state, not every output location in the protocol. Bundle homes, per-run queue and claim streams, memory proposals, epoch publication, and generated reports have their separately specified write paths. Memory's contract expressly exempts proposals, epochs, views, and the current pointer from the private run directory. CONTRACT-ONLY (ENGRAM.md:14).

Distinct runs append distinct streams, so honest clones merge those files as a union rather than fork a shared chain. The merged verifier still checks duplicate identifiers, conflicting digests, and shared capacity. Unique namespaces remove a routine write collision; they do not make every conflicting semantic update commutative. ENFORCED (tools/runs.py, first landed 2026-09-18; tests/test_runs.py); ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_parallel.py).

Hostile ownership and confidentiality require more than path separation. A marker can carry a claimed principal, and a full clone can expose another instrument's files. DEFERRED (DEFERRED.md: "Run ownership is authenticated only by `run.json` bytes"; "A full clone does not enforce the information barrier between humans").

### 8.8 Memory proposals, epochs, and manifest-bound views

In one implementation, a run writes proposed file bodies under `.memory/proposals/<run_id>/`. Each proposal identifies its base epoch, file name, source digest, and run. It does not edit the currently authoritative memory file. Publication inventories proposals across runs rather than accepting only the publishing run's proposal set. ENFORCED (tools/epochs.py, first landed 2026-09-18; tests/test_epochs.py).

The epoch publisher compares every proposal base with the current epoch before writing a successor. Different runs proposing the same file conflict, even if a silent overwrite would be convenient. A stale base, unreadable source, or source-digest mismatch stops publication with the affected proposal named. In one implementation, the conflict and stale refusals are `proposal-conflict` and `proposal-stale`. ENFORCED (tools/epochs.py, first landed 2026-09-18; tests/test_epochs.py).

For a first publication, the tool snapshots the recognized authoritative root files. For a successor, it takes existing epoch files and replaces the names for which acceptable proposals supply new bytes. It refuses an already existing successor directory. This is file-level folding, not an assertion that the epoch publisher semantically merges arbitrary ledger rows. ENFORCED (tools/epochs.py, first landed 2026-09-18; tests/test_epochs.py).

In one implementation, `.memory/epochs/<n>/manifest.json` records the epoch, parent epoch number, publishing run, publication instant, file digests, and applied proposal identities. `.memory/current.json` names the current epoch and manifest digest. Existing published files remain the comparison source for later checks. ENFORCED (tools/epochs.py, first landed 2026-09-18; tests/test_epochs.py).

In one implementation, `.memory/views/<n>/` carries both projections and `anchor_standing.yaml`, with a manifest-digest binding beside them. Root copies serve compatibility readers only. The checker compares epoch bytes with manifest digests, projection bytes with epoch bytes, and root copies with the current epoch. It emits `EPOCH_TAMPERED` or `EPOCH_DRIFT` rather than treating a divergent root copy as another authority. ENFORCED (tools/epochs.py, first landed 2026-09-18; tests/test_epochs.py).

The contract requires publication of both projections and anchor standing together, and workers pin the manifest digest of the epoch they consume. The implementation copies supplied projection files when present; it does not prove that a semantic projector recomputes every projection from the entire ledger. CONTRACT-ONLY (ENGRAM.md:43, 177).

The two-phase design calls for a serialized publication boundary. Local code checks stale bases and existing directories, but contains no cross-clone admission service or crash-atomic transaction spanning all epoch, view, compatibility, and pointer writes. Two clones can each construct the same successor number. DEFERRED (DEFERRED.md: "Epoch publication races between two clones").

A complete embodiment would admit a successor against the accepted current epoch under exclusive publication authority, verify the complete manifest and view set, and expose the current pointer only after those checks. Interrupted preparation would remain unpublished; a competing successor would require renewed base validation. That integrated admission and publication protocol is PROSPECTIVE, not a claim about the present remote.

### 8.9 Merge-time reconciliation and anchor graduation

Reconciliation inventories resident bundles and their seal records, seats ungraduated anchors first, and orders ordinary sealed residents by seal order with deterministic tie handling. In one implementation, the sample root holds exactly thirty when sufficient eligible residents exist, and otherwise holds fewer; the tool never manufactures bundles to fill a quota. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py, tests/test_parallel.py).

In one implementation, published anchor standing maps an identifier to `CANDIDATE`, `ANCHORED`, or `SUPERSEDED`. The latter states permit graduation into the delivery root after the duration row folds into memory. Reconciliation reads the reduced standing file, not the underlying duration or hardness ledger. CONTRACT-ONLY (FORGE.md:420; ENGRAM.md:177); implementation behavior: ENFORCED (tools/lanes.py, first landed 2026-09-17; tests/test_pipeline.py).

The move frees a sample seat for the next ordinary resident. It preserves task identity and carries bundle-local evidence with the task. Malformed standing produces reconciliation drift and no graduation based on a guessed state. A legacy resident without a seal remains fixed and counts first; an existing historical delivery classification remains in delivery. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py).

The mover checks destination occupancy and uses rename rather than a copy-and-delete workflow. It reports a move that cannot complete, including filesystem failure. A delivery-capacity finding remains a refusal, not permission to silently discard overflow. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py).

Reconciliation renders lane README inventories and root reports from run reports. In one implementation, `--check` reports required moves or regenerated bytes without performing them, and the pre-push hook invokes that check. The separate report-only command regenerates reporting without relocating bundles. ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_pipeline.py, tests/test_hooks.py).

The anchor-graduation source is the CHANGELOG.md entry dated 2026-09-18. Its publication-state dependency does not prove that every anchor designation or signed duration is independently validated by the mover. DEFERRED (DEFERRED.md: "Starter anchor cardinality and identity").

### 8.10 Subject-closure qualification

The verifier computes the qualification subject from disk under a fixed enumeration. In one implementation, the closure includes input bytes within the run namespace, identifiers and full sealed digests of bundles that run seals or judges, the human roots `requirements/` and `touchstones/`, the instrument's consumed projection, and the governing checkout's gitlink. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py).

Each regular-file entry records a kind, logical path, mode, size, and digest. The manifest sorts entries by kind and path and hashes the serialization with a schema discriminator. The candidate cannot choose which unrelated file to substitute for a required input. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py).

Derived outputs have a narrow exclusion set to avoid self-binding. In one implementation, run-root disposition, report, progress, TODO, tracker card, and gate receipts do not enter the subject. Feedback and phase receipts remain inputs; nesting an input under a different name does not make it a root-output exclusion. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py, tests/test_tracker.py).

An unrelated run's commit need not alter the closure. A changed included contract, human input, projection, governed bundle identity, or gitlink does alter it. The bundle entry comes from the sealed record; pipeline verification must separately check that live task bytes still match that record. Subject hashing alone is not a second complete sealed-byte verifier. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py); ENFORCED (tools/pipeline.py, first landed 2026-09-16; tests/test_parallel.py).

The integrated embodiment checks epoch integrity before consuming its projection and qualifies against that projection's computed closure. The current subject implementation names the consumed projection bytes, not an explicit epoch-manifest field. Adding the manifest binding as a direct closure member is PROSPECTIVE and must not be represented as an existing field.

The lifecycle decision requires subject-bearing feedback and phase receipts to stabilize before report-moment qualification. A later write requires fresh qualification rather than broader exclusions. CONTRACT-ONLY (docs/adr/0005-run-lifecycle-closure.md:29-43); this decision does not itself prove that every caller implements the ordering.

### 8.11 Frozen tracker cards and deterministic generated reports

No run writes a tracker byte in the disclosed reporting protocol. A run contributes its own frozen card and report; the renderer reads the combined set. In one implementation, the card schema is `trinity.tracker-card/v1`, and the writer derives state, phase, counts, identity, and source digests from that run's `run.json`, `report.md`, and `progress.yaml`. ENFORCED (tools/tracker.py, first landed 2026-09-20; tests/test_tracker.py).

The closing instant is a separately recorded write-once event field. It is not a count or disposition supplied by the caller, and it is not regenerated at report-render time. Re-emission over matching sources and derived fields preserves the original card and closing instant byte-for-byte. This qualifies the shorthand that every card field derives from the sources: the initial close instant is recorded once. ENFORCED (tools/tracker.py, first landed 2026-09-20; tests/test_tracker.py).

In one implementation, changed sources produce `TRACKER_CARD_CONFLICT`, missing sources produce `TRACKER_CARD_INPUT_MISSING`, and an instrument or run mismatch produces `TRACKER_CARD_IDENTITY_MISMATCH`. The strict reader reports `TRACKER_CARD_MALFORMED` for malformed or unbound cards; the dashboard shows unknown closure rather than silently repairing the card. ENFORCED (tools/tracker_card.py, first landed 2026-09-20; tests/test_tracker.py); ENFORCED (tools/dashboard.py, first landed 2026-09-20; tests/test_dashboard.py).

The lifecycle ADR distinguishes pause from terminal closure. A human gate pauses the same run without freezing its sources; terminal closure freezes the final card after report and progress stabilize. The earlier every-invocation wording conflicts with legitimate continuation. The draft adopts terminal closure as the embodiment and identifies coordinated caller integration as pending, rather than inventing permission to rewrite a card or rename a paused run. CONTRACT-ONLY (ENGRAM.md:110; docs/adr/0005-run-lifecycle-closure.md:21-27, 45-51).

In one implementation, the whole founder tracker has sixteen sections covering headline, organizational lanes, dispositions, decisions, changes, cycles, bundle flow, occupancy, aging, blockers, sign-offs, instrument summaries, history, and a legend. The snapshot derives its as-of instant from the newest recorded disk instant. It does not read the wall clock for rendering, so repeated renders of identical inputs yield identical bytes. ENFORCED (tools/tracker_snapshot.py, first landed 2026-09-20; tests/test_tracker_snapshot.py, tests/test_dashboard.py); ENFORCED (tools/dashboard.py, first landed 2026-09-20; tests/test_dashboard.py).

In one implementation, six hooks cover pre-commit, pre-merge-commit, post-checkout, post-merge, post-rewrite, and pre-push. Commit hooks compare expected report bytes with staged bytes, post-operation hooks render and report, and pre-push refuses failed qualification. Hooks may write generated working-tree bytes and name paths for human staging, but never stage, commit, amend, push, stash, or check out. ENFORCED (tools/report_staging.py, first landed 2026-09-20; tests/test_hooks.py).

In one implementation, `.gitattributes` assigns the root reports to the `trinity-generated` merge driver. The driver retains local rendered bytes; the subsequent deterministic render rebuilds reports from the merged sources. Exact staged comparison prevents an old retained rendering from masquerading as the merged report. ENFORCED (tools/report_staging.py, first landed 2026-09-20; tests/test_hooks.py); supporting source: the installed-hook and merge-attribute templates.

Signed report-to-byte binding and generated-report derivation are distinct checks. The former detects a changed signed report; the latter detects a report that no longer matches its disk inputs. The cited report-binding tests do not prove the canary normalizer or the epoch publisher. Supporting test evidence: tests/test_report_binding.py.

A deterministic human dashboard does not prove that an agent never reads another run's card. That prohibition remains part of the information-flow contract. DEFERRED (DEFERRED.md: "What stays unenforced is the projection-leak check: no checker proves that a run never reads `TRACKING.md` or a peer's tracker card").

### 8.12 Absolute containment and canonical authored paths

The parent root is exactly the directory whose direct child is the vendored governing-specification checkout. A trusted orchestrator fixes the invocation root at startup; candidate bytes and configuration contents never select that root. This avoids treating an attacker-selected ancestor as the security boundary. CONTRACT-ONLY (ENGRAM.md:1).

In one implementation, every authored, persisted, printed, and command-line path uses canonical `./` form. Absolute resolution is internal-only. The path resolver rejects traversal, redundant segments, backslashes, absolute input, and symbolic-link traversal before operational work; display functions avoid leaking the host root. ENFORCED (tools/project_paths.py, first landed 2026-09-16; tests/test_project_paths.py, tests/test_cli_path_scope.py).

In one implementation, the required submodule roster is `trinity/`, `.memory/`, `samples/`, `delivery/`, and `harness/`, each with a distinct remote. The parent records gitlinks rather than embedded task bytes. The registration policy specifies a tracked branch and merge update mode; staging may be a directory or a separately registered optional root. ENFORCED (tools/layout.py, first landed 2026-09-18; tests/test_layout.py).

In one implementation, crossed boundaries produce `PARENT_LAYOUT_SYMLINK`, `PARENT_LAYOUT_SHARED_REMOTE`, `PARENT_LAYOUT_UNKNOWN_SUBMODULE`, `PARENT_LAYOUT_PARENT_TRACKS_BUNDLE`, or `PARENT_LAYOUT_BOUNDARY_LEAK`. Incomplete registration and a nonempty retired mirror root hold, including `PARENT_LAYOUT_RETIRED_ROOT`. Bounded scans report exhaustion rather than asserting an unseen remainder is clean. ENFORCED (tools/layout.py, first landed 2026-09-18; tests/test_layout.py).

The inspected CLI resolver confines paths relative to its supplied root, and the layout checks inspect the audited tree. Neither proves that an arbitrary agent starts at the true parent or never scaffolds above it. A universal runtime guard remains open. DEFERRED (DEFERRED.md: "A run that roots itself one directory above the project that vendors `trinity/` and scaffolds a harness there").

A complete root-enforcement embodiment would verify the direct-child relation at trusted launch and mediate every filesystem operation of the agent against that root. Such mediation is PROSPECTIVE; the existing path and layout checks are narrower and must not be described as a process sandbox.

### 8.13 Versioned structure migration without inherited authority

The migrator recognizes a closed source-to-target matrix, not arbitrary schema inference. In one implementation, the supported rows include project-manifest bootstrap, canonical path-map conversion, recognized delivery-manifest transformations, and a queue-digest conversion only when the historical or current pre-migration digest proves the existing bytes. ENFORCED (tools/migrate.py, first landed 2026-09-16; tests/test_migrate.py); matrix: docs/migrations.md:9-26.

Application takes an exclusive local lock and writes exact content-addressed backups before replacing files. In one implementation, `.trinity/migrations/` holds the resumable journal and immutable backups. Exclusive backup creation prevents clobbering; an existing backup must match its digest and safe mode. ENFORCED (tools/migrate.py, first landed 2026-09-16; tests/test_migrate.py).

Journal and target replacement use synced temporary files, atomic rename, and directory synchronization. A retry reconstructs the original virtual snapshot from verified backups and untouched inputs, re-derives the supported plan, and checks every bound step before resuming. Matching before-state remains pending; matching after-state permits completion of an interrupted journal step. ENFORCED (tools/migrate.py, first landed 2026-09-16; tests/test_migrate.py).

Unknown versions, unsafe paths, symlinks, changed backups or targets, unproved queue seals, and required revalidation produce actionable holds. Rollback preserves original bytes and modes; an unknown self-consistent journal cannot redirect a known step to an authority path. ENFORCED (tools/migrate.py, first landed 2026-09-16; tests/test_migrate.py).

Migration never creates a key, edits approval material, changes role membership or thresholds, or reserializes a signed envelope. It can retain original signed bytes as history, but changed task or manifest bytes require ordinary current validation, audit, and signing. An unsigned progress journal grants no authority. ENFORCED (tools/migrate.py, first landed 2026-09-16; tests/test_migrate.py).

A permitted legacy queue conversion may recompute a historical chain after proving its input seal. That compatibility operation does not waive accepted-prefix refusal for an already accepted stream, and it does not waive write-once task identity. The draft does not claim that every migration can pass both regimes automatically; incompatible accepted history requires a separate authorized reconciliation or successor process. CONTRACT-ONLY (docs/migrations.md:22, 27, 37); integration beyond the supported matrix is PROSPECTIVE.

### 8.14 Named prior art and novelty residue: RFC 9562, TUF, and related art

For identity, BIG-bench's canary GUID and Thinkst Canarytokens teach markers, RFC 9562 supplies name-based identifiers, and US6367012B1 and Authenticode teach hash exclusions around embedded certification material. RFC 8785 supplies canonical serialization. The novelty residue asserted for examination is the acyclic hash-derive-plant-bind relation with preserved slot structure, exact token reverification, and a separately governed evidence subtree, not any individual hash, marker, or identifier primitive.

For write-once homes within the identity mechanism, Nix RFC 0062, Guix (arXiv 1305.4584), US8560503B1, US8335889, and WO2015178944A1 teach content-addressed storage approaches; US7487178, US9659029, US8200721B2, and EP1604260A4 address WORM constraints. The novelty residue depends on integrating these familiar constraints with canary-normalized identity and evidence exclusion without a second authoritative task copy. Patent status, family scope, and any unconfirmed assignee require human checking.

For lanes, US9201693B2 supplies hard-maximum quotas, US12602259 separates quota targets and hard limits, US12309078 and US12068973 teach parent-compartment ceilings a child cannot override, and US11979336 (Google) addresses distributed quotas; the earlier cited US12719813 was not found on 2026-09-21 and is withdrawn. The novelty residue cannot be a non-overridable ceiling alone; it is the digest-gated immutable lane classification, byte-rederived residency, and specified placement function applied together. Changing the workload label to an evaluation task would not itself distinguish the quota art.

For sealed queues, Gerrit non-fast-forward rejection and git ancestor-check hooks already restrict history replacement. The novelty residue is exact accepted byte-prefix preservation of each closed-field run stream, joined to sealed task verification and reconciled-commit checking. A fast-forward commit can replace file contents, so commit ancestry is not the same predicate as stream extension.

For the format pin, TUF expiry and consistent snapshots and Nix RFC 0062 supply strong comparators for reproducible, version-bound artifacts. The novelty residue is the combination of stable-release currency checks, bounded lock age, isolated native schema validation, and digest-bound receipts as placement prerequisites. Neither a lock file nor expiry alone is asserted as new.

For run namespaces, Dolt and Noms and Merkle-CRDTs already support immutable content and replicated state. The novelty residue is run-local chain preparation composed with a closed seal payload and later scarce-placement reconciliation. The disclosure concedes that branch-scoped writers and union of independent files are established techniques.

For epochs, TUF consistent snapshots, IPLD, Dolt/Noms, and Merkle-CRDTs teach authenticated immutable structures and concurrent histories. The novelty residue is current-base run proposals followed by serialized epoch publication with manifest-bound projections and qualification keyed to the computed subject closure. The implementation gap in cross-clone serialization limits any assertion about present enforcement.

For merge-time reconciliation, Merkle-CRDTs provide ordering-based convergence and US11979336 provides distributed quota comparisons. The novelty residue is seating ungraduated anchors before ordinary seal order, then graduating only from published folded-duration standing without exposing duration memory to the mover. The fixed count is illustrative, not the distinction.

For subject qualification, Bazel Remote Execution API action-cache and CAS inputs are a close comparator for content-derived input closure. The novelty residue is computing the qualification closure from run ownership, sealed and judged bundles, human roots, consumed memory projection, and governing gitlink while integrating epoch integrity. The draft does not claim invention of dependency hashing.

For generated reports, WORM approaches including US8200721B2 and deterministic immutable structures in Dolt/Noms supply familiar components. The novelty residue is a write-once run card bound to its source digests, a disk-derived print instant, and whole-file regeneration with staged-byte checks and non-staging hooks. This register supplies indirect rather than exhaustive dashboard prior art, so further searching remains necessary before filing.

For path containment, Nix RFC 0062 and Guix supply deterministic path and store comparisons, while RFC 8785 illustrates canonical representation without itself specifying filesystem confinement. The novelty residue asserted here is the trusted direct-child root relation composed with canonical authored paths and distinct-remote roster checks. The register does not establish an exhaustive confinement search, and the universal runtime guard is deferred.

For migration, TUF consistent snapshots and WORM patent US7487178 supply comparisons for preserved versions and irreversible storage states. The novelty residue is a closed compatibility matrix with verified before/after bytes, immutable backups, resumable recovery, and an express prohibition on carrying approval to changed bytes. Journaling, atomic rename, and migration version numbers individually remain conventional.

These passages rely on Groups 1 and 2 of the supplied prior-art register. No source is newly retrieved in this drafting pass. Register summaries are search leads, not adjudicated claim constructions; assignees were agent-verified on 2026-09-21 against Google Patents, family scope beyond the cited numbers remains unchecked, and the human filing gate stands. No novelty or validity opinion is asserted.

### 8.15 Prevention register and practical application

| Claims | Operative prevention | Artifact or operation withheld | Technical anchor |
| --- | --- | --- | --- |
| 1, 2, 19, 20 | Normalize, derive, compare, refuse reassignment | Invalid identity binding | Removes digest self-dependency without accepting arbitrary excluded token values |
| 1, 8, 9, 19, 20 | Re-derive, seat, refuse duplicate residency | Second authoritative home or excess placement | Deterministic filesystem allocation from merged bytes |
| 1, 7, 19, 20 | Compare proposal bases, refuse conflict, bind views | Incoherent successor memory | Reproducible snapshot consumption rather than mixed mutable versions |
| 3, 4 | Reject extra fields and rewritten prefixes | Invalid queue admission and unreconciled push | Preserves sealed-byte lineage beyond commit ancestry |
| 5 | Compare pin, lock, schema, and receipt | Untested or stale format qualification | Prevents parser-version and manifest-byte mismatch |
| 6, 10 | Enumerate namespace inputs and compare closure | Reuse across relevant input changes | Avoids unrelated-tip invalidation without trusting candidate scope |
| 11, 12 | Freeze sources and derive print time | Changed close card or nondeterministic report | Byte-identical reporting over a fixed tree |
| 13, 14 | Compare staged bytes and regenerate | Stale generated report in a commit | Keeps derived output synchronized without autonomous staging |
| 15, 16 | Resolve internally and refuse escape | Out-of-root path or crossed repository boundary | Filesystem containment and history separation |
| 17, 18 | Verify backups and withhold inherited approval | Unsafe migration or implicit reapproval | Crash recovery and preservation of evidence semantics |

For Alice Step 2A Prong Two, the independent claims apply mathematical derivations to executable artifact identity, storage placement, and coherent machine-readable snapshots. The prevention register names concrete writes and transitions the system refuses. The argument is an improvement to pipeline integrity and deterministic operation, not the mere use of cryptography or automation for an abstract administrative rule.

For Step 2B, any asserted inventive concept rests on the ordered interaction of the claimed mechanisms. Each primitive faces substantial prior-art pressure. Implementation gaps and the possibility of an aggregation objection remain material; the drafting posture does not promise eligibility or nonobviousness.

### 8.16 EPO and India technical-effect notes

For EPO Article 52 and Guidelines G-II 3.3 and 3.3.1, hashing, normalization, ordering, and projection binding serve the specific technical purpose of maintaining data integrity and deterministic reproducibility of a distributed pipeline. The claimed steps govern filesystem writes, queue acceptance, and snapshot use. They do not improve a business score or claim a mathematical result in isolation, and no new machine-learning model is required.

For independent system claim 1 under India s.3(k), the technical problem is identity circularity and inconsistent distributed artifact state. The technical solution uses a normalized digest domain, ordered token derivation, byte-derived placement, and manifest-bound memory publication. In the Ferid Allani and Microsoft v. Assistant Controller vocabulary, the proposed measurable technical benefit is stable identity under valid evidence accrual, refusal of duplicate residency, and reproducible projection consumption; these are testable properties, not measured results asserted here, and no novel hardware is required.

For independent method claim 19 under India s.3(k), the technical problem is unsafe sequencing of concurrent file preparation and publication. The technical solution orders hashing before marker planting, binds classification before authoring, checks actual residency, and admits proposals only against the current epoch. The proposed measurable technical benefit is deterministic refusal of mismatched bytes and conflicting proposals while unrelated preparation remains mergeable. Ferid Allani and Microsoft v. Assistant Controller support framing the contribution by technical effect rather than a computer-program label; no novel hardware is required.

For independent storage-medium claim 20 under India s.3(k), the technical problem is reproduction of the same integrity constraints across processing installations. The instructions implement the same byte-domain normalization, storage-write restrictions, and epoch/view binding as the system and method claims. The proposed measurable technical benefit is identical valid identities and projection bindings for identical inputs, with refusal on changed protected inputs. This is the technical-contribution framing of Ferid Allani and Microsoft v. Assistant Controller, not a claim that a medium label alone avoids exclusion; no novel hardware is required.

### 8.17 Evidence boundaries and drafting record

The historical parent claims preserve normalization, write-once identity, and pre-byte routing support, while current code supplies narrower tree-hash, queue, placement, and publication checks. The present draft does not silently upgrade contract language to implementation evidence. Nor does it silently preserve the parent's obsolete three-section self-written tracker or retired evidence-mirror layout.

In one implementation, the modern tracker is whole-file generated, and anchor graduation changes current residency without changing the admission classification. Those distinctions carry into the claims. The permanently fixed-root historical embodiment remains described only as an alternative incompatible with relocation of that same home.

Ethara.AI is the stated applicant and assignee, and the disclosure describes its Trinity project. That authorship interest is explicit. Human review must address priority support, unity, restriction strategy, the cited patent families, the deferred controls, and claim scope before any filing decision.

### 8.18 Scope, single-actor operation, and the permanently human acts

File names, paths, role names, predicate strings, refusal codes, algorithms, and configured counts identify examples rather than mandatory claim vocabulary. The claims use generic mechanisms. The specification's illustrative count does not convert the structural ceiling into a grant-adjustable policy.

A single platform operator may perform or cause each claimed operation through separate processes or services. Different logical authorities need not be different legal entities. The operator can enforce task/evidence write separation and serialized publication while using shared conventional hardware. Actual runtime isolation and remote admission remain subject to the evidence limitations above.

The drafting party reconciles this disclosure and never files it. Filing is a human act. Publication beyond the repository, operational acceptance, and admission into a human-graded calibration library also remain human decisions. No statement asserts any filing, deployment, or measured pass rate.

## 9. CLAIMS

What is claimed is:

**1. A system for maintaining integrity of machine-learning evaluation bundles, comprising:** one or more processors; one or more non-transitory memories storing instructions that cause the processors to bind a lane classification from a closed vocabulary at a digest-bound approval gate before authoring bundle bytes; compute a task digest over a canonical domain that replaces designated canary-slot values with fixed placeholders while retaining slot quantities and positions; derive a task identifier from the task digest and a namespace pinned in approved scope, derive canary values from the task digest by a pure key-derivation function, plant the derived values after hashing, and bind the task identifier to the resulting representation in an acyclic hash-derive-plant-bind order; refuse reassignment of the task identifier to different normalized task bytes; maintain a single authoritative bundle home and a separately keyed rollout-evidence subtree holding no task bytes and governed by an evidence-write authority distinct from task-write authority; retain the lane classification for the life of the task identifier, re-derive residency from committed bytes, and select current placement by a deterministic reconciliation function that refuses duplicate residency and enforces a structural residency ceiling that no requirements grant relaxes; and prepare run-specific memory proposals against a current epoch, then serialize publication by validating proposal bases and conflicts, materializing an immutable successor epoch with a manifest, and publishing projections bound to a digest of the manifest before designating the successor as current.

**2.** The system of claim 1, wherein the instructions further cause the processors to bind a normalization-domain version, retain slot ordering and surrounding bytes in the canonical domain, re-derive expected canary values from the task digest, and refuse a planted value that differs from its expected value even when the normalized digest matches.

**3.** The system of claim 1, wherein the instructions further cause the processors to append seals to producer-run-specific hash-chained streams whose application payload consists of an identifier, bundle digest, seal instant, and producer run identity, reject an additional application field, maintain run-specific claim files, and refuse work violating a pending-depth bound or claim lifetime.

**4.** The system of claim 3, wherein the instructions further cause the processors to require every accepted stream to remain an exact byte prefix of its proposed successor, refuse an unresolvable accepted revision, and refuse a push offering a non-deletion commit other than the local commit whose tree satisfies reconciliation checking.

**5.** The system of claim 1, wherein the instructions further cause the processors to record a current stable delivery-format release from a package index in a dated lock, execute that format's validator under an exact release pin in an isolated interpreter, bind a validation receipt to manifest bytes and the pin, and refuse a stale or untested pin, stale lock, drifted schema, or inconsistent receipt.

**6.** The system of claim 1, wherein the instructions further cause the processors to mint a run identity once within a closed grammar, confine mutable private run state to the namespace of that identity, refuse reopening under a different declared owner, and maintain independent run streams whose merge preserves each stream's existing bytes.

**7.** The system of claim 1, wherein the instructions further cause the processors to refuse publication on conflicting proposals to a file or a proposal against a superseded epoch, publish anchor standing with the projections under the manifest-digest binding, and refuse a compatibility copy or projection that differs from the current epoch.

**8.** The system of claim 1, wherein the reconciliation function seats ungraduated anchor bundles before ordinary resident bundles ordered by seal order, retains eligible residents up to the structural residency ceiling, and relocates overflow to another root without changing their task identifiers or lane classifications.

**9.** The system of claim 8, wherein the reconciliation function graduates an anchor only when published anchor standing indicates that its duration row is folded into memory, relocates the anchor to free a resident seat without reading the underlying duration ledger, and refuses to infer graduation from unreadable standing.

**10.** The system of claim 7, wherein the instructions further cause the processors to qualify a run against a computed subject closure comprising its namespace inputs, sealed or judged bundle identities, human input roots, a consumed projection checked against the epoch, and a governing-specification gitlink rather than a repository tip, such that an unrelated commit outside the closure does not invalidate qualification and a change to an included input does.

**11.** The system of claim 1, wherein the instructions further cause the processors to emit at terminal run closure a write-once tracker card whose state fields derive from the run's identity record, report, and progress record and whose source bindings comprise their digests, preserve a recorded closing instant upon identical re-emission, and refuse changed sources, missing inputs, identity mismatch, or a malformed card.

**12.** The system of claim 11, wherein the instructions further cause the processors to render a complete tracker from run cards and run reports without a run editing the tracker, derive its print instant from recorded disk state rather than a render-time wall clock, and produce byte-identical renderings for identical inputs.

**13.** The system of claim 12, wherein repository hooks render generated report bytes into a working tree, compare expected report bytes with staged report bytes before a commit, and name differing paths for human action without staging, committing, amending, or pushing any bytes.

**14.** The system of claim 13, wherein repository attributes bind the generated reports to a merge driver that retains a local generated representation during merge and causes a subsequent whole-file rendering from merged source records, with staged-byte comparison refusing an obsolete representation.

**15.** The system of claim 1, wherein the instructions further cause the processors to anchor path resolution to a trusted startup root whose direct child is a vendored governing-specification checkout, prevent candidate bytes from selecting that root, require canonical explicitly relative authored, persisted, and printed paths, and use absolute resolution only internally to refuse traversal and symbolic-link escape.

**16.** The system of claim 15, wherein the instructions further cause the processors to require a closed roster of governing, memory, public-bundle, private-bundle, and execution-harness roots registered as submodules against distinct remotes, refuse parent-tracked task bytes and crossed root boundaries, and hold a retired evidence-mirror root pending reconciliation.

**17.** The system of claim 15, wherein the instructions further cause the processors to migrate project structure only through a closed supported version matrix under an exclusive lock, preserve immutable content-addressed backups, perform atomic writes with a resumable journal, and hold on an unknown version, unsafe path, changed evidence, unproved seal, or required revalidation.

**18.** The system of claim 17, wherein the migration preserves existing signed bytes without transferring their authority to changed bytes, creates no key, edits no approval or trust policy, changes no role membership or threshold, and withholds current acceptance until affected bytes satisfy ordinary validation, audit, and signing requirements.

**19. A computer-implemented method for maintaining integrity of machine-learning evaluation bundles, comprising:** binding, by one or more processors, a lane classification from a closed vocabulary at a digest-bound approval gate before authoring bundle bytes; computing a task digest over a canonical domain that replaces designated canary-slot values with fixed placeholders while retaining slot quantities and positions; deriving a task identifier from the task digest and a namespace pinned in approved scope and deriving canary values from the task digest by a pure key-derivation function; planting the derived values after hashing and binding the identifier to the resulting representation in an acyclic hash-derive-plant-bind order; refusing reassignment to different normalized task bytes; maintaining a single authoritative bundle home and a separately keyed rollout-evidence subtree holding no task bytes under evidence-write authority distinct from task-write authority; retaining the lane classification for the life of the identifier, re-deriving residency from committed bytes, and selecting placement by deterministic reconciliation that refuses duplicate residency and enforces a structural residency ceiling that no requirements grant relaxes; and preparing run-specific memory proposals against a current epoch followed by serialized publication that validates proposal bases and conflicts, materializes an immutable successor epoch with a manifest, and publishes projections bound to the manifest digest before designating the successor as current.

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by one or more processors, cause the processors to maintain integrity of machine-learning evaluation bundles by:** binding a lane classification from a closed vocabulary at a digest-bound approval gate before authoring bundle bytes; computing a task digest over a canonical domain that replaces designated canary-slot values with fixed placeholders while retaining slot quantities and positions; deriving a task identifier from the task digest and a namespace pinned in approved scope and deriving canary values from the task digest by a pure key-derivation function; planting the derived values after hashing and binding the identifier to the resulting representation in an acyclic hash-derive-plant-bind order; refusing reassignment to different normalized task bytes; maintaining a single authoritative bundle home and a separately keyed rollout-evidence subtree holding no task bytes under evidence-write authority distinct from task-write authority; retaining the lane classification for the life of the identifier, re-deriving residency from committed bytes, and selecting placement by deterministic reconciliation that refuses duplicate residency and enforces a structural residency ceiling that no requirements grant relaxes; and preparing run-specific memory proposals against a current epoch followed by serialized publication that validates proposal bases and conflicts, materializes an immutable successor epoch with a manifest, and publishes projections bound to the manifest digest before designating the successor as current.

## 10. ABSTRACT OF THE DISCLOSURE

Systems maintain integrity of machine-learning evaluation bundles across concurrent runs. A canonical hash domain replaces designated canary values with placeholders while retaining slot structure. A digest determines a write-once task identifier and derived canaries in an acyclic hash, derive, plant, and bind sequence. A single task home excludes separately governed rollout evidence from task identity. A digest-bound lane classification and byte-derived residency govern deterministic placement under a structural ceiling. Runs prepare memory proposals against a current epoch; publication checks conflicts and produces an immutable successor with manifest-bound projections. Qualification may bind a computed subject closure rather than a repository tip. Closed queue streams, format-validation receipts, frozen tracker cards, clock-free report rendering, contained paths, and authority-preserving migration provide additional integrity controls.
