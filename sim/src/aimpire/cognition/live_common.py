"""What the live adapters share: worst-case bounds, usage fallbacks, failure results, scrubbing.

Worst-case input tokens are bounded by **UTF-8 bytes**, not by a tokenizer.
Byte-level BPE tokenizers (the GPT, Llama, Qwen and Claude families) never
produce more tokens than input bytes, so ``bytes + overhead`` is a true upper
bound that needs no tokenizer and no network. It over-reserves by roughly
three to four times, which only matters near a cap, and the reservation is
released and replaced by the actual cost after the call (``budget.settle``).

When a priced endpoint reports no usage, the call is charged as its worst
case (``fallback_usage``). Charging zero would under-count spend and let a
run cross its cap; charging the worst case can only over-count.

Error text from a provider is kept for audit (``raw_text`` of an ``error``
result), but only after ``scrub`` removes the key itself. The run store
redacts again (``persistence.blobs.redact``), but that pass only knows
variables named ``*API_KEY`` and similar; a profile may name any variable,
so the adapter removes the value it actually used.
"""

import json
import time
from collections.abc import Mapping
from typing import Any, Final

from aimpire.cognition.profiles import Profile
from aimpire.cognition.protocol import (
    NO_USAGE,
    CognitionRequest,
    CognitionResult,
    Status,
    Usage,
    elapsed_ms,
)

REDACTED: Final = "[REDACTED]"
ERROR_TEXT_MAX_CHARS: Final = 2000
# Chat templates add role markers and separators around each message; this
# allowance per call is generous for every template we know of.
TEMPLATE_OVERHEAD_TOKENS: Final = 256
JSON_INSTRUCTION: Final = "Reply with one JSON object that matches this JSON schema:"


def schema_text(schema: Mapping[str, Any]) -> str:
    """The reply schema as compact, stable JSON text (sorted keys)."""
    return json.dumps(schema, sort_keys=True, separators=(",", ":"))


def max_output_tokens(req: CognitionRequest, profile: Profile) -> int:
    """The output cap actually sent: the smaller of the request's and the profile's."""
    return max(1, min(req.max_output_tokens, profile.max_output_tokens))


def timeout_s(req: CognitionRequest, profile: Profile) -> float:
    """The per-call timeout actually used: the smaller of the request's and the profile's."""
    return min(req.timeout_s, profile.timeout_s)


def input_token_bound(req: CognitionRequest, *extra: str) -> int:
    """An upper bound on the input tokens of ``req``: UTF-8 bytes of everything sent."""
    texts = (req.system, req.observation_text, schema_text(req.reply_schema), *extra)
    return sum(len(t.encode("utf-8")) for t in texts) + TEMPLATE_OVERHEAD_TOKENS


def estimate_micro_usd(req: CognitionRequest, profile: Profile, *extra: str) -> int:
    """Worst-case cost of ``req`` in micro-dollars: bounded input plus the full output cap."""
    return profile.price.worst_case(input_token_bound(req, *extra), max_output_tokens(req, profile))


def fallback_usage(req: CognitionRequest, profile: Profile, *extra: str) -> Usage:
    """Usage to charge when a priced endpoint reported none: the worst case (fail closed)."""
    if profile.price.input_micro_usd_per_mtok == profile.price.output_micro_usd_per_mtok == 0:
        return NO_USAGE
    return Usage(
        input_tokens=input_token_bound(req, *extra),
        output_tokens=max_output_tokens(req, profile),
        reasoning_tokens=0,
    )


def split_usage(input_tokens: int, output_tokens: int, reasoning_tokens: int) -> Usage:
    """Usage from an inclusive output count: reasoning is billed as output, never twice.

    Both APIs report reasoning (thinking) tokens as a part of the output total,
    while ``Usage`` keeps them apart and ``Price.cost`` adds them back.
    """
    reasoning = max(0, min(reasoning_tokens, output_tokens))
    return Usage(
        input_tokens=max(0, input_tokens),
        output_tokens=max(0, output_tokens) - reasoning,
        reasoning_tokens=reasoning,
    )


def as_int(value: object) -> int:
    """A reported token count as an int; anything that is not a whole number counts as 0."""
    if type(value) is int:
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return 0


def scrub(text: str, secret: str | None) -> str:
    """``text`` without ``secret`` (raw or JSON-escaped), cut to a bounded length."""
    if secret:
        text = text.replace(secret, REDACTED)
        escaped = json.dumps(secret)[1:-1]
        if escaped != secret:
            text = text.replace(escaped, REDACTED)
    return text[:ERROR_TEXT_MAX_CHARS]


def failed(
    status: Status, model: str, start_ns: int, raw_text: str = "", usage: Usage = NO_USAGE
) -> CognitionResult:
    """A result with no usable reply: ``timeout``, ``error``, ``refusal`` or ``truncated``.

    ``usage`` is what the call still cost: a refused or truncated reply was billed.
    """
    return CognitionResult(
        raw_text=raw_text,
        parsed=None,
        status=status,
        usage=usage,
        model_reported=model,
        latency_ms=elapsed_ms(start_ns, time.perf_counter_ns()),
        attempts=1,
    )
