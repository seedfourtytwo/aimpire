"""A line per council while a live model plays, so a long run is visibly alive.

Why: a year with a local model takes ten minutes or more, and ``aimpire run``
used to print nothing until the end, which reads as a hang. This sink wraps
the run store, forwards every call unchanged, and echoes one line after each
council: its number, the day, the outcome and how long it took.

Wall-clock time is read here, in the experiments layer, never in ``sim/``; it
is shown to the person and never stored or hashed.
"""

import time
from collections import Counter
from collections.abc import Sequence

from aimpire.cognition.council import Settled
from aimpire.cognition.runner import CouncilSink
from aimpire.experiments.preflight import Echo
from aimpire.sim.state import WorldState


class ProgressSink:
    """Forwards to ``inner``; echoes ``council 3/12, day 20: VALID (58 s)`` after each."""

    def __init__(self, inner: CouncilSink, *, councils: int, echo: Echo) -> None:
        self._inner = inner
        self._councils = councils
        self._echo = echo
        self._since = time.monotonic()

    def record_council(self, tick: int, council: int, settled: Sequence[Settled]) -> None:
        """Persist through the inner sink, then report the council."""
        self._inner.record_council(tick, council, settled)
        now = time.monotonic()
        outcomes = Counter(str(s.record.outcome) for s in settled)
        shown = ", ".join(f"{name} {n}" if n > 1 else name for name, n in sorted(outcomes.items()))
        self._echo(
            f"council {council}/{self._councils}, day {tick}: {shown or 'none'} "
            f"({round(now - self._since)} s)"
        )
        self._since = now

    def checkpoint(self, state: WorldState, label: str) -> None:
        """Forwarded unchanged."""
        self._inner.checkpoint(state, label)
