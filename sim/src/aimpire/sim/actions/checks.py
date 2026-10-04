"""Per-item legality checks for a schema-valid m0 reply (ADR-0013 section 5).

Each check reads one part of the reply and the ``CouncilSeat``, appends
``Rejection``s and ``Flagged`` notes to a shared ``Findings``, and returns what
it accepted. Nothing here touches ``WorldState``.

Conventions:

* Items are checked in reply order. Items past a list cap are dropped with
  ``CAP_EXCEEDED`` (the cap is not in the schema; see
  ``aimpire.contracts.vocabulary``).
* A number outside its allowed range is ``CAP_EXCEEDED``; note 50's closed
  list has no separate "bad argument" reason.
* Anything the civilization does not know of (a place, a civilization, an
  entity) is ``UNKNOWN_ENTITY``, whether or not it exists, so a rejection
  never reveals unseen truth.
* An item whose text is empty is "not used" and skipped without a rejection.
* Over-long text is cut and flagged ``TEXT_TRUNCATED``; never a rejection.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from aimpire.contracts.mind import Belief, Commitment, Message, Name, Order, Policy
from aimpire.contracts.vocabulary import (
    ACTIVITIES,
    BELIEF_MAX_CHARS,
    COMMITMENT_KINDS,
    MAX_BELIEFS,
    MAX_COMMITMENTS,
    MAX_EVIDENCE_PER_BELIEF,
    MAX_MESSAGES,
    MAX_NAMES,
    MAX_ORDERS,
    MAX_RATION_PERMILLE,
    MESSAGE_MAX_CHARS,
    NAME_MAX_CHARS,
    ORDER_KINDS,
    ORDER_TEXT_MAX_CHARS,
    PERMILLE,
    VOICE,
)
from aimpire.sim.actions.decision import (
    AcceptedBelief,
    AcceptedCommitment,
    AcceptedMessage,
    AcceptedName,
    AcceptedOrder,
    CouncilSeat,
    Flagged,
    PolicyLine,
    Rejection,
    StandingPolicy,
)
from aimpire.sim.actions.outcomes import Flag, Reason

# A scouting party is 1 to 4 people (research note 50, `explore`).
SCOUT_MAX_PEOPLE: Final = 4


@dataclass(slots=True)
class Findings:
    """Rejections and flags gathered while checking one reply."""

    rejections: list[Rejection] = field(default_factory=list[Rejection])
    flags: list[Flagged] = field(default_factory=list[Flagged])

    def reject(self, where: str, reason: Reason) -> None:
        """Record that ``where`` was dropped for ``reason``."""
        self.rejections.append(Rejection(where, reason))

    def text(self, value: str, limit: int, where: str) -> str:
        """Return ``value`` cut to ``limit`` code points, flagging a cut."""
        if len(value) <= limit:
            return value
        self.flags.append(Flagged(where, Flag.TEXT_TRUNCATED))
        return value[:limit]


def _within_cap[T](items: Sequence[T], cap: int, name: str, out: Findings) -> list[tuple[int, T]]:
    """Index the first ``cap`` items; reject the rest with ``CAP_EXCEEDED``."""
    for index in range(cap, len(items)):
        out.reject(f"{name}[{index}]", Reason.CAP_EXCEEDED)
    return list(enumerate(items[:cap]))


def check_policy(policy: Policy, seat: CouncilSeat, out: Findings) -> StandingPolicy:
    """Return the policy in force after this reply.

    Empty allocations keep the current allocations and ration 0 keeps the
    current ration ("not used"). Any problem rejects the whole new policy and
    the previous one stays in force (ADR-0013 section 5).
    """
    local = Findings()
    lines: list[PolicyLine] = []
    seen: set[tuple[str, str]] = set()
    for i, a in enumerate(policy.allocations):
        where = f"policy.allocations[{i}]"
        if a.activity not in ACTIVITIES:
            local.reject(where, Reason.UNKNOWN_ACTION)
        elif a.place not in seat.known_places:
            local.reject(where, Reason.UNKNOWN_ENTITY)
        elif not 0 <= a.share <= PERMILLE:
            local.reject(where, Reason.CAP_EXCEEDED)
        elif (a.activity, a.place) in seen:
            local.reject(where, Reason.SCHEMA_INVALID)
        else:
            seen.add((a.activity, a.place))
            lines.append(PolicyLine(a.activity, a.place, a.share))
    if sum(line.share for line in lines) > PERMILLE:
        local.reject("policy.allocations", Reason.CAP_EXCEEDED)
    if not 0 <= policy.ration <= MAX_RATION_PERMILLE:
        local.reject("policy.ration", Reason.CAP_EXCEEDED)
    if local.rejections:
        out.rejections.extend(local.rejections)
        return seat.policy
    return StandingPolicy(
        allocations=tuple(lines) if policy.allocations else seat.policy.allocations,
        ration=policy.ration if policy.ration else seat.policy.ration,
    )


def _order_reason(order: Order, seat: CouncilSeat, reserved: int, moved: bool) -> Reason | None:
    """Why ``order`` cannot be accepted given labour already ``reserved``, or None."""
    if order.kind not in ORDER_KINDS:
        return Reason.UNKNOWN_ACTION
    if order.place not in seat.known_places or order.target:
        return Reason.UNKNOWN_ENTITY  # m0 orders name a place and no other entity
    if order.kind == "MOVE_CAMP":
        # One move per council, and it takes everyone: qty is 0 ("not used") or the head count.
        out_of_range = moved or order.qty not in (0, seat.people)
    else:
        top = SCOUT_MAX_PEOPLE if order.kind == "SCOUT" else seat.people
        out_of_range = not 1 <= order.qty <= max(top, 1)
    if out_of_range:
        return Reason.CAP_EXCEEDED
    if order.kind != "MOVE_CAMP" and reserved + order.qty > seat.people:
        return Reason.INSUFFICIENT_LABOR
    return None


def check_orders(
    orders: Sequence[Order], seat: CouncilSeat, out: Findings
) -> tuple[AcceptedOrder, ...]:
    """Accept orders in reply order against cumulative labour reservations."""
    accepted: list[AcceptedOrder] = []
    reserved = 0
    moved = False
    for i, order in _within_cap(orders, MAX_ORDERS, "orders", out):
        reason = _order_reason(order, seat, reserved, moved)
        if reason is not None:
            out.reject(f"orders[{i}]", reason)
            continue
        if order.kind == "MOVE_CAMP":
            moved = True
        else:
            reserved += order.qty
        text = out.text(order.text, ORDER_TEXT_MAX_CHARS, f"orders[{i}].text")
        accepted.append(AcceptedOrder(i, order.kind, order.place, order.target, order.qty, text))
    return tuple(accepted)


def check_messages(
    messages: Sequence[Message], seat: CouncilSeat, out: Findings
) -> tuple[AcceptedMessage, ...]:
    """Messages go to ``VOICE`` or a civilization this one knows. Text is only text."""
    accepted: list[AcceptedMessage] = []
    for i, message in _within_cap(messages, MAX_MESSAGES, "messages", out):
        if message.to != VOICE and (message.to not in seat.known_civs or message.to == seat.civ_id):
            out.reject(f"messages[{i}]", Reason.UNKNOWN_ENTITY)
        elif message.text:
            text = out.text(message.text, MESSAGE_MAX_CHARS, f"messages[{i}].text")
            accepted.append(AcceptedMessage(i, message.to, text))
    return tuple(accepted)


def _commitment_reason(c: Commitment, seat: CouncilSeat) -> Reason | None:
    if c.kind not in COMMITMENT_KINDS:
        return Reason.UNKNOWN_ACTION
    place_needed = c.kind == "BE_AT"
    if (c.place or place_needed) and c.place not in seat.known_places:
        return Reason.UNKNOWN_ENTITY
    if c.qty < (1 if c.kind == "STOCK_AT_LEAST" else 0):
        return Reason.CAP_EXCEEDED
    if c.by_council <= seat.council:
        return Reason.OUT_OF_RANGE  # a promise must fall due at a later council
    return None


def check_commitments(
    commitments: Sequence[Commitment], seat: CouncilSeat, out: Findings
) -> tuple[AcceptedCommitment, ...]:
    """Accept commitments the world can later check."""
    accepted: list[AcceptedCommitment] = []
    for i, c in _within_cap(commitments, MAX_COMMITMENTS, "commitments", out):
        reason = _commitment_reason(c, seat)
        if reason is None:
            accepted.append(AcceptedCommitment(i, c.kind, c.place, c.qty, c.by_council))
        else:
            out.reject(f"commitments[{i}]", reason)
    return tuple(accepted)


def check_beliefs(
    beliefs: Sequence[Belief], seat: CouncilSeat, out: Findings
) -> tuple[AcceptedBelief, ...]:
    """Beliefs must cite at least one evidence id shown in the observation."""
    accepted: list[AcceptedBelief] = []
    for i, belief in _within_cap(beliefs, MAX_BELIEFS, "beliefs", out):
        if not belief.statement:
            continue
        if len(belief.evidence) > MAX_EVIDENCE_PER_BELIEF:
            out.reject(f"beliefs[{i}]", Reason.CAP_EXCEEDED)
        elif not belief.evidence or any(e not in seat.evidence_ids for e in belief.evidence):
            out.reject(f"beliefs[{i}]", Reason.UNCITED_EVIDENCE)
        else:
            text = out.text(belief.statement, BELIEF_MAX_CHARS, f"beliefs[{i}].statement")
            accepted.append(AcceptedBelief(i, text, tuple(belief.evidence)))
    return tuple(accepted)


def check_names(
    names: Sequence[Name], seat: CouncilSeat, out: Findings
) -> tuple[AcceptedName, ...]:
    """Names apply to known places; one name per place per reply."""
    accepted: list[AcceptedName] = []
    named: set[str] = set()
    for i, entry in _within_cap(names, MAX_NAMES, "names", out):
        if entry.id not in seat.known_places:
            out.reject(f"names[{i}]", Reason.UNKNOWN_ENTITY)
        elif entry.id in named:
            out.reject(f"names[{i}]", Reason.SCHEMA_INVALID)
        elif entry.name:
            named.add(entry.id)
            text = out.text(entry.name, NAME_MAX_CHARS, f"names[{i}].name")
            accepted.append(AcceptedName(i, entry.id, text))
    return tuple(accepted)
