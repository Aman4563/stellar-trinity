"""Mechanical output contract for TRACKING.md: plain Markdown plus GitHub Mermaid.

Nothing here pins the human wording of a section, and the section order itself is
proved once in ``tests/test_dashboard.py``. Every rule below is a property of the
rendered bytes alone, held against a fixture matrix rather than one happy path, so
a renderer change that breaks plain-text output fails on the offending line.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Final

import pytest
from tools import dashboard

from tests.tracker_fixtures import ParentFixture, parent_fixture

SCENARIOS: Final[Mapping[str, Callable[[Path], ParentFixture]]] = {
    "zero-runs": partial(parent_fixture, zero_runs=True),
    "single-instrument": partial(parent_fixture, runs=("FORGE",)),
    "late-run-and-graduated-anchor": partial(parent_fixture, late_run=True, graduated_anchor=True),
    "malformed-card": partial(parent_fixture, malformed_card=True),
}
FENCE: Final = "```"
DIAGRAMS: Final = frozenset(
    {"flowchart", "pie", "gantt", "xychart-beta", "timeline", "quadrantChart", "kanban"}
)
AXIS_LIMIT: Final = 10
MMDC: Final = ("npx", "-y", "@mermaid-js/mermaid-cli", "-i", "TRACKING.md", "-o", "out.md")
MMDC_TIMEOUT: Final = 180
PARSE_MARKERS: Final = ("Parse error", "Syntax error", "UnknownDiagramError")

_HTML: Final = re.compile(r"<[A-Za-z/]")
_IMAGE: Final = re.compile(r"!\[")
_URL: Final = re.compile(r"https?://")
_ENTITY: Final = re.compile(r"&#")
_TAB: Final = re.compile(r"\t")
_SHORTCODE: Final = re.compile(r"(?<![\w:]):[a-z][a-z0-9_+-]*:(?![\w:])")
_BLOCK: Final = re.compile(r"[\u2580-\u259f]")
_CODE_SPAN: Final = re.compile(r"`[^`]*`")
_RATIO: Final = re.compile(r"(\d+) of (\d+) \((\d+)%\)")
_PERCENT: Final = re.compile(r"\d+%")
_AXIS: Final = re.compile(r"^x-axis\s*\[(.*)\]$")
_QUOTED: Final = re.compile(r'"[^"]*"')


@dataclass(frozen=True, slots=True)
class Fence:
    """One fenced block: where it opened, its info string, and whether it closed."""

    line: int
    info: str
    closed: bool
    body: tuple[str, ...]


def _fences(lines: Sequence[str]) -> list[Fence]:
    found: list[Fence] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith(FENCE):
            index += 1
            continue
        close = next((j for j in range(index + 1, len(lines)) if lines[j] == FENCE), None)
        stop = len(lines) if close is None else close
        info = lines[index][len(FENCE) :].strip()
        found.append(Fence(index + 1, info, close is not None, tuple(lines[index + 1 : stop])))
        index = stop + 1
    return found


def _fenced_indices(lines: Sequence[str]) -> set[int]:
    """Zero-based indices of every fence marker line and every line between them."""
    return {n for f in _fences(lines) for n in range(f.line - 1, f.line + len(f.body) + 1)}


def _paragraphs(lines: Sequence[str]) -> set[int]:
    """Zero-based indices of paragraph lines: not blank, structural, or fenced.

    Structural mirrors ``tools.prose.is_structural``: headings, table rows, list items,
    blockquotes, and backtick lines are never prose.
    """
    fenced = _fenced_indices(lines)
    return {
        i
        for i, line in enumerate(lines)
        if i not in fenced
        and line.strip()
        and not line.startswith(("#", "|", "- ", "* ", ">", "`"))
    }


def _mermaid(rendered: str, keyword: str | None = None) -> list[Fence]:
    blocks = [f for f in _fences(rendered.split("\n")) if f.info == "mermaid"]
    if keyword is None:
        return blocks
    return [f for f in blocks if f.body and f.body[0].split()[0].startswith(keyword)]


def _offenders(lines: Sequence[str], pattern: re.Pattern[str]) -> list[str]:
    return [f"L{i + 1}: {line!r}" for i, line in enumerate(lines) if pattern.search(line)]


@pytest.fixture(scope="module", params=sorted(SCENARIOS))
def rendered(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> str:
    """Rendered TRACKING.md bytes for one scenario, built once per module."""
    name = str(request.param)
    root = tmp_path_factory.mktemp(name.replace("-", "_"))
    SCENARIOS[name](root)
    return dashboard.render_tracker(root)


def test_carries_no_markup_beyond_plain_markdown(rendered: str) -> None:
    # Given a rendered dashboard.
    lines = rendered.split("\n")
    # When every banned markup form is searched for.
    found = {
        "raw HTML": _offenders(lines, _HTML),
        "image": _offenders(lines, _IMAGE),
        "network link": _offenders(lines, _URL),
        "HTML entity": _offenders(lines, _ENTITY),
    }
    # Then no line carries one.
    assert not any(found.values()), found


def test_whitespace_is_hygienic(rendered: str) -> None:
    # Given a rendered dashboard.
    lines = rendered.split("\n")
    # When tabs, padded line ends, and the file ending are inspected.
    padded = [f"L{i + 1}: {line!r}" for i, line in enumerate(lines) if line != line.rstrip()]
    tabs = _offenders(lines, _TAB)
    # Then nothing is padded and the file closes on exactly one newline.
    assert not tabs and not padded, (tabs, padded)
    assert rendered.endswith("\n") and not rendered.endswith("\n\n"), repr(rendered[-4:])


def test_no_emoji_shortcode_outside_a_mermaid_fence(rendered: str) -> None:
    # Given every line that is not inside a fence.
    lines = rendered.split("\n")
    fenced = _fenced_indices(lines)
    # When the shortcode form is searched for, tolerating stamps and colon-joined tokens.
    hits = [
        f"L{i + 1}: {match.group(0)!r} in {line!r}"
        for i, line in enumerate(lines)
        if i not in fenced
        for match in _SHORTCODE.finditer(line)
    ]
    # Then no token reads as an emoji shortcode.
    assert not hits, hits


def test_every_paragraph_is_one_line(rendered: str) -> None:
    # Given the paragraph lines of a rendered dashboard.
    lines = rendered.split("\n")
    paragraphs = _paragraphs(lines)
    # When each paragraph line is checked against the line that follows it.
    wrapped = [
        f"L{i + 1}: {lines[i]!r} is followed by L{i + 2}: {lines[i + 1]!r}"
        for i in sorted(paragraphs)
        if i + 1 in paragraphs
    ]
    # Then no paragraph is hard wrapped across two lines.
    assert not wrapped, wrapped


def test_unicode_bars_stay_inside_backticks(rendered: str) -> None:
    # Given a rendered dashboard with its code spans removed.
    lines = rendered.split("\n")
    # When block drawing characters are searched for in what remains.
    escaped = [
        f"L{i + 1}: {line!r}"
        for i, line in enumerate(lines)
        if _BLOCK.search(_CODE_SPAN.sub("", line))
    ]
    # Then every bar character sits inside backticks on its own line.
    assert not escaped, escaped


def test_every_mermaid_fence_closes_on_a_supported_diagram(rendered: str) -> None:
    # Given every mermaid fence the dashboard opened.
    blocks = _mermaid(rendered)
    # When each fence's closing marker and opening keyword are read.
    unclosed = [f"L{f.line}" for f in blocks if not f.closed]
    unsupported = [
        f"L{f.line}: {f.body[0]!r}" if f.body else f"L{f.line}: empty fence"
        for f in blocks
        if not f.body or f.body[0].split()[0] not in DIAGRAMS
    ]
    # Then every fence closes and declares a diagram GitHub renders.
    assert not unclosed and not unsupported, (unclosed, unsupported)


def test_xychart_axes_are_quoted_and_bounded(rendered: str) -> None:
    # Given every xychart fence.
    charts = _mermaid(rendered, "xychart")
    # When each declaration and x-axis category list is read.
    suffix = [f"L{f.line}: {f.body[0]!r}" for f in charts if f.body[0].strip() != "xychart-beta"]
    axes = [
        (f.line, match.group(1).strip())
        for f in charts
        for line in f.body
        if (match := _AXIS.match(line.strip()))
    ]
    malformed = [
        (line, inner)
        for line, inner in axes
        if ", ".join(_QUOTED.findall(inner)) != inner or len(_QUOTED.findall(inner)) > AXIS_LIMIT
    ]
    # Then the beta suffix survives and every category is a bounded quoted string.
    assert not suffix and not malformed, (suffix, malformed)


def test_gantt_charts_pin_dates_and_disable_the_today_marker(rendered: str) -> None:
    # Given every gantt fence.
    charts = _mermaid(rendered, "gantt")
    required = {"todayMarker off", "dateFormat YYYY-MM-DD"}
    # When each chart's directive lines are read.
    missing = [
        f"L{f.line}: missing {sorted(required - {line.strip() for line in f.body})}"
        for f in charts
        if not required <= {line.strip() for line in f.body}
    ]
    # Then no timeline depends on the reader's wall clock or locale.
    assert not missing, missing


def test_every_percentage_is_derived_from_its_own_counts(rendered: str) -> None:
    # Given every percentage in a rendered dashboard.
    wrong: list[str] = []
    for index, line in enumerate(rendered.split("\n")):
        spans: list[tuple[int, int]] = []
        # When each ratio is recomputed from the counts printed beside it.
        for match in _RATIO.finditer(line):
            done, total, percent = (int(group) for group in match.groups())
            spans.append(match.span())
            if percent != (int(done * 100 / total) if total else 0):
                wrong.append(f"L{index + 1}: {match.group(0)!r} is not int(done * 100 / total)")
        wrong += [
            f"L{index + 1}: bare percentage {bare.group(0)!r} in {line!r}"
            for bare in _PERCENT.finditer(line)
            if not any(start <= bare.start() and bare.end() <= end for start, end in spans)
        ]
    # Then every percentage carries both counts and follows from them.
    assert not wrong, wrong


def test_every_heading_appears_once_in_the_published_order(rendered: str) -> None:
    # Given a rendered dashboard.
    # When its level two headings are read in order.
    headings = [line for line in rendered.split("\n") if line.startswith("## ")]
    # Then they are exactly the published skeleton, each appearing once.
    assert headings == list(dashboard.HEADINGS)


def test_mermaid_cli_parses_every_rendered_fence(tmp_path: Path) -> None:
    # Given the populated dashboard written out as a real TRACKING.md.
    if shutil.which("npx") is None:
        pytest.skip("mermaid validation needs npx on PATH and none was found")
    parent_fixture(tmp_path, late_run=True, graduated_anchor=True)
    (tmp_path / "TRACKING.md").write_text(dashboard.render_tracker(tmp_path), encoding="utf-8")
    # When mermaid-cli renders every fence of that file.
    try:
        done = subprocess.run(
            MMDC,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=MMDC_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"mermaid-cli could not start or finish offline: {exc!r}")
    output = f"{done.stdout}\n{done.stderr}".strip()
    if done.returncode != 0 and not any(marker in output for marker in PARSE_MARKERS):
        pytest.skip(f"mermaid-cli exited {done.returncode} for a non-parse reason: {output}")
    # Then mermaid accepts every fence and writes the converted document.
    assert done.returncode == 0, output
    assert (tmp_path / "out.md").is_file(), output
