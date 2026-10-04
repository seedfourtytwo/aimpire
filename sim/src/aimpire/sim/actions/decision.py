"""Decision inputs and records, and the append-only decision log.

``CouncilSeat`` — the seam to the world
---------------------------------------
The validator needs to know what one civilization can refer to at one
council: its known places, its head count, its contacts, the evidence ids it
was shown and its standing policy. In m0 there is no places module yet
(``sim/places.py`` is built in parallel, F5c), so the caller supplies these
in a ``CouncilSeat``. When places and people exist in ``WorldState``, the
council barrier (F5e) builds the seat from the state and the observation;
the validator does not change.

Where the log lives, and the hash
---------------------------------
``DecisionLog`` is kept **outside** ``WorldState``, so validating a reply never
changes the state hash. What a decision does to the world is carried only by
the accepted items in its ``DecisionRecord``, applied later by the systems
that run tasks (M0b) and by the barrier, which commits the policy and the
journal into civilization state at the next tick (note 50 section 1). Records
hold only ints, strings and closed enums, and ``to_value`` gives the
canonical JSON form the run store (F5e) persists and hashes.
"""

from dataclasses import dataclass

from aimpire.sim.actions.outcomes import Flag, Outcome, Reason
from aimpire.sim.state import Value


@dataclass(frozen=True, slots=True)
class PolicyLine:
    """A standing share of workers: ``share`` in permille."""

    activity: str
    place: str
    share: int


@dataclass(frozen=True, slots=True)
class StandingPolicy:
    """A civilization's policy in force. ``ration`` is permille of a full daily ration."""

    allocations: tuple[PolicyLine, ...]
    ration: int

    def to_value(self) -> Value:
        """Canonical JSON form (ints and strings only)."""
        return {
            "allocations": [[a.activity, a.place, a.share] for a in self.allocations],
            "ration": self.ration,
        }


@dataclass(frozen=True, slots=True)
class CouncilSeat:
    """What the validator may check a reply against for one civilization at one council.

    ``decision_id`` is the id issued with the observation; the reply must echo
    it. ``observation_version`` is the civilization's *current* version; a
    reply to any other version is stale. ``people`` is the head count
    available for orders. ``evidence_ids`` are the ids shown in the
    observation. ``policy`` is the policy in force before this decision.
    """

    civ_id: str
    decision_id: str
    council: int
    observation_version: str
    known_places: frozenset[str]
    people: int
    known_civs: frozenset[str]
    evidence_ids: frozenset[str]
    policy: StandingPolicy


@dataclass(frozen=True, slots=True)
class AcceptedOrder:
    """An order that becomes a task. ``index`` is its position in the reply."""

    index: int
    kind: str
    place: str
    target: str
    qty: int
    text: str


@dataclass(frozen=True, slots=True)
class AcceptedMessage:
    """A message to deliver. Text only; it never acts on the world."""

    index: int
    to: str
    text: str


@dataclass(frozen=True, slots=True)
class AcceptedCommitment:
    """A promise the world will check by ``by_council``."""

    index: int
    kind: str
    place: str
    qty: int
    by_council: int


@dataclass(frozen=True, slots=True)
class AcceptedBelief:
    """A recorded belief and the observed evidence ids it cites."""

    index: int
    statement: str
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AcceptedName:
    """A name the civilization gives to a known place. Names never touch physics."""

    index: int
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Rejection:
    """Why ``field`` (``"orders[3]"``, ``"policy.ration"``, ``""`` for the reply) was dropped."""

    field: str
    reason: Reason


@dataclass(frozen=True, slots=True)
class Flagged:
    """A non-rejecting change to ``field``, such as truncated text."""

    field: str
    flag: Flag


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """The one terminal result of one decision.

    ``policy`` is the policy in force after the decision: the new one if it was
    accepted, else the previous one. Empty ``journal`` or ``annal`` means the
    mind did not use them (ADR-0013: empty means not used).
    """

    decision_id: str
    civ_id: str
    council: int
    tick: int
    contract: str
    observation_version: str
    outcome: Outcome
    policy: StandingPolicy
    orders: tuple[AcceptedOrder, ...]
    messages: tuple[AcceptedMessage, ...]
    commitments: tuple[AcceptedCommitment, ...]
    beliefs: tuple[AcceptedBelief, ...]
    names: tuple[AcceptedName, ...]
    journal: str
    annal: str
    rejections: tuple[Rejection, ...]
    flags: tuple[Flagged, ...]

    def to_value(self) -> Value:
        """Canonical JSON form: ints and strings only, lists in reply order."""
        return {
            "decision_id": self.decision_id,
            "civ_id": self.civ_id,
            "council": self.council,
            "tick": self.tick,
            "contract": self.contract,
            "observation_version": self.observation_version,
            "outcome": self.outcome.value,
            "policy": self.policy.to_value(),
            "orders": [[o.index, o.kind, o.place, o.target, o.qty, o.text] for o in self.orders],
            "messages": [[m.index, m.to, m.text] for m in self.messages],
            "commitments": [
                [c.index, c.kind, c.place, c.qty, c.by_council] for c in self.commitments
            ],
            "beliefs": [[b.index, b.statement, list(b.evidence)] for b in self.beliefs],
            "names": [[n.index, n.id, n.name] for n in self.names],
            "journal": self.journal,
            "annal": self.annal,
            "rejections": [[r.field, r.reason.value] for r in self.rejections],
            "flags": [[f.field, f.flag.value] for f in self.flags],
        }


# The validator's result is the record it appends.
Decision = DecisionRecord


class DecisionLog:
    """Append-only list of decision records, indexed by decision id.

    Not part of ``WorldState`` and not hashed with it. A decision id appears at
    most once: that is what makes re-validation idempotent.
    """

    __slots__ = ("_by_id", "_records")

    def __init__(self) -> None:
        self._records: list[DecisionRecord] = []
        self._by_id: dict[str, DecisionRecord] = {}

    def get(self, decision_id: str) -> DecisionRecord | None:
        """The stored record for ``decision_id``, if any."""
        return self._by_id.get(decision_id)

    def append(self, record: DecisionRecord) -> None:
        """Add a record. A second record for the same decision id is an error."""
        if record.decision_id in self._by_id:
            raise ValueError(f"decision {record.decision_id!r} is already recorded")
        self._records.append(record)
        self._by_id[record.decision_id] = record

    @property
    def records(self) -> tuple[DecisionRecord, ...]:
        """All records in the order they were appended."""
        return tuple(self._records)

    def __len__(self) -> int:
        return len(self._records)
