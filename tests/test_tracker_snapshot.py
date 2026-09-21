"""Deterministic dashboard inventory against real parent-shaped evidence."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from tools import tracker, tracker_cache
from tools._findings import Severity
from tools.tracker_snapshot import as_of_instant, load_snapshot

from tests.tracker_fixtures import parent_fixture


def test_display_fields_are_sanitized_at_parse(tmp_path: Path) -> None:
    # Given markup in each free-text evidence surface.
    parent_fixture(tmp_path)
    raw = "<b>phase</b> [link](https://example.org) :smile: !`|&#*\u2603"
    expected = "bphase/b linkhttpsexample.org smile #"
    directory = next((tmp_path / ".seed/runs").iterdir())
    (directory / "progress.yaml").write_text(f"phase: {raw}\nopen_gates: [{raw}]\n")
    marker = directory / "run.json"
    payload = json.loads(marker.read_text())
    payload["principal"] = raw
    marker.write_text(json.dumps(payload))
    for relative, names in (
        (".podium/cycles.yaml", ("instrument", "disposition", "stop_reason")),
        (".trial/gates.yaml", ("contract", "phase", "artifact", "digest_file", "tier")),
    ):
        path = tmp_path / relative
        path.write_text(
            "\n".join(
                f"{line.split(':', 1)[0]}: {raw}"
                if line.strip().split(":", 1)[0] in names
                else line
                for line in path.read_text().splitlines()
            )
            + "\n"
        )
    manifest = tmp_path / ".memory/epochs/1/manifest.json"
    payload = json.loads(manifest.read_text())
    payload["published_by"] = raw
    manifest.write_text(json.dumps(payload))
    # When parsing the evidence, then every display field is already plain text.
    snapshot = load_snapshot(tmp_path)
    record = next(r for r in snapshot.runs if r.instrument == "FORGE")
    assert (record.phase, record.principal, record.open_gates) == (expected, expected, (expected,))
    assert record.disposition == "HOLD:PILOT_REQUIRED"
    cycle, gate = snapshot.cycles[0], snapshot.gates[0]
    assert (cycle.instrument, cycle.disposition, cycle.stop_reason) == (expected,) * 3
    assert (gate.contract, gate.phase, gate.artifact, gate.digest_file, gate.tier) == (
        expected,
    ) * 5
    assert snapshot.epochs[0].published_by == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  a\t b\n c  ", "a b c"),
        ("z" * 100, "z" * 80),
        ("HOLD:PILOT_REQUIRED", "HOLD:PILOT_REQUIRED"),
        (":smile: :+1: :wave:", "smile +1 wave"),
    ],
)
def test_plain_text_preserves_tokens_and_bounds_display(raw: str, expected: str) -> None:
    # Given raw display text, when sanitized, then its grammar and length are bounded.
    assert tracker_cache.plain_text(raw) == expected


@pytest.mark.parametrize(
    "source, code, severity",
    [
        ("run.json", tracker.MALFORMED, Severity.ERROR),
        ("report.md", tracker.SUPERSEDED, Severity.ADVISORY),
        ("progress.yaml", tracker.SUPERSEDED, Severity.ADVISORY),
    ],
)
def test_card_not_binding_current_bytes_is_a_finding_and_renders_unknown(
    tmp_path: Path, source: str, code: str, severity: Severity
) -> None:
    # Given a frozen run whose current source bytes have drifted.
    parent_fixture(tmp_path)
    card = next((tmp_path / ".seed/runs").glob("*/tracker.json"))
    path = card.parent / source
    path.write_bytes(path.read_bytes() + b"\n")
    # When checking and projecting that evidence.
    findings = tracker.check_tracker_cards(str(tmp_path))
    record = next(r for r in load_snapshot(tmp_path).runs if r.instrument == "FORGE")
    # Then identity drift is an error, derived drift is advisory, and neither asserts closure.
    assert [(f.code, f.severity) for f in findings] == [(code, severity)]
    assert (record.closure, record.closed_at) == ("unknown", None)


def test_as_of_is_the_newest_recorded_instant(tmp_path: Path) -> None:
    # Given a cycle whose offset puts it after the queue seal.
    parent_fixture(tmp_path)
    path = tmp_path / ".podium/cycles.yaml"
    path.write_text(path.read_text().replace("12:00:00Z", "23:00:00+02:00"))
    # When reading recorded activity, then offsets are normalized before comparison.
    assert as_of_instant(tmp_path) == "2026-09-17T21:00:00Z"


def test_as_of_is_none_for_an_empty_parent(tmp_path: Path) -> None:
    # Given no recorded activity.
    parent_fixture(tmp_path, zero_runs=True)
    # When collecting the inventory, then no clock supplies a substitute.
    assert as_of_instant(tmp_path) is None


def test_warm_and_cold_loads_are_identical(tmp_path: Path) -> None:
    # Given a populated parent and an empty disposable cache.
    fixture = parent_fixture(tmp_path / "parent")
    cache = tmp_path / "cache"
    cold = load_snapshot(fixture.root, cache=cache)
    # When loading unchanged bytes again.
    warm = load_snapshot(fixture.root, cache=cache)
    # Then counters differ but semantic output does not.
    assert warm == cold
    assert cold.parsed_runs == 3
    assert warm.parsed_runs == 0
    assert len(tuple((cache / "runs").glob("*.json"))) == 3


def test_cache_loss_rebuilds_identical_snapshot(tmp_path: Path) -> None:
    # Given a previously cached snapshot.
    fixture = parent_fixture(tmp_path / "parent")
    cache = tmp_path / "cache"
    original = load_snapshot(fixture.root, cache=cache)
    shutil.rmtree(cache)
    # When rebuilding after cache loss.
    rebuilt = load_snapshot(fixture.root, cache=cache)
    # Then all runs are parsed and the inventory is unchanged.
    assert rebuilt == original
    assert rebuilt.parsed_runs == 3


@pytest.mark.parametrize("corruption", ["{", "{}", '{"closure": "closed"}'])
def test_corrupt_cache_entry_is_discarded(tmp_path: Path, corruption: str) -> None:
    # Given one damaged cache entry.
    fixture = parent_fixture(tmp_path / "parent")
    cache = tmp_path / "cache"
    original = load_snapshot(fixture.root, cache=cache)
    next((cache / "runs").glob("*.json")).write_text(corruption)
    # When loading again.
    recovered = load_snapshot(fixture.root, cache=cache)
    # Then only that run is reparsed.
    assert recovered == original
    assert recovered.parsed_runs == 1


def test_unwritable_cache_still_loads(tmp_path: Path) -> None:
    # Given a regular file where the cache directory would be (also fails as root).
    fixture = parent_fixture(tmp_path / "parent")
    cache = tmp_path / "cache"
    cache.write_text("not a directory")
    original = load_snapshot(fixture.root)
    # When the cache cannot be written, then inventory is still complete.
    assert load_snapshot(fixture.root, cache=cache) == original


def test_boundary_falls_back_to_the_cycle_ledger(tmp_path: Path) -> None:
    # Given epoch 1 and two completed cycles in the fixture's prefixed ID format.
    parent_fixture(tmp_path)
    path = tmp_path / ".podium/cycles.yaml"
    first = path.read_text()
    path.write_text(first + first.replace("cycle-0001", "cycle-0002"))
    # When selecting a boundary, then the preceding completed cycle is used.
    assert load_snapshot(tmp_path).boundary == "cycle-1"


def test_boundary_is_unavailable_without_history(tmp_path: Path) -> None:
    # Given a first epoch and first cycle, not a previous boundary.
    parent_fixture(tmp_path)
    # When selecting a boundary, then history is explicitly unavailable.
    assert load_snapshot(tmp_path).boundary is None


def test_runs_are_sorted_chronologically_with_late_arrival(tmp_path: Path) -> None:
    # Given a run arriving after its newer peers.
    fixture = parent_fixture(tmp_path, late_run=True)
    # When collecting runs.
    snapshot = load_snapshot(tmp_path)
    # Then ordering depends on recorded start, instrument, and identity only.
    assert [run.run_id for run in snapshot.runs] == [
        run.run_id
        for run in sorted(
            fixture.runs, key=lambda run: (run.started_at, run.instrument, run.run_id)
        )
    ]


def test_closure_states_closed_open_unknown(tmp_path: Path) -> None:
    # Given one valid, one absent, and one malformed card.
    parent_fixture(tmp_path, malformed_card=True)
    next((tmp_path / ".seed/runs").glob("*/tracker.json")).unlink()
    # When collecting closure.
    snapshot = load_snapshot(tmp_path)
    # Then missing is open, malformed is unknown, and only valid is closed.
    assert [run.closure for run in snapshot.runs] == ["closed", "open", "unknown"]
    assert [run.closed_at for run in snapshot.runs] == ["2026-09-17T12:00:00Z", None, None]
    assert any("tracker.json" in item for item in snapshot.diagnostics)


def test_gate_approval_presence(tmp_path: Path) -> None:
    # Given one declared gate with approval and another without it.
    parent_fixture(tmp_path)
    path = tmp_path / ".trial/gates.yaml"
    first = path.read_text()
    path.write_text(first + first.replace("engram-phase-0.5", "pending-gate"))
    # When reading the gate projection.
    gates = load_snapshot(tmp_path).gates
    # Then declarations never imply approval.
    assert [(gate.gate, gate.approved) for gate in gates] == [
        ("engram-phase-0.5", True),
        ("pending-gate", False),
    ]


@pytest.mark.parametrize("bad", ["- cycle: nope\n", "- cycle: 2\n  samples: nope\n", "- broken\n"])
def test_malformed_cycle_row_is_a_diagnostic(tmp_path: Path, bad: str) -> None:
    # Given a malformed row beside valid history.
    parent_fixture(tmp_path)
    path = tmp_path / ".podium/cycles.yaml"
    path.write_text(path.read_text() + bad)
    # When parsing the narrow ledger.
    snapshot = load_snapshot(tmp_path)
    # Then the bad row is counted without losing the valid row.
    assert len(snapshot.cycles) == 1
    assert len(snapshot.diagnostics) == 1
    assert "cycles.yaml" in snapshot.diagnostics[0]


def test_inventory_projects_real_surfaces_without_findings(tmp_path: Path) -> None:
    # Given queue, claims, verdicts, residency, epoch, and graduated anchor evidence.
    fixture = parent_fixture(tmp_path, graduated_anchor=True)
    # When collecting the renderer's substrate.
    snapshot = load_snapshot(tmp_path)
    # Then each inventory comes from its own evidence surface.
    assert snapshot.staged == (fixture.staging_uuid,)
    assert (
        snapshot.sealed_uuids
        == snapshot.claimed_uuids
        == snapshot.audited_uuids
        == (fixture.sample_uuid,)
    )
    assert (snapshot.samples_resident, snapshot.delivery_resident) == (1, 1)
    assert snapshot.epochs[0].epoch == snapshot.current_epoch == 1
    assert snapshot.epochs[0].proposals == 0
    assert snapshot.anchor_standing == {fixture.anchor_uuid: "ANCHORED"}
    assert snapshot.as_of == "2026-09-17T15:00:00Z"
    assert all(not hasattr(run, "sections") for run in snapshot.runs)
    assert all(run.gap_count == run.gaps == 1 for run in snapshot.runs)


def test_cache_invalidates_only_changed_run(tmp_path: Path) -> None:
    # Given cached runs, one of which gets a missing closure card.
    fixture = parent_fixture(tmp_path / "parent")
    cache = tmp_path / "cache"
    load_snapshot(fixture.root, cache=cache)
    next((fixture.root / ".seed/runs").glob("*/tracker.json")).unlink()
    # When reading changed evidence.
    snapshot = load_snapshot(fixture.root, cache=cache)
    # Then unchanged peers stay cached and the new closure is visible.
    assert snapshot.parsed_runs == 1
    assert snapshot.runs[1].closure == "open"


def test_boundary_prefers_previous_published_epoch(tmp_path: Path) -> None:
    # Given a current second epoch with its preceding publication on disk.
    parent_fixture(tmp_path)
    path = tmp_path / ".memory/current.json"
    path.write_text(json.dumps({"schema": "trinity.memory-current/v1", "epoch": 2}))
    # When choosing the persisted boundary, then epoch history wins.
    assert load_snapshot(tmp_path).boundary == "epoch-1"


def test_cache_payload_corruption_cannot_change_output(tmp_path: Path) -> None:
    # Given a syntactically valid cache with a corrupted projected identity.
    fixture = parent_fixture(tmp_path / "parent")
    cache = tmp_path / "cache"
    original = load_snapshot(fixture.root, cache=cache)
    path = next((cache / "runs").glob("*.json"))
    path.write_text(path.read_text().replace("operator", "imposter"))
    # When loading the damaged cache, then it is rebuilt rather than trusted.
    recovered = load_snapshot(fixture.root, cache=cache)
    assert recovered == original
    assert recovered.parsed_runs == 1


def test_cache_entry_copied_under_another_key_is_ignored(tmp_path: Path) -> None:
    # Given two valid entries, with one copied over the other's key.
    fixture = parent_fixture(tmp_path / "parent")
    cache = tmp_path / "cache"
    cold = load_snapshot(fixture.root, cache=cache)
    first, second, *_ = sorted((cache / "runs").glob("*.json"))
    second.write_bytes(first.read_bytes())
    # When loading the poisoned cache.
    warm = load_snapshot(fixture.root, cache=cache)
    # Then only the displaced entry is reparsed and evidence wins.
    assert warm == cold
    assert warm.parsed_runs == 1


def test_cycle_requires_a_flat_list_mapping(tmp_path: Path) -> None:
    # Given valid fields without the required YAML list marker.
    parent_fixture(tmp_path)
    path = tmp_path / ".podium/cycles.yaml"
    path.write_text(path.read_text().replace("- cycle:", "  cycle:"))
    # When reading the ledger, then a mapping is not mistaken for a list.
    snapshot = load_snapshot(tmp_path)
    assert snapshot.cycles == ()
    assert len(snapshot.diagnostics) == 1


def test_git_cache_and_harness_gitlink(tmp_path: Path) -> None:
    # Given a real temporary git index with the harness gitlink, no commit needed.
    parent_fixture(tmp_path, zero_runs=True)
    revision = "a" * 40
    for args in (
        ("init", "-q"),
        ("update-index", "--add", "--cacheinfo", f"160000,{revision},harness"),
    ):
        subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            check=True,
            capture_output=True,
            env={**os.environ, "GIT_MASTER": "1"},
        )
    # When loading through the public API, then Git supplies revision and cache location.
    snapshot = load_snapshot(tmp_path)
    assert snapshot.harness_revision == revision
    assert (tmp_path / ".git/trinity/tracker-cache/v1").is_dir()


@pytest.mark.parametrize(
    "surface", [".memory", ".seed", ".audit", ".trial", ".podium", "samples", "delivery", "staging"]
)
def test_evidence_cache_destination_is_never_written(tmp_path: Path, surface: str) -> None:
    # Given an explicit cache override inside an evidence namespace.
    parent_fixture(tmp_path)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    # When loading with that override, then the evidence bytes and file inventory stay fixed.
    load_snapshot(tmp_path, cache=tmp_path / surface / "tracker-cache")
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("__bold__ ~~strike~~", "bold strike"),
        ("thumbs :+1: and :100: done", "thumbs +1 and 100 done"),
        ("HOLD:PILOT_REQUIRED stays_intact", "HOLD:PILOT_REQUIRED stays_intact"),
    ],
)
def test_plain_text_neutralizes_active_markdown(raw: str, expected: str) -> None:
    assert tracker_cache.plain_text(raw) == expected


def test_cache_key_changes_with_the_parser_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a run directory keyed by the current parser.
    parent_fixture(tmp_path)
    directory = next(tmp_path.glob(".seed/runs/*"))
    current = tracker_cache._cache_key(directory, tmp_path)
    # When an older parser version is in force.
    monkeypatch.setattr(tracker_cache, "PARSER_VERSION", tracker_cache.PARSER_VERSION - 1)
    previous = tracker_cache._cache_key(directory, tmp_path)
    # Then the two keys differ, so an entry a previous sanitizer wrote is never a hit.
    assert current is not None and previous is not None and current != previous
    assert tracker_cache.PARSER_VERSION + 1 >= 3
