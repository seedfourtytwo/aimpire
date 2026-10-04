"""Advance a world tick by tick, holding councils on cadence and checkpointing (ADR-0004, ADR-0011).

The loop, for each of ``ticks`` ticks:

1. if ``state.tick`` is a council tick (a multiple of ``every_ticks``), hold
   a council for the seats ``seats_for`` builds, hand the results to the
   sink, and checkpoint with label ``barrier`` (ADR-0007: a full snapshot
   hash at every cognition barrier);
2. step the scheduler once;
3. checkpoint with label ``periodic`` when the new tick is a multiple of
   ``checkpoint_every``.

A ``final`` checkpoint closes the run. The same loop serves recording and
recorded replay: only the providers in the seats and the gate differ, so
any difference in checkpoint hashes comes from the decisions, not the loop.

Triggered councils (ADR-0011 section 5) and fast-forward inputs arrive with
the scenario settings that need them; this loop has the fixed cadence only.
"""

from collections.abc import Callable, Sequence
from typing import Protocol

from aimpire.cognition.budget import Gate
from aimpire.cognition.council import SeatCall, Settled, hold_council
from aimpire.sim.actions import DecisionLog
from aimpire.sim.scheduler import Scheduler
from aimpire.sim.state import WorldState

SeatsFor = Callable[[WorldState, int], Sequence[SeatCall]]


class CouncilSink(Protocol):
    """Where a run's decisions and checkpoints go; the run store implements it."""

    def record_council(self, tick: int, council: int, settled: Sequence[Settled]) -> None:
        """Persist one council's results, in turn order."""
        ...

    def checkpoint(self, state: WorldState, label: str) -> None:
        """Persist the full state and its hashes."""
        ...


async def run_with_councils(  # noqa: PLR0913 (each is a separate run setting)
    state: WorldState,
    scheduler: Scheduler,
    *,
    ticks: int,
    every_ticks: int,
    checkpoint_every: int,
    seats_for: SeatsFor,
    gate: Gate,
    sink: CouncilSink,
) -> DecisionLog:
    """Run ``ticks`` ticks with a council every ``every_ticks``; return the decision log.

    Councils are numbered from 1 in the order they are held.
    """
    if ticks < 0 or every_ticks < 1 or checkpoint_every < 1:
        raise ValueError("ticks must be >= 0; every_ticks and checkpoint_every >= 1")
    log = DecisionLog()
    council = 0
    for _ in range(ticks):
        if state.tick % every_ticks == 0:
            council += 1
            calls = seats_for(state, council)
            settled = await hold_council(state, calls, gate=gate, log=log)
            sink.record_council(state.tick, council, settled)
            sink.checkpoint(state, "barrier")
        scheduler.step(state)
        if state.tick % checkpoint_every == 0:
            sink.checkpoint(state, "periodic")
    sink.checkpoint(state, "final")
    return log
