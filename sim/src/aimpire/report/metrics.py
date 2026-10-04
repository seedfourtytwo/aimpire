"""Per-tick metric table for a run, written as deterministic CSV (F4a).

Why: every experiment compares runs by a few integer time series (food on
land, people alive, ...). A metric is any function ``WorldState -> int``,
usually an F3 ledger ``Measure`` so the chart and the ledger agree by
construction. Values are milli-units or plain counts, never floats, so the CSV
is byte-identical for identical runs.

Use: call ``record(state)`` once per tick, after ``Scheduler.step``.
"""

from collections.abc import Callable, Mapping
from pathlib import Path

from aimpire.sim.state import WorldState

MetricFn = Callable[[WorldState], int]
_TICK = "tick"
_FORBIDDEN_IN_NAME = frozenset(',"\r\n')


def _check_name(name: str) -> None:
    if not name or name == _TICK or any(c in _FORBIDDEN_IN_NAME for c in name):
        raise ValueError(f'metric name must be non-empty, not {_TICK!r}, without , " or newlines')


class MetricsRecorder:
    """An in-memory table: one row per recorded tick, one int column per metric.

    Column order is the order of ``measures``, so the CSV layout is fixed by
    the caller and never by hashing or set order.
    """

    def __init__(self, measures: Mapping[str, MetricFn]) -> None:
        for name in measures:
            _check_name(name)
        self._measures: tuple[tuple[str, MetricFn], ...] = tuple(measures.items())
        self.rows: list[tuple[int, ...]] = []

    @property
    def columns(self) -> tuple[str, ...]:
        """``("tick", <metric names in order>)``."""
        return (_TICK, *(name for name, _ in self._measures))

    @property
    def names(self) -> tuple[str, ...]:
        """Metric names without the tick column."""
        return self.columns[1:]

    def record(self, state: WorldState) -> tuple[int, ...]:
        """Measure ``state`` and append a row. Ticks must strictly increase."""
        if self.rows and state.tick <= self.rows[-1][0]:
            raise ValueError(f"tick {state.tick} is not after the last recorded tick")
        row = [state.tick]
        for name, measure in self._measures:
            value = measure(state)
            if type(value) is not int:  # rejects float, bool and numpy scalars alike
                raise TypeError(f"metric {name!r} returned {type(value).__name__}, expected int")
            row.append(value)
        self.rows.append(tuple(row))
        return self.rows[-1]

    def ticks(self) -> list[int]:
        """The recorded ticks, in order."""
        return [row[0] for row in self.rows]

    def series(self, name: str) -> list[int]:
        """All recorded values of one metric, in tick order."""
        index = self.columns.index(name)
        return [row[index] for row in self.rows]

    def to_csv(self) -> str:
        """Header plus one line per row, ``\\n`` line endings, no quoting needed."""
        lines = [",".join(self.columns), *(",".join(map(str, row)) for row in self.rows)]
        return "\n".join(lines) + "\n"

    def write_csv(self, path: Path) -> None:
        """Write ``to_csv()`` as ASCII bytes (no platform newline translation)."""
        Path(path).write_bytes(self.to_csv().encode("ascii"))
