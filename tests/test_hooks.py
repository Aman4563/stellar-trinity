"""Installed report hooks exercised through real Git and the report-only CLI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from tools import gate, pipeline, report_staging, reports, runs
from tools._findings import Severity

from tests.test_gate import NOW, fake_gh, github_parent
from tests.tracker_fixtures import parent_fixture

ROOT = Path(__file__).resolve().parents[1]
HOOKS = (
    "pre-commit",
    "pre-merge-commit",
    "post-checkout",
    "post-merge",
    "post-rewrite",
    "pre-push",
)
ATTRIBUTES = tuple(
    f"{name} merge=trinity-generated"
    for name in ("TRACKING.md", "DIRECTIVE.md", "EDICT.md", "VERDICT.md")
)


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={
            **os.environ,
            "GIT_MASTER": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        },
    )


def checked_git(root: Path, *args: str) -> str:
    done = git(root, *args)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout.strip()


def hook(root: Path, name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", str(root / ".githooks" / name), *args],
        cwd=root,
        input="",
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


@pytest.fixture
def parent(tmp_path: Path) -> Path:
    root = tmp_path / "parent"
    parent_fixture(root)
    (root / "trinity").symlink_to(ROOT, target_is_directory=True)
    (root / ".gitignore").write_text(".sentinel/\n", encoding="utf-8")
    checked_git(root, "init", "-q", "-b", "main")
    gate.install(root, now=NOW)
    return root


def test_install_writes_every_hook_in_the_roster(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a parent with GitHub protection handled by the existing wire fake.
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    # When installation runs.
    installed = gate.install(root, now=NOW)
    # Then the complete public roster is written byte-for-byte and executable.
    assert gate.HOOK_TEMPLATES == HOOKS
    assert gate.hook_templates() == [
        (f".githooks/{name}", ROOT / "templates" / name) for name in HOOKS
    ]
    for relative, template in gate.hook_templates():
        assert relative in installed.written
        assert (root / relative).read_bytes() == template.read_bytes()
        assert os.access(root / relative, os.X_OK)


def test_install_writes_gitattributes_and_merge_driver(parent: Path) -> None:
    # Given foreign attributes, including a missing final newline.
    (parent / ".gitattributes").write_text("*.bin binary", encoding="utf-8")
    # When installing into an unborn repository.
    installed = gate.install(parent, now=NOW)
    # Then foreign lines survive and both driver settings are configured.
    assert (parent / gate.ATTRIBUTES_PATH).read_text().splitlines() == ["*.bin binary", *ATTRIBUTES]
    assert installed.hooks_path_set
    assert checked_git(parent, "config", "--get", "core.hooksPath") == gate.HOOK_DIR
    assert checked_git(parent, "config", "--get", f"merge.{gate.MERGE_DRIVER}.driver") == "true"
    assert checked_git(parent, "config", "--get", f"merge.{gate.MERGE_DRIVER}.name") == (
        "Trinity generated report; keep ours and re-render"
    )
    assert gate.install(parent, now=NOW).written == ()


def test_install_repairs_an_overriding_gitattributes_line(parent: Path) -> None:
    # Given present required lines overridden by a later foreign rule.
    target = parent / ".gitattributes"
    target.write_text("\n".join((*ATTRIBUTES, "*.md merge=union")) + "\n", encoding="utf-8")
    # When installation repairs the effective policy.
    installed = gate.install(parent, now=NOW)
    # Then the foreign rule survives above the winning report rules.
    assert gate.ATTRIBUTES_PATH in installed.written
    assert target.read_text().splitlines()[-5:] == ["*.md merge=union", *ATTRIBUTES]
    for line in ATTRIBUTES:
        name = line.split()[0]
        assert checked_git(parent, "check-attr", "merge", "--", name) == (
            f"{name}: merge: trinity-generated"
        )
    assert gate.install(parent, now=NOW).written == ()


def test_check_gates_installed_refuses_an_overridden_merge_driver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given installed gates with report attributes overridden by a later rule.
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    gate.install(root, now=NOW)
    with (root / ".gitattributes").open("a", encoding="utf-8") as handle:
        handle.write("*.md merge=union\n")
    # When checking the effective installed policy.
    findings = gate.check_gates_installed(str(root))
    # Then every affected path is named in an attributes refusal.
    assert findings
    assert all(item.code == gate.GATE_ATTRIBUTES_MISSING for item in findings)
    for line in ATTRIBUTES:
        assert any(line.split()[0] in item.message for item in findings)


@pytest.mark.parametrize("name", HOOKS)
def test_check_gates_installed_refuses_a_drifted_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    # Given an installed parent with one drifted hook.
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    gate.install(root, now=NOW)
    target = root / ".githooks" / name
    target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    # When checking the installed surfaces.
    findings = gate.check_gates_installed(str(root))
    # Then exactly the drifted hook is an error.
    assert [(item.code, item.severity, item.path) for item in findings] == [
        (gate.GATE_HOOK_MISSING, Severity.ERROR, str(target))
    ]


@pytest.mark.parametrize("setting", (None, "union"))
def test_check_gates_installed_refuses_a_missing_merge_driver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, setting: str | None
) -> None:
    # Given a driver that is absent or unsafe.
    root = github_parent(tmp_path)
    fake_gh(tmp_path, monkeypatch)
    gate.install(root, now=NOW)
    key = "merge.trinity-generated.driver"
    checked_git(root, "config", "--unset", key) if setting is None else checked_git(
        root, "config", key, setting
    )
    # When checking the parent.
    findings = gate.check_gates_installed(str(root))
    # Then the merge policy refuses as an error.
    assert [(item.code, item.severity) for item in findings] == [
        (gate.GATE_MERGE_DRIVER_MISSING, Severity.ERROR)
    ]


def test_pre_commit_refuses_stale_staged_reports_and_writes_expected_bytes(parent: Path) -> None:
    # Given stale staged reports and fully staged inputs.
    expected = reports.rendered_root_reports(parent)
    (parent / "TRACKING.md").write_text("stale\n", encoding="utf-8")
    checked_git(parent, "add", "-A")
    # When a human attempts a commit with the installed hook.
    done = git(parent, "-c", "core.hooksPath=.githooks", "commit", "-m", "scaffold")
    # Then commit refuses, renders the expected bytes, and leaves the index untouched.
    assert done.returncode == 1, done.stdout + done.stderr
    assert "wrote " in done.stderr
    assert checked_git(parent, "show", ":TRACKING.md") == "stale"
    assert {name: (parent / name).read_text() for name in expected} == expected


def test_pre_commit_refuses_unstaged_inputs(parent: Path) -> None:
    # Given a staged snapshot whose report inputs subsequently change.
    reports.render_root_reports(parent)
    checked_git(parent, "add", "-A")
    source = next((parent / ".seed/runs").glob("*/progress.yaml"))
    source.write_text(source.read_text() + "\n# unstaged input\n", encoding="utf-8")
    # When committing without staging that input.
    done = git(parent, "-c", "core.hooksPath=.githooks", "commit", "-m", "partial")
    # Then the commit refuses for the staged-input finding.
    assert done.returncode == 1, done.stdout + done.stderr
    assert (
        source.relative_to(parent).as_posix()
        in (parent / ".sentinel/pre-commit-reports.txt").read_text()
    )


def test_staged_check_refuses_when_git_status_fails(
    parent: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given current staged reports but an unavailable status inventory.
    reports.render_root_reports(parent)
    checked_git(parent, "add", "-A")
    real_git = report_staging._git

    def unavailable_status(root: Path, *arguments: str) -> bytes | None:
        return None if arguments[0] == "status" else real_git(root, *arguments)

    monkeypatch.setattr(report_staging, "_git", unavailable_status)
    monkeypatch.chdir(parent)
    # When the commit-time CLI checks the index.
    code = pipeline.main(["pipeline.py", "render-reports", "./", "--check", "--staged"])
    # Then status failure refuses rather than claiming a clean inventory.
    assert code == 3
    assert "REPORT_STAGED_UNAVAILABLE" in capsys.readouterr().out


@pytest.mark.parametrize("lane", ("staging", "samples", "delivery"))
def test_staged_check_refuses_an_untracked_staging_bundle(parent: Path, lane: str) -> None:
    # Given an untracked bundle while all report bytes are staged and current.
    checked_git(parent, "add", "-A")
    bundle = parent / lane / "c663e086-b586-5876-9d70-8152ea59ed90"
    bundle.mkdir(parents=True)
    (bundle / "task.txt").write_text("untracked bundle\n", encoding="utf-8")
    reports.render_root_reports(parent)
    checked_git(parent, "add", "TRACKING.md", "DIRECTIVE.md", "EDICT.md", "VERDICT.md")
    # When the real report CLI checks the index.
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/pipeline.py"),
            "render-reports",
            "./",
            "--check",
            "--staged",
        ],
        cwd=parent,
        capture_output=True,
        text=True,
        check=False,
    )
    # Then the missing bundle is named even though the reports themselves match.
    assert done.returncode == 3, done.stdout + done.stderr
    assert "REPORT_INPUTS_UNSTAGED" in done.stdout
    assert f"{lane}/" in done.stdout


@pytest.mark.parametrize("name", ("post-merge", "post-rewrite"))
def test_post_merge_refresh_is_advisory(parent: Path, name: str) -> None:
    # Given stale reports and a malformed card that the dashboard must diagnose.
    next((parent / ".seed/runs").glob("*/tracker.json")).write_text("{", encoding="utf-8")
    expected = reports.rendered_root_reports(parent)
    # When the post-operation hook runs.
    done = hook(parent, name)
    # Then it refreshes bytes without failing or staging anything.
    assert done.returncode == 0, done.stderr
    assert "rendered " in done.stdout
    assert {name: (parent / name).read_text() for name in expected} == expected
    assert checked_git(parent, "ls-files") == ""


@pytest.mark.parametrize("flag", ("0", "1"))
def test_post_checkout_warns_and_never_fails(parent: Path, flag: str) -> None:
    # Given a stale checkout.
    (parent / "TRACKING.md").write_text("stale\n", encoding="utf-8")
    # When checking out files or a branch.
    done = hook(parent, "post-checkout", "a" * 40, "b" * 40, flag)
    # Then branch checkout warns, file checkout is silent, and neither writes a report.
    assert done.returncode == 0
    assert bool(done.stderr) == (flag == "1")
    assert (parent / "TRACKING.md").read_text() == "stale\n"


def test_pre_push_refuses_a_commit_that_is_not_the_reconciled_head(parent: Path) -> None:
    # Given a reconciled HEAD and a push of another local commit to a new remote ref.
    pipeline.reconcile(parent)
    checked_git(parent, "add", "-A")
    checked_git(parent, "commit", "-m", "reconciled")
    # When the real pre-push protocol names a different local SHA.
    done = subprocess.run(
        ["sh", ".githooks/pre-push"],
        cwd=parent,
        input=f"refs/heads/other {'1' * 40} refs/heads/other {'0' * 40}\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    # Then it refuses before invoking the qualification gate.
    assert done.returncode == 1
    assert "the pushed commit is not the reconciled HEAD" in done.stderr
    assert not (parent / ".sentinel/pre-push.json").exists()


def pipeline_cli(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "./trinity/tools/pipeline.py", *args, "./", "--check", "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_a_superseded_card_never_refuses_reconcile_or_the_push(parent: Path) -> None:
    # Given a reconciled tree whose frozen run lawfully resumed and rewrote its report.
    pipeline.reconcile(parent)
    report = next((parent / ".seed/runs").glob("*/report.md"))
    report.write_bytes(report.read_bytes() + b"\n")
    pipeline.reconcile(parent)
    # When both hook-facing entry points run in check mode.
    reconciled = pipeline_cli(parent, "reconcile")
    rendered = pipeline_cli(parent, "render-reports")
    done = hook(parent, "pre-push")
    # Then the card is named once as an advisory and neither entry point refuses.
    advisory = [("TRACKER_CARD_SUPERSEDED", "advisory")]
    assert reconciled.returncode == 0, reconciled.stdout + reconciled.stderr
    assert [
        (item["code"], item["severity"]) for item in json.loads(reconciled.stdout)["findings"]
    ] == advisory
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    assert [(item["code"], item["severity"]) for item in json.loads(rendered.stdout)] == advisory
    # And the pre-push hook passes its reconciliation stage on to the gate.
    assert "the tree is not reconciled" not in done.stderr
    assert (
        "the run continued after closure: report.md moved"
        in (parent / ".sentinel/pre-push-reconcile.txt").read_text()
    )


def test_real_git_push_of_a_non_head_commit_is_refused_before_the_gate(
    parent: Path, tmp_path: Path
) -> None:
    # Given two reconciled commits and a bare remote.
    pipeline.reconcile(parent)
    checked_git(parent, "add", "-A")
    checked_git(parent, "commit", "-m", "first")
    (parent / "note.txt").write_text("second\n", encoding="utf-8")
    checked_git(parent, "add", "note.txt")
    checked_git(parent, "commit", "-m", "second")
    remote = tmp_path / "origin.git"
    assert git(tmp_path, "init", "-q", "--bare", str(remote)).returncode == 0
    checked_git(parent, "remote", "add", "origin", str(remote))
    # When git itself runs the hook for a push of HEAD~1, feeding the ref line on stdin.
    done = git(parent, "push", "origin", "HEAD~1:refs/heads/main")
    # Then the ref loop, not the gate, refuses: the check that ran first must not eat stdin.
    assert done.returncode != 0
    assert "the pushed commit is not the reconciled HEAD" in done.stderr
    assert not (parent / ".sentinel/pre-push.json").exists()


def test_no_hook_issues_a_git_write() -> None:
    # Given every installed template, excluding comments.
    bodies = [
        line
        for name in HOOKS
        for line in (ROOT / "templates" / name).read_text().splitlines()
        if not line.lstrip().startswith("#")
    ]
    # When scanning executable shell text for forbidden Git commands.
    # Then no hook stages or changes history.
    assert not any(
        re.search(r"\bgit\s+(add|commit|push|stash|checkout)\b", line) for line in bodies
    )


@pytest.mark.parametrize("name", ("post-merge", "post-rewrite", "post-checkout"))
def test_advisory_hooks_allow_renderer_failure(parent: Path, name: str) -> None:
    # Given a directory blocking the output file.
    (parent / "TRACKING.md").mkdir()
    # When an advisory hook encounters the I/O failure.
    done = hook(parent, name, "a" * 40, "b" * 40, "1")
    # Then it never fails the completed Git operation.
    assert done.returncode == 0


def test_check_gates_installed_refuses_missing_attributes(parent: Path) -> None:
    # Given a committed parent whose attributes subsequently drift.
    reports.render_root_reports(parent)
    checked_git(parent, "add", "-A")
    checked_git(parent, "commit", "-m", "base")
    (parent / ".gitattributes").write_text("*.bin binary\n", encoding="utf-8")
    # When checking the installed surfaces.
    findings = gate.check_gates_installed(str(parent))
    # Then the missing generated-report policy is an error.
    assert (gate.GATE_ATTRIBUTES_MISSING, Severity.ERROR) in [
        (item.code, item.severity) for item in findings
    ]


def test_merge_driver_keeps_ours_and_rerender_is_byte_identical(
    parent: Path, tmp_path: Path
) -> None:
    # Given two clones whose valid rendered dashboards diverge with disjoint inputs.
    reports.render_root_reports(parent)
    checked_git(parent, "add", "-A")
    checked_git(parent, "commit", "-m", "base")
    clones = [tmp_path / name for name in ("ours", "theirs")]
    for clone, gate_id in zip(clones, ("left", "right"), strict=True):
        checked_git(tmp_path, "clone", "-q", str(parent), str(clone))
        checked_git(clone, "remote", "remove", "origin")
        gate.install(clone, now=NOW)
        # Distinct run directories ensure both branches change the dashboard, not one line of input.
        runs.open_run(clone, "FORGE", f"forge-{gate_id}", principal=gate_id, now=NOW)
        reports.render_root_reports(clone)
        checked_git(clone, "add", "-A")
        checked_git(clone, "commit", "-m", gate_id)
    ours, theirs = clones
    before = (ours / "TRACKING.md").read_bytes()
    checked_git(ours, "fetch", "-q", str(theirs), "main")
    # When Git merges using the installed keep-ours driver, without committing yet.
    done = git(ours, "merge", "--no-commit", "--no-ff", "FETCH_HEAD")
    # Then the driver leaves ours, and a full rerender matches a fresh merged-tree render.
    assert done.returncode == 0, done.stdout + done.stderr
    assert checked_git(ours, "show", ":TRACKING.md").encode() + b"\n" == before
    assert b"<<<<<<<" not in (ours / "TRACKING.md").read_bytes()
    fresh = tmp_path / "fresh"
    shutil.copytree(
        ours,
        fresh,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git", ".sentinel", "TRACKING.md", *reports.ROOT_REPORTS.values()
        ),
    )
    expected = reports.rendered_root_reports(fresh)
    rendered = subprocess.run(
        [sys.executable, "trinity/tools/pipeline.py", "render-reports", "./"],
        cwd=ours,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    assert {name: (ours / name).read_text() for name in expected} == expected
    checked_git(ours, "add", "-A")
    checked_git(ours, "commit", "-m", "merged rendered tree")
