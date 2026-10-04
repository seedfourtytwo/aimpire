"""Assemble a ready-to-run M0 petri dish from a rules directory (backlog M0b, for M0c's run CLI).

The one call that does the I/O the simulation may not do: read the calendar,
``m0.yaml`` and the world constants, apply Lab ``--set`` overrides, then build
the world at the map scale of ``scale.yaml``, place one tribe per seat and
bind the ``m0`` preset to the same rules and W0 rates:

    world = build_m0_run(seed, rules_dir, settings=args.set)
    seats = [Seat(civ, eid, mind, provider) for civ, eid in world.civs]
    build = seats_for(seats, walk_speed=world.walk_speed, ...)
    await run_with_councils(world.state, world.scheduler, seats_for=build, ...)

``World.civs`` is ``(civ_id, entity_id)`` in seat order (``C1``, ``C2``, ...).
The same seed, rules directory and settings always give the same state hash.
"""

from collections.abc import Iterable
from pathlib import Path

from aimpire.experiments.worlds import World
from aimpire.lab.variant import resolve_variant
from aimpire.rules import load_calendar, load_m0_rules, load_map_scale
from aimpire.sim.presets import PRESETS, m0_quantities, system_registry
from aimpire.sim.scheduler import Scheduler
from aimpire.sim.world.m0 import build_m0_world
from aimpire.sim.world.tribe import place_tribe


def build_m0_run(
    seed: int,
    rules_dir: Path,
    *,
    seats: int = 1,
    settings: Iterable[str] = (),
    checked: bool = False,
) -> World:
    """A tick-0 M0 world with ``seats`` tribes and its scheduler.

    ``rules_dir`` is a rules version directory such as ``rules/v1``; its name
    is the rules version. ``checked`` turns on the ledger check after every
    system (slower; for tests and audits).
    """
    if seats < 1:
        raise ValueError(f"seats must be >= 1, got {seats}")
    rules_dir = Path(rules_dir)
    calendar = load_calendar(rules_dir)
    rules = load_m0_rules(rules_dir, calendar)
    resolved = resolve_variant(rules_dir, settings)
    state = build_m0_world(
        seed,
        rules,
        resolved.derived,
        rules_version=rules_dir.name,
        rules_hash=resolved.rules_hash,
        scale=load_map_scale(rules_dir),
    )
    civs: list[tuple[str, int]] = []
    for seat in range(seats):
        civ_id = f"C{seat + 1}"
        civs.append((civ_id, place_tribe(state, rules, civ_id=civ_id, seat=seat)))
    scheduler = Scheduler(
        PRESETS["m0"],
        system_registry(rules, derived=resolved.derived),
        calendar,
        quantities=m0_quantities() if checked else None,
    )
    return World(
        state=state,
        scheduler=scheduler,
        calendar=calendar,
        civs=tuple(civs),
        walk_speed=resolved.derived.walk_speed,
    )
