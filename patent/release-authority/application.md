# UNITED STATES NON-PROVISIONAL UTILITY PATENT APPLICATION

**Filed under 35 U.S.C. § 111(a)**

**Title:** Externally Governed Release Authority with Threshold Dispositions, Control Receipts, and Software-Only Signing for Machine-Learning Evaluation Artifacts

**Inventor:** Sarvex Jatasra

**Applicant / Assignee:** Ethara.AI

**Docket Reference:** Trinity/release-authority

---

## 1. TITLE OF THE INVENTION

Externally Governed Release Authority with Threshold Dispositions, Control Receipts, and Software-Only Signing for Machine-Learning Evaluation Artifacts

## 2. CROSS-REFERENCE TO RELATED APPLICATIONS

The related disclosure is entitled "Cryptographically Controlled Certification of Machine-Learning Evaluation Tasks Using Isolated Generation, Audit, and Evidence Domains." Its filing is prospective. This application is intended as a divisional or continuation of that disclosure, with the choice left to the human filing decision. The relationship concerns the parent's sections 8.13, 8.37, and 8.39 and proposed claim 35; the present description supplies the release protocol without requiring those sections to complete it.

No application number, priority date, restriction requirement, or entitlement to a statutory safe harbor is asserted. Counsel must confirm support, continuity, inventorship, and any restriction before choosing a filing route. The statutory title-block legend denotes the intended application form, not an accomplished filing.

## 3. STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

## 4. FIELD OF THE INVENTION

The disclosure concerns cryptographic release control for executable machine-learning evaluation artifacts. It concerns distinct local qualification and external authorization capabilities, immutable artifact bindings, principal-based threshold signatures, closed execution-control receipts, bounded signature-carrier parsing, and byte-preserving verification. The computer controls whether an artifact obtains release authority; it does not merely display a recommendation about benchmark quality.

## 5. BACKGROUND OF THE INVENTION

A first deficiency is self-authorization by a candidate workspace. A local checker that can emit the same terminal value as the publisher permits a modified report, local trust root, or replaced checker to masquerade as final authority. Administrative instructions not to self-approve do not remove that capability.

A second deficiency is verification against mutable or incomplete subjects. A signature over task identity alone need not cover export-only files, file modes, or the candidate revision. Replacing any omitted bytes can preserve a valid signature while changing the material a consumer receives.

A third deficiency is substituting signature quantity for authority. Repeated signatures, aliases, or several keys belonging to one principal can resemble a quorum. A threshold must count distinct authenticated principals in externally controlled roles and must exclude producer principals from approval.

A fourth deficiency is treating a valid signature as proof of complete execution. An authentic receipt can omit a required negative control, mark a control skipped, duplicate a favorable row, or include outcomes from different evidence closures. Signature validity alone does not distinguish these defects.

A fifth deficiency is executing an untrusted benchmark inside the component that holds release authority. Such execution lets candidate programs interact with an authorization environment. Independent execution evidence can support verification without granting the release verifier a benchmark-execution function.

A sixth deficiency is semantic rewriting of signed records. Converting an old signed payload into a current schema, reordering its fields, or rebuilding it from parsed values changes the signed message. Signatures over the earlier bytes cannot approve the replacement representation.

A seventh deficiency is enforcing software-key custody only through a command-line algorithm label. A carrier can contain an embedded key type different from an outer label. Device discovery or a signing subprocess can occur before the program discovers that the embedded key violates its policy.

An eighth deficiency is ambiguity in byte termination and audience naming. A producer that signs a trailing line feed and a verifier that drops it sign different messages. An audience containing a host's absolute directory can also change when the same governed authority tree moves to another host.

TUF, in-toto, SLSA, Sigstore, and independent benchmark audits provide substantial relevant teachings. Section 8.11 identifies their overlap rather than treating signature thresholds, external review, canonical JSON, or separated duties as new primitives. The proposed distinction lies in the ordered release protocol and its specific refusals.

## 6. SUMMARY OF THE INVENTION

A local qualification routine has a closed result type that excludes terminal release. Its machine record, not authored prose, supplies report standing. A separate governance publisher evaluates immutable candidate and export snapshots using verifier and trust revisions that the candidate cannot choose. The verifier treats candidate bytes as data and does not execute the benchmark.

For each required instrument disposition, the verifier authenticates signatures over a typed payload and evaluates externally enrolled producer principals before a disjoint approver set. It requires the applicable role thresholds rather than a raw signature count. An assembler accumulates signatures over exactly matching payload bytes across sessions without receiving private keys.

For each bundle, an authorized execution receipt must cover every policy-required control exactly once under a common manifest closure. Missing or non-passing evidence prevents terminal authorization. The policy can declare only a judge control non-applicable; execution fidelity remains mandatory. Configuration, execution telemetry, and pilot-conformance carriers constrain the evidence accepted by the corresponding validators.

Further embodiments parse software-signing carriers before invoking cryptographic subprocesses, include a terminating line feed inside the signed canonical payload, and bind external evidence to a canonical project-relative audience. Existing accepted disposition versions retain their signed bytes; that compatibility does not create a route for superseded receipt or release-policy schemas.

The disclosure separates implemented validation predicates from operational prerequisites. No deployment of a publisher, external execution service, or quality-controls runner is established. The integrated deployment remains PROSPECTIVE, and the relevant DEFERRED entries remain blockers rather than implied successful execution.

## 7. BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 depicts a candidate workspace containing a local qualification routine, separate governance storage containing pinned trust and verifier revisions, and a publisher receiving immutable candidate and export snapshots as data. The local result type excludes terminal release.

FIG. 2 depicts a disposition payload shared by separate signing sessions, exact-byte partial-envelope assembly, authenticated principal recovery, producer-threshold evaluation, and approver-threshold evaluation after exclusion of producer principals.

FIG. 3 depicts a closed policy, a per-bundle execution receipt, a required-control set, exact coverage comparison, common closure recomputation, and rejection paths that prevent publication without executing candidate programs.

FIG. 4 depicts configuration adequacy, per-rollout telemetry, pilot membership and conformance, and fidelity-ledger bindings beside the receipt. Dashed connections denote external observation and cross-artifact services whose deployment remains unestablished.

FIG. 5 depicts bounded private-key, signature, and signer-policy carriers entering software-only algorithm checks before any signing or verification subprocess. It also depicts typed payload framing that prevents reuse across instrument domains.

FIG. 6 depicts canonical JSON production with its terminating byte, verification over the retained transmitted payload, and a project-relative audience that remains unchanged when the enclosing authority tree moves without changing its relative layout.

## 8. DETAILED DESCRIPTION OF THE INVENTION

### 8.1 Overview

The system uses processors, non-transitory memory, candidate storage, an externally administered trust store, a signature backend, and a release verifier. A candidate contains executable task bytes and evidence offered in support of release. A local routine computes qualification. A separately governed publisher would invoke the trusted verifier and expose a release result only after all required checks accept.

The threat model includes a candidate operator who can edit the checkout, root reports, local configuration, and apparent release strings. Such edits cannot confer the external publisher's authority. The model does not assume that a Python function can stop an administrator from editing arbitrary files on an unrestricted host. Instead, terminal authorization depends on checks and credentials outside that administrator's candidate-controlled domain.

In one implementation, author and auditor dispositions correspond to FORGE and CRUCIBLE, while ENGRAM maintains memory. Those names identify protocol domains, not separate legal persons. Both author and auditor dispositions must validate for a release. A local command may prepare proposed final-record bytes, but those bytes acquire no release authority merely because the command writes a terminal-looking field.

Implementation labels describe available predicates and their tests, not execution results from this drafting pass. First-landed dates below identify the earliest addition of the named module, not the first implementation date of every current feature. Operational boundaries carry separate contract, deferred, or prospective labels.

### 8.2 Definitions

A local qualification routine is the code path that maps local findings to a closed nonterminal result type. Structural incapacity to mint terminal release means that this path has no terminal result constructor and no authority to satisfy the publisher's terminal acceptance conditions. It does not mean that an untrusted user cannot type the same word into an unrelated file.

A release-eligible qualification value means that local qualification permits submission for external authorization. It is not terminal release, an execution receipt, or an authorization waiver. A report ceiling means the greatest standing that the bound machine record permits that report to express.

A governance publisher is a repository and execution context whose administration fixes trusted repository identities, verifier revision, trust revision, signer policy, and release policy outside the candidate tree. An external trust store is external to candidate write authority, even where the same legal operator administers both environments through distinct principals.

An immutable snapshot is a byte set bound to an immutable revision and checked digest, presented without candidate-controlled mutation during verification. A complete export snapshot digest commits to the export's enumerated files and relevant metadata. A canonical bundle-set identity separately commits to the collection of bundle identities; the latter is not a substitute for the former.

An externally enrolled principal is an authenticated signing identity whose enrollment and role membership reside in a trust root the candidate cannot write. A role threshold is a positive required count of distinct eligible principals for a role at the evaluation instant. Duplicate identities do not increase the count, and expired or revoked principals do not contribute.

A group disposition is a closed-schema release record with instrument-specific payload typing and role-based authorization. Producer-first evaluation identifies eligible producer signers, then excludes them from the approver count. This is an authorization order, not a requirement that every producer physically sign before every approver.

An exact-payload partial is an envelope containing signatures over the same decoded payload bytes and payload type as the target record. Assembly preserves that payload and adds signatures; it does not reconstruct a message from semantically equivalent parsed fields. The outer envelope representation may change while the signed payload remains identical.

A control receipt is an externally signed observation carrier for one bundle. A closed release policy enumerates required controls and allowed statuses. Exact coverage means that the receipt's control identifiers equal the required set with no duplicates. A manifest closure digest commits to the control outcome bodies and their evidence bindings without circularly hashing their own closure fields.

An execution-fidelity control addresses whether the evidence supports faithful execution under the declared configuration and population. A non-applicable designation is a policy-authorized outcome for a particular control, not a missing row. A non-executing verifier validates signatures, structures, identities, and digests without launching the benchmark, its harness, or its scoring programs.

A software-only signing policy accepts only the supported software-key carrier forms and excludes hardware-key or device-discovery paths. Carrier parsing establishes conformity to those representations and interfaces; it cannot prove the physical custody of an ordinary-looking key held by an opaque external service.

A canonical-path audience is the canonical path of the audited project relative to a trusted authority root, with an explicit relative-root prefix. Relocation invariance means preservation under movement of the whole authority tree with the same relative layout, not equivalence across arbitrary project renames or different authorities.

### 8.3 Local qualification with an unreachable terminal value

In one implementation, the local gate mints only BLOCK, HOLD, and SHIP_ELIGIBLE. Its ceiling mapping contains no SHIP result. The run-scoped machine record uses `trinity.qualification/v2` and binds an instrument, run identity, subject-closure digest, governing revision, and computed disposition. A successful local qualification therefore remains a nonterminal result.

The routine derives qualification from findings rather than accepting a caller's desired terminal token. A subject-closure binding permits an unrelated commit outside that closure without treating it as approval of altered subject bytes. A separate final disposition binds an immutable candidate commit and export snapshot; the two identities serve different stages.

The root report's disposition line copies the applicable minted machine record verbatim. The reporting contract does not let a prose author reinterpret eligibility as release. In one implementation, a report token above its record triggers `SAB_DISPOSITION_UNBOUND` or the corresponding gate mismatch refusal. A stricter report token cannot manufacture terminal authority either.

For example, a clean local record with a release-eligible result does not support a terminal token pasted into a root report. The report check would refuse the mismatch, and the publisher would independently require signed final dispositions and execution receipts. These checks address different bypass points.

The final-record preparation interface is not an exception to the qualification ceiling. It prepares the message external principals may sign. Without valid external role authorization, that message remains candidate data. The disclosure confines structural incapacity to authorized state transitions, not to the ability to write arbitrary text.

In one implementation, the gate preserves existing record bytes while their bound subject and ceiling remain current. Avoiding gratuitous record changes prevents later local invocations from destroying the message on which partial signing sessions depend.

The minting and mismatch predicates are ENFORCED (tools/gate.py, first landed 2026-09-16; tests/test_gate.py) and ENFORCED (tools/sabotage.py, first landed 2026-09-16; tests/test_sabotage.py). The verbatim report-source obligation is CONTRACT-ONLY (ENGRAM.md:69, 71) to the extent this disclosure does not establish every reporting path's implementation.

The local gate alone does not establish external release authority. That operational boundary is DEFERRED (DEFERRED.md: "Candidate `gate.py install` cannot establish or prove this deployment").

### 8.4 Separate publisher and immutable release subjects

The governance publisher would reside in a repository distinct from the candidate repository. Governance would fix repository identities and immutable verifier and trust commits there. It would present candidate and export checkouts as immutable snapshots and deny the candidate any choice of verifier, trust directory, policy, or expected identity.

In one implementation, a closed `trinity.release-policy/v3` supplies project identity, repository identity, verifier revision, trust-root version, receipt requirements, and temporal bounds. The verifier rejects candidate-local trust and compares supplied policy identities against governance pins. Its library interface accepts trusted caller inputs; deployment must ensure that the candidate operator does not control those inputs.

The release record binds the complete export snapshot digest, canonical bundle-set identity, immutable candidate commit, repository identity, project identity, and trusted verifier revision. A bundle digest alone does not bind every export byte. Both the export representation and the canonical bundle identities participate in acceptance.

The export manifest records paths, content digests, and executable-bit identity. Thus a content substitution, an added file, or a relevant mode change changes the snapshot commitment even if the logical bundle list does not change. Unsafe tree members and a release with no bundle population do not provide an alternative acceptance route.

The verifier compares the signed snapshot and candidate bindings against the actual immutable inputs. Later movement of a branch neither extends an earlier release to new bytes nor changes the old signed candidate identity. A new candidate requires validation and signatures that bind its own bytes.

In one implementation, `gate.py install` installs local qualification surfaces only. It does not install the separate publisher workflow or credentials. A local installation receipt and a local scaffold comparison cannot prove independent administration, protected variables, immutable mounts, or control of a publisher account.

The input-binding and release predicates are ENFORCED (tools/release.py, first landed 2026-09-16; tests/test_release.py) and ENFORCED (tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py). The external architecture is CONTRACT-ONLY (ENGRAM.md:71).

Publisher operation remains DEFERRED (DEFERRED.md: "Externally governed publisher evaluates immutable snapshots"; "publisher deployment remain external governance work"). Immutable presentation and exclusion of operator-selected deployment inputs are PROSPECTIVE operational requirements, not an asserted installation.

### 8.5 Threshold dispositions and resumable exact-payload signing

In one implementation, new promotions use `trinity.release-disposition/v3`. Each instrument has a separate payload type, and the closed record binds project, repository, snapshot, candidate, verifier, issue time, expiry time, and producer and approver roles. Human governance enrolls software-key principals and fixes positive thresholds outside the candidate.

In one implementation, the roles are `gate_producer` and `gate_approver`, and a policy may require 2-of-N for either role. The verifier first authenticates signatures, resolves the resulting identities against the external producer role, and then evaluates the approver role after excluding producer principals. Duplicating signatures or presenting multiple keys for one principal cannot satisfy a distinct-principal threshold.

The verifier checks trust-root version, root expiry, principal expiry, and revocation at a declared evaluation instant. A signature's historical validity does not grandfather a now-ineligible principal. Group signer-policy checks also constrain ambiguous identity mappings. Enrollment must still establish the intended relationship between a principal and its custodian; cryptography alone does not prove distinct human persons.

In one implementation, `sign-partial` lets each enrolled principal sign the same frozen record using that principal's software private key. Each session writes a partial envelope. No participant supplies a private key to another participant or to the assembler. Candidate validation precedes the signing key access path.

In one implementation, `signing-status` authenticates persisted partials and reports each role's threshold, eligible principals, missing count, and completion. A combined completion value requires both roles. A status report does not replace final authorization, and a filename claiming an approver does not count without signature authentication.

In one implementation, `cosign-assemble` starts from the existing exact-payload envelope when present and combines supplied matching partials. It requires equality of payload bytes and payload type, refuses duplicate signature entries, and preserves the payload while writing the combined envelope. Assembly itself is not proof of threshold completion; verification and authorization remain separate checks.

Existing valid `trinity.release-disposition/v2` payload bytes remain acceptable under their own named-principal rules. In one implementation, explicit `gate.py promote --approver NAME` selects that compatibility path. Compatibility neither reserializes existing signed bytes nor treats them as signatures over a newer schema. Copying an author envelope into an auditor slot, or copying a preceding-schema envelope into the group-schema domain, fails typed verification.

The signing and assembly behavior is ENFORCED (tools/gate.py, first landed 2026-09-16; tests/test_gate.py). Group and compatibility authorization is ENFORCED (tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py). Byte-preserving signature verification is ENFORCED (tools/attest/dsse.py, first landed 2026-08-26; tests/test_attest_dsse.py).

Principal thresholds and exclusions are ENFORCED (tools/attest/trustroot.py, first landed 2026-08-26; tests/test_attest_trustroot.py). External enrollment and the intended collaboration procedure are CONTRACT-ONLY (ENGRAM.md:71, 73); key-to-human binding remains DEFERRED (DEFERRED.md: "the trust root names principals, nothing here proves a principal is a distinct person"). These labels do not establish deployed enrollment ceremonies or custody services.

### 8.6 Closed control receipts with a non-executing verifier

In one implementation, each bundle requires an authorized `trinity.oracle-run/v4` receipt under closed `trinity.release-policy/v3`. The verifier authenticates the receipt's execution signer against external trust and validates the task and bundle identity, environment pins, time window, run identities, reward bounds, and control coverage. The signer remains trusted to observe what the receipt asserts.

The policy requires six core control families, expressed generically as build assets and harness; oracle behavior with no-op, known-wrong, and adversary integrity; alternate correct solution with mutant ladder, grading, and instruction scope; judge completeness and repeatability; trial and reward accounting; and execution fidelity. A policy may require further controls, but the receipt must then cover that exact enlarged set.

The verifier checks identifier-set equality and uniqueness before accepting control outcomes. Every outcome binds the same bundle and verifier revision. It recomputes one manifest closure from ordered control bodies with their closure fields excluded and requires every row to name that closure. An outcome from a different observation set cannot substitute merely because its control name matches.

Missing, failed, skipped, deferred, waived, duplicate, or extra outcomes each refuse release. A missing row fails coverage; a duplicate fails uniqueness; an extra row fails set equality; and a non-passing status fails the policy's permitted-status comparison. A signature over any such malformed collection does not cure it.

Only trusted policy may mark the judge control non-applicable, and the receipt still contains its outcome row. Candidate prose, an execution signer acting alone, or an operator argument cannot grant that exception. Execution fidelity is never non-applicable, and policy parsing rejects a purported exception for it.

In one implementation, the fidelity outcome binds the canonical forensic ledger digest and rejects empty, blocked, or nonconforming evidence. The refusal family includes `ORACLE_FIDELITY_DIGEST_MISMATCH` and `ORACLE_FIDELITY_REFUSED`. Receipt-to-ledger comparison does not by itself establish the separate execution-attestation and authenticated-roster cross-binding.

The verifier never executes the benchmark. It parses data, recomputes digests, authenticates signatures, and decides acceptance. A missing receipt does not trigger an execution fallback. A publisher deployment would deny candidate execution capability in its authorization environment, rather than allowing candidate harness code to inherit publisher credentials.

Receipt and policy predicates are ENFORCED (tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py). Release-specific execution-fidelity validation is ENFORCED (tools/attest/policies/execution_fidelity.py, first landed 2026-09-18; tests/test_attest_execution_policy.py). The no-execution architectural obligation is CONTRACT-ONLY (ENGRAM.md:71); deployed capability isolation is PROSPECTIVE.

External production remains DEFERRED (DEFERRED.md: "External execution service produces accepted oracle receipts"; "A separately governed quality-controls runner must execute the immutable bundle, run every control, and sign the resulting observation; that runner remains absent"). The unresolved cross-binding remains DEFERRED (DEFERRED.md: "Only the execution-attestation and authenticated roster cross-binding remains deferred").

### 8.7 Measurement-fidelity carriers and closed version boundaries

In one implementation, `trinity.harness-config/v1` pins the effective harness configuration beside a separate configuration-adequacy judgment. The configuration includes declared model and harness identities, context and output limits, timeout, sampling settings, prompt identity, sandbox, and policy fields. Shape validity, approval, adequacy, and agreement with effective execution are distinct questions.

The configuration validator refuses absent or unknown fields, ambiguous model identity, invalid limits, and a missing adequacy block. Comparison with an approved configuration and execution evidence would detect drift. A declaration that headroom is adequate is not an empirical proof that the configuration supports the task's full horizon.

In one implementation, `trinity.execution/v2` carries per-rollout telemetry for turns, context events, termination reason, and provider errors. It binds configuration, effective-configuration reconciliation, population roster, observation capture, and the trajectory population. Its parser requires telemetry identities to match duration identities; release policy also compares the telemetry population with the committed trajectory manifest.

In one implementation, `trinity.pilot-policy/v2` and `trinity.pilot-attempt/v2` carry predeclared disjoint groups, configuration and evidence digests, and per-rollout conformance tokens. The tokens distinguish conforming, nonconforming, and indeterminate standing. A missing or unproved group does not silently reduce the fixed population used for a release bound.

These carriers sit beside and bind the receipt's measurement-fidelity evidence, rather than letting an attractive aggregate score substitute for faithful execution. The available validators check their respective structures and supplied bindings. The disclosure does not infer an end-to-end observer or automatic publisher resolution of every collateral resource merely from the existence of those validators.

In one implementation, the receipt parser refuses superseded `trinity.oracle-run/v3`, and the release-policy parser refuses superseded `trinity.release-policy/v2`. There is no legacy release-acceptance route for either. Governance must issue current policy and obtain current receipts. The disposition-only acceptance of existing signed v2 bytes does not relax these version checks.

Configuration parsing is ENFORCED (tools/harness_config.py, first landed 2026-09-18; tests/test_harness_config.py). Execution telemetry is ENFORCED (tools/attest/execution_v2.py, first landed 2026-09-18; tests/test_attest_execution_policy.py). Pilot conformance is ENFORCED (tools/pilot.py, first landed 2026-09-03; tests/test_pilot.py). Receipt and policy version refusal is ENFORCED (tools/release_evidence.py, first landed 2026-09-16; tests/test_release.py).

External observation remains DEFERRED (DEFERRED.md: "Independent execution authority controls admission, execution, observation, and custody"). Adequacy judgment remains DEFERRED (DEFERRED.md: "Configuration adequacy judged by a governance authority"). The complete deployed measurement chain is PROSPECTIVE.

### 8.8 Software-only signing enforced before subprocess invocation

In one implementation, every signing principal uses a software private key. Hardware security keys, physical tokens, FIDO discovery, and HSM signing interfaces are forbidden. The backend does not attempt device discovery to decide whether a key is permissible.

The backend first bounds and decodes the OpenSSH private-key carrier. It checks its magic, length-prefixed fields, key count, and embedded public-key algorithm. It refuses a forbidden or malformed header before creating a signing subprocess. An outer label cannot override the algorithm embedded in the public blob.

Before verification, the backend bounds and decodes the SSHSIG carrier and inspects both its public key and signature algorithm. It also parses each relevant `allowed_signers` public blob and checks its relationship to the declared algorithm. Unsupported or malformed policy input fails closed before subprocess invocation.

In one implementation, prohibited families include `sk-ssh-ed25519@openssh.com` and `sk-ecdsa-sha2-nistp256@openssh.com`, including their `-cert-v01@openssh.com` forms. A certificate-shaped carrier does not hide an otherwise forbidden security-key algorithm. Resource bounds limit both whole carriers and individual policy lines.

An ordinary software key that passes the parser still must authenticate a current externally enrolled principal. Software form does not grant a role, satisfy a threshold, or permit producer self-approval. The software-only restriction and the authorization policy are independent conjuncts.

The custody claim has a defined limit: parsing reveals what the carrier declares and constrains this backend's execution path. It cannot distinguish a remote service that emits an ordinary software-form signature while hiding its internal implementation. No claim here treats algorithm-name inspection as physical remote attestation.

Carrier refusals and their order before subprocess calls are ENFORCED (tools/attest/backend_ssh.py, first landed 2026-08-26; tests/test_attest_backend.py). The broader ban on hardware custody is CONTRACT-ONLY (ENGRAM.md:75). A universal external-custodian audit would be PROSPECTIVE.

In one implementation, docs/adr/0001-signing-backend.md records the software command backend and the need to layer principal thresholds above signer lookup. Its historical context is not evidence that current verification remains absent, and its backend choice does not establish a deployed signing service.

### 8.9 Canonical bytes and retained-message verification

In one implementation, `trinity.jcs-lf.v1` uses RFC 8785 JSON serialization followed by exactly one terminating line feed. That final byte belongs to every digest and signature input that claims this profile. It is not an unbound transport decoration. In typed envelope signing, the pre-authentication encoding includes the retained payload length and those complete payload bytes.

Object keys follow unsigned UTF-16 code-unit order, strings use UTF-8 output without Unicode normalization, and finite numbers follow the required binary64 serialization rules. Array order remains significant. The normative docs/canonical-bytes.md supplies these rules; the earlier code-point shorthand in docs/adr/0003-canonicalization.md does not replace them.

The producer rejects lone surrogates, non-finite numbers, duplicate object keys, non-string object keys, and cyclic programmatic containers. It rejects programmatic integers that cannot round-trip exactly through finite binary64. Oversized numeric input receives a controlled refusal rather than an unchecked conversion failure.

The bounded text parser rejects nesting past sixty-four levels. This is an implementation resource bound, not an extra requirement of RFC 8785. The normative profile itself distinguishes serialization grammar from deployment resource limits, and programmatic serialization also reports recursion failure rather than asserting an identical text-depth check on every input path.

The integer limit does not mean that every integer above the usual safe interval fails. Some larger integers are exactly representable. Parsed JSON numbers follow binary64 semantics and can round before serialization; applications requiring exact larger integers encode them as strings under a separate schema. This distinction prevents an inaccurate claim that all large textual integers receive rejection.

A verifier authenticates the transmitted decoded payload bytes, never a replacement obtained by parsing and reserializing them. A current-schema validator may separately canonicalize the parsed value and compare it with the transmitted payload to check profile conformity. That comparison does not replace the signed-message input or upgrade historical disposition bytes.

For example, removing the terminal line feed from a profile-conforming signed payload changes its message and its length framing. Reordering source object keys can preserve semantic values but cannot rescue an existing signature over changed bytes. The verifier either validates the retained message under its allowed schema or refuses it.

Canonical serialization and text limits are ENFORCED (tools/attest/canonical.py, first landed 2026-08-26; tests/test_attest_canonical.py). Retained-byte signature verification is ENFORCED (tools/attest/dsse.py, first landed 2026-08-26; tests/test_attest_dsse.py). The profile is documented in docs/canonical-bytes.md and docs/adr/0003-canonicalization.md; these statements do not claim a new cryptographic primitive.

### 8.10 Relocation-invariant canonical-path audience

In one implementation, the trusted orchestrator fixes the authority root from its invocation context. The audited project's canonical `./` path relative to that authority root becomes the gate policy's `expectedAudience`. The SHA-256 of that string keys the policy file. Candidate content cannot choose a different root to reinterpret the audience.

External execution or approval producers sign the same audience string. The verifier compares the signed audience with the expected value in trusted policy independently of signature validity. A valid signature addressed to another project cannot authorize this one.

Path validation requires an explicit relative-root prefix and forward separators and refuses traversal, redundant segments, absolute authored paths, home expansion, and symlink traversal. Absolute resolution remains an internal containment operation, not the persisted audience. External trust and keys remain outside the candidate tree while residing inside the governed authority root.

If the authority tree moves from one host directory to another without changing internal relative locations, the audience string and its policy key remain unchanged. Moving only the candidate to a different relative path does not preserve identity. Likewise, identical relative paths under distinct trust authorities do not merge those authorities.

Audience binding supplements instrument and schema typing. The audience scopes the intended project, while payload typing scopes the operation and instrument. Neither substitutes for snapshot binding or role authorization. All must agree before terminal acceptance.

The path rules are ENFORCED (tools/project_paths.py, first landed 2026-09-16; tests/test_project_paths.py). Role authorization remains ENFORCED (tools/attest/trustroot.py, first landed 2026-08-26; tests/test_attest_trustroot.py), but that module is not itself the audience-policy locator.

The audience construction and SHA-256 policy-key rule follow the README paragraph "Every authored path starts at `./`" as CONTRACT-ONLY for this evidence map. The separate gate-policy and replay interfaces consume that expected string; this subsection does not attribute their behavior to the trust-root parser.

External producers using that audience in operational receipts remain PROSPECTIVE until the external execution and governance services exist. The unresolved service dependency is DEFERRED (DEFERRED.md: "External execution service produces accepted oracle receipts").

### 8.11 Named prior art and novelty residue: TUF and related art

For the local ceiling, the TUF root, targets, snapshot, and timestamp role split and the PSF TUF ceremony runbook are strong analogs for separating online convenience from higher release authority. SLSA Build L3's inaccessible signing material further narrows the distinction. The proposed novelty residue is the closed local nonterminal mint type combined with record-bound reports and receipt-conditioned external terminal acceptance, not separated duties alone.

For the publisher boundary, Debian Reproducible Builds, `rebuilderd`, `reproduce.debian.net`, and in-toto `apt-transport-in-toto` teach independent verification and rebuilder thresholds. MLPerf's audit guidelines and inference rules teach an external auditor that can rerun submission code, which differs from a publisher verifier forbidden to execute the benchmark. Against these references and TUF, the proposed novelty residue is the separately pinned publisher's complete export and candidate bindings coupled to that prohibition and a closed receipt gate.

For group dispositions, in-toto layouts and functionaries already teach authorized step thresholds; SLSA two-party review addresses alternate-identity bypass; Sigstore cosign and Connaisseur teach independently accumulated signatures and configurable admission thresholds. The proposed novelty residue is their particular combination with externally enrolled principal counts, producer exclusion before approval, exact-payload resumable assembly, version-preserving acceptance, and typed domain-copy refusal. No novelty rests on counting signatures or avoiding shared private keys alone.

For control receipts, MLPerf submission rules teach external review, confidentiality, objections, and possible waivers, while its audit rules permit independent reruns. Debian `.buildinfo` and `debrebuild`, together with in-toto rebuilder links, supply close receipt-per-artifact analogs. The proposed novelty residue is exact policy-set coverage under one closure, explicit refusal of every non-passing class, judge-only trusted non-applicability, mandatory fidelity, and a terminal verifier that cannot execute a missing control itself.

For fidelity carriers, SLSA provenance and the in-toto attestation framework bind execution-related facts, and MLPerf rules constrain measurement conditions. US12192372 / EP4280543A1 address provable provenance for AI assessments, WO2025166192A1 concerns a verifiable computing notary for AI benchmarks, and US11843522 addresses model certification with hidden benchmark samples. The proposed novelty residue is the receipt-linked configuration, telemetry, and group-conformance chain with explicit diagnosis versus release version boundaries, subject to the disclosed external-observation gaps.

For software signing, OpenSSH SSHSIG namespace-bound detached signatures, `PROTOCOL.sshsig`, and `draft-josefsson-sshsig-format-04` disclose the carrier structure. OpenSSH FIDO2/U2F security-key algorithms and `PubkeyAcceptedAlgorithms` filtering already disclose algorithm-based acceptance decisions. Against that art and SLSA custody separation, the proposed novelty residue is bounded inspection of private headers, signature algorithms, and signer-policy blobs before subprocess or device access, in this software-only release protocol; reversing a familiar allow-list policy alone presents an obviousness risk.

For canonical bytes, RFC 8785 provides the serialization primitive, Sigstore cosign uses canonicalization for transparency-related verification, and Authenticode illustrates explicit hash-domain choices. The proposed novelty residue is the line-feed extension inside the payload's digest and signature input together with transmitted-byte verification and exact-payload version discipline. RFC 8785 itself does not append that byte, and a known delimiter convention alone need not confer patentability.

For audience binding, RFC 8707 resource indicators and RFC 9068 access-token audiences already require intended-resource matching; SSHSIG also binds a signature namespace. Against these and TUF's trusted metadata roles, the proposed novelty residue is the authority-relative canonical path and digest-keyed policy lookup that preserve project identity when the whole authority tree moves, composed with distinct instrument, schema, and snapshot bindings rather than claimed as audience checking in general.

Additional Group 3 comparisons concern US20220121479A1 (Opsera, published 2022-04-21, an abandoned application cited as a publication only; agent-verified 2026-09-21), "Configuring DevOps Pipelines Using Access Controlled Gates And Thresholds"; US12572354, "CI/CD template framework for DevSecOps teams"; and US12430425, "Continuous integration and continuous deployment pipeline security." Their register summaries respectively describe RBAC approval gates, centrally owned security thresholds, and risk-classified pipeline termination with approvals. These teach meaningful parts of the combination; none of those summaries establishes the full exact-payload and receipt protocol. Assignees and grant dates were agent-verified on 2026-09-21 on Google Patents (Opsera, abandoned application; Citizant, granted 2026-03-10; IBM, granted 2025-09-30), with the human filing gate untouched.

The preceding comparisons account for every Group 3 item in the saved lane output, including the distinct MLPerf submission and audit references, both Debian rebuilder and build-information references, Connaisseur, SSHSIG, OpenSSH algorithm filtering, and both OAuth RFCs. The comparison draws on that local register without new network retrieval. It is a drafting position, not an opinion that no reference anticipates a claim.

### 8.12 Prevention register and technical effects

The following register states the computer actions that ground the eligibility position. It names the artifact whose acceptance or production the mechanism prevents. It does not use a desired quality judgment as a substitute for an executable check.

| Claims | Prevention verbs | Artifact and technical consequence |
| --- | --- | --- |
| 1, 2, 27, 28 | excludes; copies; refuses | Local qualification cannot become an authoritative terminal record through report editing |
| 1, 3, 4, 27, 28 | pins; recomputes; compares; denies | Candidate-selected verifier or changed export bytes cannot obtain the publisher's release result |
| 1, 5, 6, 7, 8, 9, 10, 27, 28 | authenticates; excludes; counts; preserves; refuses | Duplicate principals, self-approval, changed payloads, and cross-domain envelopes cannot satisfy authority |
| 1, 11 through 19, 26, 27, 28 | enumerates; compares; refuses; prevents | Incomplete control evidence cannot produce terminal authorization, and the verifier cannot execute a replacement observation |
| 20, 21 | binds; reconciles; refuses | Measurement carriers and current receipt-policy versions cannot give way to incompatible legacy evidence |
| 22 | parses; bounds; refuses | Forbidden signature carriers cannot reach backend subprocess or device discovery paths |
| 23, 24 | includes; retains; rejects | Byte termination and malformed input cannot silently alter the signed message |
| 25 | derives; hashes; compares | A valid signature for a different project cannot pass the audience boundary |

For Alice Step 2A Prong Two, independent claims 1, 27, and 28 integrate signature and set operations into a concrete release-control architecture. The processor excludes a terminal constructor locally, checks immutable subjects outside candidate authority, and refuses release without the prescribed evidence. The claimed effect is prevention of unauthorized release bypass, not organizing human reviewers or assigning trust scores.

For Alice Step 2B, the asserted contribution is the ordered combination, including the verifier's inability to execute the benchmark to manufacture replacement evidence. The known status of hashing, signatures, thresholds, and policy checking remains a substantial obviousness and eligibility headwind. Dependent claims identify narrower byte-level and carrier-level fallback structures rather than relying on the label machine learning.

Under EPO Article 52 and Guidelines G-II 3.3 and 3.3.1, the specific technical purpose is cryptographic release control over executable artifact bytes. Hash computation and set comparison protect message integrity, subject identity, and authorization boundaries. The machine-learning artifact is the controlled object, not an asserted improvement to a mathematical model. Prevention of unauthorized release bypass and avoidance of candidate execution in the publisher are the claimed technical effects.

For independent claim 1 under India s.3(k), in the Ferid Allani and Microsoft v. Assistant Controller vocabulary, the technical problem is candidate-controlled self-release and evidence substitution. The technical solution is the processor-enforced capability split with immutable digest comparison, disjoint-principal thresholds, and exact receipt coverage. A measurable technical benefit would be refusal of altered snapshots and unauthorized terminal records under specified attack inputs; no novel hardware is required, and no measured rate is asserted.

For independent claim 27 under India s.3(k), the technical problem is an authorization path that accepts mutable subjects or incomplete execution observations. The technical solution is the ordered computer method that retains the local ceiling, verifies externally pinned subjects, counts eligible role principals, and checks receipt completeness without executing candidate code. A measurable technical benefit would be deterministic refusal of those bypass inputs and absence of benchmark invocation by the verifier; no novel hardware is required.

For independent claim 28 under India s.3(k), the technical problem is software that can transform local eligibility or semantic re-encoding into apparent final authority. The technical solution is stored instructions implementing the same bounded authorization sequence and non-execution constraint. A measurable technical benefit would be reproducible exclusion of unauthorized terminal transitions on a fixed input corpus, not an administrative efficiency claim; no novel hardware is required, and the medium form does not replace analysis of the technical contribution.

### 8.13 Scope, single-actor operation, and the permanently human acts

File names, paths, role names, predicate strings, disposition tokens, refusal codes, algorithm labels, vocabulary sizes, and illustrative thresholds identify implementations rather than claim limitations. Other typed encodings and cryptographic functions may implement the described relationships where technically consistent. The dependency claims preserve functional byte and authority constraints without importing those labels.

A single platform operator may perform or cause every claimed step through separately administered execution contexts. Externality describes issuance authority, write authority, and exclusion of candidate principals, not a requirement for different legal entities. Receipt production can occur in another organizational unit; the claimed verifier receives and validates its evidence rather than requiring the verifier to execute the benchmark.

The drafting party reconciles the description and never files it. Filing is a permanently human act. Publication beyond the repository, operational acceptance against a capped disposition, and admission into a human-graded calibration collection also remain human decisions; none waives a release predicate.

No statement asserts any filing, deployment, or measured pass rate. The repository contains verifier-side mechanisms, while the publisher deployment, external execution service, and quality-controls runner remain unestablished. Missing external evidence therefore remains a blocker, not a prophetic successful result. The applicant has an interest in the described portfolio, and counsel must assess patentability and filing strategy independently.

## 9. CLAIMS

What is claimed is:

**1. A system for controlling release of machine-learning evaluation artifacts, comprising:** one or more processors; one or more non-transitory memories storing instructions executable by the processors to implement a local qualification routine whose closed result type excludes a terminal release value, and a verifier in a governance publisher repository separate from a candidate repository; and a governance trust store outside candidate write authority; wherein the verifier operates at an independently pinned revision on immutable candidate and export snapshots under identities, trust revisions, and a closed release policy fixed outside a candidate tree, authenticates instrument-specific group dispositions against a producer-role threshold of distinct externally enrolled principals and then an approver-role threshold that excludes the producer principals, requires for each exported bundle an authorized execution receipt containing a single outcome for each policy-required control under a common manifest closure digest with neither duplicate nor additional control outcomes, and permits terminal release authorization only upon acceptance of the snapshots, dispositions, and receipts, while preventing execution of the benchmark by the verifier.

**2.** The system of claim 1, wherein the instructions copy a disposition line of each report of a set of root reports verbatim from its applicable machine record and refuse a report token that exceeds the standing permitted by that record.

**3.** The system of claim 1, wherein each group disposition binds a complete export snapshot digest, a canonical bundle-set identity, an immutable candidate commit, a repository identity, a project identity, and the independently pinned verifier revision.

**4.** The system of claim 3, wherein the governance publisher fixes expected repository identities, verifier and trust commits, a signer policy, a trusted-root version, and the closed release policy outside the candidate tree and denies candidate selection of those inputs.

**5.** The system of claim 1, wherein the verifier counts distinct authenticated principal identities rather than signatures, excludes revoked and expired principals at an evaluation instant, and prevents repeated signatures or multiple keys attributed to a common principal from increasing either role's eligible-principal count.

**6.** The system of claim 1, wherein the instructions retain partial signatures from separate signing sessions over unchanged disposition payload bytes without transferring a private key between signers or supplying a private key to an envelope assembler.

**7.** The system of claim 6, wherein the instructions authenticate the retained partial signatures and report, for each role, a required threshold, eligible principals, a missing-principal count, and a completion indication.

**8.** The system of claim 6, wherein the envelope assembler resumes from an existing envelope, requires each added partial to match the existing envelope's payload bytes and payload type exactly, refuses duplicate signature entries, and preserves the payload bytes when forming a combined envelope.

**9.** The system of claim 1, wherein the verifier accepts an existing valid signed disposition of a preceding named-principal schema through an expressly selected compatibility path without reserializing its signed payload or treating its signatures as approval of a newer-schema payload.

**10.** The system of claim 1, wherein typed signature framing distinguishes instrument and schema domains and the verifier refuses an otherwise valid envelope copied from a different instrument domain or schema domain.

**11.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome is missing from a receipt.

**12.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates failure.

**13.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates skipped execution.

**14.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates deferred execution.

**15.** The system of claim 1, wherein the verifier refuses terminal release authorization when a required control outcome indicates a waiver.

**16.** The system of claim 1, wherein the verifier refuses terminal release authorization when a receipt repeats a required control identifier, irrespective of agreement between the repeated outcomes.

**17.** The system of claim 1, wherein the verifier refuses terminal release authorization when a receipt contains a control outcome outside the policy-required control set.

**18.** The system of claim 1, wherein only the closed release policy outside candidate write authority may designate a judge-completeness and repeatability control non-applicable, and the receipt must retain an outcome row for that control.

**19.** The system of claim 18, wherein the verifier refuses a non-applicable designation for an execution-fidelity control regardless of a candidate declaration or receipt signer's assertion.

**20.** The system of claim 19, wherein the instructions validate measurement-fidelity carriers comprising a pinned harness configuration with a separate adequacy approval, per-rollout execution telemetry, and pilot policy and attempt records binding predeclared disjoint groups and rollout conformance standing, while preventing absent fidelity coverage from constituting a passing control outcome.

**21.** The system of claim 20, wherein the verifier refuses superseded execution-receipt and release-policy schemas without a legacy acceptance route, independently of compatibility permitted for a preceding disposition schema.

**22.** The system of claim 6, wherein a software-only signature backend parses bounded private-key public headers, detached-signature public-key and signature-algorithm fields, and signer-policy public blobs to refuse hardware-security-key algorithms and their certificate forms before invoking a cryptographic subprocess or performing device discovery.

**23.** The system of claim 8, wherein a canonical byte profile appends a terminating line-feed byte to a canonical serialization of a structured data object and includes that byte inside every digest and signature input using the profile, and the verifier authenticates transmitted payload bytes rather than a reserialization.

**24.** The system of claim 23, wherein the canonical byte profile rejects lone surrogates, non-finite numbers, duplicate object keys, cyclic containers, and programmatic integers not exactly representable as finite binary floating-point values, and a text parser refuses nesting beyond a defined resource bound.

**25.** The system of claim 1, wherein a gate policy uses a canonical project-root path relative to a trusted authority root as an expected signed audience and uses a digest of that path to identify the policy, such that relocation of the whole authority tree preserving its relative layout preserves the audience while an audience mismatch prevents authorization.

**26.** The system of claim 1, wherein the policy-required controls comprise build-asset and harness integrity, oracle and negative-control integrity, alternate-solution and mutation-based grading integrity with instruction scope, judge completeness and repeatability, trial and reward accounting, and execution fidelity.

**27. A computer-implemented method for controlling release of machine-learning evaluation artifacts, comprising:** computing, by processors, a local qualification with a closed result type excluding a terminal release value; operating a verifier at an independently pinned revision in a governance publisher repository separate from a candidate repository, using identities, trust revisions, and a closed release policy fixed outside a candidate tree to evaluate immutable candidate and export snapshots; authenticating instrument-specific group dispositions against a producer-role threshold of distinct externally enrolled principals and then an approver-role threshold excluding those producer principals; requiring for each exported bundle an authorized execution receipt containing a single outcome for each policy-required control under a common manifest closure digest with neither duplicate nor additional control outcomes; permitting terminal release authorization only upon acceptance of the snapshots, dispositions, and receipts; and preventing the verifier from executing the benchmark.

**28. A non-transitory computer-readable storage medium comprising:** instructions that, when executed by processors, cause the processors to control release of machine-learning evaluation artifacts by: computing a local qualification with a closed result type excluding a terminal release value; operating a verifier at an independently pinned revision in a governance publisher repository separate from a candidate repository under identities, trust revisions, and a closed release policy fixed outside a candidate tree to evaluate immutable candidate and export snapshots; authenticating instrument-specific group dispositions against a producer-role threshold of distinct externally enrolled principals and then an approver-role threshold excluding those producer principals; requiring for each exported bundle an authorized execution receipt containing a single outcome for each policy-required control under a common manifest closure digest with neither duplicate nor additional control outcomes; permitting terminal release authorization only upon acceptance of the snapshots, dispositions, and receipts; and preventing the verifier from executing the benchmark.

## 10. ABSTRACT OF THE DISCLOSURE

A computing system controls release of machine-learning evaluation artifacts through distinct qualification and authorization capabilities. A local routine has a closed result type excluding terminal release. A separate governance publisher verifies immutable candidate and export snapshots using independently pinned verifier and trust revisions. Instrument-specific group dispositions require thresholds of distinct externally enrolled producer principals and disjoint approver principals. Partial signatures accumulate over unchanged payload bytes without shared private keys. Each bundle requires an authorized execution receipt covering every policy-required control exactly once under a common manifest closure. Non-passing or incomplete evidence prevents release, and the verifier does not execute the benchmark. Further embodiments enforce software-only signing through bounded carrier parsing, retain transmitted signed bytes across version compatibility, include a terminating line feed within canonical signature inputs, and bind evidence to a relocation-invariant project-relative audience.
