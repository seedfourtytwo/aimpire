"""The knob registry: every tunable, declared once (ADR-0020, LAB0).

Why one registry: the CLI (``--set``), the run manifest, the reports and the
future workshop page all read the same list, so a knob cannot mean one thing
in one place and another elsewhere. It is exported to ``schema/`` as JSON
Schema (``aimpire.lab.schema``).

Each knob has two ranges:
    * **allowed**: values outside it are refused (the laws cannot be computed,
      or the value is meaningless);
    * **validated**: where the science behind it holds. Outside it a run is
      still allowed but tagged ``beyond-model``.

Layers decide where an override goes: ``world``, ``rules`` and ``tribe``
change the rules hash; ``mind`` and ``god`` are recorded in the run manifest
only; ``display`` is never recorded.

ADR-0019: no knob may name a personality, temperament, institution, regime,
role or belief. Those are outcomes, not inputs (``test_no_outcome_knobs``).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal


class KnobError(ValueError):
    """An override names an unknown knob or a value the knob does not allow."""


class Layer(StrEnum):
    """Where a knob acts, which decides whether it enters the rules hash."""

    WORLD = "world"
    RULES = "rules"
    TRIBE = "tribe"
    MIND = "mind"
    GOD = "god"
    DISPLAY = "display"


HASHED_LAYERS: Final = frozenset({Layer.WORLD, Layer.RULES, Layer.TRIBE})
"""Layers whose overrides change the world itself, so they enter the rules hash."""

RECORDED_LAYERS: Final = HASHED_LAYERS | {Layer.MIND, Layer.GOD}
"""Layers whose overrides are recorded in the run manifest (``display`` is not)."""

Value = int | str
"""A canonical knob value: an integer, or one of an enum knob's choices."""


@dataclass(frozen=True, slots=True)
class Knob:
    """One tunable: identity, type, unit, default, ranges, layer and meaning."""

    path: str
    """``<layer>.<name>``, for example ``world.gravity``."""
    layer: Layer
    kind: Literal["int", "enum"]
    unit: str
    default: Value
    description: str
    allowed: tuple[int, int] | None = None
    """Inclusive bounds for an ``int`` knob."""
    validated: tuple[int, int] | None = None
    """Inclusive bounds where the model holds; ``None`` means the whole allowed range."""
    choices: tuple[str, ...] = ()
    """The values of an ``enum`` knob (all validated)."""

    @property
    def in_rules_hash(self) -> bool:
        """True if an override of this knob changes the rules hash."""
        return self.layer in HASHED_LAYERS

    def parse(self, text: str) -> Value:
        """Turn ``--set`` text into a checked canonical value, or raise ``KnobError``."""
        if self.kind == "enum":
            return self.check(text.strip())
        try:
            value = int(text.strip(), 10)  # accepts 950000 and 950_000; refuses 0.95
        except ValueError:
            raise KnobError(f"{self.path} takes an integer in {self.unit}, got {text!r}") from None
        return self.check(value)

    def check(self, value: Value) -> Value:
        """Return ``value`` if this knob allows it; raise ``KnobError`` otherwise."""
        if self.kind == "enum":
            if value not in self.choices:
                raise KnobError(
                    f"{self.path} must be one of {', '.join(self.choices)}, got {value!r}"
                )
            return value
        if type(value) is not int or self.allowed is None:
            raise KnobError(f"{self.path} takes an integer in {self.unit}, got {value!r}")
        low, high = self.allowed
        if not low <= value <= high:
            raise KnobError(
                f"{self.path}={value} is outside the allowed range {low}..{high} ({self.unit})"
            )
        return value

    def beyond_validated(self, value: Value) -> bool:
        """True if an allowed ``value`` lies outside the validated range."""
        if self.kind == "enum" or self.validated is None or type(value) is not int:
            return False
        low, high = self.validated
        return not low <= value <= high


KNOBS: Final[tuple[Knob, ...]] = (
    Knob(
        path="world.gravity",
        layer=Layer.WORLD,
        kind="int",
        unit="ppm of Earth g",
        default=1_000_000,
        allowed=(100_000, 10_000_000),
        validated=(500_000, 1_500_000),
        description=(
            "Surface gravity. Drives walking speed, carry load, walking energy, "
            "water speed, tree height, fall harm and throw range."
        ),
    ),
    Knob(
        path="world.sunlight",
        layer=Layer.WORLD,
        kind="int",
        unit="ppm of Earth mean sunlight",
        default=1_000_000,
        allowed=(0, 5_000_000),
        description="Mean sunlight at the surface. Drives the plant growth ceiling.",
    ),
    Knob(
        path="world.rain",
        layer=Layer.WORLD,
        kind="int",
        unit="ppm of reference rain",
        default=1_000_000,
        allowed=(0, 5_000_000),
        description="Rainfall. Drives the plant growth ceiling.",
    ),
    Knob(
        path="world.tilt",
        layer=Layer.WORLD,
        kind="int",
        unit="milli-degrees",
        default=23_440,
        allowed=(0, 90_000),
        validated=(0, 45_000),
        description="Axial tilt. Drives the strength of summer and winter.",
    ),
    Knob(
        path="mind.renderer",
        layer=Layer.MIND,
        kind="enum",
        unit="choice",
        default="places",
        choices=("places", "grid"),
        description="How an observation is laid out as prompt text (ADR-0013).",
    ),
    Knob(
        path="mind.knowledge_arm",
        layer=Layer.MIND,
        kind="enum",
        unit="choice",
        default="A0",
        choices=("A0", "A1", "A2", "A3"),
        description="How much a mind could know in advance (ADR-0018).",
    ),
)
"""Every knob, in a fixed order. M0 adds its rules and tribe knobs here."""

_BY_PATH: Final = {knob.path: knob for knob in KNOBS}


def get_knob(path: str) -> Knob:
    """The knob at ``path``; ``KnobError`` (with near matches) if there is none."""
    knob = _BY_PATH.get(path)
    if knob is None:
        near = [p for p in sorted(_BY_PATH) if p.split(".")[0] == path.split(".", maxsplit=1)[0]]
        hint = f"; {near[0].split('.')[0]} knobs: {', '.join(near)}" if near else ""
        raise KnobError(f"unknown knob {path!r}{hint} (see schema/lab-knobs.schema.json)")
    return knob
