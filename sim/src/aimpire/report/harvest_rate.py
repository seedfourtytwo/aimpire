"""Harvest per forager-tick: how much food one forager brings in a day (observer layer, LAB1).

Why this metric: a Lab twin changes physics such as gravity, which moves
carry load (∝ 1/g) and walking speed (∝ √g) at once. Population and stores
show the end result; the yield of one forager's day shows the mechanism, the
trade-off itself, before people die or prosper from it.

Definition, over a trailing window of ``window`` ticks (a season in a twin
report, so the per-tick noise of carried remainders and trip arrivals
averages out):

    harvest_per_forager_tick = sum(HARVEST into stores) // sum(foragers out)

in milli-units (mu; 1_000 mu feeds one person for one tick) per
forager-tick, rounded down. 0 when nobody foraged in the window.

*Foragers out* in a tick: the standing ``FORAGE`` workers of the day's work
split (``work_lines``) plus the people on ``FORAGE`` trips still away
(``EN_ROUTE`` or ``RETURNING``). A trip forager counts every day on the road,
because those days are what a trip costs.

The harvest comes from the scheduler's ledger (``HARVEST`` entries on the
``stores`` material whose ref starts with the tribe's civ id), so the chart
and the ledger agree by construction. This is observer data: it never
reaches a mind.

Use: one ``HarvestRate`` per run, called exactly once per recorded tick in
tick order (it is stateful: it reads the ledger entries written since the
last call). It fits ``MetricsRecorder`` as a ``MetricFn``.
"""

from collections import deque
from typing import Final

from aimpire.sim.ledger import Ledger
from aimpire.sim.state import WorldState
from aimpire.sim.systems.tribe import HARVEST, STORES, civ_id
from aimpire.sim.systems.work import EN_ROUTE, FORAGE, RETURNING, tasks, work_lines

_AWAY: Final = frozenset({EN_ROUTE, RETURNING})


class HarvestRate:
    """Trailing-window harvest per forager-tick of one tribe, mu (module docstring)."""

    def __init__(self, ledger: Ledger, entity_id: int, window: int) -> None:
        if window < 1:
            raise ValueError(f"window must be at least 1 tick, got {window}")
        self._ledger = ledger
        self._entity_id = entity_id
        self._seen = len(ledger.entries)
        self._days: deque[tuple[int, int]] = deque(maxlen=window)

    def _harvest_since_last(self, prefix: str) -> int:
        fresh = self._ledger.entries[self._seen :]
        self._seen = len(self._ledger.entries)
        return sum(
            e.delta
            for e in fresh
            if e.material == STORES and e.kind == HARVEST and e.ref.startswith(prefix)
        )

    def __call__(self, state: WorldState) -> int:
        """Record this tick and return the window's harvest per forager-tick, mu."""
        entity = state.entities[self._entity_id]
        harvest = self._harvest_since_last(f"{civ_id(entity)}:")
        standing = sum(n for activity, _, n in work_lines(entity) if activity == FORAGE)
        trips = sum(t.qty for t in tasks(entity) if t.kind == FORAGE and t.status in _AWAY)
        self._days.append((harvest, standing + trips))
        foragers = sum(f for _, f in self._days)
        return sum(h for h, _ in self._days) // foragers if foragers else 0
