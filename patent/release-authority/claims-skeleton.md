Filing: US Non-Provisional utility application (35 U.S.C. § 111(a)). Inventor: Sarvex Jatasra. Assignee: Ethara.AI. The strategy uses an apex system claim 1, mirrored method claim 27, mirrored medium claim 28, and dependent claims 2 through 26. No claim is deleted once numbered; revision retains its number, or a supersession note names its successor. Filing remains prospective and human-gated. Counsel determines divisional or continuation treatment relative to the related parent disclosure.

## Title

Primary: Externally Governed Release Authority with Threshold Dispositions, Control Receipts, and Software-Only Signing for Machine-Learning Evaluation Artifacts.

Alternative: Cryptographic Release Control Through Capability-Limited Qualification, Principal Thresholds, and Closed Execution Receipts.

## Abstract (proposed)

A computing system controls release of machine-learning evaluation artifacts through distinct qualification and authorization capabilities. A local routine has a closed result type excluding terminal release. A separate governance publisher verifies immutable candidate and export snapshots using independently pinned verifier and trust revisions. Instrument-specific group dispositions require thresholds of distinct externally enrolled producer principals and disjoint approver principals. Partial signatures accumulate over unchanged payload bytes without shared private keys. Each bundle requires an authorized execution receipt covering every policy-required control exactly once under a common manifest closure. Non-passing or incomplete evidence prevents release, and the verifier does not execute the benchmark. Further embodiments enforce software-only signing through bounded carrier parsing, retain transmitted signed bytes across version compatibility, include a terminating line feed within canonical signature inputs, and bind evidence to a relocation-invariant project-relative audience.

## Apex pillars in independent claims

1. Local qualification excludes terminal release from its closed result type; a report or an unsigned proposed final record cannot override that incapacity.
2. A separate governance publisher verifies immutable candidate and export snapshots using independent verifier and trust pins outside candidate authority.
3. Instrument-specific group dispositions require thresholds of distinct externally enrolled producer principals and then disjoint approver principals, not counts of signature objects.
4. Each bundle requires an authorized receipt with exact policy-control coverage under a common manifest closure, and the verifier cannot execute the benchmark to fill an evidence gap.

Deliberately excluded from apex are the literal disposition labels, schema versions, optional quorum values, report formatting, specific snapshot field spellings, partial-signing commands, named compatibility command, software-key algorithm names, canonicalization profile label, and relative-path prefix. Claims 2 through 26 preserve structural fallbacks without making implementation vocabulary the invention.

Named surfaces must be described only generically in claims: in one implementation, illustrative names include BLOCK, HOLD, SHIP_ELIGIBLE, SHIP, FORGE, CRUCIBLE, `trinity.qualification/v2`, `trinity.release-disposition/v2`, `trinity.release-disposition/v3`, `gate_producer`, `gate_approver`, `signing-status`, `cosign-assemble`, `gate.py promote --approver NAME`, `SAB_DISPOSITION_UNBOUND`, `trinity.oracle-run/v4`, `trinity.release-policy/v3`, and `execution_fidelity`. The optional 2-of-N setting and the six-control count are examples, not claim numerals.

In one implementation, further illustrative vocabulary comprises `trinity.harness-config/v1`, `trinity.execution/v2`, `trinity.pilot-policy/v2`, `trinity.pilot-attempt/v2`, `ORACLE_FIDELITY_REFUSED`, `ORACLE_FIDELITY_DIGEST_MISMATCH`, `trinity.jcs-lf.v1`, `expectedAudience`, `./`, `allowed_signers`, OpenSSH, SSHSIG, and the `sk-` algorithm families and certificate forms. File names, control names, and sixty-four as a parser depth remain specification examples. Single-outcome coverage is a structural uniqueness relation, not an arbitrary vocabulary size.

## Claims

**1. A system for controlling release of machine-learning evaluation artifacts, comprising:** one or more processors; one or more non-transitory memories storing instructions executable by the processors to implement a local qualification routine whose closed result type excludes a terminal release value, and a verifier in a governance publisher repository separate from a candidate repository; and a governance trust store outside candidate write authority; wherein the verifier operates at an independently pinned revision on immutable candidate and export snapshots under identities, trust revisions, and a closed release policy fixed outside a candidate tree, authenticates instrument-specific group dispositions against a producer-role threshold of distinct externally enrolled principals and then an approver-role threshold that excludes the producer principals, requires for each exported bundle an authorized execution receipt containing a single outcome for each policy-required control under a common manifest closure digest with neither duplicate nor additional control outcomes, and permits terminal release authorization only upon acceptance of the snapshots, dispositions, and receipts, while preventing execution of the benchmark by the verifier.

*Drafting note (1):* Preserve all apex pillars together. Application sections 8.2 through 8.6 define the boundaries and algorithms. The local incapacity concerns the qualification code path and external acceptance, not a claim that an adversary cannot type a terminal-looking string. The deployed publisher isolation remains prospective; verifier-side implementation alone does not prove it.

**2.** The system of claim 1, wherein the instructions copy a disposition line of each report of a set of root reports verbatim from its applicable machine record and refuse a report token that exceeds the standing permitted by that record.

*Drafting note (2):* This fallback addresses report elevation rather than signature validity alone. Distinguish the contractual verbatim-rendering requirement from the implemented mismatch refusals. A lower standing does not manufacture release authority.

**3.** The system of claim 1, wherein each group disposition binds a complete export snapshot digest, a canonical bundle-set identity, an immutable candidate commit, a repository identity, a project identity, and the independently pinned verifier revision.

*Drafting note (3):* Complete export binding and logical bundle-set identity perform different jobs. Keep both to prevent a task-only digest from leaving export bytes outside the release commitment.

**4.** The system of claim 3, wherein the governance publisher fixes expected repository identities, verifier and trust commits, a signer policy, a trusted-root version, and the closed release policy outside the candidate tree and denies candidate selection of those inputs.

*Drafting note (4):* This narrows the authority source, not the directory's spelling. Library arguments can supply trusted inputs, but deployment must prevent a candidate operator from choosing them. Local installation is not proof of that deployment.

**5.** The system of claim 1, wherein the verifier counts distinct authenticated principal identities rather than signatures, excludes revoked and expired principals at an evaluation instant, and prevents repeated signatures or multiple keys attributed to a common principal from increasing either role's eligible-principal count.

*Drafting note (5):* Principal equality and external enrollment are material. Do not equate distinct principal strings with proven distinct human persons. The trust root and signer-policy constraints supply machine-checkable identity rules, while enrollment remains an external governance duty.

**6.** The system of claim 1, wherein the instructions retain partial signatures from separate signing sessions over unchanged disposition payload bytes without transferring a private key between signers or supplying a private key to an envelope assembler.

*Drafting note (6):* Accumulation survives session boundaries because the payload does not change. Sigstore supplies close prior art for independent signing; the fallback gains specificity through its dependency on the complete apex combination.

**7.** The system of claim 6, wherein the instructions authenticate the retained partial signatures and report, for each role, a required threshold, eligible principals, a missing-principal count, and a completion indication.

*Drafting note (7):* The status computation authenticates evidence before reporting progress. A count of files or asserted signer names is insufficient. The displayed completion state does not replace publisher verification.

**8.** The system of claim 6, wherein the envelope assembler resumes from an existing envelope, requires each added partial to match the existing envelope's payload bytes and payload type exactly, refuses duplicate signature entries, and preserves the payload bytes when forming a combined envelope.

*Drafting note (8):* Keep byte equality rather than semantic JSON equality. The outer envelope can change to accommodate additional signatures without changing the signed payload. Assembly need not itself evaluate role thresholds; the verifier performs that separate task.

**9.** The system of claim 1, wherein the verifier accepts an existing valid signed disposition of a preceding named-principal schema through an expressly selected compatibility path without reserializing its signed payload or treating its signatures as approval of a newer-schema payload.

*Drafting note (9):* In one implementation, existing valid v2 disposition bytes remain accepted, while explicit named-approver promotion chooses the v2 compatibility form. Do not imply that a migration creates replacement signatures or that receipt-policy downgrade follows from disposition compatibility. Counsel may separate generation-path selection from automatic verification dispatch if broader support warrants that revision.

**10.** The system of claim 1, wherein typed signature framing distinguishes instrument and schema domains and the verifier refuses an otherwise valid envelope copied from a different instrument domain or schema domain.

*Drafting note (10):* The fallback rejects copied authority even where a key remains valid. Namespace and payload-type art is substantial, so retain the instrument-specific group-disposition context rather than claiming generic domain separation.

**11.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome is missing from a receipt.

*Drafting note (11):* Coverage uses required-set equality. Absence cannot mean an implicit passing outcome or a request for the verifier to run the benchmark.

**12.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates failure.

*Drafting note (12):* A valid signature authenticates a failed observation but cannot convert it into acceptance. This is a separate status refusal from missing coverage.

**13.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates skipped execution.

*Drafting note (13):* A declared skip is present evidence of non-execution, not a missing row and not an allowed policy exception.

**14.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates deferred execution.

*Drafting note (14):* Planned later work cannot satisfy current release conditions. Present-tense protocol disclosure does not assert that a deferred runner exists.

**15.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates a waiver.

*Drafting note (15):* A signature over a waiver remains insufficient. Human operational acceptance of a capped state cannot raise it to terminal release.

**16.** The system of claim 1, wherein the verifier refuses terminal release authorization when a receipt repeats a required control identifier, irrespective of agreement between the repeated outcomes.

*Drafting note (16):* This forecloses replacing uniqueness with deduplication. Even matching favorable duplicates fail the receipt's exact coverage relation.

**17.** The system of claim 1, wherein the verifier refuses terminal release authorization when a receipt contains a control outcome outside the policy-required control set.

*Drafting note (17):* A trusted policy may enlarge the required set, but a receipt cannot enlarge it unilaterally. Extra outcomes fail equality rather than disappearing during parsing.

**18.** The system of claim 1, wherein only the closed release policy outside candidate write authority may designate a judge-completeness and repeatability control non-applicable, and the receipt must retain an outcome row for that control.

*Drafting note (18):* Non-applicability is a trusted-policy decision with a represented outcome. It is neither a signer-authored waiver nor an omitted row.

**19.** The system of claim 18, wherein the verifier refuses a non-applicable designation for an execution-fidelity control regardless of a candidate declaration or receipt signer's assertion.

*Drafting note (19):* Execution fidelity never inherits the judge exception. This limitation provides a narrower fallback against generic configurable checklist systems.

**20.** The system of claim 19, wherein the instructions validate measurement-fidelity carriers comprising a pinned harness configuration with a separate adequacy approval, per-rollout execution telemetry, and pilot policy and attempt records binding predeclared disjoint groups and rollout conformance standing, while preventing absent fidelity coverage from constituting a passing control outcome.

*Drafting note (20):* Carrier validators exist, but external observation, substantive adequacy judgment, and the complete execution-attestation and authenticated-roster cross-binding remain separate dependencies. Do not describe supplied collateral validation as proof that the publisher automatically obtains every resource or that a signer observed execution faithfully.

**21.** The system of claim 20, wherein the verifier refuses superseded execution-receipt and release-policy schemas without a legacy acceptance route, independently of compatibility permitted for a preceding disposition schema.

*Drafting note (21):* Compatibility is type-specific. The specification's current receipt and policy versions require fresh evidence, unlike retained valid disposition payloads of the preceding accepted version.

**22.** The system of claim 6, wherein a software-only signature backend parses bounded private-key public headers, detached-signature public-key and signature-algorithm fields, and signer-policy public blobs to refuse hardware-security-key algorithms and their certificate forms before invoking a cryptographic subprocess or performing device discovery.

*Drafting note (22):* Claim parsing of embedded carriers and pre-invocation ordering, not a preference against hardware. Ordinary-looking signatures do not disclose the physical custody of an opaque remote signer. No universal hardware-provenance claim follows from an algorithm string.

**23.** The system of claim 8, wherein a canonical byte profile appends a terminating line-feed byte to a canonical serialization of a structured data object and includes that byte inside every digest and signature input using the profile, and the verifier authenticates transmitted payload bytes rather than a reserialization.

*Drafting note (23):* The terminating byte belongs inside typed signature framing and its payload length, not outside as transport formatting. A canonical-conformity comparison may serialize for comparison without substituting that serialization as the signed message.

**24.** The system of claim 23, wherein the canonical byte profile rejects lone surrogates, non-finite numbers, duplicate object keys, cyclic containers, and programmatic integers not exactly representable as finite binary floating-point values, and a text parser refuses nesting beyond a defined resource bound.

*Drafting note (24):* Avoid claiming rejection of every integer above the common safe interval. Exactly representable larger programmatic integers can qualify, while parsed numeric tokens use binary64 semantics. The implementation's text-depth limit is distinct from RFC 8785 itself.

**25.** The system of claim 1, wherein a gate policy uses a canonical project-root path relative to a trusted authority root as an expected signed audience and uses a digest of that path to identify the policy, such that relocation of the whole authority tree preserving its relative layout preserves the audience while an audience mismatch prevents authorization.

*Drafting note (25):* Relocation invariance does not cover renaming the candidate within the tree or replacing the trust authority. Path checks and role authorization have different implementations; do not attribute policy-file lookup to the trust-root role parser.

**26.** The system of claim 1, wherein the policy-required controls comprise build-asset and harness integrity, oracle and negative-control integrity, alternate-solution and mutation-based grading integrity with instruction scope, judge completeness and repeatability, trial and reward accounting, and execution fidelity.

*Drafting note (26):* The categories identify technical observations in generic language. Neither the implementation's control identifiers nor its literal count limits this claim. The closed policy may enumerate further controls, each requiring its own unique outcome.

**27. A computer-implemented method for controlling release of machine-learning evaluation artifacts, comprising:** computing, by processors, a local qualification with a closed result type excluding a terminal release value; operating a verifier at an independently pinned revision in a governance publisher repository separate from a candidate repository, using identities, trust revisions, and a closed release policy fixed outside a candidate tree to evaluate immutable candidate and export snapshots; authenticating instrument-specific group dispositions against a producer-role threshold of distinct externally enrolled principals and then an approver-role threshold excluding those producer principals; requiring for each exported bundle an authorized execution receipt containing a single outcome for each policy-required control under a common manifest closure digest with neither duplicate nor additional control outcomes; permitting terminal release authorization only upon acceptance of the snapshots, dispositions, and receipts; and preventing the verifier from executing the benchmark.

*Drafting note (27):* This mirrors claim 1's ordered computer operations. A single platform operator can cause the steps through separate administrative domains. Receipt verification does not require the verifier itself to perform an external execution act, and producer-first authorization is not a temporal ordering of all signing sessions.

**28. A non-transitory computer-readable storage medium comprising:** instructions that, when executed by processors, cause the processors to control release of machine-learning evaluation artifacts by: computing a local qualification with a closed result type excluding a terminal release value; operating a verifier at an independently pinned revision in a governance publisher repository separate from a candidate repository under identities, trust revisions, and a closed release policy fixed outside a candidate tree to evaluate immutable candidate and export snapshots; authenticating instrument-specific group dispositions against a producer-role threshold of distinct externally enrolled principals and then an approver-role threshold excluding those producer principals; requiring for each exported bundle an authorized execution receipt containing a single outcome for each policy-required control under a common manifest closure digest with neither duplicate nor additional control outcomes; permitting terminal release authorization only upon acceptance of the snapshots, dispositions, and receipts; and preventing the verifier from executing the benchmark.

*Drafting note (28):* The medium stores instructions implementing the same concrete architecture, not policy prose alone. The claim form does not establish eligibility by itself. Preserve the processor actions and inability to execute the benchmark in the authorization context.

## §101 Alice positioning

Step 2A Prong Two anchors for claims 1, 27, and 28 are the prevention-register verbs in application section 8.12: excludes a local terminal constructor; pins and compares immutable release subjects; authenticates and counts enrolled principals; excludes producers from approval; refuses incomplete control coverage; and prevents benchmark execution by the verifier. These actions control whether the computer produces a terminal release authorization for executable bytes.

Claims 2 through 5 add record-copy, complete snapshot, governance-pin, and distinct-principal checks. The relevant effect is denial of release authority to changed bytes or unauthorized signers, not a more persuasive report or a different management hierarchy.

Claims 6 through 10 preserve payload bytes, authenticate partial status, compare typed domains, and refuse copied envelopes. Claims 11 through 19 and 26 enumerate specific receipt failures and the limited applicability exception. The computer's refusal to produce an accepted terminal result provides the operational anchor.

Claims 20 and 21 bind measurement carriers and refuse incompatible legacy schemas. Claims 22 through 25 parse carriers before subprocess access, retain transmitted messages, include the terminating byte in cryptographic inputs, and compare project-scoped audiences. These are concrete authorization-path and data-representation constraints rather than generic use of cryptography.

Step 2B rests on the ordered combination, not any single known primitive. TUF, in-toto, SLSA, and Sigstore create substantial headwinds against broad claims to external approval or multi-signature release. The framing must explain how the coupled incapacities and exact receipt relation change the computer's operation, without claiming a measured security improvement that the evidence does not establish.

## EPO technical effect

Under Article 52 and Guidelines G-II 3.3 and 3.3.1, claims 1, 27, and 28 address cryptographic release control over executable evaluation artifacts. Their specific technical purpose is preventing unauthorized release bypass through candidate-controlled state, mutable subject substitution, incomplete observation carriers, or execution of candidate code in the authorization context.

Hashing, canonicalization, principal-set comparison, and control-set equality serve integrity and access-control purposes. They do not claim a mathematical result in isolation. The machine-learning benchmark is the controlled executable subject; no generic model-accuracy improvement supplies the technical contribution.

For claims 20 through 25, the technical purposes are preserving execution-configuration identity, rejecting incompatible evidence, preventing forbidden signing interfaces from invocation, retaining exact cryptographic message bytes, and restricting evidence to its intended project. Human adequacy judgments and organizational enrollment duties remain outside the asserted automated proof.

## India s.3(k) technical effect

For independent claim 1, the technical problem is candidate-controlled self-release and substitution of the export after local checks. In the Ferid Allani and Microsoft v. Assistant Controller vocabulary, the technical solution is a processor-enforced split between nonterminal qualification and externally pinned authorization, coupled to disjoint-principal thresholds and complete control receipts. A measurable technical benefit would be refusal of altered snapshots and unauthorized terminal records under defined attack inputs. No novel hardware is required, and no measured refusal rate is asserted.

For independent claim 27, the technical problem is an authorization path that accepts mutable subjects or missing execution observations. The technical solution is an ordered computer method that pins immutable subjects, authenticates external principal roles, verifies exact receipt coverage, and prevents the verifier from running candidate code. A measurable technical benefit would be deterministic blocking of those bypass inputs and absence of benchmark invocation in the verifier. No novel hardware is required; the contribution lies in operation of the computing system rather than an administrative approval method.

For independent claim 28, the technical problem is software that permits semantic rewriting or local eligibility to become apparent release authority. The technical solution is stored executable instructions implementing the same capability split, typed disposition authentication, and closed receipt gate. A measurable technical benefit would be reproducible exclusion of unauthorized terminal transitions on fixed input bytes. No novel hardware is required, and the medium form remains subject to examination of the technical contribution rather than an assumption that storage alone avoids s.3(k).

## Obviousness posture

vs TUF offline/online role separation + the PSF TUF runbook: combination yields separated metadata authority and threshold ceremonies but not the claimed local qualification result type joined to benchmark-control receipts and a publisher verifier that cannot execute the benchmark. TUF is the strongest single architectural analog; incapacity to self-authorize alone is not a safe novelty position.

vs in-toto layouts and functionaries + SLSA Source two-party review and Build L3 provenance protection: combination yields role-scoped attestations, alias-resistant review, and signing secrets inaccessible to builds but not necessarily instrument-specific group dispositions with exact-payload resumption, preceding-schema byte preservation, and the complete apex receipt gate.

vs Sigstore cosign + Connaisseur: combination yields independent signature attachment and threshold admission but not necessarily producer-first exclusion over externally enrolled principal sets, immutable candidate and export binding, and copied-schema refusal within this protocol. No-key-sharing accumulation and threshold configuration are admitted close teachings, not independent inventions here.

vs in-toto `apt-transport-in-toto` + Debian `rebuilderd` and `reproduce.debian.net`: combination yields out-of-band reproducibility corroboration and rebuilder thresholds but not the claimed local terminal incapacity combined with exact evaluation-control outcomes and a non-executing publisher verifier. Rebuilding and verifying a signed observation are different operations; the comparison does not claim that rebuilders never execute build tools.

vs Debian `.buildinfo` and `debrebuild` + in-toto attestation links: combination yields toolchain-bound, signable artifact evidence but not exact required-control coverage under a common manifest closure with judge-only non-applicability and mandatory execution fidelity. Receipt-per-artifact granularity alone is close prior art.

vs MLPerf submission rules + MLPerf audit guidelines and inference rules: combination yields external review, objections, confidentiality, and independent reruns but not a cryptographic publisher verifier forbidden to rerun the benchmark or a closed machine gate that rejects waivers and all other non-passing control classes. The audit rerun is an important difference, not evidence that MLPerf teaches verifier non-execution.

vs SLSA provenance + US12192372 / EP4280543A1 or WO2025166192A1: combination yields provenance for AI assessments and verifiable benchmark-related evidence but not necessarily the claimed receipt-linked configuration, telemetry, group-conformance, and version-refusal protocol. US11843522 adds hidden benchmark certification rather than the complete release-authority sequence. A claim-by-claim human read remains necessary before filing.

vs OpenSSH SSHSIG, `PROTOCOL.sshsig`, and `draft-josefsson-sshsig-format-04` + OpenSSH FIDO2/U2F algorithm identifiers and `PubkeyAcceptedAlgorithms`: combination yields namespace binding and algorithm-filtered key admission but not necessarily bounded inspection across all specified carriers before subprocess invocation in the claimed release protocol. Reversing hardware-preferred policy to software-only policy may be an obvious choice; carrier coverage and ordering carry the narrower fallback.

vs RFC 8785 + Sigstore canonicalization: combination yields canonical signed representations but not the profile's terminal byte inside each digest and signature input together with retained-payload compatibility and assembly. Authenticode adds prior art for deliberate hash-domain inclusion and exclusion. A delimiter extension alone remains vulnerable to a predictable-variation argument.

vs RFC 8707 + RFC 9068: combination yields resource-bound authorization and rejection of audience mismatch but not an authority-relative project path whose digest identifies policy and whose value survives relocation of the entire authority tree. Keep the canonical-path construction and trust boundary rather than claiming audiences in general.

vs US20220121479A1 + TUF: combination yields access-controlled pipeline gates and threshold authority but not necessarily the closed local nonterminal mint type with the exact receipt protocol. The saved register supplies the title "Configuring DevOps Pipelines Using Access Controlled Gates And Thresholds"; agent-verified 2026-09-21 on Google Patents as an Opsera application published 2022-04-21 and since abandoned, cited as a publication only.

vs US12572354 + SLSA: combination yields centrally owned CI/CD templates and security thresholds with separated duties but not necessarily exact-payload disposition assembly and per-control closure checks. The saved title is "CI/CD template framework for DevSecOps teams"; agent-verified 2026-09-21 on Google Patents as Citizant Inc, granted 2026-03-10.

vs US12430425 + MLPerf external review: combination yields automated pipeline risk classification followed by external approval but not deterministic cryptographic receipt-set acceptance by a verifier forbidden to execute. The saved title is "Continuous integration and continuous deployment pipeline security"; agent-verified 2026-09-21 on Google Patents as IBM, granted 2025-09-30.

Every Group 3 item from the saved lane output participates in the preceding comparisons. These positions use the local register, not a new search or an assertion of exhaustive prior-art coverage. Counsel should test the full ordered combination and narrower fallbacks against the actual references, including motivation to combine.

## Design-around foreclosures

1. Local terminal text: claim 1 excludes terminal release from the qualification result type, and claim 2 refuses a report above its bound record. The specification distinguishes arbitrary text from an externally accepted authorization.
2. Candidate-selected verifier: claims 3 and 4 bind complete snapshots and external governance pins. Merely placing a trust directory outside the checkout does not establish independent control over it.
3. Threshold by key count: claim 5 counts distinct current enrolled principals, and claim 1 excludes producer principals from approval. Alias-resistant enrollment remains a governance assumption, not an inference from strings alone.
4. One signing session or shared keys: claims 6 through 8 preserve the message across sessions and assemble without private keys. Serialization of the envelope container cannot authorize changed payload bytes.
5. Silent version upgrade: claims 9, 10, and 21 distinguish exact old disposition acceptance, typed domain separation, and refusal of obsolete receipt-policy versions. No migration grants authority to changed bytes.
6. Checklist coercion: claims 11 through 17 refuse each outcome class separately. Claim 18 permits a judge exception only through trusted policy, and claim 19 denies that exception to execution fidelity.
7. Run missing controls inside the publisher: independent claims 1, 27, and 28 prevent benchmark execution by the verifier. A receipt gap remains a refusal, not an execution request under privileged credentials.
8. Cosmetic software-key declaration: claim 22 requires embedded-carrier inspection before subprocess or device discovery. It does not claim to identify concealed hardware behind an ordinary software-form external service.
9. Strip the terminator before verification: claim 23 places the byte inside the cryptographic input and authenticates the retained message. Claim 24 adds input-domain and parser-bound fallbacks.
10. Host-specific audience: claim 25 preserves identity under movement of the complete authority tree, not arbitrary renaming. Audience, schema, instrument, and snapshot bindings remain separate checks.

## ENFORCED and PROSPECTIVE map

| Mechanism | Claims | Evidence class | Evidence (tools/tests or contract line or DEFERRED row) |
| --- | --- | --- | --- |
| Local nonterminal mint and report mismatch | 1, 2, 27, 28 | ENFORCED | tools/gate.py, first landed 2026-09-16; tests/test_gate.py; tools/sabotage.py, first landed 2026-09-16; tests/test_sabotage.py |
| Verbatim report-source rule | 2 | CONTRACT-ONLY for the full rendering obligation | ENGRAM.md:69, 71; mismatch checks do not alone prove every renderer |
| Snapshot and identity comparison | 1, 3, 4, 27, 28 | ENFORCED | tools/release.py, first landed 2026-09-16; tests/test_release.py; tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py |
| Independent publisher administration and immutable input presentation | 1, 4, 27, 28 | DEFERRED; integrated deployment PROSPECTIVE | DEFERRED.md: "Externally governed publisher evaluates immutable snapshots"; "Candidate `gate.py install` cannot establish or prove this deployment" |
| Group threshold and principal exclusion | 1, 5, 27, 28 | ENFORCED | tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py; tools/attest/trustroot.py, first landed 2026-08-26; tests/test_attest_trustroot.py |
| Partial accumulation, status, and exact assembly | 6, 7, 8 | ENFORCED | tools/gate.py, first landed 2026-09-16; tests/test_gate.py |
| External enrollment and key-to-human binding | 1, 5, 6, 7, 8, 27, 28 | CONTRACT-ONLY (ENGRAM.md:73); key-to-human binding DEFERRED | DEFERRED.md: "the trust root names principals, nothing here proves a principal is a distinct person" |
| Retained payload and typed-domain refusal | 9, 10, 23 | ENFORCED | tools/attest/dsse.py, first landed 2026-08-26; tests/test_attest_dsse.py; tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py |
| Exact control outcomes and trusted applicability | 11 through 19, 26 | ENFORCED | tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py |
| External observations and control execution | 1, 11 through 20, 26, 27, 28 | DEFERRED | DEFERRED.md: "External execution service produces accepted oracle receipts"; "that runner remains absent" |
| Benchmark non-execution in verifier design | 1, 27, 28 | CONTRACT-ONLY; deployed isolation PROSPECTIVE | ENGRAM.md:71; application section 8.6 distinguishes verification from external execution |
| Harness configuration and pilot conformance validators | 20 | ENFORCED | tools/harness_config.py, first landed 2026-09-18; tests/test_harness_config.py; tools/pilot.py, first landed 2026-09-03; tests/test_pilot.py |
| Execution telemetry and release fidelity policy | 20 | ENFORCED | tools/attest/execution_v2.py, first landed 2026-09-18; tools/attest/policies/execution_fidelity.py, first landed 2026-09-18; tests/test_attest_execution_policy.py |
| Adequacy judgment and complete evidence cross-binding | 20 | DEFERRED | DEFERRED.md: "Configuration adequacy judged by a governance authority"; "Only the execution-attestation and authenticated roster cross-binding remains deferred" |
| Receipt-policy downgrade refusal | 21 | ENFORCED | tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py |
| Software-carrier parsing before subprocess | 22 | ENFORCED; broader custody rule CONTRACT-ONLY | tools/attest/backend_ssh.py, first landed 2026-08-26; tests/test_attest_backend.py; ENGRAM.md:75 |
| Canonical serialization and text parser limits | 23, 24 | ENFORCED | tools/attest/canonical.py, first landed 2026-08-26; tests/test_attest_canonical.py; docs/canonical-bytes.md |
| Canonical path containment | 25 | ENFORCED | tools/project_paths.py, first landed 2026-09-16; tests/test_project_paths.py |
| Audience construction and digest-keyed policy selection | 25 | CONTRACT-ONLY in this evidence map; external producer operation PROSPECTIVE | README paragraph "Every authored path starts at `./`"; role authorization in tools/attest/trustroot.py is a separate predicate |

First-landed dates identify module additions, not deployment dates or dates for every current feature. The evidence classes do not assert that any publisher, external execution service, or quality-controls runner operates. A hypothetical complete deployment is not interchangeable with the available verifier-side code.

## §112 / drafting cautions

Avoid unexplained functional placeholders such as "controller configured to" that could invoke 112(f) concerns under Williamson v. Citrix. The specification supplies processors, memories, typed records, set comparisons, byte comparisons, role exclusion, and signature-carrier parsing as corresponding implementation detail. Counsel should check the final claim syntax rather than relying on labels to avoid means-plus-function treatment.

Maintain antecedent basis for candidate and export snapshots, the verifier, each group disposition, the producer principals, and the required control set. A common manifest closure is the recomputed digest of outcome bodies excluding their own closure fields, not a circular hash or a free-form label.

Define terminal incapacity at the local qualification path. Proposed final-record creation and untrusted terminal-looking prose do not contradict it because neither grants publisher acceptance. The external trust store must lie outside candidate write authority, not merely outside a named subdirectory.

Keep the absence of benchmark execution distinct from absence of every subprocess. The verifier may invoke a trusted signature backend or safe metadata reader without executing candidate benchmark code. Deployment isolation remains prospective and must not silently acquire an implemented-status label.

Keep exact-payload assembly distinct from final cryptographic authorization. The assembler compares payload type and bytes and rejects duplicate signature entries; status and publisher verification authenticate principals and evaluate thresholds. Do not claim the assembler proves a quorum merely because it writes an envelope.

Compatibility accepts existing signed disposition bytes as their own message. A deliberately selected named-principal promotion form is separate from verification dispatch. Receipt and release-policy version refusal has no legacy path. Counsel should avoid broad phrasing that conflates these behaviors.

Retain the distinction between binary64 programmatic integer validation and parsed-number semantics. The text parser's depth bound does not redefine RFC 8785, and canonical-conformity comparison does not mean signature verification over a reserialization. The terminating byte is part of the claimed profile's signed input.

Carrier parsing constrains the accepted backend interfaces and identifiable key formats. It cannot prove remote physical custody or a principal's human uniqueness. Claims should not promise those properties without further supported mechanisms.

The specification treats labels, paths, refusal codes, schemas, role names, and illustrative numerals as examples. Functional uniqueness and threshold relations remain meaningful limitations. Maintain the single-actor formulation while preserving administrative separation within the operator's system.

The set contains 28 claims with three independent claims. Counsel should assess excess-claim costs, unity, restriction, double patenting, and parent support before filing. A divisional safe harbor depends on an actual restriction and consonance, not this drafting label. No filing route or legal outcome is represented as complete.

The drafting party reconciles and never files. Filing, publication beyond the repository, operational acceptance, and calibration admission remain human acts. No statement here asserts a filing, service deployment, benchmark execution result, or measured pass rate.
