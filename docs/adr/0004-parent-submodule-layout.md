# 0004. The parent submodule roster and its need-to-know boundaries

## Status

Accepted.

## Date

2026-09-18

## Context

Commit `b49f381`, whose message is `Git Dirty`, demoted `samples/` and `delivery/` from submodules of the parent to plain directories, and it made that demotion in every place at once: `GATED_SUBMODULES` in `tools/gate.py`, ENGRAM Phase G step 8, FORGE invariant 35, `README.md`, `docs/migrations.md`, and the tests that pinned them. No sentence in that commit records a decision, and none of the three boundaries it crossed was named.

The demotion folds two audiences into one history. `samples/` is the public marketing root and `delivery/` is the private corpus root, so one repository now carries both, and publishing the public root publishes the private corpus with it. Need-to-know between the two lanes stops being a repository boundary and becomes a promise about which directory a human copies.

The same demotion leaves `.memory/` resident in the parent history, which is the breach ADR 0002 identified. CRUCIBLE is ordered to inventory the parent project tree, to treat full git history as a deliverable surface, and to run a full-history secret scan, and `G-CON-STRIP` in `CRUCIBLE.md` step 8i refuses recoverable history in every unpacked layer. A mandated full-history walk over a parent that holds `.memory/` reaches `HARDNESS.md` and `.memory/hardness.yaml` whatever the contract says about opening them by name. ADR 0002 adopted option 1 on 2026-08-26, which relocates those bytes behind the boundary CRUCIBLE already does not cross, and no code ever required that boundary to exist. The barrier stayed a naming convention for twenty-three days.

The third defect predates `b49f381`. Rollout evidence lived in a mirror tree at `deliverables/<uuid>/trajectories/`, keyed by the same uuid as the bundle it graded but resident under a different root, so a bundle could be placed, reconciled into the other lane, or exported while its evidence stayed behind. A mirror keyed by convention is a boundary nothing holds.

## Decision

Close the parent layout behind one table, one registered check, and a need-to-know forbidden set per root. `tools/layout.py` holds the table, `check_parent_layout` in `tools/integrity.py` is the check, and it is registered in `QUALIFICATION_CHECKS` immediately after `check_parent_submodule`, so the trinity-only freshness check keeps its slot and the roster check reads as its generalization.

Five roster roots are required and `staging` is optional, each registered as a submodule with `branch = main` and `update = merge` against its own remote, distinct from every other roster remote. The parent records each root by gitlink alone and tracks no bundle byte of its own. This table is transcribed from `LAYOUT_ROSTER` in `tools/layout.py`, in the roster's own order, which is load-bearing because `PROTECTED_ROOTS` and the branch-protection order derive from it.

| Root | Kind | Gitlink required | Audience | Forbidden inside the checkout |
| --- | --- | --- | --- | --- |
| `trinity` | `TOOLING` | yes | `VENDORED` | nothing |
| `.memory` | `HARNESS` | yes | `INSTRUMENT` | a bundle-shaped directory, `.seed`, `.audit`, `.trial`, `.podium`, `trinity`, `samples`, `delivery`, `deliverables` |
| `samples` | `BUNDLE_PUBLIC` | yes | `PUBLIC` | `BUNDLE_FORBIDDEN` |
| `delivery` | `BUNDLE_PRIVATE` | yes | `CORPUS` | `BUNDLE_FORBIDDEN` |
| `harness` | `RUNNER` | yes | `PUBLIC` | `.memory`, `.seed`, `.audit`, `.trial`, `.podium`, `trinity`, `samples`, `delivery`, `deliverables`, `requirements`, `touchstones`, `HARDNESS.md`, `.secrets` |
| `staging` | `STAGING` | no | `CORPUS` | `BUNDLE_FORBIDDEN` |

`BUNDLE_FORBIDDEN` in `tools/layout.py` holds twelve entries: `.memory`, `.seed`, `.audit`, `.trial`, `.podium`, `trinity`, `requirements`, `touchstones`, `deliverables`, `.secrets`, `.trinity-runtime`, and `HARDNESS.md`. A directory-form entry matches on path-segment equality at any depth, so `samples/<uuid>/.memory/` is as much a leak as `samples/.memory/`, and a file-form entry matches on basename equality at any depth. A bundle that ships a file named `HARDNESS.md` for its own reasons is refused, and the operator renames it; the module docstring in `tools/layout.py` records that known false positive. `trajectories` is absent from every forbidden set because it is now lawful bundle content, `deliverables` is present in every forbidden set because a stray mirror tree inside a checkout is a leak of the retired layout, and `solution/` is absent from every forbidden set because a bundle legitimately carries it and it is private at mount time, not at repository level. `PROTECTED_ROOTS` is every roster path except `trinity`, whose branch protection is upstream's responsibility and whose remote `check_submodule_canonical_remote` already governs.

The `harness` root alone may be a trinity project in its own right, so that its Engineering lane can run CRUCIBLE inside it and fast-track its own delivery without waiting on the parent's audit cycle. `is_trinity_project_root` in `tools/layout.py` recognizes that shape by the same rule the README uses to define a project root: the checkout's own `.gitmodules` registers a submodule at exactly `trinity`, that submodule is checked out with its `.git` metadata present, and `tools/gate.py` is a regular file inside it, with a symlink anywhere on that path answering no. Root reports or an `AGENTS.md` at the checkout root prove nothing and exempt nothing. When the rule holds, `check_parent_layout` does not enter that checkout: its `.audit/` belongs to its own CRUCIBLE, and its layout is its own gate's finding rather than the parent's. The exemption is bound to `RootKind.RUNNER`, so a bundle, memory, or staging root that vendors `trinity/` is still the leak the roster names, and the `harness` root's own registration, remote, branch, and symlink checks are unchanged.

ADR 0002 option 1 becomes mechanical here. `check_parent_layout` requires a mode `160000` index entry for `.memory`, so a parent that keeps ENGRAM's ledger as a plain directory is refused, and the hardness contract sits in a history a parent-only clone never carries. The same check refuses a `HARDNESS.md` or `.memory` path resident inside any roster checkout, which closes the copy-it-back route the relocation alone left open. `HARNESS_ROOTS` in `tools/integrity.py` is unchanged: `.memory` is the same path whether it is a mount point or a plain directory, and the gitlink requirement lives in one place.

The severity line is stated once in the module docstring of `tools/layout.py` and it is the reason the twelve codes split five to seven. An incomplete or retired registration is an unfinished scaffold and holds, because every parent carries one until genesis completes. A crossed or collapsed boundary is evidence and blocks. The codes, their ceilings, and the sentinel column below are transcribed from `LAYOUT_CODES` and `BLOCKING_CODES` in `tools/layout.py`, from `BLOCK_CODES` and `is_block_code` in `tools/gate.py`, and from `FINDING_CODE_MAP` in `tools/sentinel.py`.

| Code | Fires when | Ceiling | Sentinel classification |
| --- | --- | --- | --- |
| `PARENT_LAYOUT_GITMODULES_INVALID` | `.gitmodules` is absent or unreadable, a section lacks `path` or `url` or repeats a key, a roster path is registered twice, or a registration path is absolute, contains `..` or an empty segment, or is nested under a roster root | HOLD | absent |
| `PARENT_LAYOUT_SUBMODULE_MISSING` | a required roster root has no declared `[submodule]` section | HOLD | absent |
| `PARENT_LAYOUT_PLAIN_DIRECTORY` | a declared roster root carries no mode `160000` index entry | HOLD | absent |
| `PARENT_LAYOUT_BRANCH_INVALID` | a roster section declares a branch other than `main` or an update policy other than `merge` | HOLD | absent |
| `PARENT_LAYOUT_RETIRED_ROOT` | `deliverables` is a gitlink, or a directory holding any entry | HOLD | absent |
| `PARENT_LAYOUT_RUNTIME_UNIGNORED` | the parent `.gitignore` omits `.secrets/` or `.trinity-runtime/` | HOLD | absent |
| `PARENT_LAYOUT_SCAN_TRUNCATED` | the boundary scan reached `SCAN_MAX_ENTRIES`, or the index, a checkout, or a directory within a checkout was unreadable | HOLD | absent |
| `PARENT_LAYOUT_UNKNOWN_SUBMODULE` | the parent index holds a gitlink outside `KNOWN_ROOTS` | BLOCK | `SAB_SUBMODULE_TAMPERED` |
| `PARENT_LAYOUT_SHARED_REMOTE` | two roster roots normalize to one remote | BLOCK | `SAB_SUBMODULE_TAMPERED` |
| `PARENT_LAYOUT_PARENT_TRACKS_BUNDLE` | the parent index holds a non-gitlink entry under `samples/` or `delivery/` | BLOCK | `SAB_SUBMODULE_TAMPERED` |
| `PARENT_LAYOUT_BOUNDARY_LEAK` | a forbidden path is resident in a roster checkout, or the parent index tracks a `.secrets/` or `.trinity-runtime/` entry | BLOCK | `SAB_SUBMODULE_TAMPERED` |
| `PARENT_LAYOUT_SYMLINK` | a roster root is a symlink, or a symlink is met inside a checkout | BLOCK | `SAB_SUBMODULE_TAMPERED` |

HOLD and BLOCK are not severities in `tools/_findings.py`, which carries `ADVISORY` and `ERROR` alone. The ceiling column is the disposition `gate.ceiling` computes, and `is_block_code` blocks on the closed `BLOCK_CODES` set, which is `layout.BLOCKING_CODES`, in addition to the `SAB_`, `RELEASE_`, and `TRINITY_FRESHNESS_` prefixes it already blocked on. The seven holding codes are deliberately absent from `FINDING_CODE_MAP`, carrying the in-file comment that an absence is never evidence of intent, on the precedent `LEDGER_CHECKPOINT_CHAIN_INVALID` set in the same map.

`deliverables/` is retired into the bundle. Every bundle is complete where it lives: `samples/<uuid>/` and `delivery/<uuid>/` each carry the task and its rollout evidence under `<lane>/<uuid>/trajectories/`, lanes stay disjoint, and `check_bundle_layout` requires a `trajectories/` directory on every placed lane bundle. `deliverables` is named in `RETIRED_ROOTS` in `tools/layout.py`, and the asymmetry between its two codes is deliberate: `deliverables/` at the parent root is `PARENT_LAYOUT_RETIRED_ROOT` at HOLD because it is a migration state, while `deliverables/` inside a roster checkout is `PARENT_LAYOUT_BOUNDARY_LEAK` at BLOCK because it is a breach.

Bundle identity must not move when evidence is added, so `BUNDLE_EVIDENCE_DIRS` in `tools/bundle_identity.py` is the single-entry frozen set `{"trajectories"}`, and `bundle_digest` passes it to `tree_manifest` as `exclude_top_level`. `IDENTITY_VERSION` stays at `trinity.bundle-identity/v1` and is not bumped, because no existing bundle carries a top-level `trajectories/` directory and every existing digest is therefore byte-identical under the new rule. The exclusion is top-level only, so a bundle's own `tests/trajectories/` is still hashed, and `tests/test_bundle_identity.py::test_bundle_digest_is_stable_when_trajectories_are_added` holds both halves of that claim. `release_snapshot_digest` is unchanged and its value legitimately moves, because it binds every byte under the lane root, so a parent that adds trajectories re-signs through the ordinary `needs_revalidation` path in `docs/migrations.md`.

The retirement makes a public root carry rollout evidence, which reads as a contradiction until the word private is separated into the three independent axes it carries. `FORGE.md` calls trajectories private on the first two axes and never on the third. This table is the one place the three are stated together.

| Axis | What private means on it | Governed by | Status under this decision |
| --- | --- | --- | --- |
| Agent-private at mount time | The solver under test never sees `solution/` or `trajectories/` | FORGE item 11 leak gate, item 11a canaries, and item 10h delivery closure | Unchanged, and the `harness/` extension must now also expose no `trajectories/` path to the agent |
| Instrument-firewalled | `FORGE_VIEW` and `CRUCIBLE_VIEW` forbid rollout bytes in full | The ENGRAM projection firewall | Unchanged in force and re-pathed only, from `deliverables/<uuid>/trajectories/` to `<lane>/<uuid>/trajectories/` |
| Publication | `samples/` is the public marketing root and `delivery/` the private corpus root | A human request alone, never a tool | Trajectories are evidence the public root lawfully shows, because a frontier model failing is the marketing claim |

`solution/` is private on axes 1 and 3. `trajectories/` is private on axes 1 and 2, and public on axis 3 when it is resident under `samples/`.

## Consequences

- **A parent-only clone no longer carries the hardness contract, and absence is a fail-closed condition.** ADR 0002 stated this for the relocation; the gitlink requirement now makes it the only lawful shape. Tooling that assumes `.memory/` is present in a shallow or non-recursive clone holds instead of guessing, and the bound is honest: `check_parent_layout` returns no finding when the parent has no `.git` at all, because `integrity.py parent` audits whichever directory it is handed and hundreds of non-git fixtures are lawful inputs.
- **The information barrier is now enforced in two places instead of one.** The `.audit/` citation scan catches an auditor whose recorded evidence cites a forbidden path, and the roster boundary catches a parent whose repository shape lets the mandated traversal reach those bytes at all. Neither closes the runtime channel of one agent session holding both roles, which ADR 0002 recorded as its fifth consequence and which stays a declared residual risk.
- **Genesis and every adopter gain a remote-creation obligation no tool can discharge.** Each roster root needs its own remote, and creating a remote is a governance act. `docs/migrations.md` names the human step for a parent holding a lane root as a plain directory and for a parent still holding `deliverables/`, states that no matrix row performs either change, and names the code the gate holds at until the work lands. `migrate.py` gets no matrix row and no code change.
- **Rollout evidence and the bundle it grades can no longer drift apart.** They move together because they are one directory, and the move changes no bundle identity. The cost is that `release_snapshot_digest` moves whenever trajectories are added, which is correct, because trajectories now ship in the export.
- **Seven of the twelve codes are invisible to the sentinel by design.** A parent mid-genesis, a parent that has not yet written its `.gitignore`, and a parent whose scan hit its entry bound all hold without being recorded as evidence of intent. Only the five boundary codes reach `SAB_SUBMODULE_TAMPERED`, and a repeat of one of those is what the sentinel counts.
- **Out of scope and carried forward unfixed: the eleven-versus-ten doc-spine drift that the first consequence of ADR 0002 predicted.** `SPINE` in `tools/integrity.py` holds ten entries, `INDEX.md`, `CHARTER.md`, `ARCHITECTURE.md`, `PIPELINE.md`, `TAXONOMY.md`, `GLOSSARY.md`, `RESEARCH.md`, `GROUNDING.md`, `ASSURANCE.md`, and `OPERATIONS.md`, and it excludes `HARDNESS.md`, while `ENGRAM.md` and `README.md` both still describe an eleven-file spine with `HARDNESS.md` as its one generated member. The linter and the prose disagree by exactly one file, the linter is the side that matches this decision, and reconciling the count is a separate change to the doc-spine doctrine that this decision does not make.

## Reversal cost

High, and higher than ADR 0002's, because this decision is enforced. Reverting means deleting `check_parent_layout` and its registration, deleting `tools/layout.py` together with the four `.gitmodules` parsers that now route through it, restoring `deliverables` to `SHARED_DIRS`, `PARENT_SHARED_DIRS`, and the work-digest roots, and reabsorbing five submodule histories into the parent. Every adopter that fast-forwarded onto the roster has created five remotes and re-pointed its clone workflow, so a reversal is a coordinated change across every adopter and not one commit here. The `BUNDLE_EVIDENCE_DIRS` exclusion reverses cheaply on existing bytes, since no bundle predating it carries a top-level `trajectories/`, but any bundle placed after it would lose its evidence from the hash domain on the way back and would need a fresh identity.
