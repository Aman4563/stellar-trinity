"""RED-to-GREEN proof that ``tools/render.py`` projects the TODO backlog from disk."""

from __future__ import annotations

from pathlib import Path

import pytest
from tools import render, reports, runs, subject

from tests import parent_fixtures

ENGRAM_RUN = "engram-ada-todo-1"
FORGE_RUN = "forge-ada-todo-1"
BUCKET_D_MODULE = ".memory/ingest.py"
BUCKET_D_CONSEQUENCE = "the ledger holds at STALE"
UNPROVEN_INSTRUMENT = "ingestor"
PROVEN_INSTRUMENT = "freshener"
CAPABILITIES_WITH_BUCKET_D = (
    "capabilities:\n"
    f"  - id: {parent_fixtures.CAPABILITY_DECLARED}\n"
    "    state: declared\n"
    "    definition: the gatekeeper identity and its gate_approver role\n"
    "    module: .memory/gatekeeper.py\n"
    "    consequence: every digest gate stays human\n"
    f"  - id: {parent_fixtures.CAPABILITY_IMPLEMENTED}\n"
    "    state: implemented\n"
    "bucket_d_status:\n"
    f"  - instrument: {UNPROVEN_INSTRUMENT}\n"
    "    bytes_present: false\n"
    "    implemented: false\n"
    "    liveness_proven: false\n"
    f"    module: {BUCKET_D_MODULE}\n"
    f"    consequence: {BUCKET_D_CONSEQUENCE}\n"
    f"  - instrument: {PROVEN_INSTRUMENT}\n"
    "    bytes_present: true\n"
    "    implemented: true\n"
    "    liveness_proven: true\n"
)


def build(root: Path, instrument: str, run_id: str, *, principal: str = "ada") -> Path:
    return parent_fixtures.write_resume_parent(root, instrument, run_id, principal=principal)


def write_capabilities(root: Path, instrument: str, body: str) -> None:
    harness = root / runs.HARNESS[instrument]
    (harness / "capabilities.yaml").write_text(body, encoding="utf-8")


def write_report(directory: Path, gaps: str) -> None:
    bodies = dict.fromkeys(reports.REPORT_SECTIONS, "Section content.")
    bodies["Coverage gaps"] = gaps
    text = "\n\n".join(f"## {name}\n\n{bodies[name]}" for name in reports.REPORT_SECTIONS)
    (directory / "report.md").write_text(f"{text}\n", encoding="utf-8")


def todo_path(root: Path, instrument: str, run_id: str) -> Path:
    return runs.run_dir(root, instrument, run_id) / "TODO.md"


def emit(*argv: str) -> int:
    return render.main(["render.py", "todo", "./", *argv])


def engram(*argv: str) -> int:
    return emit("--instrument", "ENGRAM", "--run", ENGRAM_RUN, "--principal", "ada", *argv)


def rendered(root: Path, instrument: str = "ENGRAM", run_id: str = ENGRAM_RUN) -> str:
    return todo_path(root, instrument, run_id).read_text(encoding="utf-8")


def test_todo_is_byte_identical_on_repeat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "fixture"
    directory = build(root, "ENGRAM", ENGRAM_RUN)
    write_report(directory, "- one gap")
    monkeypatch.chdir(root)

    assert engram() == 0
    first = todo_path(root, "ENGRAM", ENGRAM_RUN).read_bytes()
    assert engram() == 0

    assert todo_path(root, "ENGRAM", ENGRAM_RUN).read_bytes() == first


def test_todo_carries_the_shared_generated_banner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    build(root, "ENGRAM", ENGRAM_RUN)
    monkeypatch.chdir(root)

    assert engram() == 0

    assert reports.GENERATED_BANNER in rendered(root)
    module = Path(str(render.__file__)).read_text(encoding="utf-8")
    assert reports.GENERATED_BANNER not in module


def test_todo_names_capabilities_yaml_as_its_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    build(root, "ENGRAM", ENGRAM_RUN)
    monkeypatch.chdir(root)

    assert engram() == 0

    assert ".memory/capabilities.yaml" in rendered(root)


def test_declared_but_unimplemented_capability_gets_a_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    build(root, "ENGRAM", ENGRAM_RUN)
    write_capabilities(root, "ENGRAM", CAPABILITIES_WITH_BUCKET_D)
    monkeypatch.chdir(root)

    assert engram() == 0

    text = rendered(root)
    assert parent_fixtures.CAPABILITY_DECLARED in text
    assert ".memory/gatekeeper.py" in text
    assert "every digest gate stays human" in text


def test_implemented_capability_gets_no_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    build(root, "ENGRAM", ENGRAM_RUN)
    monkeypatch.chdir(root)

    assert engram() == 0

    assert parent_fixtures.CAPABILITY_IMPLEMENTED not in rendered(root)


def test_every_coverage_gap_gets_a_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "fixture"
    directory = build(root, "ENGRAM", ENGRAM_RUN)
    write_report(directory, "- hardness catalog is empty\n- cohort-refresh-overdue\n- no anchor")
    monkeypatch.chdir(root)

    assert engram() == 0

    text = rendered(root)
    for gap in ("hardness catalog is empty", "cohort-refresh-overdue", "no anchor"):
        assert gap in text


def test_engram_renders_bucket_d_liveness_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    build(root, "ENGRAM", ENGRAM_RUN)
    write_capabilities(root, "ENGRAM", CAPABILITIES_WITH_BUCKET_D)
    monkeypatch.chdir(root)

    assert engram() == 0

    text = rendered(root)
    assert UNPROVEN_INSTRUMENT in text
    assert BUCKET_D_MODULE in text
    assert BUCKET_D_CONSEQUENCE in text
    assert PROVEN_INSTRUMENT not in text


def test_forge_renders_no_bucket_d_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "fixture"
    build(root, "FORGE", FORGE_RUN)
    write_capabilities(root, "FORGE", CAPABILITIES_WITH_BUCKET_D)
    monkeypatch.chdir(root)

    assert emit("--instrument", "FORGE", "--run", FORGE_RUN, "--principal", "ada") == 0

    text = rendered(root, "FORGE", FORGE_RUN)
    assert parent_fixtures.CAPABILITY_DECLARED in text
    assert UNPROVEN_INSTRUMENT not in text
    assert "bucket_d_status" not in text


def test_check_exits_zero_on_a_freshly_rendered_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    directory = build(root, "ENGRAM", ENGRAM_RUN)
    write_report(directory, "- one gap")
    monkeypatch.chdir(root)
    assert engram() == 0

    assert engram("--check") == 0


def test_check_exits_two_with_todo_drift_after_a_hand_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "fixture"
    build(root, "ENGRAM", ENGRAM_RUN)
    monkeypatch.chdir(root)
    assert engram() == 0
    path = todo_path(root, "ENGRAM", ENGRAM_RUN)
    hand_edited = path.read_bytes() + b"x\n"
    path.write_bytes(hand_edited)
    capsys.readouterr()

    code = engram("--check")

    captured = capsys.readouterr()
    assert code == 2
    assert render.DRIFT in captured.out
    assert path.read_bytes() == hand_edited


def test_todo_is_excluded_from_the_subject_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    directory = build(root, "ENGRAM", ENGRAM_RUN)
    write_report(directory, "- one gap")
    monkeypatch.chdir(root)
    before = subject.subject_digest(root, "ENGRAM", ENGRAM_RUN)

    assert engram() == 0

    assert subject.subject_digest(root, "ENGRAM", ENGRAM_RUN) == before


def test_render_refuses_a_run_owned_by_another_principal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "fixture"
    build(root, "ENGRAM", ENGRAM_RUN, principal="ada")
    monkeypatch.chdir(root)

    code = emit("--instrument", "ENGRAM", "--run", ENGRAM_RUN, "--principal", "bob")

    assert code == 3
    assert not todo_path(root, "ENGRAM", ENGRAM_RUN).exists()
