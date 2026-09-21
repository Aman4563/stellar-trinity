# Trinity independent execution authority

## Purpose and scope

This document specifies the independent execution authority that `FORGE.md` already requires at Phase 4 item 2a and that has never existed. It fixes four duties, admission, execution, observation, and custody, each with explicit acceptance criteria and each stated as what it refuses. A duty is met only when every one of its criteria holds, because an authority that holds three duties out of four leaves the fourth with the party it was brought in to check.

The document is normative for duty shape and silent on who holds them. Nothing here asserts that such an authority, an immutable runner, or a provider attestation exists, and nothing here grants authority to any actor. Read it beside `docs/measurement-fidelity.md`, which fixes the vocabulary used below, and beside `DEFERRED.md`, which stays the register of what is stated and unenforced.

## What the authority is

The authority is a party controlled by neither the author nor the auditor, authorized for the `execution_operator` role by the external trust policy named in `.seed/pilot.yaml`, and holding the four duties in effective control rather than in prose. A self-asserted role is not authorization. The signature backend verifies a signature and returns a principal, and the trust root then decides whether that principal is bound to the role at the caller-supplied evaluation instant, so an envelope calling its own producer an `execution_operator` grants nothing.

Effective control is the whole claim. An operator who declares the population, runs the image, records the log, and stores the bytes is one party wearing four hats, and a measurement checked by its own producer is a self-report with extra steps.

## The four duties at a glance

| Duty | What it binds | What it refuses |
| --- | --- | --- |
| Admission | a precommitted roster of task, solver, group, rollout, effective configuration digest, and seed, committed and timestamped before execution begins | an unrostered rollout, and a roster amendment after the first rollout of its window |
| Execution | an immutable approved runner at a pinned image digest, the approved configuration, fresh per-rollout state, and mediated provider credentials | a divergent runner digest, a configuration digest that is not the admitted one, and reused state |
| Observation | the capture of effective requests and responses, tool and environment input and output, final-submission identity, and termination events, taken at the boundary before operator-side editing and bound by digest | a fidelity claim resting only on the agent's self-report |
| Custody | independent retention bound to the roster for a declared window | a retrieval that cannot be tied to a roster row, and a deletion inside the window |

## Admission

The authority holds a precommitted roster binding, for every rollout the pilot will count, the frozen task identity, the solver identity, the group identity, the rollout identity, the effective configuration digest, and the seed.

The duty is met when all of the following hold.

- The roster is committed and timestamped before the first rollout of the window it covers, and the timestamp is proven by the authority's own signature against an external time source, never by a field the operator writes about itself.
- The roster enumerates every rollout identity the pilot will count, each bound to exactly one task, one solver, one group, one effective configuration digest, and one seed.
- Group membership is disjoint, and the group count N is fixed at commitment at or above the computed floor `minimum_groups` derives from the ceiling, the familywise confidence, and the comparison family, and never fewer than eight.
- The permitted looks and the comparison family M are fixed in the same commitment, which sits alongside the decoy-seed commitment and the attempt budget, stopping rule, and freeze window Phase 4 items 2a and 4a already require, and replaces none of them.
- An amendment opens a new window with its own commitment; it never edits a window whose first rollout has begun.

Refusal: the authority refuses a rollout whose identity is absent from the roster, and refuses a roster amendment after the first rollout of that window has begun. The commitment must predate the execution interval it covers, exactly as Phase 4 item 2a already requires of the decoy-seed commitment, and for the same reason. A commitment made once outcomes are visible constrains nothing, because a party free to choose what to commit after results are known can still commit to a flattering subset. A population that cannot be proven against its roster is `BLOCK:INVALID_PILOT`, because an unprovable population is no measurement rather than a weak one.

## Execution

The authority runs an immutable approved runner at a pinned image digest under the approved configuration, with fresh per-rollout state and provider credentials it mediates rather than hands over.

The duty is met when all of the following hold.

- The runner is an immutable image pinned by digest, and that digest equals the one the `harness/` extension binds and the one the release record carries.
- The effective configuration is the admitted one, and its lowercase hex SHA-256 equals the `harness_config_digest` the pilot block carries over the mirrored bytes at `.seed/harness-config.json`, bound as closed `trinity.harness-config/v1`.
- Every rollout starts from fresh state: a new container, a new working tree, no inherited cache, no inherited session, and no conversation carried from an earlier rollout.
- The authority holds the provider credential and mediates every provider call, so neither the operator, the runner image, nor the agent under test ever holds that credential.
- The runner drives the same inference and evaluation entry points the bundle was authored against, through the pinned image the release record binds.

Refusal: the authority refuses a runner whose image digest differs from the approved one, refuses a rollout that inherits state from an earlier rollout, and refuses execution under a configuration whose digest is not the admitted one. Drift between the pinned and the attested configuration caps at `HOLD:SUPPRESSED_MEASUREMENT`, which the audit side privately classifies as `config-drift`, and an absent or unbound configuration caps there under `config-unpinned`. Approval is never adequacy: a configuration that is signed, pinned, and reproducible while still leaving the solver short of the horizon the task needs is approved-but-inadequate and caps identically under `config-inadequate`.

## Observation

The authority captures the effective requests and responses, the tool and environment input and output, the identity of the final submission, and every termination event at the boundary, before any operator-side editing, and binds that capture by digest.

The duty is met when all of the following hold.

- The capture is taken by the authority's own process at the boundary between the runner and the provider, and at the boundary between the runner and its environment.
- It records, for every provider call, the effective request as sent and the effective response as received, including the served model identity the provider reports.
- It records every tool and environment interaction as input and output bytes, the identity of the final submission that reaches the scorer, and every termination event with its declared cause.
- The capture is bound by digest at the instant it is taken, and that digest is signed by the authority before any operator-side process can read or rewrite the bytes.
- The capture is native and never a conversion product, and never the agent's own account of itself.

Refusal: the authority refuses a fidelity claim resting only on the agent's self-report, and refuses to certify a capture taken where an operator-side process could have edited it first. A capture the operator could have edited before it was recorded proves custody of whatever survived and never faithful execution. A self-reported zero is not evidence of absence, so a clean reading supported only by the harness reporting on itself resolves as INSUFFICIENT_EVIDENCE under the refusal FIDELITY_SELF_REPORTED_ONLY and never as COVERED_CLEAN.

## Custody

The authority retains the capture independently, bound to the roster, for a retention window declared before execution begins.

The duty is met when all of the following hold.

- Retention is on storage the authority controls, which neither the author nor the auditor can write.
- Every retained object binds to exactly one roster row, by rollout identity and capture digest.
- The retention window is declared before execution begins and is carried in the same commitment as the roster.
- A retrieval names the roster row it answers, and the authority records which principal retrieved which object at which instant.
- Deletion inside the declared window is refused, and expiry at the end of the window is recorded as its own event instead of as silence.

Refusal: the authority refuses a retrieval that cannot be tied to a roster row, and refuses a deletion inside the declared window. Retention the operator can write is not custody, and a capture that cannot be tied back to the roster row it belongs to cannot establish which population it evidences.

## Declared trust assumptions

Four assumptions survive a perfect authority. Each is declared here so no reader mistakes this specification for a closed threat model.

- Provider-internal routing. The authority observes the request it sent and the response it received, never the machine, region, replica, or cache path that served them. Everything inside the provider boundary is trusted and never verified.
- In-provider model substitution and fallback. A provider that serves a smaller model, a lower reasoning effort, or a fallback route returns bytes the authority records faithfully, and the authority cannot prove what produced them. The served model identity is a provider assertion, and closing it needs a provider attestation that does not exist.
- An organization administrator with write access to both the authority and this repository. That actor changes governance, pins, rosters, and retention at once, and stays outside this repository's threat boundary. A client requiring defense against it needs independently witnessed transparency records and client-side re-execution.
- Hardware-level compromise. Compromised firmware, a compromised hypervisor, or a compromised host anywhere in the execution path defeats every duty above while leaving the capture those duties bind internally consistent.

## The independent re-execution fallback

Where no authority holds all four duties, the minimum replacement measurement is a fresh independent re-execution under a pinned configuration by a party controlled by neither the author nor the auditor.

The fallback replaces a measurement and never erases one.

```text
N is the group count fixed at admission, and it is never lowered afterward.

X* counts the groups whose worst-case indicator is one, over that same fixed N.

A replacement group enters as its own row, and the group it replaces stays in N.
```

- The original groups stay in the fixed N. A replacement never retires a group, never lowers N, and never turns a group carrying a member that is not `conforming` into a clean one.
- Both the original and the replacement are reported. A reader shown only the replacement cannot tell a repaired run from a discarded one.
- Exclude-then-impute is refused. A descriptive valid-only rate over the conforming groups alone may be reported beside the corrected bound and never authorizes release.
- A re-execution that cannot pin its own configuration, or that the author or the auditor controls, is not a replacement measurement and settles nothing.
- The fallback is a floor and never an upgrade. A replacement measurement carries the standing of the measurement it replaces and never more, and no re-execution converts an unprovable population into a proven one.

## Least-privilege routing

Routing is least-privilege by principal and surface, because a detector's reason vocabulary is an adaptation channel.

| Principal | Receives | Never receives |
| --- | --- | --- |
| Independent execution authority | the effective configuration, the raw capture, and the population records | nothing withheld, since this principal is the origin of all three |
| CRUCIBLE | the full evidence and its own derived findings, retained under `.audit/attestations/execution/` and reduced into `.audit/fidelity.yaml` | the hardness contract, which its projection withholds entirely |
| Trusted pilot and release verifier | authenticated group eligibility and outcomes, enough to recompute the corrected bound privately | the raw capture bytes, and the detector reasoning behind a finding |
| ENGRAM | existing projections, receipt references, and an explicitly authorized coarse disposition | reason-specific trial-status counts |
| FORGE | the same coarse disposition, plus the three conformance tokens on its own rollouts | any selected reason code, any detector outcome, and any reason-specific trial-status count |

FORGE never receives a selected reason code. An author who learns why a pilot was refused writes the next task toward the instrument that refused it, which is reward hacking by construction, so the six private classifications stay on the audit side and only the capped disposition and the three conformance tokens cross into the authoring lane.

The execution receipt binds the observed artifacts and the effective configuration, while audit conclusions stay on a separate surface. The clause keeping this repository away from duration records, decoy values, access telemetry, blinding results, and detector outcomes names a principal and a surface: it binds the FORGE lane and the `.seed/` surface, and it never reaches the auditor's retention under `.audit/attestations/execution/` or the evidence ledger the auditor emits.

## Standing in this repository

Nothing in this repository satisfies any of the four duties, and nothing in this repository can.

- No admission roster has ever been committed, so no population is bound to a precommitment.
- No runner is pinned and operated by a party outside this repository, so every execution claim is an operator assertion.
- No capture is taken ahead of operator-side editing, so no observation is bound at the boundary.
- No independent custody store exists, so no retained object is bound to a roster row.

Each of the four duties is registered in `DEFERRED.md` as a stated obligation nothing enforces, beside the rows for the execution attestation nobody has produced and for the external operator and runner that do not exist. This specification exists so the gap is legible and never to imply coverage: naming what an authority would have to do is not the same as having one, and a reader who finishes this document should open that register next.

The operational consequence is unchanged. `FORGE.md` stays capped at `HOLD:PILOT_REQUIRED` while no authorized operator produces a signed execution attestation, and the mandatory `execution_fidelity` control reconciles against evidence the auditor emits and is never marked satisfied by the contract that emits it. No sentence here upgrades an unmeasured claim, and no sentence here is evidence that an authority, an immutable runner, or a provider attestation was ever deployed.
