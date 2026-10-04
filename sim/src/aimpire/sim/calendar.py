"""Game calendar and rates with an explicit period (ADR-0011).

Why: the season and year lengths are rules data, not code, so that no rate
silently changes meaning if the calendar changes. Rules state every rate with
its period (``per: year | season | tick``); ``Rate.resolve`` turns that into
``(ppm, per_ticks)`` for ``aimpire.sim.fixed.apply_rate``. A rate is linear
over its period, not compounded.

A tick is the base step. Prose may call it a day, but it is a game day: with a
120-tick year one tick stands for about three calendar days.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, get_args

Period = Literal["tick", "season", "year"]
_PERIODS: tuple[str, ...] = get_args(Period)


@dataclass(frozen=True, slots=True)
class Calendar:
    """Season and year lengths in ticks. Built from ``rules/<version>/calendar.yaml``."""

    ticks_per_season: int
    seasons_per_year: int

    def __post_init__(self) -> None:
        for name in ("ticks_per_season", "seasons_per_year"):
            value: object = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive int, got {value!r}")

    @property
    def ticks_per_year(self) -> int:
        return self.ticks_per_season * self.seasons_per_year

    def season_of(self, tick: int) -> int:
        """Season index within the year, from 0."""
        _check_tick(tick)
        return (tick // self.ticks_per_season) % self.seasons_per_year

    def year_of(self, tick: int) -> int:
        """Year index, from 0."""
        _check_tick(tick)
        return tick // self.ticks_per_year

    def is_season_start(self, tick: int) -> bool:
        _check_tick(tick)
        return tick % self.ticks_per_season == 0

    def is_year_start(self, tick: int) -> bool:
        _check_tick(tick)
        return tick % self.ticks_per_year == 0

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> Calendar:
        """Build from parsed rules data. Unknown or missing keys are errors."""
        _check_keys(data, {"ticks_per_season", "seasons_per_year"})
        tps, spy = data["ticks_per_season"], data["seasons_per_year"]
        if type(tps) is not int or type(spy) is not int:
            raise ValueError("calendar lengths must be integers")
        return cls(ticks_per_season=tps, seasons_per_year=spy)


@dataclass(frozen=True, slots=True)
class Rate:
    """A rate in parts per million over a stated period."""

    ppm: int
    per: Period

    def __post_init__(self) -> None:
        if type(self.ppm) is not int or self.ppm < 0:
            raise ValueError(f"ppm must be a non-negative int, got {self.ppm!r}")
        if self.per not in _PERIODS:
            raise ValueError(f"per must be one of {_PERIODS}, got {self.per!r}")

    def resolve(self, calendar: Calendar) -> tuple[int, int]:
        """Return ``(ppm, per_ticks)`` for ``apply_rate`` under ``calendar``."""
        if self.per == "tick":
            return self.ppm, 1
        if self.per == "season":
            return self.ppm, calendar.ticks_per_season
        return self.ppm, calendar.ticks_per_year

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> Rate:
        """Build from rules data such as ``{ppm: 2500, per: season}``."""
        _check_keys(data, {"ppm", "per"})
        ppm, per = data["ppm"], data["per"]
        if type(ppm) is not int:
            raise ValueError(f"ppm must be an int, got {ppm!r}")
        if per not in _PERIODS:
            raise ValueError(f"per must be one of {_PERIODS}, got {per!r}")
        return cls(ppm=ppm, per=per)  # pyright: ignore[reportArgumentType]


def _check_tick(tick: int) -> None:
    if tick < 0:
        raise ValueError(f"tick must be >= 0, got {tick}")


def _check_keys(data: Mapping[str, object], expected: set[str]) -> None:
    keys = set(data)
    if keys != expected:
        missing, extra = sorted(expected - keys), sorted(keys - expected)
        raise ValueError(f"expected keys {sorted(expected)}; missing {missing}, unknown {extra}")
