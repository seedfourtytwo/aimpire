"""``OpenAICompatProvider``: the OpenAI-compatible chat completions API (ADR-0005, backlog F6a).

One adapter covers every server that speaks ``POST <base_url>/chat/completions``:

* Ollama, ``http://localhost:11434/v1`` (local, free, no key);
* llama.cpp ``llama-server``, ``http://localhost:8080/v1``;
* OpenRouter, ``https://openrouter.ai/api/v1`` (key in ``OPENROUTER_API_KEY``).

Structured output (``profile.structured_output``):

* ``json_schema``: ``response_format = {"type": "json_schema", "json_schema":
  {"name", "strict": true, "schema"}}``, the form OpenRouter documents and
  Ollama and llama.cpp accept;
* ``json_object``: ``{"type": "json_object"}`` plus the schema in the system
  message, for servers that only guarantee JSON;
* ``prompt``: the schema in the system message only (plain-JSON fallback).

The fallback is chosen in the profile, never on the fly: a silent switch
would change what the model was shown between two decisions of one run
(ADR-0014). Whatever comes back goes through ``parse_reply`` and the
validator, exactly as mock and rule replies do; nothing is repaired here.

Usage: ``prompt_tokens`` and ``completion_tokens``, with
``completion_tokens_details.reasoning_tokens`` as the reasoning part of the
completion (OpenRouter returns usage on every response). Cost is
``profile.price`` applied to that usage by the council (``Price.cost``).
When the server also states the cost (OpenRouter's ``usage.cost``), it is
kept as ``reported_cost_micro_usd`` for ``aimpire qualify`` to compare.

HTTP goes through ``httpx2``, the maintained continuation of httpx that the
Anthropic SDK is built on, so both adapters share one HTTP stack. Tests pass
an ``httpx2.MockTransport``; nothing here opens a socket unless a profile and
a key are given and ``complete`` is awaited.
"""

import json
import time
from dataclasses import replace
from typing import Any

import httpx2

from aimpire.cognition.live_common import (
    JSON_INSTRUCTION,
    as_int,
    estimate_micro_usd,
    failed,
    fallback_usage,
    max_output_tokens,
    reported_cost_micro_usd,
    schema_text,
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

SCHEMA_NAME = "mind_reply"


def _reported_cost(envelope: dict[str, Any]) -> int | None:
    """OpenRouter's own figure for the call (``usage.cost``), when the server sends one."""
    usage = envelope.get("usage")
    return reported_cost_micro_usd(usage.get("cost")) if isinstance(usage, dict) else None  # pyright: ignore[reportUnknownMemberType]


class OpenAICompatProvider:
    """A live model behind an OpenAI-compatible endpoint, configured by one profile."""

    def __init__(self, profile: Profile, *, transport: httpx2.AsyncBaseTransport | None = None):
        if profile.kind != "openai_compat":
            raise ValueError(f"profile {profile.name!r} is not an openai_compat profile")
        self._profile = profile
        self._transport = transport

    def __repr__(self) -> str:
        p = self._profile
        return f"OpenAICompatProvider(profile={p.name!r}, model={p.model!r}, url={p.base_url!r})"

    def describe(self) -> ModelIdentity:
        """The adapter kind and the pinned model id; servers here report no digest."""
        return ModelIdentity(provider="openai_compat", model=self._profile.model, digest="")

    def _instruction(self, req: CognitionRequest) -> str:
        """Schema text added to the system message in the fallback modes, else ""."""
        if self._profile.structured_output == "json_schema":
            return ""
        return f"\n\n{JSON_INSTRUCTION}\n{schema_text(req.reply_schema)}"

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        """Worst case of ``req`` at the profile's price; 0 for a free local model."""
        return estimate_micro_usd(req, self._profile, self._instruction(req))

    def request_body(self, req: CognitionRequest) -> dict[str, Any]:
        """The JSON body sent for ``req`` (public so ``qualify`` can store it for audit)."""
        p = self._profile
        body: dict[str, Any] = {
            "model": p.model,
            "messages": [
                {"role": "system", "content": req.system + self._instruction(req)},
                {"role": "user", "content": req.observation_text},
            ],
            "max_tokens": max_output_tokens(req, p),
            "stream": False,
        }
        if p.structured_output == "json_schema":
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": SCHEMA_NAME,
                    "strict": True,
                    "schema": dict(req.reply_schema),
                },
            }
        elif p.structured_output == "json_object":
            body["response_format"] = {"type": "json_object"}
        temperature = req.temperature if req.temperature is not None else p.temperature
        if temperature is not None:
            body["temperature"] = temperature
        return body

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        """Make one call. Every failure is a status; nothing is raised for a model failure."""
        p = self._profile
        start = time.perf_counter_ns()
        try:
            key = read_key(p)
        except MissingCredential as exc:
            return failed("error", p.model, start, str(exc))
        headers = {"Content-Type": "application/json"}
        if key is not None:
            headers["Authorization"] = f"Bearer {key}"
        body = self.request_body(req)
        try:
            async with httpx2.AsyncClient(
                transport=self._transport, timeout=httpx2.Timeout(timeout_s(req, p))
            ) as client:
                response = await client.post(
                    f"{p.base_url}/chat/completions",
                    content=json.dumps(body).encode("utf-8"),
                    headers=headers,
                )
        except httpx2.TimeoutException:
            # The server may still bill a call it finished after we stopped waiting.
            usage = fallback_usage(req, p, self._instruction(req))
            return failed("timeout", p.model, start, usage=usage)
        except httpx2.HTTPError as exc:
            return failed("error", p.model, start, scrub(type(exc).__name__, key))
        except Exception as exc:  # e.g. an ExceptionGroup from anyio: still one outcome
            return failed("error", p.model, start, scrub(type(exc).__name__, key))
        if response.status_code != httpx2.codes.OK:
            text = f"HTTP {response.status_code}: {response.text}"
            return failed("error", p.model, start, scrub(text, key))
        return self._result(req, response.text, start, key)

    def _usage(self, req: CognitionRequest, envelope: dict[str, Any]) -> Usage:
        usage = envelope.get("usage")
        if not isinstance(usage, dict):
            return fallback_usage(req, self._profile, self._instruction(req))
        details = usage.get("completion_tokens_details")  # pyright: ignore[reportUnknownMemberType]
        reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else 0  # pyright: ignore[reportUnknownMemberType]
        return split_usage(
            as_int(usage.get("prompt_tokens")),  # pyright: ignore[reportUnknownMemberType]
            as_int(usage.get("completion_tokens")),  # pyright: ignore[reportUnknownMemberType]
            as_int(reasoning),
        )

    def _result(
        self, req: CognitionRequest, text: str, start: int, key: str | None
    ) -> CognitionResult:
        """Classify a 200 response: refusal, truncation, or a reply for ``parse_reply``."""
        p = self._profile
        try:
            envelope = json.loads(text)
            choice = envelope["choices"][0]
            message = choice.get("message") or {}
        except ValueError, KeyError, IndexError, TypeError, AttributeError:
            # OpenRouter can send an error object with a 200 status.
            return failed("error", p.model, start, scrub(text, key))
        usage = self._usage(req, envelope)
        model = envelope.get("model") if isinstance(envelope.get("model"), str) else p.model
        content = message.get("content")
        content = content if isinstance(content, str) else ""
        refusal = message.get("refusal")
        finish = choice.get("finish_reason")
        if (isinstance(refusal, str) and refusal) or finish == "content_filter":
            reason = refusal if isinstance(refusal, str) and refusal else content
            result = failed("refusal", model, start, scrub(reason, key), usage)
        elif finish == "length":
            result = failed("truncated", model, start, content, usage)
        else:
            parsed, status = parse_reply(content)
            result = CognitionResult(
                raw_text=content,
                parsed=parsed,
                status=status,
                usage=usage,
                model_reported=model,
                latency_ms=elapsed_ms(start, time.perf_counter_ns()),
                attempts=1,
            )
        return replace(result, reported_cost_micro_usd=_reported_cost(envelope))
