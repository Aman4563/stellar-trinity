"""Every tool command a contract prints must be accepted by that tool's own argparse.

A contract sentence that names a flag the tool does not define is a broken
instruction a reader discovers only at runtime, so this reads the commands back
out of the contracts, substitutes fixture values for the angle-bracket
placeholders, and drives each named module's parser. Nothing here touches disk:
the parser is aborted the instant it accepts, before main reaches a side effect.
"""

from __future__ import annotations

import argparse
import inspect
import itertools
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Final

import pytest
from tools import (
    epochs,
    feedback,
    gate,
    harbor,
    integrity,
    migrate,
    pipeline,
    preflight,
    progress,
    release,
    render,
    runs,
    tracker,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT: Final = Path(__file__).parents[1]

# MAESTRO.md is carried beside the three contracts because item 10 of the W4 task
# list expects it to print no tool command and a silent expectation proves nothing.
CONTRACTS: Final[dict[str, str]] = {
    "ENGRAM.md": "ENGRAM",
    "FORGE.md": "FORGE",
    "CRUCIBLE.md": "CRUCIBLE",
    "MAESTRO.md": "ENGRAM",
}

# Only the ``python3 ./`` form states an invocation the contracts ask a run to type;
# a bare ``trinity/tools/<x>.py <verb>`` span names an entry point and carries no
# root, so it is doctrine rather than a vector and is not parsed here.
COMMAND: Final = re.compile(
    r"`python3 \./trinity/tools/(?P<module>[a-z_]+)\.py(?P<vector>(?: [^`]*)?)`"
)

TOOLS: Final[dict[str, ModuleType]] = {
    "epochs": epochs,
    "feedback": feedback,
    "gate": gate,
    "harbor": harbor,
    "migrate": migrate,
    "pipeline": pipeline,
    "preflight": preflight,
    "progress": progress,
    "release": release,
    "render": render,
    "tracker": tracker,
}

# Fixture values for the placeholders the contracts write. ``<run_id>`` is derived
# per instrument instead, because a run id names its own instrument first.
PLACEHOLDERS: Final[dict[str, str]] = {
    "<principal>": "ada",
    "<login>": "ada",
    "<kind>": sorted(integrity.CHAIN_KINDS)[0],
    "<key>": "./.memory/keys/feedback_checkpointer.key",
    "<id>": "r1",
    "<file>": "./.memory/ledger.yaml",
    "<path>": "./.memory/ledger.yaml",
    "<instrument>": "ENGRAM",
    "<I>": "ENGRAM",
    "<NAME>": "ada",
}
UNKNOWN_PLACEHOLDER: Final = re.compile(r"<[^>]+>")


@dataclass(frozen=True, slots=True)
class Command:
    """One backticked tool command, bound to the contract line that prints it."""

    contract: str
    line: int
    module: str
    script: str
    vector: tuple[str, ...]

    @property
    def where(self) -> str:
        return f"{self.contract}:{self.line}"

    @property
    def printed(self) -> str:
        return " ".join((self.script, *self.vector))


def _instrument(contract: str, tokens: Sequence[str]) -> str:
    """The instrument the command runs under: its own flag first, its contract next."""
    for name, following in itertools.pairwise(tokens):
        if name == "--instrument":
            return following
    return CONTRACTS[contract]


def _substitute(token: str, instrument: str) -> str:
    """One printed token as a fixture value, keeping every literal token verbatim."""
    if "|" in token and not token.startswith("-"):
        token = token.split("|", maxsplit=1)[0]
    token = token.replace("<run_id>", runs.parse_run_id(f"{instrument.casefold()}-ada-1"))
    for placeholder, value in PLACEHOLDERS.items():
        token = token.replace(placeholder, value)
    return UNKNOWN_PLACEHOLDER.sub("x", token)


def _commands() -> list[Command]:
    found: list[Command] = []
    for contract in CONTRACTS:
        text = (ROOT / contract).read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            for match in COMMAND.finditer(line):
                printed = match.group("vector").split()
                if not printed:
                    continue
                instrument = _instrument(contract, printed)
                found.append(
                    Command(
                        contract=contract,
                        line=number,
                        module=match.group("module"),
                        script=f"./trinity/tools/{match.group('module')}.py",
                        vector=tuple(_substitute(token, instrument) for token in printed),
                    )
                )
    return found


COMMANDS: Final = _commands()


class _Accepted(BaseException):
    """Argparse took the vector; abort main here so no tool ever reaches disk."""


class _Refused(BaseException):
    """Argparse rejected the vector. Raised past every ``except SystemExit`` in main."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _process_argv(module: ModuleType, command: Command) -> list[str]:
    """The list this module's own ``__main__`` block hands to ``main``.

    Most tools pass the whole process argv and slice it inside ``main``; harbor
    passes the already-sliced vector, so the script path would land on a verb.
    """
    if "main(sys.argv[1:])" in inspect.getsource(module):
        return list(command.vector)
    return [command.script, *command.vector]


def _refusal(command: Command, monkeypatch: pytest.MonkeyPatch) -> str | None:
    """The argparse refusal for this vector, or None when the parser accepted it."""
    module = TOOLS.get(command.module)
    if module is None:
        return f"tests/test_contract_commands.py registers no tools/{command.module}.py"
    accept = argparse.ArgumentParser.parse_args

    def capture(self: argparse.ArgumentParser, *args: Any, **keywords: Any) -> Any:
        accept(self, *args, **keywords)
        raise _Accepted

    def refuse(_self: argparse.ArgumentParser, message: str) -> Any:
        raise _Refused(message)

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", capture)
    monkeypatch.setattr(argparse.ArgumentParser, "error", refuse)
    try:
        module.main(_process_argv(module, command))
    except _Accepted:
        return None
    except _Refused as refused:
        return refused.message
    return f"tools/{command.module}.py built no parser for this vector"


@pytest.mark.parametrize(
    "command",
    COMMANDS,
    ids=[f"{command.where}-{command.module}" for command in COMMANDS],
)
def test_every_tool_command_in_the_contracts_parses(
    command: Command, monkeypatch: pytest.MonkeyPatch
) -> None:
    refusal = _refusal(command, monkeypatch)
    assert refusal is None, (
        f"{command.where} prints a command its tool refuses\n"
        f"  printed: {command.printed}\n"
        f"  vector:  {[command.script, *command.vector]}\n"
        f"  argparse: {command.script}: {refusal}"
    )
