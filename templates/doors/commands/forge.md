---
description: Run FORGE, the task-authoring instrument, from trinity/FORGE.md.
---

Read `trinity/FORGE.md` and run the task-authoring flow, every phase it owns in order, stopping only at a named human gate, a terminal disposition, or a blocking gap. Operate from the parent project root, resolve every bare path there, and follow the contract end to end; this door defers to it, adds nothing to it, and restates none of it.

Run the parent gate at both moments, before any phase work and again before the root report, from the parent project root, the directory whose direct child is the `trinity/` submodule:

    just --justfile trinity/tools/justfile parent-gate instrument=FORGE moment=preflight
    just --justfile trinity/tools/justfile parent-gate instrument=FORGE moment=report
