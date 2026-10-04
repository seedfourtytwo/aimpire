"""Validate a mind's reply into one decision record (ADR-0013 sections 5 and 8).

Pure and deterministic: no I/O, no clock, no randomness. The only thing it
changes is the ``DecisionLog`` passed in, which lives outside ``WorldState``.
The state is read (for the tick) and never written, so validating any reply,
however malformed, leaves the state hash unchanged. The world changes later,
and only through the accepted items of the returned record.

Pipeline (research note 50 section 3, ADR-0013 section 5):

0. **Duplicate decision id** → the stored record, unchanged; nothing appended.
   Note 50 lists this check fourth. It runs first here because the key is
   the id the seat issued, which needs no parsing, and because checking it
   later would let a malformed or late re-delivery append a second record
   for the same decision. That breaks "exactly one outcome per decision" and
   idempotency.
1. **Schema**: the strict m0 contract. Failure → ``INVALID`` / ``SCHEMA_INVALID``.
2. **Civilization and decision id**: the caller's civ and the echoed id must
   match the seat. Failure → ``INVALID`` / ``UNAUTHORIZED``.
3. **Observation version**: must be the seat's current version. Failure →
   ``INVALID`` / ``STALE_OBSERVATION``.
4. **Items**: the policy, then orders in reply order against cumulative
   reservations, then messages, commitments, beliefs, names, journal and
   annal (``aimpire.sim.actions.checks``). Invalid items are dropped with a
   reason and the rest are kept: ``PARTIAL`` if anything was dropped, else
   ``VALID``.

Provider failures (refusal, truncation, timeout, error, budget, unparseable
text) never reach this pipeline. ``record_failure`` records them.
"""

from collections.abc import Mapping
from typing import Final, cast

from pydantic import ValidationError

from aimpire.contracts.mind import CONTRACT_VERSION, MindReply
from aimpire.contracts.vocabulary import (
    ANNAL_MAX_CHARS,
    DECISION_ID_MAX_CHARS,
    JOURNAL_MAX_CHARS,
)
from aimpire.sim.actions.checks import (
    Findings,
    check_beliefs,
    check_commitments,
    check_messages,
    check_names,
    check_orders,
    check_policy,
)
from aimpire.sim.actions.decision import (
    CouncilSeat,
    Decision,
    DecisionLog,
    DecisionRecord,
    Rejection,
)
from aimpire.sim.actions.outcomes import Outcome, Reason
from aimpire.sim.state import WorldState

# Outcomes ``record_failure`` accepts, and the note-50 reason each one carries.
# Refusal, truncation and provider errors have no reason in the closed list;
# the outcome itself says what happened.
_FAILURE_REASONS: Final[dict[Outcome, tuple[Reason, ...]]] = {
    Outcome.INVALID: (Reason.PARSE_FAILED,),
    Outcome.REFUSAL: (),
    Outcome.TRUNCATED: (),
    Outcome.TIMEOUT: (Reason.TIMEOUT,),
    Outcome.PROVIDER_ERROR: (),
    Outcome.BUDGET: (Reason.BUDGET_EXHAUSTED,),
}


def _empty(
    state: WorldState,
    seat: CouncilSeat,
    observation_version: str,
    outcome: Outcome,
    rejections: tuple[Rejection, ...],
) -> DecisionRecord:
    """A record in which nothing from the reply was applied."""
    return DecisionRecord(
        decision_id=seat.decision_id,
        civ_id=seat.civ_id,
        council=seat.council,
        tick=state.tick,
        contract=CONTRACT_VERSION,
        observation_version=observation_version,
        outcome=outcome,
        policy=seat.policy,
        orders=(),
        messages=(),
        commitments=(),
        beliefs=(),
        names=(),
        journal="",
        annal="",
        rejections=rejections,
        flags=(),
    )


def _commit(log: DecisionLog, record: DecisionRecord) -> DecisionRecord:
    log.append(record)
    return record


def _parse(reply: object) -> tuple[MindReply | None, str]:
    """Parse with the strict contract. Returns ``(reply, "")`` or ``(None, where)``."""
    if not isinstance(reply, Mapping):
        return None, ""
    try:
        parsed = MindReply.model_validate(dict(cast(Mapping[str, object], reply)))
    except ValidationError as error:
        first = error.errors()[0]["loc"] if error.error_count() else ()
        return None, ".".join(str(part) for part in first)
    except TypeError, ValueError:
        return None, ""
    if len(parsed.decision_id) > DECISION_ID_MAX_CHARS:
        return None, "decision_id"
    return parsed, ""


# Six parameters on purpose: the four positional ones are the request facts the
# backlog names, and the two keyword-only ones are the seat and the log. Bundling
# them would hide which inputs come from the model and which from the world.
def validate_reply(  # noqa: PLR0913
    state: WorldState,
    civ_id: str,
    observation_version: str,
    reply: object,
    *,
    seat: CouncilSeat,
    log: DecisionLog,
) -> Decision:
    """Validate ``reply`` for ``seat`` and append the resulting record to ``log``.

    ``civ_id`` is the civilization the reply was delivered for and
    ``observation_version`` the version it answers; both come from the
    request, not from the model. ``reply`` is normally the JSON object a
    provider parsed, but anything is accepted and judged. Returns the record,
    or the stored one if this decision was already recorded.
    """
    stored = log.get(seat.decision_id)
    if stored is not None:
        return stored
    parsed, where = _parse(reply)
    if parsed is None:
        rejection = (Rejection(where, Reason.SCHEMA_INVALID),)
        return _commit(log, _empty(state, seat, observation_version, Outcome.INVALID, rejection))
    if civ_id != seat.civ_id or parsed.decision_id != seat.decision_id:
        rejection = (Rejection("decision_id", Reason.UNAUTHORIZED),)
        return _commit(log, _empty(state, seat, observation_version, Outcome.INVALID, rejection))
    if observation_version != seat.observation_version:
        rejection = (Rejection("", Reason.STALE_OBSERVATION),)
        return _commit(log, _empty(state, seat, observation_version, Outcome.INVALID, rejection))

    out = Findings()
    policy = check_policy(parsed.policy, seat, out)
    orders = check_orders(parsed.orders, seat, out)
    messages = check_messages(parsed.messages, seat, out)
    commitments = check_commitments(parsed.commitments, seat, out)
    beliefs = check_beliefs(parsed.beliefs, seat, out)
    names = check_names(parsed.names, seat, out)
    journal = out.text(parsed.journal, JOURNAL_MAX_CHARS, "journal")
    annal = out.text(parsed.annal, ANNAL_MAX_CHARS, "annal")
    record = DecisionRecord(
        decision_id=seat.decision_id,
        civ_id=seat.civ_id,
        council=seat.council,
        tick=state.tick,
        contract=CONTRACT_VERSION,
        observation_version=observation_version,
        outcome=Outcome.PARTIAL if out.rejections else Outcome.VALID,
        policy=policy,
        orders=orders,
        messages=messages,
        commitments=commitments,
        beliefs=beliefs,
        names=names,
        journal=journal,
        annal=annal,
        rejections=tuple(out.rejections),
        flags=tuple(out.flags),
    )
    return _commit(log, record)


def record_failure(  # noqa: PLR0913 (same inputs as validate_reply)
    state: WorldState,
    civ_id: str,
    observation_version: str,
    outcome: Outcome,
    *,
    seat: CouncilSeat,
    log: DecisionLog,
) -> Decision:
    """Record a decision that produced no usable reply.

    ``outcome`` is one of ``REFUSAL``, ``TRUNCATED``, ``TIMEOUT``,
    ``PROVIDER_ERROR``, ``BUDGET``, or ``INVALID`` for text that was not JSON
    (``PARSE_FAILED``). Nothing is substituted for the missing reply: the
    previous policy stays and no orders are accepted (ADR-0014: refusals are
    counted, never silently replaced). Idempotent like ``validate_reply``.
    """
    if outcome not in _FAILURE_REASONS:
        raise ValueError(f"{outcome} is not a failure outcome; use validate_reply")
    stored = log.get(seat.decision_id)
    if stored is not None:
        return stored
    if civ_id != seat.civ_id:
        raise ValueError(f"civilization {civ_id!r} does not hold seat {seat.decision_id!r}")
    rejections = tuple(Rejection("", reason) for reason in _FAILURE_REASONS[outcome])
    return _commit(log, _empty(state, seat, observation_version, outcome, rejections))
