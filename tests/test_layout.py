from __future__ import annotations

import os
import shutil
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager
from functools import partial
from pathlib import Path

import pytest
from tools import layout, sabotage
from tools._findings import Finding

from tests.bite_shared.registration import bite
from tests.harness_imports import integrity, load_harness
from tests.parent_fixtures import commit_all, git, write_clean_parent, write_submodule_parent

gate = load_harness("gate")

UUID = "00000000-0000-5000-8000-000000000000"
ROSTER_GITMODULES = (
    '[submodule "trinity"]\n\tpath = trinity\n\tURL = https://example.invalid/trinity.git\n'
    "\tBranch = main\n\tupdate = merge\n\n"
    '[submodule "vendor"]\n\t# pinned by the roster\n\tpath = vendor/x\n'
    "\turl = https://example.invalid/vendor.git\n\n"
    '[submodule "nourl"]\n\tpath = nourl\n'
)
TRINITY_KEYS = {
    "path": "trinity",
    "url": "https://example.invalid/trinity.git",
    "branch": "main",
    "update": "merge",
}
VENDOR_KEYS = {"path": "vendor/x", "url": "https://example.invalid/vendor.git"}


def test_roster_is_closed_and_trajectories_are_lawful() -> None:
    assert hasattr(layout, "LAYOUT_ROSTER")
    roster = layout.LAYOUT_ROSTER

    assert tuple(root.path for root in roster) == (
        "trinity",
        ".memory",
        "samples",
        "delivery",
        "harness",
        "staging",
    )
    assert layout.REQUIRED_ROOTS == ("trinity", ".memory", "samples", "delivery", "harness")
    assert frozenset((*layout.REQUIRED_ROOTS, "staging")) == layout.KNOWN_ROOTS
    assert layout.PROTECTED_ROOTS == (".memory", "samples", "delivery", "harness", "staging")
    assert layout.RETIRED_ROOTS == ("deliverables",)
    assert all("trajectories" not in root.forbidden for root in roster)
    assert "trajectories" not in layout.BUNDLE_FORBIDDEN
    assert all("deliverables" in root.forbidden for root in roster if root.path != "trinity")
    assert tuple(root.required for root in roster) == (True, True, True, True, True, False)
    assert tuple(root.kind.name for root in roster) == (
        "TOOLING",
        "HARNESS",
        "BUNDLE_PUBLIC",
        "BUNDLE_PRIVATE",
        "RUNNER",
        "STAGING",
    )
    assert tuple(root.audience.name for root in roster) == (
        "VENDORED",
        "INSTRUMENT",
        "PUBLIC",
        "CORPUS",
        "PUBLIC",
        "CORPUS",
    )
    assert all(
        root.forbidden == layout.BUNDLE_FORBIDDEN
        for root in roster
        if root.path in {"samples", "delivery", "staging"}
    )


def test_parse_gitmodules_handles_tab_indented_keys_and_reports_malformed_sections() -> None:
    text = (
        '[submodule "lane"]\n\tPath = samples/task\n\tURL = first\n\turl = ignored\n'
        '\tbranch = main\n\tupdate = merge\n[submodule "missing-url"]\npath = delivery\n'
        '[submodule "missing-path"]\nurl = remote\n[submodule broken\npath = injected\n'
        '[other "section"]\nurl = unrelated\n'
    )

    sections, malformed = layout.parse_gitmodules(text)

    assert tuple(section.name for section in sections) == ("lane", "missing-url", "missing-path")
    assert sections[0].keys == {
        "path": "samples/task",
        "url": "first",
        "branch": "main",
        "update": "merge",
    }
    assert (sections[0].path, sections[0].url, sections[0].branch, sections[0].update) == (
        "samples/task",
        "first",
        "main",
        "merge",
    )
    assert sections[1].url == sections[1].branch == sections[1].update == ""
    assert sections[2].path == ""
    assert len(malformed) == 4
    assert 'section "lane" repeats key url' in malformed


def test_section_for_matches_first_path_segment() -> None:
    sections, _ = layout.parse_gitmodules(
        '[submodule "first"]\npath = /samples/nested/\nurl = first\n'
        '[submodule "second"]\npath = samples\nurl = second\n'
        '[submodule "prefix"]\npath = samples-extra\nurl = third\n'
        '[submodule "empty"]\nurl = fourth\n'
    )

    selected = layout.section_for(sections, "samples")

    assert selected is sections[0]
    assert layout.section_for(sections, "sample") is None
    assert layout.declared_paths(sections) == frozenset({"samples", "samples-extra"})


def test_scan_forbidden_matches_directory_segment_at_any_depth(tmp_path: Path) -> None:
    leak = tmp_path / "samples" / UUID / ".memory" / "x"
    leak.parent.mkdir(parents=True)
    leak.touch()
    (tmp_path / ".memory-copy").mkdir()

    result = layout.scan_forbidden(tmp_path, (".memory",))

    assert result.leaks == (f"samples/{UUID}/.memory", f"samples/{UUID}/.memory/x")
    assert result.entries == 5
    assert not result.truncated


def test_scan_forbidden_matches_hardness_basename_at_any_depth(tmp_path: Path) -> None:
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "HARDNESS.md").touch()
    (tmp_path / "HARDNESS.md").touch()
    (tmp_path / "deep" / "HARDNESS.md.bak").touch()
    (tmp_path / "deep" / "hardness.md").touch()

    result = layout.scan_forbidden(tmp_path, ("HARDNESS.md",))

    assert result.leaks == ("HARDNESS.md", "deep/HARDNESS.md")


def test_scan_forbidden_never_follows_symlinks_and_reports_them(tmp_path: Path) -> None:
    (tmp_path / "escape").symlink_to(tmp_path.parent, target_is_directory=True)
    (tmp_path / "broken").symlink_to(tmp_path / "missing")
    (tmp_path / "HARDNESS.md").touch()
    (tmp_path / "file-link").symlink_to(tmp_path / "HARDNESS.md")

    result = layout.scan_forbidden(tmp_path, ("HARDNESS.md",))

    assert result.symlinks == ("broken", "escape", "file-link")
    assert result.leaks == ("HARDNESS.md",)
    assert result.entries == 4
    assert all(
        not Path(path).is_absolute() and ".." not in Path(path).parts
        for path in (*result.leaks, *result.symlinks)
    )


def test_scan_forbidden_skips_dot_git(tmp_path: Path) -> None:
    (tmp_path / ".git" / ".memory").mkdir(parents=True)
    (tmp_path / "deep" / ".git").mkdir(parents=True)
    (tmp_path / "deep" / ".git" / "HARDNESS.md").touch()

    result = layout.scan_forbidden(tmp_path, layout.BUNDLE_FORBIDDEN)

    assert result.leaks == result.symlinks == ()
    assert result.entries == 3


def test_scan_forbidden_preserves_findings_when_second_directory_is_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "HARDNESS.md").touch()
    (tmp_path / "link").symlink_to(tmp_path / "HARDNESS.md")
    (tmp_path / "locked").mkdir()
    scandir = os.scandir

    def fail_on_descend(path: Path) -> AbstractContextManager[Iterator[os.DirEntry[str]]]:
        if path != tmp_path:
            raise PermissionError(path)
        return scandir(path)

    monkeypatch.setattr(os, "scandir", fail_on_descend)

    result = layout.scan_forbidden(tmp_path, ("HARDNESS.md",))

    assert result.leaks == ("HARDNESS.md",)
    assert result.symlinks == ("link",)
    assert result.unreadable == ("locked",)
    assert result.truncated


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses directory permissions")
def test_unreadable_directory_does_not_erase_an_observed_leak(layout_root: Path) -> None:
    (layout_root / "samples" / "HARDNESS.md").touch()
    locked = layout_root / "samples" / "locked"
    locked.mkdir()
    locked.chmod(0o000)
    try:
        findings = integrity.check_parent_layout(str(layout_root))
    finally:
        locked.chmod(0o700)

    assert codes(findings) == {
        layout.PARENT_LAYOUT_BOUNDARY_LEAK,
        layout.PARENT_LAYOUT_SCAN_TRUNCATED,
    }
    assert gate.ceiling(findings) == gate.BLOCK


def test_scan_forbidden_truncates_at_max_entries_and_reports_it(tmp_path: Path) -> None:
    for index in range(4):
        (tmp_path / str(index)).touch()

    result = layout.scan_forbidden(tmp_path, (), max_entries=2)

    assert result.truncated
    assert result.entries == 3
    assert layout.SCAN_MAX_ENTRIES == 20_000


def test_scan_forbidden_accepts_exact_budget(tmp_path: Path) -> None:
    (tmp_path / "only").touch()

    result = layout.scan_forbidden(tmp_path, (), max_entries=1)

    assert result == layout.ScanResult((), (), False, 1)


def test_solution_directory_is_not_a_leak(tmp_path: Path) -> None:
    (tmp_path / UUID / "solution").mkdir(parents=True)
    (tmp_path / UUID / "solution" / "solve.py").touch()
    (tmp_path / UUID / "trajectories").mkdir()

    result = layout.scan_forbidden(tmp_path, layout.BUNDLE_FORBIDDEN)

    assert result.leaks == ()
    assert all("solution" not in root.forbidden for root in layout.LAYOUT_ROSTER)


def test_bundle_shaped_directories_are_forbidden_only_in_memory(tmp_path: Path) -> None:
    (tmp_path / "deep" / UUID).mkdir(parents=True)
    (tmp_path / UUID).touch()
    forbidden = next(root.forbidden for root in layout.LAYOUT_ROSTER if root.path == ".memory")

    result = layout.scan_forbidden(tmp_path, forbidden)

    assert result.leaks == (f"deep/{UUID}",)
    assert layout.is_bundle_shaped(UUID)
    assert not layout.is_bundle_shaped(UUID.replace("5000", "4000"))
    assert not layout.is_bundle_shaped(UUID.replace("8000", "7000"))
    assert not layout.is_bundle_shaped(f"prefix-{UUID}")


def test_blocking_codes_are_the_five_boundary_codes_and_all_codes_are_prefixed() -> None:
    expected = frozenset(
        {
            "PARENT_LAYOUT_UNKNOWN_SUBMODULE",
            "PARENT_LAYOUT_SHARED_REMOTE",
            "PARENT_LAYOUT_PARENT_TRACKS_BUNDLE",
            "PARENT_LAYOUT_BOUNDARY_LEAK",
            "PARENT_LAYOUT_SYMLINK",
        }
    )

    assert expected == layout.BLOCKING_CODES
    assert (
        expected
        | {
            "PARENT_LAYOUT_GITMODULES_INVALID",
            "PARENT_LAYOUT_SUBMODULE_MISSING",
            "PARENT_LAYOUT_PLAIN_DIRECTORY",
            "PARENT_LAYOUT_BRANCH_INVALID",
            "PARENT_LAYOUT_RETIRED_ROOT",
            "PARENT_LAYOUT_RUNTIME_UNIGNORED",
            "PARENT_LAYOUT_SCAN_TRUNCATED",
        }
        == layout.LAYOUT_CODES
    )
    assert all(code.startswith("PARENT_LAYOUT_") for code in layout.LAYOUT_CODES)
    assert all(getattr(layout, code) == code for code in layout.LAYOUT_CODES)


def test_one_parser_serves_every_caller(tmp_path: Path) -> None:
    planted = tmp_path / "planted"
    planted.mkdir()
    (planted / ".gitmodules").write_text(ROSTER_GITMODULES, encoding="utf-8")

    sections, malformed = layout.parse_gitmodules(ROSTER_GITMODULES)
    selected = layout.section_for(sections, "trinity")

    assert selected is not None
    assert dict(selected.keys) == TRINITY_KEYS
    assert malformed == ("submodule 'nourl': missing url",)
    assert (
        integrity.submodule_section(ROSTER_GITMODULES, "trinity")
        == sabotage.gitmodules_section(ROSTER_GITMODULES, "trinity")
        == dict(selected.keys)
    )
    assert (
        integrity.submodule_section(ROSTER_GITMODULES, "vendor")
        == sabotage.gitmodules_section(ROSTER_GITMODULES, "vendor")
        == VENDOR_KEYS
    )
    assert (
        integrity.submodule_section(ROSTER_GITMODULES, "vendor/x")
        == sabotage.gitmodules_section(ROSTER_GITMODULES, "vendor/x")
        == {}
    )
    assert integrity.submodule_paths(str(planted)) == {"trinity", "vendor", "nourl"}
    assert integrity.submodule_paths(str(planted)) == layout.declared_paths(sections)
    assert integrity.submodule_paths(str(tmp_path / "absent")) == set()


def codes(findings: list[Finding]) -> set[str]:
    return {finding.code for finding in findings}


def make_layout_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    roster: Sequence[str] = layout.REQUIRED_ROOTS,
    plain: Sequence[str] = (),
    shared_remote: tuple[str, str] | None = None,
    gitignore: bool = True,
) -> Path:
    remotes = tmp_path / "remotes"
    remotes.mkdir()
    seed = tmp_path / "seed"
    git(["init", "-q", "-b", "main", str(seed)], cwd=tmp_path)
    (seed / "README.md").write_text("fixture\n", encoding="utf-8")
    commit_all(seed, "seed genesis")
    for name in roster:
        git(["clone", "-q", "--bare", str(seed), str(remotes / f"{name}.git")], cwd=tmp_path)
    root = tmp_path / "parent"
    write_submodule_parent(root, lambda _: None, roster=roster, plain=plain)
    if shared_remote is not None:
        first, second = shared_remote
        git(
            [
                "config",
                "-f",
                ".gitmodules",
                f"submodule.{second}.url",
                str(remotes / f"{first}.git"),
            ],
            cwd=root,
        )
    monkeypatch.setenv(sabotage.CANONICAL_REMOTE_ENV, str(remotes / "trinity.git"))
    if gitignore:
        (root / ".gitignore").write_text(".secrets/\n.trinity-runtime/\n", encoding="utf-8")
    commit_all(root, "parent genesis")
    return root


@pytest.fixture
def layout_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return make_layout_parent(tmp_path, monkeypatch)


def test_layout_accepts_the_full_roster(layout_root: Path) -> None:
    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == set()
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


def test_layout_is_silent_outside_a_git_repository(tmp_path: Path) -> None:
    root = tmp_path / "parent"
    write_clean_parent(root, lambda _: None)

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == set()
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


@bite("shared.md:A73")
def test_missing_submodule_registration_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roster = tuple(name for name in layout.REQUIRED_ROOTS if name != "harness")
    root = make_layout_parent(tmp_path, monkeypatch, roster=roster)

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_SUBMODULE_MISSING}
    assert [finding.path for finding in findings] == [str(root / "harness")]
    assert gate.ceiling(findings) == gate.HOLD


@bite("shared.md:A74")
def test_plain_directory_lane_root_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_layout_parent(tmp_path, monkeypatch, plain=("samples",))

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_PLAIN_DIRECTORY}
    assert [finding.path for finding in findings] == [str(root / "samples")]
    assert gate.ceiling(findings) == gate.HOLD


def test_unregistered_plain_directory_is_missing_not_plain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_layout_parent(tmp_path, monkeypatch, plain=("samples",))
    git(["config", "-f", ".gitmodules", "--remove-section", "submodule.samples"], cwd=root)

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_SUBMODULE_MISSING}
    assert layout.PARENT_LAYOUT_PLAIN_DIRECTORY not in codes(findings)
    assert gate.ceiling(findings) == gate.HOLD


@pytest.mark.parametrize("submodule", [False, True])
def test_staging_is_lawful_as_gitlink_or_plain_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, submodule: bool
) -> None:
    roster = (*layout.REQUIRED_ROOTS, "staging") if submodule else layout.REQUIRED_ROOTS
    root = make_layout_parent(tmp_path, monkeypatch, roster=roster)
    (root / "staging").mkdir(exist_ok=True)

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == set()
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


@bite("shared.md:A79")
def test_unknown_gitlink_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_layout_parent(tmp_path, monkeypatch, roster=(*layout.REQUIRED_ROOTS, "vendor"))

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_UNKNOWN_SUBMODULE}
    assert gate.ceiling(findings) == gate.BLOCK


@bite("shared.md:A80")
def test_two_roster_roots_sharing_one_remote_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_layout_parent(tmp_path, monkeypatch, shared_remote=("samples", "delivery"))

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_SHARED_REMOTE}
    assert gate.ceiling(findings) == gate.BLOCK


@pytest.mark.parametrize(("key", "value"), [("branch", "dev"), ("update", "checkout")])
@bite("shared.md:A75")
def test_branch_or_update_drift_is_refused(layout_root: Path, key: str, value: str) -> None:
    git(["config", "-f", ".gitmodules", f"submodule.delivery.{key}", value], cwd=layout_root)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_BRANCH_INVALID}
    assert gate.ceiling(findings) == gate.HOLD


@bite("shared.md:A72")
def test_missing_gitmodules_is_refused(layout_root: Path) -> None:
    (layout_root / ".gitmodules").unlink()

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {
        layout.PARENT_LAYOUT_GITMODULES_INVALID,
        layout.PARENT_LAYOUT_SUBMODULE_MISSING,
    }
    missing = [
        item.path for item in findings if item.code == layout.PARENT_LAYOUT_SUBMODULE_MISSING
    ]
    assert sorted(missing) == sorted(str(layout_root / name) for name in layout.REQUIRED_ROOTS)
    assert gate.ceiling(findings) == gate.HOLD


def test_duplicate_url_key_in_a_roster_section_is_malformed(layout_root: Path) -> None:
    remote = str(layout_root.parent / "remotes" / "samples.git")
    git(["config", "-f", ".gitmodules", "--add", "submodule.delivery.url", remote], cwd=layout_root)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_GITMODULES_INVALID}
    assert gate.ceiling(findings) == gate.HOLD


@pytest.mark.parametrize("prefix", ["", "file://"])
def test_dot_segment_alias_of_a_roster_remote_is_shared(layout_root: Path, prefix: str) -> None:
    remote = f"{prefix}{layout_root.parent}/remotes/./samples.git"
    git(["config", "-f", ".gitmodules", "submodule.delivery.url", remote], cwd=layout_root)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_SHARED_REMOTE}
    assert gate.ceiling(findings) == gate.BLOCK


@pytest.mark.parametrize("path", ["/samples", "samples/../delivery", "samples/nested", "samples//"])
def test_absolute_or_traversing_or_nested_registration_path_is_invalid(
    layout_root: Path, path: str
) -> None:
    git(["config", "-f", ".gitmodules", "submodule.samples.path", path], cwd=layout_root)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {
        layout.PARENT_LAYOUT_GITMODULES_INVALID,
        layout.PARENT_LAYOUT_SUBMODULE_MISSING,
    }
    assert any(path in item.message for item in findings)
    assert gate.ceiling(findings) == gate.HOLD


def test_duplicate_roster_registration_is_invalid(layout_root: Path) -> None:
    with (layout_root / ".gitmodules").open("a", encoding="utf-8") as stream:
        stream.write(
            '[submodule "duplicate"]\npath = samples\nurl = distinct.git\n'
            "branch = main\nupdate = merge\n"
        )

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_GITMODULES_INVALID}
    assert gate.ceiling(findings) == gate.HOLD


def test_section_without_url_is_malformed(layout_root: Path) -> None:
    git(["config", "-f", ".gitmodules", "--unset", "submodule.delivery.url"], cwd=layout_root)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_GITMODULES_INVALID}
    assert gate.ceiling(findings) == gate.HOLD


@bite("shared.md:A82")
def test_hardness_contract_inside_samples_is_a_boundary_leak(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_layout_parent(tmp_path, monkeypatch)
    (root / "samples" / "HARDNESS.md").touch()

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


def test_memory_directory_inside_delivery_is_a_boundary_leak(layout_root: Path) -> None:
    leak = layout_root / "delivery" / UUID / ".memory" / "hardness.yaml"
    leak.parent.mkdir(parents=True)
    leak.touch()

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


def test_bundle_bytes_inside_memory_are_a_boundary_leak(layout_root: Path) -> None:
    leak = layout_root / ".memory" / UUID / "manifest.toml"
    leak.parent.mkdir()
    leak.touch()

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


NESTED_PROJECT_REPORTS = ("AGENTS.md", "DIRECTIVE.md", "EDICT.md", "VERDICT.md")


def vendor_trinity_inside(checkout: Path) -> None:
    remote = checkout.parent.parent / "remotes" / "nested-trinity.git"
    seed = checkout.parent.parent / "nested-trinity-seed"
    git(["init", "-q", "-b", "main", str(seed)], cwd=checkout.parent.parent)
    (seed / "tools").mkdir()
    (seed / "tools" / "gate.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    commit_all(seed, "nested trinity genesis")
    git(["clone", "-q", "--bare", str(seed), str(remote)], cwd=checkout.parent.parent)
    argv = ["-c", "protocol.file.allow=always", "submodule", "add", "-b", "main", "-q"]
    git([*argv, str(remote), "trinity"], cwd=checkout)
    git(["config", "-f", ".gitmodules", "submodule.trinity.update", "merge"], cwd=checkout)


def write_nested_crucible_state(checkout: Path) -> None:
    for name in NESTED_PROJECT_REPORTS:
        (checkout / name).write_text(f"# {name}\n", encoding="utf-8")
    audit = checkout / ".audit"
    audit.mkdir()
    (audit / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (audit / "capabilities.yaml").write_text("capabilities: []\n", encoding="utf-8")


def test_harness_that_is_its_own_trinity_project_owns_its_audit(layout_root: Path) -> None:
    harness = layout_root / "harness"
    vendor_trinity_inside(harness)
    write_nested_crucible_state(harness)
    commit_all(harness, "harness runs its own crucible")

    findings = integrity.check_parent_layout(str(layout_root))

    assert layout.is_trinity_project_root(harness)
    assert codes(findings) == set()
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


def test_root_reports_alone_do_not_make_harness_a_trinity_project(layout_root: Path) -> None:
    harness = layout_root / "harness"
    write_nested_crucible_state(harness)

    findings = integrity.check_parent_layout(str(layout_root))

    assert not layout.is_trinity_project_root(harness)
    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


def test_unvendored_trinity_registration_does_not_exempt_harness(layout_root: Path) -> None:
    harness = layout_root / "harness"
    for key, value in (("path", "trinity"), ("url", "https://example.invalid/trinity.git")):
        git(["config", "-f", ".gitmodules", f"submodule.trinity.{key}", value], cwd=harness)
    (harness / "trinity").mkdir()
    write_nested_crucible_state(harness)

    findings = integrity.check_parent_layout(str(layout_root))

    assert not layout.is_trinity_project_root(harness)
    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


def test_bundle_root_vendoring_trinity_is_still_a_boundary_leak(layout_root: Path) -> None:
    samples = layout_root / "samples"
    vendor_trinity_inside(samples)
    (samples / ".memory").mkdir()
    (samples / ".memory" / "hardness.yaml").write_text("rows: []\n", encoding="utf-8")

    findings = integrity.check_parent_layout(str(layout_root))

    assert layout.is_trinity_project_root(samples)
    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


def test_solution_directory_inside_a_bundle_is_not_a_leak(layout_root: Path) -> None:
    solution = layout_root / "samples" / UUID / "solution" / "solve.sh"
    solution.parent.mkdir(parents=True)
    solution.touch()

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == set()
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


def test_trajectories_inside_a_bundle_are_not_a_leak(layout_root: Path) -> None:
    rollout = layout_root / "samples" / UUID / "trajectories" / "r1.json"
    rollout.parent.mkdir(parents=True)
    rollout.write_text("{}\n", encoding="utf-8")

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == set()
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


@bite("shared.md:A76")
def test_deliverables_at_parent_root_is_retired_not_a_leak(layout_root: Path) -> None:
    (layout_root / "deliverables" / "x").mkdir(parents=True)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_RETIRED_ROOT}
    assert layout.PARENT_LAYOUT_BOUNDARY_LEAK not in codes(findings)
    assert gate.ceiling(findings) == gate.HOLD


def test_retired_deliverables_gitlink_holds_and_is_not_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_layout_parent(
        tmp_path, monkeypatch, roster=(*layout.REQUIRED_ROOTS, "deliverables")
    )

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_RETIRED_ROOT}
    assert gate.ceiling(findings) == gate.HOLD


def test_nested_gitlink_under_a_retired_root_is_unknown(layout_root: Path) -> None:
    git(
        [
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{'b' * 40},deliverables/extra",
        ],
        cwd=layout_root,
    )
    git(
        ["-c", "commit.gpgsign=false", "commit", "-q", "-m", "nested retired gitlink"],
        cwd=layout_root,
    )

    findings = integrity.check_parent_layout(str(layout_root))

    assert layout.PARENT_LAYOUT_UNKNOWN_SUBMODULE in codes(findings)
    assert gate.ceiling(findings) == gate.BLOCK


def test_empty_deliverables_directory_is_clean(layout_root: Path) -> None:
    (layout_root / "deliverables").mkdir()

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == set()
    assert gate.ceiling(findings) == gate.SHIP_ELIGIBLE


@pytest.mark.parametrize("directory", ["samples/deliverables/x", f"samples/{UUID}/deliverables/x"])
def test_deliverables_inside_a_checkout_is_a_boundary_leak(
    layout_root: Path, directory: str
) -> None:
    (layout_root / directory).mkdir(parents=True)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


@bite("shared.md:A81")
def test_parent_tracked_bundle_bytes_are_refused(layout_root: Path) -> None:
    relative = f"samples/{UUID}/x"
    blob = layout_root / relative
    blob.parent.mkdir()
    blob.write_text("bundle bytes\n", encoding="utf-8")
    oid = git(["hash-object", "-w", relative], cwd=layout_root)
    git(["update-index", "--force-remove", "samples"], cwd=layout_root)
    git(["update-index", "--add", "--cacheinfo", f"100644,{oid},{relative}"], cwd=layout_root)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {
        layout.PARENT_LAYOUT_PARENT_TRACKS_BUNDLE,
        layout.PARENT_LAYOUT_PLAIN_DIRECTORY,
    }
    assert gate.ceiling(findings) == gate.BLOCK


@bite("shared.md:A83")
def test_symlinked_roster_root_is_refused(layout_root: Path) -> None:
    harness = layout_root / "harness"
    shutil.rmtree(harness)
    harness.symlink_to(layout_root.parent, target_is_directory=True)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_SYMLINK}
    assert gate.ceiling(findings) == gate.BLOCK


def test_symlink_inside_a_checkout_is_refused_and_never_followed(layout_root: Path) -> None:
    outside = layout_root.parent.parent
    (layout_root / "samples" / "link").symlink_to(outside, target_is_directory=True)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_SYMLINK}
    assert all(str(outside) not in finding.message for finding in findings)
    assert [finding.path for finding in findings] == [str(layout_root / "samples" / "link")]
    assert gate.ceiling(findings) == gate.BLOCK


@bite("shared.md:A78")
def test_scan_bound_is_reported_not_silently_truncated(
    layout_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for index in range(5):
        (layout_root / "samples" / f"entry-{index}").touch()
    monkeypatch.setattr(layout, "scan_forbidden", partial(layout.scan_forbidden, max_entries=3))

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_SCAN_TRUNCATED}
    assert gate.ceiling(findings) == gate.HOLD


def test_tracked_secrets_are_a_boundary_leak(layout_root: Path) -> None:
    secret = layout_root / ".secrets" / "key"
    secret.parent.mkdir()
    secret.write_text("synthetic test key\n", encoding="utf-8")
    git(["add", "-f", ".secrets/key"], cwd=layout_root)

    findings = integrity.check_parent_layout(str(layout_root))

    assert codes(findings) == {layout.PARENT_LAYOUT_BOUNDARY_LEAK}
    assert gate.ceiling(findings) == gate.BLOCK


@bite("shared.md:A77")
def test_unignored_runtime_roots_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = make_layout_parent(tmp_path, monkeypatch, gitignore=False)

    findings = integrity.check_parent_layout(str(root))

    assert codes(findings) == {layout.PARENT_LAYOUT_RUNTIME_UNIGNORED}
    assert gate.ceiling(findings) == gate.HOLD
