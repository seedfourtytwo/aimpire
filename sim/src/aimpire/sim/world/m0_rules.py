"""Typed M0 rules: the petri dish's numbers as one frozen record (backlog M0).

Why this type lives in ``aimpire.sim``: the world builder and the systems
consume it, and the simulation package may not import ``aimpire.rules`` (it
does no I/O). The loader (``aimpire.rules.load_m0_rules``) reads
``rules/<version>/m0.yaml`` and calls ``M0Rules.from_mapping``; the simulation
receives this plain record, as it does ``Calendar`` and ``DerivedWorld``.

Units (ADR-0012), integers only: food in milli-units (mu; 1_000 mu is one
person's need for one tick), fractions and chances in ppm, rates as
``Rate`` (ppm with a period) and amounts per period as ``Flow`` (ADR-0011).
Base values are "at Earth": systems scale them by the W0 derived rates.

Validation refuses rather than coerces: a float, a bool, a quoted number, a
missing or unknown key is a ``ValueError``. ``check_calendar`` adds the checks
that need the tick length of a period.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from aimpire.sim.calendar import Calendar, Flow, Rate
from aimpire.sim.fixed import PPM

SECTIONS: Final[dict[str, frozenset[str]]] = {
    "map": frozenset({"rows", "cols", "place_block"}),
    "food": frozenset({"ceiling", "initial"}),
    "fertility": frozenset({"min", "max", "cell"}),
    "regrowth": frozenset({"rate", "seed"}),
    "people": frozenset({"need", "start", "start_stores", "starvation_death"}),
    "stores": frozenset({"spoilage"}),
    "forage": frozenset({"carry_per_trip", "walk_energy"}),
    "scout": frozenset({"sight"}),
}
"""The exact keys of ``m0.yaml``, by section."""


@dataclass(frozen=True, slots=True)
class M0Rules:
    """Every number the M0 petri dish uses (``rules/v1/m0.yaml`` documents the values)."""

    rows: int
    """Map height in tiles."""
    cols: int
    """Map width in tiles."""
    place_block: int
    """Side of one ``grid_blocks`` place, in tiles."""
    food_ceiling: int
    """Food ceiling of one tile at Earth and full fertility, mu."""
    initial_food: int
    """Food on each tile at worldgen, ppm of that tile's ceiling."""
    fertility_min: int
    """Lowest fertility a noise lattice point can draw, ppm."""
    fertility_max: int
    """Highest fertility a noise lattice point can draw, ppm."""
    fertility_cell: int
    """Spacing of the fertility noise lattice, tiles."""
    regrowth_rate: Rate
    """Logistic rate r: growth per unit stock at low density."""
    regrowth_seed: Rate
    """Seed term s: growth per unit of the gap K - F, so zero is not absorbing."""
    food_need: Flow
    """What one person eats."""
    start_people: int
    """People in the tribe at tick 0."""
    start_stores: int
    """Food in the tribe's stores at tick 0, mu."""
    starvation_death: Rate
    """Chance that an unfed person dies, per period of shortfall."""
    store_spoilage: Rate
    """Share of open stores that spoils."""
    carry_per_trip: int
    """Food one forager brings back per trip at Earth gravity, mu."""
    walk_energy: Flow
    """Extra food a walking person burns at Earth gravity."""
    scout_sight: int
    """Manhattan reach of a scout from its place's centroid, tiles."""

    def __post_init__(self) -> None:
        for name in ("rows", "cols", "place_block", "fertility_cell"):
            _positive(name, getattr(self, name))
        for name in ("food_ceiling", "start_people", "start_stores", "carry_per_trip"):
            _non_negative(name, getattr(self, name))
        _non_negative("scout_sight", self.scout_sight)
        for name in ("initial_food", "fertility_min", "fertility_max"):
            _ppm_fraction(name, getattr(self, name))
        if self.fertility_min > self.fertility_max:
            raise ValueError("fertility min must not exceed fertility max")
        if self.place_block > min(self.rows, self.cols):
            raise ValueError(f"place_block {self.place_block} is larger than the map")
        for name in ("regrowth_rate", "regrowth_seed", "starvation_death", "store_spoilage"):
            if not isinstance(getattr(self, name), Rate):
                raise TypeError(f"{name} must be a Rate")
        for name in ("food_need", "walk_energy"):
            if not isinstance(getattr(self, name), Flow):
                raise TypeError(f"{name} must be a Flow")

    def check_calendar(self, calendar: Calendar) -> None:
        """Checks that need period lengths. Raises ``ValueError``.

        * Regrowth: r and s per tick must sum to at most 1 (``PPM``), so one
          tick never overshoots the ceiling and the logistic step is stable.
        * Chances per tick (starvation, spoilage) must be at most 1.
        """
        r_ppm, r_per = self.regrowth_rate.resolve(calendar)
        s_ppm, s_per = self.regrowth_seed.resolve(calendar)
        if r_ppm * s_per + s_ppm * r_per > PPM * r_per * s_per:
            raise ValueError("regrowth rate plus seed term must be at most 1_000_000 ppm a tick")
        for name in ("starvation_death", "store_spoilage"):
            ppm, per = cast(Rate, getattr(self, name)).resolve(calendar)
            if ppm > PPM * per:
                raise ValueError(f"{name} must be at most 1_000_000 ppm a tick")

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> M0Rules:
        """Build from parsed ``m0.yaml``: exactly the sections and keys in ``SECTIONS``."""
        sec = {name: _section(data, name) for name in _exact(data, set(SECTIONS), "m0 rules")}
        return cls(
            rows=_int(sec["map"], "rows"),
            cols=_int(sec["map"], "cols"),
            place_block=_int(sec["map"], "place_block"),
            food_ceiling=_int(sec["food"], "ceiling"),
            initial_food=_int(sec["food"], "initial"),
            fertility_min=_int(sec["fertility"], "min"),
            fertility_max=_int(sec["fertility"], "max"),
            fertility_cell=_int(sec["fertility"], "cell"),
            regrowth_rate=Rate.from_mapping(_sub(sec["regrowth"], "rate")),
            regrowth_seed=Rate.from_mapping(_sub(sec["regrowth"], "seed")),
            food_need=Flow.from_mapping(_sub(sec["people"], "need")),
            start_people=_int(sec["people"], "start"),
            start_stores=_int(sec["people"], "start_stores"),
            starvation_death=Rate.from_mapping(_sub(sec["people"], "starvation_death")),
            store_spoilage=Rate.from_mapping(_sub(sec["stores"], "spoilage")),
            carry_per_trip=_int(sec["forage"], "carry_per_trip"),
            walk_energy=Flow.from_mapping(_sub(sec["forage"], "walk_energy")),
            scout_sight=_int(sec["scout"], "sight"),
        )


def _exact(data: Mapping[str, object], expected: set[str], where: str) -> list[str]:
    keys = set(data)
    if keys != expected:
        missing, extra = sorted(expected - keys), sorted(keys - expected)
        raise ValueError(f"{where}: missing {missing}, unknown {extra}")
    return sorted(keys)


def _mapping(value: object, where: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{where} must be a mapping, got {value!r}")
    return cast(Mapping[str, object], value)


def _section(data: Mapping[str, object], name: str) -> Mapping[str, object]:
    section = _mapping(data[name], f"section {name!r}")
    _exact(section, set(SECTIONS[name]), f"section {name!r}")
    return section


def _sub(section: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _mapping(section[key], key)


def _int(section: Mapping[str, object], key: str) -> int:
    value = section[key]
    if type(value) is not int:
        raise ValueError(f"{key} must be an integer, got {value!r}")
    return value


def _positive(name: str, value: object) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


def _non_negative(name: str, value: object) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")


def _ppm_fraction(name: str, value: object) -> None:
    if type(value) is not int or not 0 <= value <= PPM:
        raise ValueError(f"{name} must be an integer from 0 to {PPM} ppm, got {value!r}")
