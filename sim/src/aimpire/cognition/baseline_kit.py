"""Shared pieces of the rule baselines: reading an observation, writing a reply (ADR-0013).

Why a kit: every baseline must reach the validator by the same path as a
model, so it reads only the typed ``Observation`` and answers with a complete
``MindReply``. These helpers do that reading and writing once:

* ``seen_food_mu`` reads a place's last-seen snapshot (``"food 120"``) back
  into milli-units, the only stock figure a mind is ever shown;
* ``read_ceilings`` / ``write_ceilings`` keep a baseline's estimate of each
  place's ceiling in its own journal. The journal is the mind's one
  self-written memory (ADR-0013 section 6), so a baseline remembers exactly
  as a model may, and nothing else. The estimate is the most food ever seen
  at the place: the dish starts full, so a first sighting of an untouched
  place is its ceiling;
* ``workers_for`` and ``shares_for`` turn a harvest rate into people and the
  people into permille shares that ``work.apportion`` splits back exactly.

Units: food in milli-units (mu) unless a name says units; shares permille.
"""

import math
import re
from collections.abc import Iterable, Sequence
from fractions import Fraction
from typing import Final

from aimpire.contracts.mind import MindReply, Observation, PlaceView
from aimpire.contracts.vocabulary import PERMILLE

MILLI: Final = 1000
FORAGE: Final = "FORAGE"
SCOUT: Final = "SCOUT"
_FOOD = re.compile(r"\bfood (\d+)\b")
_CEILING = re.compile(r"\b(PL\d+)=(\d+)\b")
_CEILINGS_HEAD: Final = "ceilings"

Line = tuple[str, str, int]
"""``(activity, place, people)``."""


def reply(
    obs: Observation,
    allocations: Sequence[Line] = (),
    orders: Sequence[dict[str, object]] = (),
    *,
    ration: int = PERMILLE,
    journal: str = "",
) -> MindReply:
    """A complete reply: every field present, unused ones empty (ADR-0013).

    ``allocations`` here are ``(activity, place, share permille)``.
    """
    return MindReply.model_validate(
        {
            "decision_id": obs.decision_id,
            "policy": {
                "allocations": [{"activity": a, "place": p, "share": s} for a, p, s in allocations],
                "ration": ration,
            },
            "orders": list(orders),
            "messages": [],
            "commitments": [],
            "beliefs": [],
            "names": [],
            "journal": journal,
            "annal": "",
        }
    )


def seen_food_mu(place: PlaceView) -> int | None:
    """Food at ``place`` when last seen, mu (shown in whole units); ``None`` if never seen."""
    if place.last_seen_tick < 0:
        return None
    found = _FOOD.search(place.seen)
    return int(found.group(1)) * MILLI if found else 0


def camp_of(obs: Observation) -> PlaceView | None:
    """The camp's own place: the known place zero ticks away (``None`` if not shown)."""
    here = [p for p in obs.places if p.travel_ticks == 0]
    return min(here, key=lambda p: p.place_id) if here else None


def read_ceilings(obs: Observation) -> dict[str, int]:
    """Ceiling estimate per place, mu: the larger of the journal's and today's sighting."""
    remembered = {pid: int(units) * MILLI for pid, units in _CEILING.findall(obs.journal)}
    for place in obs.places:
        food = seen_food_mu(place)
        if food is not None:
            remembered[place.place_id] = max(remembered.get(place.place_id, 0), food)
    return remembered


def write_ceilings(ceilings: dict[str, int]) -> str:
    """Journal text holding the estimates, in whole units: ``"ceilings PL01=1664 ..."``."""
    body = " ".join(f"{pid}={mu // MILLI}" for pid, mu in sorted(ceilings.items()))
    return f"{_CEILINGS_HEAD} {body}".strip()


def workers_for(rate_mu: Fraction, travel_ticks: int, carry_mu: int) -> int:
    """Foragers needed to bring in ``rate_mu`` a tick from a place ``travel_ticks`` away.

    A forager there makes one trip of ``1 + 2 * travel_ticks`` ticks and carries
    ``carry_mu`` home (the M0b forage rule), rounded up to whole people.
    """
    if rate_mu <= 0:
        return 0
    return math.ceil(rate_mu * (1 + 2 * travel_ticks) / carry_mu)


def fit(lines: Sequence[Line], people: int) -> list[Line]:
    """Scale the people of ``lines`` down (floor) so they sum to at most ``people``."""
    wanted = sum(n for _, _, n in lines)
    if wanted <= people:
        return list(lines)
    return [(a, p, n * people // wanted) for a, p, n in lines]


def shares_for(lines: Iterable[Line], population: int) -> list[Line]:
    """Permille shares giving each line at least its people under ``work.apportion``.

    ``ceil(1000 * n / population)`` workers' worth each, then the largest
    shares are trimmed one permille at a time until they sum to at most 1000.
    """
    if population <= 0:
        return []
    shares = {(a, p): -(-n * PERMILLE // population) for a, p, n in sorted(lines) if n > 0}
    while sum(shares.values()) > PERMILLE:
        largest = max(shares, key=lambda key: (shares[key], key))
        shares[largest] -= 1
    return [(a, p, s) for (a, p), s in sorted(shares.items())]
