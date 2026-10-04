"""Observer measures of each seat's group at checkpoints, and the world metrics drawn from them.

Why: an experiment on M0 is scored on what happened to the people (did the
mind keep them fed?), not only on whether its replies parsed. These measures
are the observer layer (ADR-0019 section 3): they read world truth, such as
the real food near a camp, to describe a run afterwards. Nothing here reaches
a mind or flows back into a run.

A world opts in by registering a measure factory (``register_measures``);
``m0`` does so in ``experiments/__init__``. For each seat the factory gives
named integer functions of the state, read at tick 0, at every multiple of
the checkpoint interval, and at the last tick:

    population      people alive;
    deaths          people lost since tick 0 (M0 has no births);
    stores_mu       food in the group's stores, milli-units (mu);
    near_camp_mu    wild food on the camp's place and its neighbours, mu.

The run metrics an experiment may pre-register (``WORLD_METRICS``) come from
the first and last checkpoints, summed over the seats one mind holds:

    survival_ppm        people alive at the end, in ppm of those at the start;
    final_population    people alive at the end;
    deaths              people lost over the run;
    final_stores_mu     food in store at the end, mu;
    final_near_camp_mu  wild food near the camp at the end, mu.

Everything is an integer and stored as JSON beside the run (``measures.json``).
"""

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from aimpire.experiments.stats import PPM
from aimpire.experiments.worlds import World
from aimpire.report.metrics import MetricFn
from aimpire.sim.state import WorldState

MEASURES_FILE: Final = "measures.json"
MEASURE_NAMES: Final = ("population", "deaths", "stores_mu", "near_camp_mu")
WORLD_METRICS: Final = (
    "survival_ppm",
    "final_population",
    "deaths",
    "final_stores_mu",
    "final_near_camp_mu",
)

MeasureFactory = Callable[[WorldState, int], Mapping[str, MetricFn]]
"""``factory(state at tick 0, entity_id)``: the measures of one seat, by ``MEASURE_NAMES``."""

_FACTORIES: dict[str, MeasureFactory] = {}


def register_measures(world: str, factory: MeasureFactory) -> None:
    """Let runs in ``world`` record measures; once per world name."""
    if world in _FACTORIES:
        raise ValueError(f"measures for {world!r} are already registered")
    _FACTORIES[world] = factory


def has_measures(world: str) -> bool:
    """Whether runs in ``world`` record measures (and may name ``WORLD_METRICS``)."""
    return world in _FACTORIES


class CheckpointMeasures:
    """The runner's per-tick hook: every seat's measures at tick 0, each ``every`` ticks, the end.

    ``data()`` is columnar: ``{"checkpoints": [ticks], "civs": {civ: {name: [values]}}}``.
    """

    def __init__(self, world_name: str, world: World, every: int) -> None:
        if every < 1:
            raise ValueError("every must be at least 1")
        factory = _FACTORIES[world_name]
        self.every = every
        self._fns = {civ: factory(world.state, eid) for civ, eid in world.civs}
        self.ticks: list[int] = []
        self._values: dict[str, dict[str, list[int]]] = {
            civ: {name: [] for name in MEASURE_NAMES} for civ in self._fns
        }
        self._take(world.state)

    def _take(self, state: WorldState) -> None:
        self.ticks.append(state.tick)
        for civ, fns in self._fns.items():
            for name in MEASURE_NAMES:
                self._values[civ][name].append(int(fns[name](state)))

    def __call__(self, state: WorldState) -> None:
        if state.tick % self.every == 0:
            self._take(state)

    def close(self, state: WorldState) -> None:
        """Take the last tick if it was not a checkpoint."""
        if self.ticks[-1] != state.tick:
            self._take(state)

    def data(self) -> dict[str, Any]:
        """The recorded measures as plain JSON-ready data."""
        return {"checkpoints": list(self.ticks), "civs": self._values}


def write_measures(data: Mapping[str, Any], run_dir: Path) -> None:
    """Write ``measures.json`` into a run's folder (sorted keys, so byte-stable)."""
    text = json.dumps(data, indent=1, sort_keys=True) + "\n"
    (run_dir / MEASURES_FILE).write_text(text, encoding="utf-8")


def read_measures(run_dir: Path) -> dict[str, Any] | None:
    """A run's measures, or ``None`` if its world records none."""
    path = run_dir / MEASURES_FILE
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def series(data: Mapping[str, Any], civs: Sequence[str]) -> dict[str, list[int]]:
    """Each measure at every checkpoint, summed over ``civs`` (the seats one mind holds)."""
    count = len(data["checkpoints"])
    return {
        name: [sum(data["civs"][civ][name][i] for civ in civs) for i in range(count)]
        for name in MEASURE_NAMES
    }


def world_metrics(data: Mapping[str, Any], civs: Sequence[str]) -> dict[str, int]:
    """The ``WORLD_METRICS`` of the seats ``civs`` (module docstring)."""
    s = series(data, civs)
    start, end = s["population"][0], s["population"][-1]
    return {
        "survival_ppm": end * PPM // start if start else 0,
        "final_population": end,
        "deaths": s["deaths"][-1],
        "final_stores_mu": s["stores_mu"][-1],
        "final_near_camp_mu": s["near_camp_mu"][-1],
    }
