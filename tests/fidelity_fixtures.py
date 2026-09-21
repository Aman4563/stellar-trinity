from pathlib import Path
from typing import Final

from tools.forensics import Authorization, TraceBundle
from tools.forensics.reading import TraceReadError, array, boolean, child, document, integer, text

FIDELITY_ROOT: Final = Path(__file__).parent / "fixtures" / "fidelity"


def load_fixture(relative: str | Path) -> TraceBundle:
    """Load any fixture subtree, including adversarial, without interpreting trace bytes.

    bundle.json has required family, harness_version, accompaniment and authorization;
    optional rollout_id defaults to synthetic-rollout. All other files retain their
    relative paths and exact bytes. Authorization accepts the TraceBundle policy fields.
    """
    directory = (FIDELITY_ROOT / relative).resolve()
    if not directory.is_relative_to(FIDELITY_ROOT.resolve()):
        raise TraceReadError
    descriptor = document((directory / "bundle.json").read_bytes())
    required = {"family", "harness_version", "accompaniment", "authorization"}
    if not required <= descriptor.keys() or descriptor.keys() - required - {"rollout_id"}:
        raise TraceReadError
    family = text(descriptor, "family")
    version = text(descriptor, "harness_version")
    if not family or not version:
        raise TraceReadError
    companions: set[str] = set()
    for value in array(descriptor, "accompaniment"):
        if not isinstance(value, str) or not value or value in companions:
            raise TraceReadError
        companions.add(value)
    policy = child(descriptor, "authorization")
    if policy.keys() - {
        "compaction",
        "max_message_chars",
        "max_turns",
        "max_iterations",
        "context_window_tokens",
        "timeout_seconds",
    }:
        raise TraceReadError
    authorization = Authorization(
        compaction=boolean(policy, "compaction") is True,
        max_message_chars=integer(policy, "max_message_chars"),
        max_turns=integer(policy, "max_turns"),
        max_iterations=integer(policy, "max_iterations"),
        context_window_tokens=integer(policy, "context_window_tokens"),
        timeout_seconds=integer(policy, "timeout_seconds"),
    )
    files: dict[str, bytes] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise TraceReadError
        if path.is_file() and path != directory / "bundle.json":
            files[path.relative_to(directory).as_posix()] = path.read_bytes()
    return TraceBundle(
        family=family,
        harness_version=version,
        files=files,
        accompaniment=frozenset(companions),
        authorization=authorization,
        rollout_id=text(descriptor, "rollout_id") or "synthetic-rollout",
    )


def load_adversarial_fixture(name: str) -> TraceBundle:
    """Load one adversarial case through the shared byte-preserving boundary."""
    if not name or Path(name).name != name or name in {".", ".."}:
        raise TraceReadError
    return load_fixture(Path("adversarial") / name)
