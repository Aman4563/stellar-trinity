"""Regenerate every case-study exhibit from the paper figures and the dated data artifact.

Exhibits 1 and 2 are byte copies of the regenerated paper figures, never redrawn.
Exhibit 3 is rendered from delivery_dispositions.json alone; the script prints the
summary counts the case and teaching note are allowed to cite and exits non-zero
when the stored assessment scope disagrees with the rows.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

EXHIBITS_DIR = Path(__file__).resolve().parent
PAPER_FIGURES = EXHIBITS_DIR.parent.parent / "paper" / "figures"
DISPOSITIONS = EXHIBITS_DIR / "delivery_dispositions.json"

REUSED_FIGURES = {
    "exhibit1_evidence_lifecycle": "evidence_lifecycle",
    "exhibit2_theme_distribution": "theme_distribution",
}


def copy_paper_figures() -> None:
    for exhibit, figure in REUSED_FIGURES.items():
        for suffix in ("pdf", "png"):
            source = PAPER_FIGURES / f"{figure}.{suffix}"
            shutil.copyfile(source, EXHIBITS_DIR / f"{exhibit}.{suffix}")


def render_exhibit3(artifact: dict[str, Any]) -> tuple[str, dict[str, int]]:
    parents = artifact["parents"]
    counts = Counter(row["disposition"] for row in parents)
    shipped = sum(row["shipped_tasks"] for row in parents)
    not_ship = sum(count for disposition, count in counts.items() if disposition != "SHIP")
    lines = [
        "| Parent | Disposition at last recorded run | Detail | Tasks shipped anyway |",
        "|---|---|---|---|",
    ]
    for row in parents:
        lines.append(
            f"| {row['parent']} | {row['disposition']} | {row['detail']} | {row['shipped_tasks']} |"
        )
    summary = {
        "parents": len(parents),
        "parents_not_ship": not_ship,
        "parents_ship": counts.get("SHIP", 0),
        "shipped_tasks": shipped,
    }
    return "\n".join(lines), summary


def main() -> int:
    artifact = json.loads(DISPOSITIONS.read_text(encoding="utf-8"))
    copy_paper_figures()
    table, summary = render_exhibit3(artifact)
    scope = artifact["assessment_scope"]
    failures = []
    if summary["parents"] != scope["repos"]:
        failures.append(f"parent rows {summary['parents']} != assessment repos {scope['repos']}")
    if summary["shipped_tasks"] < scope["tasks"]:
        failures.append(
            f"shipped tasks {summary['shipped_tasks']} < assessment tasks {scope['tasks']}"
        )
    header = (
        f"*Exhibit 3. {artifact['caption']}. Source: "
        f"{artifact['source']}. Evidence class: {artifact['evidence_class']}.*\n\n"
    )
    exhibit3 = EXHIBITS_DIR / "exhibit3_delivery_dispositions.md"
    exhibit3.write_text(header + table + "\n", encoding="utf-8")
    for key, value in summary.items():
        print(f"{key} = {value}")
    for key, value in scope.items():
        print(f"assessment_{key} = {value}")
    if failures:
        print("EXHIBIT CHECK FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("EXHIBITS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
