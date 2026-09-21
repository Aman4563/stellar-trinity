# 0005. Run lifecycle, terminal closure, and subject-bearing receipts

## Status

Accepted. This decision precedes the rerun-efficiency integration and contract edits; it does not itself change code or contract bytes.

## Date

2026-09-21

## Context

A re-paste resumes a run, but the current Card close sentences in ENGRAM rule 8, FORGE rule 9, and CRUCIBLE rule 8 require every invocation to emit a frozen card whatever its lawful stop. Those requirements conflict when a run pauses for a human and later changes its report or progress. In `./tools/tracker.py`, `write_card` freezes derived fields and the SHA-256 digests of `run.json`, `report.md`, and `progress.yaml`. An identical emission preserves the original card; changed source bytes cause `TRACKER_CARD_CONFLICT`. In `./tools/tracker_card.py`, `read_card` validates those bindings against current bytes rather than trusting a historical claim. Neither implementation supports a mutable invocation card.

In `./tools/subject.py`, `OUTPUT_NAMES` excludes only the run-root output names `disposition.json`, `report.md`, `progress.yaml`, `TODO.md`, and `tracker.json`, and `OUTPUT_DIRS` excludes `gate-receipts/`. Phase receipts and feedback remain subject-bearing. Writing either after qualification changes the closure that qualification binds. A hypothetical in-run `meter.json` would also change it. The solution must fix lifecycle and ordering without broadening exclusions or making derived state authoritative.

In `./tools/tracker_cache.py`, a missing card produces closure `open` with no `closed_at`, a valid bound card produces `closed`, and an unreadable or invalid card produces `unknown`. The dashboard labels duration "run elapsed, including waits" in `./tools/dashboard.py`. These semantics already permit a run to wait without pretending that it has closed or that elapsed time measures active computation.

## Decision

### 1. A human gate pauses the same run; only terminal closure freezes its card

**Decision.** A lawful stop at a human gate or the commit gate is a PAUSE, not terminal closure. A pause leaves the card unfrozen, meaning no `tracker.json` is emitted, and the run retains its `run_id` across re-pastes. Terminal closure occurs at a terminal disposition, a blocking gap, or the final report moment of the last phase of the invoked branch. At that terminal report moment, finish the report and progress bytes before emitting the frozen card. A commit gate alone does not cause closure; if terminal closure already occurred before that gate, waiting for the human commit does not reopen the run or permit changing its frozen sources.

**Rejected alternatives.** Freezing on every invocation makes legitimate continuation conflict with the write-once binding. Opening a new run at every human stop fragments one run merely to avoid that conflict. Rewriting, deleting, or silently repairing a frozen card would erase the terminal statement rather than resolve it. No card is silently repaired, and no new run is minted to evade `TRACKER_CARD_CONFLICT`. The tracker module's description of a human opening a new run is not permission to relabel paused continuation; a genuinely distinct later run must not disguise mutation of an already frozen run.

**Consequences.** A paused run remains `open` in the dashboard's Aging work, including its waiting time; an invalid existing card stays `unknown`, not a repaired `open` or an assumed `closed`. W4 must explicitly reword all three Card close sentences at `./ENGRAM.md` rule 8, `./FORGE.md` rule 9, and `./CRUCIBLE.md` rule 8: replace "Card close: every invocation, whatever its lawful stop, closes by emitting..." with "Card close: every run closes at terminal closure by emitting...". Their write-once and refusal rules remain intact. This ADR records that required contract change without making it here.

### 2. Phase receipts stop changing before the report-moment gate call

**Decision.** Within each invocation, every write to `./<harness>/runs/<run_id>/phases/` must finish BEFORE the report-moment gate call. The gate binds the resulting stable subject closure; no phase receipt may be created, replaced, or otherwise changed after that call in that invocation. `phases/` does NOT join `OUTPUT_DIRS`. A later invocation of a still-paused run may write receipts only before its own fresh report-moment gate call, never by treating the previous qualification as current across changed subject bytes.

**Rejected alternatives.** Excluding `phases/` would change the existing subject hash domain merely to accommodate a writer's timing. Writing receipts after the gate and hoping that qualification remains valid contradicts the disk-derived closure. Treating receipts as authority for completion would bypass current evidence, approval bindings, signatures, and reproducible checks.

**Consequences.** `progress.py close` after the report moment is a refusal, not a late receipt write or an implicit gate rerun. W2-PROGRESS and the W4 call sites must implement and test this ordering. No `./tools/subject.py` exclusion change or subject-digest migration is needed for this decision. Receipts and progress remain derived accelerators: neither a receipt nor its absence decides completion, and a missing cache triggers authoritative reconstruction rather than a silent no-op.

### 3. Continuation feedback precedes qualification, and humans commit source paths first

**Decision.** The lawful sequence within one invocation is `feedback append -> gate (preflight moment) -> phase work -> phase receipts -> gate (report moment) -> report -> commit gate`. Feedback includes the continuation re-paste and its required chain and checkpoint writes before qualification binds those bytes. A lawful earlier human stop pauses this sequence; it does not authorize skipping checks on the next invocation. Every resumed invocation reruns the never-skip checks, including freshness and FORGE's required placement and reconciliation, and reconstructs the earliest valid resume point from current evidence.

**Rejected alternatives.** Appending continuation feedback after the report-moment gate invalidates its bound subject. Excluding feedback to preserve an old qualification hides a binding input. Committing first and then appending feedback while treating the earlier clean tree as the qualified tree creates the same defect. Having a tool or hook stage or commit generated files would violate human ownership of history.

**Consequences.** No feedback file is excluded from the subject closure: the ledger, chain, checkpoint log, and signature remain included. A re-paste after a human commit legitimately dirties the namespace and requires fresh qualification over the appended bytes before its report. At the commit gate, present paths grouped by repository; the human commits the run namespace paths first, respecting submodule ownership, then any root report and tracker paths the hooks rendered. Root reports and `TRACKING.md` remain rendered, never hand-patched. Hooks may render working-tree bytes and name paths for review, but no tool or hook stages, commits, amends, or pushes. The report-moment binding concerns subject bytes, not a promise that feedback leaves the tree clean.

### 4. A frozen card describes the run's terminal state, not an invocation

**Decision.** The card is a derived statement of the run's terminal state over its final `run.json`, `report.md`, and `progress.yaml`, not a checkpoint for each paste. Its `closed_at` is write-once per run. Re-emitting over identical source bytes and derived fields is an idempotent no-op preserving that instant. Changed sources refuse with `TRACKER_CARD_CONFLICT`; malformed or unbound cards remain visible as a refusal and unknown closure rather than becoming trustworthy through rendering.

**Rejected alternatives.** An invocation timestamp or a refreshed `closed_at` on every render would conflate pauses with closure and make an unchanged tree produce new history. A mutable card would contradict both `write_card` and `read_card`. Using a card to select work or justify a disposition would turn a derived dashboard projection into authority and potentially an inter-instrument channel.

**Consequences.** Waiting time is part of run elapsed time, not evidence of compute cost or reconstruction efficiency. Keep telemetry separate from deterministic decision data; `closed_at` is recorded, never hashed as a binding input or regenerated from the render-time wall clock. No run reads its own or a peer's tracker card as decision input. The existing `CARD_KEYS`, `trinity.run/v1`, final disposition fields, bundle routing, and queue semantics are unchanged. The gate remains the only minter of local BLOCK, HOLD, and SHIP_ELIGIBLE dispositions; no pause label or preflight receipt adds a disposition.

### 5. Metering output lives outside every harness namespace

**Decision.** `meter.json` lives nowhere inside any harness namespace. T7 is an external measurement harness and writes only to a caller-supplied `--out` path outside every harness root, including `./.memory/`, `./.seed/`, `./.audit/`, `./.trial/`, and `./.podium/`. An in-harness `--out` is refused with `METER_PATH_IN_HARNESS`, not redirected or written anyway. External to the harness does not mean outside the governed project: authored paths still begin with `./`, containment uses the project path rules, and symlink traversal must not bypass the refusal.

**Rejected alternatives.** Placing telemetry beside run receipts makes measurement itself alter the measured subject closure. Adding `meter.json` to `OUTPUT_NAMES` would widen the exclusion policy to accommodate unrelated external telemetry. A shared in-harness measurement cache would also risk a cross-instrument channel.

**Consequences.** W3-METER must enforce the output-path refusal before writing and keep measurement separate from qualification and completion. Measuring cold and warm runs cannot mutate either run namespace or supply evidence of phase completion. No subject exclusion is added for telemetry, and the external location is an accepted decision, not a default that later tasks may silently reverse.

## Alternatives considered

Each numbered decision records its rejected alternatives and the invariant each would break. Together the decisions choose same-run pause and strict pre-report ordering over per-invocation freezing, conflict-driven run replacement, mutable cards, or a larger subject exclusion set. Existing code supports that choice; the incompatible requirement is the contracts' every-invocation Card close timing, whose W4 correction is explicit above.

## Consequences

This record creates no implementation claim. Later tasks that touch subject closure, tracker-card timing, or feedback ordering must cite this ADR and enforce the relevant ordering and refusal with tests. W2-PROGRESS owns the late-close refusal, W3-METER owns `METER_PATH_IN_HARNESS`, and W4 owns terminal-only Card close wording and ordered call sites. None may weaken the information barrier, reuse stale approvals, repair a frozen card, or infer a clean run from absent evidence. This change creates only `./docs/adr/0005-run-lifecycle-closure.md`; code and contract bytes stay untouched.

## Reversal cost

Low before integration, substantial afterward. Reversal would require a new lifecycle decision, coordinated contract and writer changes, and an explicit treatment of existing immutable cards and subject bindings. It must not retroactively rewrite `closed_at`, silently repair cards, or introduce a subject exclusion without stating its digest and revalidation consequences.
