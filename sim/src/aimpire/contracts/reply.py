"""The mind's reply, contract ``m0`` (ADR-0013 section 3).

Shape rules, all enforced here and checked by the F5a acceptance tests:

* every field is required: no ``Optional``, no unions, no defaults. An empty
  string, zero or an empty list means "not used";
* unknown fields are rejected (``extra="forbid"``);
* numbers are integers; ``strict=True`` also refuses ``2.0``, ``True`` and ``"2"``.
  Shares, ration and quantities are integers so nothing a model writes can
  carry a float into the hashed state;
* no length, range or count keywords in the schema. Those caps are not
  supported by Anthropic structured output, so the validator enforces them
  (see ``aimpire.contracts.vocabulary``).

Class docstrings and field descriptions become the schema's ``description``
text, which providers show to the model. They are therefore short, neutral
(ADR-0019) and say only what a field means and its unit. Developer rationale
lives in this module docstring and in ``#`` comments.
"""

from pydantic import BaseModel, ConfigDict, Field

from aimpire.contracts.vocabulary import (
    ACTIVITIES,
    ANNAL_MAX_CHARS,
    COMMITMENT_KINDS,
    JOURNAL_MAX_CHARS,
    MAX_BELIEFS,
    MAX_COMMITMENTS,
    MAX_MESSAGES,
    MAX_NAMES,
    MAX_ORDERS,
    ORDER_KINDS,
    VOICE,
    words,
)


class Closed(BaseModel):
    """Base for every contract model: closed, strict, immutable."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Allocation(Closed):
    """A standing share of the workers given to one activity at one place."""

    activity: str = Field(description=f"One of: {words(ACTIVITIES)}.")
    place: str = Field(description="A place id from the observation, such as PL07.")
    share: int = Field(description="Permille of workers, 0 to 1000.")


class Policy(Closed):
    """Standing policy, in force until replaced. No allocations and ration 0 keep it as is."""

    allocations: list[Allocation] = Field(description="Shares must sum to at most 1000.")
    ration: int = Field(description="Daily ration in permille of a full ration; 1000 is full.")


class Order(Closed):
    """A one-off task."""

    kind: str = Field(description=f"One of: {words(ORDER_KINDS)}.")
    place: str = Field(description="A place id from the observation.")
    target: str = Field(description="An entity id, or empty when not used.")
    qty: int = Field(description="Number of people, or 0 when not used.")
    text: str = Field(description="A short note, or empty.")


class Message(Closed):
    """Text sent out of the council."""

    to: str = Field(description=f"Another civilization's id, or {VOICE}.")
    text: str = Field(description="The message text.")


class Commitment(Closed):
    """A promise the world can check by a given council."""

    kind: str = Field(description=f"One of: {words(COMMITMENT_KINDS)}.")
    place: str = Field(description="A place id, or empty when not used.")
    qty: int = Field(description="Amount in whole units, or 0 when not used.")
    by_council: int = Field(description="Council number by which it should hold.")


class Belief(Closed):
    """A statement and the evidence ids that support it."""

    statement: str = Field(description="The belief, in a sentence.")
    evidence: list[str] = Field(description="Event ids from the observation, such as EV0450.")


class Name(Closed):
    """A name the civilization gives to something it knows."""

    id: str = Field(description="A place id from the observation.")
    name: str = Field(description="The name.")


class MindReply(Closed):
    """One council's reply. Every field is required; empty means not used."""

    decision_id: str = Field(description="Copy the decision id from the observation.")
    policy: Policy
    orders: list[Order] = Field(description=f"At most {MAX_ORDERS}.")
    messages: list[Message] = Field(description=f"At most {MAX_MESSAGES}.")
    commitments: list[Commitment] = Field(description=f"At most {MAX_COMMITMENTS}.")
    beliefs: list[Belief] = Field(description=f"At most {MAX_BELIEFS}.")
    names: list[Name] = Field(description=f"Names for places; at most {MAX_NAMES}.")
    journal: str = Field(
        description=f"Your notes for the next council; at most {JOURNAL_MAX_CHARS} characters."
    )
    annal: str = Field(
        description=f"One line for the chronicle; at most {ANNAL_MAX_CHARS} characters."
    )
