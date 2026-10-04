"""The M0 rule baselines: random, greedy, half full and msy (backlog M0c, ADR-0014).

What they are for: the reference a mind is scored against. Each answers the
same question, how many people forage where, from the observation alone
(plus the disclosed rule, ``cognition.disclosed``), and replies through the
same validator as a model. None reads world truth: stocks come from the
dated snapshots shown in ``places``, ceilings from the baseline's own
journal (``baseline_kit``).

* ``random``: every council, uniform random shares of all the people over the
  known places, all foraging. Seeded: the draws are a hash of a seed and the
  observation version, so a world gives the same draws on every run. It never
  scouts.
* ``greedy``: everyone but one scout forages the place with the most food
  last seen (ties: nearer, then lower id). It takes all it can reach.
* ``half_full``: forage a place only while its last-seen stock is above half
  its ceiling, and only that surplus: the excess over K/2 spread over the
  ticks to the next council. It needs no regrowth law; regrowth refills the
  place between councils and the next council takes that. Places last seen
  more than one council ago are unsure and left alone.
* ``msy``: the analytic optimum of the disclosed regrowth law: hold each
  place at x* = (1 - s/r)/2 of its ceiling and take the steady yield
  K (r + s)^2 / (4 r) a tick, plus (or minus) the gap to x* K spread over
  the ticks to the next council.

``greedy``, ``half_full`` and ``msy`` keep one person scouting the camp's own
place as a standing allocation. From the camp the scout sees the camp and its
neighbours every tick (``scout.sight``), so their snapshots are at most a
tick old: the three differ only in how much they take, not in what they know.
Nobody moves camp.

Rationing is always full (1000 permille); the baselines starve rather than ration.
"""

import hashlib
from collections.abc import Callable
from fractions import Fraction
from typing import Final

from aimpire.cognition.baseline_kit import (
    FORAGE,
    SCOUT,
    Line,
    camp_of,
    fit,
    read_ceilings,
    reply,
    seen_food_mu,
    shares_for,
    workers_for,
    write_ceilings,
)
from aimpire.cognition.disclosed import Disclosed
from aimpire.contracts.mind import MindReply, Observation
from aimpire.contracts.vocabulary import PERMILLE

M0_BASELINES: Final = ("random", "greedy", "half_full", "msy")
"""The registered names, in the order reports list them."""

_DRAW_PERSON: Final = b"aimpire-rand-v1"
RateRule = Callable[[int, int, int, Disclosed], Fraction]
"""``rate(food_mu, ceiling_mu, interval_ticks, disclosed)``: mu a tick to take."""


def _draw(seed: int, version: str, index: int) -> int:
    """A uniform integer in [0, 1000] from a hash of the seed, observation and index."""
    data = f"{seed}:{version}:{index}".encode()
    value = int.from_bytes(hashlib.blake2b(data, digest_size=8, person=_DRAW_PERSON).digest())
    return value % (PERMILLE + 1)


def random_shares(obs: Observation, seed: int = 0) -> MindReply:
    """Uniform random foraging shares over the known places, summing to 1000."""
    places = sorted(p.place_id for p in obs.places)
    if not places or obs.status.population == 0:
        return reply(obs)
    weights = [_draw(seed, obs.version, i) for i in range(len(places))]
    if not any(weights):
        weights = [1] * len(places)
    total = sum(weights)
    split = [divmod(w * PERMILLE, total) for w in weights]
    extra = PERMILLE - sum(q for q, _ in split)
    rank = sorted(range(len(places)), key=lambda i: (-split[i][1], places[i]))
    shares = [q + (1 if i in rank[:extra] else 0) for i, (q, _) in enumerate(split)]
    return reply(obs, [(FORAGE, pid, s) for pid, s in zip(places, shares, strict=True) if s])


def _scouts(population: int) -> int:
    """One standing scout, unless that would be the whole tribe."""
    return 1 if population > 1 else 0


def greedy(obs: Observation) -> MindReply:
    """Everyone but the scout forages the place with the most food last seen."""
    camp, people = camp_of(obs), obs.status.population
    seen = [(food, p) for p in obs.places if (food := seen_food_mu(p)) is not None]
    if camp is None or not seen or people == 0:
        return reply(obs)
    _, best = min(seen, key=lambda fp: (-fp[0], fp[1].travel_ticks, fp[1].place_id))
    scouts = _scouts(people)
    lines: list[Line] = [(FORAGE, best.place_id, people - scouts), (SCOUT, camp.place_id, scouts)]
    return reply(obs, shares_for(lines, people))


def half_full_rate(food_mu: int, ceiling_mu: int, interval: int, _d: Disclosed) -> Fraction:
    """The stock above K/2, spread over the ticks to the next council; 0 at or below K/2."""
    return max(Fraction(0), Fraction(2 * food_mu - ceiling_mu, 2 * interval))


def msy_rate(food_mu: int, ceiling_mu: int, interval: int, d: Disclosed) -> Fraction:
    """The steady yield at x*, corrected by the gap to x* K over the interval; at least 0."""
    gap = food_mu - d.msy_stock() * ceiling_mu
    return max(Fraction(0), d.msy_yield(ceiling_mu) + gap / interval)


def sustained(obs: Observation, d: Disclosed, rate: RateRule) -> MindReply:
    """Forage each surely known place at ``rate``; keep one scout at the camp."""
    camp, people = camp_of(obs), obs.status.population
    ceilings = read_ceilings(obs)
    journal = write_ceilings(ceilings)
    if camp is None or people == 0:
        return reply(obs, journal=journal)
    interval = max(1, obs.calendar.ticks_to_next_council)
    wants: list[Line] = []
    for place in sorted(obs.places, key=lambda p: p.place_id):
        food = seen_food_mu(place)
        if food is None or obs.calendar.tick - place.last_seen_tick > interval:
            continue  # unsure: never seen, or not seen since the last council
        take = rate(food, ceilings[place.place_id], interval, d)
        wants.append((FORAGE, place.place_id, workers_for(take, place.travel_ticks, d.carry_mu)))
    scouts = _scouts(people)
    lines = [*fit(wants, people - scouts), (SCOUT, camp.place_id, scouts)]
    return reply(obs, shares_for(lines, people), journal=journal)


def half_full(obs: Observation, d: Disclosed) -> MindReply:
    """Take only the stock above half the ceiling (module docstring)."""
    return sustained(obs, d, half_full_rate)


def msy(obs: Observation, d: Disclosed) -> MindReply:
    """Hold each place at the analytic optimum of the disclosed law (module docstring)."""
    return sustained(obs, d, msy_rate)


def m0_policy(name: str, disclosed: Disclosed) -> Callable[[Observation], MindReply]:
    """The policy registered as ``name``, bound to ``disclosed``. ``KeyError`` if unknown."""
    policies: dict[str, Callable[[Observation], MindReply]] = {
        "random": random_shares,
        "greedy": greedy,
        "half_full": lambda obs: half_full(obs, disclosed),
        "msy": lambda obs: msy(obs, disclosed),
    }
    return policies[name]
