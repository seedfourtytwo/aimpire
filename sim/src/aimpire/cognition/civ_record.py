"""Typed, read-only access to what one civilization holds (contract ``m0``).

Why a separate reader: the observation builder must see only what one
civilization could have perceived (CLAUDE.md, truth / evidence / belief). All
of its access to ``WorldState`` entities goes through this module, which
reads exactly three entity kinds and filters them by civilization:

* ``civ``      — the one entity whose ``civ_id`` is the civilization asked for;
* ``evidence`` — evidence entities whose ``civ`` is that civilization;
* ``message``  — message entities whose ``civ`` is that civilization.

Nothing here reads ``event`` entities (world truth, with ``hidden_cause``),
tile layers, or another civilization's entities. A leak would need a change
to this file, which is what the F5c acceptance tests guard.

m0 layout of a ``civ`` entity (ints and strings only, ADR-0012; quantities in
milli-units, 1000 mu = one unit, and one unit of food = one person-day):

    ``civ_id``        ``"C01"``
    ``camp``          place id where the people live
    ``population``    head count
    ``stores``        ``{material: mu}``; food is ``"food"``
    ``known``         ``{place_id: {"seen_tick": int, "seen": {material: mu}}}``:
                      places the civilization knows and its last-seen snapshot
                      of them, never the live tile values
    ``names``         ``{place_id: text}``: this civilization's own names. The
                      only place names in the state; place entities have none
                      (``aimpire.sim.places.set_civ_name`` writes here)
    ``policy``        ``{"allocations": [[activity, place, share‰]], "ration": ‰}``
                      (``StandingPolicy.to_value``)
    ``tasks``         ``[[task_id, kind, place, qty, status]]``
    ``commitments``   ``[[kind, place, qty, by_council, "MET"|"PENDING"|"MISSED"]]``
    ``last_results``  ``[[index, kind, place, "ACCEPTED"|"REJECTED", reason]]``
    ``journal``       the mind's text from its previous reply
    ``last_council``  ``{"council", "tick", "population", "stores"}``: the
                      snapshot taken at the previous council (``tick`` -1 if none)

``evidence``: ``civ``, ``tick``, ``place``, ``text``, ``witnesses`` (person ids).
``message``:  ``civ``, ``tick``, ``delivered_by`` (person id), ``route``, ``text``.

The council barrier and the M0 systems write these; this module only reads.
"""

from dataclasses import dataclass
from typing import Final, Literal, cast

from aimpire.sim.state import Entity, Value, WorldState

MILLI: Final = 1000
"""Milli-units per whole unit (ADR-0007)."""

CIV: Final = "civ"
EVIDENCE: Final = "evidence"
MESSAGE: Final = "message"

Stock = tuple[tuple[str, int], ...]
"""``(material, milli-units)`` pairs in material order."""

CommitState = Literal["MET", "PENDING", "MISSED"]
ResultOutcome = Literal["ACCEPTED", "REJECTED"]


@dataclass(frozen=True, slots=True)
class Snapshot:
    """The civilization's own figures at its previous council."""

    council: int
    tick: int
    population: int
    stores: Stock


@dataclass(frozen=True, slots=True)
class CivRecord:
    """One civilization's private state, sorted for deterministic iteration."""

    civ_id: str
    camp: str
    population: int
    stores: Stock
    known: tuple[tuple[str, int, Stock], ...]  # (place_id, seen_tick, seen) by place id
    names: tuple[tuple[str, str], ...]
    allocations: tuple[tuple[str, str, int], ...]
    ration: int
    tasks: tuple[tuple[str, str, str, int, str], ...]
    commitments: tuple[tuple[str, str, int, int, CommitState], ...]
    last_results: tuple[tuple[int, str, str, ResultOutcome, str], ...]
    journal: str
    last_council: Snapshot


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Something this civilization's people perceived."""

    entity_id: int
    tick: int
    place: str
    text: str
    witnesses: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MessageRecord:
    """Quoted text reported to this civilization's council."""

    entity_id: int
    tick: int
    delivered_by: int
    route: str
    text: str


def _int(value: Value, where: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{where} must be an int")
    return value


def _str(value: Value, where: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{where} must be a str")
    return value


def _list(value: Value, where: str) -> list[Value]:
    if not isinstance(value, list):
        raise TypeError(f"{where} must be a list")
    return value


def _dict(value: Value, where: str) -> dict[str, Value]:
    if not isinstance(value, dict):
        raise TypeError(f"{where} must be a mapping")
    return value


def _row(value: Value, size: int, where: str) -> list[Value]:
    row = _list(value, where)
    if len(row) != size:
        raise TypeError(f"{where} must have {size} items")
    return row


def _stock(value: Value, where: str) -> Stock:
    items = _dict(value, where)
    return tuple((k, _int(items[k], f"{where}.{k}")) for k in sorted(items))


def _commit_state(value: Value, where: str) -> CommitState:
    text = _str(value, where)
    if text not in ("MET", "PENDING", "MISSED"):
        raise ValueError(f"{where} must be MET, PENDING or MISSED")
    return cast(CommitState, text)


def _outcome(value: Value, where: str) -> ResultOutcome:
    text = _str(value, where)
    if text not in ("ACCEPTED", "REJECTED"):
        raise ValueError(f"{where} must be ACCEPTED or REJECTED")
    return cast(ResultOutcome, text)


def _snapshot(value: Value, where: str) -> Snapshot:
    d = _dict(value, where)
    return Snapshot(
        council=_int(d.get("council"), f"{where}.council"),
        tick=_int(d.get("tick"), f"{where}.tick"),
        population=_int(d.get("population"), f"{where}.population"),
        stores=_stock(d.get("stores"), f"{where}.stores"),
    )


def _known(value: Value, where: str) -> tuple[tuple[str, int, Stock], ...]:
    d = _dict(value, where)
    out: list[tuple[str, int, Stock]] = []
    for pid in sorted(d):
        entry = _dict(d[pid], f"{where}.{pid}")
        seen_tick = _int(entry.get("seen_tick"), f"{where}.{pid}.seen_tick")
        out.append((pid, seen_tick, _stock(entry.get("seen"), f"{where}.{pid}.seen")))
    return tuple(out)


def _view(e: Entity, w: str) -> CivRecord:
    names = _dict(e.get("names"), f"{w}.names")
    policy = _dict(e.get("policy"), f"{w}.policy")
    allocs = [_row(a, 3, f"{w}.policy.allocations") for a in _list(policy.get("allocations"), w)]
    tasks = [_row(t, 5, f"{w}.tasks") for t in _list(e.get("tasks"), f"{w}.tasks")]
    commits = [_row(c, 5, f"{w}.commitments") for c in _list(e.get("commitments"), w)]
    results = [_row(r, 5, f"{w}.last_results") for r in _list(e.get("last_results"), w)]
    return CivRecord(
        civ_id=_str(e.get("civ_id"), f"{w}.civ_id"),
        camp=_str(e.get("camp"), f"{w}.camp"),
        population=_int(e.get("population"), f"{w}.population"),
        stores=_stock(e.get("stores"), f"{w}.stores"),
        known=_known(e.get("known"), f"{w}.known"),
        names=tuple((k, _str(names[k], f"{w}.names.{k}")) for k in sorted(names)),
        allocations=tuple((_str(a, w), _str(p, w), _int(s, w)) for a, p, s in allocs),
        ration=_int(policy.get("ration"), f"{w}.policy.ration"),
        tasks=tuple(
            (_str(i, w), _str(k, w), _str(p, w), _int(q, w), _str(s, w)) for i, k, p, q, s in tasks
        ),
        commitments=tuple(
            (_str(k, w), _str(p, w), _int(q, w), _int(b, w), _commit_state(s, w))
            for k, p, q, b, s in commits
        ),
        last_results=tuple(
            (_int(i, w), _str(k, w), _str(p, w), _outcome(o, w), _str(r, w))
            for i, k, p, o, r in results
        ),
        journal=_str(e.get("journal"), f"{w}.journal"),
        last_council=_snapshot(e.get("last_council"), f"{w}.last_council"),
    )


def _owned(state: WorldState, kind: str, civ_id: str) -> list[tuple[int, Entity]]:
    """Entities of ``kind`` belonging to ``civ_id``, in entity-id order."""
    return [
        (eid, state.entities[eid])
        for eid in sorted(state.entities)
        if state.entities[eid].get("kind") == kind and state.entities[eid].get("civ") == civ_id
    ]


def read_civ(state: WorldState, civ_id: str) -> CivRecord:
    """The ``civ`` entity for ``civ_id``. ``KeyError`` if absent, ``ValueError`` if repeated."""
    found = [
        eid
        for eid in sorted(state.entities)
        if state.entities[eid].get("kind") == CIV and state.entities[eid].get("civ_id") == civ_id
    ]
    if not found:
        raise KeyError(f"no civ entity for {civ_id!r}")
    if len(found) > 1:
        raise ValueError(f"{len(found)} civ entities claim {civ_id!r}")
    return _view(state.entities[found[0]], f"civ {civ_id}")


def read_evidence(state: WorldState, civ_id: str) -> tuple[EvidenceRecord, ...]:
    """Evidence in this civilization's pool, in entity-id order."""
    out: list[EvidenceRecord] = []
    for eid, e in _owned(state, EVIDENCE, civ_id):
        w = f"evidence {eid}"
        witnesses = tuple(_int(p, f"{w}.witnesses") for p in _list(e.get("witnesses"), w))
        out.append(
            EvidenceRecord(
                entity_id=eid,
                tick=_int(e.get("tick"), f"{w}.tick"),
                place=_str(e.get("place"), f"{w}.place"),
                text=_str(e.get("text"), f"{w}.text"),
                witnesses=tuple(sorted(witnesses)),
            )
        )
    return tuple(out)


def read_messages(state: WorldState, civ_id: str) -> tuple[MessageRecord, ...]:
    """Messages reported to this civilization's council, in entity-id order."""
    out: list[MessageRecord] = []
    for eid, e in _owned(state, MESSAGE, civ_id):
        w = f"message {eid}"
        out.append(
            MessageRecord(
                entity_id=eid,
                tick=_int(e.get("tick"), f"{w}.tick"),
                delivered_by=_int(e.get("delivered_by"), f"{w}.delivered_by"),
                route=_str(e.get("route"), f"{w}.route"),
                text=_str(e.get("text"), f"{w}.text"),
            )
        )
    return tuple(out)
