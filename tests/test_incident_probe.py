from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from tools import incident_probe, sabotage

ROOT = Path(__file__).parents[1]


def test_probe_detects_inert_code_without_executing_candidate(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "candidate.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
        "def check_integrity():\n    return True\n",
        encoding="utf-8",
    )
    findings = incident_probe.probe(tmp_path)
    assert [(item.code, item.path) for item in findings] == [
        ("SAB_INERT_INSTRUMENT", ".audit/candidate.py")
    ]
    assert not marker.exists()


def test_probe_detects_changed_workflow_bypass_and_forged_disposition(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "gate.yaml").write_text(
        "run: python3 trinity/tools/integrity.py json parent . || true\n", encoding="utf-8"
    )
    (tmp_path / "VERDICT.md").write_text("# Verdict\n\n## Disposition\n\nSHIP\n", encoding="utf-8")
    codes = {item.code for item in incident_probe.probe(tmp_path, (".github/workflows/gate.yaml",))}
    assert codes == {"SAB_DISPOSITION_FORGED", "SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS"}


BENIGN_WORKFLOW = """jobs:
  build:
    steps:
      - run: pip cache purge || true
      - uses: actions/setup-python@v5
        continue-on-error: true
      - run: |
          git fetch --unshallow || true
      - name: gate
        run: |
          set -e
          python3 trinity/tools/integrity.py json parent .
  lint:
    continue-on-error: true
    steps:
      - run: ruff check .
"""


def test_probe_ignores_bypass_syntax_outside_the_gate_step(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "ci.yaml").write_text(BENIGN_WORKFLOW, encoding="utf-8")
    assert incident_probe.probe(tmp_path, (".github/workflows/ci.yaml",)) == []


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("integrity.py json parent .", "integrity.py json parent . || true"),
        ("      - name: gate\n", "      - name: gate\n        continue-on-error: true\n"),
        ("set -e", "set +e"),
        ("  build:\n", "  build:\n    continue-on-error: true\n"),
    ],
    ids=["or-true-on-gate", "step-continue-on-error", "set-plus-e", "job-continue-on-error"],
)
def test_probe_flags_bypass_syntax_on_the_gate_step(
    tmp_path: Path, before: str, after: str
) -> None:
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "ci.yaml").write_text(BENIGN_WORKFLOW.replace(before, after), encoding="utf-8")
    codes = {item.code for item in incident_probe.probe(tmp_path, (".github/workflows/ci.yaml",))}
    assert codes == {"SAB_GATE_WORKFLOW_EDITED_WITH_BYPASS"}


LIVE_PREDICATES = """def check_manifest(path):
    if not path.exists():
        return False
    return True

def check_digest(actual, expected):
    if actual != expected:
        raise ValueError("digest mismatch")
    return True

def verify_nothing():
    return True
"""


def test_probe_treats_branching_predicates_as_live(tmp_path: Path) -> None:
    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "predicates.py").write_text(LIVE_PREDICATES, encoding="utf-8")
    assert incident_probe.probe(tmp_path) == []


def test_probe_liveness_matches_the_sabotage_gate(tmp_path: Path) -> None:
    source = LIVE_PREDICATES + "\ndef check_integrity():\n    return True\n"
    tree = ast.parse(source)
    expected = {name for name, _line, _reason in sabotage.inert_functions(tree)}
    audit = tmp_path / ".audit"
    audit.mkdir()
    (audit / "mixed.py").write_text(source, encoding="utf-8")
    lines = {item.line for item in incident_probe.probe(tmp_path)}
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.lineno in lines
    }
    assert names == expected == {"check_integrity"}


def test_probe_refuses_symlinked_candidate_files(tmp_path: Path) -> None:
    audit = tmp_path / ".audit"
    audit.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text("def check_x():\n    return True\n", encoding="utf-8")
    (audit / "linked.py").symlink_to(outside)
    with pytest.raises(ValueError, match="symbolic"):
        incident_probe.probe(tmp_path)


def test_probe_output_is_bounded_closed_json(tmp_path: Path) -> None:
    payload = json.loads(incident_probe.render(incident_probe.probe(tmp_path)))
    assert set(payload) == {"codes", "evidence_digest", "schema"}
    assert payload["schema"] == incident_probe.SCHEMA
    assert re.fullmatch(r"[0-9a-f]{64}", payload["evidence_digest"])


def test_candidate_workflow_has_no_secret_dispatch_or_candidate_execution() -> None:
    text = (ROOT / "templates" / "sentinel.yaml").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "secrets." not in lowered
    assert "repository_dispatch" not in lowered
    assert "dispatches" not in lowered
    assert "gate.py" not in text
    assert "submodules: false" in text
    assert "incident_probe.py ./candidate-data" in text
    assert "python3 ./candidate-data" not in text
    assert "/tmp" not in text
    assert "./.trinity-runtime" in text
    assert "set +e" not in text
    assert "|| true" not in text


def test_observer_workflow_authenticates_sender_and_persists_probe_incidents() -> None:
    text = (ROOT / "templates" / "sentinel-observer.yaml").read_text(encoding="utf-8")
    assert "workflow_run" not in text
    assert "github.actor_id" in text
    assert "github.repository_id" in text
    assert "authorize_source" in text
    assert "authorize_target" in text
    assert "--source-repository-id" in text
    assert "api.github.com" in text
    assert "/actions/runs/" in text
    assert "incident_probe.py ./candidate-data" in text
    assert "gate.py" not in text
    assert "python3 candidate-data" not in text
    assert "OBSERVER_APP_TOKEN" in text
    assert "if: github.event_name == 'repository_dispatch'" in text
    assert "incident_store.py ingest" in text
    assert "set +e" not in text
    assert "|| true" not in text
    assert "/tmp" not in text
    assert "./.incident-service/config.json" in text
    assert "notify:" not in text
    assert "schedule:" not in text
    assert "SMTP" not in text
    assert "TRINITY_MAIL" not in text


@pytest.mark.parametrize("name", ["sentinel.yaml", "sentinel-observer.yaml"])
def test_workflow_actions_are_immutable_commit_pins(name: str) -> None:
    text = (ROOT / "templates" / name).read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*[^@\s]+@([^\s#]+)", text)
    assert uses
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in uses)


def test_observer_ingest_failure_is_not_suppressed() -> None:
    text = (ROOT / "templates" / "sentinel-observer.yaml").read_text(encoding="utf-8")
    ingest_line = next(line for line in text.splitlines() if "incident_store.py ingest" in line)
    assert "||" not in ingest_line
    assert "continue-on-error" not in text
