"""F4b acceptance: one-file JSON replay export that round-trips a run exactly (ADR-0004, ADR-0010).

Written by the planning model before implementation (ADR-0016). Read-only.
The systems below are test doubles, not simulation rules. They move people
with counter draws and change a food layer, recording every conserved change.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from aimpire.report.replay import (
    FORMAT,
    ReplayError,
    ReplayRecorder,
    decode_layer,
    load_replay,
    write_replay,
)
from aimpire.sim.calendar import Calendar
from aimpire.sim.hashing import state_hash
from aimpire.sim.ledger import entity_field_total, layer_total
from aimpire.sim.rng import Stream, draw, uniform_int
from aimpire.sim.scheduler import Cadence, Preset, Scheduler, SystemSpec, TickContext
from aimpire.sim.state import WorldState

pytestmark = pytest.mark.acceptance

CAL = Calendar(ticks_per_season=10, seasons_per_year=4)
ROWS, COLS = 6, 8
QUANTITIES = {
    "food_on_land": layer_total("food"),
    "food_carried": entity_field_total("person", ("carry", "food")),
}
STEPS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))  # stay, north, south, west, east


@dataclass
class Wander:
    """Each person steps in a drawn direction (clamped to the grid), then eats up to 50."""

    name: str = "wander"
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
            take = min(50, int(state.layers["food"][row, col]))
            state.layers["food"][row, col] -= take
            eaten = carry["food"]
            assert isinstance(eaten, int)
            carry["food"] = eaten + take
            ctx.ledger.record("food_on_land", -take, "HARVEST", ref=f"P{pid}")
            ctx.ledger.record("food_carried", take, "HARVEST", ref=f"P{pid}")


@dataclass
class Regrow:
    """Tiles below 1000 regain 7 per tick."""

    name: str = "regrow"
    cadence: Cadence = "tick"
    sequential: bool = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        food = state.layers["food"]
        gain = np.where(food < 1000, np.minimum(7, 1000 - food), 0).astype(np.int64)
        food += gain
        ctx.ledger.record("food_on_land", int(gain.sum()), "REGROWTH")


def _world(seed: int) -> WorldState:
    s = WorldState(run_seed=seed, rules_version="v1", rules_hash="test")
    s.add_layer("food", np.full((ROWS, COLS), 400, dtype=np.int64))
    s.add_layer("moisture", np.zeros((ROWS, COLS), dtype=np.int64))
    for i in range(4):
        s.add_entity("person", {"pos": [i, 2 * i], "carry": {"food": 0}})
    s.add_entity("place", {"label": "camp"})
    return s


def _scheduler() -> Scheduler:
    systems = (Wander(), Regrow())
    registry = {s.name: (lambda _p, s=s: s) for s in systems}
    preset = Preset("test", [SystemSpec(s.name) for s in systems])
    return Scheduler(preset, registry, CAL, quantities=QUANTITIES)  # type: ignore[arg-type]


def _dots(state: WorldState) -> list[list[object]]:
    out: list[list[object]] = []
    for eid in sorted(state.entities):
        e = state.entities[eid]
        pos = e.get("pos")
        if e["kind"] == "person" and isinstance(pos, list):
            out.append([eid, "person", pos[0], pos[1]])
    return out


def _run(seed: int, ticks: int, path: Path) -> tuple[list[str], list[Any], list[Any]]:
    state, scheduler = _world(seed), _scheduler()
    rec = ReplayRecorder(layer="food", kinds=("person",), calendar=CAL, scale_max=1000)
    hashes, dots, layers = [state_hash(state)], [_dots(state)], [state.layers["food"].tolist()]
    rec.capture(state)
    for _ in range(ticks):
        scheduler.step(state)
        rec.capture(state)
        hashes.append(state_hash(state))
        dots.append(_dots(state))
        layers.append(state.layers["food"].tolist())
    write_replay(rec, path)
    return hashes, dots, layers


def test_replay_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "run.json"
    hashes, dots, layers = _run(seed=11, ticks=20, path=path)
    replay = load_replay(path)
    assert replay["format"] == FORMAT
    assert replay["run_seed"] == 11
    assert replay["rules_version"] == "v1"
    assert replay["calendar"] == {"ticks_per_season": 10, "seasons_per_year": 4}
    assert replay["layers"] == ["food", "moisture"]
    assert replay["layer"] == "food"
    assert replay["grid"] == [ROWS, COLS]
    assert replay["kinds"] == ["person"]
    frames = replay["frames"]
    assert [f["tick"] for f in frames] == list(range(21))
    assert [f["hash"] for f in frames] == hashes
    assert [f["dots"] for f in frames] == dots
    assert [decode_layer(replay, i) for i in range(21)] == layers
    assert len({f["hash"] for f in frames}) == 21  # the world really changed every tick
    assert dots[0] != dots[-1]  # people moved


def test_replay_export_is_deterministic(tmp_path: Path) -> None:
    a, b, c = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "c.json"
    _run(seed=11, ticks=10, path=a)
    _run(seed=11, ticks=10, path=b)
    _run(seed=12, ticks=10, path=c)
    assert a.read_bytes() == b.read_bytes()
    assert a.read_bytes() != c.read_bytes()


def _corrupt(src: Path, dst: Path, change: object) -> Path:
    data = json.loads(src.read_text())
    change(data)  # type: ignore[operator]
    dst.write_text(json.dumps(data))
    return dst


def test_load_replay_validates(tmp_path: Path) -> None:
    good = tmp_path / "good.json"
    _run(seed=11, ticks=3, path=good)
    bad = tmp_path / "bad.json"
    cases = [
        lambda d: d.update(format="aimpire-replay-v0"),
        lambda d: d.pop("run_seed"),
        lambda d: d.update(grid=[ROWS, COLS + 1]),  # layer data no longer fits
        lambda d: d["frames"][1].update(tick=1.5),  # floats never appear
        lambda d: d["frames"][0]["dots"].append([99, "dragon", 0, 0]),  # unknown kind
        lambda d: d["frames"][2].update(hash=3),
    ]
    for change in cases:
        with pytest.raises(ReplayError):
            load_replay(_corrupt(good, bad, change))
    with pytest.raises(ReplayError):
        load_replay(tmp_path / "missing.json")
