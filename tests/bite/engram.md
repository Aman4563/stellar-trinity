# ENGRAM bite tests

Append-only discipline, human-write-only roots, and the rules separating evidence from opinion. Every scenario is decidable by reading files on disk.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| E1 | A measured CFER is overwritten in place with a corrected value. | Reject. Measured CFERs are never deleted or overwritten. | E3 | no |
| E2 | An agent writes a file into `requirements/`. | Reject. `requirements/` is human-write-only and read-only to every agent. | E9, ENGRAM.md:484 | no |
| E3 | A derived rendering lands in `research/` with no retained source bytes sharing its stem. | Reject. A rendering without its retained source is non-conformant. | E10, ENGRAM.md:486 | yes |
| E4 | A `research/` rendering is hand-authored rather than derived from the retained bytes. | Reject. The rendering is derived from the retained bytes and never hand-authored. | E10, ENGRAM.md:486 | no |
| E5 | A `research/` pair carries mismatched stems, or retained bytes whose SHA-256 differs from the recorded `content_digest`. | Reject. A mismatched stem is non-conformant, and identity is the digest over the retained bytes. | E10, ENGRAM.md:486 | yes |
| E6 | An agent writes a bundle into `touchstones/`. | Reject. An automated write into `touchstones/` is a conformance failure. | E12, E30, ENGRAM.md:488 | no |
| E7 | A staged harvest candidate is cited as screening evidence. | Reject. A staged candidate carries no authority and a proposal that grades itself is a self-attestation loop. | E30, ENGRAM.md:507 | no |
| E8 | A harvest suggested label is consumed as a human verdict. | Reject. A suggested label is advisory prose, never a verdict. | E30, ENGRAM.md:235 | no |
| E9 | `HARDNESS.md` on disk differs from the bytes regenerated out of `.memory/hardness.yaml`. | Cap at `BROKEN`. Drift between the emitted catalog and its source caps the state. | E23 | no |
| E10 | A hardness row is promoted by editing `HARDNESS.md` directly. | Reject. The catalog may only lower or cap, never promote, and regenerates from `.memory/hardness.yaml`. | E23 | no |
| E11 | An agent writes the disposition `accepted` into `.memory/feedback.yaml`. | Reject. Only the human writes `accepted` or `rejected`. | E32 | no |
| E12 | A feedback entry stores a paraphrase in the verbatim field. | Reject. Verbatim is immutable and never paraphrased. | E32 | no |
| E13 | A budget is enforced with no declaration in `requirements/` and no standing `budget:required`. | Reject. A budget applies only when `requirements/` declares one or the escalation already stands. | E34, FORGE.md:417 | no |
| E14 | A duration field arrives unsigned and is accepted as evidence. | Fail closed. An unsigned duration field or an envelope mismatch fails closed. | E34 | no |
| E15 | A self-attested ingest is recorded as `CURRENT`. | Reject. Self-attested ingests cap below `CURRENT`; only a detached external signature from an authorized issuer reaches it. | E4 | no |
| E16 | A seed row alone marks a lever `ACTIVE`. | Reject. Seed is memory, not measurement. No seed row alone makes a lever active. | E5 | no |
| E17 | A Bucket N observation mints a CFER or promotes a state. | Reject. Bucket N narrows only and may not invent CFERs, promote states, or extend horizons. | E7 | no |
| E43 | A `T3` item is admitted as an anchor while a `T1` substrate's receipt still stands `unexhausted`. | Reject. A tier opens only after every substrate of the tier above records an `exhausted` receipt, and the unexhausted lane is a named coverage gap. | ENGRAM.md:234 | no |
| E44 | A substrate answers with a challenge or a rate limit, the run records zero rows, and the lane reports clean. | Reject. A failed lane leaves its tier `unexhausted` with the reason recorded; descent from it proceeds for discovery alone. | ENGRAM.md:234 | no |
| E45 | A `T7` social post is recorded as a row's resolved anchor. | Reject. A row whose anchor stands at `T7` or `T0` is `CANDIDATE`, only a design prompt, and never counts toward a tier. | ENGRAM.md:242 | no |
| E46 | A Phase H invocation queries a substrate and writes no `engram.receipt/v1` record for it. | Reject. One receipt per substrate per invocation, and a search nobody recorded is a claim about recall rather than a measurement of it. | ENGRAM.md:240 | no |
| E47 | A row stands `SUPERSEDED` with no `engram.supersession/v1` edge naming its `target_ref`. | Cap at `BROKEN`. Every `SUPERSEDED` row resolves exactly one edge, and a tombstone is a permanent marker rather than an erasure. | ENGRAM.md:212 | no |

## Additional evidence-integrity scenarios

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| E18 | An IRT or latent-ability estimate declares a task hard before measurement. | Reject. Derived estimates are never primary evidence and may never declare a task hard pre-measurement. | E15 | no |
| E19 | A required Bucket D instrument demonstrates only its negative control on frozen fixtures. | Reject. Both decision halves must fire. Negative controls alone cannot distinguish a working instrument from an inert one. | E19 | no |
| E20 | An authored probability or a model opinion is recorded as raw difficulty evidence. | Reject. Only a signed pilot outcome over frozen bytes against a frozen solver registry is raw evidence. | E1 | no |
| E21 | A CFER is recorded with no measurement date or no named cohort. | Reject. Every CFER carries a measurement date and a named cohort. | E2 | no |
| E22 | A CFER is recorded with no traceable proof digest. | Reject. Every CFER traces to a verifiable proof digest. | E8 | no |
| E23 | A freshener queries the live world during a run. | Reject. Freshener output is pure and bit-identical over a defined closure. | E6 | no |
| E24 | An agent writes a file into `brief/` and the run proceeds on the new value without re-triggering Phase 0.5. | Reject. A brief write moves a bound digest and invalidates the standing approval. | E9a | no |
| E25 | A brief names `budget_hours` as a value rather than as a named gap. | Reject. A budget is a grant and lives in `requirements/` alone. | E9a | no |
| E26 | A brief field and a `requirements/` field name the same setting and the brief value is applied. | Reject. `requirements/` wins and the brief value is recorded as superseded. | E9a | no |
| E27 | A reported baseline carried from a paper into a brief is cited as difficulty evidence. | Reject. A reported baseline is the paper's claim, never a measurement. | E1, step 2d | no |

## Feedback capture and chain integrity

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| E28 | A run receives a human turn and appends no record to `.memory/feedback.yaml`. | Reject. Capture is unconditional and the omission is a named coverage gap, because an empty ledger is evidence of a defect. | ENGRAM.md:118 | no |
| E29 | A bare contract re-paste is treated as capturing nothing. | Reject. A re-paste is captured under the `contract_paste` kind like every other turn. | ENGRAM.md:118 | no |
| E30 | A ledger record carries a `chain_seq` no line in `.memory/feedback.chain.jsonl` claims. | Reject. Every record is attested by exactly one chain line written in the same act. | ENGRAM.md:120 | no |
| E31 | A chain line is edited so its `entry_hash` no longer covers its own fields. | Cap at `BROKEN`. The walk fails, no phase work proceeds, and `DIRECTIVE.md` is emitted flagged. | ENGRAM.md:130 | yes |
| E32 | A chain line is deleted so `seq` skips a value. | Cap at `BROKEN`. `seq` is dense and monotonic from one, so a deletion breaks the walk. | ENGRAM.md:130 | yes |
| E33 | An `anchor_ceiling` is used to declare a task hard. | Reject. Derived estimates may never declare a task hard under E15 and E35. | ENGRAM.md:512 | no |
| E34 | A fitted time-anchor mapping value crosses `CRUCIBLE_VIEW`. | Reject. `CRUCIBLE_VIEW` carries exactly its listed fields and nothing else. | ENGRAM.md:388 | no |
| E35 | A per-task `task_cost` is written into `.memory/economics.yaml`. | Reject. Economics memory stores aggregate revisions and no per-task row. | ENGRAM.md:513 | no |
| E36 | Two `cost_outcome` groups resolved under different rate cards are folded into one average. | Reject. A differing `rate_card` digest opens a new aggregate and retains the prior one. | ENGRAM.md:248 | no |
| E37 | A per-lane token total is projected through `FORGE_VIEW`. | Reject under E31 and E36. Token totals cross neither view. | ENGRAM.md:408 | no |

## Task lane shells

ENGRAM registers `.memory/`, `samples/`, `delivery/`, and `harness/` as submodules against distinct remotes and authors nothing inside a bundle shell. These two rows hold that ownership line where the third shell was added.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| E38 | Genesis registers `samples/` and omits the `delivery/` shell, or scaffolds a lane root as a plain directory. | Reject. ENGRAM registers both lane roots as submodules; `check_parent_layout` holds at PARENT_LAYOUT_SUBMODULE_MISSING or PARENT_LAYOUT_PLAIN_DIRECTORY. | ENGRAM.md:311, `tests/test_layout.py::test_missing_submodule_registration_is_refused` | yes |
| E39 | ENGRAM authors a bundle inside the `delivery/` submodule checkout at `delivery/<uuid>/`. | Reject. ENGRAM owns the shells and FORGE owns every contained bundle. | ENGRAM.md:514 | no |

## Inferred-hardness projection

These rows fit the suite's evidence and ledger scope because both failures are decidable from `.memory/strata.yaml` and the recorded projection inputs.

| ID | Scenario | Expected refusal | Source | CI |
| --- | --- | --- | --- | --- |
| E40 | An inferred-hardness projection consumes an unsigned stratum row. | Reject. Every projected hardness fact must have an external signature at its root. | ENGRAM.md:249 | no |
| E41 | A cohort refresh supersedes a stratum bound, but the bound and its derived certificate remain `CURRENT`. | Reject. The stale input makes every derived certificate stale and caps the next FORGE invocation at `HOLD:PILOT_REQUIRED`. | ENGRAM.md:515 | no |
| E42 | The design-return lane treats a return's declared composition or `composition_headroom` as evidence the task is hard, edits a return, or lets a return cross into `CRUCIBLE_VIEW`. | Reject. A return is a declaration FORGE made; the lane may mark `return-target-stale`, `return-budget-unanchored`, or `return-headroom-short`, open a gap, or set `WATCH`, and never mints a CFER, raises a disposition, or projects a return to the auditor. | ENGRAM.md:257 | no |

## Notes

E9 and E10 together are the only mechanism preventing the hardness catalog from being edited into a stronger claim. They rest entirely on byte-identical regeneration, which nothing in the repository performs today.

E2 is the invariant an arXiv ingestion lane would break if it wrote `requirements/` directly. The corpus states this rule four separate times, in ENGRAM.md:9, FORGE.md:10, CRUCIBLE.md:10 and README.md:98, plus the named invariant at ENGRAM.md:484. That redundancy is deliberate.
