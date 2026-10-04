"""Tasks from orders, and the split of free workers by the standing policy (M0b, ADR-0013).

Two kinds of work, as ADR-0013 separates them:

* **Standing policy.** ``[[activity, place, share‰]]`` stays in force until
  replaced. Each tick the free workers are split by the shares
  (``apportion``) and work at their place; the split is stored in the civ's
  ``work`` field by the camp system and read by forage and scout.
* **Orders** become **tasks**, rows ``[task_id, kind, place, qty, status]``
  in the civ's ``tasks`` list (the ``civ_record`` layout). ``task_id`` is
  ``"<decision_id>-O<index>"``, so it needs no counter and is stable under
  replay.

Task life cycle (statuses are engine words shown to the mind verbatim):

    trip (FORAGE, SCOUT):  ORDERED -> EN_ROUTE -> RETURNING -> DONE, or FAILED
    MOVE_CAMP:             ORDERED -> EN_ROUTE -> DONE

A trip started at tick ``s`` to a place ``T`` walking ticks from camp
arrives at ``s + T`` (its work is done then: a harvest or a look around) and
is back at ``s + max(1, 2T)``, so even a trip on the camp's own place takes
a tick. Its people are away, and not free for the policy, from the moment
it is ordered until it is ``DONE``. A trip starts with at most the people
then free; with none free it is ``FAILED``.

A move takes everyone. It starts only when no trip is ordered or out (the
tribe waits for its people), and no trip starts while the tribe is moving.
While moving, nobody works for the policy. Finished (``DONE``, ``FAILED``)
tasks stay visible for one council and are pruned when the next decision is
committed.
"""

from dataclasses import dataclass
from typing import Final, cast

from aimpire.sim.state import Entity, Value
from aimpire.sim.systems.tribe import sub_dict, sub_list

FORAGE: Final = "FORAGE"
SCOUT: Final = "SCOUT"
MOVE_CAMP: Final = "MOVE_CAMP"
TRIP_KINDS: Final = frozenset({FORAGE, SCOUT})

ORDERED: Final = "ORDERED"
EN_ROUTE: Final = "EN_ROUTE"
RETURNING: Final = "RETURNING"
DONE: Final = "DONE"
FAILED: Final = "FAILED"
FINISHED: Final = frozenset({DONE, FAILED})
_AWAY: Final = frozenset({ORDERED, EN_ROUTE, RETURNING})

PERMILLE: Final = 1000


@dataclass(frozen=True, slots=True)
class Task:
    """One row of the civ's ``tasks`` list."""

    task_id: str
    kind: str
    place: str
    qty: int
    status: str


@dataclass(frozen=True, slots=True)
class TripTimes:
    """Ticks of a started task: left camp, reached the place, back (or arrived, for a move)."""

    start: int
    arrive: int
    done: int


def task_id_for(decision_id: str, index: int) -> str:
    """The id of the task made from order ``index`` of a decision."""
    return f"{decision_id}-O{index}"


def tasks(entity: Entity) -> list[Task]:
    """Every task row, in stored (order) sequence."""
    rows = cast(list[list[Value]], sub_list(entity, "tasks"))
    return [
        Task(cast(str, i), cast(str, k), cast(str, p), cast(int, q), cast(str, s))
        for i, k, p, q, s in rows
    ]


def set_task(entity: Entity, task_id: str, status: str, qty: int | None = None) -> None:
    """Change one task's status, and its head count if given."""
    for row in cast(list[list[Value]], sub_list(entity, "tasks")):
        if row[0] == task_id:
            row[4] = status
            if qty is not None:
                row[3] = qty
            return
    raise KeyError(f"no task {task_id!r}")


def add_task(entity: Entity, task: Task) -> None:
    """Append a task row."""
    sub_list(entity, "tasks").append([task.task_id, task.kind, task.place, task.qty, task.status])


def prune_finished(entity: Entity) -> None:
    """Drop finished tasks and their times (they were shown at one council)."""
    rows = cast(list[list[Value]], sub_list(entity, "tasks"))
    keep = [row for row in rows if row[4] not in FINISHED]
    entity["tasks"] = cast(list[Value], keep)
    times = sub_dict(entity, "task_times")
    open_ids = {cast(str, row[0]) for row in keep}
    for task_id in sorted(set(times) - open_ids):
        del times[task_id]


def trip_times(start: int, walk: int) -> TripTimes:
    """Times of a trip that leaves at ``start`` for a place ``walk`` ticks away."""
    return TripTimes(start, start + walk, start + max(1, 2 * walk))


def times_of(entity: Entity, task_id: str) -> TripTimes:
    """The stored times of a started task."""
    row = cast(list[int], sub_dict(entity, "task_times")[task_id])
    return TripTimes(row[0], row[1], row[2])


def set_times(entity: Entity, task_id: str, times: TripTimes) -> None:
    """Store the times of a task when it starts."""
    sub_dict(entity, "task_times")[task_id] = [times.start, times.arrive, times.done]


def people_away(entity: Entity) -> int:
    """People reserved by trips that are ordered or out."""
    return sum(t.qty for t in tasks(entity) if t.kind in TRIP_KINDS and t.status in _AWAY)


def is_moving(entity: Entity) -> bool:
    """True while a camp move is under way."""
    return any(t.kind == MOVE_CAMP and t.status == EN_ROUTE for t in tasks(entity))


def apportion(workers: int, lines: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Split ``workers`` by permille ``shares``; return ``(activity, place, n)`` sorted by line.

    Largest remainder: each line gets ``floor(workers * share / 1000)``; the
    ``floor(workers * sum(shares) / 1000)`` minus those floors left over go one
    each to the largest remainders, ties to the smaller ``(activity, place)``.
    Shares summing to less than 1000 leave the rest of the workers idle.
    """
    if workers < 0:
        raise ValueError(f"workers must be >= 0, got {workers}")
    ordered = sorted(lines)
    if sum(share for _, _, share in ordered) > PERMILLE:
        raise ValueError("policy shares sum to more than 1000 permille")
    split = [divmod(workers * share, PERMILLE) for _, _, share in ordered]
    total, _ = divmod(workers * sum(share for _, _, share in ordered), PERMILLE)
    extra = total - sum(n for n, _ in split)
    rank = sorted(range(len(ordered)), key=lambda i: (-split[i][1], ordered[i][:2]))
    bonus = set(rank[:extra])
    return [
        (activity, place, split[i][0] + (1 if i in bonus else 0))
        for i, (activity, place, _) in enumerate(ordered)
    ]


def work_lines(entity: Entity) -> list[tuple[str, str, int]]:
    """Today's ``(activity, place, workers)`` as the camp system stored it."""
    rows = cast(list[list[Value]], entity.get("work", []))
    return [(cast(str, a), cast(str, p), cast(int, n)) for a, p, n in rows]


def set_work(entity: Entity, lines: list[tuple[str, str, int]]) -> None:
    """Store today's split."""
    entity["work"] = [[a, p, n] for a, p, n in lines]
