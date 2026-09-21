Filing: US Non-Provisional utility application (35 U.S.C. § 111(a)). Inventor: Sarvex Jatasra. Assignee: Ethara.AI. Claim strategy: independent system claim 1, mirrored method claim 19, and mirrored storage-medium claim 20, with dependent claims 2-18. No claim is deleted once numbered; revision remains in place or marks a successor expressly. Filing is prospective and permanently human.

## Title

Primary: Out-of-Band Discharge of Digest-Bound Sign-Off Gates by a Unanimous Multi-Lineage Model Council, with Hazard-Scoped Conduct of Isolated Instruments.

Alternative: Cryptographic Gate Discharge with Producer-Excluding Model Councils and Isolated Instrument Scheduling.

## Abstract (proposed)

Systems and methods control out-of-band discharge of digest-bound sign-off gates. A processor recomputes a frozen artifact digest and records break-attempt lanes. At least three council seats have pairwise-distinct model lineages, each distinct from the producer lineage. Seats cast independent blind ballots. A signed envelope binds artifact identity, an externally authorized approver distinct from the producer, the roster, ballots, and a failed-attack transcript digest. Discharge requires unanimous approval and verified bindings; deficient evidence or roster qualification leaves human sign-off available. An enumerated permanently-human class remains outside automated discharge. Dependent embodiments retain a legacy digest interface, bounded disputes, per-seat calibration, and single-writer gatekeeping lobes. A separate conductor sequences isolated record-keeper, author, and auditor movements using restricted derived surfaces and specification-fixed hazard holds. A synchronization barrier and repeated-state stop bound cycling. A consolidated sheet presents approval instructions without discharging gates.

## Apex pillars in independent claims

1. Claims 1, 19, and 20 bind an enabling gate transition to a recomputed artifact digest and a signed typed envelope carrying authorized approver and distinct producer identities. CONTRACT-ONLY (GAUNTLET.md:5,43-51).

2. Claims 1, 19, and 20 require at least three pairwise-distinct model lineages, each distinct from the producer lineage, with independent blind ballots and all-seat approval. CONTRACT-ONLY (GAUNTLET.md:10,14,44,54,57).

3. Claims 1, 19, and 20 require a concluded failed break-attempt transcript digest bound in that envelope, not merely a score or an absence of criticism. CONTRACT-ONLY (GAUNTLET.md:6,44,52-54).

4. Claims 1, 19, and 20 keep deficient approvals shut with human fallback and affirmatively prevent automated discharge of the enumerated permanently-human class. CONTRACT-ONLY (GAUNTLET.md:11,14,45,55,57).

Deliberately excluded from apex: the compatibility digest write, explicit dissent and collision branches, dispute closure states, full-thread binding, per-seat calibration and demotion, lobe ownership, conductor ordering and read restrictions, hazard holds, synchronization, stopping, verbatim gate sheet, resumption, and tier-specific authorization. Claims 2-18 preserve these as fallback limitations. Concrete envelope encodings, hash algorithms, paths, and date formats remain specification examples.

Named surfaces must be described only generically in claims: in one implementation, GAUNTLET, MAESTRO, and NEO name work-order or successor concepts; `.trial/`, `.podium/`, `.memory/`, `.seed/`, and `.audit/` name harnesses; `DIRECTIVE.md`, `EDICT.md`, `VERDICT.md`, and `SCORE.md` name reports. These are illustrative vocabulary, not claim limitations.

In one implementation, `trinity.approval/v1` names a predicate; `gate_approver` names a role; `approval_record` names feedback; `approve`, `reject`, `converged`, `escalated`, `gates-pending`, and `steady-state` name states. In one implementation, `SAB_DISPOSITION_UNBOUND` names a refusal, `sample_ceiling` names a quota parameter, and thirty names its example value. None of these spellings limits a claim; the expressly claimed minimum of three council seats does.

Parent relationship: parent claim 34 is a dependent storage-medium claim with the council conjunction. Its notes prohibit merging the council envelope with parent claim 35's terminal release-disposition envelope. This sibling claims council discharge independently and keeps the conductor in system dependents; it does not assert that either mechanism has an executable implementation. CONTRACT-ONLY (GAUNTLET.md:43-57; MAESTRO.md:5-13).

## Claims

**1. A system for controlling out-of-band discharge of a digest-bound sign-off gate for an artifact produced using a machine-learning model, comprising:** one or more processors; one or more non-transitory memories storing instructions; and a trust-policy store identifying an external trust root, wherein execution of the instructions causes the processors to maintain the gate shut, recompute a canonical digest from frozen artifact bytes, record applicable break-attempt lanes over those bytes to a concluded transcript, qualify a council roster of at least three seats whose model lineages are pairwise distinct and each distinct from a producer model lineage, cause each seat independently to cast a verdict over the frozen bytes and transcript while preventing access to other seats' ballots before casting its own ballot, and permit discharge only upon verification of a signed approval envelope of a declared predicate type binding the canonical digest, an approver identity resolving to an authorized approver role in the external trust root, a producer identity distinct from the approver identity, the producer model lineage, the roster, every cast verdict, and a digest of the concluded transcript establishing that the applicable break-attempt lanes fail to break the artifact, with every cast verdict approving and the recomputed digest equal to the bound digest, wherein the processors keep the gate shut and retain human sign-off as a fallback when the required authorization, roster, ballots, or transcript do not qualify, and prevent discharge by any such envelope for an enumerated permanently-human class comprising publication of a task bundle or manuscript beyond a repository, patent filing, recording operational acceptance against a capped disposition, and admission of a staged candidate into a human-graded calibration library.

*Drafting note (1):* Preserve the conjunction and the artifact whose gate cannot open. A signature count is not a roster, a model instance is not a lineage, and an approving opinion is not failed-attack evidence. The positive all-seat requirement and negative human-class prevention both belong in the apex. Support: application sections 8.2-8.6; CONTRACT-ONLY (GAUNTLET.md:5-14,43-57).

**2.** The system of claim 1, wherein the processors, only for an approving envelope, write the bound digest into a legacy digest file byte-identically to a human approval interface, retain the envelope as authority distinct from that file, and recompute the artifact digest before a consuming operation, refusing the operation upon inequality.

*Drafting note (2):* The file is compatibility, not an alternative authorization source. Keep the consumer's unchanged recompute-first check and the byte-identical write together. Existing digest checks do not imply an implemented council consumer. Support: application section 8.3; CONTRACT-ONLY (GAUNTLET.md:43-46,51).

**3.** The system of claim 1, wherein any dissenting seat causes a rejecting verdict irrespective of the quantity of approving seats, and the rejecting verdict causes no legacy approval digest write.

*Drafting note (3):* This adds an explicit rejecting branch and its unwritten artifact, not merely a restatement of unanimous approval. Rejection opens dialogue rather than treating dissent as a permanent veto against all future bytes. Support: application sections 8.5-8.7; CONTRACT-ONLY (GAUNTLET.md:14,47,54,63).

**4.** The system of claim 1, wherein a lineage collision with the producer or another seat, or inability to seat the qualifying council, causes fallback to human sign-off without reducing the required seat count.

*Drafting note (4):* A different process name cannot cure shared lineage. Preserve the no-reduction clause against a runtime that silently substitutes two seats. The lineage-equivalence resolver remains prospective; the roster rule itself is CONTRACT-ONLY (GAUNTLET.md:10,14,57,80). Support: application sections 8.2 and 8.5.

**5.** The system of claim 1, wherein rejection opens an append-only dispute thread with arguments, rebuttals, and producer revisions under a bound round count, and the thread closes converged only upon withdrawal or resolution of every standing argument and unanimous approval of final bytes, or closes escalated upon exhaustion with surviving arguments and human fallback.

*Drafting note (5):* Converged and escalated express closure predicates rather than required token spellings. The producer owns revision; the gatekeeper never edits the inspected artifact. Human fallback does not erase surviving feedback. Support: application section 8.7; CONTRACT-ONLY (GAUNTLET.md:7,63-68).

**6.** The system of claim 5, wherein a signed approver argument record enters the producing instrument's feedback capture path with exact argument bytes and approver identity, each revision undergoes another attack as new frozen bytes, and a converged approval binds a digest of the full thread as its transcript digest.

*Drafting note (6):* This fallback connects dispute content to the same cryptographic authorization object, rather than to an optional discussion forum. Feedback capture step 1 expressly includes the out-of-band approver argument record. Support: application section 8.7; CONTRACT-ONLY (GAUNTLET.md:64-67; ENGRAM.md:116,123).

**7.** The system of claim 1, wherein contradiction of an approval by signed pilot evidence, an auditor finding, or a human reversal causes an append-only false-approval record that names a contradiction evidence digest and charges every council seat whose approving ballot joins that approval.

*Drafting note (7):* Every unanimous seat receives the contradiction attribution; no averaging removes a member's participation. An auditor finding and a human reversal are listed separately from signed pilot evidence so the claim does not invent a universal signature requirement for all contradiction sources. Support: application section 8.8; CONTRACT-ONLY (GAUNTLET.md:74).

**8.** The system of claim 7, wherein a memory instrument separate from the council owns demotion of approval authority to a watch standing requiring human sign-off, supports demotion of an individual seat, and permits restoration only under human-signed authorization and rotation of that seat's trust-root identity only by a human.

*Drafting note (8):* Distinguish the separate memory instrument that decides demotion from the gatekeeper memory lobe that records observations. The council cannot restore its own authority. No numerical false-approval threshold has source support in this lane. Support: application section 8.8; CONTRACT-ONLY (GAUNTLET.md:74-76,80).

**9.** The system of claim 1, wherein gatekeeping is pre-partitioned into memory, argument, and judgment lobes with disjoint single-writer artifact ownership, the memory lobe mediates standing between the other lobes, the argument lobe owns attacks and disputes but cannot sign verdicts, and the judgment lobe alone owns approval records and the signing credential.

*Drafting note (9):* Claim the existing ownership design, not an eventual organizational metamorphosis. A later split can move the owned directories without changing their meanings, but no named successor or deleted file is a limitation. Support: application section 8.9; CONTRACT-ONLY (GAUNTLET.md:25-29,82,87).

**10.** The system of claim 1, further comprising a conductor outside record-keeper, author, and auditor instruments, wherein the conductor performs none of their work, owns a disjoint harness with an append-only cycle ledger, and launches one isolated lane per movement in fixed order of record-keeper, author, then auditor.

*Drafting note (10):* The conductor is not the gatekeeper and inherits no approval power. This dependent introduces all three instruments without importing the parent's full certification claim. Fixed launch order does not require a non-hazarded movement to wait for every prior movement's completion. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:5,12,20,28-32).

**11.** The system of claim 10, wherein the conductor's sequencing read set consists of the three instruments' root reports, its own harness, and resident-bundle directory counts, and excludes instrument projections, raw instrument ledgers, proof stores, instrument harness internals, and bundle contents.

*Drafting note (11):* Use the closed read-set formulation. The conductor's own cycle ledger is not a forbidden raw instrument ledger. A root report is a derived sequencing surface, not a license to inspect the evidence beneath it. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:7,20-21,30).

**12.** The system of claim 11, wherein each movement's lane prompt names only its governing specification and a verified project root, and the conductor appends movement outcomes, report digests, pending gates, and named conditions to the cycle ledger without transmitting private findings or grading criteria between lanes.

*Drafting note (12):* Merely starting a fresh process is insufficient if the prompt carries a prior lane's findings. Retain both the minimal prompt and the content-limited record. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:5-7,29-30,45).

**13.** The system of claim 10, wherein governing specifications fix a hazard relation under which an open record-keeper gate prevents launch of both peer movements and an open author gate does not prevent launch of the auditor movement, without the conductor deriving a different hazard relation per run.

*Drafting note (13):* The fixed relation is structural, not a workflow engine's discretionary risk score. It distinguishes the record-keeper's upstream influence from the absent direct author-auditor channel. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:31).

**14.** The system of claim 13, wherein a cycle boundary forms a synchronization barrier preventing a new cycle until every gate of the closing cycle has discharge and every lane finishes, and an open gate when continuation would otherwise occur causes a pending-gates stop.

*Drafting note (14):* The boundary barrier coexists with hazard-scoped continuation inside a cycle. A paused lane is not a completed movement; a new memory projection must not replace the context beneath that lane. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:29,31-33).

**15.** The system of claim 14, wherein two consecutive cycles with identical root-report fingerprints, identical resident-bundle counts, and an identical pending-gate set cause a steady-state stop regardless of disposition prose in the reports.

*Drafting note (15):* Keep all three equality tests and their consecutive-cycle scope. A report-only stop misses occupancy changes and gate-set changes; an arbitrary timeout lacks the disclosed state comparison. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:34).

**16.** The system of claim 13, wherein the conductor presents a consolidated gate sheet containing verbatim approval instructions from a lane halted at an open gate, the instructions naming an artifact to inspect, a digest computation, and an approval target, while writing no approval digest, fabricating no signature, invoking no out-of-band approver, and discharging no gate.

*Drafting note (16):* Presentation is not authorization. Verbatim instructions preserve the lane's actual bound artifact and target instead of a conductor's summary. The conductor does not call the separately authorized gatekeeper. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:8,30-31,39-40).

**17.** The system of claim 14, wherein, for a lane halted at the open gate, discharge of that gate resumes the same halted lane through its own preflight, movements within the open gate's hazard remain unlaunched, and movements outside that hazard may run to their own lawful stops.

*Drafting note (17):* Initial isolation and same-session resumption are compatible. Re-paste supplies sequencing resumption, not permission to reproduce another instrument's phase state in the conductor. Support: application section 8.10; CONTRACT-ONLY (MAESTRO.md:11,29,31,41,45).

**18.** The system of claim 1, wherein a human-signed project authorization separately grants lower-tier scope or design approval and higher-tier release sign-off, and the higher tier requires a bound count of consecutive externally piloted, audit-clean cycles without enabling discharge of the permanently-human class.

*Drafting note (18):* A release sign-off inside the project is not terminal release authorization or the act of external publication. Do not import a multi-signature role threshold from the sibling release family into the council's unanimity rule. Support: application sections 8.3 and 8.6; CONTRACT-ONLY (GAUNTLET.md:11,55,80-82).

**19. A computer-implemented method for controlling out-of-band discharge of a digest-bound sign-off gate for an artifact produced using a machine-learning model, comprising, by one or more processors:** maintaining the gate shut; recomputing a canonical digest from frozen artifact bytes; recording applicable break-attempt lanes over those bytes to a concluded transcript; qualifying a council roster of at least three seats whose model lineages are pairwise distinct and each distinct from a producer model lineage; causing each seat independently to cast a verdict over the frozen bytes and transcript while preventing access to other seats' ballots before casting its own ballot; verifying a signed approval envelope of a declared predicate type against an external trust root, the envelope binding the canonical digest, an approver identity resolving to an authorized approver role, a producer identity distinct from the approver identity, the producer model lineage, the roster, every cast verdict, and a digest of the concluded transcript establishing that the applicable break-attempt lanes fail to break the artifact; permitting discharge only when that verification succeeds, every cast verdict approves, and the recomputed digest equals the bound digest; keeping the gate shut and retaining human sign-off as a fallback when the required authorization, roster, ballots, or transcript do not qualify; and preventing discharge by any such envelope for an enumerated permanently-human class comprising publication of a task bundle or manuscript beyond a repository, patent filing, recording operational acceptance against a capped disposition, and admission of a staged candidate into a human-graded calibration library.

*Drafting note (19):* This independent method mirrors claim 1 without relying on another claim for antecedent trust-root support. One operator may cause all computational steps through separate authority domains; actual human exercise of a fallback is not a required method step. Support: application sections 8.2-8.6 and 8.13; CONTRACT-ONLY (GAUNTLET.md:5-14,43-57).

**20. A non-transitory computer-readable storage medium storing instructions that, when executed by one or more processors, cause the processors to control out-of-band discharge of a digest-bound sign-off gate for an artifact produced using a machine-learning model by:** maintaining the gate shut; recomputing a canonical digest from frozen artifact bytes; recording applicable break-attempt lanes over those bytes to a concluded transcript; qualifying a council roster of at least three seats whose model lineages are pairwise distinct and each distinct from a producer model lineage; causing each seat independently to cast a verdict over the frozen bytes and transcript while preventing access to other seats' ballots before casting its own ballot; verifying a signed approval envelope of a declared predicate type against an external trust root, the envelope binding the canonical digest, an approver identity resolving to an authorized approver role, a producer identity distinct from the approver identity, the producer model lineage, the roster, every cast verdict, and a digest of the concluded transcript establishing that the applicable break-attempt lanes fail to break the artifact; permitting discharge only when that verification succeeds, every cast verdict approves, and the recomputed digest equals the bound digest; keeping the gate shut and retaining human sign-off as a fallback when the required authorization, roster, ballots, or transcript do not qualify; and preventing discharge by any such envelope for an enumerated permanently-human class comprising publication of a task bundle or manuscript beyond a repository, patent filing, recording operational acceptance against a capped disposition, and admission of a staged candidate into a human-graded calibration library.

*Drafting note (20):* Retain the full mirrored process and the non-transitory storage limitation. An instruction carrier is not an experimental result or an assertion that the present repository implements the council. Support: application sections 8.2-8.6 and 8.13; CONTRACT-ONLY (GAUNTLET.md:5-14,43-57).

## §101 Alice positioning

Step 2A Prong Two anchors appear in the application's prevention register. Claims 1, 19, and 20 recompute, compare, verify, resolve, require, and prevent a gate transition. The denied artifact is an effective out-of-band approval for changed bytes, unqualified authority, incomplete attack evidence, or a prohibited act. The subject is machine authorization, not the abstract desirability of review. CONTRACT-ONLY (GAUNTLET.md:5-14,43-57).

Claims 2-4 refuse the compatibility write or the approving state on digest inequality, dissent, or roster collapse. Claims 5-8 bind revised bytes and external demotion to continued authority rather than a panel's self-assessment. Claim 9 denies sibling write and signing authority. CONTRACT-ONLY (GAUNTLET.md:25-28,46-57,63-76).

Claims 10-12 restrict machine-readable access and prompt contents. Claims 13-14 prevent hazarded launches and new-cycle advance. Claims 15-17 stop repeated machine state and prevent a gate sheet from functioning as approval. These restrictions name inaccessible inputs and disabled transitions rather than advisory management procedures. CONTRACT-ONLY (MAESTRO.md:5-8,28-41).

Step 2B relies on the ordered combination: frozen bytes, concluded attack transcript, producer-excluding lineage roster, blind all-seat approval, externally resolved distinct signer, and affirmative human-class exclusion. Hashing, signatures, model panels, and workflow scheduling individually carry substantial conventional-art risk. Contract-only support cannot be represented as demonstrated implementation when making this argument.

| Prevention verb | Claims | Machine object or transition |
|---|---|---|
| Recomputes and compares | 1-2,19-20 | Digest-bound operation remains disabled on changed bytes |
| Verifies and resolves | 1,19-20 | Unauthorized or producer-signed approval has no discharge effect |
| Prevents access | 1,19-20 | Other seat ballots remain unavailable before casting |
| Refuses | 3-4 | Dissent or lineage collision cannot yield an approving digest write |
| Requires binding | 1,6,19-20 | Missing transcript or revised-byte mismatch cannot support approval |
| Prevents discharge | 1,19-20 | Permanently-human act lacks an automated authorization edge |
| Denies write authority | 9 | Argument lobe cannot write a signed verdict |
| Restricts reads | 11-12 | Conductor cannot access private instrument evidence |
| Prevents launch and advance | 13-14 | Hazarded movement and next cycle remain held |
| Stops and discharges nothing | 15-17 | Repeated cycle and sheet-based self-approval have no execution path |

The register describes claim-required prevention, not a list of functions that the current repository implements. Council support is CONTRACT-ONLY (GAUNTLET.md:5-14,25-28,43-76); conductor support is CONTRACT-ONLY (MAESTRO.md:5-8,28-41).

## EPO technical effect

Under Article 52 and Guidelines G-II 3.3 and 3.3.1, the specific technical purpose of digest computation is byte identity, signature verification is authority resolution, and lineage and ballot evaluation is control of a gate-state transition. Cryptographic gate discharge is a machine state transition, not delegation of human judgment. CONTRACT-ONLY (GAUNTLET.md:43-57).

For claims 1, 19, and 20, model outputs serve a constrained authorization protocol rather than an unconstrained recommendation. A changed artifact cannot use the prior byte binding, and a missing concluded attack cannot become an implied approving ballot. The claimed technical effect depends on implementing those refusals, not on calling review trustworthy. CONTRACT-ONLY (GAUNTLET.md:6,43-57).

For claims 10-17, the technical purpose is preventing orchestration from transmitting private data between isolated execution domains or changing a projection beneath an unfinished lane. A report digest and residency count support scheduling without underlying evidence reads. The fixed relation and barrier implement that restriction; ordinary task scheduling alone is not the asserted contribution. CONTRACT-ONLY (MAESTRO.md:7,29-34).

## India s.3(k) technical effect

Independent claim 1: the technical problem is unauthorized progression on changed artifact bytes or insufficient authorization evidence. The technical solution is a processor-and-memory system combining canonical digest comparison, external role resolution, isolated blind ballots, producer-excluding lineages, transcript binding, and refusal of prohibited transitions. A measurable technical benefit would be rejection of mismatched or incomplete approval inputs at the gate. Ferid Allani and Microsoft v. Assistant Controller support this technical-contribution framing without requiring novel hardware; no measured benefit is asserted.

Independent claim 19: the technical problem is a review result detached from the bytes and authority that permit an operation. The technical solution is the ordered computer process of recomputing, recording, qualifying, verifying, and preventing discharge. A measurable technical benefit would be no enabled operation for negative cases involving changed bytes, missing transcript, or a lineage collision. Under Ferid Allani and Microsoft v. Assistant Controller, the method's operation on machine authorization state supplies the argument, not automation of a mental judgment or a claim of novel hardware.

Independent claim 20: the technical problem is execution of stored approval logic that admits self-approval, stale byte identity, or an incomplete review. The technical solution is the same constrained verification process encoded as instructions on a non-transitory medium. A measurable technical benefit would be refusal of those invalid execution paths when the instructions run. Ferid Allani and Microsoft v. Assistant Controller permit a technical-effect argument without novel hardware, but the medium label alone supplies none and no deployment is asserted.

## Obviousness posture

vs IETF draft-schrock-ep-authorization-receipts (revision 01 as retrieved, revision 13 current; agent-verified 2026-09-21) + US12001822B2: combination yields an authorization receipt and multi-signature artifact validation but not necessarily the entire producer-excluding lineage roster, blind unanimity, concluded failed-attack binding, human fallback, and permanently-human prevention of claims 1, 19, and 20.

vs arXiv 2609.15803 + US11328214B2 + PoLL arXiv 2404.18796: combination yields unanimity reasoning and diverse panel review but not necessarily an envelope whose gate effect depends on a producer-distinct authorized approver, the same frozen artifact and transcript digests, and a human-only class outside every envelope's scope.

vs US11392940B2 + US12001822B2: combination yields M-of-N authorization and signed deployment-artifact approval but not the all-seated-lineages condition or a no-break transcript that must exist before approval can carry authority. Retain the explicit no-seat-reduction and dissent branches in claims 3-4.

vs Avizienis N-version programming + DO-178C: combination yields diversity and assurance discipline but not necessarily each unanimous seat's digest-linked false-approval charge, a separate memory instrument's surgical demotion decision, and human-only restoration. Claims 7-9 remain narrower record and ownership fallbacks rather than a claim to diversity itself.

vs PoLL arXiv 2404.18796 + Collina et al. arXiv 2609.15803 (the informal Qorum Method and quorum-review items were withdrawn as panel teachings on 2026-09-21): combination yields panel review and discussion but not necessarily a bounded append-only thread whose final authorization binds the full thread digest, whose producer alone revises bytes, and whose exhausted arguments remain pending feedback. Claims 5-6 preserve this distinction.

vs auditor-independence statute + Brewer and Nash Chinese Wall + Apache Airflow: combination yields role separation, conflicting-access restrictions, and conventional workflow sequencing but not necessarily a conductor restricted to derived reports, its own harness, and residency counts with a specification-fixed hold relation, minimal lane prompts, and a closing-cycle barrier. Claims 10-17 add those concrete restrictions rather than generic orchestration.

The novelty residue asserted against US12001822B2, arXiv 2609.15803, and US11328214B2 is the complete conjunction in the portfolio register, not any isolated consensus primitive. For the conductor, the novelty residue against Brewer and Nash Chinese Wall plus Apache Airflow includes derived-surface-only reads and a hold relation fixed in specification text. These distinctions require claim-chart and effective-date review before filing.

No new network retrieval supports this draft. The authorization-receipt draft and informal quorum tools remain reported with verification pending. The conductor comparison follows parent section 8.36 and the expressly requested references; it does not assert a specific statutory provision or an Airflow configuration that this lane does not inspect.

## Design-around foreclosures

1. Process multiplicity is not lineage diversity: the roster compares lineage classes pairwise and against the producer, not process names or key counts. CONTRACT-ONLY (GAUNTLET.md:10,44,57).

2. Majority substitution does not satisfy the apex: every seated ballot must approve; claims 3-4 additionally deny an approval write on dissent or a smaller roster. CONTRACT-ONLY (GAUNTLET.md:14,47,54,57).

3. Silent inspection does not supply attack evidence: a missing or inconclusive lane forces rejection, and the envelope must bind a concluded failed-attack transcript. CONTRACT-ONLY (GAUNTLET.md:6,44,53-54).

4. Digest-only approval does not supply out-of-band authority: the legacy file remains compatibility and the consuming check must verify the envelope. CONTRACT-ONLY (GAUNTLET.md:43-46).

5. Revising bytes cannot preserve old inspection authority: re-attack follows producer revision, and convergence binds the full final thread. CONTRACT-ONLY (GAUNTLET.md:65-67).

6. Aggregate blame cannot remove individual participation: every approving seat receives the false-approval charge and a separate memory instrument owns demotion. CONTRACT-ONLY (GAUNTLET.md:74-76).

7. Directory colocation does not erase ownership: single-writer lobes remain distinct even in one run, and the argument lobe never signs. CONTRACT-ONLY (GAUNTLET.md:25-29,82).

8. A fresh lane with a prior-lane summary still creates a channel: the conductor prompt carries only the specification and verified root. CONTRACT-ONLY (MAESTRO.md:5-7,29).

9. An author gate is not a global stop: the fixed hazard relation leaves the auditor launch free, while the cycle boundary still blocks a fresh cycle under any open gate. CONTRACT-ONLY (MAESTRO.md:31-33).

10. Unchanged report prose is not the steady-state test: report fingerprints, occupancy, and the pending-gate set must all match across consecutive cycles. CONTRACT-ONLY (MAESTRO.md:34).

11. A consolidated approval dashboard cannot approve: the conductor copies instructions verbatim and never invokes the gatekeeper or writes the target digest. CONTRACT-ONLY (MAESTRO.md:8,39-41).

12. Automated publication remains outside these claims by their express terms. The permanently-human exclusion narrows scope intentionally; do not describe that excluded architecture as captured by the claims. CONTRACT-ONLY (GAUNTLET.md:11,55).

## ENFORCED and PROSPECTIVE map

The council and conductor family is contract-only. The two narrow implementation rows concern pre-existing gate and release checks, not an implemented council or conductor. Module introduction dates identify first appearance, not the arrival date of each current condition; all four named source and test files exist on disk.

| Mechanism | Claims | Evidence class | Evidence (tools/tests or contract line or DEFERRED row) |
|---|---|---|---|
| Digest-bound council gate and legacy interface | 1-2,19-20 | CONTRACT-ONLY | GAUNTLET.md:43-51 |
| Failed break-attempt transcript and lane completeness | 1,19-20 | CONTRACT-ONLY | GAUNTLET.md:6,35,44,52-56 |
| Producer-distinct authorized approver | 1,19-20 | CONTRACT-ONLY | GAUNTLET.md:5,44-45,80-82 |
| Blind pairwise-distinct roster and unanimity | 1,3-4,19-20 | CONTRACT-ONLY | GAUNTLET.md:10,14,44,54,57 |
| Lineage collision and unseatable human fallback | 4 | CONTRACT-ONLY | GAUNTLET.md:10,14,57 |
| Dispute states and full-thread digest | 5-6 | CONTRACT-ONLY | GAUNTLET.md:63-68 |
| Exact signed argument feedback capture | 6 | CONTRACT-ONLY | GAUNTLET.md:64; ENGRAM.md:116,123 |
| Every-seat false-approval record | 7 | CONTRACT-ONLY | GAUNTLET.md:74 |
| Separate memory demotion and human-only restoration | 8 | CONTRACT-ONLY | GAUNTLET.md:75-76,80 |
| Three-lobe disjoint ownership | 9 | CONTRACT-ONLY | GAUNTLET.md:25-29,82,87 |
| Fixed movement order and cycle ledger | 10 | CONTRACT-ONLY | MAESTRO.md:5,12,20,28-30 |
| Restricted reads and minimal lane prompts | 11-12 | CONTRACT-ONLY | MAESTRO.md:5-7,29-30 |
| Specification-fixed hazard relation | 13 | CONTRACT-ONLY | MAESTRO.md:31 |
| Boundary barrier and pending-gates stop | 14 | CONTRACT-ONLY | MAESTRO.md:33,39-41 |
| Two-cycle steady-state conjunction | 15 | CONTRACT-ONLY | MAESTRO.md:34 |
| Verbatim gate sheet without discharge | 16-17 | CONTRACT-ONLY | MAESTRO.md:8,39-41,45 |
| Tiered human-signed authorization | 18 | CONTRACT-ONLY | GAUNTLET.md:55,80-82 |
| Permanently-human class in full | 1,19-20 | CONTRACT-ONLY | GAUNTLET.md:11; no general code enforcement asserted |
| Permanently-human carve-out on release path: no acceptance waiver of cap | 1,19-20, boundary only | ENFORCED | tools/release.py, first landed 2026-09-16; tests/test_release.py; categorical waiver refusal only |
| Recompute-first digest check on qualified artifact path | 1-2,19-20, check only | ENFORCED | tools/gate.py, first landed 2026-09-16; tests/test_gate.py; recomputation and changed-byte refusal only |
| Formal lineage-equivalence resolver and isolated service realization | 1,4,19-20 | PROSPECTIVE | Parent claims-skeleton definition; no council or conductor module asserted |

In one implementation, the release waiver check refuses operational acceptance as a way to raise a capped release disposition, including a waiver that looks signed. This is not code enforcement of patent filing or human calibration admission outside the release path. The gate's recomputed bundle-set comparison likewise does not implement the council envelope consumer.

## §112 / drafting cautions

Define lineage objectively before allowance. The parent drafting note proposes a trust-recorded equivalence relation for shared base model, training pipeline, or provider derivation. A closure over those relations avoids treating display-name changes as new lineages. The present contract supplies the exclusion rule and roster, not a complete resolver implementation; the formal resolver remains PROSPECTIVE.

Avoid an unexplained "controller configured to" black box under Williamson and section 112(f). Claim 1 recites processors, memory, trust storage, and the ordered comparisons and refusals. The specification must support each computation and the denied transition, not merely a desired quality outcome.

Antecedent basis: claims 1, 19, and 20 each introduce the external trust root independently. Claim 10 introduces the conductor and the three instruments. Claim 11 introduces the restricted read set, claim 13 the fixed hazard relation, and claim 14 the closing cycle and an open gate. Claim 16 introduces a lane halted at an open gate. Claim 17 depends on claim 14, inherits its open gate and claim 13's hazard relation, and independently introduces a lane halted at that gate before referring to the same halted lane. The gatekeeper memory lobe of claim 9 is not the demotion-owning memory instrument of claim 8.

Keep the declared predicate type generic. Do not require a file name, a work-order name, a software package, a refusal code, or a role token as a claim limitation. The minimum of three seats and two consecutive cycles are deliberate express functional counts, not incidental path numerals.

Do not promise statistical independence or zero false approvals from distinct lineages. Blind ballots prohibit sharing ballots before casting; they do not prove that training sources are independent. A failed break attempt means a concluded attack without a break, not a failed process or missing evidence. CONTRACT-ONLY (GAUNTLET.md:10,53-57).

Citations follow the current on-disk line numbering of GAUNTLET.md and MAESTRO.md.

The conductor source has a tension between restricted reads and its reference to minted disposition records, and between non-performance rules and reconciliation wording. Do not infer permission to read a private ledger, perform pipeline work, or make git writes. The claims use derived reports, the fixed hazard relation, and the boundary barrier; precise runtime realization remains PROSPECTIVE.

Single-actor posture: one platform operator may perform or cause the computations using isolated services and externally rooted authority. Distinct producer and approver identities are not necessarily distinct legal entities. Human fallback and permanently-human exclusions constrain machine authority rather than requiring a human to complete an independent method step. PROSPECTIVE.

Unity and double-patenting review remain human legal tasks. Parent claim 34 overlaps the core council disclosure, and the conductor dependents may face distinct-invention or unity objections unless their shared technical contribution is established. A divisional requires appropriate procedural support; this draft asserts none. Keep the conductor combination supported without pretending it shares signature authority with the council.

All council and conductor mechanisms remain CONTRACT-ONLY except formal extensions marked PROSPECTIVE. Claims state proposed instruction behavior, never that a council sits, votes, approves, or a conductor runs in this repository. Filing, deployment, and measured outcomes are not asserted. The drafting party reconciles and never files; filing stays human. CONTRACT-ONLY (GAUNTLET.md:11; ENGRAM.md:294).
