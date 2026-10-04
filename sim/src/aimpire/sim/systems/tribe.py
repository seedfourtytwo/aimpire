"""Shared access to a tribe's ``civ`` entity for the M0 systems (backlog M0b).

Why one module: forage, scout, camp, hunger and the commit step all read and
write the same entity, and the observation reads it back through
``aimpire.cognition.civ_record``. Keeping every accessor here keeps the layout
in one place. The public layout is the one ``civ_record`` documents
(``camp``, ``population``, ``stores``, ``known``, ``tasks`` ...). The M0
systems add three engine-only fields that observations never read:

    ``carries``      ``{name: int}``: carried remainders of the tribe's flows
                     (ADR-0012), such as the food need or spoilage. Units are
                     ``1 / (PPM * per_ticks)`` mu of the flow they belong to.
    ``task_times``   ``{task_id: [start, arrive, done]}``: ticks of a started
                     task (see ``aimpire.sim.systems.work``).
    ``work``         ``[[activity, place, workers]]``: today's split of the
                     free workers by the standing policy, written by the camp
                     system and read by forage and scout in the same tick.

Units: food in milli-units (mu; 1_000 mu feeds one person for one tick),
people as head counts, ticks as game days. Integers only.
"""

from typing import Final, cast

from aimpire.sim.fixed import PPM, apply_rate
from aimpire.sim.ledger import Ledger
from aimpire.sim.state import Entity, Value, WorldState

CIV: Final = "civ"
EVIDENCE: Final = "evidence"
STORES: Final = "stores"
"""Ledger material for the food in a tribe's stores (mu)."""
FOOD: Final = "food"
"""The stores key for food, and the snapshot key in ``known``."""

CONSUME: Final = "CONSUME"
HARVEST: Final = "HARVEST"
SPOIL: Final = "SPOIL"


def civ_entity_ids(state: WorldState) -> list[int]:
    """Ids of every ``civ`` entity, sorted (callers shuffle with ``ctx.order``)."""
    return sorted(eid for eid, e in state.entities.items() if e.get("kind") == CIV)


def living_civ_ids(state: WorldState) -> list[int]:
    """Civs with at least one person. An extinct civ (population 0) is left alone."""
    return [eid for eid in civ_entity_ids(state) if population(state.entities[eid]) > 0]


def _str(entity: Entity, key: str) -> str:
    value = entity.get(key)
    if type(value) is not str:
        raise TypeError(f"civ field {key!r} must be a str")
    return value


def sub_dict(entity: Entity, key: str) -> dict[str, Value]:
    """The mapping stored at ``entity[key]``, created empty if absent."""
    value = entity.setdefault(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"civ field {key!r} must be a mapping")
    return value


def sub_list(entity: Entity, key: str) -> list[Value]:
    """The list stored at ``entity[key]``, created empty if absent."""
    value = entity.setdefault(key, [])
    if not isinstance(value, list):
        raise TypeError(f"civ field {key!r} must be a list")
    return value


def civ_id(entity: Entity) -> str:
    """The civilization id, such as ``"C1"``."""
    return _str(entity, "civ_id")


def camp(entity: Entity) -> str:
    """The place id where the people live."""
    return _str(entity, "camp")


def population(entity: Entity) -> int:
    """Head count; 0 means extinct. Missing counts as 0 (a pre-M0 test civ)."""
    value = entity.get("population", 0)
    if type(value) is not int or value < 0:
        raise TypeError("civ field 'population' must be a non-negative int")
    return value


def ration(entity: Entity) -> int:
    """The ration of the standing policy, permille of the full need."""
    policy = sub_dict(entity, "policy")
    value = policy.get("ration")
    if type(value) is not int or value < 0:
        raise TypeError("civ policy ration must be a non-negative int")
    return value


def policy_lines(entity: Entity) -> list[tuple[str, str, int]]:
    """``(activity, place, share permille)`` of the standing policy, in stored order."""
    rows = cast(list[list[Value]], sub_dict(entity, "policy").get("allocations", []))
    return [(cast(str, a), cast(str, p), cast(int, s)) for a, p, s in rows]


def stores_food(entity: Entity) -> int:
    """Food in the stores, mu."""
    value = sub_dict(entity, "stores").get(FOOD, 0)
    if type(value) is not int or value < 0:
        raise TypeError("civ stores food must be a non-negative int")
    return value


def add_to_stores(entity: Entity, ledger: Ledger, amount: int, kind: str, ref: str) -> None:
    """Put ``amount`` mu of food into the stores and record it."""
    if amount < 0:
        raise ValueError(f"amount must be >= 0, got {amount}")
    if amount:
        sub_dict(entity, "stores")[FOOD] = stores_food(entity) + amount
        ledger.record(STORES, amount, kind, ref)


def take_from_stores(entity: Entity, ledger: Ledger, wanted: int, kind: str, ref: str) -> int:
    """Remove up to ``wanted`` mu from the stores; return what was taken.

    Stores never go negative: a demand larger than the stores takes them all,
    and the caller decides what the unmet part means (hunger counts it).
    """
    if wanted < 0:
        raise ValueError(f"wanted must be >= 0, got {wanted}")
    taken = min(wanted, stores_food(entity))
    if taken:
        sub_dict(entity, "stores")[FOOD] = stores_food(entity) - taken
        ledger.record(STORES, -taken, kind, ref)
    return taken


def carry(entity: Entity, name: str) -> int:
    """A carried remainder (0 if never set)."""
    value = sub_dict(entity, "carries").get(name, 0)
    if type(value) is not int or value < 0:
        raise TypeError(f"carry {name!r} must be a non-negative int")
    return value


def set_carry(entity: Entity, name: str, value: int) -> None:
    """Store a carried remainder."""
    sub_dict(entity, "carries")[name] = value


def flow(entity: Entity, name: str, value: int, ppm: int, per_ticks: int) -> int:
    """This tick's whole mu of ``value * ppm / (PPM * per_ticks)``, carrying the rest.

    ``fixed.apply_rate`` with the carry kept in ``carries[name]``. Some flows
    change their period when the camp moves (a trip's length). A stored carry
    is always worth less than 1 mu; if it is not below the new denominator it
    is dropped, so a period change moves at most 1 mu of rounding.
    """
    held = carry(entity, name)
    if held >= PPM * per_ticks:
        held = 0
    delta, rest = apply_rate(value, ppm, per_ticks, held)
    set_carry(entity, name, rest)
    return delta


def add_evidence(state: WorldState, entity: Entity, place: str, text: str) -> int:
    """Record something this tribe's people perceived (``civ_record`` evidence layout).

    M0 has no person entities, so ``witnesses`` is empty: the people are a count.
    """
    fields: dict[str, Value] = {
        "civ": civ_id(entity),
        "tick": state.tick,
        "place": place,
        "text": text,
        "witnesses": [],
    }
    return state.add_entity(EVIDENCE, fields)
