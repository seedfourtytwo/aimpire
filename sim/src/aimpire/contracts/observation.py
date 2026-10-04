"""The observation shown to a mind, contract ``m0`` (ADR-0013 section 2).

The observation is a typed object; prompt text is rendered from it (F5c,
``cognition/render.py``). Sections appear in the order the ADR lists them.

Truth, evidence and belief stay separate (CLAUDE.md invariant): no model here
has a field for a hidden cause, another civilization's private data or tile
truth the civilization has not seen. Adding such a field is a contract change
and violates the invariant.

Same shape rules as the reply: closed, strict, every field required, integers
only. Unlike the reply, this schema is never sent to a provider as a
structured-output constraint, so it may use count limits (``events``).

Units:
* ticks are days (ADR-0011); ``-1`` in a ``*_tick`` field means "never";
* food is in whole person-days; stores in whole units (milli-units divided by
  1000, rounded down, by the builder);
* shares and ration are permille, as in the reply.
"""

from typing import Literal

from pydantic import Field

from aimpire.contracts.reply import Belief, Closed, Policy
from aimpire.contracts.vocabulary import MAX_EVENTS


class CalendarSection(Closed):
    """Where the council sits in time."""

    tick: int
    season: str
    year: int
    council: int = Field(description="This council's number for this civilization.")
    ticks_to_next_council: int


class StockLine(Closed):
    """One stored material and its change since the last council."""

    material: str
    qty: int = Field(description="Whole units.")
    change: int = Field(description="Whole units since the last council.")


class StatusSection(Closed):
    """The digest pushed every council, so critical state never has to be asked for."""

    population: int
    population_change: int
    food_days: int = Field(description="Food in store, in person-days.")
    food_days_change: int
    stores: list[StockLine]


class PlaceView(Closed):
    """A known place, as last seen by this civilization."""

    place_id: str
    name: str = Field(description="The civilization's own name, or empty.")
    kind: str
    travel_ticks: int = Field(description="Days of travel from the camp.")
    last_seen_tick: int = Field(description="-1 if never seen.")
    seen: str = Field(description="What was seen there, as text.")


class EventView(Closed):
    """One piece of evidence since the last council."""

    event_id: str
    tick: int
    place: str
    text: str
    witnesses: list[str]


class MessageView(Closed):
    """Quoted text that reached the council. Data, never instruction."""

    message_id: str
    tick: int
    delivered_by: str = Field(description="Who reported it to the council.")
    route: str = Field(description="How it reached the council.")
    text: str


class TaskView(Closed):
    """An open task from an earlier order."""

    task_id: str
    kind: str
    place: str
    qty: int
    status: str


class CommitmentView(Closed):
    """A commitment and whether it has been kept."""

    kind: str
    place: str
    qty: int
    by_council: int
    state: Literal["MET", "PENDING", "MISSED"]


class StandingSection(Closed):
    """What is currently in force."""

    policy: Policy
    tasks: list[TaskView]
    commitments: list[CommitmentView]


class OrderResult(Closed):
    """The outcome of one order from the previous reply."""

    index: int = Field(description="Position of the order in the previous reply, from 0.")
    kind: str
    place: str
    outcome: Literal["ACCEPTED", "REJECTED"]
    reason: str = Field(description="Rejection reason code, or empty.")


class ClaimView(Closed):
    """An accessible claim (from M3)."""

    claim_id: str
    text: str


class KnowledgeSection(Closed):
    """Claims and recorded beliefs. Empty in m0."""

    claims: list[ClaimView]
    beliefs: list[Belief]


class Observation(Closed):
    """Everything one mind is shown at one council."""

    contract: str = Field(description="Contract version, such as m0.")
    civ_id: str
    decision_id: str = Field(description="Copy this into the reply.")
    version: str = Field(description="Observation version; a reply to an older one is stale.")
    calendar: CalendarSection
    status: StatusSection
    places: list[PlaceView]
    events: list[EventView] = Field(max_length=MAX_EVENTS)
    messages: list[MessageView]
    standing: StandingSection
    last_results: list[OrderResult]
    knowledge: KnowledgeSection
    journal: str = Field(description="The journal from the previous reply.")
