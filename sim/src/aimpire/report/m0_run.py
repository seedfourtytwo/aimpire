"""What ``aimpire run m0`` measures, draws and prints about one tribe (backlog M0c).

This is the observer layer (ADR-0019 section 3): it reads world truth, such
as the real food near the camp, to describe a finished run to a person. Nothing
here reaches a mind or flows back into the run.

* ``m0_measures``: the per-tick metrics, all integers. Food is in milli-units
  (mu; 1_000 mu feeds one person for one tick), people are counts.
    ``population``      people alive;
    ``deaths``          people lost since tick 0 (M0 has no births);
    ``stores_mu``       food in the tribe's stores;
    ``near_camp_mu``    wild food on the camp's place and its neighbours, the
                        places a tribe that stays put lives from;
    ``wild_food_mu``    wild food on the whole map.
* ``camp_dot``: the replay draws the tribe as one dot at its camp's centroid.
* ``summary_lines``: the short table printed when a run ends, one row a year.
"""

from collections.abc import Mapping, Sequence
from typing import Final

from aimpire.report.metrics import MetricFn, MetricsRecorder
from aimpire.sim.ledger import layer_total
from aimpire.sim.places import places_by_id
from aimpire.sim.state import Entity, WorldState
from aimpire.sim.systems.survey import place_food
from aimpire.sim.systems.tribe import camp, population, stores_food
from aimpire.sim.world.m0 import FOOD

MILLI: Final = 1000
CIV_KIND: Final = "civ"


def _civ(state: WorldState, entity_id: int) -> Entity:
    return state.entities[entity_id]


def near_camp_mu(state: WorldState, entity: Entity) -> int:
    """True wild food on the camp's place and its neighbours, mu (observer data)."""
    places = places_by_id(state)
    here = places[camp(entity)]
    return sum(place_food(state, places[pid]) for pid in (here.place_id, *here.neighbours))


def m0_measures(entity_id: int, start_people: int) -> dict[str, MetricFn]:
    """The metrics of the tribe stored as entity ``entity_id`` (module docstring)."""
    return {
        "population": lambda s: population(_civ(s, entity_id)),
        "deaths": lambda s: start_people - population(_civ(s, entity_id)),
        "stores_mu": lambda s: stores_food(_civ(s, entity_id)),
        "near_camp_mu": lambda s: near_camp_mu(s, _civ(s, entity_id)),
        "wild_food_mu": layer_total(FOOD),
    }


def camp_dot(state: WorldState, entity: Entity) -> tuple[int, int] | None:
    """A tribe's dot: its camp's centroid. Other entities are not drawn."""
    if entity.get("kind") != CIV_KIND or population(entity) == 0:
        return None
    return places_by_id(state, with_tiles=False)[camp(entity)].centroid


def _row_at(metrics: MetricsRecorder, tick: int) -> dict[str, int]:
    """The last recorded row at or before ``tick``."""
    rows = [row for row in metrics.rows if row[0] <= tick]
    return dict(zip(metrics.columns, rows[-1], strict=True))


def summary_lines(
    metrics: MetricsRecorder,
    ticks_per_year: int,
    outcomes: Mapping[str, int],
    footer: Sequence[str] = (),
) -> list[str]:
    """The end-of-run table: one row per year boundary, then councils and outcomes."""
    last = metrics.ticks()[-1]
    marks = sorted({*range(0, last + 1, ticks_per_year), last})
    lines = [f"{'tick':>6} {'year':>5} {'people':>6} {'deaths':>6} {'stores':>7} {'near camp':>9}"]
    for tick in marks:
        row = _row_at(metrics, tick)
        lines.append(
            f"{tick:>6} {tick // ticks_per_year:>5} {row['population']:>6} {row['deaths']:>6} "
            f"{row['stores_mu'] // MILLI:>7} {row['near_camp_mu'] // MILLI:>9}"
        )
    lines.append("stores and near camp are in food units (one feeds a person for a tick)")
    councils = sum(outcomes.values())
    shown = ", ".join(f"{name} {count}" for name, count in sorted(outcomes.items()) if count)
    lines.append(f"councils {councils}: {shown or 'none'}")
    if councils and outcomes.get("PROVIDER_ERROR", 0) == councils:
        lines.append(
            "WARNING: every council failed with PROVIDER_ERROR, so no mind steered this run. "
            "This is the provider, not the model: see the notebook for the error text."
        )
    return [*lines, *footer]
