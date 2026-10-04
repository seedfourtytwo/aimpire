"""The provider protocol: what the council barrier sends and gets back (ADR-0005).

A provider turns one ``CognitionRequest`` into one ``CognitionResult``. It does
not validate the reply against the world; that is ``aimpire.sim.actions``. It
only reports what came back and how: the raw text exactly as received, a
parsed JSON object when there is one, and a status.

Why these types live outside the simulation: they hold wall-clock latency,
token counts and request settings (``timeout_s``, ``temperature``) that are
floats or vary between runs. None of that may enter the hashed state.
Everything in ``CognitionResult`` that a later step might copy into state
(usage, latency, attempts) is an ``int``; ``parsed`` is the model's JSON and
still has to pass the strict contract, which rejects floats.

``asyncio`` is used here only; ``aimpire.sim`` never imports this package.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, Literal, Protocol, runtime_checkable

from pydantic import ValidationError

from aimpire.contracts.mind import MindReply, Observation

Status = Literal["ok", "schema_fail", "refusal", "timeout", "truncated", "error"]
STATUSES: Final[frozenset[str]] = frozenset(
    {"ok", "schema_fail", "refusal", "timeout", "truncated", "error"}
)


@dataclass(frozen=True, slots=True)
class Usage:
    """Token counts reported by the provider. Reasoning tokens count toward output caps."""

    input_tokens: int
    output_tokens: int
    reasoning_tokens: int


NO_USAGE: Final = Usage(input_tokens=0, output_tokens=0, reasoning_tokens=0)


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    """Who answered: provider kind, resolved model id and digest ("" when none)."""

    provider: str
    model: str
    digest: str


@dataclass(frozen=True, slots=True)
class CognitionRequest:
    """One council turn for one civilization, ready to send.

    ``observation`` is the typed object that ``observation_text`` was rendered
    from. Live providers send only the text; ``RuleProvider`` reads the object,
    so rule baselines see the same information as models without re-parsing
    prose. ``effort`` and ``temperature`` are ``None`` unless a profile sets
    them (ADR-0014: no provider default is left implicit, and some models
    reject a temperature).
    """

    decision_id: str
    civ_id: str
    contract: str
    system: str
    observation: Observation
    observation_text: str
    reply_schema: Mapping[str, Any]
    max_output_tokens: int
    timeout_s: float
    effort: str | None
    temperature: float | None


@dataclass(frozen=True, slots=True)
class CognitionResult:
    """What came back. ``latency_ms`` is wall-clock and never enters world state.

    ``parsed`` is the JSON object in ``raw_text`` when the text is one, even if
    it fails the contract (``schema_fail``), so the validator can record why.
    It is ``None`` when the text is not a JSON object or the call failed.

    ``reported_cost_micro_usd`` is what the provider itself said the call cost
    (OpenRouter's ``usage.cost``), rounded up to whole micro-dollars; ``None``
    when it said nothing. It is reported beside the profile-priced cost and is
    never what the budget charges, so a provider cannot talk a cap down.
    """

    raw_text: str
    parsed: dict[str, Any] | None
    status: Status
    usage: Usage
    model_reported: str
    latency_ms: int
    attempts: int
    reported_cost_micro_usd: int | None = None


@runtime_checkable
class Provider(Protocol):
    """Any source of mind replies: mock, rule, recorded, or (F6) a live model."""

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        """Answer one request. Never raises for a model failure; reports a status."""
        ...

    def describe(self) -> ModelIdentity:
        """Identify the provider and resolved model, for the decision record."""
        ...

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        """Upper bound on the cost of ``req`` in millionths of a US dollar; None if unpriced."""
        ...


def _no_constants(name: str) -> object:
    # JSON has no NaN or Infinity; Python's json accepts them by default.
    raise ValueError(f"non-standard JSON constant {name}")


def parse_reply(raw_text: str) -> tuple[dict[str, Any] | None, Status]:
    """Parse raw model text and classify it against the contract.

    Returns ``(parsed, status)``: ``status`` is ``"ok"`` when the text is a JSON
    object that passes ``MindReply``, else ``"schema_fail"``. ``parsed`` is the
    JSON object when there is one. Floats are kept as parsed so the record
    shows what the model wrote; the strict contract rejects them.
    """
    try:
        value: object = json.loads(raw_text, parse_constant=_no_constants)
    except ValueError:
        return None, "schema_fail"
    if not isinstance(value, dict):
        return None, "schema_fail"
    parsed: dict[str, Any] = value  # pyright: ignore[reportUnknownVariableType]
    try:
        MindReply.model_validate(parsed)
    except ValidationError:
        return parsed, "schema_fail"
    return parsed, "ok"


def elapsed_ms(start_ns: int, end_ns: int) -> int:
    """Whole milliseconds between two ``perf_counter_ns`` readings, rounded up (integer math)."""
    return max(0, -(-(end_ns - start_ns) // 1_000_000))
