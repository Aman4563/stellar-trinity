---
description: Run CRUCIBLE, the project auditor, from trinity/CRUCIBLE.md.
---

Read `trinity/CRUCIBLE.md` and run the audit flow, every phase it owns in order, stopping only at a named human gate, a terminal disposition, or a blocking gap. Operate from the parent project root, resolve every bare path there, and follow the contract end to end; this door defers to it, adds nothing to it, and restates none of it.

Run the parent gate at both moments, before any phase work and again before the root report, from the parent project root, the directory whose direct child is the `trinity/` submodule:

    just --justfile trinity/tools/justfile parent-gate instrument=CRUCIBLE moment=preflight
    just --justfile trinity/tools/justfile parent-gate instrument=CRUCIBLE moment=report
