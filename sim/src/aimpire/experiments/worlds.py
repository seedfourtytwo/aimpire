"""Preset factories: how an experiment names the world it runs in (ADR-0010, ADR-0015).

An experiment file says ``world: <name>``; the batch runner asks the factory
registered under that name for a fresh world per run, built from the run's
seed and its number of seats. The batch runner knows nothing else about the
world, so a milestone plugs in by registering its preset:

    register_world("m0", build_m0_world)   # M0a/M0b

A factory must be deterministic: the same seed and seat count give the same
state hash. Its civilizations use the m0 ``civ`` layout (``civ_record``), in
seat order, so the observation builder and the seat builder work unchanged.
"""

from collections.abc import Callable
from dataclasses import dataclass

from aimpire.sim.calendar import Calendar
from aimpire.sim.scheduler import Scheduler
from aimpire.sim.state import WorldState


@dataclass(frozen=True, slots=True)
class World:
    """A fresh world for one run. ``civs`` is ``(civ_id, entity_id)`` in seat order."""

    state: WorldState
    scheduler: Scheduler
    calendar: Calendar
    civs: tuple[tuple[str, int], ...]


PresetFactory = Callable[[int, int], World]
"""``factory(seed, seats)``: a new world with one civilization per seat."""

_FACTORIES: dict[str, PresetFactory] = {}


def register_world(name: str, factory: PresetFactory) -> None:
    """Make ``factory`` available to experiment files as ``world: <name>``."""
    if not name or name in _FACTORIES:
        raise ValueError(f"world name {name!r} is empty or already registered")
    _FACTORIES[name] = factory


def world_names() -> list[str]:
    """Every registered world name, sorted."""
    return sorted(_FACTORIES)


def world_factory(name: str) -> PresetFactory:
    """The factory registered as ``name``; ``KeyError`` names the known worlds."""
    if name not in _FACTORIES:
        raise KeyError(f"unknown world {name!r}; registered worlds: {world_names()}")
    return _FACTORIES[name]
