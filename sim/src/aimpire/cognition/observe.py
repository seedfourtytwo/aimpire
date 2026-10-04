"""Build the observation one mind is shown at one council (ADR-0013 section 2).

Why it is built this way: the observation must hold nothing a civilization
could not have perceived (CLAUDE.md, truth / evidence / belief). So the
builder takes its civilization-specific inputs only from
``aimpire.cognition.civ_record``, which reads that civilization's own ``civ``,
``evidence`` and ``message`` entities and nothing else. The only other state
it reads is geography from ``aimpire.sim.places``: the kind of each known
place and travel times. It never reads tile layers (a place's contents come
from the civilization's last-seen snapshot), ``event`` entities (world truth
with ``hidden_cause``), or other civilizations. Place names come from the
civilization's own ``names`` map; place entities carry none.

Travel times use only routes through places this civilization knows, plus its
camp (``travel_ticks_within``). The true shortest path could run through a
place it has never seen, and its length would reveal that place. If the known
places do not connect, the time shown is ``lower_bound_ticks``: the Manhattan
distance between the two known centroids, which uses the endpoints' geometry
only and never exceeds the true time. So adding, removing or reshaping an
unseen place leaves the observation unchanged.

Consequences, checked by the F5c acceptance tests:

* changing another civilization's private state, a truth event or an unseen
  tile leaves the observation, and its hash, unchanged;
* the same state gives the same observation, byte for byte, in any process.

Units: authoritative state is in milli-units; the observation holds whole
units, rounded down (``MILLI``). Food is whole person-days. Ticks are days.
Shares and ration stay in permille, the unit the reply uses.

``version`` is ``"<civ>:c<council>:<hash12>"``, where the hash covers the whole
observation with an empty version. A reply that echoes an older version is
stale (the validator's ``STALE_OBSERVATION``).
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Final

from aimpire.cognition.civ_record import (
    MILLI,
    CivRecord,
    Stock,
    read_civ,
    read_evidence,
    read_messages,
)
from aimpire.cognition.render import GridLayout
from aimpire.contracts.mind import (
    CONTRACT_VERSION,
    Allocation,
    CalendarSection,
    CommitmentView,
    EventView,
    KnowledgeSection,
    MessageView,
    Observation,
    OrderResult,
    PlaceView,
    Policy,
    StandingSection,
    StatusSection,
    StockLine,
    TaskView,
)
from aimpire.contracts.vocabulary import MAX_EVENTS
from aimpire.sim.calendar import Calendar
from aimpire.sim.places import lower_bound_ticks, places_by_id, travel_ticks_within
from aimpire.sim.state import WorldState

FOOD: Final = "food"
_HASH_PERSON: Final = b"aimpire-obs-v1"
_VERSION_HEX: Final = 12


@dataclass(frozen=True, slots=True)
class CouncilCall:
    """Which council is being held. Issued by the council barrier (F5e).

    ``next_council_tick`` is the tick of the next scheduled council, from the
    scenario's cadence (ADR-0011); triggered councils are not predicted.
    """

    civ_id: str
    council: int
    decision_id: str
    next_council_tick: int


def _units(mu: int) -> int:
    """Whole units, rounded down. Display only: never written back to state."""
    return mu // MILLI


def _calendar(state: WorldState, call: CouncilCall, calendar: Calendar) -> CalendarSection:
    season = calendar.season_of(state.tick) + 1
    return CalendarSection(
        tick=state.tick,
        season=f"{season} of {calendar.seasons_per_year}",
        year=calendar.year_of(state.tick) + 1,
        council=call.council,
        ticks_to_next_council=max(0, call.next_council_tick - state.tick),
    )


def _status(civ: CivRecord) -> StatusSection:
    now, then = dict(civ.stores), dict(civ.last_council.stores)
    others = sorted((now.keys() | then.keys()) - {FOOD})
    return StatusSection(
        population=civ.population,
        population_change=civ.population - civ.last_council.population,
        food_days=_units(now.get(FOOD, 0)),
        food_days_change=_units(now.get(FOOD, 0)) - _units(then.get(FOOD, 0)),
        stores=[
            StockLine(
                material=m,
                qty=_units(now.get(m, 0)),
                change=_units(now.get(m, 0)) - _units(then.get(m, 0)),
            )
            for m in others
        ],
    )


def _seen_text(seen: Stock) -> str:
    """The last-seen snapshot of a place as text: ``"food 12"``; ``"nothing"`` if empty."""
    return ", ".join(f"{m} {_units(mu)}" for m, mu in seen) or "nothing"


def _known_travel(state: WorldState, camp: str, pid: str, allowed: frozenset[str]) -> int:
    """Days from the camp using known places only; the lower bound if they do not connect."""
    found = travel_ticks_within(state, camp, pid, allowed)
    return lower_bound_ticks(state, camp, pid) if found is None else found


def _places(state: WorldState, civ: CivRecord) -> list[PlaceView]:
    geography = places_by_id(state)
    names = dict(civ.names)
    allowed = frozenset(pid for pid, _, _ in civ.known) | {civ.camp}
    views: list[PlaceView] = []
    for pid, seen_tick, seen in civ.known:
        if pid not in geography:
            raise KeyError(f"{civ.civ_id} knows {pid!r}, which is not a place")
        views.append(
            PlaceView(
                place_id=pid,
                name=names.get(pid, ""),
                kind=geography[pid].kind,
                travel_ticks=_known_travel(state, civ.camp, pid, allowed),
                last_seen_tick=seen_tick,
                seen=_seen_text(seen),
            )
        )
    return views


def _events(state: WorldState, civ: CivRecord) -> list[EventView]:
    """Evidence since the last council; the newest ``MAX_EVENTS``, oldest first."""
    since = civ.last_council.tick
    fresh = [e for e in read_evidence(state, civ.civ_id) if since < e.tick <= state.tick]
    fresh.sort(key=lambda e: (e.tick, e.entity_id))
    return [
        EventView(
            event_id=f"EV{e.entity_id:04d}",
            tick=e.tick,
            place=e.place,
            text=e.text,
            witnesses=[f"P{w:04d}" for w in e.witnesses],
        )
        for e in fresh[-MAX_EVENTS:]
    ]


def _messages(state: WorldState, civ: CivRecord) -> list[MessageView]:
    since = civ.last_council.tick
    fresh = [m for m in read_messages(state, civ.civ_id) if since < m.tick <= state.tick]
    fresh.sort(key=lambda m: (m.tick, m.entity_id))
    return [
        MessageView(
            message_id=f"MS{m.entity_id:04d}",
            tick=m.tick,
            delivered_by=f"P{m.delivered_by:04d}",
            route=m.route,
            text=m.text,
        )
        for m in fresh
    ]


def _standing(civ: CivRecord) -> StandingSection:
    return StandingSection(
        policy=Policy(
            allocations=[Allocation(activity=a, place=p, share=s) for a, p, s in civ.allocations],
            ration=civ.ration,
        ),
        tasks=[
            TaskView(task_id=i, kind=k, place=p, qty=q, status=s) for i, k, p, q, s in civ.tasks
        ],
        commitments=[
            CommitmentView(kind=k, place=p, qty=q, by_council=b, state=s)
            for k, p, q, b, s in civ.commitments
        ],
    )


def observation_hash(obs: Observation) -> str:
    """BLAKE2b-256 hex digest of the observation's canonical JSON (sorted keys, ASCII)."""
    data = json.dumps(
        obs.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.blake2b(data, digest_size=32, person=_HASH_PERSON).hexdigest()


def build_observation(state: WorldState, call: CouncilCall, calendar: Calendar) -> Observation:
    """The observation for ``call.civ_id`` at ``state.tick``. Reads, never writes, the state."""
    civ = read_civ(state, call.civ_id)
    draft = Observation(
        contract=CONTRACT_VERSION,
        civ_id=civ.civ_id,
        decision_id=call.decision_id,
        version="",
        calendar=_calendar(state, call, calendar),
        status=_status(civ),
        places=_places(state, civ),
        events=_events(state, civ),
        messages=_messages(state, civ),
        standing=_standing(civ),
        last_results=[
            OrderResult(index=i, kind=k, place=p, outcome=o, reason=r)
            for i, k, p, o, r in civ.last_results
        ],
        knowledge=KnowledgeSection(claims=[], beliefs=[]),  # from M3
        journal=civ.journal,
    )
    version = f"{civ.civ_id}:c{call.council:04d}:{observation_hash(draft)[:_VERSION_HEX]}"
    return draft.model_copy(update={"version": version})


def grid_layout(state: WorldState) -> GridLayout:
    """Block positions of every place, for the grid renderer.

    Public geometry only: distinct centroid rows and columns are ranked from
    1. Fits ``grid_blocks``; a partition where two places would share a cell
    (irregular regions, from M1) raises ``ValueError``.
    """
    places = places_by_id(state)
    row_rank = {r: i + 1 for i, r in enumerate(sorted({p.centroid[0] for p in places.values()}))}
    col_rank = {c: i + 1 for i, c in enumerate(sorted({p.centroid[1] for p in places.values()}))}
    cells = tuple(
        (pid, row_rank[p.centroid[0]], col_rank[p.centroid[1]]) for pid, p in places.items()
    )
    if len({(r, c) for _, r, c in cells}) != len(cells):
        raise ValueError("two places share a grid cell; this partition has no block grid")
    return GridLayout(rows=len(row_rank), cols=len(col_rank), cells=cells)
