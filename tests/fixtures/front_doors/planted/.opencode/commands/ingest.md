---
description: Run the ENGRAM Phase H ingest lane for one source-class-qualified identifier.
---

Read `trinity/ENGRAM.md` and run the Phase H step 2d ingest lane for the source-class-qualified identifier the invocation names. Operate from the parent project root, resolve every bare path there, and follow the contract end to end; this door defers to it, adds nothing to it, and restates none of it.

Run the parent gate at both moments, before any phase work and again before the root report, from the parent project root, the directory whose direct child is the `trinity/` submodule:

    just --justfile trinity/tools/justfile parent-gate instrument=ENGRAM moment=preflight
    just --justfile trinity/tools/justfile parent-gate instrument=ENGRAM moment=report
