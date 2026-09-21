import hashlib
import json
import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from tools import runs
from tools.attest.canonical import JSONValue, canonicalize

from tests.harness_imports import integrity

ParentSetup = Callable[[Path], None]

SPINE: list[str] = integrity.SPINE
ALL_REPORTS: list[str] = integrity.ALL_REPORTS
REPORT_SECTIONS: list[str] = integrity.REPORT_SECTIONS
REPORTS: dict[str, str] = integrity.REPORTS
PARENT_SHARED_DIRS: tuple[str, ...] = integrity.PARENT_SHARED_DIRS
PARENT_FRONT_DOOR_DIR: str = integrity.PARENT_FRONT_DOOR_DIR
README_HERO: str = integrity.README_HERO
README_SECTIONS: list[str] = integrity.README_SECTIONS
MERMAID_INIT: str = integrity.MERMAID_INIT

TRUST_VERSION: int = 7
TRUST_EXPIRES: str = "2030-01-01T00:00:00Z"
PRINCIPAL_EXPIRES: str = "2029-01-01T00:00:00Z"
FEEDBACK_ROLE: str = "feedback_checkpointer"
SIGNER_NAMESPACE: str = "trinity.attestation.v1"

CAPABILITY_DECLARED: str = "autonomous_gates"
CAPABILITY_IMPLEMENTED: str = "contamination"

APPROVAL_INPUTS: dict[str, tuple[str, str]] = {
    instrument: next(
        (str(gate.artifact), str(gate.digest))
        for gate in integrity.APPROVAL_GATES
        if str(gate.artifact).startswith(f"{harness}/")
    )
    for instrument, harness in runs.HARNESS.items()
}


def write_bundle(root: Path, uuid: str, lane_root: str = "samples") -> Path:
    bundle = root / lane_root / uuid
    (bundle / "tests").mkdir(parents=True)
    (bundle / "solution").mkdir()
    for name in integrity.BUNDLE_REQUIRED_FILES:
        (bundle / name).write_text(f"{name}\n", encoding="utf-8")
    for directory, name in integrity.BUNDLE_ENTRY_POINTS.items():
        (bundle / directory / name).write_text("#!/bin/sh\n", encoding="utf-8")
    for name in integrity.SOLUTION_GENERATED:
        content = integrity.GENERATED_BANNER if name == integrity.TRUTH_FILE else f"{name}\n"
        (bundle / "solution" / name).write_text(content, encoding="utf-8")
    if lane_root in {"samples", "delivery"}:
        (bundle / "trajectories").mkdir()
        sections = "\n\n".join(integrity.SAMPLES_SECTIONS)
        readme = f"{integrity.GENERATED_BANNER}\n\n{sections}\n\n| {uuid} |\n"
        (root / lane_root / "README.md").write_text(readme, encoding="utf-8")
    return bundle


def write_lane_registry(root: Path, entries: list[tuple[str, str]]) -> Path:
    path = root / ".seed" / "lanes.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    row_count = path.read_text(encoding="utf-8").count("  - uuid: ") if exists else 0
    with path.open("a", encoding="utf-8") as registry:
        if not exists:
            registry.write("lanes:\n")
        for slot, (uuid, task_lane) in enumerate(entries, start=row_count + 1):
            registry.write(
                f"  - uuid: {uuid}\n"
                f"    task_lane: {task_lane}\n"
                f"    slot: {slot}\n"
                "    batch: batch-0001\n"
            )
    return path


def write_clean_parent(root: Path, setup: ParentSetup) -> None:
    root.mkdir()
    for name in [*SPINE, *ALL_REPORTS]:
        (root / name).write_text("content", encoding="utf-8")
    report = "\n\n".join(f"## {name}\n\nSection content." for name in REPORT_SECTIONS)
    for name in REPORTS.values():
        (root / name).write_text(report, encoding="utf-8")
    for name in PARENT_SHARED_DIRS:
        (root / name).mkdir()
    (root / PARENT_FRONT_DOOR_DIR).mkdir()
    (root / README_HERO).parent.mkdir(parents=True, exist_ok=True)
    (root / README_HERO).write_text("hero", encoding="utf-8")
    sections = "\n\n".join(f"## {name}\n\nSection content." for name in README_SECTIONS)
    readme = (
        f"# Showcase\n\n```mermaid\n{MERMAID_INIT} theme: 'base'}}%%\n"
        f"graph TD\nA-->B\n```\n\n{sections}\n"
    )
    (root / "README.md").write_text(readme, encoding="utf-8")
    setup(root)


def git(argv: list[str], *, cwd: Path) -> str:
    environment = {
        **{key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
        "GIT_AUTHOR_NAME": "Human Operator",
        "GIT_AUTHOR_EMAIL": "human@trinity.test",
        "GIT_COMMITTER_NAME": "Human Operator",
        "GIT_COMMITTER_EMAIL": "human@trinity.test",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    completed = subprocess.run(
        ["git", *argv],
        cwd=cwd,
        capture_output=True,
        check=False,
        env=environment,
        shell=False,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return completed.stdout.strip()


def commit_all(root: Path, message: str = "commit") -> str:
    git(["add", "-A"], cwd=root)
    git(["-c", "commit.gpgsign=false", "commit", "-q", "-m", message], cwd=root)
    return git(["rev-parse", "HEAD"], cwd=root)


def write_submodule_parent(
    root: Path, setup: ParentSetup, *, roster: Sequence[str], plain: Sequence[str] = ()
) -> None:
    write_clean_parent(root, lambda _: None)
    git(["init", "-q", "-b", "main"], cwd=root)
    for name in roster:
        bare = root.parent / "remotes" / f"{name}.git"
        checkout = root / name
        if name in plain:
            checkout.mkdir(exist_ok=True)
            for key, value in (("path", name), ("url", str(bare)), ("branch", "main")):
                git(["config", "-f", ".gitmodules", f"submodule.{name}.{key}", value], cwd=root)
        else:
            if checkout.is_dir():
                checkout.rmdir()
            git(
                [
                    "-c",
                    "protocol.file.allow=always",
                    "submodule",
                    "add",
                    "-b",
                    "main",
                    "-q",
                    str(bare),
                    name,
                ],
                cwd=root,
            )
        git(["config", "-f", ".gitmodules", f"submodule.{name}.update", "merge"], cwd=root)
    setup(root)


def write_resume_parent(
    root: Path, instrument: str, run_id: str, *, principal: str = "ada", approved: bool = False
) -> Path:
    write_clean_parent(root, lambda _: None)
    run_directory = runs.open_run(root, instrument, run_id, principal=principal)
    artifact_name, digest_name = APPROVAL_INPUTS[instrument]
    artifact = root / artifact_name
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        f"instrument: {instrument}\nrun: {run_id}\nprincipal: {principal}\n", encoding="utf-8"
    )
    (artifact.parent / "capabilities.yaml").write_text(
        "capabilities:\n"
        f"  - id: {CAPABILITY_DECLARED}\n    state: declared\n"
        f"  - id: {CAPABILITY_IMPLEMENTED}\n    state: implemented\n",
        encoding="utf-8",
    )
    if approved:
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        (root / digest_name).write_text(f"{digest}\n", encoding="utf-8")
    return run_directory


def write_feedback_trust(root: Path, *, principal: str = "ada") -> Path:
    token = "".join(letter if letter.isalnum() else "-" for letter in principal.casefold())
    private_key = root.parent / f"TEST_ONLY_{token}_ed25519"
    public_key = Path(f"{private_key}.pub")
    private_key.unlink(missing_ok=True)
    public_key.unlink(missing_ok=True)
    argv = ["ssh-keygen", "-t", "ed25519", "-N", "", "-C", principal, "-q", "-f", str(private_key)]
    completed = subprocess.run(
        argv, capture_output=True, check=False, shell=False, text=True, timeout=30
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    memory = root / ".memory"
    memory.mkdir(parents=True, exist_ok=True)
    parts = public_key.read_text(encoding="utf-8").split()
    (memory / "allowed_signers").write_text(
        f'{principal} namespaces="{SIGNER_NAMESPACE}" {parts[0]} {parts[1]}\n', encoding="utf-8"
    )
    document: dict[str, JSONValue] = {
        "version": TRUST_VERSION,
        "expires": TRUST_EXPIRES,
        "roles": [{"name": FEEDBACK_ROLE, "threshold": 1}],
        "principals": [{"name": principal, "roles": [FEEDBACK_ROLE], "expires": PRINCIPAL_EXPIRES}],
        "revocations": [],
    }
    (memory / "roots.yaml").write_bytes(canonicalize(document))
    (memory / "trusted-root-version").write_text(f"{TRUST_VERSION}\n", encoding="utf-8")
    return private_key


# Field names below were captured from a real `opencode export <id> --sanitize` on
# opencode 1.1.51: the document is {"info", "messages"}, export adds only `cost` and
# `tokens` to the stored session record, and `parentID` is the session-tree edge.
def _meter_id(prefix: str, stem: str) -> str:
    return f"{prefix}_{stem:0<26}"


METER_EXPORT: Path = Path(__file__).parent / "fixtures" / "meter" / "export-sample.json"
METER_ROOT: str = _meter_id("ses", "meterroot")
METER_SESSIONS: tuple[tuple[str, str | None], ...] = (
    (METER_ROOT, None),
    (_meter_id("ses", "meterlanea"), METER_ROOT),
    (_meter_id("ses", "meterlaneb"), METER_ROOT),
)
METER_TURNS: int = 2
METER_VERSION: str = "1.1.51"
METER_MODEL: str = "big-pickle"
METER_EPOCH_MS: int = 1770290999000


def _meter_counts(index: int, turn: int) -> tuple[int, int, int, int]:
    scale, step = index + 1, turn + 1
    return (1000 * scale * step, 100 * scale * step, scale + turn, 20000 * scale * step)


def _meter_tokens(counts: Sequence[int]) -> JSONValue:
    cache: JSONValue = {"read": counts[3], "write": 0}
    return {"input": counts[0], "output": counts[1], "reasoning": counts[2], "cache": cache}


def _meter_message(body: dict[str, JSONValue], session_id: str) -> JSONValue:
    part = f"prt{str(body['id']).removeprefix('msg')}"
    text: JSONValue = {
        "id": part,
        "sessionID": session_id,
        "messageID": body["id"],
        "type": "text",
        "text": f"[redacted:text:{part}]",
    }
    return {"info": {**body, "sessionID": session_id}, "parts": [text]}


def _meter_messages(session_id: str, index: int) -> list[JSONValue]:
    created = METER_EPOCH_MS + index * 60_000
    prompt = _meter_id("msg", f"meterprompt{index}")
    bodies: list[dict[str, JSONValue]] = [
        {"id": prompt, "role": "user", "time": {"created": created + 1}}
    ]
    bodies += [
        {
            "id": _meter_id("msg", f"meterreply{index}{turn}"),
            "parentID": prompt,
            "role": "assistant",
            "modelID": METER_MODEL,
            "providerID": "opencode",
            "cost": 0,
            "tokens": _meter_tokens(_meter_counts(index, turn)),
            "finish": "stop",
            "time": {"created": created + 2 + turn, "completed": created + 8 + turn},
        }
        for turn in range(METER_TURNS)
    ]
    return [_meter_message(body, session_id) for body in bodies]


def _meter_document(session_id: str, parent_id: str | None, index: int) -> JSONValue:
    created = METER_EPOCH_MS + index * 60_000
    turns = [_meter_counts(index, turn) for turn in range(METER_TURNS)]
    info: dict[str, JSONValue] = {
        "id": session_id,
        "projectID": "global",
        "version": METER_VERSION,
        "cost": 0,
        "directory": f"[redacted:session-directory:{session_id}]",
        "title": f"[redacted:session-title:{session_id}]",
        "tokens": _meter_tokens([sum(values) for values in zip(*turns, strict=True)]),
        "time": {"created": created, "updated": created + 30_000},
    }
    if parent_id is not None:
        info["parentID"] = parent_id
    return {"info": info, "messages": _meter_messages(session_id, index)}


def write_meter_export(root: Path, *, sessions: Sequence[tuple[str, str | None]]) -> Path:
    documents = [
        _meter_document(session_id, parent_id, index)
        for index, (session_id, parent_id) in enumerate(sessions)
    ]
    path = root / "opencode-export.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(documents, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
