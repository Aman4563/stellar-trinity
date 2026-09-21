from collections.abc import Mapping
from typing import Final

from .bundle import Authorization
from .core import FidelityOutcome, FidelityRefusal, SignalClass, SignalFinding
from .guard import observed
from .reading import Json, boolean, integer

TIMEOUT_TOLERANCE_SECONDS: Final = 1  # Integer-second capture may round the horizon down.


def limit_findings(
    data: Mapping[str, Json], authorization: Authorization, pointer: str
) -> tuple[SignalFinding, ...]:
    """Compare observed limits with bound policy, never authorize from the trace."""
    findings: list[SignalFinding] = []
    for key, counter, approved in (
        ("max_turns", "turns", authorization.max_turns),
        ("maxTurns", "turns", authorization.max_turns),
        ("max_iterations", "iterations", authorization.max_iterations),
    ):
        cap = integer(data, key)
        if cap is None:
            continue
        count = integer(data, counter)
        if cap != approved or count is not None:
            exact = cap == approved and count is not None and count <= cap
            findings.append(observed(SignalClass.TURN_CAP, exact, pointer))
        else:
            findings.append(
                SignalFinding(
                    SignalClass.TURN_CAP,
                    FidelityOutcome.INSUFFICIENT_EVIDENCE,
                    FidelityRefusal.FIDELITY_SELF_REPORTED_ONLY,
                    pointer,
                )
            )
    timed_out = boolean(data, "timed_out")
    timeout = integer(data, "timeout_seconds")
    if timed_out:
        exact = timeout is not None and timeout == authorization.timeout_seconds
        elapsed = integer(data, "elapsed_seconds")
        if not exact:
            findings.append(observed(SignalClass.TIMEOUT, False, pointer))
        elif elapsed is not None and timeout is not None:
            findings.append(
                observed(
                    SignalClass.TIMEOUT,
                    elapsed >= timeout - TIMEOUT_TOLERANCE_SECONDS,
                    pointer,
                )
            )
    return tuple(findings)
