# UNITED STATES NON-PROVISIONAL UTILITY PATENT APPLICATION

**Filed under 35 U.S.C. § 111(a)**

**Title:** Tiered Evidence Admission with Exhaustion Receipts, Supersession Edges, and Blinded Hardness Memory for Benchmark Authoring

**Inventor:** Sarvex Jatasra

**Applicant / Assignee:** Ethara.AI

**Docket Reference:** Trinity/evidence-admission

---

## 1. TITLE OF THE INVENTION

Tiered Evidence Admission with Exhaustion Receipts, Supersession Edges, and Blinded Hardness Memory for Benchmark Authoring

## 2. CROSS-REFERENCE TO RELATED APPLICATIONS

The related parent disclosure is titled "Cryptographically Controlled Certification of Machine-Learning Evaluation Tasks Using Isolated Generation, Audit, and Evidence Domains." Its filing is prospective. This application is intended as a divisional or continuation of that disclosure, with the choice left to the human filing decision and any applicable restriction, support, and priority requirements. No application number, filing date, priority entitlement, or restriction requirement is asserted.

Parent sections 8.29 and 8.30 describe calibration staging and a projected hardness catalog. This sibling describes the evidence-admission mechanisms in full, without requiring incorporation of the parent to understand their operation. The parent also contains related evidence passages during this reconciliation; their presence does not establish filing or priority. This title block identifies an intended statutory form, not a filing event.

## 3. STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH OR DEVELOPMENT

Not Applicable.

## 4. FIELD OF THE INVENTION

The disclosure concerns computing infrastructure that supplies external evidence to machine-learning benchmark authoring processes. It addresses receipt-gated discovery, byte-bound corpus integrity, retained supersession relations, and deterministic information-flow control between evidence and authoring domains. Evidence appraisal informs design inputs but does not certify the difficulty of an executable task.

## 5. BACKGROUND OF THE INVENTION

A first deficiency concerns failed discovery presented as absence. A challenged endpoint, unresolved repository rename, or unfollowed redirect can yield no usable records. Treating that outcome as a completed search lets lower-quality material displace evidence that the system never retrieves.

A second deficiency concerns provenance multiplication. Independent hostnames can mirror a common board or report. Counting hostnames as independent corroboration increases apparent support without increasing independent evidence.

A third deficiency concerns mutable source identity. A stable-looking path may point to changed bytes, and a pinned code revision may load data through a mutable alias. A text rendering without retained source bytes or a recorded conversion tool cannot establish its asserted provenance.

A fourth deficiency concerns invalidation leakage. Deleting an obsolete row destroys its history, but disclosing its replacement evidence to a task author reveals why the row no longer qualifies. An invalidation graph can therefore become an unintended channel into the author's design process.

A fifth deficiency concerns automated self-calibration. A machine that proposes examples and also inserts them into the reference library controls the standard against which its own outputs are assessed. Screening a proposal does not solve that authority problem.

A sixth deficiency concerns conflated thresholds. A target above published capability, a composition count above a design floor, and an upper bound on observed solver success constrain different quantities. Substituting one for another can make a well-provisioned design appear empirically difficult without execution evidence.

PRISMA-S, GRADE appraisal systems, content identifiers, and invalidation graphs address parts of these deficiencies. The disclosed combination instead prevents specific state transitions and field exposures: discovery cannot admit, failed retrieval cannot authorize descent, and retained supersession evidence cannot cross into the authoring projection.

## 6. SUMMARY OF THE INVENTION

In some embodiments, processors operate an evidence domain and a separately access-controlled authoring domain. The evidence domain maintains an ordered source-class policy, a discovery-receipt store, an admitted corpus, a hardness catalog, and a retained supersession relation. The authoring domain receives catalog information only through a deterministic projection.

A discovery scheduler opens a lower tier only after each substrate of the immediately preceding tier carries an exhaustion receipt for the invocation. A receipt binds the issued query and returned-set digest under a closed field schema. An unanswered lane remains a named gap, not a clean empty result. Discovery and admission use separate authority, so descent never grants anchor status.

A corpus validator recomputes retained-byte and rendering digests and compares them with a sidecar. The complete admission embodiment also requires derivation from retained bytes using a named converter at a pinned version. The present validator checks that declaration and the stored bytes, not actual converter execution.

A supersession processor retains obsolete rows and chainable edges to their superseding evidence. A deterministic projector excludes the edge, its target evidence, and its supersession kind from the authoring domain. A superseded row without its required edge fails closed before it can support catalog use.

Dependent embodiments add source appraisal, confidence caps, separate target and composition headroom, a non-increasing measured-pass ceiling, human-only calibration admission, and current corroborated reconnaissance that may narrow standing but never certify it. These are configured controls, not reports of measured benchmark performance.

## 7. BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 depicts an evidence domain, a receipt store, an admitted corpus, a catalog, a supersession store, a deterministic projector, and an authoring domain behind a restricted read interface.

FIG. 2 depicts ordered tier opening, collection of substrate-specific receipts, retention of unexhausted gaps, and separate resolution and admission of a discovered lead.

FIG. 3 depicts retained source bytes and a derived rendering under a shared stem, a sidecar binding their digests and converter declaration, and refusal branches for missing or inconsistent members.

FIG. 4 depicts a retained superseded row linked to replacement evidence, tier-gated edge creation, and exclusion of both the link and its target from the author projection.

FIG. 5 depicts a versioned hardness row, target headroom, composition headroom, a measured-pass ceiling, and independent paths for narrowing design inputs and obtaining external measurement.

FIG. 6 depicts read-only reconnaissance and harvest lanes, their dated advisory outputs, and a human-controlled boundary separating proposed calibration bundles from the admitted reference library.

## 8. DETAILED DESCRIPTION OF THE INVENTION

### 8.1 Overview

The system separates finding a source, admitting stable evidence, deriving a design target, and certifying an execution. A discovery receipt records the first operation only. A corpus record binds stored bytes, a catalog row expresses a source-grounded design input, and an external execution record supplies any measurement authority. CONTRACT-ONLY (ENGRAM.md:231-243, 249).

In some embodiments the evidence domain alone writes the shared corpus and catalog. Private research staging from another domain enters only through independent rediscovery, not copying sender-selected metadata into an admitted artifact. The sender cannot determine the admitted set by attaching its own staging timestamp or rationale. CONTRACT-ONLY (ENGRAM.md:234).

The intended runtime uses access-controlled resources rather than secrecy advice. A projection is computed from defined input bytes and a declared evaluation instant, and only that output is readable by the authoring domain. Full runtime confidentiality is not established by a repository scanner. CONTRACT-ONLY (ENGRAM.md:386, 408); DEFERRED (DEFERRED.md: "A full clone does not enforce the information barrier between humans").

The evidence map distinguishes executable checks from contract obligations. Existing vocabulary tests prove token presence and separation, not live search, confidence computation, or graph traversal. Existing corpus tests exercise stored-byte validation, not historical conversion. No network retrieval or execution of benchmark tasks forms part of this drafting pass.

The dated basis is the Phase H trust-ladder and content-addressed-corpus entry dated 2026-09-20 at CHANGELOG.md:23, together with the corpus and PRISMA-S follow-up entry dated 2026-09-20 at CHANGELOG.md:22. The entry dated 2026-09-21 at CHANGELOG.md:21 is the Phase S scribe record, not the Phase H follow-up. The PRISMA-S addition to the contract has commit 0231cd1 dated 2026-09-21. Entry dates and subjects identify these sources if their line numbers shift.

### 8.2 Definitions

An evidence domain is a machine access-control boundary holding corpus and catalog write authority. An authoring domain is a separate boundary that generates executable benchmark tasks from permitted design inputs, without direct read authority over the underlying private evidence state.

A substrate is a separately identified searchable resource within the declared discovery scope. A tier is a default prior associated with a source class, not a verdict, a row state, or a task disposition. Exhaustion means recorded completion of the substrate's declared search for an invocation, not proof that all facts on the Internet are known.

A lead identifies material to resolve further. An anchor is an admitted, stable artifact bound to a catalog row by content identity and accompanied by cohort, score, and date. Retaining a low-authority lead does not confer anchor authority.

A closed schema has an enumerated field set and rejects missing or unrecognized fields. A receipt's returned-set digest binds the search result population represented by that receipt; it is distinct from the digest of an admitted source artifact.

A supersession edge is a stored relation naming an obsolete row and its superseding evidence or successor row. Retaining the edge preserves queryable invalidation history. A supersession kind distinguishes replacement from retirement without adding another row state.

A deterministic projection is an executable transformation of a defined input closure. Fields forbidden to the recipient are structurally absent from its output, not merely hidden by a display widget. Repeated evaluation of the same input bytes under the same transformation and declared instant produces the same output bytes.

A refusal prevents the relevant opening, admission, reliance, or export operation. It need not prohibit independent work unrelated to the failed condition. A named gap identifies the missing evidence and cannot serve as an approving result.

A certification record is an authoritative assertion rooted in qualifying external execution evidence. Neither a receipt, a confidence level, a proposed calibration label, nor a configured headroom target is such a record. CONTRACT-ONLY (ENGRAM.md:108, 212, 240, 243, 245).

### 8.3 Source-class trust ladder, adjudication, provenance, and liveness

In one implementation the eight-member tier vocabulary is T0 through T7. T0 excludes agent recollection and model self-reported difficulty. T1 covers independently adjudicated evidence, including refereed papers, preprints, and dated independent institute evaluations. Refereed status is an attribute, not a correctness premium above a preprint. CONTRACT-ONLY (ENGRAM.md:234).

In one implementation T2 covers maintainer-adjudicated evidence: boards, changelogs, release notes, errata, proceedings, issued patents, official reviews and decisions, and resolved forecast markets. T3 covers first-party lab cards, technical reports, safety frameworks, and evaluation blogs. T4 covers third parties conducting their own measurements. CONTRACT-ONLY (ENGRAM.md:234).

In one implementation T5 covers engineering issues, pull requests, discussions, dataset-card threads, advisories, postmortems, and third-party audits. T6 covers hosted vendor submissions, trade press, and scraper boards. T7 covers unreproduced social or blog claims. These defaults do not prevent a merged engineering fix from carrying stronger adjudication than an unreproduced launch claim. CONTRACT-ONLY (ENGRAM.md:234).

In one implementation every admitted item carries an adjudication token selected only from `adjudicated-by-issuer`, `merged-fix`, `admission-against-interest`, `reproduced-by-third-party`, `open-with-reproduction`, `open-unreproduced`, `disputed`, and `withdrawn`. A missing or outside token does not establish an adjudication. CONTRACT-ONLY (ENGRAM.md:234).

Each item records provenance sufficient to distinguish independent sources from mirrors. Multiple scrapers of the same board count as that board's provenance; an article quoting an institute report counts as the report, not independent corroboration. In one implementation liveness is exactly `active`, `maintenance`, `frozen`, `retired`, or `archived`. A retired board's dated slice may remain evidence but cannot assert current frontier capability. CONTRACT-ONLY (ENGRAM.md:234).

A source still appending to itself is a lead never an anchor. A dated or versioned slice may anchor after ordinary admission. Hashing the bytes observed at one instant does not by itself convert an open-ended source identity into a pinned source record. CONTRACT-ONLY (ENGRAM.md:486).

In one implementation `SOURCE_TIERS` is disjoint from row, lever, ledger, task, spine, and band states. ENFORCED (tools/integrity.py, first landed 2026-06-24; tests/test_hardness_contract_vocab.py) covers the vocabulary half; the tier constant enters on 2026-09-20 in commit 8f0b38a. The tier policy, appraisal, provenance independence, and liveness decisions remain CONTRACT-ONLY (ENGRAM.md:234).

### 8.4 Ordered descent and failure-preserving coverage gaps

The discovery scheduler opens a lower tier only after every substrate of the immediately preceding tier records an exhausted receipt for the invocation. Missing receipts and any unexhausted receipt prevent that tier from being represented as drained. The scheduler does not substitute an aggregate success count for every-substrate completion. CONTRACT-ONLY (ENGRAM.md:234, 240).

Descent is for discovery never admission. In one implementation a T6 or T7 find opens a lead that is sought at T1 or T2; the higher-tier record must independently resolve and pass admission before it can anchor. The lower-tier find does not inherit the resolved anchor's authority and is discarded as a load-bearing citation. CONTRACT-ONLY (ENGRAM.md:234).

A challenge, rate limit, failure status, unfollowed redirect, or unresolved rename leaves the lane unexhausted. In one implementation unresolved T1 or T2 lanes appear as named coverage gaps in `DIRECTIVE.md`. Empty result rows are not proof of a functioning endpoint or a resolved identity. CONTRACT-ONLY (ENGRAM.md:234, 240).

The contract also permits discovery alone with a failed-lane gap retained. Here an incidental lower-tier lead does not constitute lawful opening of that tier or authorize any admission; the ordinary ordered-descent gate stays closed. This distinction preserves both the every-substrate gate and the ability to record adjacent leads without asserting exhaustion. CONTRACT-ONLY (ENGRAM.md:234).

For example, a renamed repository that returns no records under its old name remains a resolution gap. A later invocation can resolve its canonical identity and append a new receipt, but it cannot rewrite the earlier receipt into a successful search. This is a conditional trace, not a retrieval result. CONTRACT-ONLY (ENGRAM.md:240, 255).

### 8.5 Closed discovery receipt and PRISMA-S correspondence

In one implementation `engram.receipt/v1` carries exactly twenty-one fields, listed below. There is one immutable receipt per substrate per invocation, appended to the dated hardness block. A missing or unknown field fails closed. The invocation and block identify the receipt context without introducing an extra field into the closed payload. CONTRACT-ONLY (ENGRAM.md:240, 255).

In one implementation `substrate_kind` is exactly `database`, `registry`, `browsed-resource`, `citation-index`, `contact`, or `other-method`. Exhaustion is exactly `exhausted` or `unexhausted`, with its reason carried in that field's value. The canonical identity is the host-returned identity resolved before querying, not a user-supplied alias. CONTRACT-ONLY (ENGRAM.md:240).

The following item-by-item mapping identifies PRISMA-S reporting concerns and explicit protocol extensions. It does not assert that a field name alone satisfies the complete checklist. Any missing detail, including constituent databases for a multi-database search, remains a named gap. CONTRACT-ONLY (ENGRAM.md:240); PRISMA-S, Rethlefsen et al. 2021, DOI 10.1186/s13643-020-01542-z.

| Closed field in one implementation | PRISMA-S correspondence or additional protocol purpose |
| --- | --- |
| `substrate` | Items 1-7: identify the database, registry, resource, citation index, contact, or other method |
| `substrate_kind` | Items 1-7: classify the source, with constituent databases additionally identified for item 2 |
| `substrate_tier` | Protocol extension: default source-class prior beside the source description |
| `canonical_identity_resolved` | Items 1-7 identification, strengthened with the current host-returned identity |
| `transport` | Platform or access-method description for items 1 and 3-7 |
| `endpoint` | Resource or platform location used for items 1-7 |
| `query_verbatim` | Item 8: full search strategy exactly as issued |
| `filters` | Item 9 restrictions and item 10 search filters |
| `filter_provenance` | Item 10: published filter reused |
| `strategy_provenance` | Item 11: earlier strategy adapted |
| `date_bounds` | Item 9 date restrictions, distinct from the search execution date |
| `http_status` | Protocol extension: transport outcome, including failed access |
| `records_returned` | Item 15: source-specific record count |
| `records_admitted` | Item 15 accounting extension: admitted count separate from returned count |
| `deduplication` | Item 16: removal process and software |
| `rung_answered` | Items 1-7 method description, extended with the resolving rung |
| `result_set_digest` | Item 15 accounting extension: binding to the returned population |
| `instant_utc` | Item 13: date searched, refined to an exact instant |
| `update_method` | Item 12: method for updating an earlier search |
| `peer_review` | Item 14: reviewer of the search strategy |
| `exhaustion` | Protocol extension: completion or unresolved failure with a reason |

A topic list cannot replace the issued query. A result-set digest binds discovery output, not the truth of that output or the availability of higher-tier evidence. The receipt mints no certification record, promotes no row, evidences no difficulty tier, and raises no disposition. CONTRACT-ONLY (ENGRAM.md:240).

The Phase H entry dated 2026-09-20 at CHANGELOG.md:23 describes fifteen fields; the follow-up entry dated 2026-09-20 at CHANGELOG.md:22 and the current contract add source kind, filter provenance, strategy provenance, update method, peer review, and deduplication while retaining the predicate name. Current drafting uses the full field set and does not silently accept the shorter form. CONTRACT-ONLY (ENGRAM.md:240; the entries dated 2026-09-20 at CHANGELOG.md:22-23).

### 8.6 Source-specific resolution and mutable-data-alias findings

In one implementation scholarly T1 resolution walks the redirect-following arXiv interface, open bibliographic indexes, versioned preprint interfaces, venue proceedings, then an open-access archive. The anchor identity is a versioned arXiv identifier or registered document identifier; a mutable index is discovery infrastructure, not the anchor. Institute T1 resolution walks the publisher page, dated report file, then a capture with recorded archive digest. CONTRACT-ONLY (ENGRAM.md:241).

In one implementation maintainer-board T2 resolution walks a git-backed branch, release tag or changelog, a host dataset revision, a versioned release object, then a dated static post. Failure to pin through these rungs demotes the board to T6. Reaching a branch name does not excuse pinning the relevant bytes. CONTRACT-ONLY (ENGRAM.md:241, 486).

In one implementation OpenReview T2 clearance begins with a real browser session completing its managed challenge. The browser mints a short-lived, address-bound clearance token; ordinary requests obtain forum notes and edits within the clearance window. The anchor pins forum identity, note identity, `tmdate`, and the SHA-256 of note text. Re-verification reads the edit log for a later modification time. CONTRACT-ONLY (ENGRAM.md:241).

A third-party OpenReview dump remains adjacent at T6 and cannot substitute for the maintainer's anchor. Clearance permits access, not appraisal or certification. This embodiment describes authorized resolution through the service's challenge workflow, not any actual session in this drafting pass. CONTRACT-ONLY (ENGRAM.md:241).

In one implementation lab-document T3 resolution prefers a publisher content-addressed path, then a commit-pinned raw path, then a capture with archive digest. Engineering T5 resolution first obtains the host's canonical repository identity, queries the item index, and pins item number plus retained-body digest. Rumour T7 requires a capture at read time even to retain a lead. CONTRACT-ONLY (ENGRAM.md:241).

An archive digest corroborates provenance but is not the served artifact's identity. A class with no answering rung retains a named resolution gap listing attempted rungs. Name similarity is adjacent evidence, never a resolved identity. CONTRACT-ONLY (ENGRAM.md:241).

The harness-code lane first queries the hosting hub's paper index, follows code links in the latest paper version and one additional project-page hop, then inspects repositories named by linked model or dataset cards. It pins an immutable commit and records the answering rung. A code-search hit on the paper identifier alone is adjacent. CONTRACT-ONLY (ENGRAM.md:237).

In one implementation a resolved loader selecting benchmark data through a mutable alias receives the advisory finding `mutable-data-alias`. A pinned program does not imply pinned data. The lane records harness-shape facts against the reference plugin structure, pinned at commit `405bae7140d7e961a75f4910a0b2e7069731db96`, and proposes rather than pronouncing a calibration verdict. CONTRACT-ONLY (ENGRAM.md:237).

Source-classed ingest also produces a partial brief binding identity, digest, tier, adjudication, liveness, converter declaration, source-located levers, corpus and harness revisions, baselines, gaps, and proposal standing. In one implementation `engram.brief/v2` and the related `engram.next/v2` successor form replace identifier-only assumptions; missing human grants remain gaps, and changed brief bytes require approval before consumption. CONTRACT-ONLY (ENGRAM.md:238, 267-270).

### 8.7 Content-addressed dual retention and corpus refusals

Every admitted artifact has retained source bytes under their own extension and a derived rendering under the same stem. In one implementation a paper retains a PDF and a Markdown rendering under `research/paper/`. The rendering must derive from the retained bytes through a named tool at a pinned version, never manual authorship. CONTRACT-ONLY (ENGRAM.md:24, 238, 486).

Content identity is the SHA-256 computed over retained bytes. The stem labels the artifact but does not define its identity, so relocating unchanged bytes under the source class does not change the content digest. Path-to-manifest consistency remains a separate requirement; relocation does not permit a sidecar to name a different pair. CONTRACT-ONLY (ENGRAM.md:24, 486).

In one implementation the sidecar `engram.identity/v1` has exactly `schema`, `source_class`, `stem`, `retained`, `rendering`, `content_digest`, `rendering_digest`, `deriving_tool`, and `deriving_tool_version`. The writer declines to overwrite an existing sidecar. The reader compares the exact field set and schema, recomputes both digests, and checks path-associated names and nonempty converter declarations. ENFORCED (tools/corpus_identity_manifest.py, first landed 2026-09-20; tests/test_corpus_identity.py).

In one implementation the following ten refusal classes identify the failing half. They are diagnostic vocabulary, not claim limitations. ENFORCED (tools/corpus_identity.py, first landed 2026-09-20; tests/test_corpus_identity.py), with tools/corpus_identity_manifest.py supplying pair validation.

| Refusal in one implementation | Condition preventing conformance |
| --- | --- |
| `CORPUS_LOOSE_ARTIFACT` | Artifact outside the source-class directories |
| `CORPUS_UNKNOWN_CLASS` | Directory not in the closed source-class vocabulary |
| `CORPUS_RENDERING_MISSING` | Retained bytes without their rendering |
| `CORPUS_RETAINED_MISSING` | Rendering without retained source bytes |
| `CORPUS_MANIFEST_MISSING` | Pair without an identity sidecar |
| `CORPUS_MANIFEST_MALFORMED` | Unreadable sidecar, wrong schema, or missing or unknown fields |
| `CORPUS_DIGEST_MISMATCH` | Retained bytes disagree with their recorded digest |
| `CORPUS_RENDERING_DIGEST_MISMATCH` | Rendering bytes disagree with their recorded digest |
| `CORPUS_STEM_MISMATCH` | Sidecar class, stem, or member names disagree with the path |
| `CORPUS_TOOL_UNRECORDED` | Empty deriving-tool identity or version |

In one implementation the admitted BenchEvolver pair uses stem `2606.01286-benchevolver-frontier-task-synthesis-via-solution-centric-evolution`. Its sidecar names the PDF and Markdown members, content digest `35d239716ec97af90b0f5025059150e4a931ae940d4543b00752c69b4872f30c`, and rendering digest `abd2ad0b071e224896f84cf1145a2888c8ff87c910760ecfea6db65455b48d37`. These are recorded values, not newly measured performance or a newly verified conversion.

That sidecar records both deriving tool and version as `unestablished`. The rendering's opening identifies the paper and contains extraction artifacts. It grounds the dual-retention description but does not establish the stronger derivation requirement. DEFERRED (DEFERRED.md: "Rendering derivation is declared, never reproduced"); CONTRACT-ONLY (ENGRAM.md:238, 486).

The executable reader accepts nonempty declarations, including that token, and coerces parsed values to strings after checking the field set. It neither runs a converter nor proves that a named version produces the stored rendering. ENFORCED (tools/corpus_identity_manifest.py, first landed 2026-09-20; tests/test_corpus_identity.py) is limited to the stated structural and digest checks, not full typed validation or historical derivation proof.

The tests cover each refusal code, a conforming synthetic pair, no-overwrite behavior, and the real corpus check. The research-fidelity suite separately checks class-qualified layout and recorded citations. Those tests do not supply an admission runtime or proof of tool provenance. CONTRACT-ONLY (ENGRAM.md:238, 486) retains the unevaluated half.

### 8.8 GRADE-shaped confidence seeded by tier

In one implementation each row carries exactly `high`, `moderate`, `low`, or `very_low`. These mean respectively that further research is unlikely to change confidence, likely to have an important impact, highly likely to change the estimate, or confronted with deep uncertainty. The domains producing the level are recorded beside it. CONTRACT-ONLY (ENGRAM.md:243).

In one implementation T1 seeds high, T2 moderate, T3 through T5 low, and T6 very_low. T6 never exceeds low. Excluded or rumour material does not acquire anchor authority through a confidence label. CONTRACT-ONLY (ENGRAM.md:242-243).

The downgrade domains are risk of bias, inconsistency, indirectness, imprecision, and publication bias. A disputed or withdrawn claim, conflicting independent provenances, a neighboring cohort, an absent interval, or a claimant-only report can invoke the respective domain. Each invoked domain lowers a level, or two levels when doubly serious. CONTRACT-ONLY (ENGRAM.md:243).

The upgrade domains are large effect, dose-response, and plausible confounding. Their disclosed grounds are replication across independent provenances, consistent direction across versions or cohorts, and an admission against interest. Each invoked domain raises a level, subject to the ceiling supported by the highest-tier anchor. CONTRACT-ONLY (ENGRAM.md:243).

The profile names the GRADE vocabulary of Cochrane Handbook chapter 14. The source ladder takes its shape from OCEBM 2011 levels without mapping a tier to a cell of that clinical grid. These are the contract's methodological attributions, not additional prior-art retrievals in this lane. CONTRACT-ONLY (ENGRAM.md:243).

Confidence is not measurement, row promotion, a certification record, or a disposition increase. The vocabulary tests assert the presence of the levels and domains but do not calculate a row's confidence or execute its cap. CONTRACT-ONLY (ENGRAM.md:243).

### 8.9 Retained supersession edges and blinded author projection

In one implementation the only row states are `CANDIDATE`, `ANCHORED`, and `SUPERSEDED`. An expired anchor, a later anchor showing the same cohort clearing the mechanism, or expiry of every anchored lever's qualifying evidence causes supersession while retaining the row. CONTRACT-ONLY (ENGRAM.md:212, 253).

In one implementation `superseded_kind` is `revoked` when a successor stands or `deprecated` when the mechanism retires without one. It is an axis on the superseded state, not a fourth state. A retirement can still point to evidence establishing retirement; absence of a successor row does not excuse an absent edge. CONTRACT-ONLY (ENGRAM.md:253, 255).

In one implementation `engram.supersession/v1` carries exactly `source_ref`, `target_ref`, `relationship`, `evidence_digest`, and `instant_utc`, with relationship `revoked-by`. The source names the superseded row; the target names superseding evidence or a successor row. An unknown or absent field fails closed. CONTRACT-ONLY (ENGRAM.md:253).

Each superseded row resolves its required edge; no edge means broken standing rather than continued anchored use. Edges chain through successive rows and remain queryable, never deleted. The current assertion requires exactly one resolving edge for the row; it does not license arbitrary competing targets. CONTRACT-ONLY (ENGRAM.md:212, 253).

In one implementation T1 or T2 evidence may supersede; T3 evidence may supersede only as an admission against interest. A resolved forecast market on a named board and date is saturation evidence for supersession, not a signed task measurement. T6 or T7 alone supersedes nothing. CONTRACT-ONLY (ENGRAM.md:253).

The dated reconciliation includes a retraction check for every identifier-bearing anchor. A hit re-tags the row deprecated in place and uses the retraction identity as the target. Retraction does not erase the source artifact or its invalidation trail. CONTRACT-ONLY (ENGRAM.md:255).

The author projection excludes the superseding anchor, the edge, and the supersession kind. A superseded row crosses only as its identifier and superseded state, allowing retirement of dependent designs without revealing what supersedes them. The exclusion concerns machine-readable fields, not display redaction. CONTRACT-ONLY (ENGRAM.md:386, 408).

The existing scanner detects forbidden hardness-path citations in auditor evidence, not supersession objects in author projections. ENFORCED (tools/integrity.py, first landed 2026-06-24; tests/test_barrier.py) covers that narrow citation check; the scanner's addition dates to 2026-08-27, commit f4c1a30. Its Markdown visibility rules omit code blocks and comments. It does not inspect a runtime edge graph or prove recipient isolation.

The complete edge walk, tier authority decision, and projection exclusion remain CONTRACT-ONLY (ENGRAM.md:212, 253, 408). DEFERRED (DEFERRED.md: "A full clone does not enforce the information barrier between humans") preserves the runtime confidentiality gap. A list of forbidden fields is not proof that those fields are inaccessible.

### 8.10 Row-versioned hardness catalog and separate policy thresholds

In one implementation `engram.hardness/v2` supplies one machine-readable row per lever, with `row_version` incremented on content change. Each row carries mechanism, category, axis, grading mode, orthogonality group, confidence and domains, anchor source class and identity, retained content digest, cohort, reported score, date, and a frontier-defeat target. CONTRACT-ONLY (ENGRAM.md:242-254).

Category axes are closed to Perception, Reasoning, and Agentic in one implementation. Shared orthogonality groups count as a shared coverage axis, not independent mechanisms merely because their labels differ. Until qualifying fitted evidence exists, groups remain authored priors with a named gap. CONTRACT-ONLY (ENGRAM.md:244, 251).

The evidence-domain target derives upward from published evidence and the latest reconnaissance block. In one implementation it is at or above one-and-six-tenths times the strongest anchored evidence for the category, a target headroom floor of sixty percent. A target below that floor remains a gap until re-derived. CONTRACT-ONLY (ENGRAM.md:245).

On the author side, a separate composition multiple is one-and-one-half times each governing floor, rounding up. It constrains lever and category provisioning, not the magnitude of the anchored result. A generous composition cannot substitute for an under-derived target. CONTRACT-ONLY (ENGRAM.md:257, 386; FORGE.md:349); parent section 8.30 supplies the corresponding disclosure.

In one implementation the measured pass ceiling is 0.40 on the pass-at-eight scale. A grant, calibration disposition, or stricter projection may lower the effective ceiling, but no source may raise it above the bound. The ceiling is a necessary measurement condition, not a measured result and not sufficient certification authority. CONTRACT-ONLY (ENGRAM.md:386; FORGE.md:350, 404).

In one implementation the single source `.memory/hardness.yaml` regenerates `HARDNESS.md` byte-identically with `GENERATED SECTION. DO NOT HAND-EDIT.` and the source named. The sheet renders axes, categories, eligibility, composition, gaps, superseded rows, anchors, domains, targets, and computed headroom. Drift fails closed. CONTRACT-ONLY (ENGRAM.md:212, 254).

The author receives the catalog only through its projection. Projected difficulty floors may only rise; the measured-pass ceiling may only fall. The catalog carries no budget or cost value. Duration mapping and cost aggregation are distinct derived state and cannot promote rows or supply hardness evidence. CONTRACT-ONLY (ENGRAM.md:245-249, 386).

The phase assertion recomputes an anchored row's retained-byte binding, cohort, score, citation horizon, and grading mode. A missing or mismatched anchor cannot continue as anchored, and an honestly empty catalog is a named gap, not a pass. These catalog assertions are not established by the corpus checker alone. CONTRACT-ONLY (ENGRAM.md:212).

### 8.11 Harvest staging under propose-never-admit

The harvest lane extracts public task-corpus references from admitted artifacts and resolves stable host identities at immutable revisions. It follows links in paper bytes, then the host's paper-bound data index, then the paper's named code repository. Unresolved or name-similar material remains a proposal with a resolution gap. CONTRACT-ONLY (ENGRAM.md:235).

In one implementation the staging root is `.memory/staging/`, with each bundle carrying `candidate.yaml` under `engram.harvest/v1`. The closed record names artifact stem, host corpus identity, revision digest, license, source kind, provenance date, per-atom screening outcomes and root digests, screening and expiry instants, suggested label, rationale, and standing. Standing is proposed, rejected, or expired. CONTRACT-ONLY (ENGRAM.md:56, 235).

The lane screens against the effective roots before proposing and retains screened-out candidates with rejection reasons. Materialized payloads bind file sizes and digests, license identity, resolved revision, source identity, and download instant. Retrieval, size, digest, or license failures remain named proposal gaps. CONTRACT-ONLY (ENGRAM.md:235-236).

Staged bytes are advisory only, never calibration input. The lane cannot write the calibration library or its verdict table, and a suggested label is not a human verdict. Only the human copies a bundle into the library, assigns its verdict, updates the verdict table, and re-signs scope. CONTRACT-ONLY (ENGRAM.md:56, 235); parent section 8.29 states the human admission sequence.

The computer-side admission boundary waits for the human-controlled library and renewed approval; it does not perform those human acts on the person's behalf. Screening success alone cannot affect a projection, disposition, lever state, or certification record while the bundle remains staged. CONTRACT-ONLY (ENGRAM.md:235); parent section 8.29.

### 8.12 Current corroborated frontier reconnaissance with narrowing-only output

On each invocation, after resume preflight and before phase work, parallel read-only lanes inspect evaluator leaderboards and dated reports, provider model and system cards, independent aggregators, and saturation literature. Each lane records source identity, URL, source class and default tier, retrieval instant, exact model and version, and reported score. CONTRACT-ONLY (ENGRAM.md:108).

In one implementation a capability claim enters the dated block only if its source timestamp is at most thirty days old at retrieval and at least two independent sources corroborate it. Mirror provenance does not satisfy independence. A stale or single-source claim is a named currency gap rather than current capability evidence. CONTRACT-ONLY (ENGRAM.md:108, 234).

Reconnaissance may open a gap, narrow a lever to WATCH in one implementation, request an externally signed registry refresh, or feed target derivation upward. It may never declare the cohort, mint a certification record, expire or restore a lever, raise a disposition, or clear a family flag. Supersession requires the separate admission and authority path, not a reconnaissance lane's own verdict. CONTRACT-ONLY (ENGRAM.md:108, 253, 256).

Each invocation appends a dated reconnaissance block, never overwriting prior findings, and surfaces currency gaps. Freshness is assessed at the recorded retrieval instant rather than by treating the present viewing time as a new retrieval. CONTRACT-ONLY (ENGRAM.md:108).

For example, a fresh pair of independent reports can require re-derivation of a target, but cannot make an expired lever active. A lone fresh launch card remains a currency gap. These are conditional behavior examples, not a report that reconnaissance executes here. CONTRACT-ONLY (ENGRAM.md:108, 245).

### 8.13 Named prior art and novelty residue: PRISMA-S, GRADE, and PROV comparisons

For source appraisal, US12639507 describes credibility with signed provenance and US9087048B2 concerns source-rating thresholds; WO2019043379A1 and US11526675 are additional register comparators for claim review. Such combinations present substantial obviousness risk for ranking alone. The asserted novelty residue is the coupling of a source-class prior with adjudication, independent provenance, and liveness under a discovery boundary that cannot grant admission authority. The register does not supply a claim chart for each patent, so no broader exclusion of their scope is asserted.

For ordered descent, Cormack and Grossman TAR stopping patents US10229117, US10671675, US10445374, and US10242001 concern search or review stopping. The asserted novelty residue is every-substrate exhaustion as the prerequisite to lower-tier opening, with unresolved lanes retained as gaps and descent denied admission authority, rather than stopping based only on retrieval yield or estimated recall.

For discovery receipts, PRISMA-S, DOI 10.1186/s13643-020-01542-z, and the search-history JSON structure PMC9682961 supply reporting and structured search history. The asserted novelty residue is the closed receipt's executable role in the descent gate, including verbatim query, result-set binding, and refusal to treat transport or identity failure as clean emptiness. Reporting-standard compliance alone is not claimed as inventive.

For class resolution, PRISMA-S identifies resources and SWHID ISO/IEC 18670:2025 separates content identity from location. The asserted novelty residue is source-specific ordered resolution with an authorized transient review-clearance window, edit-history pinning, secondary-dump demotion, and a separate mutable-data-alias finding that prevents a pinned harness from implying pinned data. This comparison does not claim novelty in browser clearance itself.

For corpus retention, SWHID ISO/IEC 18670:2025 and IPFS CID already teach location-independent content identification. Protocol Labs patents US10615979, US11570001, and US12294654 add a material patent-review headwind. The asserted novelty residue is retained-source plus derived-rendering binding at evidence admission, with a recorded converter and stable-slice requirement, not hashing, paired files, or distributed storage in isolation.

For confidence, GRADErater, J Clin Epidemiol 2026, and EvidenceGRADEr / URSE structure evidence appraisal. The asserted novelty residue is the source-tier seed and anchor-supported cap operating within a versioned design catalog whose confidence cannot promote a row or certify difficulty. The GRADE vocabulary and OCEBM-shaped ladder are acknowledged inputs, not renamed inventions.

For supersession, W3C PROV `wasInvalidatedBy` and Wikidata deprecated rank with P2241 preserve invalidation semantics; CrossRef Retraction Watch and the 2026 patents-citing-retractions study make retraction linkage pertinent. The asserted novelty residue is tier-gated authority, including the against-interest exception, combined with permanent edges and structural exclusion of the edge, its kind, and target evidence from the author projection. Retraction lookup alone supplies no such information-flow boundary.

For the catalog, item-bank exposure control US5841655 and US8348674, Duolingo S2A3 arXiv 2606.07364, and Epoch AI Rosetta Stone dated 2025-12-02 address exposure, assessment, or comparative performance. The asserted novelty residue is a row-versioned catalog with distinct evidence-target and author-composition headroom, plus a measured-pass ceiling that can only tighten, supplied through a blinded projection without substituting design arithmetic for execution evidence.

For harvest, Scale AI US12189719 and US11308364 represent automatic-benchmarking admission approaches in the register and point in the opposite direction from a permanent human admission boundary. Snorkel US2023/0419121 and the open-source goldset and golden-set-builder projects strengthen the combination risk for proposals and labels. The asserted novelty residue is strict staging partition: even screened, materialized candidates cannot become calibration input until human copying, verdict assignment, table update, and renewed scope approval. The register's teaching-away characterization is an argument for review, not a conclusion of legal nonobviousness.

For reconnaissance, Epoch AI Rosetta Stone, BenchEvolver arXiv 2606.01286, and PROPEL arXiv 2606.18284 make frontier tracking and benchmark evolution relevant. The asserted novelty residue is age-bounded independent corroboration coupled to append-only, demotion-only output that cannot authorize cohort membership or certification. This is the thinnest-searched mechanism in the register; further human prior-art review is necessary before any novelty conclusion.

The register supplies these named comparisons; this lane performs no network search and does not claim an exhaustive search or freedom-to-operate opinion. The combined PRISMA-S, GRADE, content-identity, and blinded-supersession arrangement remains a proposed distinction requiring claim-specific examination, not a presumption from the absence of an identical title.

### 8.14 Prevention register and technical effects

| Claims | Prevented operation | Mechanism and intended technical effect |
| --- | --- | --- |
| 1, 26, 27 | Opening a lower tier on unresolved retrieval | Require every-substrate exhaustion, preserving failed access as a gap |
| 1, 26, 27 | Admitting a source because discovery descends | Separate receipt authority from anchor admission authority |
| 1, 26, 27 | Exporting invalidation evidence to the author | Withhold the edge and target through deterministic field exclusion |
| 2-7 | Opening, admission, or export forbidden by claim 1 | Inherit claim 1's prevention rows while adding appraisal and resolution constraints |
| 8-14 | Accepting changed or incomplete corpus bytes | Recompute digests and compare pair and manifest identities |
| 15-18 | Relying on unjustified confidence or unlinked supersession | Cap confidence and refuse unsupported invalidation transitions |
| 19-22 | Substituting a design target for measured hardness | Version rows and keep target, composition, and success constraints separate |
| 23-25 | Self-admitting calibration or promoting reconnaissance | Deny machine library admission and upward authority from advisory output |

For Alice Step 2A Prong Two, claims 1, 26, and 27 integrate appraisal inputs into controls that prevent resource opening, deny admission, and withhold fields from a machine execution domain. Claims 8-14 additionally recompute and compare bytes. The asserted improvement is deterministic evidence integrity and information-flow control, not organizing scholarship or asking a model to rate trust. Step 2B rests on the ordered combination, not a generic processor or a digest alone. These are intended effects, not a representation of complete current enforcement.

For EPO Art. 52 and Guidelines G-II 3.3 and 3.3.1, mathematical confidence and threshold operations serve the specified purpose of controlling which byte-bound design inputs a benchmark-authoring process may consume. Projection exclusion changes machine-readable accessibility; digest comparison detects inconsistent retained evidence. Tier semantics alone may be nontechnical, so any inventive-step argument must identify the concrete refusal and access-control implementation rather than an improved review method.

For India s.3(k), independent system claim 1 addresses the technical problem of failed retrieval and invalidation metadata entering an authoring process as authoritative inputs. Its technical solution uses receipt-gated transitions and deterministic exclusion of edge and target bytes. In the Ferid Allani and Microsoft v. Assistant Controller vocabulary, the intended measurable technical benefit is reproducible refusal of unauthorized opening or admission and absence of forbidden fields from exported bytes; no novel hardware is required, and no measured benefit is asserted.

For India s.3(k), independent method claim 26 addresses the same technical problem through an ordered processor-executed sequence rather than a review policy. The technical solution records closed receipts before opening tiers, denies discovery-based admission, and computes the restricted output. Its intended measurable technical benefit is repeatable transition decisions and prevention of invalidation-data exposure under identical inputs, consistent with Ferid Allani and Microsoft v. Assistant Controller; no novel hardware is required.

For India s.3(k), independent storage-medium claim 27 addresses unauthorized evidence use and cross-domain exposure through executable instructions implementing those controls. The technical solution changes the processor's permitted operations and accessible output fields, not merely stored informational content. Its intended measurable technical benefit is the same reproducible refusal and excluded-field property under execution, in the Ferid Allani and Microsoft v. Assistant Controller vocabulary; no novel hardware is required and this is not a claim of measured deployment performance.

### 8.15 Scope, single-actor operation, and the permanently human acts

In some embodiments a single platform operator establishes the domains, configures the receipt and admission rules, maintains the stores, and operates the deterministic projector. Source publishers supply data, not claimed processor steps. A human-controlled calibration boundary can exist within that operator's organization without granting machine principals authority to perform the human admission acts.

In one implementation the file names, predicate strings, role names, refusal codes, tier labels, state labels, field spellings, vocabulary sizes, and numerals illustrate the architecture. They are not claim limitations. Functionally comparable data carriers and collision-resistant digest functions may implement the same controls. Changing terminology does not remove the required gating order or excluded data relationship.

The drafting party reconciles and never files. Filing is a human act, as are publication beyond the repository, operational acceptance against a capped disposition, and admission into the human-graded calibration library. No statement asserts any filing, deployment, or measured pass rate. The current disclosure is a draft grounded in contracts, implementation sources, tests, and dated history; it invents no memory-ledger digest. CONTRACT-ONLY (ENGRAM.md:294).

## 9. CLAIMS

What is claimed is:

**1. A system for controlling evidence inputs to machine-learning benchmark authoring, comprising:** one or more processors; one or more non-transitory memories storing instructions that cause the processors to maintain an evidence domain and an access-controlled authoring domain, assign source classes to ordered discovery tiers, record an immutable discovery receipt for each substrate invocation under a closed schema binding a verbatim issued query and a result-set digest, open a lower discovery tier only after every substrate of the immediately preceding tier records exhaustion, record an unexhausted lane as a named coverage gap rather than a clean empty result, deny evidence admission by descent alone, retain a superseded catalog row and a chainable supersession edge binding the row to target evidence with an evidence digest and an instant, and provide catalog information to the authoring domain only through a deterministic projection that structurally excludes both the edge and the target evidence.

**2.** The system of claim 1, wherein each admitted item carries an adjudication token selected from a closed set separately from its source-class tier.

**3.** The system of claim 2, wherein each admitted item carries provenance and a liveness token from a closed set, corroboration counts independent provenance rather than mirrored hosts, and a retired source's retained dated slice cannot establish current capability.

**4.** The system of claim 1, wherein an unresolved lower-authority item and a source that continues appending remain leads incapable of anchoring a catalog row until qualifying higher-authority evidence or a stable source slice, respectively, resolves and independently satisfies admission requirements.

**5.** The system of claim 1, wherein the receipt maps source identification, issued strategy, restrictions, filter and strategy provenance, update method, search instant, strategy review, record counts, and deduplication to respective published search-reporting checklist items, with an unmet item retained as a named gap and the receipt incapable of promoting a row or creating a certification record.

**6.** The system of claim 1, wherein official-review resolution uses a browser-minted clearance token limited by lifetime and client address, pins forum identity, note identity, modification time, and note-text digest, rechecks an edit log for later modification, and refuses a third-party dump as a substitute anchor.

**7.** The system of claim 1, wherein a source-class resolution ladder pins an evaluation-harness revision, records its answering rung, treats a name-similarity match as adjacent rather than resolved, and records a mutable-data-selector finding when the pinned harness loads data without an immutable revision.

**8.** The system of claim 1, wherein admitting an artifact requires retaining source bytes and a rendering derived from those bytes by a named tool at a pinned version under a common stem, and computing content identity from the retained bytes independently of storage location.

**9.** The system of claim 8, wherein an identity sidecar binds the source class, stem, member names, retained-byte digest, rendering digest, deriving-tool identity, and tool version, and the processors recompute the digests before accepting the pair as conformant.

**10.** The system of claim 9, wherein the processors refuse an artifact outside the source-class layout or within an unrecognized source class.

**11.** The system of claim 9, wherein the processors refuse a retained artifact without its rendering and a rendering without its retained artifact.

**12.** The system of claim 9, wherein the processors refuse a missing or unreadable sidecar, an unrecognized sidecar schema, and a sidecar containing an absent or additional field.

**13.** The system of claim 9, wherein the processors refuse inequality of either recomputed digest and its recorded counterpart or disagreement between a sidecar's class, stem, or member names and the pair's paths.

**14.** The system of claim 9, wherein the processors refuse an empty deriving-tool identity or version and decline to overwrite an existing identity sidecar.

**15.** The system of claim 1, wherein a catalog confidence level is seeded by anchor tier, adjusted through recorded downgrade and upgrade domains, capped by support from the highest-tier anchor, and denied authority to promote a row or substitute for execution measurement.

**16.** The system of claim 1, wherein supersession authority is limited to independently adjudicated or maintainer-adjudicated evidence, with first-party evidence permitted only as an admission against interest and unresolved secondary evidence denied such authority.

**17.** The system of claim 16, wherein a resolved forecast market bound to a named board and date can supply saturation evidence for supersession without constituting execution measurement.

**18.** The system of claim 16, wherein replacement or retirement is represented as a supersession-kind axis rather than an additional row state, a retraction re-tags the retained row as retired with the retraction identity as its edge target, a superseded row without its required edge fails closed, and the deterministic projection also excludes the supersession-kind axis.

**19.** The system of claim 1, wherein a machine-readable catalog supplies a row per lever with a schema version and a row version incremented upon content change, and regenerates a human-readable knob sheet byte-identically with a generated-content warning while refusing drift.

**20.** The system of claim 19, wherein a category target must exceed the strongest anchored evidence by a bound target-headroom multiple, author-side composition must exceed its governing floor by a separate composition-headroom multiple, and satisfaction of either multiple cannot substitute for satisfaction of the other or for execution evidence.

**21.** The system of claim 20, wherein a measured-success ceiling on a grouped-attempt success scale is bounded by a non-increasing policy limit that a stricter authorized input may lower but no source may raise.

**22.** The system of claim 20, wherein the authoring domain receives the catalog only through the deterministic projection, projected difficulty floors may only increase, and the catalog excludes budget and cost values.

**23.** The system of claim 1, wherein machine-proposed calibration bundles occupy a separate staging store under a closed candidate schema and are advisory only, with machine principals denied authority to insert the bundles into a calibration library or assign the library's authoritative verdicts.

**24.** The system of claim 23, wherein the processors prevent a staged bundle from serving as calibration input pending human-controlled copying into the library, assignment of a verdict, update of a verdict table, and renewed scope approval.

**25.** The system of claim 1, wherein parallel read-only reconnaissance records source and model identities, retrieval and source instants, and reported scores, admits a capability claim only within a bound source-age window and with corroboration across independent provenances, retains deficient claims as currency gaps in appended dated blocks, and permits the reconnaissance output only to open gaps, narrow standing, request registry refresh, or increase target requirements without declaring cohort membership, creating certification, restoring or expiring a lever, increasing a disposition, or clearing a flag.

**26. A computer-implemented method for controlling evidence inputs to machine-learning benchmark authoring, comprising:** maintaining, by processors, an evidence domain and an access-controlled authoring domain; assigning source classes to ordered discovery tiers; recording an immutable discovery receipt for each substrate invocation under a closed schema binding a verbatim issued query and a result-set digest; opening a lower discovery tier only after every substrate of the immediately preceding tier records exhaustion; recording an unexhausted lane as a named coverage gap rather than a clean empty result; denying evidence admission by descent alone; retaining a superseded catalog row and a chainable supersession edge binding the row to target evidence with an evidence digest and an instant; and providing catalog information to the authoring domain only through a deterministic projection that structurally excludes both the edge and the target evidence.

**27. A non-transitory computer-readable storage medium storing instructions that, when executed by processors, cause the processors to control evidence inputs to machine-learning benchmark authoring by operations comprising:** maintaining an evidence domain and an access-controlled authoring domain; assigning source classes to ordered discovery tiers; recording an immutable discovery receipt for each substrate invocation under a closed schema binding a verbatim issued query and a result-set digest; opening a lower discovery tier only after every substrate of the immediately preceding tier records exhaustion; recording an unexhausted lane as a named coverage gap rather than a clean empty result; denying evidence admission by descent alone; retaining a superseded catalog row and a chainable supersession edge binding the row to target evidence with an evidence digest and an instant; and providing catalog information to the authoring domain only through a deterministic projection that structurally excludes both the edge and the target evidence.

## 10. ABSTRACT OF THE DISCLOSURE

Systems and methods control evidence supplied to benchmark authoring processes. An evidence domain records immutable closed-schema discovery receipts binding issued queries and returned-set digests. A lower source tier opens only after every substrate of the preceding tier records exhaustion; unresolved access remains a named gap. Discovery does not confer admission authority. Admitted artifacts can retain source bytes and derived renderings under content identities. A catalog retains superseded rows and chainable edges to superseding evidence. An access-controlled authoring domain receives catalog information only through a deterministic projection excluding the supersession edges and their target evidence. Dependent controls include source appraisal, bounded confidence, versioned catalog rows, separate design headroom and measured-success constraints, human-controlled calibration admission, and freshness-bounded corroborated reconnaissance restricted to narrowing output. The architecture separates discovery, evidence integrity, design direction, and execution certification.
