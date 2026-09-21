"""Deterministic private ledger bytes and an explicit, lossy public allowlist."""

import hashlib
import json
import os
import re
import secrets
from contextlib import suppress
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tools import harness_config as hc
else:
    try:
        from tools import harness_config as hc
    except ModuleNotFoundError:
        import harness_config as hc

from . import reading
from .bundle import MAX_TRACE_BYTES, Authorization
from .core import (
    TRIAL_CONFORMANCE_RULE,
    FidelityOutcome,
    FidelityRefusal,
    RolloutFidelity,
    SignalClass,
    SignalFinding,
)
from .family_config import ConfigStanding
from .family_models import GROUP_SIZE, FidelityLedger, FidelityRow, PopulationStanding
from .filesystem import directory_fd, read_regular
from .reading import Json, TraceReadError
from .registry import FIDELITY_FAMILIES

ADAPTER_VERSIONS: Final = MappingProxyType(
    dict.fromkeys(FIDELITY_FAMILIES, "trinity.fidelity-adapter/v1")
)


class FidelityLedgerPathError(ValueError):
    def __str__(self) -> str:
        return "FIDELITY_LEDGER_PATH_OUTSIDE_AUDIT"


class FidelityProjectionError(ValueError):
    def __str__(self) -> str:
        return "Fidelity projection unavailable"


class FidelityLedgerReadError(ValueError):
    def __str__(self) -> str:
        return "Fidelity ledger unavailable"


def _text(value: Json) -> str:
    if not isinstance(value, str):
        raise FidelityLedgerReadError
    return value


def _signal(value: Json, signal: SignalClass | None = None) -> SignalFinding:
    row = reading.record(value)
    refusal = row["refusal"]
    return SignalFinding(
        signal if signal is not None else SignalClass(_text(row["signal"])),
        FidelityOutcome(_text(row["outcome"])),
        FidelityRefusal(_text(refusal)) if refusal is not None else None,
        _text(row["evidencePointer"]),
    )


def parse_fidelity_ledger(raw: bytes) -> FidelityLedger:
    try:
        body = reading.document(raw)
        config_data = reading.record(body["config"])
        reason = config_data["refusal"]
        adequacy_reason = config_data["adequacyRefusal"]
        config = ConfigStanding(
            reading.boolean(config_data, "pinned") is True,
            hc.ReconcileOutcome(
                reading.boolean(config_data, "reconciled") is True,
                hc.HarnessConfigFailureReason(_text(reason)) if reason is not None else None,
                _text(config_data["detail"]),
            ),
            hc.AdequacyOutcome(
                reading.boolean(config_data, "adequate") is True,
                hc.HarnessConfigFailureReason(_text(adequacy_reason))
                if adequacy_reason is not None
                else None,
                "",
            ),
            _text(config_data["digest"]) if config_data["digest"] is not None else None,
            Authorization(),
            "",
        )
        population_data = reading.record(body["population"])
        population = PopulationStanding(
            tuple(_text(item) for item in reading.array(population_data, "extra")),
            tuple(_text(item) for item in reading.array(population_data, "missing")),
            reading.boolean(population_data, "structureValid") is True,
        )
        rows: list[FidelityRow] = []
        for value in reading.array(body, "rollouts"):
            row = reading.record(value)
            operator = row["operatorStatus"]
            rows.append(
                FidelityRow(
                    RolloutFidelity(
                        _text(row["rolloutId"]),
                        _text(row["family"]),
                        tuple(_signal(item) for item in reading.array(row, "signals")),
                    ),
                    _signal(row["handoff"], SignalClass.HANDOFF_FAILURE),
                    config,
                    population,
                    _text(operator) if operator is not None else None,
                )
            )
        count = reading.integer(body, "groupCount")
        if count is None:
            raise FidelityLedgerReadError
        groups = tuple(
            tuple(_text(item) for item in reading.array({"group": group}, "group"))
            for group in reading.array(body, "groups")
        )
        ledger = FidelityLedger(tuple(rows), config, population, count, groups)
        encoded = (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if encoded != ledger_bytes(ledger):
            raise FidelityLedgerReadError
        identities = [identity for group in groups for identity in group]
        if population.accepted and (
            len(groups) != count
            or any(len(group) != GROUP_SIZE for group in groups)
            or len(set(identities)) != len(identities)
            or set(identities) != {row.trace.rollout_id for row in rows}
        ):
            raise FidelityLedgerReadError
        project_for_pilot(ledger)
        return ledger
    except (KeyError, ValueError, TypeError, RecursionError) as error:
        raise FidelityLedgerReadError from error


def read_fidelity_ledger(audit_root: Path) -> FidelityLedger:
    try:
        raw = read_regular(
            audit_root / "fidelity.yaml",
            project_root=audit_root.parent,
            max_bytes=MAX_TRACE_BYTES,
        )
        return parse_fidelity_ledger(raw)
    except (OSError, TraceReadError) as error:
        raise FidelityLedgerReadError from error


def ledger_bytes(ledger: FidelityLedger) -> bytes:
    """JSON is a YAML subset; one canonical encoding binds file and projection."""
    rows: list[Json] = [
        {
            "rolloutId": row.trace.rollout_id,
            "family": row.trace.family,
            "overall": row.trace.overall.value,
            "trialStatus": row.trial_status,
            "selectedReason": row.selected_reason,
            "operatorStatus": row.operator_status,
            "signals": [
                {
                    "signal": finding.signal.value,
                    "outcome": finding.outcome.value,
                    "refusal": finding.refusal,
                    "evidencePointer": finding.evidence_pointer,
                }
                for finding in row.trace.findings
            ],
            "handoff": {
                "outcome": row.handoff.outcome.value,
                "refusal": row.handoff.refusal,
                "evidencePointer": row.handoff.evidence_pointer,
            },
        }
        for row in ledger.rows
    ]
    body: dict[str, Json] = {
        "trialConformanceRule": TRIAL_CONFORMANCE_RULE,
        "adapterVersions": dict(ADAPTER_VERSIONS),
        "groupCount": ledger.group_count,
        "groups": [list(group) for group in ledger.groups],
        "blocked": ledger.blocked,
        "selectedReason": ledger.selected_reason,
        "population": {
            "extra": list(ledger.population.extra),
            "missing": list(ledger.population.missing),
            "structureValid": ledger.population.structure_valid,
        },
        "config": {
            "digest": ledger.config.digest,
            "pinned": ledger.config.pinned,
            "reconciled": ledger.config.reconciliation.accepted,
            "refusal": ledger.config.reconciliation.reason,
            "detail": ledger.config.reconciliation.detail,
            "adequate": ledger.config.adequacy.accepted,
            "adequacyRefusal": ledger.config.adequacy.reason,
        },
        "rollouts": rows,
    }
    return (json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode()


def emit_fidelity_ledger(ledger: FidelityLedger, audit_root: Path, *, project_root: Path) -> Path:
    """Publish only below a real .audit root; parent callers must first pass assay.

    No scope approval is created here. The caller owns the CRUCIBLE mutation gate.
    Reject symlink components rather than trusting a lexical .audit path segment.
    """
    absolute = audit_root.absolute()
    try:
        parts = absolute.relative_to(project_root.absolute()).parts
    except ValueError as error:
        raise FidelityLedgerPathError from error
    if parts != (".audit",) and not (
        len(parts) == len((".audit", "runs", "run_id"))
        and parts[:2] == (".audit", "runs")
        and re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", parts[2])
    ):
        raise FidelityLedgerPathError
    path = absolute / "fidelity.yaml"
    if path.is_symlink():
        raise FidelityLedgerPathError
    raw = ledger_bytes(ledger)
    try:
        with directory_fd(absolute, project_root=project_root, create=True) as parent:
            temporary = f".fidelity-{secrets.token_hex(16)}.tmp"
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=parent,
            )
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(raw)
                    handle.flush()
                os.replace(temporary, "fidelity.yaml", src_dir_fd=parent, dst_dir_fd=parent)
            finally:
                with suppress(FileNotFoundError):
                    os.unlink(temporary, dir_fd=parent)
    except TraceReadError as error:
        raise FidelityLedgerPathError from error
    return path


def project_for_pilot(ledger: FidelityLedger) -> dict[str, str]:
    """Only rollout tokens plus fidelityLedgerDigest, never detector vocabulary."""
    if any(
        row.operator_status is not None and row.operator_status != row.trial_status
        for row in ledger.rows
    ):
        raise FidelityProjectionError
    result: dict[str, str] = {}
    forbidden = tuple(member.value for member in (*FidelityRefusal, *SignalClass))
    for row in ledger.rows:
        identity = row.trace.rollout_id
        if (
            re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*", identity) is None
            or identity == "fidelityLedgerDigest"
            or identity in result
            or any(token in identity for token in forbidden)
        ):
            raise FidelityProjectionError
        result[identity] = row.trial_status
    result["fidelityLedgerDigest"] = hashlib.sha256(ledger_bytes(ledger)).hexdigest()
    return result
