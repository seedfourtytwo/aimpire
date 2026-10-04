"""Named rule baselines, for ``aimpire qualify rule:<name>`` and batch arms (ADR-0014).

Why here: experiments and qualification name minds by text (``rule:hold``),
so the rules need one registry. Each rule reads only the typed observation it
is given, exactly what a model is shown, and answers through ``RuleProvider``
and the same validator as a model (ADR-0005).

These two are plumbing baselines, not the M0 set: ``hold`` is the null mind
and ``forage_nearest`` exercises policy and orders on every observation. M0c
registers the analytic baselines (random, greedy, half full, msy) here.
"""

from collections.abc import Mapping
from typing import Final

from aimpire.cognition.offline import RulePolicy, RuleProvider
from aimpire.contracts.mind import MindReply, Observation, PlaceView
from aimpire.contracts.vocabulary import PERMILLE

DEFAULT_RULE: Final = "forage_nearest"


def _reply(
    obs: Observation, policy: dict[str, object], orders: list[dict[str, object]]
) -> MindReply:
    """A complete reply: every field present, unused ones empty (ADR-0013)."""
    return MindReply.model_validate(
        {
            "decision_id": obs.decision_id,
            "policy": policy,
            "orders": orders,
            "messages": [],
            "commitments": [],
            "beliefs": [],
            "names": [],
            "journal": "",
            "annal": "",
        }
    )


def hold(obs: Observation) -> MindReply:
    """Change nothing: no allocations and ration 0 keep the policy in force; no orders."""
    return _reply(obs, {"allocations": [], "ration": 0}, [])


def _nearest(places: list[PlaceView]) -> PlaceView:
    return min(places, key=lambda p: (p.travel_ticks, p.place_id))


def _stalest(places: list[PlaceView]) -> PlaceView:
    return min(places, key=lambda p: (p.last_seen_tick, p.place_id))


def forage_nearest(obs: Observation) -> MindReply:
    """Everyone forages the nearest known place; one person scouts the least recently seen one."""
    if not obs.places:
        return hold(obs)
    nearest = _nearest(obs.places)
    allocation = {"activity": "FORAGE", "place": nearest.place_id, "share": PERMILLE}
    orders: list[dict[str, object]] = []
    if obs.status.population >= 1:
        target = _stalest(obs.places).place_id
        orders.append({"kind": "SCOUT", "place": target, "target": "", "qty": 1, "text": ""})
    return _reply(obs, {"allocations": [allocation], "ration": PERMILLE}, orders)


RULES: Final[Mapping[str, RulePolicy]] = {"forage_nearest": forage_nearest, "hold": hold}


def rule_provider(name: str) -> RuleProvider:
    """The ``RuleProvider`` for a registered rule. ``KeyError`` names the known rules."""
    if name not in RULES:
        raise KeyError(f"unknown rule {name!r}; known rules: {sorted(RULES)}")
    return RuleProvider(RULES[name], name=name)
