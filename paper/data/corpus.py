"""Self-checking loader for the anchor-corpus data artifact.

This module is the single estimator for every aggregate reported in the
position paper. Running it as a script recomputes each headline number from
the raw anchors array in corpus.json, asserts equality with the stored
aggregates block, prints every headline aggregate, and exits non-zero on any
disagreement. The paper may only cite numbers that this self-check prints.

The check validates arithmetic consistency only. It cannot validate the
selection of anchors or their theme labels, which are editorial inputs
recorded in the artifact's selection_note. Aggregates over this curated list
are reported as plain counts; the corpus is a selection, not a sample.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent / "corpus.json"


def load() -> dict[str, Any]:
    with DATA_PATH.open(encoding="utf-8") as handle:
        artifact: dict[str, Any] = json.load(handle)
    return artifact


def compute_aggregates(anchors: list[dict[str, Any]]) -> dict[str, Any]:
    theme_counts = Counter(anchor["theme"] for anchor in anchors)
    year_counts = Counter(str(anchor["year"]) for anchor in anchors)
    ranked = theme_counts.most_common()
    largest_theme, largest_theme_count = ranked[0]
    second_largest_theme_count = ranked[1][1] if len(ranked) > 1 else 0
    total = len(anchors)
    return {
        "total_anchors": total,
        "theme_count": len(theme_counts),
        "theme_counts": dict(theme_counts),
        "largest_theme": largest_theme,
        "largest_theme_count": largest_theme_count,
        "second_largest_theme_count": second_largest_theme_count,
        "largest_theme_margin": largest_theme_count - second_largest_theme_count,
        "year_counts": dict(year_counts),
    }


THEME_TITLES = {
    "benchmark_construction_and_hardening": "Benchmark construction and hardening",
    "temporal_memory_and_forgetting": "Temporal memory and forgetting",
    "judge_reliability": "Judge reliability",
    "shortcut_learning": "Shortcut learning",
    "reward_integrity": "Reward integrity",
    "measurement_theory": "Measurement theory",
    "agentic_case_studies": "Agentic case studies",
}

MD_BEGIN = "<!-- anchors-table:begin -->"
MD_END = "<!-- anchors-table:end -->"


def _tex_escape(text: str) -> str:
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("#", "\\#")
        .replace("_", "\\_")
    )


def render_anchor_table_markdown(anchors: list[dict[str, Any]]) -> str:
    rows = ["| arXiv | Class | First author | Year | Theme |", "|---|---|---|---|---|"]
    for anchor in sorted(anchors, key=lambda item: item["arxiv_id"]):
        rows.append(
            f"| {anchor['arxiv_id']} | {anchor['source_class']} | {anchor['first_author']} | "
            f"{anchor['year']} | {THEME_TITLES[anchor['theme']]} |"
        )
    return "\n".join(rows)


def render_anchor_table_latex(anchors: list[dict[str, Any]]) -> str:
    lines = [
        "\\begin{tabular}{@{}lllrl@{}}",
        "\\toprule",
        "arXiv & Class & First author & Year & Theme \\\\",
        "\\midrule",
    ]
    for anchor in sorted(anchors, key=lambda item: item["arxiv_id"]):
        lines.append(
            f"{anchor['arxiv_id']} & {_tex_escape(anchor['source_class'])} & "
            f"{_tex_escape(anchor['first_author'])} & {anchor['year']} & "
            f"{_tex_escape(THEME_TITLES[anchor['theme']])} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines)


def render_tables() -> int:
    """Write the per-instance anchor table into both manuscript mirrors.

    The Markdown mirror carries the table between the two marker comments in
    paper/main.md; the LaTeX mirror reads paper/data/anchors_table.tex through
    an \\input. Both are regenerated from corpus.json alone, never hand-edited.
    """
    anchors = load()["anchors"]
    paper_dir = DATA_PATH.parent.parent
    (DATA_PATH.parent / "anchors_table.tex").write_text(
        render_anchor_table_latex(anchors) + "\n", encoding="utf-8"
    )
    main_md = paper_dir / "main.md"
    text = main_md.read_text(encoding="utf-8")
    begin = text.index(MD_BEGIN) + len(MD_BEGIN)
    end = text.index(MD_END)
    text = text[:begin] + "\n" + render_anchor_table_markdown(anchors) + "\n" + text[end:]
    main_md.write_text(text, encoding="utf-8")
    print(f"anchor tables rendered for {len(anchors)} anchors (main.md, anchors_table.tex)")
    return 0


def self_check() -> int:
    artifact = load()
    anchors = artifact["anchors"]
    stored = artifact["aggregates"]
    computed = compute_aggregates(anchors)

    failures = []
    for key, value in computed.items():
        if stored.get(key) != value:
            failures.append(f"{key}: stored={stored.get(key)!r} computed={value!r}")

    theme_sum = sum(computed["theme_counts"].values())
    year_sum = sum(computed["year_counts"].values())
    if theme_sum != computed["total_anchors"]:
        failures.append(f"theme partition sum {theme_sum} != total {computed['total_anchors']}")
    if year_sum != computed["total_anchors"]:
        failures.append(f"year partition sum {year_sum} != total {computed['total_anchors']}")

    unique_ids = {anchor["arxiv_id"] for anchor in anchors}
    if len(unique_ids) != len(anchors):
        failures.append("duplicate arXiv identifiers in anchors array")

    for anchor in anchors:
        found = sorted(
            (DATA_PATH.parent.parent.parent / "research" / anchor["source_class"]).glob(
                f"{anchor['arxiv_id']}-*.identity.json"
            )
        )
        if len(found) != 1:
            failures.append(f"{anchor['arxiv_id']}: {len(found)} research manifests resolve")
            continue
        recorded = json.loads(found[0].read_text(encoding="utf-8"))["content_digest"]
        if recorded != anchor["content_digest"]:
            failures.append(
                f"{anchor['arxiv_id']}: digest {anchor['content_digest']} != manifest {recorded}"
            )

    print(f"total_anchors = {computed['total_anchors']}")
    print(f"theme_count = {computed['theme_count']}")
    theme_counts = sorted(
        computed["theme_counts"].items(),
        key=lambda item: (-item[1], item[0]),
    )
    for theme, count in theme_counts:
        print(f"theme {theme} = {count}/{computed['total_anchors']}")
    print(
        "largest_theme = "
        f"{computed['largest_theme']} "
        f"({computed['largest_theme_count']}/{computed['total_anchors']})"
    )
    for year, count in sorted(computed["year_counts"].items()):
        print(f"year {year} = {count}/{computed['total_anchors']}")
    print(
        "largest_theme_margin = "
        f"{computed['largest_theme_margin']} "
        f"({computed['largest_theme_count']} - {computed['second_largest_theme_count']})"
    )

    if failures:
        print("SELF-CHECK FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print("SELF-CHECK OK")
    return 0


def check_manuscript() -> int:
    """Fail when either manuscript mirror drifts from the data artifact's headlines.

    Every headline string the paper is allowed to carry is built here from the
    recomputed aggregates and must appear in both mirrors; any other
    "k of N" count whose N differs from the total may appear only inside an
    Erratum paragraph, where superseded numbers are permitted.
    """
    artifact = load()
    aggregates = compute_aggregates(artifact["anchors"])
    total = aggregates["total_anchors"]
    years = aggregates["year_counts"]
    expected = [
        f"reading list of {total} recent papers",
        f"(n = {total})",
        f"The list of {total} papers",
        f"1 of the {total} entries appeared in 2024, {years['2025']} of {total} in 2025, "
        f"and {years['2026']} of {total} in 2026",
    ]
    expected += [
        f"{THEME_TITLES[theme]} ({count} of {total})"
        for theme, count in aggregates["theme_counts"].items()
    ]
    paper_dir = DATA_PATH.parent.parent
    mirrors = {
        "main.md": paper_dir / "main.md",
        "latex/main.tex": paper_dir / "latex" / "main.tex",
    }
    count_pattern = re.compile(r"\b(\d+) of (\d+)\b(?: in (20\d\d))?")
    failures = []
    for name, path in mirrors.items():
        text = path.read_text(encoding="utf-8")
        for needle in expected:
            if needle not in text:
                failures.append(f"{name}: missing headline {needle!r}")
        for paragraph in text.split("\n"):
            if "Erratum" in paragraph:
                continue
            for match in count_pattern.finditer(paragraph):
                denominator = int(match.group(2))
                if denominator != total:
                    failures.append(f"{name}: stale count {match.group(0)!r}")
    if failures:
        print("MANUSCRIPT CHECK FAILED", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(f"MANUSCRIPT CHECK OK ({len(expected)} headlines present in both mirrors)")
    return 0


def main(argv: list[str]) -> int:
    if argv[1:] == ["--render-tables"]:
        return render_tables()
    if argv[1:] == ["--check-manuscript"]:
        return check_manuscript()
    if argv[1:]:
        print("usage: corpus.py [--render-tables | --check-manuscript]", file=sys.stderr)
        return 2
    return self_check()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
