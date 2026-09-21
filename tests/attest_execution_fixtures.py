"""Synthetic fidelity collateral shared by execution-policy regression tests."""

import copy
import hashlib
from pathlib import Path

from tools.attest.canonical import JSONValue

FIXTURES = Path(__file__).parent / "fixtures" / "attest"
FIDELITY_COLLATERAL = {
    "harnessConfig": b'{"test":"harness config"}\n',
    "effectiveConfigReconciliation": b"test reconciliation\n",
    "populationRoster": b"test precommitted roster\n",
    "observationCapture": b"test independent capture\n",
}
HARNESS_DIGEST = hashlib.sha256(FIDELITY_COLLATERAL["harnessConfig"]).hexdigest()


def with_fidelity(statement: dict[str, JSONValue]) -> dict[str, JSONValue]:
    result = copy.deepcopy(statement)
    result["predicateType"] = "trinity.execution/v2"
    predicate = result["predicate"]
    assert isinstance(predicate, dict)
    for name, content in FIDELITY_COLLATERAL.items():
        predicate[name] = {"name": name, "digest": {"sha256": hashlib.sha256(content).hexdigest()}}
    predicate["rolloutDurations"] = [
        {"rollout": rollout, "seconds": 12.5} for rollout in ("rollout-1", "rollout-2")
    ]
    predicate["rolloutTelemetry"] = [
        {
            "rollout": rollout,
            "turns": 3,
            "contextEvents": 0,
            "terminationReason": "completed",
            "providerErrorCount": 0,
        }
        for rollout in ("rollout-1", "rollout-2")
    ]
    return result


def without_fidelity(statement: dict[str, JSONValue]) -> dict[str, JSONValue]:
    result = copy.deepcopy(statement)
    result["predicateType"] = "trinity.execution/v1"
    predicate = result["predicate"]
    assert isinstance(predicate, dict)
    for name in (*FIDELITY_COLLATERAL, "rolloutTelemetry"):
        predicate.pop(name, None)
    return result
