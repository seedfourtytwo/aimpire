"""Named rule baselines, for ``rule:<name>`` minds in qualify, batch and run (ADR-0014).

Why here: experiments and qualification name minds by text (``rule:half_full``),
so the rules need one registry. Each rule reads only the typed observation it
is given, exactly what a model is shown, and answers through ``RuleProvider``
and the same validator as a model (ADR-0005).

* The M0 baselines (``cognition.m0_baselines``): ``random``, ``greedy``,
  ``half_full`` and ``msy``. They also know the disclosed rule
  (``cognition.disclosed``); by default that of ``DEFAULT_RULES_DIR``.
* Two plumbing rules, kept because the F6 and M0b acceptance tests name them
  (``world: stub`` experiments, ``aimpire qualify rule``): ``hold`` is the
  null mind and ``forage_nearest`` exercises policy and orders on every
  observation. They are not baselines and no report compares a mind to them.
"""

from collections.abc import Mapping
from typing import Final

from aimpire.cognition.baseline_kit import reply
from aimpire.cognition.disclosed import Disclosed, default_disclosed
from aimpire.cognition.m0_baselines import M0_BASELINES, m0_policy
from aimpire.cognition.offline import RulePolicy, RuleProvider
from aimpire.contracts.mind import MindReply, Observation, PlaceView
from aimpire.contracts.vocabulary import PERMILLE

DEFAULT_RULE: Final = "forage_nearest"
"""What a bare ``rule`` mind means (the F6 acceptance tests pin it)."""


def hold(obs: Observation) -> MindReply:
    """Change nothing: no allocations and ration 0 keep the policy in force; no orders."""
    return reply(obs, ration=0)


def _nearest(places: list[PlaceView]) -> PlaceView:
    return min(places, key=lambda p: (p.travel_ticks, p.place_id))


def _stalest(places: list[PlaceView]) -> PlaceView:
    return min(places, key=lambda p: (p.last_seen_tick, p.place_id))


def forage_nearest(obs: Observation) -> MindReply:
    """Everyone forages the nearest known place; one person scouts the least recently seen one."""
    if not obs.places:
        return hold(obs)
    nearest = _nearest(obs.places)
    orders: list[dict[str, object]] = []
    if obs.status.population >= 1:
        target = _stalest(obs.places).place_id
        orders.append({"kind": "SCOUT", "place": target, "target": "", "qty": 1, "text": ""})
    return reply(obs, [("FORAGE", nearest.place_id, PERMILLE)], orders)


PLUMBING: Final[Mapping[str, RulePolicy]] = {"forage_nearest": forage_nearest, "hold": hold}
RULE_NAMES: Final = frozenset(PLUMBING) | frozenset(M0_BASELINES)
"""Every name ``rule:<name>`` accepts."""


def rule_provider(name: str, disclosed: Disclosed | None = None) -> RuleProvider:
    """The ``RuleProvider`` for a registered rule. ``KeyError`` names the known rules.

    ``disclosed`` is the rule an M0 baseline plays under; ``None`` reads the
    default rules. The plumbing rules ignore it.
    """
    if name in PLUMBING:
        return RuleProvider(PLUMBING[name], name=name)
    if name not in RULE_NAMES:
        raise KeyError(f"unknown rule {name!r}; known rules: {sorted(RULE_NAMES)}")
    return RuleProvider(m0_policy(name, disclosed or default_disclosed()), name=name)
