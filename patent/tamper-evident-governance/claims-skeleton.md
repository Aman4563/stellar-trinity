Filing: US Non-Provisional utility application (35 U.S.C. § 111(a)). Inventor: Sarvex Jatasra. Assignee: Ethara.AI. The strategy uses one apex system claim, mirrored method and storage-medium claims, and a dependent ladder totaling twenty claims. No claim is deleted once numbered; a revision preserves its number or marks it superseded with its successor identified. This is a draft, not an assertion of filing.

## Title

Primary: Tamper-Evident Capture, Attribution, and Anti-Sabotage Control of Agent-Operated Repositories.

Alternative: Fail-Closed Repository Execution Through Verbatim Capture, Current Governance, and Preserved Refusal Evidence.

## Abstract (proposed)

Systems, methods, and storage media control agent-operated repositories through preconditions on phase execution. Every received human turn enters a verbatim ledger without classification gating and receives a digest-linked chain entry. An end-to-end chain walk and equality of an unmodified governing checkout to a fetched upstream tip precede phase work. Unresolvable currency fails closed without an approval waiver. A rule-based classifier treats history changes that erase a refusal as further instances of the refused class and requires disjointly authorized append-only remediation preserving flagged commits. Dependent mechanisms separate a secretless candidate probe from an independently governed observer with persistent incidents and no reset. Signed run-operation chains authenticate authoritative records. A caller-supplied trusted context governs lawful-successor decisions, and subject-closure digests preserve qualification across unrelated commits. Instruments and hooks write without staging, while human commit gates and deterministic report regeneration preserve reviewable history.

## Apex pillars in independent claims

1. Claims 1, 19, and 20 require unconditional verbatim capture and a digest-chain walk before phase work, not selective logging or a post-work warning.

2. The same claims require current governing bytes equal to the fetched upstream tip. Behind, diverged, locally modified, and unresolvable states expressly block, without waiver by cache, approval, or signature.

3. The same claims require rule-based refusal of governance co-editing and reflexive classification of erasure into the refused class. Clearance preserves the original evidence and requires append-only remediation authorized by a disjoint principal group.

The apex is an ordered repository-security mechanism. Its complete runtime interlock and historical-remediation consumer are prospective despite existing local checks. Claim scope is not an implementation-conformance assertion.

Deliberately excluded from apex are the attribution ladder, precise schemas, checkpoint publication, per-run repeat detection, software-key clearance format, independently governed observer, operation-chain fields, trusted-context transition details, subject closure, and no-stage hook implementation. Claims 2 through 18 provide these fallbacks without making implementation vocabulary an apex limitation.

Named surfaces must be described only generically in claims. In one implementation, illustrative vocabulary includes ENGRAM, FORGE, CRUCIBLE, feedback.yaml, feedback.chain.jsonl, checkpoints.yaml, allowed_signers, roots.yaml, trinity.run-operation/v1, sentinel_clearer, run_operator, SAB_REPEATED_ATTEMPT, SAB_SENTINEL_CLEARANCE_UNSIGNED, OPERATION_PRINCIPAL_MISMATCH, OPERATION_CHAIN_BROKEN, OPERATION_ENVELOPE_INVALID, OPERATION_UNAUTHORIZED, main, trinity-generated, DSSE, SHA-256, GitHub, SSH, and SQLite. Paths, predicate strings, role names, refusal codes, tool names, and configured numerals explain embodiments; claims use structural relationships and generic typed signatures instead.

## Claims

**1. A system for tamper-evident control of an agent-operated repository, comprising:** one or more processors; one or more non-transitory memories storing instructions that cause the processors to append a verbatim record of every received human-originated turn without classification gating and a corresponding digest-linked chain entry; walk the chain end to end as a precondition of phase work and prevent the phase work upon a failed walk; admit a governing-specification checkout only when unmodified and equal to a fetched upstream branch tip, treating a behind, diverged, locally modified, or unresolvable checkout as stale and preventing the phase work irrespective of a cached result, prior approval, or signed approval envelope; and apply a rule-based repository classifier that refuses a governance edit committed with its governed subject, classifies a history rewrite, force-push, replacement, or padding that removes a prior refusal from a scan window as a further instance of the refused class, and permits clearance of that refusal only through an append-only signed remediation record authorized by a principal group disjoint from authority introduced by flagged commits while preserving the flagged commits and refusal evidence.

*Drafting note (1):* This is the complete conjunctive embodiment. Application sections 8.3 through 8.5 supply structure, ordering, and the distinction between contractual duties and implemented checks. The prospective remediation reader must remain explicit; a valid sentinel-clearance verifier does not silently fill that different gap.

**2.** The system of claim 1, wherein attribution first selects an authenticated repository-hosting command-line login, then a runtime-supplied hosting-platform actor identity, and otherwise records an unattributed value with a named coverage gap without guessing an identity or suppressing capture.

*Drafting note (2):* This fallback preserves the fixed ladder and the unattributed record. It does not equate a platform username with a cryptographically enrolled human. Application section 8.3 identifies the present authenticity gap.

**3.** The system of claim 1, wherein the processors fold a chain-head sequence position and digest into a signed checkpoint, publish both in a root report, and reject a chain head that does not match the checkpoint.

*Drafting note (3):* Checkpoint publication makes the head visible beyond the chain file. It does not make a second candidate-controlled file an independent transparency service. Signed head verification has implementation support; publication cadence remains a contract obligation.

**4.** The system of claim 1, wherein the processors determine that the checkout is behind the fetched upstream branch tip and hard-block phase work despite a cached currency result.

*Drafting note (4):* This expressly retains the behind condition and cache refusal for prosecution clarity. It emphasizes an apex condition rather than adding a distinct independent inventive concept.

**5.** The system of claim 1, wherein the processors determine that the checkout diverges from the fetched upstream branch tip and hard-block phase work despite prior approval.

*Drafting note (5):* Divergence is not a mere age comparison. Preserve the revision-graph comparison and prior-approval refusal if narrowing the currency family.

**6.** The system of claim 1, wherein the processors detect local modifications in the checkout and hard-block phase work despite a signed approval envelope.

*Drafting note (6):* A valid signature does not authorize modified governing bytes. The condition concerns the governing checkout, not every report byte the gate itself emits.

**7.** The system of claim 1, wherein inability to resolve the checkout, its remote, or the fetched upstream branch tip constitutes staleness and hard-blocks phase work without an offline waiver.

*Drafting note (7):* Keep unresolvable in the claim, not only in the description. The novelty argument is weakest if an unavailable network silently selects a cached success.

**8.** The system of claim 1, wherein the processors append refusal attempts to hash-chained sentinel streams assigned per run, evaluate qualifying attempts across the streams within a rolling window, and cap disposition at a blocking value upon a repeat threshold crossing attributed to an alerted actor.

*Drafting note (8):* Per-run streams prevent two clones from extending one shared chain. Repeat evaluation reads across streams, so starting a new run does not reset the actor's history. Threshold and window remain governed parameters rather than fixed numerals.

**9.** The system of claim 8, wherein clearance of a repeat alert requires a typed signed envelope using a software-held signing key under a distinct clearance role, verification against an allowed-signer policy and versioned trust root, and exclusion of the alerted actor's verified principals from eligible clearers, and wherein a typed unsigned clearance clears nothing.

*Drafting note (9):* The concrete embodiment uses DSSE and a software SSH key under sentinel_clearer. Generic claim language preserves the authenticated payload and distinct-role relationship without importing those strings. A claimed actor without verified principals creates an explicit exclusion gap, and a repeat-alert clearance never substitutes for historical remediation.

**10.** The system of claim 1, further comprising a candidate workflow having no secrets, dispatch authority, delivery authority, or release authority and running only an immutable reviewed probe over candidate data, and a separately governed observer that accepts requests only through an allowlisted application bridge, authenticates sender and target identities through a hosting-platform interface, reruns the probe read-only, and retains closed-schema incidents, equivocations, and repeat alerts in external state with bounded inspection and without candidate reset authority or a delivery transport.

*Drafting note (10):* The candidate's lack of credentials is an architectural incapacity, not an instruction to behave. The observer template and incident parser support parts of the mechanism; bridge, runner, allowlists, credentials, and durable-volume deployment remain prospective. No-reset means no reset interface or candidate authority, not invulnerability to the storage administrator.

**11.** The system of claim 1, wherein each authoritative run write requires a typed signed operation statement binding project identity, run identity, operation verb, a cryptographic digest of the authorized record, sequence position, predecessor digest, and principal, verified against an allowed-signer policy and a versioned trust root under an operation-authorizing role.

*Drafting note (11):* The embodiment maps these fields to trinity.run-operation/v1 and run_operator. The signature authenticates the operation's record digest rather than only a namespace marker. Universal admission interposition remains prospective; the existing module verifies statements when called.

**12.** The system of claim 11, wherein the processors reject a signature whose verified principal does not match the statement's claimed principal, reject an operation whose sequence, predecessor link, or namespace membership breaks the run chain, and reject an invalid envelope or a principal lacking role authorization.

*Drafting note (12):* Preserve the two distinct principal-mismatch and broken-chain refusals. Invalid carrier and unauthorized role are separate failures. A retained accepted head is needed to detect complete suffix removal; chain continuity alone cannot prove that a removed suffix once existed.

**13.** The system of claim 1, wherein the processors decide lawful succession of a candidate revision against a caller-supplied trusted context binding an accepted base revision, a trust-policy digest, an enrolled-principal set, and an authenticated operator rather than against the candidate's own baseline assertion.

*Drafting note (13):* The trusted context is an authority input, not a candidate declaration with a different filename. Keep the decision distinct from a service that serializes accepted-reference updates. The repository supplies the decision but no exclusive admission writer.

**14.** The system of claim 13, wherein the succession decision refuses a changed candidate without the accepted base as sole parent, a merge that buries the base as another parent, a rewritten or truncated accepted queue stream, mutation or deletion of an accepted claim, verdict, sentinel entry, or epoch, a namespace write outside its accepted principal binding, an unenrolled operator, a double claim, a verdict without an accepted owner's claim, a non-sequential epoch, a backwards current pointer, a seal instant preceding an accepted watermark, or candidate-carried trust-policy bytes differing from the pinned digest.

*Drafting note (14):* This preserves the closed refusal ladder and accepted-order arbitration. "Sentinel entry" denotes existing evidence, so appending a new entry is not mutation. A candidate equal to the base remains a no-op; a changed merge cannot use ancestry containment as sole-parent equality.

**15.** The system of claim 1, wherein qualification binds a digest computed over a run's namespace and enumerated inputs rather than a repository tip revision, such that a commit changing only bytes outside that closure leaves the qualification binding unchanged and a change to a bound input invalidates the binding.

*Drafting note (15):* A foreign commit means one outside the computed closure, not every commit by a different person. Shared requirements or governing bytes remain bound inputs. Application section 8.9 explains derived-output exclusions to avoid circular qualification.

**16.** The system of claim 1, wherein an instrument and repository hooks write working-tree bytes without staging, committing, amending, or pushing, the instrument halts at a human commit gate displaying changed paths grouped by repository and a suggested message, and generated reports use a custom merge driver followed by deterministic regeneration and staged-byte comparison.

*Drafting note (16):* The specific combination couples human-reviewed history to derived report state. Hook code supports no-stage behavior; a universal restriction on arbitrary agent shell commands requires an execution capability boundary. A bypassable hook does not establish remote admission control.

**17.** The system of claim 1, wherein each verbatim record has a closed field set for record identity, receipt instant, kind, verbatim content, invocation context, attributed identity, appended reasoning hypotheses, targets, chain position, and disposition, and each corresponding chain entry binds capture time, writer, attributed identity, record identity, kind, verbatim digest, record digest, sequence, predecessor digest, and entry digest.

*Drafting note (17):* This captures the schemas generically. Preserve original append-time record bytes when later reasoning or disposition changes; do not silently claim a digest over a mutable record still authenticates its original state. Application section 8.3 marks the preserving serialization refinement prospective.

**18.** The system of claim 1, wherein the classifier's refusal set comprises unbound disposition, unverified signature, an inert required instrument detected by abstract-syntax-tree inspection, uncommitted evidence, a non-canonical governing remote, an off-branch checkout, typed sign-off, governance co-editing with its subject, and a dirty tree, and wherein the remediation record binds corrective commits, a re-verified trust snapshot, and rerun evidence while retaining the flagged commits and recording resolution without erasure.

*Drafting note (18):* Static AST inspection supports a rule-based inertness heuristic, not completeness over program semantics. The local co-edit scan distinguishes suspicion from bypass-backed blocking and scans bounded history. The reflexive erasure rule and disjoint remediation consumer remain the contract-level and prospective portion of this fallback.

**19. A computer-implemented method for tamper-evident control of an agent-operated repository, comprising:** appending, by one or more processors, a verbatim record of every received human-originated turn without classification gating and a corresponding digest-linked chain entry; walking the chain end to end as a precondition of phase work and preventing the phase work upon a failed walk; admitting a governing-specification checkout only when unmodified and equal to a fetched upstream branch tip, treating a behind, diverged, locally modified, or unresolvable checkout as stale and preventing the phase work irrespective of a cached result, prior approval, or signed approval envelope; and applying a rule-based repository classifier that refuses a governance edit committed with its governed subject, classifies a history rewrite, force-push, replacement, or padding that removes a prior refusal from a scan window as a further instance of the refused class, and permits clearance of that refusal only through an append-only signed remediation record authorized by a principal group disjoint from authority introduced by flagged commits while preserving the flagged commits and refusal evidence.

*Drafting note (19):* Mirror every apex limitation rather than claiming generic monitoring as a method. A single operator may cause the steps across credential-separated domains; external authority means inaccessible credentials and governed authorization, not necessarily another legal entity.

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by one or more processors, cause the processors to control an agent-operated repository by:** appending a verbatim record of every received human-originated turn without classification gating and a corresponding digest-linked chain entry; walking the chain end to end as a precondition of phase work and preventing the phase work upon a failed walk; admitting a governing-specification checkout only when unmodified and equal to a fetched upstream branch tip, treating a behind, diverged, locally modified, or unresolvable checkout as stale and preventing the phase work irrespective of a cached result, prior approval, or signed approval envelope; and applying a rule-based repository classifier that refuses a governance edit committed with its governed subject, classifies a history rewrite, force-push, replacement, or padding that removes a prior refusal from a scan window as a further instance of the refused class, and permits clearance of that refusal only through an append-only signed remediation record authorized by a principal group disjoint from authority introduced by flagged commits while preserving the flagged commits and refusal evidence.

*Drafting note (20):* The storage-medium claim carries the same concrete prevention behavior. It excludes transitory signals and does not rely on program storage alone as the technical effect. Preserve the independent-claim India paragraph even if counsel changes claim category or numbering.

## §101 Alice positioning

Step 2A Prong Two anchors follow the application section 8.13 prevention register. Claims 1, 19, and 20 capture, recompute, compare, and prevent phase dispatch. The effect is an unavailable execution transition under missing continuity or current governance, not a report recommending better records.

Claims 2, 3, and 17 record, retain, sign, and publish binding data. These claims support receipt coverage and authenticated continuity rather than claiming human reasoning itself. The probable-reasoning field holds advisory hypotheses and never authorizes an operation.

Claims 4 through 7 resolve, compare, and block use of governing bytes. A failed fetch or missing resolver does not permit work. The specific security improvement concerns behavior at the network-resolution failure boundary.

Claims 8 through 12 chain, count, exclude, authenticate, rerun, retain, and reject. They prevent candidate-controlled accusation authority, verified-actor self-clearance, principal substitution, and chain transplantation. The observer and operation chains change accessible authority and machine state, not merely accountability language.

Claims 13 and 14 pin, compare, and refuse destructive successor states against external context. Claim 15 enumerates, hashes, and preserves a qualification binding despite irrelevant tip movement. Claim 16 halts, compares, and regenerates, preventing unreviewed staging and non-derived report merges.

Recentive Analytics v. Fox is a specific caution for classifier claims 1, 18, 19, and 20. This classifier is rule-based over commit shape, static syntax, and retained evidence; it is not generic ML applied to governance. The reflexive rule treats evidence-erasing history changes as refused repository operations and requires preserving resolution, a concrete architectural mechanism rather than a predicted label.

Step 2B should emphasize the ordered conjunction, not signatures or ordinary processors in isolation. Hash chains, role policies, and signed receipts carry a strong conventionality objection. The claimed residue must remain tied to the exact work-prevention, unresolvable-as-stale, and preserving-clearance operations, with prospective portions disclosed as such.

## EPO technical effect

Under Article 52 and Guidelines G-II 3.3 and 3.3.1, the specific technical purposes are network and repository security, tamper evidence, and fail-closed gating. Hashes bind exact records and accepted state; signatures authenticate operation authority; graph comparisons detect unlawful succession; static AST rules identify inert decision paths without running candidate code.

The mathematical operations serve those technical purposes rather than a business risk score. No ML step decides sabotage standing. Model-generated reasoning about a prompt is non-authoritative metadata and should not carry the inventive-step argument.

The shared special technical feature proposed for unity is the pre-work integrity interlock that retains refused history while checking current governing bytes. Observer deployment and succession fallbacks may attract a unity objection if they cease to share that feature. Human counsel should assess Article 82, Rule 44, and PCT Rule 13 against the final claim set.

## India s.3(k) technical effect

Independent claim 1: the technical problem is agent execution under incomplete input evidence or stale governing code. The technical solution couples verbatim capture and chain verification to revision comparison and preserving refusal state. The measurable technical benefit is a blocked unsafe phase dispatch and retained flagged evidence on reproducible tampering inputs, not a claimed empirical result. In the Ferid Allani and Microsoft v. Assistant Controller vocabulary, the contribution is a technical effect on computer security and requires no novel hardware.

Independent claim 19: the technical problem is a method that allows work before verifying repository continuity or that treats erased evidence as remediation. The technical solution orders capture, end-to-end verification, currency resolution, and disjoint preserving clearance before the permitted transition. The measurable technical benefit is deterministic refusal of digest mismatch, unresolved upstream state, and evidence-erasing recovery. This is a technical solution on ordinary processors, not a business method or an abstract algorithm alone.

Independent claim 20: the technical problem is stored instructions that permit an unsafe repository execution state when integrity predicates do not hold. The technical solution makes the processor enforce the same preconditions and preserve flagged history. The measurable technical benefit is prevention of that execution state under defined failure inputs without novel hardware, consistent with Ferid Allani and Microsoft v. Assistant Controller.

Each paragraph describes a proposed eligibility position. No paragraph asserts judicial approval, filing, or measured performance.

## Obviousness posture

vs Schneier and Kelsey secure audit logs + IBM US7305564B1 + Snodgrass et al., VLDB 2004: combination yields tamper-evident retained records but not unconditional receipt capture tied to a mandatory pre-work walk and unwaivable current-governance check. Claims 1, 3, 17, 19, and 20 must distinguish completeness of receipt from integrity of retained records.

vs US12555008 + US12651078 + US12613956B2: combination yields cognitive or agent-event ledgers and log-tampering prevention but not the fixed attribution ladder that captures even unclassified and unattributed inputs before work. The register describes the cognitive ledger as classification-gated; verify the actual claims and dates before using that contrast.

vs US12602481 NOVACOV + OpenSSF Scorecard pinned-dependencies: combination yields freshness-sensitive permits and pinned dependencies but not unwaivable equality of governing code to a freshly fetched moving tip with unresolvable expressly stale. Claims 4 through 7 retain each refusal condition rather than relying on generic freshness language.

vs Torres-Arias RSL + gittuf + git-ratchet: combination yields authenticated reference-state protection and rollback resistance but not the asserted reflexive classification of evidence erasure coupled to disjoint-group append-only remediation preserving the flagged commits. Claims 1, 18, 19, and 20 face substantial section 103 pressure from this combination.

vs Sigstore Rekor v2 + gitsign + US12651078: combination yields externally observable signatures and agent-communication evidence but not the proposed secretless candidate and disjoint-governance observer that reruns only reviewed read-only code and has no candidate reset or delivery transport. Claim 10 depends on capability absence, not naming a second workflow.

vs in-toto DSSE + RFC 9943 SCITT + SLSA Source track v1.2: combination yields signed provenance and transparent statements but not, without further structure, operation-principal equality plus run-chain continuity joined to trusted-context successor refusal. Claims 11 through 14 must not present the envelope format as the invention.

vs RSL + gittuf + RFC 9943 SCITT: combination yields strong policy-governed update authentication but not necessarily the enumerated successor decision against a caller's accepted base, pinned policy, enrolment, and operator while rejecting candidate-selected baselines. This is a narrow claimed distinction, not a conclusion that these references cannot be combined.

vs SLSA Source track v1.2 + in-toto: combination yields source and artifact binding but not necessarily run qualification over namespace and input closure that survives irrelevant tip changes. Claim 15 is a weaker fallback if the examiner supplies content-closure teachings; a source digest alone is not novel.

vs gitsign + Sigstore Rekor: combination yields signed repository activity but not the specific no-stage human commit stop with regeneration-bound reports. Claim 16 remains narrow and should not rely on the generic fact that humans can commit files.

vs draft-sharif-agent-audit-trail (revision 04 current; agent-verified 2026-09-21) + draft-sahu-agent-action-receipts-00 (agent-verified 2026-09-21) + draft-maintainer-1f916-agent-record-01 (agent-verified 2026-09-21): reported combination yields agent audit and action receipts but not the complete unconditional-capture, unresolvable-as-stale, and reflexive-preservation interlock as presently framed.

RSL, gittuf, SCITT, DSSE, and the reported agent-logging drafts create a serious obviousness headwind. The residue lies in the ordered preconditions, preservation rule, observer incapacity, and caller-supplied authority context. The present comparison uses the supplied register only, with no network retrieval or exhaustive search.

## Design-around foreclosures

1. Classification-gated omission: capture every received turn, including residual and unattributed turns; classification supplies metadata but cannot suppress a record.

2. Offline pass: keep unresolvable as stale in each independent claim and retain the explicit no-cache, no-approval, and no-signature waiver language.

3. Clean scan by padding: preserve prior flagged commit identities outside the candidate-controlled window and classify removal as another refused event, not a remedy.

4. Self-issued clearance: distinguish the alerted actor's verified principals from a typed login and exclude authority introduced by the flagged change from historical remediation.

5. Shared incident credentials: give the candidate no dispatch or reset authority; only an authenticated independently governed rerun may supply incident evidence.

6. Signed marker only: require each authoritative record's digest in its operation statement and verify the principal and preceding chain position.

7. Candidate baseline laundering: require the accepted baseline and trust context from the trusted caller, with sole-parent comparison rather than ancestry containment.

8. Timestamp arbitration: decide contested claim ownership from accepted sequence, refuse double claims, and reject seals preceding the accepted watermark.

9. Global-tip qualification: bind namespace and inputs, excluding derived output bytes, so unrelated commits do not invalidate qualification while changed shared inputs do.

10. Auto-staging hook: permit generated working-tree bytes but leave the index and history to a human; regenerate report merges before staged-byte acceptance.

11. Deployment overclaim: preserve the distinction between a local decision and exclusive admission. Neither a post-push check nor an observer template proves deployed enforcement.

## ENFORCED and PROSPECTIVE map

The evidence class applies only to the named portion. File-introduction dates do not establish when every predicate first exists. Test citations identify source evidence rather than test runs in this drafting pass.

| Mechanism | Claims | Evidence class | Evidence (tools/tests or contract line or DEFERRED row) |
| --- | --- | --- | --- |
| Chain syntax, sequence, links, entry digests, signed head verification | 1, 3, 17, 19, 20 | ENFORCED | tools/integrity.py, first landed 2026-06-24; tests/test_integrity_parent.py |
| Every received turn captured, complete ledger-to-chain walk, report head publication | 1-3, 17, 19, 20 | CONTRACT-ONLY | ENGRAM.md:114-123; FORGE.md:119-128; CRUCIBLE.md:72 |
| GitHub identity ladder and authenticity | 2 | CONTRACT-ONLY; DEFERRED | ENGRAM.md:117; DEFERRED.md: "Feedback `github_id` attribution authenticity" |
| Preflight genuinely precedes phase execution | 1, 19, 20 | DEFERRED; PROSPECTIVE runtime interlock | DEFERRED.md: "The gate preflight ran before phase work, not after" |
| Append-time snapshot retained despite later reasoning updates | 17 | PROSPECTIVE serialization refinement | Application 8.3; support review required |
| Currency predicate and stale refusal codes | 1, 4-7, 19, 20 | ENFORCED | tools/integrity.py, first landed 2026-06-24; tools/gate.py, first landed 2026-09-16; tests/test_freshness.py |
| No currency waiver and invocation ordering | 1, 4-7, 19, 20 | CONTRACT-ONLY | ENGRAM.md:65; FORGE.md:70 |
| Static sabotage predicates and bounded co-edit scan | 1, 18-20 | ENFORCED | tools/sabotage.py, first landed 2026-09-16; tests/test_sabotage.py |
| Reflexive historical-erasure classification | 1, 18-20 | CONTRACT-ONLY; PROSPECTIVE evaluator | ENGRAM.md:69; FORGE.md:74; bounded scan is not a complete erasure detector |
| Per-run sentinel chains and rolling-window repeat | 8 | ENFORCED | tools/sentinel.py, first landed 2026-09-16; tests/test_sentinel.py |
| Signed software-key repeat-alert clearance and verified-principal exclusion | 9 | ENFORCED | tools/sentinel.py, first landed 2026-09-16; tests/test_sentinel_clearance.py |
| Excluding a human whose actor identity has no verified principal | 9 | DEFERRED | DEFERRED.md: "A clearance for an alert raised against an unverified actor excludes nobody" |
| Disjoint-group append-only historical remediation consumer | 1, 18-20 | DEFERRED; PROSPECTIVE | DEFERRED.md: "no registered check reads a remediation record"; ENGRAM.md:69 |
| Immutable static probe over candidate bytes | 10 | ENFORCED | tools/incident_probe.py, first landed 2026-09-16; tests/test_incident_probe.py |
| Closed incidents, equivocation retention, bounded status, no reset or transport | 10 | ENFORCED | tools/incident_store.py, first landed 2026-09-17; tests/test_incident_store.py |
| Candidate incapacity and observer API workflow template | 10 | CONTRACT-ONLY; template support | ENGRAM.md:77; templates/sentinel.yaml; templates/sentinel-observer.yaml |
| Bridge, credentials, allowlists, runner, durable volume, monitoring | 10 | DEFERRED; PROSPECTIVE deployment | DEFERRED.md: "this session configured none of that infrastructure" |
| Signed run-operation fields, authorization, mismatch and chain checks | 11, 12 | ENFORCED | tools/operations.py, first landed 2026-09-20; tests/test_operations.py |
| Universal authoritative-write interposition and key-to-human enrolment | 11, 12 | DEFERRED; PROSPECTIVE boundary | DEFERRED.md: "a parent with no enrolled `run_operator` role is judged on structure alone" and "nothing here proves a principal is a distinct person" |
| Caller-supplied trusted-context successor decision | 13, 14 | ENFORCED | tools/transition.py and tools/transition_records.py, first landed 2026-09-18; tools/transition_signing.py, first landed 2026-09-20; tests/test_transition.py |
| Accepted-state reader | 13, 14 | ENFORCED with indirect tests only | tools/accepted_state.py, first landed 2026-09-18; tests/test_transition.py; no dedicated accepted-state test |
| Serialized push admission and accepted-reference custody | 13, 14 | DEFERRED; PROSPECTIVE service | DEFERRED.md: "no process holds exclusive write on an accepted ref, so nothing invokes it as admission" |
| Subject-closure digest | 15 | ENFORCED | tools/subject.py, first landed 2026-09-18; tests/test_subject.py |
| No-stage hooks, staged rendering, custom merge-driver binding | 16 | ENFORCED | tools/report_staging.py, first landed 2026-09-20; tools/gate.py, first landed 2026-09-16; tests/test_hooks.py |
| Signed report counterpart byte binding | 3, 16 | Related evidence, not hook proof | tests/test_report_binding.py |
| Instrument commit stop and universal no-history-write capability | 16 | CONTRACT-ONLY; PROSPECTIVE capability restriction | ENGRAM.md:79; templates/ hook roster |

## §112 / drafting cautions

Define human-originated turn, phase work, closed schema, stale checkout, governance path, subject path, refusal, disjoint principal group, trusted context, lawful successor, and subject closure before relying on them. Application section 8.2 supplies those definitions. Receipt completeness cannot be inferred from an intact chain of selectively retained records.

Avoid means-plus-function ambiguity under Williamson v. Citrix. The claims recite processors, stored instructions, data bindings, comparisons, and explicit refusal operations rather than an unexplained "controller configured to" result. If counsel uses that phrase, retain the disclosed algorithms and corresponding structures.

Claim 8 introduces "an alerted actor" by attributing the repeat threshold crossing to that actor, supplying antecedent basis for "the alerted actor's verified principals" in dependent claim 9. Check antecedent basis for the accepted base, pinned digest, and flagged commits after further amendments. Claims 9, 12, and 14 depend on claims 8, 11, and 13 respectively; every other dependent expressly depends on claim 1. Independent claims 19 and 20 mirror claim 1, and every claim remains a single sentence.

Claims 4 through 7 emphasize conditions already in the apex. Counsel should assess whether further narrowing structure is needed for formal dependent-claim practice, without deleting their numbers. No fallback should silently relax unconditional capture, permit an offline pass, or equate sentinel clearance with historical remediation.

The bounded scanner can miss erased history after the scan window advances. The checkpoint verifier does not prove every received turn exists in the ledger. The signed operation checker does not prove key-to-human identity. The transition checker does not serialize writes. Preserve these enablement and implementation limits instead of presenting the complete system as deployed.

The observer template resolves a run and commit through the platform API but does not retain an independent ref field in the closed incident schema. Claims should not imply complete ref-policy enforcement beyond disclosed support. Findings are suspected tampering, never proof of intent.

The intended family relationship remains prospective. Human counsel chooses continuation or divisional only after evaluating actual common support and any restriction; section 121 safe harbor is not automatic. New material requires separate support analysis and must not acquire an earlier priority date through wording alone.

The twenty-claim, three-independent structure fits the register's baseline fee strategy, subject to human verification of current rules. MPEP 802/806, 37 CFR 1.141-1.146, and the unity rules guide partition decisions, not an assertion that a restriction exists. This draft neither files nor authorizes filing.

No network search supports this pass. Human counsel should verify all register citations, effective dates, and reported drafts before any information disclosure statement, patentability conclusion, or filing. No statement asserts deployment, filing, or measured pass rate.
