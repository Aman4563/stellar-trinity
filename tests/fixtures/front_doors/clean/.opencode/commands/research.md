---
description: Run the ENGRAM genesis research pass over the shared research corpus.
---

Read `trinity/ENGRAM.md` and run the genesis research pass Phase G step 7 names, under the Phase H step 2 protocol. Operate from the parent project root, resolve every bare path there, and follow the contract end to end; this door defers to it, adds nothing to it, and restates none of it.

Run the parent gate at both moments, before any phase work and again before the root report, from the parent project root, the directory whose direct child is the `trinity/` submodule:

    just --justfile trinity/tools/justfile parent-gate instrument=ENGRAM moment=preflight
    just --justfile trinity/tools/justfile parent-gate instrument=ENGRAM moment=report
