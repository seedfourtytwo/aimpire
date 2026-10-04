"""Offline providers: mock fixtures, rule baselines and recorded replay (ADR-0005).

These are the only providers tests and CI use. None of them touches the
network, and none of them makes up a reply: when there is nothing to give back
for a decision id, the result is ``status="error"`` with empty text. A made-up
reply would be a fabricated decision in the record (CLAUDE.md: no fabricated
emergence).

All three cost nothing, so ``estimate_max_cost_micro_usd`` returns 0 (a known
price of zero, not ``None`` for unknown).
"""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from aimpire.cognition.protocol import (
    NO_USAGE,
    CognitionRequest,
    CognitionResult,
    ModelIdentity,
    Status,
    elapsed_ms,
    parse_reply,
)
from aimpire.cognition.recording import result_from_record
from aimpire.contracts.mind import MindReply, Observation


def _error(start_ns: int, model: str) -> CognitionResult:
    """The result for "nothing to give back": no text, no parse, no usage."""
    return CognitionResult(
        raw_text="",
        parsed=None,
        status="error",
        usage=NO_USAGE,
        model_reported=model,
        latency_ms=elapsed_ms(start_ns, time.perf_counter_ns()),
        attempts=1,
    )


@dataclass(frozen=True, slots=True)
class MockFailure:
    """A scripted non-reply for a mock fixture: refusal, timeout, truncation or error."""

    status: Status
    raw_text: str = ""


class MockProvider:
    """Replies from a fixture ``{decision_id: raw text | MockFailure}``.

    Raw text is classified exactly as live text would be (``parse_reply``), so a
    fixture can hold malformed replies to exercise the validator.
    """

    def __init__(self, replies: Mapping[str, str | MockFailure], model: str = "mock") -> None:
        self._replies = dict(replies)
        self._model = model

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        """Return the fixture reply for ``req.decision_id``, or an error if there is none."""
        start = time.perf_counter_ns()
        scripted = self._replies.get(req.decision_id)
        if scripted is None:
            return _error(start, self._model)
        if isinstance(scripted, MockFailure):
            raw_text, parsed, status = scripted.raw_text, None, scripted.status
        else:
            raw_text = scripted
            parsed, status = parse_reply(raw_text)
        return CognitionResult(
            raw_text=raw_text,
            parsed=parsed,
            status=status,
            usage=NO_USAGE,
            model_reported=self._model,
            latency_ms=elapsed_ms(start, time.perf_counter_ns()),
            attempts=1,
        )

    def describe(self) -> ModelIdentity:
        """Identify as the mock provider."""
        return ModelIdentity(provider="mock", model=self._model, digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        """Fixtures cost nothing."""
        return 0


RulePolicy = Callable[[Observation], MindReply]


class RuleProvider:
    """A scripted baseline (ADR-0008 traits configure these) behind the same interface.

    The rule's ``MindReply`` is serialised to JSON and parsed back with the same
    ``parse_reply`` live text goes through, so baselines and models reach the
    validator by the exact same path. If the rule raises, the result is an
    error; no fallback reply is substituted.
    """

    def __init__(self, policy: RulePolicy, name: str) -> None:
        self._policy = policy
        self._name = name

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        """Run the rule on the typed observation and report its reply as text."""
        start = time.perf_counter_ns()
        model = f"rule:{self._name}"
        try:
            reply = self._policy(req.observation)
        except Exception:  # a broken baseline is an error outcome, not a crash of the run
            return _error(start, model)
        raw_text = reply.model_dump_json()
        parsed, status = parse_reply(raw_text)
        return CognitionResult(
            raw_text=raw_text,
            parsed=parsed,
            status=status,
            usage=NO_USAGE,
            model_reported=model,
            latency_ms=elapsed_ms(start, time.perf_counter_ns()),
            attempts=1,
        )

    def describe(self) -> ModelIdentity:
        """Identify as a rule baseline."""
        return ModelIdentity(provider="rule", model=self._name, digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        """Rules cost nothing."""
        return 0


class RecordedProvider:
    """Replays stored results keyed by decision id, raw text byte for byte.

    Everything comes from the record, latency included, so a replayed run
    reports what the original run measured. Records are validated when the
    provider is built, so a corrupt recording fails before the run starts.
    """

    def __init__(self, records: Mapping[str, Mapping[str, Any]], label: str = "recorded") -> None:
        self._results = {key: result_from_record(rec) for key, rec in sorted(records.items())}
        self._label = label

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        """Return the stored result, or an error if this decision was never recorded."""
        result = self._results.get(req.decision_id)
        if result is None:
            return _error(time.perf_counter_ns(), self._label)
        return result

    def describe(self) -> ModelIdentity:
        """Identify as a replay; each result still carries the original ``model_reported``."""
        return ModelIdentity(provider="recorded", model=self._label, digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        """Replay costs nothing."""
        return 0
