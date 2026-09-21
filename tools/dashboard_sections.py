"""Operational sections projected only from the typed dashboard snapshot."""

from __future__ import annotations

from tools import dashboard_charts as charts
from tools import reports
from tools.dashboard_charts import (
    INSTRUMENTS,
    age,
    bars,
    counted_bars,
    explain,
    fence,
    label,
    plain,
    table,
    worst,
)
from tools.tracker_snapshot import Snapshot

HEADLINE_INTRO = (
    "The whole project in six numbers. Every section after this one expands one of these rows."
)
LANES_INTRO = (
    "Who is accountable for what, and the last moment each group signed something off. Research "
    "owns the memory, Engineering owns the machinery that runs tasks, and Operations runs the "
    "author and the inspector."
)
BOARD_INTRO = (
    "How the runs of each instrument ended. The worst outcome is shown first because one refusal "
    "holds the work whatever the rest did."
)
DECISIONS_INTRO = (
    "Stops that are waiting for a person to sign, oldest first. Nothing behind a gate moves until "
    "someone signs it, and the chart below plots how many days each one has been waiting."
)
CHANGES_INTRO = (
    "What has happened since the last published boundary, so recent movement is visible without "
    "reading the whole history."
)
FLOW_INTRO = (
    "A task moves through five stages in order: staged, sealed, claimed, audited, placed. A count "
    "that drops sharply between two stages is where work is piling up."
)
AGING_INTRO = (
    "Runs that have not finished yet, longest waiting first. A run ages because it is blocked, "
    "not because it is busy."
)
BLOCKERS_INTRO = (
    "What is standing in the way: gaps are required work nothing covers yet, escalations are runs "
    "that raised a problem, and open gates are stops waiting for a signature."
)
SIGNOFF_INTRO = "Every sign-off recorded on disk, earliest first."


def headline(snapshot: Snapshot) -> list[str]:
    ages = [age(r.started_at, snapshot.as_of) for r in snapshot.runs if r.open_gates]
    known = [a for a in ages if a is not None]
    gates = sum(len(r.open_gates) for r in snapshot.runs)
    open_runs = sum(r.closure != "closed" for r in snapshot.runs)
    waiting = len(set(snapshot.sealed_uuids) - set(snapshot.audited_uuids))
    oldest = max(known) if known else 0
    counts = [
        ("open gates", gates),
        ("open runs", open_runs),
        ("samples resident", snapshot.samples_resident),
        ("sealed not audited", waiting),
        ("oldest gate days", oldest),
    ]
    return [
        HEADLINE_INTRO,
        "",
        *table(
            "metric | value | plain meaning",
            [
                (
                    "worst disposition",
                    explain(worst(snapshot.runs)),
                    "the worst outcome any run reached",
                ),
                (
                    "open gates",
                    gates if snapshot.runs else "no run",
                    "stops waiting for a human signature",
                ),
                (
                    "open runs",
                    open_runs if snapshot.runs else "no run",
                    "sittings that have not finished",
                ),
                (
                    "samples occupancy",
                    reports._ratio(snapshot.samples_resident, reports.SAMPLE_CEILING),
                    "how full the public shelf of thirty is",
                ),
                (
                    "sealed not audited",
                    waiting if snapshot.runs else "no run",
                    "finished tasks still waiting to be inspected",
                ),
                (
                    "oldest open gate age (days)",
                    max(known) if known else "no run",
                    "how long the longest signature has been waited on",
                ),
            ],
        ),
        *counted_bars(counts if snapshot.runs else []),
    ]


def lanes(snapshot: Snapshot) -> list[str]:
    research = [r for r in snapshot.runs if r.instrument == "ENGRAM"]
    forge = [r for r in snapshot.runs if r.instrument == "FORGE"]
    crucible = [r for r in snapshot.runs if r.instrument == "CRUCIBLE"]
    engineering = [r for r in forge if "harness" in r.phase.lower()]
    epoch = next((e for e in snapshot.epochs if e.epoch == snapshot.current_epoch), None)
    research_standing = (
        f"epoch {snapshot.current_epoch}" if snapshot.current_epoch else "no epoch published"
    )
    research_standing += f"; ENGRAM {worst(research)}"
    if epoch is not None:
        research_standing += f"; published by {epoch.published_by}"
    revision = (
        f"harness gitlink {snapshot.harness_revision[:12]}"
        if snapshot.harness_revision
        else "harness revision unknown"
    )
    concurrent = any(
        f.started_at <= (c.closed_at or snapshot.as_of or "")
        and c.started_at <= (f.closed_at or snapshot.as_of or "")
        for f in forge
        for c in crucible
    )
    operations = "no run"
    if forge or crucible:
        operations = (
            f"FORGE {len(forge)} runs; CRUCIBLE {len(crucible)} runs; "
            f"{len(snapshot.claimed_uuids)} claims; {len(snapshot.audited_uuids)} verdicts; "
            + ("concurrent" if concurrent else "sequential")
        )
    rows = table(
        "lane | standing | last sign-off instant | artifact",
        [
            (
                "Research",
                research_standing,
                epoch.published_at if epoch else "unknown",
                f".memory/epochs/{snapshot.current_epoch}/manifest.json"
                if epoch
                else "no epoch published",
            ),
            (
                "Engineering",
                f"{revision}; {len(engineering)} harness runs",
                max((r.closed_at for r in engineering if r.closed_at), default="unknown"),
                "harness/",
            ),
            (
                "Operations",
                operations,
                max((r.closed_at for r in [*forge, *crucible] if r.closed_at), default="unknown"),
                "EDICT.md, VERDICT.md",
            ),
        ],
    )
    return [
        LANES_INTRO,
        "",
        *rows,
        "",
        *fence(
            [
                "flowchart LR",
                '    subgraph Research["Research"]',
                f"        RES0[{label(research_standing)}]",
                "    end",
                '    subgraph Engineering["Engineering"]',
                f"        ENG0[{label(revision)}]",
                "    end",
                '    subgraph Operations["Operations"]',
                f"        OPS0[{label(f'FORGE {len(forge)} runs')}]",
                f"        OPS1[{label(f'CRUCIBLE {len(crucible)} runs')}]",
                "    end",
                "    RES0 --> ENG0",
                "    ENG0 --> OPS0",
                "    ENG0 --> OPS1",
            ]
        ),
    ]


def dispositions(snapshot: Snapshot) -> list[str]:
    tokens = ("BLOCK", "HOLD", "SHIP_ELIGIBLE")
    rows: list[tuple[str | int, ...]] = []
    totals = [0, 0, 0]
    for instrument in INSTRUMENTS:
        items = [r for r in snapshot.runs if r.instrument == instrument]
        counts = [sum(r.disposition.split(":")[0] == token for r in items) for token in tokens]
        totals = [a + b for a, b in zip(totals, counts, strict=True)]
        values: tuple[str | int, ...] = (*counts, len(items)) if items else ("no run",) * 4
        rows.append((instrument, explain(worst(items)), *values))
    result = [
        BOARD_INTRO,
        "",
        *table("instrument | worst disposition | BLOCK | HOLD | SHIP_ELIGIBLE | runs", rows),
    ]
    if snapshot.runs:
        result += [
            "",
            *fence(
                [
                    "pie showData",
                    "    title Dispositions",
                    *(
                        f"    {label(token)} : {count}"
                        for token, count in zip(tokens, totals, strict=True)
                        if count
                    ),
                ]
            ),
        ]
    return result


def decisions(snapshot: Snapshot) -> list[str]:
    pending = [
        (age(r.started_at, snapshot.as_of), r.instrument, gate, r.run_id)
        for r in snapshot.runs
        for gate in r.open_gates
    ]
    pending.sort(key=lambda v: (-(v[0] if v[0] is not None else -1), v[1], v[2], v[3]))
    if not pending:
        return [DECISIONS_INTRO, "", "no open gate is recorded"]
    result = [
        DECISIONS_INTRO,
        "",
        *table(
            "gate | instrument | run | age (days)",
            [
                (gate, instrument, run, days if days is not None else "unknown")
                for days, instrument, gate, run in pending
            ],
        ),
    ]
    known = [(f"{g} {i}", days) for days, i, g, _ in pending if days is not None]
    return result + (["", *charts.decision_bars(known)] if known else [])


def changes(snapshot: Snapshot) -> list[str]:
    if snapshot.boundary is None:
        return [CHANGES_INTRO, "", "unavailable: no earlier boundary is recorded on disk"]
    instants = [e.published_at for e in snapshot.epochs if f"epoch-{e.epoch}" == snapshot.boundary]
    instants += [c.at for c in snapshot.cycles if f"cycle-{c.cycle}" == snapshot.boundary]
    result = [CHANGES_INTRO, "", f"Boundary: {plain(snapshot.boundary)}", ""]
    if not instants:
        return [*result, "unavailable: boundary instant is unknown"]
    at = max(instants)
    counts = [
        ("runs started", sum(r.started_at > at for r in snapshot.runs)),
        ("cycles completed", sum(c.at > at for c in snapshot.cycles)),
        ("epochs published", sum(e.published_at > at for e in snapshot.epochs)),
    ]
    return (
        result
        + table("activity | count", [(f"{name} after", count) for name, count in counts])
        + counted_bars(counts)
    )


def flow(snapshot: Snapshot) -> list[str]:
    counts = [
        ("staged", len(snapshot.staged)),
        ("sealed", len(snapshot.sealed_uuids)),
        ("claimed", len(snapshot.claimed_uuids)),
        ("audited", len(snapshot.audited_uuids)),
        ("placed", snapshot.samples_resident + snapshot.delivery_resident),
    ]
    sources = ("staging/ dirs", "queue", "claims", "verdicts", "samples + delivery residency")
    return [
        FLOW_INTRO,
        "",
        *table(
            "stage | count | counted from",
            [(name, count, source) for (name, count), source in zip(counts, sources, strict=True)],
        ),
        "",
        *bars(counts),
    ]


def aging(snapshot: Snapshot) -> list[str]:
    limit = 12
    pending = [
        (age(r.started_at, snapshot.as_of), r) for r in snapshot.runs if r.closure != "closed"
    ]
    pending.sort(key=lambda v: (-(v[0] if v[0] is not None else -1), v[1].instrument, v[1].run_id))
    if not pending:
        return [AGING_INTRO, "", "no open run is recorded"]
    result = [
        AGING_INTRO,
        "",
        *table(
            "run | instrument | principal | started | age (days)",
            [
                (
                    r.run_id,
                    r.instrument,
                    r.principal,
                    r.started_at,
                    days if days is not None else "unknown",
                )
                for days, r in pending[:limit]
            ],
        ),
    ]
    if len(pending) > limit:
        result += ["", f"and {len(pending) - limit} more open runs"]
    return result + counted_bars(
        charts.decision_labels([(r.run_id, d) for d, r in pending[:limit] if d is not None])
    )


def blockers(snapshot: Snapshot) -> list[str]:
    rows: list[tuple[str | int, ...]] = []
    counts: list[tuple[str, int]] = []
    for instrument in INSTRUMENTS:
        items = [r for r in snapshot.runs if r.instrument == instrument]
        gaps, escalations = sum(r.gaps for r in items), sum(r.has_escalations for r in items)
        gates = sorted({g for r in items for g in r.open_gates})
        if gaps or escalations or gates:
            rows.append((instrument, gaps, escalations, ", ".join(gates) or "none"))
            counts += [(f"{instrument} gaps", gaps), (f"{instrument} gates", len(gates))]
    if not rows:
        return [BLOCKERS_INTRO, "", "no blocker is recorded"]
    return [
        BLOCKERS_INTRO,
        "",
        *table("instrument | gaps | runs with escalations | open gate names", rows),
        *counted_bars(counts),
    ]


def signoffs(snapshot: Snapshot) -> list[str]:
    rows = [
        (e.published_at, f"epoch-{e.epoch}", "published", e.published_by) for e in snapshot.epochs
    ]
    rows += [
        (c.at, f"cycle-{c.cycle} {c.instrument}", c.disposition, c.stop_reason)
        for c in snapshot.cycles
    ]
    rows += [
        (
            "unknown",
            f"gate {g.gate}",
            "approved" if g.approved else "declared, not approved",
            g.tier,
        )
        for g in snapshot.gates
    ]
    return [SIGNOFF_INTRO, ""] + (
        table("instant | sign-off | status | by / tier / stop reason", sorted(rows))
        if rows
        else ["no sign-off is recorded"]
    )
