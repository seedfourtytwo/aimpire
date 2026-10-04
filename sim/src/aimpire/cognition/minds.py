"""Name a mind by text and get its price, limits and provider (ADR-0005, backlog F6).

``aimpire qualify`` and ``aimpire batch`` take minds as text:

* ``mock``: scripted replies supplied by the caller (qualify's frozen cases);
* ``rule`` or ``rule:<name>``: a registered baseline (``cognition.baselines``);
* a path ending in ``.toml``: a model profile (``cognition.profiles``).

Resolving a name and building its provider are separate steps on purpose.
``resolve_mind`` reads no key and opens nothing, so a planner can price the
worst case and refuse over budget before any provider exists. Only
``build_provider`` reads the key (``MissingCredential`` if it is unset).

Money is integer micro-dollars (``cognition.budget``). Offline minds are free
and never refused for cost.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from aimpire.cognition.baselines import DEFAULT_RULE, RULES, rule_provider
from aimpire.cognition.budget import DEFAULT_RUN_CAP_MICRO_USD, FREE, Price
from aimpire.cognition.live import provider_from_profile
from aimpire.cognition.offline import MockFailure, MockProvider
from aimpire.cognition.profiles import Profile, load_profile
from aimpire.cognition.protocol import Provider

MOCK: Final = "mock"
RULE_PREFIX: Final = "rule"
PROFILE_SUFFIX: Final = ".toml"
# Request settings for offline minds: they ignore both, but every request carries them.
OFFLINE_MAX_OUTPUT_TOKENS: Final = 4096
OFFLINE_TIMEOUT_S: Final = 60.0

MindKind = Literal["mock", "rule", "profile"]


class MindError(ValueError):
    """A mind name that names nothing usable."""


@dataclass(frozen=True, slots=True)
class MindSpec:
    """A resolved mind: what it is called, what it may cost, how requests are sized.

    ``label`` is what reports and run manifests show: ``mock``,
    ``rule:<name>`` or the profile's name. ``worst_case_call_micro_usd`` is
    the planning worst case of one call (0 for offline minds).
    """

    label: str
    kind: MindKind
    price: Price
    worst_case_call_micro_usd: int
    run_cap_micro_usd: int
    max_output_tokens: int
    timeout_s: float
    effort: str | None
    temperature: float | None
    profile: Profile | None = None
    rule: str = ""


def _offline(label: str, kind: MindKind, rule: str = "") -> MindSpec:
    return MindSpec(
        label=label,
        kind=kind,
        price=FREE,
        worst_case_call_micro_usd=0,
        run_cap_micro_usd=DEFAULT_RUN_CAP_MICRO_USD,
        max_output_tokens=OFFLINE_MAX_OUTPUT_TOKENS,
        timeout_s=OFFLINE_TIMEOUT_S,
        effort=None,
        temperature=None,
        rule=rule,
    )


def _from_profile(profile: Profile) -> MindSpec:
    return MindSpec(
        label=profile.name,
        kind="profile",
        price=profile.price,
        worst_case_call_micro_usd=profile.worst_case_call_micro_usd(),
        run_cap_micro_usd=profile.run_cap_micro_usd,
        max_output_tokens=profile.max_output_tokens,
        timeout_s=profile.timeout_s,
        effort=profile.effort,
        temperature=profile.temperature,
        profile=profile,
    )


def resolve_mind(name: str, base_dir: Path) -> MindSpec:
    """Resolve ``name``; a relative profile path is taken from ``base_dir``. Reads no key."""
    if name == MOCK:
        return _offline(MOCK, "mock")
    head, _, rule = name.partition(":")
    if head == RULE_PREFIX:
        rule = rule or DEFAULT_RULE
        if rule not in RULES:
            raise MindError(f"unknown rule {rule!r}; known rules: {sorted(RULES)}")
        return _offline(f"{RULE_PREFIX}:{rule}", "rule", rule)
    if name.endswith(PROFILE_SUFFIX):
        path = Path(name) if Path(name).is_absolute() else base_dir / name
        if not path.is_file():
            raise MindError(f"profile file not found: {name}")
        return _from_profile(load_profile(path))
    raise MindError(f"unknown mind {name!r}: use mock, rule[:<name>] or a profile .toml path")


def build_provider(
    mind: MindSpec, mock_replies: Mapping[str, str | MockFailure] | None = None
) -> Provider:
    """The provider for ``mind``. A profile's key is read here, before any call."""
    if mind.kind == "mock":
        return MockProvider(mock_replies or {})
    if mind.kind == "rule":
        return rule_provider(mind.rule)
    if mind.profile is None:
        raise MindError(f"mind {mind.label!r} has no profile")
    return provider_from_profile(mind.profile)
