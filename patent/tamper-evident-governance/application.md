# UNITED STATES NON-PROVISIONAL UTILITY PATENT APPLICATION

**Filed under 35 U.S.C. § 111(a)**

**Title:** Tamper-Evident Capture, Attribution, and Anti-Sabotage Control of Agent-Operated Repositories

**Inventor:** Sarvex Jatasra

**Applicant / Assignee:** Ethara.AI

**Docket Reference:** Trinity/tamper-evident-governance

---

## 1. TITLE OF THE INVENTION

Tamper-Evident Capture, Attribution, and Anti-Sabotage Control of Agent-Operated Repositories

This is a draft for human filing review. The title-block filing phrase identifies the intended application form and does not assert a filing.

## 2. CROSS-REFERENCE TO RELATED APPLICATIONS

The related disclosure is titled "Cryptographically Controlled Certification of Machine-Learning Evaluation Tasks Using Isolated Generation, Audit, and Evidence Domains." Its filing is prospective. This application is intended as a divisional or continuation of that disclosure, with the choice left to the human filing decision.

The present description supplies its own technical disclosure rather than relying on the related text to supply missing mechanisms. The related draft describes this subject in sections 8.26, 8.27, 8.38, and 8.42 and claims 29, 30, and 37. Those internal draft references establish neither priority nor entitlement to benefit.

Human counsel must reconcile common disclosure, new matter, inventorship, and any actual restriction requirement before selecting a route. A divisional designation and the protection of section 121 require the applicable facts and consonance; a proposed family partition alone supplies neither.

## 3. STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

## 4. FIELD OF THE INVENTION

The disclosure concerns repository security for software agents that receive human instructions and modify version-controlled artifacts. It concerns tamper-evident input capture, verification of current governing bytes, rule-based detection of hostile repository changes, credential-separated incident observation, and cryptographic decisions about successor repository state.

## 5. BACKGROUND OF THE INVENTION

A first deficiency concerns selective logging. A system that logs only instructions classified as corrections cannot distinguish a quiet operator from an omitted instruction. A cryptographically sound chain proves continuity only for the records that enter it; it does not prove capture of every received input.

A second deficiency concerns stale governing code. A valid signature on an old checkout proves a signature over old bytes. It does not establish equality with the current upstream security specification. A cached success becomes an unsafe substitute when the upstream cannot be resolved.

A third deficiency concerns erasure of a refusal. A bounded history scan can cease to display a hostile change after history replacement or enough padding commits. Treating the resulting clean scan as remediation rewards removal of the evidence rather than correction of the defect.

A fourth deficiency concerns shared observation authority. A candidate workflow that holds incident credentials can manufacture accusations or remove evidence about itself. A candidate-local ledger also disappears when the candidate state disappears unless another domain retains the observation.

A fifth deficiency concerns namespace impersonation. An editable run marker can name any principal. Signing that marker alone leaves later operations unbound, while signing individual artifacts without chain context permits reordering or transplantation into another run.

A sixth deficiency concerns self-selected baselines. A candidate that chooses its own accepted base can make its destructive changes appear to preserve prior state. A merge can contain an accepted commit without being the single successor that an admission boundary expects.

A seventh deficiency concerns excessive invalidation. Binding a qualification to the repository tip invalidates an unrelated run when a collaborator changes bytes outside that run's inputs. Conversely, binding only a local output ignores changed inputs that should invalidate it.

An eighth deficiency concerns hidden history mutation. A hook that stages regenerated reports can include bytes the human does not review. A textual merge of generated reports can produce a report corresponding to neither source state nor merged state.

These deficiencies motivate a computing architecture that prevents phase work until its evidence and governing bytes qualify. The architecture retains the evidence of refusals, separates observation authority, and compares candidate state against trust that the candidate does not select.

## 6. SUMMARY OF THE INVENTION

The system comprises processors, memories, an input-capture path, a chain verifier, a specification-currency gate, and a rule-based repository classifier. Every received human turn enters a verbatim ledger without a classification filter. The chain verifier walks the attesting chain before phase execution.

The currency gate requires an unmodified governing checkout equal to a fetched upstream tip. Behind, diverged, dirty, and unresolvable checkouts all block phase work. A cached success, prior approval, or signed envelope does not waive the gate.

The classifier compares commit structure, signature evidence, static instrument structure, and governed paths. It treats a history operation that removes an existing refusal from observation as a further instance of the refused class. A preserving remediation path requires append-only evidence and authorization disjoint from the authority introduced by the flagged change.

Dependent embodiments separate a secretless candidate probe from an observer with independent governance. Other embodiments authenticate every authoritative run operation, decide lawful succession from a caller-supplied trusted context, bind qualification to a computed subject closure, and stop at a human commit gate without staging bytes.

The implementation supports many local predicates but not a complete admission service. The description distinguishes executable checks from contractual sequencing, external identity enrolment, observer deployment, and the prospective historical-remediation reader. A claimed combination describes an embodiment, not a declaration that every part operates today.

## 7. BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 depicts the input receiver, append-only feedback records, companion hash chain, signed checkpoint, root report, and fail-closed phase scheduler.

FIG. 2 depicts the currency gate resolving upstream state and refusing phase execution for behind, diverged, locally modified, or unresolvable governing checkouts.

FIG. 3 depicts the rule-based sabotage classifier, per-run sentinel streams, rolling-window repeat detection, and distinct clearance and historical-remediation paths.

FIG. 4 depicts the secretless candidate workflow, allowlisted application bridge, separately governed observer, immutable probe, and external incident database.

FIG. 5 depicts signed run operations and a successor decision over candidate bytes against a caller-supplied accepted baseline, pinned trust digest, enrolled principals, and authenticated operator.

FIG. 6 depicts subject-closure hashing and generated-report rendering, with a human commit gate between working-tree writes and authoritative repository history.

## 8. DETAILED DESCRIPTION OF THE INVENTION

### 8.1 Overview

An agent-operated repository contains candidate artifacts, governing specifications, per-run state, and human-facing reports. A run receives instructions, performs phases, and offers resulting bytes for review. An operator may control candidate files and local hooks, so a local declaration cannot establish external authority.

The disclosed ordering separates input receipt from phase work. Receipt and preservation remain permissible during a block; authoring or audit phase work does not. A scheduler in the complete embodiment admits phase work only after capture, chain verification, currency verification, and applicable refusal checks succeed. PROSPECTIVE runtime enforcement supplements the contract sequencing described below.

A durable observation outside candidate control is necessary to detect erasure of all candidate-local history and checkpoints. A local chain alone cannot defeat an administrator who replaces both its data and every anchor. The complete embodiment therefore preserves refusals outside the mutable candidate state.

Evidence labels identify implementation support, not measured performance. First-landed dates below are file-introduction dates from local commit history, not dates when every current predicate first exists. Test citations identify inspectable fixtures; they do not assert execution of those tests during preparation of this draft.

### 8.2 Definitions

A human-originated turn is an input received from outside the agent's own execution through the human-input interface, irrespective of its content, usefulness, or classification. An empty turn remains a turn when the interface records its receipt.

Phase work means the substantive authoring, evaluation, or state-changing work of a run. Capture, verification, recording a block, and presenting a human gate are not phase work for this ordering.

A closed schema permits exactly its enumerated fields and specified values. A residual classification preserves a turn that does not fit a more specific class; it does not authorize omission.

An append-only chain contains ordered records whose digest links each entry to its predecessor. A checkpoint authenticates a chain position and head digest under a trusted signing policy. Rewriting a chain together with its local head is not protection against an external anchor.

A stale governing checkout is any checkout that is behind, diverged, locally modified, or unresolvable against the fetched upstream branch tip. Equality of resolved revisions and a clean checkout are necessary for currency.

A governance path carries authority or gate configuration. A subject path carries bytes that authority governs. A same-commit comparison detects co-editing; it does not establish the independence of the governance administrator.

A refusal is a machine decision that prevents a specified operation. A finding is its retained evidence, not proof of an actor's mental intent. The sabotage classifier is a deterministic rule-based classifier over commit shape and evidence, not a machine-learning classifier.

A disjoint principal group contains no principal belonging to the excluded authority set under the governing enrolment policy. Different strings or different keys alone do not prove distinct humans.

A trusted context is a caller-supplied structure containing an accepted base revision, trust-policy digest, enrolled-principal set, project identity, and authenticated operator. Its authority comes from the caller's governance boundary, never from a baseline asserted by the candidate.

A lawful successor preserves protected accepted state while adding only authorized records and advancing ordered state according to the transition rules. A successful decision is not an atomic update of an accepted reference.

A subject closure is a deterministic enumeration of a run's namespace, applicable inputs, views, governing revision, and relevant bundle identities, excluding designated derived outputs. Its digest binds that content rather than every byte at the repository tip.

### 8.3 Total prompt capture, attribution, and pre-work chain verification

The complete capture path appends every received human turn verbatim before phase work. Contract pastes, re-pastes, questions, acknowledgements, corrections, and approver argument records all enter the ledger. A classifier supplies metadata only after receipt cannot be discarded. CONTRACT-ONLY (ENGRAM.md:114-118; FORGE.md:119-123).

In one implementation, the record schema contains exactly the following fields. Their names illustrate a concrete serialization and do not limit the claims. CONTRACT-ONLY (ENGRAM.md:118).

| Field | Content and constraint |
| --- | --- |
| feedback_id | Dense positive record identifier, without gaps or reuse |
| received_at | UTC receipt instant |
| kind | One of contract_paste, correction, instruction, question, approval_record, or other |
| verbatim | Exact received prompt bytes, without trimming or paraphrase |
| invocation_context | Branch or batch, reconstructed phase state, current revision, and attribution source |
| github_id | Resolved hosting-platform login, or explicit unattributed value |
| probable_reasoning | Append-only dated machine hypotheses, never facts about private human thought |
| targets | Clauses, phases, invariants, or artifacts the turn addresses |
| chain_seq | Position of the corresponding attesting chain entry |
| disposition | Pending, applied, accepted, rejected, or superseded standing |

The machine records an unclassifiable turn under the residual class. Only a human supplies the accepted or rejected feedback disposition. Malformed input remains preserved with a malformed indication rather than silently disappearing. CONTRACT-ONLY (ENGRAM.md:116-119).

In one implementation, attribution first resolves the authenticated GitHub CLI user's login, then the runtime-provided GITHUB_ACTOR value. If neither resolves, the record carries unattributed and a named gap. The path never guesses from an email, Git configuration name, or filesystem owner, and identity failure never suppresses capture. CONTRACT-ONLY (ENGRAM.md:117; FORGE.md:122).

The attribution ladder is not equivalent to cryptographic human identification. The current chain-shape check requires a nonempty login string; it does not itself authenticate the session or execute the ladder. DEFERRED (DEFERRED.md: "Feedback `github_id` attribution authenticity").

In one implementation, the companion line contains exactly the following fields and uses sorted-key compact UTF-8 JSON with a terminating newline. The entry digest covers the fields other than the entry digest itself, using the specified canonical hash input. CONTRACT-ONLY (ENGRAM.md:120).

| Field | Binding |
| --- | --- |
| seq | Dense chain position |
| captured_at | UTC capture instant |
| feedback_id | Attested record identifier |
| kind | Record classification |
| verbatim_sha256 | SHA-256 of exact prompt bytes |
| record_sha256 | SHA-256 of the canonical record at append time |
| writer | Runtime, model lineage, and writing revision |
| github_id | Same attributed login as the record |
| prev_hash | Preceding entry digest, or zero digest at genesis |
| entry_hash | SHA-256 sealing the preceding fields |

In one implementation, the current head position and digest fold into the signed checkpoint log, and the root report prints both. The report publishes an anchor outside the chain file without disclosing prompt contents. CONTRACT-ONLY (ENGRAM.md:121; FORGE.md:126).

The full walk recomputes every entry digest, predecessor link, sequence position, verbatim digest, and append-time record digest. It checks one-to-one coverage between captured turns, ledger records, and chain lines and compares the resulting head to the signed checkpoint. A missing chain beside a nonempty ledger, unreadable bytes, or uncovered head prevents phase work. CONTRACT-ONLY (ENGRAM.md:97, 121).

The inspected chain verifier enforces canonical line shape, dense sequence, predecessor linkage, recomputed entry hashes, and signature-backed checkpoint matching. ENFORCED (tools/integrity.py, first landed 2026-06-24; tests/test_integrity_parent.py).

That verifier alone does not establish receipt completeness or recompute every ledger record against its append-time serialization. Its absence check also cannot detect an omitted turn when all feedback artifacts are absent. The complete receipt-to-record walk remains a stronger contract obligation, not an inference from a structurally valid chain. CONTRACT-ONLY (ENGRAM.md:116, 121).

Later hypotheses and standing updates must not alter the append-time digest domain. A preserving embodiment retains the original record snapshot and represents subsequent changes as appended events referencing that snapshot. This supplies the original bytes for later digest comparison without rewriting an old line. PROSPECTIVE serialization refinement requires support review before any continuity claim.

The report names the first broken position with expected and observed digests. A signed reconciliation explains a break while retaining evidence; it does not make altered original bytes authentic. A complete runtime refuses to resume until the required walk succeeds under the reconciliation policy. CONTRACT-ONLY (ENGRAM.md:121).

The local checker does not prove that a runtime calls it before work rather than afterward. Enforcing that order requires a trusted invocation boundary. DEFERRED (DEFERRED.md: "The gate preflight ran before phase work, not after").

### 8.4 Governing-specification currency gate

The gate resolves the vendored governing checkout and fetches the tracked upstream branch tip on invocation. It compares the checked-out revision to the fetched revision and inspects local modifications. A tracking declaration without that comparison cannot establish currency. CONTRACT-ONLY (ENGRAM.md:61-65; FORGE.md:66-70).

In one implementation, the fetch targets upstream main and the emitted refusal codes distinguish these outcomes. ENFORCED (tools/integrity.py, first landed 2026-06-24; tools/gate.py, first landed 2026-09-16; tests/test_freshness.py).

| Observed condition | Decision in one implementation |
| --- | --- |
| Clean checkout equal to fetched main | Currency predicate passes |
| Checkout behind fetched tip | TRINITY_FRESHNESS_BEHIND, hard block |
| Checkout diverged from fetched tip | TRINITY_FRESHNESS_DIVERGED, hard block |
| Local modification | TRINITY_FRESHNESS_LOCALLY_MODIFIED, hard block |
| Missing remote, checkout, network resolution, or failed fetch | TRINITY_FRESHNESS_UNVERIFIABLE, hard block |
| Missing Git executable | TRINITY_FRESHNESS_GIT_ABSENT, hard block |

A cached currency record cannot replace the fetched tip. A prior sign-off cannot authorize an older revision. A signed approval envelope cannot convert an unresolvable checkout into a current checkout. CONTRACT-ONLY (ENGRAM.md:65).

The gate emits the local revision, resolved upstream revision when available, and a dated reason for refusal. An unavailable upstream revision remains unavailable in the report, never an invented equality. A complete scheduler admits no phase work until the current-byte predicate passes. CONTRACT-ONLY (ENGRAM.md:65).

This posture differs from immutable dependency pinning. The immutable probe used by an observer protects verifier identity; the moving-reference gate protects governing-specification currency. Each has a different object and a different trust purpose.

The freshness fixtures construct local upstream and vendored repositories to distinguish equality, behind state, divergence, local modification, and resolution failures. They support the predicate without asserting a live network fetch in this drafting pass. ENFORCED (tools/integrity.py, first landed 2026-06-24; tests/test_freshness.py).

### 8.5 Rule-based sabotage classification and preserving clearance

The classifier inspects committed records, signatures, static syntax, repository configuration, and working-tree state. It does not ask a language model whether an operator seems malicious. Its findings describe mechanical refusal conditions, not adjudications of intent. ENFORCED (tools/sabotage.py, first landed 2026-09-16; tests/test_sabotage.py).

The disclosed closed refusal set contains the following conditions. The historical-erasure rule extends an existing refused class rather than permitting an open-ended accusation taxonomy. CONTRACT-ONLY (ENGRAM.md:69; FORGE.md:74).

| Refusal condition | Machine comparison |
| --- | --- |
| Disposition unbound | Report standing lacks the required bound machine record |
| Signature unverified | Disposition signature or authorized signer does not verify |
| Inert required instrument | Static syntax reveals only gap, constant, or empty return paths without a live decision |
| Uncommitted evidence | Cited evidence lacks committed repository bytes |
| Non-canonical remote | Governing checkout resolves to a remote outside the canonical policy |
| Off-branch checkout | Governing checkout is not on its tracked branch |
| Typed sign-off | A typed approval substitutes for the recomputed digest or verified signature |
| Governance edit beside subject | One commit changes governing authority and the subject it governs |
| Dirty tree | Relevant uncommitted bytes remain at the gate |

In one implementation, the AST scan examines required-instrument functions and their own return nodes. A raise, assertion, live marker, or non-gap call can establish a decision path for this heuristic. The scan is not a proof of all possible program behavior. ENFORCED (tools/sabotage.py, first landed 2026-09-16; tests/test_sabotage.py).

In one implementation, same-commit co-editing without bypass syntax produces suspicion, while bypass syntax or an entering release token supports the blocking workflow-tamper class. The current scan examines a bounded recent history, not an immutable lifetime history. ENFORCED (tools/sabotage.py, first landed 2026-09-16; tests/test_sabotage.py).

The historical doctrine treats rewriting, force-pushing, replacement, or padding that removes a refusal from the scan window as a further instance of that refused class. A prospective evaluator compares previously retained flagged commit identities with candidate history and the current scan window. It appends an erasure finding if an offered recovery removes the original evidence. CONTRACT-ONLY (ENGRAM.md:69); PROSPECTIVE historical-erasure evaluator.

In one implementation, each run appends its refusals to a separate sentinel stream with a hash-linked attempt ledger and head. Independent streams avoid two clones extending the same chain position. The repeat evaluator reads their union rather than treating a new stream as a new actor. ENFORCED (tools/sentinel.py, first landed 2026-09-16; tests/test_sentinel.py).

The rolling-window evaluator counts qualifying attempts using retained actor and run identities, with duplicate observations of the same attempt not creating independent retries. Crossing the configured repeat threshold adds an alert. In one implementation, SAB_REPEATED_ATTEMPT caps the disposition at BLOCK. ENFORCED (tools/sentinel.py, first landed 2026-09-16; tests/test_sentinel.py).

The repeat alert clears only through a signed typed envelope whose authenticated principal satisfies a distinct clearance role. In one implementation, a DSSE envelope uses a software SSH key, allowed_signers, and the versioned trust root's sentinel_clearer role. The eligible set excludes the alerted actor's verified principals. ENFORCED (tools/sentinel.py, first landed 2026-09-16; tests/test_sentinel_clearance.py).

In one implementation, a plain clearance file carrying a name instead of a signature yields SAB_SENTINEL_CLEARANCE_UNSIGNED and clears nothing. Clearance binds the alert and its underlying attempts rather than a free-text assertion that a problem is fixed. ENFORCED (tools/sentinel.py, first landed 2026-09-16; tests/test_sentinel_clearance.py).

An actor with no verifiable commit signature supplies no verified principal to exclude. Therefore string attribution cannot establish self-clearance resistance for that actor. DEFERRED (DEFERRED.md: "A clearance for an alert raised against an unverified actor excludes nobody").

Historical workflow-tamper remediation is separate from repeat-alert clearance. Its append-only record binds flagged commit identities, corrective commits, a re-verified trust snapshot, and rerun evidence. Authorized signers form a principal group disjoint from every authority introduced by the flagged commits. Original commits and findings remain retained, with resolved standing rather than erasure. CONTRACT-ONLY (ENGRAM.md:69).

No registered checker currently consumes that historical remediation record. The historical finding therefore remains blocking while the record-reader obligation is open. DEFERRED (DEFERRED.md: "no registered check reads a remediation record").

The complete preserving mechanism would reject unsigned remediation, authority introduced by the flagged change, and a missing original commit. It would append a resolution edge only after the corrective evidence and disjoint authorization verify. PROSPECTIVE remediation-reader embodiment, distinct from the implemented sentinel-clearance verifier.

### 8.6 Secretless candidate sentinel and separately governed observer

The candidate workflow holds no secret, dispatch capability, delivery authority, or release authority. It runs a reviewed probe from an immutable revision over candidate bytes as data, never executing candidate scripts. In one implementation, the workflow is sentinel.yaml. CONTRACT-ONLY (ENGRAM.md:77); template support in templates/sentinel.yaml.

The probe performs bounded reads and static checks, including instrument inertness and gate-bypass syntax. It emits finding codes and a digest rather than sending an accusation. Candidate-side qualification checks use the same pinned checkout but do not convert the diagnostic into an external incident. ENFORCED (tools/incident_probe.py, first landed 2026-09-16; tests/test_incident_probe.py).

A separately governed observer accepts dispatch only through an allowlisted application bridge. Governance fixes sender and source identities; the hosting platform supplies the authenticated event context. The observer resolves target repository, workflow run, run attempt, actor, ref context, and commit using the platform API rather than trusting candidate text. CONTRACT-ONLY (ENGRAM.md:77); template support in templates/sentinel-observer.yaml.

The inspected template checks source identifiers against governance configuration, queries the target run and commit, and checks out the resulting immutable commit as data. Its durable incident schema records the commit, not a separate ref field. Independent proof of deployment and exhaustive ref-policy enforcement is not inferred from that template.

The observer reruns the same reviewed probe read-only. Only its authenticated rerun can supply an incident to the external store. The candidate has no reset or ingestion credential for that store. CONTRACT-ONLY (ENGRAM.md:77); PROSPECTIVE deployment boundary.

In one implementation, the closed incident carrier is trinity.sentinel-incident/v1 with the fields schema, repository_id, repository, run_id, run_attempt, occurred_at, actor_id, actor_login, commit_sha, evidence_digest, and finding_codes. The store derives an event identity from repository, run, and attempt rather than accepting an arbitrary event identifier. ENFORCED (tools/incident_store.py, first landed 2026-09-17; tests/test_incident_store.py).

The parser refuses duplicate JSON keys, extra or missing fields, oversized input, malformed identifiers, unsupported findings, and timestamps outside the admitted bounds. It validates bounded positive run-attempt integers and fixed-form commit and evidence digests. ENFORCED (tools/incident_store.py, first landed 2026-09-17; tests/test_incident_store.py).

External SQLite state retains incidents, conflicting observations of the same event as equivocations, and threshold-crossing repeat alerts. Duplicate equal observations do not erase or replace the original. A bounded status query reports retained state without supplying a reset operation. ENFORCED (tools/incident_store.py, first landed 2026-09-17; tests/test_incident_store.py).

A meaningful repeat alert causes a nonzero status result; an operational or integrity failure also fails closed rather than presenting a clean status. The service contains no delivery transport, recipient, or send path. Incident retention is not proof that a notification reaches a person. ENFORCED (tools/incident_store.py, first landed 2026-09-17; tests/test_incident_store.py).

The bridge, application credentials, allowlists, observer runner, durable volume, and monitoring are external provisioning obligations. DEFERRED (DEFERRED.md: "this session configured none of that infrastructure"). No deployment is asserted here.

### 8.7 Run-operation signed chain

Authority attaches to each authoritative write rather than merely to an editable run marker. A statement binds project identity, run identity, operation verb, record digest, chain position, predecessor digest, and principal. The verifier authenticates both the statement bytes and the principal's role. ENFORCED (tools/operations.py, first landed 2026-09-20; tests/test_operations.py).

In one implementation, trinity.run-operation/v1 carries project, run_id, verb, artifact_digest, seq, previous, and principal, together with its schema identifier. The artifact digest is SHA-256 of the authorized record. The supported verbs denote opening, sealing, claiming, recording a verdict, and publishing. ENFORCED (tools/operations.py, first landed 2026-09-20; tests/test_operations.py).

A DSSE envelope protects the typed payload. The verifier checks allowed_signers and authorizes the verified principal against the versioned trust root at the evaluation instant. In one implementation, the purpose-specific role is run_operator. ENFORCED (tools/operations.py, first landed 2026-09-20; tests/test_operations.py).

In one implementation, OPERATION_PRINCIPAL_MISMATCH rejects a valid signature whose verified identity does not include the statement's claimed principal. OPERATION_CHAIN_BROKEN rejects sequence, predecessor, or run-membership mismatch. OPERATION_ENVELOPE_INVALID and OPERATION_UNAUTHORIZED distinguish malformed or unverified envelopes from missing role authority. ENFORCED (tools/operations.py, first landed 2026-09-20; tests/test_operations.py).

Removing an interior operation, inserting an operation without updating its successor, or reordering entries breaks the following link. Detecting deletion of an entire suffix also requires an accepted head or accepted-state comparison; a prefix alone cannot prove that a later entry once existed.

The transition signing check matches new claims and verdicts by their content digests against verified operation statements. It rejects an envelope located in another run's namespace. It is not a universal interposition layer for every filesystem write. ENFORCED (tools/transition_signing.py, first landed 2026-09-20; tests/test_transition.py).

A parent lacking an enrolled operation role can still receive structure-only evaluation where no signing policy is supplied. A complete authoritative-write embodiment would require the signing policy and chain check at every admission. DEFERRED (DEFERRED.md: "a parent with no enrolled `run_operator` role is judged on structure alone").

The binding between a key and a distinct human remains external enrolment work. A cryptographic signature proves control of the enrolled key, not an independently verified human identity. DEFERRED (DEFERRED.md: "the trust root names principals, nothing here proves a principal is a distinct person").

### 8.8 Lawful-successor decision against trusted context

The caller supplies the accepted base, pinned trust-policy digest, enrolment set, and authenticated operator. Candidate bytes supply the proposed successor only. Reading a baseline declaration from the candidate would permit self-authorization and is not the disclosed trusted-context decision. ENFORCED (tools/transition.py, first landed 2026-09-18; tests/test_transition.py).

The decision resolves the base and candidate to commits. For a state-changing transition, the candidate must have exactly the accepted base as its sole parent. A candidate equal to the base can represent a no-op; containment of the base somewhere in merge ancestry does not authorize a changed candidate. ENFORCED (tools/transition.py, first landed 2026-09-18; tests/test_transition.py).

In one implementation, accepted_state.py reads protected paths and blob identities from commit objects without executing candidate scripts. It supplies state to the transition rules. It has no dedicated test file; coverage is indirect through the transition tests. ENFORCED (tools/accepted_state.py, first landed 2026-09-18; tests/test_transition.py, indirect coverage only).

The decision applies the following refusal rules to protected accepted state. ENFORCED (tools/transition.py, first landed 2026-09-18; tools/transition_records.py, first landed 2026-09-18; tools/transition_signing.py, first landed 2026-09-20; tests/test_transition.py).

| Proposed change | Refusal |
| --- | --- |
| Sole parent differs from accepted base | Base mismatch |
| Accepted base buried as a merge parent | Base mismatch |
| Queue stream rewritten or truncated | Accepted byte prefix does not survive |
| Accepted claim or verdict mutated or deleted | Protected record continuity fails |
| Accepted sentinel or epoch deleted | Protected evidence disappears |
| Accepted immutable sentinel or epoch bytes changed | Protected record mutation |
| Append-only sentinel stream rewritten | Prior accepted byte prefix changes |
| Namespace write outside accepted principal binding | Foreign-run write |
| Operator outside enrolment set | Unenrolled operator |
| Second claim on an accepted assignment or double claim in one transition | Contested claim |
| Verdict without the accepted owner's prior claim | Orphan or unowned verdict |
| Epoch publication not next in sequence | Epoch fork |
| Current pointer moves backward | Epoch rollback |
| New seal instant precedes accepted watermark | Backdated ordering |
| Candidate carries trust-policy bytes not equal to the pin | Trust drift |

Append-only streams may grow while preserving their exact accepted prefixes. Immutable records may not change. The decision therefore distinguishes a lawful appended sentinel event from mutation of an existing event rather than forbidding all sentinel growth.

Accepted claim order decides ownership, not a timestamp supplied by a competing auditor. A verdict follows a claim already present in the accepted state, so an offered claim and verdict cannot jointly invent prior ownership. ENFORCED (tools/transition_records.py, first landed 2026-09-18; tests/test_transition.py).

The trust check compares any candidate-carried policy bytes to the pinned digest; absence does not create a new policy. When the caller supplies signing policy, claim and verdict acceptance also requires a matching verified operation digest. ENFORCED (tools/transition_signing.py, first landed 2026-09-20; tests/test_transition.py).

Nothing here atomically advances a protected accepted reference. A complete admission service would hold exclusive write authority, decide against the current accepted base, and serialize successful updates so competing candidates cannot both succeed against an obsolete base. PROSPECTIVE admission service.

No process in the repository holds that exclusive write authority or invokes the transition decision as admission. Local pre-push refusal and post-push detection are weaker properties. DEFERRED (DEFERRED.md: "no process holds exclusive write on an accepted ref, so nothing invokes it as admission").

### 8.9 Subject-closure binding

A run's qualification binds a computed content closure instead of the tip commit. The closure includes the run namespace, human input roots, applicable role view, relevant bundle identities, and governing revision. Derived reports and progress outputs are excluded to avoid self-invalidating qualification. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py).

In one implementation, each manifest entry records kind, logical path, normalized executable mode, size, and digest. The manifest sorts entries deterministically before hashing. A symlink or non-regular file where regular bytes are required prevents safe closure computation. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py).

The author closure contains bundle identities sealed by that run. The auditor closure contains bundle identities judged by that run and its own allowed view. The closure does not absorb a peer's outputs merely because those outputs share a repository. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py).

A foreign commit whose changes lie wholly outside the closure leaves the qualification binding unchanged. A foreign commit changing a shared input lies inside the closure and invalidates the binding. "Foreign" therefore does not mean that all changes by another person are irrelevant.

This prevents unrelated tip movement from requiring a replacement qualification while preserving invalidation for changed governing inputs. It does not waive the separate currency gate or establish a release authorization. ENFORCED (tools/subject.py, first landed 2026-09-18; tests/test_subject.py).

### 8.10 Write-without-stage discipline and report merge binding

Instruments write working-tree bytes but never stage, commit, amend, or push. A run halts at a commit gate and prints exact changed paths grouped by repository, submodule changes before parent gitlinks, a suggested message, and the command for the report moment. A human commits before the run resumes. CONTRACT-ONLY (ENGRAM.md:79).

The report moment can produce only the permitted report, receipt, disposition, tracker, and sentinel outputs, followed by another human commit gate. This resolves the apparent conflict between a dirty-tree refusal and generation of the report that describes it. CONTRACT-ONLY (ENGRAM.md:79).

Hooks obey the same no-stage and no-history-write discipline. Before commit or merge commit, they compare staged reports to deterministic rendering and refuse mismatch while leaving replacement bytes for human review. After merge or rewrite, report refresh remains advisory. ENFORCED (tools/report_staging.py, first landed 2026-09-20; tests/test_hooks.py).

In one implementation, pre-commit and pre-merge-commit call the staged report checker; post-checkout checks report currency; post-merge and post-rewrite render reports; pre-push checks reconciliation and accepted stream prefixes. The hooks never stage their outputs. Template support: templates/pre-commit, templates/pre-merge-commit, templates/post-checkout, templates/post-merge, templates/post-rewrite, and templates/pre-push.

In one implementation, gitattributes binds the root reports to the trinity-generated custom merge driver. The driver keeps the local rendering, and the next render derives reports from merged inputs instead of textually combining two generated outputs. Installed-template checks refuse missing attributes or a changed driver. ENFORCED (tools/gate.py, first landed 2026-09-16; tests/test_hooks.py).

The signed-report tests separately check byte binding of a human report to its signed counterpart. They do not establish hook installation or that an agent cannot issue arbitrary shell commands. ENFORCED (tools/report_staging.py, first landed 2026-09-20; tests/test_hooks.py); related report evidence: tests/test_report_binding.py.

A bypassable local hook is not an exclusive admission boundary. The complete execution-domain embodiment would deny history-writing capabilities to the agent itself. PROSPECTIVE capability restriction; CONTRACT-ONLY (ENGRAM.md:79).

### 8.11 Named prior art and novelty residue (RSL, gittuf, and related art)

Capture: Schneier and Kelsey secure audit logs, IBM US7305564B1, and Snodgrass et al., VLDB 2004, supply substantial tamper-evident logging context. US12613956B2 concerns log-tampering prevention. The novelty residue is unconditional verbatim capture coupled to an end-to-end walk as a precondition of phase execution, not hash chaining alone.

Capture attribution: the register describes US12555008 as a classification-gated cognitive inference ledger and US12651078 as monitoring agent communications through a distributed ledger. The novelty residue is a fixed attribution ladder that never suppresses capture when identity fails, with omission itself treated as a coverage defect rather than an uneventful interval.

Currency: US12602481 NOVACOV supplies fail-closed permits with freshness policy and graded dispositions. OpenSSF Scorecard pinned-dependencies expresses the inverse posture for dependency versions. The novelty residue is equality of governing bytes to a fetched moving tip, with unresolvable explicitly stale and no cache, approval, or signature waiver.

Sabotage: Torres-Arias et al. RSL, USENIX Security 2016, gittuf, NDSS 2025, and git-ratchet supply authenticated reference history and repository-update protection. The novelty residue is reflexive classification of evidence erasure into the class it would remove, coupled to disjoint-group append-only remediation that preserves flagged commits. The bounded current scanner alone does not supply that entire difference.

Observation: Sigstore Rekor v2, gitsign, and US12651078 provide logging, signing, and agent-observation context. The novelty residue is a candidate without accusation credentials plus a separately governed observer that authenticates platform identities, reruns an immutable probe as data inspection, and retains incidents without candidate reset authority or delivery transport.

Run operations: in-toto attestation and DSSE, RFC 9943 SCITT, and SLSA Source track v1.2 already support strong provenance and signed statements. The novelty residue sought is the ordered run-operation binding of record digest, principal, and predecessor together with namespace and accepted-state refusal, not the envelope format or a signature alone.

Succession: RSL, gittuf, and git-ratchet make rollback and reference authorization a serious obviousness comparison. The novelty residue is the combined successor decision using caller-supplied baseline, pinned policy digest, enrolment set, and authenticated operator while rejecting candidate-selected authority, protected-state deletion, contested claims, and backwards ordered state.

Subject closure: SLSA Source track v1.2 and in-toto provide source and artifact provenance. The novelty residue sought is selective run qualification over enumerated inputs and namespace bytes that survives unrelated tip changes but not shared-input changes. Content hashing in isolation is not the asserted distinction.

Write discipline: gitsign and Sigstore Rekor authenticate repository activity without, by that fact alone, excluding agent staging. The novelty residue is the combined human commit stop, hook no-stage restriction, and regeneration-bound report merge path. This is a narrower dependent fallback, not a claim that human commits or merge drivers are new.

The IETF draft-sharif-agent-audit-trail (revision 04 current as of 2026-09-15, revision 03 as retrieved; agent-verified 2026-09-21), draft-sahu-agent-action-receipts-00 (agent-verified 2026-09-21), and draft-maintainer-1f916-agent-record-01 (agent-verified 2026-09-21) directly pressure agent-logging breadth. Their reported status and teachings require human verification before reliance in filing or an information disclosure statement.

The section 103 headwind is substantial from RSL, gittuf, SCITT, DSSE, and the reported agent-logging drafts. The proposed distinctions rest on the ordered preventive combination, not a claim that its cryptographic primitives are individually novel. This local-register comparison is neither an exhaustive search nor a patentability opinion.

### 8.12 Scope, single-actor operation, and the permanently human acts

File names, paths, tool names, predicate strings, refusal codes, role labels, numerals, and fixed parameters describe illustrative implementations only. Functionally comparable storage, signature, and hashing formats may serve the same structural relationships. Claims recite the relationships and refusal behavior rather than branded vocabulary.

A single platform operator may perform or cause every claimed step across separate logical execution domains. Separation concerns credential issuance, write authority, and authenticated principal sets, not a requirement for distinct legal entities or physical computers. Software-key custodians within the same organization can occupy disjoint governed roles.

The drafting party reconciles this description and never files it. Filing is a permanently human act, as are publication beyond the repository, operational acceptance, and admission to human-graded calibration holdings. No statement asserts any filing, deployment, or measured pass rate.

This draft uses current local source and the portfolio's prior-art register. No network retrieval supports this drafting pass. Human review must verify bibliographic details, effective prior-art dates, family support, restriction facts, and final claim scope before any filing decision.

### 8.13 Prevention register and eligibility anchors

The following register links claims to prevented computer operations. It distinguishes the complete claimed architecture from partial implementation support and supplies Step 2A Prong Two anchors rather than relying on the word "agent" for eligibility.

| Claims | Operative verbs | Artifact or operation prevented | Technical anchor |
| --- | --- | --- | --- |
| 1, 19, 20 | Captures, recomputes, compares, prevents | Phase dispatch without input continuity or current governing bytes | Execution gate changes when repository work can occur |
| 1, 18, 19, 20 | Classifies, retains, excludes | Clean standing obtained by erasing a refusal | Rule-based commit-shape mechanism preserves the refused history |
| 2, 17 | Records, retains | Unattributed or unclassifiable input disappearing | Total receiver-to-ledger mapping |
| 3 | Signs, publishes, compares | Acceptance of an unauthenticated chain head | Externalized head commitment |
| 4-7 | Resolves, compares, blocks | Work under behind, diverged, dirty, or unresolvable governance | Fail-closed repository and network-security gate |
| 8, 9 | Chains, counts, excludes | Repeat bypass or self-clearance by an authenticated actor | Per-run continuity and role-separated clearance |
| 10 | Denies, authenticates, reruns, retains | Candidate-issued incident authority or reset | Credential-separated observer and read-only data handling |
| 11, 12 | Verifies, binds, rejects | Forged principal or transplanted operation | Typed cryptographic operation chain |
| 13, 14 | Pins, compares, refuses | Self-authorized or destructive successor | Accepted-state continuity from external context |
| 15 | Enumerates, hashes, preserves | Unrelated tip change invalidating qualification | Content-dependent binding without global-tip dependence |
| 16 | Halts, compares, regenerates | Agent staging or arbitrary generated-report merge | Human-reviewed history and deterministic report bytes |

Recentive Analytics v. Fox warns against treating a generic machine-learning classifier applied to a new setting as the invention. Claims 1, 18, 19, and 20 instead concern a rule-based classifier over commit shape and retained evidence. The reflexive rule changes which repository transition the machine refuses; it is not a proposal to train a model to recognize sabotage.

For Alice Step 2B, the asserted combination joins unconditional capture, cryptographic continuity, moving-reference currency, and preserving refusal state. The argument does not rest on generic processors, ordinary record keeping, or cryptography in the abstract. The deferred runtime and remediation components require clear support, not exaggerated implementation assertions.

### 8.14 EPO and India technical-effect notes

Under EPO Article 52 and Guidelines G-II 3.3 and 3.3.1, hashing and rule evaluation serve specific network and repository-security purposes. They prevent execution under unverifiable governing bytes, detect tampered history, and reject unauthorized successor state. The classifier uses no ML training step; any model-generated probable reasoning remains advisory and does not determine acceptance.

For India s.3(k), independent claim 1 addresses the technical problem of agent phase execution proceeding on incomplete or tampered repository evidence. The technical solution interlocks capture, chain verification, current-revision comparison, and preserving refusal state. The measurable technical benefit is observable refusal of unauthorized phase dispatch and retention of flagged commit evidence, not an asserted benchmark result. In the Ferid Allani and Microsoft v. Assistant Controller framework, no novel hardware is required for that claimed computer-security effect.

For India s.3(k), independent claim 19 addresses the technical problem of a repository transition hiding missing input or stale governance behind a passing record. Its technical solution orders byte capture and verification before phase execution and refuses erasure-based clearance. The measurable technical benefit is a reproducible blocked transition on a changed digest, unresolvable upstream, or removed refusal, without relying on novel hardware.

For India s.3(k), independent claim 20 addresses the technical problem of stored program instructions permitting execution before repository integrity predicates hold. The technical solution causes the processor to enforce the same capture, freshness, and preserving-clearance interlock. The measurable technical benefit is prevention of an otherwise reachable unsafe execution state on conventional hardware, consistent with the technical-effect vocabulary of Ferid Allani and Microsoft v. Assistant Controller.

These jurisdictional positions are drafting arguments for human counsel. They establish no eligibility ruling, grant, or measured result.

## 9. CLAIMS

What is claimed is:

**1. A system for tamper-evident control of an agent-operated repository, comprising:** one or more processors; one or more non-transitory memories storing instructions that cause the processors to append a verbatim record of every received human-originated turn without classification gating and a corresponding digest-linked chain entry; walk the chain end to end as a precondition of phase work and prevent the phase work upon a failed walk; admit a governing-specification checkout only when unmodified and equal to a fetched upstream branch tip, treating a behind, diverged, locally modified, or unresolvable checkout as stale and preventing the phase work irrespective of a cached result, prior approval, or signed approval envelope; and apply a rule-based repository classifier that refuses a governance edit committed with its governed subject, classifies a history rewrite, force-push, replacement, or padding that removes a prior refusal from a scan window as a further instance of the refused class, and permits clearance of that refusal only through an append-only signed remediation record authorized by a principal group disjoint from authority introduced by flagged commits while preserving the flagged commits and refusal evidence.

**2.** The system of claim 1, wherein attribution first selects an authenticated repository-hosting command-line login, then a runtime-supplied hosting-platform actor identity, and otherwise records an unattributed value with a named coverage gap without guessing an identity or suppressing capture.

**3.** The system of claim 1, wherein the processors fold a chain-head sequence position and digest into a signed checkpoint, publish both in a root report, and reject a chain head that does not match the checkpoint.

**4.** The system of claim 1, wherein the processors determine that the checkout is behind the fetched upstream branch tip and hard-block phase work despite a cached currency result.

**5.** The system of claim 1, wherein the processors determine that the checkout diverges from the fetched upstream branch tip and hard-block phase work despite prior approval.

**6.** The system of claim 1, wherein the processors detect local modifications in the checkout and hard-block phase work despite a signed approval envelope.

**7.** The system of claim 1, wherein inability to resolve the checkout, its remote, or the fetched upstream branch tip constitutes staleness and hard-blocks phase work without an offline waiver.

**8.** The system of claim 1, wherein the processors append refusal attempts to hash-chained sentinel streams assigned per run, evaluate qualifying attempts across the streams within a rolling window, and cap disposition at a blocking value upon a repeat threshold crossing attributed to an alerted actor.

**9.** The system of claim 8, wherein clearance of a repeat alert requires a typed signed envelope using a software-held signing key under a distinct clearance role, verification against an allowed-signer policy and versioned trust root, and exclusion of the alerted actor's verified principals from eligible clearers, and wherein a typed unsigned clearance clears nothing.

**10.** The system of claim 1, further comprising a candidate workflow having no secrets, dispatch authority, delivery authority, or release authority and running only an immutable reviewed probe over candidate data, and a separately governed observer that accepts requests only through an allowlisted application bridge, authenticates sender and target identities through a hosting-platform interface, reruns the probe read-only, and retains closed-schema incidents, equivocations, and repeat alerts in external state with bounded inspection and without candidate reset authority or a delivery transport.

**11.** The system of claim 1, wherein each authoritative run write requires a typed signed operation statement binding project identity, run identity, operation verb, a cryptographic digest of the authorized record, sequence position, predecessor digest, and principal, verified against an allowed-signer policy and a versioned trust root under an operation-authorizing role.

**12.** The system of claim 11, wherein the processors reject a signature whose verified principal does not match the statement's claimed principal, reject an operation whose sequence, predecessor link, or namespace membership breaks the run chain, and reject an invalid envelope or a principal lacking role authorization.

**13.** The system of claim 1, wherein the processors decide lawful succession of a candidate revision against a caller-supplied trusted context binding an accepted base revision, a trust-policy digest, an enrolled-principal set, and an authenticated operator rather than against the candidate's own baseline assertion.

**14.** The system of claim 13, wherein the succession decision refuses a changed candidate without the accepted base as sole parent, a merge that buries the base as another parent, a rewritten or truncated accepted queue stream, mutation or deletion of an accepted claim, verdict, sentinel entry, or epoch, a namespace write outside its accepted principal binding, an unenrolled operator, a double claim, a verdict without an accepted owner's claim, a non-sequential epoch, a backwards current pointer, a seal instant preceding an accepted watermark, or candidate-carried trust-policy bytes differing from the pinned digest.

**15.** The system of claim 1, wherein qualification binds a digest computed over a run's namespace and enumerated inputs rather than a repository tip revision, such that a commit changing only bytes outside that closure leaves the qualification binding unchanged and a change to a bound input invalidates the binding.

**16.** The system of claim 1, wherein an instrument and repository hooks write working-tree bytes without staging, committing, amending, or pushing, the instrument halts at a human commit gate displaying changed paths grouped by repository and a suggested message, and generated reports use a custom merge driver followed by deterministic regeneration and staged-byte comparison.

**17.** The system of claim 1, wherein each verbatim record has a closed field set for record identity, receipt instant, kind, verbatim content, invocation context, attributed identity, appended reasoning hypotheses, targets, chain position, and disposition, and each corresponding chain entry binds capture time, writer, attributed identity, record identity, kind, verbatim digest, record digest, sequence, predecessor digest, and entry digest.

**18.** The system of claim 1, wherein the classifier's refusal set comprises unbound disposition, unverified signature, an inert required instrument detected by abstract-syntax-tree inspection, uncommitted evidence, a non-canonical governing remote, an off-branch checkout, typed sign-off, governance co-editing with its subject, and a dirty tree, and wherein the remediation record binds corrective commits, a re-verified trust snapshot, and rerun evidence while retaining the flagged commits and recording resolution without erasure.

**19. A computer-implemented method for tamper-evident control of an agent-operated repository, comprising:** appending, by one or more processors, a verbatim record of every received human-originated turn without classification gating and a corresponding digest-linked chain entry; walking the chain end to end as a precondition of phase work and preventing the phase work upon a failed walk; admitting a governing-specification checkout only when unmodified and equal to a fetched upstream branch tip, treating a behind, diverged, locally modified, or unresolvable checkout as stale and preventing the phase work irrespective of a cached result, prior approval, or signed approval envelope; and applying a rule-based repository classifier that refuses a governance edit committed with its governed subject, classifies a history rewrite, force-push, replacement, or padding that removes a prior refusal from a scan window as a further instance of the refused class, and permits clearance of that refusal only through an append-only signed remediation record authorized by a principal group disjoint from authority introduced by flagged commits while preserving the flagged commits and refusal evidence.

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by one or more processors, cause the processors to control an agent-operated repository by:** appending a verbatim record of every received human-originated turn without classification gating and a corresponding digest-linked chain entry; walking the chain end to end as a precondition of phase work and preventing the phase work upon a failed walk; admitting a governing-specification checkout only when unmodified and equal to a fetched upstream branch tip, treating a behind, diverged, locally modified, or unresolvable checkout as stale and preventing the phase work irrespective of a cached result, prior approval, or signed approval envelope; and applying a rule-based repository classifier that refuses a governance edit committed with its governed subject, classifies a history rewrite, force-push, replacement, or padding that removes a prior refusal from a scan window as a further instance of the refused class, and permits clearance of that refusal only through an append-only signed remediation record authorized by a principal group disjoint from authority introduced by flagged commits while preserving the flagged commits and refusal evidence.

## 10. ABSTRACT OF THE DISCLOSURE

Systems, methods, and storage media control agent-operated repositories through preconditions on phase execution. Every received human turn enters a verbatim ledger without classification gating and receives a digest-linked chain entry. An end-to-end chain walk and equality of an unmodified governing checkout to a fetched upstream tip precede phase work. Unresolvable currency fails closed without an approval waiver. A rule-based classifier treats history changes that erase a refusal as further instances of the refused class and requires disjointly authorized append-only remediation preserving flagged commits. Dependent mechanisms separate a secretless candidate probe from an independently governed observer with persistent incidents and no reset. Signed run-operation chains authenticate authoritative records. A caller-supplied trusted context governs lawful-successor decisions, and subject-closure digests preserve qualification across unrelated commits. Instruments and hooks write without staging, while human commit gates and deterministic report regeneration preserve reviewable history.
