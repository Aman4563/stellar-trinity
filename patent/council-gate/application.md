# UNITED STATES NON-PROVISIONAL UTILITY PATENT APPLICATION

**Filed under 35 U.S.C. § 111(a)**

**Title:** Out-of-Band Discharge of Digest-Bound Sign-Off Gates by a Unanimous Multi-Lineage Model Council, with Hazard-Scoped Conduct of Isolated Instruments

**Inventor:** Sarvex Jatasra

**Applicant / Assignee:** Ethara.AI

**Docket Reference:** Trinity/council-gate

---

## 1. TITLE OF THE INVENTION

Out-of-Band Discharge of Digest-Bound Sign-Off Gates by a Unanimous Multi-Lineage Model Council, with Hazard-Scoped Conduct of Isolated Instruments

This document is a prospective application draft. The statutory title-block legend identifies the intended application form and does not assert a filing.

## 2. CROSS-REFERENCE TO RELATED APPLICATIONS

The related parent disclosure is titled "Cryptographically Controlled Certification of Machine-Learning Evaluation Tasks Using Isolated Generation, Audit, and Evidence Domains." Its filing is prospective. This application is intended as a divisional or continuation of that disclosure, with the choice left to the human filing decision and the applicable support and restriction requirements.

Parent sections 8.14, 8.28, and 8.36 supply the digest gate, council, and conductor context. Parent claim 34 and its drafting notes distinguish council approval from external release authorization. This draft elevates council discharge to independent system, method, and storage-medium claims without importing the parent's full certification architecture.

No priority date, application number, restriction requirement, or entitlement to a statutory safe harbor is asserted. Counsel must confirm support and any benefit claim before a human filing decision.

## 3. STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

## 4. FIELD OF THE INVENTION

The disclosure concerns cryptographic controls on machine-readable sign-off gates in model-assisted artifact production. It concerns digest comparison, signature authorization, model-lineage constraints, transcript binding, and prevention of unauthorized gate-state transitions. It also concerns sequencing isolated execution domains without conveying their private working state. CONTRACT-ONLY (GAUNTLET.md:5-15,43-57; MAESTRO.md:5-13,28-34).

## 5. BACKGROUND OF THE INVENTION

A first deficiency concerns approval detached from artifact identity. A review statement or digest file alone does not establish which authority approves which version. Capital One's US12001822B2 addresses multi-signature validation of deployment artifacts, but signature multiplicity alone does not specify the council and failed-attack conjunction disclosed here.

A second deficiency concerns correlated review. Multiple processes may share a model lineage, and a majority can outvote a valid objection. Verga et al.'s PoLL, arXiv 2404.18796, and IBM/Kyndryl US11328214B2 provide relevant panel and dissimilar-platform context. Neither panel size nor platform diversity alone establishes the required producer-excluding lineage relation.

A third deficiency concerns an empty inspection record. An approving ballot can mean that a reviewer sees no defect without identifying any attack that it attempts. The unanimity analysis in arXiv 2609.15803 addresses strategic reviewers; it does not by itself bind a concluded attack transcript to current artifact bytes.

A fourth deficiency concerns authority expansion through a compatibility interface. tZero US11392940B2 supplies M-of-N context. IETF draft-schrock-ep-authorization-receipts supplies authorization-receipt and self-approval context (revision 01 as retrieved, revision 13 current as of 2026-09-12; agent-verified 2026-09-21, human sign-off pending). A threshold or receipt alone does not distinguish an internally dischargeable gate from an act that remains permanently human.

A fifth deficiency concerns an orchestration channel around an isolation boundary. Auditor-independence statute separates engagement management from an audit opinion, and Brewer and Nash's Chinese Wall restricts conflicting access. Conventional workflow orchestrators such as Apache Airflow sequence work and support output exchange. Those features alone do not confine a conductor to derived reports while fixing its gate-hold relation in specification text.

A sixth deficiency concerns retrospective accountability. A panel can produce an aggregate verdict that obscures each member's participation. Avizienis N-version programming and DO-178C provide diversity and assurance context, but diversity alone does not define an append-only false-approval record charging every unanimous seat or an external demotion decision.

These comparisons identify drafting issues, not conclusions of anticipation, validity, or freedom to operate. The art descriptions follow the portfolio register and parent conductor passage without a new network search. The informal Qorum Method repository, checked on 2026-09-21, describes single-reviewer risk-tiered delegation with a human approver rather than a multi-model panel, and the reported quorum-review skill was not located, so neither is relied on as a panel-review teaching.

## 6. SUMMARY OF THE INVENTION

The proposed system maintains a digest-bound sign-off gate in a shut state. A judgment function recomputes artifact identity and verifies an external approver role before an automated approval can change that state. The producer cannot approve its own bytes. CONTRACT-ONLY (GAUNTLET.md:5,43-51).

An argument function records applicable break-attempt lanes over frozen bytes. A council comprises at least three seats with pairwise-distinct model lineages, all distinct from the producer lineage. Each seat weighs the same record independently without seeing other ballots before casting its own. CONTRACT-ONLY (GAUNTLET.md:6-7,10,14,52-57).

Only unanimous approval after concluded, unsuccessful break attempts supports an approving envelope. The envelope binds the artifact digest, producer and approver identities, producer lineage, roster, cast verdicts, and transcript digest. A legacy digest file serves compatibility and never replaces that authority. CONTRACT-ONLY (GAUNTLET.md:43-47,54).

Lineage collision, insufficient qualifying seats, missing authority, or invalid evidence leaves human sign-off as the fallback. Publication beyond the repository, patent filing, operational acceptance against a capped disposition, and admission into a human-graded calibration library remain excluded from automated discharge. CONTRACT-ONLY (GAUNTLET.md:10-14,45,55,80).

A rejection opens a bounded dispute. The producing instrument alone revises its artifact, and a revision requires another attack over the new frozen bytes. False approvals charge every approving seat, while a separate memory instrument owns demotion and a human controls restoration. CONTRACT-ONLY (GAUNTLET.md:63-76).

A separate conductor sequences record-keeper, author, and auditor movements without performing their work or discharging gates. Restricted reads, content-free lane prompts, specification-fixed hazard holds, and a cycle synchronization barrier preserve isolation while allowing movements outside a hold to proceed. CONTRACT-ONLY (MAESTRO.md:5-13,28-34).

All council and conductor mechanisms in this disclosure are contract specifications, not implemented council or conductor modules. The two narrow existing checks identified in section 8.12 do not establish an operating council, an operating conductor, or machine enforcement of every asserted boundary.

## 7. BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 depicts a proposed gate-state path from a frozen artifact through digest recomputation, attack recording, blind council ballots, signature validation, and a compatibility digest write. A separate human path remains available, and the permanently-human class has no automated discharge edge. CONTRACT-ONLY (GAUNTLET.md:5-14,43-57).

FIG. 2 depicts a proposed signed envelope carrying a typed predicate, artifact digest, external approver authorization, producer identity and lineage, roster and ballots, transcript digest, signing instant, and validity bound. The legacy digest interface is downstream of the approving envelope. CONTRACT-ONLY (GAUNTLET.md:43-47).

FIG. 3 depicts a proposed dispute thread whose arguments receive rebuttals or producer revisions. Re-attack follows changed bytes, convergence requires unanimous approval, and exhaustion escalates to human sign-off. A calibration branch records contradiction evidence against every approving seat. CONTRACT-ONLY (GAUNTLET.md:63-76).

FIG. 4 depicts a proposed memory, argument, and judgment partition with single-writer ownership. The memory lobe mediates standing, the argument lobe owns attack and dispute records, and the judgment lobe owns approval records and the signing credential. CONTRACT-ONLY (GAUNTLET.md:25-29,82,87).

FIG. 5 depicts a proposed conductor outside three instrument harnesses. Fixed movement order and a fixed hazard relation govern launches; a cycle barrier, pending-gates stop, and repeated-state guard govern continuation. The consolidated sheet presents instructions but has no approval-writing path. CONTRACT-ONLY (MAESTRO.md:7-13,28-41).

## 8. DETAILED DESCRIPTION OF THE INVENTION

### 8.1 Overview

In a proposed embodiment, one or more processors execute stored instructions for an out-of-band gatekeeper and a consuming gate. The gatekeeper does not create the artifact under review. Its authority derives from a human-authorized trust policy rather than from its own assertion of competence. CONTRACT-ONLY (GAUNTLET.md:5,45,80-82).

The consuming gate treats discharge as a machine-state transition that enables an otherwise held operation on particular bytes. Approval is not a statement that an artifact is correct for all purposes. It has a digest identity, an authorized scope, a recorded inspection basis, and a validity bound. CONTRACT-ONLY (GAUNTLET.md:43-55).

In one implementation, the gatekeeper work order is GAUNTLET.md and the conductor work order is MAESTRO.md. The sources on disk contain 95 and 52 lines respectively. Citations in this draft refer to the actual on-disk line numbering.

The parent describes these mechanisms as embodiments; this sibling explicitly marks their current evidence class. A description of what instructions would prevent is not evidence that the repository already supplies those instructions as an executable council or conductor service.

### 8.2 Definitions

A digest-bound sign-off gate is a control whose approval concerns the artifact bytes identified by a canonical cryptographic digest and whose consuming check recomputes identity before proceeding. A frozen artifact is the byte representation to which that digest binds, not a promise that storage cannot change. CONTRACT-ONLY (GAUNTLET.md:43-51).

An approval envelope is a signed, typed record whose required fields identify the gate, bytes, authority, reviewer roster, outcome, and attack evidence. A compatibility digest file is the consumer's pre-existing digest input and is not independent proof of out-of-band authority. CONTRACT-ONLY (GAUNTLET.md:43-47).

An external trust root is authorization state outside the producer's authority, against which the consuming instrument resolves the signer role. Externality concerns write and credential authority, not whether another legal entity holds the key. CONTRACT-ONLY (GAUNTLET.md:45,80-82).

A model lineage is a recorded equivalence class for model derivation, rather than a process identifier or a display name. As a prospective formalization of the parent drafting definition, shared base model, training pipeline, or provider derivation establishes an equivalence relation recorded with the trust policy before review. PROSPECTIVE; the required roster and lineage exclusions are CONTRACT-ONLY (GAUNTLET.md:10,44,80).

A qualifying council has at least three seats whose lineage classes differ pairwise and from the producer class. A blind ballot is a seat's verdict formed without access to another seat's ballot before its own cast. Unanimity for discharge means every seated verdict approves, not that a threshold subset approves. CONTRACT-ONLY (GAUNTLET.md:10,14,44,54,57).

A failed break-attempt transcript records an attack that concludes without breaking the bound artifact. It does not mean a crashed attack process, an unavailable lane, or an empty record. A lane that cannot conclude supplies a gap and forces rejection. CONTRACT-ONLY (GAUNTLET.md:6,52-56).

A dispute thread is an append-only sequence of arguments, rebuttals, revisions, and withdrawals under a bound round count. Its closing states are convergence with unanimous approval of final bytes, or escalation with surviving arguments and human fallback. CONTRACT-ONLY (GAUNTLET.md:63-68).

A lobe is a functional ownership partition within one gatekeeper run. Single-writer ownership assigns each artifact to exactly one lobe and prohibits sibling writes. A later division into separate instruments preserves these assignments. CONTRACT-ONLY (GAUNTLET.md:25-29,87).

A movement is one instrument invocation in an isolated lane, including same-lane resumption at a gate. A cycle contains record-keeper, author, and auditor movements in that fixed launch order. A gate halt pauses a movement rather than completing it. CONTRACT-ONLY (MAESTRO.md:28-31,45).

A hazard relation is the fixed specification relation identifying which movements an open gate holds. A cycle barrier prevents a new cycle while a closing-cycle gate remains open or a lane remains unfinished. Steady state compares report fingerprints, residency counts, and pending-gate sets across two consecutive cycles. CONTRACT-ONLY (MAESTRO.md:31-34).

### 8.3 Digest-bound gate, compatibility interface, and permanently-human class

The judgment lobe first recomputes the artifact's canonical digest from disk. Disagreement with the producer's digest claim refuses further approval processing. This mirrors the recompute-first gate of parent section 8.14 without assuming that a producer-supplied digest proves byte identity. CONTRACT-ONLY (GAUNTLET.md:51).

The consuming check also recomputes the digest before the approved operation. Changed bound bytes invalidate the old approval. In one implementation the digest is canonical SHA-256 and the legacy file contains the same digest bytes that a human approval would supply. CONTRACT-ONLY (GAUNTLET.md:44,46,51).

The legacy file is an interface, not authority. For out-of-band discharge, the signed envelope must independently verify under the consuming instrument's trust policy. A digest file without qualifying authority cannot convert an automated actor into a human approver. CONTRACT-ONLY (GAUNTLET.md:43-46).

The permanently-human class comprises publication of task bundles or a manuscript beyond the repository, patent filing, recording operational acceptance against a capped disposition, and admission of a staged candidate into the human-graded calibration library. No envelope, tier authorization, or council verdict discharges any act in this class. CONTRACT-ONLY (GAUNTLET.md:11,55).

Operational acceptance does not raise the signed disposition. Every proposed discharge first runs the producing instrument's report gate, and an approval over report prose above the minted record is void. In one implementation, publication of sample bundles also passes a release verifier before the separate human act. CONTRACT-ONLY (GAUNTLET.md:11).

The initial grant of autonomous authority itself requires a human signature. Lower-tier authorization does not grant higher-tier authority, and the governing-specification freshness gate admits no council waiver. These are additional boundaries, not additions silently substituted for the enumerated permanently-human class. CONTRACT-ONLY (GAUNTLET.md:15,55,80-81).

### 8.4 Recorded break-attempt precondition

The argument lobe attacks frozen bytes without editing them. Applicable lanes include contradiction search against requirements, drift comparison with prior approved bytes, semantic red-teaming of checkers, feedback-ledger correction checks, and closed-vocabulary and reference-resolution sweeps. CONTRACT-ONLY (GAUNTLET.md:7,52).

Each attack record identifies a date, target clause, method, and outcome. A lane runs to a recorded conclusion. A lane that cannot run creates a named gap and forces rejection instead of disappearing from the inspection record. CONTRACT-ONLY (GAUNTLET.md:35,52-53).

Independent lanes may execute in parallel, but a failed process is not an unsuccessful break attempt. The orchestrating run merges lane transcripts; only a complete record of applicable lanes without a break can support approval. CONTRACT-ONLY (GAUNTLET.md:53-57).

The judgment lobe receives the frozen bytes and full transcript. It does not author attacks that it then weighs. Approval without an attached failed-attack transcript is void even if every seat otherwise supplies an approving ballot. CONTRACT-ONLY (GAUNTLET.md:6,54,57).

The envelope binds the transcript digest to the same artifact digest that the gate consumes. Substitution of another artifact or another transcript would defeat the binding rather than establish a fresh approval. CONTRACT-ONLY (GAUNTLET.md:44,51,54).

The gatekeeper may read only surfaces that the gated instrument may read. Attack breadth cannot justify access to private material excluded by that instrument's information boundary. An unavailable permitted attack remains a gap, not permission to cross the boundary. CONTRACT-ONLY (GAUNTLET.md:8,53).

### 8.5 Council roster, blind balloting, and fail-closed fallback

The roster requires at least three qualifying seats. Every seat has a member identity and a model lineage, and each lineage differs from the producer lineage and every other seated lineage. Several instances of one lineage do not supply diversity. CONTRACT-ONLY (GAUNTLET.md:10,14,44).

Each seat weighs the full transcript independently. Its lane receives the frozen transcript and bound bytes, sees no sibling lane, and returns a ballot with reasons to the judgment lobe alone. Ballots meet there only after the seats cast them. CONTRACT-ONLY (GAUNTLET.md:54,57).

Every seat must approve for an approving verdict. Any dissent resolves to rejection, including a mixture of approving and rejecting ballots. Even unanimous ballots cannot override an attack lane that breaks the artifact or cannot conclude. CONTRACT-ONLY (GAUNTLET.md:14,53-54).

A lineage collision causes human fallback. A runtime that cannot seat the required qualifying roster also falls back to human sign-off rather than lowering the seat count. Sequential attack execution does not excuse the council requirement. CONTRACT-ONLY (GAUNTLET.md:10,14,57).

A rejecting verdict writes no legacy digest file. It leaves the gate shut and opens the bounded dispute path. Thus dissent first yields rejection and dialogue, while a roster failure denies autonomous authority and leaves the human route available. CONTRACT-ONLY (GAUNTLET.md:47,54,63-67).

Lineage separation does not establish statistical independence or guarantee absence of common blind spots. The disclosed mechanism constrains admissible rosters and evidence, not an asserted probability of correctness. CONTRACT-ONLY (GAUNTLET.md:1,10,14).

### 8.6 Signed approval envelope and authorization

In one implementation, the envelope uses DSSE and the declared predicate type `trinity.approval/v1`. The closed payload has a monotonic project approval identifier and a gate identity naming the specification, phase, and bound artifact path. CONTRACT-ONLY (GAUNTLET.md:43-44).

The payload includes the canonical bound digest, approver identity and role, producer identity, and producer model lineage. The consuming instrument verifies the signature and resolves the role against its own trust root. A self-asserted role is insufficient. CONTRACT-ONLY (GAUNTLET.md:44-45).

The payload also includes every seat's identity, lineage, and cast verdict; the attack transcript digest; the aggregate verdict; a signing instant; and a validity bound. In one implementation the instant follows RFC 3339 UTC and verdict tokens are `approve` and `reject`. CONTRACT-ONLY (GAUNTLET.md:44).

Producer and approver identities must differ. A self-signed approval fails closed as though no approval exists. The judgment lobe alone holds the signing key, and that key never resides in the producing instrument's harness or any repository byte. CONTRACT-ONLY (GAUNTLET.md:5,27,82).

On a valid approving verdict, the judgment lobe signs the envelope and writes the legacy digest file byte-identically to the human interface. On rejection it appends evidence and writes no digest file. Prior envelopes and transcripts remain append-only. CONTRACT-ONLY (GAUNTLET.md:12,46-47).

Envelope validity limits how long approval stands before the gate re-fires. A run cache recording an earlier verdict remains derived and non-authoritative. Neither a cached result nor a file's presence substitutes for the required digest and signature checks. CONTRACT-ONLY (GAUNTLET.md:39,44-46,51).

The council envelope is not the terminal release-disposition envelope. Parent claim 34 concerns an internal sign-off gate, while parent claim 35 concerns separately governed release authority. The council's all-seat rule is not a role threshold counted from interchangeable signers. CONTRACT-ONLY (GAUNTLET.md:11,43-55).

### 8.7 Bounded dispute and feedback capture

A rejection opens a dated thread per contested gate. Each opening argument carries a claim, exact bytes and clause, supporting evidence, severity, and proposed remedy. The producer may choose another remedy but cannot ignore the gate's closed state. CONTRACT-ONLY (GAUNTLET.md:63).

The argument lobe sends a dated, signed argument record to the producing instrument's feedback capture path. In one implementation the record kind is `approval_record`; its exact bytes and approver identity accompany the feedback entry. CONTRACT-ONLY (GAUNTLET.md:64; ENGRAM.md:116).

The record-keeper's feedback capture step 1 expressly includes an out-of-band approver argument record without a classification filter. Its rebuttal path retains pending standing while recording reasoning, or revises the artifact through normal sign-off before recording application. CONTRACT-ONLY (GAUNTLET.md:64-65; ENGRAM.md:116,123).

The producer responds with evidence-based rebuttal or a revision of its own bytes. Every revision becomes new frozen bytes for re-attack. A defeated argument receives a dated withdrawal, never silent deletion, and a surviving argument keeps the gate shut. CONTRACT-ONLY (GAUNTLET.md:65-66).

The consuming project's capability bytes bound the round count. A thread closes converged only when no argument stands and every council seat approves final bytes; the closing approval binds the full thread digest through the transcript-digest field. CONTRACT-ONLY (GAUNTLET.md:67).

A thread closes escalated when the bound expires with surviving arguments. Human sign-off receives the full thread as briefing, and surviving arguments remain pending feedback. The closing improvement inventory records changes, withdrawals, and weaknesses requiring human specification edits. CONTRACT-ONLY (GAUNTLET.md:67-68).

### 8.8 Revocation, calibration, and surgical demotion

An approval is a prediction subject to downstream contradiction, not irrevocable authority. A contradicting signed pilot, auditor finding, or human reversal causes the memory lobe to append a false-approval record naming the approval and contradiction evidence digest. CONTRACT-ONLY (GAUNTLET.md:74).

The record names every seat whose approving ballot joins the unanimous verdict and the contradiction class. Charging every such seat preserves individual accountability rather than assigning error only to the council aggregate or to a selected member. CONTRACT-ONLY (GAUNTLET.md:74).

The separate memory instrument ingests this calibration mirror and owns demotion. Demotion moves authority to human-only watch standing, and the affected gates return to human sign-off without a change to their specification bytes. CONTRACT-ONLY (GAUNTLET.md:9,75).

Demotion may target one seat whose ballots deteriorate. Only the human rotates that seat identity in the trust root. A roster with an ineligible seat must still satisfy the minimum distinct-lineage rule before autonomous discharge can resume. CONTRACT-ONLY (GAUNTLET.md:10,14,75).

Restoration requires the human-signed authorization that bootstraps autonomy. The gatekeeper cannot decide its own calibration standing; its mirror remains observation rather than self-issued permission. No numerical false-approval threshold is invented here. CONTRACT-ONLY (GAUNTLET.md:75-76,80).

### 8.9 Three-lobe pre-partition with single-writer ownership

The memory lobe owns gate, calibration, and progress records and is the sole standing bridge between argument and judgment. In one implementation its surfaces are `.trial/gates.yaml`, `.trial/calibration.yaml`, and `.trial/progress.yaml`. CONTRACT-ONLY (GAUNTLET.md:25,28,34,38-39).

The argument lobe authors attacks and disputes and never signs verdicts. In one implementation it owns `.trial/attacks/` and `.trial/disputes/`. It cannot change the producer's artifact while attempting to improve it through arguments. CONTRACT-ONLY (GAUNTLET.md:7,26,35,37,64).

The judgment lobe recomputes digests, verifies signatures, seats the council, and signs its verdict. In one implementation it owns `.trial/approvals/` and the compatibility digest files, and alone holds the authorized approver key. CONTRACT-ONLY (GAUNTLET.md:27,36,82).

Every gatekeeper artifact has one writing lobe. Argument and judgment exchange no standing directly; the memory lobe mediates their records. Council-seat ballots are internal to judgment, not permission for the argument lobe to sign or inspect sibling votes. CONTRACT-ONLY (GAUNTLET.md:28,54,57).

The lobes may begin as phases in one run. A later separation lifts each lobe's work order and moves its owned records to a separate harness while preserving ownership and meaning. Re-provisioning the judgment identity does not turn either other lobe into an approver. CONTRACT-ONLY (GAUNTLET.md:29,87).

This pre-partition is a specification for later separation, not evidence of separate operating services. The claimed fallback concerns disjoint ownership, and does not require any named successor project or a future deletion of a work-order file. CONTRACT-ONLY (GAUNTLET.md:25-29,87-88).

### 8.10 Conductor outside isolated instruments

The conductor performs no record-keeper, author, or auditor phase inline. Each movement launches one isolated lane whose prompt names only the governing specification and verified project root. It passes no summary, goal, hint, finding, or prior-lane result. CONTRACT-ONLY (MAESTRO.md:1,5-6,29,45).

A fresh movement has fresh context; a gate-halted or failed movement resumes its own session with context preserved. These are distinct cases. A runtime without isolated movement contexts must fall back to separate human invocations rather than merge the three work orders. CONTRACT-ONLY (MAESTRO.md:6,11,41,45).

The conductor owns one disjoint harness and its root cycle report. In one implementation these are `.podium/` and `SCORE.md`, with an installed thin front door that the conductor does not hand-author. It never writes instrument harness bytes or performs their pipeline operations. CONTRACT-ONLY (MAESTRO.md:8,12,18-24).

Its sequencing read set comprises the three root reports, its own harness, and resident-bundle directory counts. It never reads a computed projection, an instrument's raw ledger, a proof store, or bundle contents. The prohibition on raw ledgers concerns instrument state, not the conductor's own cycle ledger. CONTRACT-ONLY (MAESTRO.md:7,20-21).

In one implementation the three reports are `DIRECTIVE.md`, `EDICT.md`, and `VERDICT.md`. The conductor carries only disposition, gate name, stop reason, digest, and residency count across movements, never private evidence or a grading criterion. CONTRACT-ONLY (MAESTRO.md:7,30).

The append-only cycle ledger has a dated entry per movement identifying the lane outcome, report disposition headline, report digest, pending gates, and named conditions. Post-cycle counts and a derived progress cache support resumption, but the cache does not authorize work. CONTRACT-ONLY (MAESTRO.md:20-21,30).

The fixed movement order is record-keeper, author, then auditor. The next record-keeper movement reconciles the prior cycle using its own permitted channels. The conductor supplies sequencing memory rather than becoming a second owner of instrument phase state. CONTRACT-ONLY (MAESTRO.md:11,28-29).

The specifications fix the hazard relation. An open record-keeper gate holds both peers because both consume its direction. An open author gate never holds the auditor's launch because those instruments share no direct channel. An open auditor gate holds no later movement inside that cycle. CONTRACT-ONLY (MAESTRO.md:31).

Fixed order governs movement launch order, not an invented requirement that every earlier movement finish before a non-hazarded movement starts. Dependency-admitted work may proceed outside a pending gate's hazard. This does not permit the conductor to inspect private state to derive a different relation per run. CONTRACT-ONLY (MAESTRO.md:28,31-32).

The cycle boundary is a synchronization barrier. A new cycle opens only after every closing-cycle gate has discharge and every lane reaches completion. A pending gate when the loop would otherwise continue produces a pending-gates stop even below quota. CONTRACT-ONLY (MAESTRO.md:33,39-41).

Two consecutive cycles with identical report fingerprints, residency counts, and pending-gate sets cause a steady-state stop regardless of report prose. The conjunction matters: report equality alone cannot hide changing occupancy or a changing gate set. CONTRACT-ONLY (MAESTRO.md:34).

Quota, terminal disposition, and blocking conditions supply other lawful stops. A failed launch, crash, or missing root report becomes a named condition, never a silent skip. Counts concern resident directories and do not require access to bundle contents. CONTRACT-ONLY (MAESTRO.md:7,10,13,33,39).

The consolidated gate sheet copies verbatim the file to inspect, digest command, and target path from each lane's halt output. It presents each instruction when the gate appears and at the final stop. The sheet discharges nothing and cannot replace the lane's approval check. CONTRACT-ONLY (MAESTRO.md:8,30-31,39-41).

The conductor never writes an approval digest or signature, invokes an out-of-band gatekeeper, or raises an operational disposition. An authorized gatekeeper runs separately under its own work order. Conductor scheduling and council authority therefore remain distinct mechanisms even when one operator controls both services. CONTRACT-ONLY (MAESTRO.md:8).

Source reconciliation limits: the current conductor text also discusses dependency concurrency, queue surfaces, and reconciliation operations. This draft does not infer a new conductor right to invoke pipeline verbs, perform git writes, or read private ledgers from those passages. The explicit non-performance and restricted-read rules govern the claimed conductor. CONTRACT-ONLY (MAESTRO.md:7-8,12,31-35).

### 8.11 Named prior art and novelty residue: US12001822B2 and related references

For the digest gate and human boundary, Capital One US12001822B2 and IETF draft-schrock-ep-authorization-receipts (revision 01 as retrieved, revision 13 current; agent-verified 2026-09-21) supply multi-signature and authorization-receipt context. The novelty residue is the conjunction of a recomputed artifact binding, a compatibility-only digest interface, and a permanently-human class that no autonomous envelope discharges. CONTRACT-ONLY (GAUNTLET.md:11,43-51).

For break attempts, arXiv 2609.15803 and Avizienis N-version programming supply reviewer and diversity context. The novelty residue is a recorded attack over the same frozen bytes, a concluded no-break outcome rather than absent inspection, and a transcript digest required inside the authorizing envelope. CONTRACT-ONLY (GAUNTLET.md:6-7,44,52-54).

For the roster, IBM/Kyndryl US11328214B2, PoLL arXiv 2404.18796, and arXiv 2609.15803 address dissimilar platforms, model panels, and unanimity. The novelty residue is their specific conjunction with pairwise lineage exclusions extending to the producer, blind ballots, unanimity, and human fallback on collision or an unseatable roster. CONTRACT-ONLY (GAUNTLET.md:10,14,44,54,57).

For the envelope, tZero US11392940B2 and IETF draft-schrock-ep-authorization-receipts (revision 01 as retrieved, revision 13 current; agent-verified 2026-09-21) supply M-of-N and self-approval context. The novelty residue is not signature count: it is the single typed binding of artifact, producer-distinct authorized approver, producer lineage, qualifying full roster, every verdict, and failed-attack transcript, subject to the human exclusions. CONTRACT-ONLY (GAUNTLET.md:5,11,43-47).

For disputes, PoLL arXiv 2404.18796 provides panel-review context; the informal Qorum Method repository and the reported quorum-review skill were checked on 2026-09-21 and withdrawn as panel teachings. The novelty residue is a bounded append-only argument and rebuttal path whose final approval binds the full thread digest, whose producer alone changes bytes, and whose escalation retains pending feedback. CONTRACT-ONLY (GAUNTLET.md:63-68).

For calibration, Avizienis N-version programming and DO-178C supply assurance context. The novelty residue is the false-approval record charging every unanimous seat, an external memory instrument's demotion decision, surgical seat demotion, and human-only restoration rather than a panel adjusting its own authority. CONTRACT-ONLY (GAUNTLET.md:74-76,80).

For pre-partition, IBM/Kyndryl US11328214B2 and Avizienis N-version programming supply multi-agent and diversity context. The novelty residue is disjoint single-writer memory, argument, and judgment ownership from the outset, with memory-mediated standing and judgment-only signing custody so a later split moves directories rather than meanings. CONTRACT-ONLY (GAUNTLET.md:25-29,82,87).

For conduct, auditor-independence statute, Brewer and Nash's Chinese Wall, and Apache Airflow supply separation and workflow context. The novelty residue is a conductor read set confined to derived root reports, its own harness, and residency counts, combined with a hold relation fixed in specification text, content-free lane prompts, and a synchronization barrier that prevents re-projection beneath a halted lane. CONTRACT-ONLY (MAESTRO.md:5-8,28-34).

These are proposed combination distinctions, not assertions that any single primitive is new. The strongest obviousness risk combines authorization receipts, artifact signatures, diverse panel review, and unanimity. Claim construction must retain the attack binding, fallback, and affirmative prevention of permanently-human discharge rather than relying on a label such as council.

### 8.12 Evidence map and prevention register

The following ENFORCED and PROSPECTIVE map separates two existing narrow checks from the contract-only family. The named files exist on disk. A first-landed date identifies the module's introduction, not the date on which every present check enters that module.

| Mechanism | Claims | Evidence class | Evidence and limit |
|---|---|---|---|
| Council gate and compatibility write | 1-4,19-20 | CONTRACT-ONLY | GAUNTLET.md:43-57; no council module implements discharge |
| Failed break-attempt binding | 1,19-20 | CONTRACT-ONLY | GAUNTLET.md:6,44,52-54 |
| Authorized identity and blind lineage roster | 1,3-4,19-20 | CONTRACT-ONLY | GAUNTLET.md:5,10,14,44-45,54,57 |
| Bounded disputes and captured feedback | 5-6 | CONTRACT-ONLY | GAUNTLET.md:63-68; ENGRAM.md:116,123 |
| False approvals and per-seat demotion | 7-8 | CONTRACT-ONLY | GAUNTLET.md:74-76 |
| Single-writer lobe partition | 9 | CONTRACT-ONLY | GAUNTLET.md:25-29,82,87 |
| Conductor ordering, reads, holds, barrier, stops, sheet | 10-17 | CONTRACT-ONLY | MAESTRO.md:5-13,20-21,28-45 |
| Tier authorization | 18 | CONTRACT-ONLY | GAUNTLET.md:55,80-82 |
| Permanently-human class in full | 1,19-20 | CONTRACT-ONLY | GAUNTLET.md:11; no claim of general automation detecting every human act |
| Permanently-human carve-out on release path: acceptance cannot waive a cap | 1,19-20, boundary only | ENFORCED | tools/release.py, first landed 2026-09-16; tests/test_release.py; waiver refusal, not council execution |
| Recompute-first digest check on qualified artifact path | 1-2,19-20, check only | ENFORCED | tools/gate.py, first landed 2026-09-16; tests/test_gate.py; current bundle digest comparison, not council verification |
| Formal lineage equivalence validation and service realization | 1,4,19-20 | PROSPECTIVE | Parent drafting definition; no current resolver or isolated council service asserted |

The release-path exception has narrow support: the release verifier categorically refuses waivers, including signed-looking waivers, and acceptance cannot clear disposition or control failures. It does not establish automation enforcing patent filing or calibration admission outside that path.

The digest exception has narrow support: the gate compares the recomputed bundle-set digest with the qualified record and refuses changed bytes. The corresponding tests exercise digest agreement and refusal after sample bytes move. That is not proof that the contract-only approval envelope has an executable consumer.

| Prevention operation | Claims | Artifact or transition denied | Contract support |
|---|---|---|---|
| Recomputes and compares bytes | 1-2,19-20 | Discharge for a different artifact digest | GAUNTLET.md:46,51 |
| Verifies and resolves authority | 1,19-20 | Self-issued or unauthorized approving envelope | GAUNTLET.md:5,44-45 |
| Prevents ballot disclosure before casting | 1,19-20 | Cross-seat ballot influence path | GAUNTLET.md:54,57 |
| Refuses roster collapse and dissent | 1,3-4,19-20 | Approval with shared lineage, fewer seats, or dissent | GAUNTLET.md:10,14,54,57 |
| Requires transcript binding | 1,19-20 | Approval with no concluded attack evidence | GAUNTLET.md:6,44,53-54 |
| Prevents class discharge | 1,19-20 | Automated authorization of a permanently-human act | GAUNTLET.md:11,55 |
| Denies sibling write authority | 9 | Attack author writing an approval record | GAUNTLET.md:25-28 |
| Restricts reads and prompt contents | 10-12 | Conductor transmission of private instrument state | MAESTRO.md:5-7,29-30 |
| Prevents hazarded launches and cycle advance | 13-14 | Dependent movement or new cycle while held | MAESTRO.md:31-33 |
| Stops repeated state; discharges nothing | 15-17 | Unproductive repetition or sheet-based approval | MAESTRO.md:34,39-41 |

For Alice Step 2A Prong Two, claims 1, 19, and 20 integrate model review into the prevention operations above. The proposed improvement is a byte-bound authorization transition whose absent prerequisites prevent the machine from opening the gate, not advice that humans should obtain diverse opinions. CONTRACT-ONLY (GAUNTLET.md:5-14,43-57).

For Step 2B, the asserted inventive concept is the ordered conjunction rather than cryptography or a model in isolation. Claims 10-17 add a computer information-access restriction and scheduling refusal, not a manager's discretion about which colleague waits. These are eligibility arguments for proposed instruction behavior, not claims of current enforcement. CONTRACT-ONLY (MAESTRO.md:5-8,28-41).

For EPO Article 52 and Guidelines G-II 3.3 and 3.3.1, hashing serves identity comparison, signatures serve authorization, and lineage and ballot tests control whether a particular operation can execute. The specific technical effect is cryptographic gate discharge as a machine state transition, not delegation of human judgment. The conductor extension restricts data accessibility during scheduling. CONTRACT-ONLY (GAUNTLET.md:43-57; MAESTRO.md:7,29-34).

For India s.3(k), independent system claim 1 addresses unauthorized progression on altered or insufficiently reviewed artifact bytes. Its technical solution combines digest recomputation, role verification, isolated ballots, transcript binding, and a fail-closed gate. The measurable technical benefit would be refusal of mismatched or incomplete authorizations rather than a subjective increase in quality. Under Ferid Allani and Microsoft v. Assistant Controller, this argument requires no novel hardware and asserts no measured result.

For India s.3(k), independent method claim 19 addresses the same technical problem through an ordered machine process. Its technical solution freezes the inspection subject, restricts ballot visibility, validates the signed bindings, and refuses discharge absent the conjunction. A measurable technical benefit would be the absence of enabled operations in negative byte-mismatch, missing-transcript, and lineage-collision cases. This is the Ferid Allani and Microsoft v. Assistant Controller technical-effect posture, without novel hardware or an executed test claim.

For India s.3(k), independent storage-medium claim 20 addresses deployment of instructions that could otherwise admit self-approval or stale approval. The stored instructions provide the same technical solution and control the same state transition. Their measurable technical benefit would be machine refusal of invalid authorization paths when executed, not the presence of software on a medium. Ferid Allani and Microsoft v. Assistant Controller support framing technical contribution without requiring novel hardware.

### 8.13 Scope, single-actor operation, and the permanently human acts

File names, predicate strings, role tokens, state labels, and directory names are illustrative implementation vocabulary rather than claim limitations. Hash and envelope encodings may vary while retaining the disclosed bindings. The claims expressly retain at least three seats; an illustrative-vocabulary statement does not erase that claimed minimum.

In a prospective service embodiment, one platform operator performs or causes each claimed computation, including roster qualification, isolated ballot execution, envelope validation, and gate control. An external trust root denotes an authority boundary that producer principals cannot rewrite, not a requirement for a separate legal entity. The conductor can belong to that operator while retaining its limited reads and writes. PROSPECTIVE.

The contract describes lobes and isolated lanes; it does not supply operating-system confinement code or demonstrate a deployed access-control boundary. Any implementation must supply the claimed prevention operations, not merely repeat the words of a work order. PROSPECTIVE.

The drafting party reconciles this disclosure and never files it. Filing remains a human act that no council, conductor, or instrument discharges. Publication beyond the repository, operational acceptance against a capped disposition, and admission into the human-graded calibration library likewise remain human. CONTRACT-ONLY (GAUNTLET.md:11; ENGRAM.md:294).

No statement asserts any filing, deployment, measured pass rate, council session, vote, or approval event. All operational embodiments use present or conditional tense. The proposed drawings, examples, and eligibility benefits describe requirements or expected behavior rather than experimental results.

## 9. CLAIMS

What is claimed is:

**1. A system for controlling out-of-band discharge of a digest-bound sign-off gate for an artifact produced using a machine-learning model, comprising:** one or more processors; one or more non-transitory memories storing instructions; and a trust-policy store identifying an external trust root, wherein execution of the instructions causes the processors to maintain the gate shut, recompute a canonical digest from frozen artifact bytes, record applicable break-attempt lanes over those bytes to a concluded transcript, qualify a council roster of at least three seats whose model lineages are pairwise distinct and each distinct from a producer model lineage, cause each seat independently to cast a verdict over the frozen bytes and transcript while preventing access to other seats' ballots before casting its own ballot, and permit discharge only upon verification of a signed approval envelope of a declared predicate type binding the canonical digest, an approver identity resolving to an authorized approver role in the external trust root, a producer identity distinct from the approver identity, the producer model lineage, the roster, every cast verdict, and a digest of the concluded transcript establishing that the applicable break-attempt lanes fail to break the artifact, with every cast verdict approving and the recomputed digest equal to the bound digest, wherein the processors keep the gate shut and retain human sign-off as a fallback when the required authorization, roster, ballots, or transcript do not qualify, and prevent discharge by any such envelope for an enumerated permanently-human class comprising publication of a task bundle or manuscript beyond a repository, patent filing, recording operational acceptance against a capped disposition, and admission of a staged candidate into a human-graded calibration library.

**2.** The system of claim 1, wherein the processors, only for an approving envelope, write the bound digest into a legacy digest file byte-identically to a human approval interface, retain the envelope as authority distinct from that file, and recompute the artifact digest before a consuming operation, refusing the operation upon inequality.

**3.** The system of claim 1, wherein any dissenting seat causes a rejecting verdict irrespective of the quantity of approving seats, and the rejecting verdict causes no legacy approval digest write.

**4.** The system of claim 1, wherein a lineage collision with the producer or another seat, or inability to seat the qualifying council, causes fallback to human sign-off without reducing the required seat count.

**5.** The system of claim 1, wherein rejection opens an append-only dispute thread with arguments, rebuttals, and producer revisions under a bound round count, and the thread closes converged only upon withdrawal or resolution of every standing argument and unanimous approval of final bytes, or closes escalated upon exhaustion with surviving arguments and human fallback.

**6.** The system of claim 5, wherein a signed approver argument record enters the producing instrument's feedback capture path with exact argument bytes and approver identity, each revision undergoes another attack as new frozen bytes, and a converged approval binds a digest of the full thread as its transcript digest.

**7.** The system of claim 1, wherein contradiction of an approval by signed pilot evidence, an auditor finding, or a human reversal causes an append-only false-approval record that names a contradiction evidence digest and charges every council seat whose approving ballot joins that approval.

**8.** The system of claim 7, wherein a memory instrument separate from the council owns demotion of approval authority to a watch standing requiring human sign-off, supports demotion of an individual seat, and permits restoration only under human-signed authorization and rotation of that seat's trust-root identity only by a human.

**9.** The system of claim 1, wherein gatekeeping is pre-partitioned into memory, argument, and judgment lobes with disjoint single-writer artifact ownership, the memory lobe mediates standing between the other lobes, the argument lobe owns attacks and disputes but cannot sign verdicts, and the judgment lobe alone owns approval records and the signing credential.

**10.** The system of claim 1, further comprising a conductor outside record-keeper, author, and auditor instruments, wherein the conductor performs none of their work, owns a disjoint harness with an append-only cycle ledger, and launches one isolated lane per movement in fixed order of record-keeper, author, then auditor.

**11.** The system of claim 10, wherein the conductor's sequencing read set consists of the three instruments' root reports, its own harness, and resident-bundle directory counts, and excludes instrument projections, raw instrument ledgers, proof stores, instrument harness internals, and bundle contents.

**12.** The system of claim 11, wherein each movement's lane prompt names only its governing specification and a verified project root, and the conductor appends movement outcomes, report digests, pending gates, and named conditions to the cycle ledger without transmitting private findings or grading criteria between lanes.

**13.** The system of claim 10, wherein governing specifications fix a hazard relation under which an open record-keeper gate prevents launch of both peer movements and an open author gate does not prevent launch of the auditor movement, without the conductor deriving a different hazard relation per run.

**14.** The system of claim 13, wherein a cycle boundary forms a synchronization barrier preventing a new cycle until every gate of the closing cycle has discharge and every lane finishes, and an open gate when continuation would otherwise occur causes a pending-gates stop.

**15.** The system of claim 14, wherein two consecutive cycles with identical root-report fingerprints, identical resident-bundle counts, and an identical pending-gate set cause a steady-state stop regardless of disposition prose in the reports.

**16.** The system of claim 13, wherein the conductor presents a consolidated gate sheet containing verbatim approval instructions from a lane halted at an open gate, the instructions naming an artifact to inspect, a digest computation, and an approval target, while writing no approval digest, fabricating no signature, invoking no out-of-band approver, and discharging no gate.

**17.** The system of claim 14, wherein, for a lane halted at the open gate, discharge of that gate resumes the same halted lane through its own preflight, movements within the open gate's hazard remain unlaunched, and movements outside that hazard may run to their own lawful stops.

**18.** The system of claim 1, wherein a human-signed project authorization separately grants lower-tier scope or design approval and higher-tier release sign-off, and the higher tier requires a bound count of consecutive externally piloted, audit-clean cycles without enabling discharge of the permanently-human class.

**19. A computer-implemented method for controlling out-of-band discharge of a digest-bound sign-off gate for an artifact produced using a machine-learning model, comprising, by one or more processors:** maintaining the gate shut; recomputing a canonical digest from frozen artifact bytes; recording applicable break-attempt lanes over those bytes to a concluded transcript; qualifying a council roster of at least three seats whose model lineages are pairwise distinct and each distinct from a producer model lineage; causing each seat independently to cast a verdict over the frozen bytes and transcript while preventing access to other seats' ballots before casting its own ballot; verifying a signed approval envelope of a declared predicate type against an external trust root, the envelope binding the canonical digest, an approver identity resolving to an authorized approver role, a producer identity distinct from the approver identity, the producer model lineage, the roster, every cast verdict, and a digest of the concluded transcript establishing that the applicable break-attempt lanes fail to break the artifact; permitting discharge only when that verification succeeds, every cast verdict approves, and the recomputed digest equals the bound digest; keeping the gate shut and retaining human sign-off as a fallback when the required authorization, roster, ballots, or transcript do not qualify; and preventing discharge by any such envelope for an enumerated permanently-human class comprising publication of a task bundle or manuscript beyond a repository, patent filing, recording operational acceptance against a capped disposition, and admission of a staged candidate into a human-graded calibration library.

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by one or more processors, cause the processors to control out-of-band discharge of a digest-bound sign-off gate for an artifact produced using a machine-learning model by:** maintaining the gate shut; recomputing a canonical digest from frozen artifact bytes; recording applicable break-attempt lanes over those bytes to a concluded transcript; qualifying a council roster of at least three seats whose model lineages are pairwise distinct and each distinct from a producer model lineage; causing each seat independently to cast a verdict over the frozen bytes and transcript while preventing access to other seats' ballots before casting its own ballot; verifying a signed approval envelope of a declared predicate type against an external trust root, the envelope binding the canonical digest, an approver identity resolving to an authorized approver role, a producer identity distinct from the approver identity, the producer model lineage, the roster, every cast verdict, and a digest of the concluded transcript establishing that the applicable break-attempt lanes fail to break the artifact; permitting discharge only when that verification succeeds, every cast verdict approves, and the recomputed digest equals the bound digest; keeping the gate shut and retaining human sign-off as a fallback when the required authorization, roster, ballots, or transcript do not qualify; and preventing discharge by any such envelope for an enumerated permanently-human class comprising publication of a task bundle or manuscript beyond a repository, patent filing, recording operational acceptance against a capped disposition, and admission of a staged candidate into a human-graded calibration library.

## 10. ABSTRACT OF THE DISCLOSURE

Systems and methods control out-of-band discharge of digest-bound sign-off gates. A processor recomputes a frozen artifact digest and records break-attempt lanes. At least three council seats have pairwise-distinct model lineages, each distinct from the producer lineage. Seats cast independent blind ballots. A signed envelope binds artifact identity, an externally authorized approver distinct from the producer, the roster, ballots, and a failed-attack transcript digest. Discharge requires unanimous approval and verified bindings; deficient evidence or roster qualification leaves human sign-off available. An enumerated permanently-human class remains outside automated discharge. Dependent embodiments retain a legacy digest interface, bounded disputes, per-seat calibration, and single-writer gatekeeping lobes. A separate conductor sequences isolated record-keeper, author, and auditor movements using restricted derived surfaces and specification-fixed hazard holds. A synchronization barrier and repeated-state stop bound cycling. A consolidated sheet presents approval instructions without discharging gates.
