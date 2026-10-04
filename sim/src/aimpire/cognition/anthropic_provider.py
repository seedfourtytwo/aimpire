"""``AnthropicProvider``: the Claude Messages API through the official SDK (ADR-0005, backlog F6b).

Checked against the current documentation on 2026-10-04 (anthropic 1.11.0):

* Structured output is ``output_config = {"format": {"type": "json_schema",
  "schema": ...}}`` on ``messages.create``; no beta header. The older
  ``output_format`` parameter is deprecated. The reply is JSON text in the
  response's text block. The SDK's ``create`` passes the schema as given, and
  the m0 contract already fits the documented limits: every object has
  ``additionalProperties: false`` and there are no min/max keywords.
* ``stop_reason`` ``"refusal"`` is a ``REFUSAL`` (the text may not match the
  schema); ``"max_tokens"`` and ``"model_context_window_exceeded"`` are
  ``TRUNCATED``.
* ``usage.output_tokens`` is the inclusive, billed output total;
  ``usage.output_tokens_details.thinking_tokens`` is the reasoning part of it.
  Cache read and write tokens, if any, are charged here at the full input
  price (an over-count; this adapter does not use prompt caching).
* ``temperature`` is deprecated: models after Claude Opus 4.6 accept only 1.0.
  The SDK's ``create`` no longer lists it, so a profile that sets one sends it
  through ``extra_body``. ``output_config.effort`` is sent when set.
* Errors: ``APITimeoutError`` (a subclass of ``APIConnectionError``) is a
  timeout; every other ``APIError`` is a provider error. The SDK retries
  twice by default; this adapter sets ``max_retries=0`` so a decision is one
  attempt with one latency and one charge (ADR-0014).

The key is read from the environment at call time and handed straight to a
client built for that call; it is never stored on the provider. Tests inject
``client_factory`` to supply a fake client; nothing here touches the network
unless ``complete`` is awaited with a real key.
"""

import time
from collections.abc import Callable
from typing import Any

import anthropic

from aimpire.cognition.live_common import (
    as_int,
    estimate_micro_usd,
    failed,
    fallback_usage,
    max_output_tokens,
    scrub,
    split_usage,
    timeout_s,
)
from aimpire.cognition.profiles import MissingCredential, Profile, read_key
from aimpire.cognition.protocol import (
    CognitionRequest,
    CognitionResult,
    ModelIdentity,
    Usage,
    elapsed_ms,
    parse_reply,
)

# Builds a client for one call from the key; returns an object with
# ``messages.create`` (``anthropic.AsyncAnthropic`` or a test double).
ClientFactory = Callable[[str], Any]
_TRUNCATED = frozenset({"max_tokens", "model_context_window_exceeded"})


class AnthropicProvider:
    """A Claude model through the official SDK, configured by one profile."""

    def __init__(self, profile: Profile, *, client_factory: ClientFactory | None = None):
        if profile.kind != "anthropic":
            raise ValueError(f"profile {profile.name!r} is not an anthropic profile")
        self._profile = profile
        self._factory = client_factory

    def __repr__(self) -> str:
        return f"AnthropicProvider(profile={self._profile.name!r}, model={self._profile.model!r})"

    def describe(self) -> ModelIdentity:
        """The adapter kind and the pinned model id (the API reports no digest)."""
        return ModelIdentity(provider="anthropic", model=self._profile.model, digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        """Worst case of ``req``: bounded input plus the full output cap (thinking included)."""
        return estimate_micro_usd(req, self._profile)

    def _client(self, key: str, req: CognitionRequest) -> Any:
        if self._factory is not None:
            return self._factory(key)
        return anthropic.AsyncAnthropic(
            api_key=key,
            base_url=self._profile.base_url,
            max_retries=0,
            timeout=timeout_s(req, self._profile),
        )

    def request_params(self, req: CognitionRequest) -> dict[str, Any]:
        """The ``messages.create`` arguments for ``req`` (public so ``qualify`` can store them)."""
        p = self._profile
        output_config: dict[str, Any] = {
            "format": {"type": "json_schema", "schema": dict(req.reply_schema)}
        }
        effort = req.effort if req.effort is not None else p.effort
        if effort is not None:
            output_config["effort"] = effort
        params: dict[str, Any] = {
            "model": p.model,
            "max_tokens": max_output_tokens(req, p),
            "system": req.system,
            "messages": [{"role": "user", "content": req.observation_text}],
            "output_config": output_config,
            "timeout": timeout_s(req, p),
        }
        temperature = req.temperature if req.temperature is not None else p.temperature
        if temperature is not None:
            params["extra_body"] = {"temperature": temperature}
        return params

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        """Make one call. Every failure is a status; nothing is raised for a model failure."""
        p = self._profile
        start = time.perf_counter_ns()
        try:
            key = read_key(p)
        except MissingCredential as exc:
            return failed("error", p.model, start, str(exc))
        if key is None:  # the loader requires a key for remote endpoints; be explicit anyway
            return failed("error", p.model, start, f"profile {p.name!r} names no api_key_env")
        outcome = await self._send(req, key, start)
        if isinstance(outcome, CognitionResult):
            return outcome
        return self._result(req, outcome, start, key)

    async def _send(self, req: CognitionRequest, key: str, start: int) -> Any:
        """The SDK message, or a failed result for a timeout or an API error."""
        p = self._profile
        client = self._client(key, req)
        try:
            return await client.messages.create(**self.request_params(req))
        except anthropic.APITimeoutError:
            return failed("timeout", p.model, start, usage=fallback_usage(req, p))
        except anthropic.APIStatusError as exc:
            text = f"HTTP {exc.status_code}: {type(exc).__name__}: {exc.message}"
            return failed("error", p.model, start, scrub(text, key))
        except anthropic.APIError as exc:
            return failed("error", p.model, start, scrub(f"{type(exc).__name__}: {exc}", key))
        except Exception as exc:  # a broken client or SDK change: still one outcome, no crash
            return failed("error", p.model, start, scrub(type(exc).__name__, key))
        finally:
            close = getattr(client, "close", None)
            if self._factory is None and close is not None:
                await close()

    def _usage(self, req: CognitionRequest, message: Any) -> Usage:
        usage = getattr(message, "usage", None)
        if usage is None:
            return fallback_usage(req, self._profile)
        details = getattr(usage, "output_tokens_details", None)
        thinking = getattr(details, "thinking_tokens", 0) if details is not None else 0
        input_tokens = (
            as_int(getattr(usage, "input_tokens", 0))
            + as_int(getattr(usage, "cache_creation_input_tokens", 0))
            + as_int(getattr(usage, "cache_read_input_tokens", 0))
        )
        return split_usage(
            input_tokens, as_int(getattr(usage, "output_tokens", 0)), as_int(thinking)
        )

    def _result(self, req: CognitionRequest, message: Any, start: int, key: str) -> CognitionResult:
        """Classify a response by ``stop_reason``; a full reply goes to ``parse_reply``."""
        p = self._profile
        usage = self._usage(req, message)
        model = getattr(message, "model", None)
        model = model if isinstance(model, str) and model else p.model
        blocks = getattr(message, "content", None) or []
        text = "".join(
            b.text for b in blocks if getattr(b, "type", "") == "text" and isinstance(b.text, str)
        )
        stop_reason = getattr(message, "stop_reason", None)
        if stop_reason == "refusal":
            return failed("refusal", model, start, scrub(text, key), usage)
        if stop_reason in _TRUNCATED:
            return failed("truncated", model, start, text, usage)
        parsed, status = parse_reply(text)
        return CognitionResult(
            raw_text=text,
            parsed=parsed,
            status=status,
            usage=usage,
            model_reported=model,
            latency_ms=elapsed_ms(start, time.perf_counter_ns()),
            attempts=1,
        )
