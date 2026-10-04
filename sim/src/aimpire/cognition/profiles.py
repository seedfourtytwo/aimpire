"""Model profiles: named TOML files in ``profiles/`` that pin one live model (ADR-0005, ADR-0014).

A profile says which endpoint and model to call, how (timeout, output cap,
effort, temperature, structured-output mode), what it costs (integer
micro-dollars per million tokens, with the page and date the price was read
from) and the worst case a planner should assume per call.

Why the loader is strict:

* **No secrets.** A profile names the environment variable that holds the key
  (``api_key_env``), never the key. A field called ``api_key`` (or any unknown
  field) is refused, so a key pasted into a profile fails loudly instead of
  being carried around. The key is read only at call time (``read_key``).
* **No invented model ids** (CLAUDE.md). A template keeps its model as
  ``REPLACE_WITH_...``; the loader refuses it until someone fills in an id
  checked against the provider's own page.
* **Caps fail closed.** A remote endpoint with a price of zero would make
  every call look free and skip the budget. Only a loopback endpoint (a local
  Ollama or llama.cpp server) may be priced at zero.
* **Nothing implicit** (ADR-0014). ``effort`` and ``temperature`` are sent
  only when the profile sets them; the other settings are required.

Profiles live outside the simulation, so ``timeout_s`` and ``temperature``
may be floats: they never enter world state.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal
from urllib.parse import urlsplit

from aimpire.cognition.budget import DEFAULT_RUN_CAP_MICRO_USD, Caps, Price

Kind = Literal["openai_compat", "anthropic"]
StructuredOutput = Literal["json_schema", "json_object", "prompt"]

PLACEHOLDER_PREFIX: Final = "REPLACE_WITH_"
_KINDS: Final = ("openai_compat", "anthropic")
_STRUCTURED: Final = ("json_schema", "json_object", "prompt")
_LOOPBACK: Final = frozenset({"localhost", "127.0.0.1", "::1"})
_TOP_KEYS: Final = frozenset(
    {
        "kind",
        "model",
        "base_url",
        "api_key_env",
        "structured_output",
        "timeout_s",
        "max_output_tokens",
        "effort",
        "temperature",
        "price",
        "budget",
    }
)
_PRICE_KEYS: Final = frozenset(
    {"input_micro_usd_per_mtok", "output_micro_usd_per_mtok", "source", "as_of"}
)
_BUDGET_KEYS: Final = frozenset({"max_input_tokens_per_call", "run_cap_micro_usd"})


class ProfileError(ValueError):
    """A profile file that cannot be used as written."""


class MissingCredential(RuntimeError):  # noqa: N818 (reads better at the call site than ...Error)
    """The environment variable a profile names is not set. Raised before any call."""


@dataclass(frozen=True, slots=True)
class Profile:
    """One validated profile. ``api_key_env`` is a variable *name*; "" means no key is sent.

    ``max_input_tokens_per_call`` is a planning estimate for worst-case cost
    before any request exists (``aimpire qualify`` and ``batch``); a live
    adapter bounds each actual request from its size instead.
    """

    name: str
    kind: Kind
    model: str
    base_url: str
    api_key_env: str
    structured_output: StructuredOutput
    timeout_s: float
    max_output_tokens: int
    effort: str | None
    temperature: float | None
    price: Price
    price_source: str
    price_as_of: str
    max_input_tokens_per_call: int
    run_cap_micro_usd: int

    @property
    def is_local(self) -> bool:
        """True when the endpoint is on this machine (no key needed, may be free)."""
        return (urlsplit(self.base_url).hostname or "") in _LOOPBACK

    def caps(self, monthly_micro_usd: int | None = None) -> Caps:
        """Budget caps for a run with this profile: its run cap, the default monthly cap."""
        if monthly_micro_usd is None:
            return Caps(run_micro_usd=self.run_cap_micro_usd)
        return Caps(run_micro_usd=self.run_cap_micro_usd, monthly_micro_usd=monthly_micro_usd)

    def worst_case_call_micro_usd(self) -> int:
        """Planning worst case of one call: the input estimate plus every output token."""
        return self.price.worst_case(self.max_input_tokens_per_call, self.max_output_tokens)


def read_key(profile: Profile) -> str | None:
    """The key from the environment at call time, or None when the profile needs none.

    Raises ``MissingCredential`` naming the variable (never a value) when it is
    unset or empty.
    """
    if not profile.api_key_env:
        return None
    value = os.environ.get(profile.api_key_env, "")
    if not value:
        raise MissingCredential(
            f"profile {profile.name!r} needs the environment variable "
            f"{profile.api_key_env} to hold its API key; it is not set"
        )
    return value


# --- loading ---------------------------------------------------------------------


def _get(table: dict[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in table:
        raise ProfileError(f"{where}: missing {key!r}")
    value = table[key]
    if kind is float and type(value) is int:
        value = float(value)
    if type(value) is not kind:
        raise ProfileError(f"{where}: {key!r} must be a {kind.__name__}, got {value!r}")
    return value


def _opt(table: dict[str, Any], key: str, kind: type, where: str) -> Any:
    return _get(table, key, kind, where) if key in table else None


def _table(raw: dict[str, Any], key: str, allowed: frozenset[str], where: str) -> dict[str, Any]:
    table = raw.get(key)
    if not isinstance(table, dict):
        raise ProfileError(f"{where}: missing the [{key}] table")
    unknown = sorted(set(table) - allowed)  # pyright: ignore[reportUnknownArgumentType]
    if unknown:
        raise ProfileError(f"{where}: unknown [{key}] fields {unknown}")
    return table  # pyright: ignore[reportUnknownVariableType]


def _positive(value: int, key: str, where: str) -> int:
    if value <= 0:
        raise ProfileError(f"{where}: {key!r} must be > 0, got {value}")
    return value


def _base_url(raw: dict[str, Any], kind: str, where: str) -> str:
    if kind == "anthropic":
        return _opt(raw, "base_url", str, where) or "https://api.anthropic.com"
    url: str = _get(raw, "base_url", str, where).rstrip("/")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ProfileError(f"{where}: base_url must be an http(s) URL")
    if parts.username or parts.password:
        raise ProfileError(f"{where}: base_url must not hold credentials")
    return url


def _from_raw(raw: dict[str, Any], name: str) -> Profile:
    where = f"profile {name!r}"
    unknown = sorted(set(raw) - _TOP_KEYS)
    if unknown:
        raise ProfileError(f"{where}: unknown fields {unknown} (keys go in the environment)")
    kind = _get(raw, "kind", str, where)
    if kind not in _KINDS:
        raise ProfileError(f"{where}: kind must be one of {_KINDS}, got {kind!r}")
    model: str = _get(raw, "model", str, where)
    if not model or model.startswith(PLACEHOLDER_PREFIX):
        raise ProfileError(
            f"{where}: model is a placeholder ({model!r}); fill in an id verified on the "
            "provider's current models page"
        )
    structured = raw.get("structured_output", "json_schema")
    if structured not in _STRUCTURED:
        raise ProfileError(f"{where}: structured_output must be one of {_STRUCTURED}")
    if kind == "anthropic" and structured != "json_schema":
        raise ProfileError(f"{where}: the anthropic kind always uses json_schema output")
    api_key_env: str = _get(raw, "api_key_env", str, where)
    if api_key_env and not api_key_env.replace("_", "").isalnum():
        raise ProfileError(f"{where}: api_key_env must be an environment variable name")

    price_t = _table(raw, "price", _PRICE_KEYS, where)
    price = Price(
        _get(price_t, "input_micro_usd_per_mtok", int, where),
        _get(price_t, "output_micro_usd_per_mtok", int, where),
    )
    budget_t = _table(raw, "budget", _BUDGET_KEYS, where)
    run_cap = _opt(budget_t, "run_cap_micro_usd", int, where)
    if run_cap is None:
        run_cap = DEFAULT_RUN_CAP_MICRO_USD
    if not 0 <= run_cap <= DEFAULT_RUN_CAP_MICRO_USD:
        raise ProfileError(f"{where}: run_cap_micro_usd may only lower the default run cap")

    profile = Profile(
        name=name,
        kind=kind,
        model=model,
        base_url=_base_url(raw, kind, where),
        api_key_env=api_key_env,
        structured_output=structured,
        timeout_s=_get(raw, "timeout_s", float, where),
        max_output_tokens=_positive(
            _get(raw, "max_output_tokens", int, where), "max_output_tokens", where
        ),
        effort=_opt(raw, "effort", str, where),
        temperature=_opt(raw, "temperature", float, where),
        price=price,
        price_source=_get(price_t, "source", str, where),
        price_as_of=_get(price_t, "as_of", str, where),
        max_input_tokens_per_call=_positive(
            _get(budget_t, "max_input_tokens_per_call", int, where),
            "max_input_tokens_per_call",
            where,
        ),
        run_cap_micro_usd=run_cap,
    )
    if profile.timeout_s <= 0:
        raise ProfileError(f"{where}: timeout_s must be > 0")
    if not profile.is_local and price.output_micro_usd_per_mtok == 0:
        raise ProfileError(f"{where}: a remote endpoint needs a price (only loopback is free)")
    if not profile.is_local and not api_key_env:
        raise ProfileError(f"{where}: a remote endpoint needs api_key_env")
    if kind == "openai_compat" and profile.effort is not None:
        raise ProfileError(f"{where}: effort is not supported by the openai_compat adapter yet")
    return profile


def parse_profile(text: str, name: str) -> Profile:
    """Parse and validate profile TOML ``text``; ``name`` labels it in errors and records."""
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"profile {name!r}: not valid TOML ({exc})") from None
    return _from_raw(raw, name)


def load_profile(path: Path) -> Profile:
    """Load ``profiles/<name>.toml``; the profile is named after the file stem."""
    return parse_profile(path.read_text(encoding="utf-8"), name=path.stem)
