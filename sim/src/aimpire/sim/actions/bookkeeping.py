"""What a committed decision leaves in the civ entity besides policy and journal (M0b).

``commit_decision`` calls ``apply_bookkeeping`` once per record, at the
council tick, after the observation for this council was built. So what it
writes is what the *next* observation shows:

* ``tasks``: finished tasks (shown once already) are pruned; each accepted
  order becomes a task ``[task_id, kind, place, qty, "ORDERED"]``. The M0
  systems start it in this same tick (``aimpire.sim.systems.work``). A
  ``MOVE_CAMP`` with ``qty`` 0 ("not used") takes everyone, so its qty is the
  head count.
* ``last_results``: one row per order of the reply, by index:
  ``[index, kind, place, "ACCEPTED", ""]`` for an accepted order and
  ``[index, "", "", "REJECTED", reason]`` for a rejected one. The record
  keeps no copy of a rejected order, so its kind and place are empty; the
  reason code is what the mind needs, and an order naming an unseen place
  reads exactly like one naming a place that does not exist (no leak).
* ``commitments``: those resolved at an earlier council (shown once) are
  pruned; those due at or before this council are resolved now; accepted new
  ones are added as ``PENDING``. ``STOCK_AT_LEAST qty`` is met when the stores
  hold at least ``qty`` whole food units; with a place, when the tribe's own
  last-seen snapshot of that place does (never live truth, which the tribe
  could not know). ``BE_AT place`` is met when the camp is there.
* ``names``: accepted names go into the civ's own ``names`` map.
* ``last_council``: ``{council, tick, population, stores}`` now, the baseline
  for the "change since the last council" figures of the next observation.

Messages and beliefs need no state in M0 (delivery and belief records come
with M2 and M3).
"""

import re
from typing import Final, cast

from aimpire.sim.actions.decision import AcceptedCommitment, DecisionRecord
from aimpire.sim.state import Entity, Value
from aimpire.sim.systems.tribe import FOOD, population, sub_dict, sub_list
from aimpire.sim.systems.work import (
    MOVE_CAMP,
    ORDERED,
    Task,
    add_task,
    prune_finished,
    task_id_for,
)

MILLI: Final = 1000
"""Milli-units per whole unit: commitment quantities are whole food units."""
MET: Final = "MET"
PENDING: Final = "PENDING"
MISSED: Final = "MISSED"
_ORDER_FIELD: Final = re.compile(r"orders\[(\d+)\]")


def _tasks(entity: Entity, record: DecisionRecord) -> None:
    prune_finished(entity)
    for order in record.orders:
        qty = population(entity) if order.kind == MOVE_CAMP else order.qty
        task_id = task_id_for(record.decision_id, order.index)
        add_task(entity, Task(task_id, order.kind, order.place, qty, ORDERED))


def _results(entity: Entity, record: DecisionRecord) -> None:
    rows: list[tuple[int, list[Value]]] = [
        (o.index, [o.index, o.kind, o.place, "ACCEPTED", ""]) for o in record.orders
    ]
    for rejection in record.rejections:
        match = _ORDER_FIELD.fullmatch(rejection.field)
        if match is not None:
            index = int(match.group(1))
            rows.append((index, [index, "", "", "REJECTED", rejection.reason.value]))
    entity["last_results"] = [row for _, row in sorted(rows, key=lambda r: r[0])]


def _food_seen(entity: Entity, place: str) -> int:
    seen = sub_dict(entity, "known").get(place)
    if not isinstance(seen, dict):
        return 0
    snapshot = seen.get("seen")
    food = snapshot.get(FOOD, 0) if isinstance(snapshot, dict) else 0
    return food if type(food) is int else 0


def _met(entity: Entity, kind: str, place: str, qty: int) -> bool:
    if kind == "BE_AT":
        return entity.get("camp") == place
    if place:
        return _food_seen(entity, place) >= qty * MILLI
    stores = sub_dict(entity, "stores").get(FOOD, 0)
    return type(stores) is int and stores >= qty * MILLI


def _commitments(entity: Entity, council: int, new: tuple[AcceptedCommitment, ...]) -> None:
    rows = cast(list[list[Value]], sub_list(entity, "commitments"))
    kept: list[Value] = []
    for kind, place, qty, by_council, status in rows:
        if status != PENDING:
            continue  # resolved earlier and already shown
        now = status
        if cast(int, by_council) <= council:
            met = _met(entity, cast(str, kind), cast(str, place), cast(int, qty))
            now = MET if met else MISSED
        kept.append([kind, place, qty, by_council, now])
    kept.extend([c.kind, c.place, c.qty, c.by_council, PENDING] for c in new)
    entity["commitments"] = kept


def _snapshot(entity: Entity, council: int, tick: int) -> None:
    stores = sub_dict(entity, "stores")
    entity["last_council"] = {
        "council": council,
        "tick": tick,
        "population": population(entity),
        "stores": dict(stores),
    }


def apply_bookkeeping(entity: Entity, record: DecisionRecord, tick: int) -> None:
    """Write tasks, results, commitments, names and the council snapshot (module docstring)."""
    _tasks(entity, record)
    _results(entity, record)
    _commitments(entity, record.council, record.commitments)
    names = sub_dict(entity, "names")
    for name in record.names:
        names[name.id] = name.name
    _snapshot(entity, record.council, tick)
