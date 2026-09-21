"""ENGRAM memory epochs: parallel proposals, one admitted publication.

Many ENGRAM runs prepare evidence at once, yet FORGE and CRUCIBLE must read one coherent
memory and one projection pair computed from it. A run therefore never edits the
authoritative files under ``.memory/`` directly. It records proposals, one per file, under
``.memory/proposals/<run>/`` against the epoch it read, and ``publish`` folds every
proposal whose base is the current epoch into an immutable snapshot under
``.memory/epochs/<n>/``, advances ``.memory/current.json``, publishes both projections
together under ``.memory/views/<n>/`` bound to the manifest digest, and rewrites the
root copies as compatibility views. Two proposals for one path conflict and are refused
for a human to reconcile; a proposal against a superseded epoch is stale and refused.

``check_epochs`` refuses a root copy that drifted from the current epoch, a tampered
epoch file, and a projection that does not carry its manifest digest, so the root files
are never an alternate authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools._findings import Finding, Severity, render_finding
else:
    try:
        from tools._findings import Finding, Severity, render_finding
    except ModuleNotFoundError:  # pragma: no cover - direct execution from tools/
        from _findings import Finding, Severity, render_finding

MEMORY_DIR: Final = Path(".memory")
EPOCHS_DIR: Final = MEMORY_DIR / "epochs"
PROPOSALS_DIR: Final = MEMORY_DIR / "proposals"
VIEWS_DIR: Final = MEMORY_DIR / "views"
CURRENT_PATH: Final = MEMORY_DIR / "current.json"
MANIFEST_SCHEMA: Final = "trinity.memory-epoch/v1"
PROPOSAL_SCHEMA: Final = "trinity.memory-proposal/v1"
CURRENT_SCHEMA: Final = "trinity.memory-current/v1"
AUTHORITATIVE: Final = (
    "ledger.yaml",
    "hardness.yaml",
    "works.yaml",
    "checkpoints.yaml",
    "forge_view.yaml",
    "crucible_view.yaml",
    "anchor_standing.yaml",
)
VIEW_FILES: Final = ("forge_view.yaml", "crucible_view.yaml", "anchor_standing.yaml")
_RUN = re.compile(r"[a-z0-9][a-z0-9.-]{7,79}\Z")
_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\.(?:yaml|json|md)\Z")


class EpochError(ValueError):
    """An epoch refusal with a closed public code."""

    code: str

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True, slots=True)
class Proposal:
    run_id: str
    seq: str
    base_epoch: int
    path: str
    sha256: str
    source: Path

    @property
    def label(self) -> str:
        return f"{self.run_id}/{self.seq}"


@dataclass(frozen=True, slots=True)
class Published:
    epoch: int
    applied: tuple[str, ...]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finding(path: Path, code: str, message: str) -> Finding:
    return Finding(code, Severity.ERROR, str(path), None, message)


def _write_json(path: Path, body: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def current(root: Path) -> int:
    """The current epoch number, 0 before the first publication."""
    value = _read_json(root / CURRENT_PATH)
    if value is None or value.get("schema") != CURRENT_SCHEMA:
        return 0
    epoch = value.get("epoch")
    return epoch if isinstance(epoch, int) and not isinstance(epoch, bool) and epoch > 0 else 0


def manifest_digest(root: Path, epoch: int) -> str:
    return _sha((root / EPOCHS_DIR / str(epoch) / "manifest.json").read_bytes())


def _validate_path(path: str) -> str:
    if _PATH.fullmatch(path) is None or "/" in path or path.startswith("."):
        raise EpochError("invalid-path", f"{path!r} is not an authoritative memory file name")
    return path


def propose(root: Path, run_id: str, path: str, data: bytes) -> Path:
    """Record one run's proposed bytes for one authoritative file against the current epoch."""
    if _RUN.fullmatch(run_id) is None:
        raise EpochError("invalid-run", f"{run_id!r} is outside the run id grammar")
    name = _validate_path(path)
    directory = root / PROPOSALS_DIR / run_id
    (directory / "files").mkdir(parents=True, exist_ok=True)
    seq = sum(1 for _ in directory.glob("*.json")) + 1
    (directory / "files" / name).write_bytes(data)
    record = directory / f"{seq:04d}.json"
    _write_json(
        record,
        {
            "schema": PROPOSAL_SCHEMA,
            "run_id": run_id,
            "seq": f"{seq:04d}",
            "base_epoch": current(root),
            "path": name,
            "sha256": _sha(data),
        },
    )
    return record


def pending_proposals(root: Path) -> list[Proposal]:
    """Every readable proposal not yet folded into an epoch, in run then sequence order."""
    directory = root / PROPOSALS_DIR
    if not directory.is_dir():
        return []
    out: list[Proposal] = []
    for run_dir in sorted(directory.iterdir()):
        if not run_dir.is_dir() or _RUN.fullmatch(run_dir.name) is None:
            continue
        for record in sorted(run_dir.glob("*.json")):
            value = _read_json(record)
            if value is None or value.get("schema") != PROPOSAL_SCHEMA:
                continue
            base = value.get("base_epoch")
            path = value.get("path")
            digest = value.get("sha256")
            if (
                not isinstance(base, int)
                or not isinstance(path, str)
                or not isinstance(digest, str)
            ):
                continue
            out.append(
                Proposal(run_dir.name, record.stem, base, path, digest, run_dir / "files" / path)
            )
    return out


def _authoritative_present(root: Path) -> list[str]:
    return [name for name in AUTHORITATIVE if (root / MEMORY_DIR / name).is_file()]


def publish(root: Path, run_id: str) -> Published:
    """Fold every current-base proposal into a new immutable epoch and advance current."""
    if _RUN.fullmatch(run_id) is None:
        raise EpochError("invalid-run", f"{run_id!r} is outside the run id grammar")
    base = current(root)
    proposals = pending_proposals(root)
    for item in proposals:
        if item.base_epoch != base:
            raise EpochError(
                "proposal-stale",
                f"{item.label} was made against epoch {item.base_epoch}; current is {base}",
            )
    by_path: dict[str, Proposal] = {}
    for item in proposals:
        held = by_path.get(item.path)
        if held is not None and held.run_id != item.run_id:
            raise EpochError(
                "proposal-conflict",
                f"{held.label} and {item.label} both change {item.path}; reconcile by hand",
            )
        by_path[item.path] = item
    files: dict[str, bytes] = {}
    if base:
        base_dir = root / EPOCHS_DIR / str(base)
        for name in AUTHORITATIVE:
            if (base_dir / name).is_file():
                files[name] = (base_dir / name).read_bytes()
    else:
        for name in _authoritative_present(root):
            files[name] = (root / MEMORY_DIR / name).read_bytes()
    for name, item in by_path.items():
        try:
            data = item.source.read_bytes()
        except OSError as exc:
            raise EpochError("proposal-unreadable", f"{item.label} bytes are missing") from exc
        if _sha(data) != item.sha256:
            raise EpochError("proposal-unreadable", f"{item.label} bytes do not match its digest")
        files[name] = data
    epoch = base + 1
    epoch_dir = root / EPOCHS_DIR / str(epoch)
    if epoch_dir.exists():
        raise EpochError("epoch-exists", f"epoch {epoch} already exists")
    epoch_dir.mkdir(parents=True)
    for name, data in files.items():
        (epoch_dir / name).write_bytes(data)
    _write_json(
        epoch_dir / "manifest.json",
        {
            "schema": MANIFEST_SCHEMA,
            "epoch": epoch,
            "parent_epoch": base,
            "published_by": run_id,
            "published_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files": {name: _sha(data) for name, data in sorted(files.items())},
            "proposals": sorted(item.label for item in by_path.values()),
        },
    )
    digest = manifest_digest(root, epoch)
    views_dir = root / VIEWS_DIR / str(epoch)
    views_dir.mkdir(parents=True)
    for name in VIEW_FILES:
        if name in files:
            (views_dir / name).write_bytes(files[name])
    _write_json(views_dir / "manifest-digest.json", {"epoch": epoch, "manifest_digest": digest})
    for name, data in files.items():
        (root / MEMORY_DIR / name).write_bytes(data)
    _write_json(
        root / CURRENT_PATH, {"schema": CURRENT_SCHEMA, "epoch": epoch, "manifest_digest": digest}
    )
    for item in by_path.values():
        run_dir = root / PROPOSALS_DIR / item.run_id
        if run_dir.is_dir():
            shutil.rmtree(run_dir)
    return Published(epoch, tuple(sorted(item.label for item in by_path.values())))


def check_epochs(root: str, _evaluation_time: datetime | None = None) -> list[Finding]:
    """The root copies equal the current epoch, the epoch is intact, and the views are bound."""
    root_path = Path(root)
    epoch = current(root_path)
    if not epoch:
        return []
    epoch_dir = root_path / EPOCHS_DIR / str(epoch)
    manifest = _read_json(epoch_dir / "manifest.json")
    out: list[Finding] = []
    if manifest is None or manifest.get("schema") != MANIFEST_SCHEMA:
        return [_finding(epoch_dir / "manifest.json", "EPOCH_TAMPERED", "manifest is unreadable")]
    recorded = _read_json(root_path / CURRENT_PATH) or {}
    if recorded.get("manifest_digest") != manifest_digest(root_path, epoch):
        out.append(
            _finding(root_path / CURRENT_PATH, "EPOCH_TAMPERED", "current.json digest drift")
        )
    files = manifest.get("files")
    if not isinstance(files, dict):
        return [_finding(epoch_dir / "manifest.json", "EPOCH_TAMPERED", "manifest lists no files")]
    for name, digest in sorted(files.items()):
        try:
            stored = (epoch_dir / name).read_bytes()
        except OSError:
            out.append(_finding(epoch_dir / name, "EPOCH_TAMPERED", f"{name} is missing"))
            continue
        if _sha(stored) != digest:
            out.append(
                _finding(epoch_dir / name, "EPOCH_TAMPERED", f"{name} differs from its manifest")
            )
            continue
        try:
            live = (root_path / MEMORY_DIR / name).read_bytes()
        except OSError:
            live = b""
        if live != stored:
            out.append(
                _finding(
                    root_path / MEMORY_DIR / name,
                    "EPOCH_DRIFT",
                    f"{name} differs from epoch {epoch}; propose and publish, never edit",
                )
            )
    views_dir = root_path / VIEWS_DIR / str(epoch)
    bound = _read_json(views_dir / "manifest-digest.json") or {}
    if bound.get("manifest_digest") != manifest_digest(root_path, epoch):
        out.append(_finding(views_dir, "EPOCH_TAMPERED", "views are not bound to the manifest"))
    for name in VIEW_FILES:
        if name not in files:
            continue
        try:
            view = (views_dir / name).read_bytes()
        except OSError:
            view = b""
        if view != (epoch_dir / name).read_bytes():
            out.append(
                _finding(views_dir / name, "EPOCH_TAMPERED", f"{name} differs from the epoch")
            )
    return out


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 tools/epochs.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pub = sub.add_parser("publish", help="fold current-base proposals into a new epoch")
    pub.add_argument("root")
    pub.add_argument("--run", required=True)
    pro = sub.add_parser("propose", help="record one file's proposed bytes for the next epoch")
    pro.add_argument("root")
    pro.add_argument("--run", required=True)
    pro.add_argument("--path", required=True)
    pro.add_argument("--from", dest="source", required=True, help="file holding the proposed bytes")
    chk = sub.add_parser("check", help="verify the current epoch, its views, and the root copies")
    chk.add_argument("root")
    return parser


def main(argv: list[str]) -> int:
    arguments = _parser().parse_args(argv[1:])
    root = Path(arguments.root)
    if not root.is_dir() or root.is_absolute():
        print("refused: root must be a relative existing directory", file=sys.stderr)
        return 2
    try:
        if arguments.command == "publish":
            done = publish(root, arguments.run)
            print(f"published epoch {done.epoch} with {len(done.applied)} proposal(s)")
            return 0
        if arguments.command == "propose":
            record = propose(
                root, arguments.run, arguments.path, Path(arguments.source).read_bytes()
            )
            print(str(record))
            return 0
        findings = check_epochs(str(root))
        for item in findings:
            print(render_finding(item))
        return 1 if findings else 0
    except (EpochError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
