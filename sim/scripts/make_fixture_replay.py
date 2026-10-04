"""Generate (or check) the fixture replay the static player opens by default (F4b).

Usage, from ``sim/``::

    uv run python scripts/make_fixture_replay.py          # write the fixture
    uv run python scripts/make_fixture_replay.py --check  # fail if it is stale or invalid
    uv run python scripts/make_fixture_replay.py --frame-sha256  # for the player smoke test

The world here is a TEST DOUBLE for the viewer, not simulation rules: a
fertile band of food, eight dots that wander by counter draws and eat, and
food that regrows toward each tile's fertility. Every food change is recorded
in the ledger and checked (F3), so even the demo obeys the invariants.
The output is byte-identical on every run.
"""

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aimpire.report.frames import frame_array
from aimpire.report.replay import ReplayRecorder, dumps, load_replay
from aimpire.sim.calendar import Calendar
from aimpire.sim.ledger import entity_field_total, layer_total
from aimpire.sim.rng import Stream, draw, stream_key, uniform_int
from aimpire.sim.scheduler import Cadence, Preset, Scheduler, SystemSpec, TickContext
from aimpire.sim.state import WorldState

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "client" / "replay" / "fixtures" / "wander.json"
SEED, ROWS, COLS, TICKS = 42, 16, 24, 60
CAL = Calendar(ticks_per_season=15, seasons_per_year=4)
STEPS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))
BITE, REGROWTH = 120, 6  # milli-units per tick


@dataclass
class DemoWander:
    """Each dot steps in a drawn direction, clamped to the grid, then eats a bite."""

    name: str = "demo_wander"
    cadence: Cadence = "tick"
    sequential: bool = True

    def step(self, state: WorldState, ctx: TickContext) -> None:
        key = ctx.key(Stream.MOCK)
        people = [i for i, e in state.entities.items() if e["kind"] == "person"]
        for pid in ctx.order(people):
            person = state.entities[pid]
            pos, carry = person["pos"], person["carry"]
            assert isinstance(pos, list) and isinstance(carry, dict)
            row, col = pos
            assert isinstance(row, int) and isinstance(col, int)
            dr, dc = STEPS[uniform_int(draw(key, pid), len(STEPS))]
            row, col = min(max(row + dr, 0), ROWS - 1), min(max(col + dc, 0), COLS - 1)
            person["pos"] = [row, col]
            take = min(BITE, int(state.layers["food"][row, col]))
            state.layers["food"][row, col] -= take
            eaten = carry["food"]
            assert isinstance(eaten, int)
            carry["food"] = eaten + take
            ctx.ledger.record("food_on_land", -take, "HARVEST", ref=f"P{pid}")
            ctx.ledger.record("food_carried", take, "HARVEST", ref=f"P{pid}")


@dataclass
class DemoRegrow:
    """Food regrows toward the tile's fertility by a fixed amount per tick."""

    name: str = "demo_regrow"
    cadence: Cadence = "tick"
    sequential: bool = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        food, fertility = state.layers["food"], state.layers["fertility"]
        gain = np.minimum(REGROWTH, np.maximum(fertility - food, 0)).astype(np.int64)
        food += gain
        ctx.ledger.record("food_on_land", int(gain.sum()), "REGROWTH")


def build_world() -> WorldState:
    """A fertile band down the middle columns; dots start at drawn positions."""
    state = WorldState(run_seed=SEED, rules_version="fixture", rules_hash="fixture")
    fertility = np.full((ROWS, COLS), 300, dtype=np.int64)
    fertility[:, 9:15] = 1000
    fertility[5:9, 3:6] = 700
    state.add_layer("fertility", fertility)
    state.add_layer("food", fertility.copy())
    key = stream_key(SEED, 0, Stream.WORLDGEN)
    for i in range(8):
        row, col = uniform_int(draw(key, i, 1), ROWS), uniform_int(draw(key, i, 2), COLS)
        state.add_entity("person", {"pos": [row, col], "carry": {"food": 0}})
    return state


def run_fixture() -> tuple[str, WorldState]:
    """Run the demo world; return the canonical replay JSON text and the final state."""
    systems = (DemoWander(), DemoRegrow())
    registry = {s.name: (lambda _p, s=s: s) for s in systems}
    quantities = {
        "food_on_land": layer_total("food"),
        "food_carried": entity_field_total("person", ("carry", "food")),
    }
    preset = Preset("fixture", [SystemSpec(s.name) for s in systems])
    scheduler = Scheduler(preset, registry, CAL, quantities=quantities)  # type: ignore[arg-type]
    state = build_world()
    recorder = ReplayRecorder(layer="food", kinds=("person",), calendar=CAL, scale_max=1000)
    recorder.capture(state)
    for _ in range(TICKS):
        scheduler.step(state)
        recorder.capture(state)
    return dumps(recorder.to_dict()), state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify instead of writing")
    parser.add_argument(
        "--frame-sha256",
        action="store_true",
        help="print the SHA-256 of the final frame's RGB bytes (the JS player must match it)",
    )
    args = parser.parse_args(argv)
    text, final = run_fixture()
    if args.frame_sha256:
        frame = frame_array(final, "food", ("person",), scale_max=1000)
        print(hashlib.sha256(frame.tobytes()).hexdigest())
        return 0
    if args.check:
        load_replay(FIXTURE)  # raises ReplayError if invalid
        if FIXTURE.read_text(encoding="ascii") != text:
            print(f"{FIXTURE} is stale: run scripts/make_fixture_replay.py", file=sys.stderr)
            return 1
        print(f"fixture replay ok: {FIXTURE.relative_to(REPO)}")
        return 0
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_bytes(text.encode("ascii"))
    print(f"wrote {FIXTURE.relative_to(REPO)} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
