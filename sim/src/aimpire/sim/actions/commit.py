"""Commit a decision record into civilization state (ADR-0013 sections 3 and 6).

Why here and not in the barrier: committing changes ``WorldState``, and the
state may only change through ``aimpire.sim`` (CLAUDE.md, authoritative sim).
The council barrier (``aimpire.cognition.council``) calls ``commit_decision``
once per record, in the turn-order permutation, after every seat has replied.

What a record commits, per ADR-0013 and ``decision.py``:

* ``policy``: the policy in force after the decision. A rejected or missing
  reply carries the previous policy, so committing it changes nothing.
* ``journal``: replaces the previous journal when the mind wrote one. Empty
  means "not used", so the old journal stays (ADR-0013 section 3).

* ``tasks``, ``last_results``, ``commitments``, ``names`` and
  ``last_council`` (M0b): accepted orders become tasks the M0 systems start
  in this same tick, so an order applies at the council tick, before the
  scheduler steps. See ``aimpire.sim.actions.bookkeeping``.

Messages and beliefs are carried by the record only: delivery and belief
records come in later milestones.

A civilization is an entity of kind ``civ`` with the string fields ``civ_id``
and ``journal`` and a ``policy`` value in ``StandingPolicy.to_value`` form.
The kind name is a mechanic of the engine, not an institution (ADR-0019).
"""

from typing import Final, cast

from aimpire.sim.actions.bookkeeping import apply_bookkeeping
from aimpire.sim.actions.decision import DecisionRecord, PolicyLine, StandingPolicy
from aimpire.sim.state import Entity, Value, WorldState

CIV_KIND: Final = "civ"


def standing_policy_of(entity: Entity) -> StandingPolicy:
    """Read the policy in force from a civilization entity.

    Raises ``ValueError`` when the stored value is not in ``to_value`` form,
    which would mean something other than this module wrote it.
    """
    value = entity.get("policy")
    if not isinstance(value, dict):
        raise ValueError("civilization entity has no policy")
    allocations, ration = value.get("allocations"), value.get("ration")
    if not isinstance(allocations, list) or type(ration) is not int:
        raise ValueError("civilization policy is malformed")
    lines: list[PolicyLine] = []
    for row in allocations:
        items = cast(list[Value], row) if isinstance(row, list) else []
        if len(items) != 3:
            raise ValueError("policy allocation must be [activity, place, share]")
        activity, place, share = items
        if type(activity) is not str or type(place) is not str or type(share) is not int:
            raise ValueError("policy allocation must be [activity, place, share]")
        lines.append(PolicyLine(activity, place, share))
    return StandingPolicy(allocations=tuple(lines), ration=ration)


def commit_decision(state: WorldState, civ_entity_id: int, record: DecisionRecord) -> None:
    """Write ``record``'s policy, journal and bookkeeping into the civilization entity.

    The entity must be a ``civ`` whose ``civ_id`` matches the record; anything
    else is a wiring error in the caller and raises ``ValueError``.
    """
    entity = state.entities.get(civ_entity_id)
    if entity is None or entity.get("kind") != CIV_KIND:
        raise ValueError(f"entity {civ_entity_id} is not a civilization")
    if entity.get("civ_id") != record.civ_id:
        raise ValueError(f"entity {civ_entity_id} does not hold civilization {record.civ_id!r}")
    entity["policy"] = record.policy.to_value()
    if record.journal:
        entity["journal"] = record.journal
    apply_bookkeeping(entity, record, state.tick)
