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

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic.config import JsonDict

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


def one_of(words_: frozenset[str]) -> JsonDict:
    """Schema extra that lists the allowed words as a JSON-schema ``enum``.

    Why: a description in prose does not bind a model. With the ``enum`` in the
    schema, providers that constrain decoding to the schema (Ollama, OpenAI,
    Anthropic structured output) can only produce a listed word. The Python type
    stays ``str`` on purpose: a word from a provider that does not constrain is
    still reported by the validator as ``UNKNOWN_ACTION``, a closed reason
    (ADR-0013), not as a schema failure.
    """
    allowed: list[JsonValue] = list(sorted(words_))
    return {"enum": allowed}


class Closed(BaseModel):
    """Base for every contract model: closed, strict, immutable."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Allocation(Closed):
    """A standing share of the workers given to one activity at one place."""

    activity: str = Field(
        description=f"One of: {words(ACTIVITIES)}.", json_schema_extra=one_of(ACTIVITIES)
    )
    place: str = Field(description="A place id from the observation, such as PL07.")
    share: int = Field(description="Permille of workers, 0 to 1000.")


class Policy(Closed):
    """Standing policy, in force until replaced. No allocations and ration 0 keep it as is."""

    allocations: list[Allocation] = Field(description="Shares must sum to at most 1000.")
    ration: int = Field(description="Daily ration in permille of a full ration; 1000 is full.")


class Order(Closed):
    """A one-off task."""

    kind: str = Field(
        description=f"One of: {words(ORDER_KINDS)}.", json_schema_extra=one_of(ORDER_KINDS)
    )
    place: str = Field(description="A place id from the observation.")
    # No m0 order kind takes a target, so the m0 schema allows only "". A small
    # model filled it with a place id on every order in a live year (all rejected
    # UNKNOWN_ENTITY); the validator still rejects a non-empty target from a
    # provider that does not constrain decoding (acceptance test F5d).
    target: str = Field(
        description="Not used by any order in this contract; leave empty.",
        json_schema_extra=one_of(frozenset({""})),
    )
    qty: int = Field(description="Number of people, or 0 when not used.")
    text: str = Field(description="A short note, or empty.")


class Message(Closed):
    """Text sent out of the council."""

    to: str = Field(description=f"Another civilization's id, or {VOICE}.")
    text: str = Field(description="The message text.")


class Commitment(Closed):
    """A promise the world can check by a given council."""

    kind: str = Field(
        description=f"One of: {words(COMMITMENT_KINDS)}.",
        json_schema_extra=one_of(COMMITMENT_KINDS),
    )
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
