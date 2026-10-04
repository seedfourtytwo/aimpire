"""The council barrier: every due seat answers before anything applies (ADR-0004, ADR-0013).

Research mode needs equal cognition opportunities: a fast endpoint must never
get its orders in before a slow one, and the order in which replies arrive
must never change the world (original handoff, "barrier"; note 50 section 1).
So one council runs in three phases:

1. **Reserve**, in turn order: the budget gate grants or refuses each call
   before any is sent (``aimpire.cognition.budget``). Turn order makes the
   refusal under a tight cap deterministic.
2. **Collect**: every granted call is sent at once and the barrier waits for
   all of them. A call that times out, raises, or is refused still ends in
   exactly one outcome; no reply is ever substituted.
3. **Validate, then commit**, both in turn order: each reply goes through
   ``validate_reply`` (or ``record_failure``) into the ``DecisionLog``, then
   ``commit_decision`` writes policy and journal into the civilization.

Turn order is ``permutation(stream_key(seed, tick, ORDER), civ entity ids)``
with the registered ``turn_order`` draw site, the same per-tick shuffle the
scheduler gives sequential systems (ADR-0007, ADR-0012 section C).

Nothing here reads wall-clock time into the world. Latency is measured by
providers and only stored for audit.
"""

import asyncio
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final

from aimpire.cognition.budget import Gate, Grant, Price
from aimpire.cognition.protocol import (
    NO_USAGE,
    CognitionRequest,
    CognitionResult,
    Provider,
    Status,
)
from aimpire.sim.actions import (
    CouncilSeat,
    DecisionLog,
    DecisionRecord,
    Outcome,
    record_failure,
    validate_reply,
)
from aimpire.sim.actions.commit import commit_decision
from aimpire.sim.rng import SITES, permutation, stream_key
from aimpire.sim.state import WorldState

_TURN_STREAM, _TURN_N = SITES["turn_order"]

# Provider statuses that carry no usable reply, and the outcome each records.
_FAILURES: Final[dict[Status, Outcome]] = {
    "refusal": Outcome.REFUSAL,
    "truncated": Outcome.TRUNCATED,
    "timeout": Outcome.TIMEOUT,
    "error": Outcome.PROVIDER_ERROR,
}


def decision_id_for(civ_id: str, council: int) -> str:
    """The deterministic decision id of one civilization's council, such as ``C1-K0003``.

    It does not include the run id, so a recorded replay (a new run) asks for
    the same ids as the run it replays (ADR-0004).
    """
    if council < 0:
        raise ValueError(f"council must be >= 0, got {council}")
    return f"{civ_id}-K{council:04d}"


def council_order(run_seed: int, tick: int, entity_ids: Iterable[int]) -> list[int]:
    """The turn order of civilization entity ids at ``tick``: a fresh seeded shuffle."""
    return permutation(stream_key(run_seed, tick, _TURN_STREAM), entity_ids, _TURN_N)


@dataclass(frozen=True, slots=True)
class SeatCall:
    """One civilization's turn: its entity, the seat to validate against, the call to make.

    ``price`` turns the reported usage into the actual charge after the call.
    """

    entity_id: int
    seat: CouncilSeat
    request: CognitionRequest
    provider: Provider
    price: Price


@dataclass(frozen=True, slots=True)
class Settled:
    """What happened to one seat: the grant, the result (None if not called), the record."""

    call: SeatCall
    grant: Grant
    result: CognitionResult | None
    charged: int
    record: DecisionRecord


def _failed(status: Status, model: str) -> CognitionResult:
    return CognitionResult(
        raw_text="",
        parsed=None,
        status=status,
        usage=NO_USAGE,
        model_reported=model,
        latency_ms=0,
        attempts=1,
    )


async def _ask(call: SeatCall) -> CognitionResult:
    """Make one call under its timeout. Never raises for a provider failure."""
    request = call.request
    model = call.provider.describe().model
    try:
        async with asyncio.timeout(request.timeout_s):
            return await call.provider.complete(request)
    except TimeoutError:
        return _failed("timeout", model)
    except Exception:  # a broken adapter is a recorded PROVIDER_ERROR, not a crashed run
        return _failed("error", model)


def _decide(
    state: WorldState, seat: CouncilSeat, result: CognitionResult | None, log: DecisionLog
) -> DecisionRecord:
    """The one record for a seat. ``result`` is None when the gate refused the call."""
    version = seat.observation_version
    if result is None:
        return record_failure(state, seat.civ_id, version, Outcome.BUDGET, seat=seat, log=log)
    if result.status in _FAILURES:
        outcome = _FAILURES[result.status]
        return record_failure(state, seat.civ_id, version, outcome, seat=seat, log=log)
    if result.parsed is None:  # text that was not a JSON object at all
        return record_failure(state, seat.civ_id, version, Outcome.INVALID, seat=seat, log=log)
    return validate_reply(state, seat.civ_id, version, result.parsed, seat=seat, log=log)


def _check_calls(calls: Sequence[SeatCall]) -> None:
    entity_ids = [c.entity_id for c in calls]
    if len(set(entity_ids)) != len(entity_ids):
        raise ValueError("a civilization holds at most one seat per council")
    for call in calls:
        request = call.request
        if (request.decision_id, request.civ_id) != (call.seat.decision_id, call.seat.civ_id):
            raise ValueError(f"request and seat disagree for {call.seat.decision_id!r}")


async def hold_council(
    state: WorldState, calls: Sequence[SeatCall], *, gate: Gate, log: DecisionLog
) -> tuple[Settled, ...]:
    """Run one council for every seat in ``calls``; return what happened, in turn order."""
    _check_calls(calls)
    by_entity = {call.entity_id: call for call in calls}
    ordered = [by_entity[i] for i in council_order(state.run_seed, state.tick, by_entity)]

    grants: list[Grant] = []
    for call in ordered:
        estimate = call.provider.estimate_max_cost_micro_usd(call.request)
        grants.append(gate.reserve(call.seat.decision_id, estimate))

    granted = [call for call, grant in zip(ordered, grants, strict=True) if grant.refused is None]
    replies = await asyncio.gather(*(_ask(call) for call in granted))
    by_decision = {c.seat.decision_id: r for c, r in zip(granted, replies, strict=True)}

    out: list[Settled] = []
    for call, grant in zip(ordered, grants, strict=True):
        result = by_decision.get(call.seat.decision_id)
        charged = 0
        if result is not None:
            charged = gate.settle(grant, call.price.cost(result.usage))
        record = _decide(state, call.seat, result, log)
        out.append(Settled(call, grant, result, charged, record))
    for item in out:
        commit_decision(state, item.call.entity_id, item.record)
    return tuple(out)
