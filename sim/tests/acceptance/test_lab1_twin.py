"""LAB1 acceptance: twin worlds, and travel days that match the physics (ADR-0020, backlog LAB1).

Written before the code, in the planning role (ADR-0016). Read-only for implementers.

A twin runs the baseline (no overrides at all) and a variant on the same
seeds with the same mind, compares the two states part by part after every
tick (``subsystem_hashes``) and writes one report. The ``meta`` part holds
the rules hash, which a variant changes by construction, so the first
divergence is looked for in the world's own parts (layers, carries, entities).

The last test pins a physics-consistency fix: the travel days a mind is shown
are the days a walk takes in its world, at the W0 walking speed, still over
known places only.
"""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from aimpire.cli.main import main
from aimpire.cognition.minds import resolve_mind
from aimpire.cognition.render import system_prompt
from aimpire.cognition.seats import Seat, seat_from_observation, seats_for
from aimpire.contracts.mind import Observation
from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.worlds import World
from aimpire.persistence.store import RunStore
from aimpire.sim.actions import DecisionLog, validate_reply
from aimpire.sim.actions.commit import commit_decision
from aimpire.sim.hashing import subsystem_hashes
from aimpire.sim.places import places_by_id, travel_ticks

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
GRAVITY_095 = "world.gravity=950000"
GRAVITY_06 = "world.gravity=600000"


def _twin(out: Path, *args: str) -> tuple[int, Path]:
    """Run ``aimpire lab twin m0`` into ``out``; return the exit code and the report folder."""
    argv = ["lab", "twin", "m0", "--mind", "rule:half_full", "--out", str(out), *args]
    code = main(argv)
    reports = sorted(p.parent for p in out.glob("*/twin.md"))
    assert len(reports) == 1, f"one twin report expected, found {reports}"
    return code, reports[0]


def _data(report: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads((report / "twin.json").read_text()))


def test_twin_with_no_override_never_diverges(tmp_path: Path) -> None:
    """With no override the two sides are the same world: no tick and no part ever differs."""
    code, report = _twin(tmp_path, "--seeds", "1-2", "--ticks", "60")
    assert code == 0
    data = _data(report)
    assert [d["seed"] for d in data["divergence"]] == [1, 2]
    for row in data["divergence"]:
        assert row["first_tick"] is None
        assert row["first_parts"] == []
        assert row["final_parts"] == []
    finals: dict[int, set[str]] = {}
    for run in data["runs"]:
        finals.setdefault(run["seed"], set()).add(run["final_hash"])
    assert sorted(finals) == [1, 2]
    assert all(len(hashes) == 1 for hashes in finals.values()), "same final hash on both sides"
    assert "never" in (report / "twin.md").read_text()


def test_gravity_twin_diverges_and_names_first_part(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """At 0.95 g every seed diverges; the report names the tick and the world part(s) first hit."""
    code, report = _twin(tmp_path, "--seeds", "1-2", "--ticks", "120", "--set", GRAVITY_095)
    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines()[0].startswith("worst-case cost"), "the estimate is printed first"
    assert "pre-registered" in out, "the ADR-0014 reminder is printed"

    layers = {p for p in subsystem_hashes(build_m0_run(1, RULES_V1).state) if p != "meta"}
    data = _data(report)
    text = (report / "twin.md").read_text()
    assert [d["seed"] for d in data["divergence"]] == [1, 2]
    for row in data["divergence"]:
        assert isinstance(row["first_tick"], int)
        assert 0 <= row["first_tick"] <= 120
        assert row["first_parts"], "at least one part is named"
        for part in row["first_parts"]:
            assert part in layers or part.startswith("entities:"), f"{part} is a world part"
        assert row["first_parts"] == sorted(row["first_parts"])
        for part in row["first_parts"]:
            assert part in text

    laws = {row["law"]: row for row in data["physics"]}
    assert laws["walk_speed"]["ppm"] == 974_679  # round(sqrt(0.95) * 1e6)
    assert laws["carry_load"]["ppm"] == 1_052_632  # round(1e6 / 0.95)
    assert all(row["beyond_model"] is False for row in data["physics"])
    assert "walk_speed" in text

    for run in data["runs"]:
        with RunStore.open(tmp_path / run["run_id"], read_only=True) as store:
            manifest = store.manifest()
        assert "exploratory" in manifest["config"]["tags"], run["run_id"]
        assert manifest["config"]["twin"]["side"] == run["side"]
    sides = {(r["seed"], r["side"]) for r in data["runs"]}
    assert sides == {(s, side) for s in (1, 2) for side in ("baseline", "variant")}


def test_twin_report_is_reproducible(tmp_path: Path) -> None:
    """Same arguments, byte-identical report, data and charts in two different folders."""
    args = ("--seeds", "3", "--ticks", "60", "--set", GRAVITY_095)
    code_a, a = _twin(tmp_path / "a", *args)
    code_b, b = _twin(tmp_path / "b", *args)
    assert code_a == code_b == 0
    files_a = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert files_a == files_b
    assert any(p.suffix == ".svg" for p in files_a), "the report has charts"
    for rel in files_a:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def _observe(world: World) -> Observation:
    """The observation of council 1, built by the run's own seat builder."""
    civ_id, entity_id = world.civs[0]
    mind = resolve_mind("mock", REPO)
    build = seats_for(
        [Seat(civ_id, entity_id, mind, provider=cast(Any, None))],
        calendar=world.calendar,
        every_ticks=10,
        renderer="places",
        system=system_prompt(),
        walk_speed=world.walk_speed,
    )
    return build(world.state, 1)[0].request.observation


def test_observation_travel_matches_simulated_travel() -> None:
    """At 0.6 g the days shown to reach a neighbour equal the ticks a MOVE_CAMP there takes."""
    world = build_m0_run(1, RULES_V1, settings=(GRAVITY_06,), checked=True)
    state = world.state
    civ = cast(dict[str, Any], state.entities[world.civs[0][1]])
    camp = str(civ["camp"])
    dest = places_by_id(state)[camp].neighbours[0]
    obs = _observe(world)
    shown = {p.place_id: p.travel_ticks for p in obs.places}
    assert dest in shown, "the neighbour is known at the start"
    assert shown[dest] > travel_ticks(state, camp, dest), "0.6 g walks slower than Earth"

    reply: dict[str, Any] = {
        "decision_id": obs.decision_id,
        "policy": {"allocations": [], "ration": 1000},
        "orders": [{"kind": "MOVE_CAMP", "place": dest, "target": "", "qty": 0, "text": ""}],
        "messages": [],
        "commitments": [],
        "beliefs": [],
        "names": [],
        "journal": "",
        "annal": "",
    }
    record = validate_reply(
        state, obs.civ_id, obs.version, reply, seat=seat_from_observation(obs), log=DecisionLog()
    )
    commit_decision(state, world.civs[0][1], record)
    world.scheduler.step(state)
    times = list(civ["task_times"].values())
    assert len(times) == 1, "one task: the move"
    start, arrive, _ = times[0]
    assert arrive - start == shown[dest], "the move takes the days the mind was shown"
    while civ["camp"] == camp:
        assert state.tick <= arrive, "the camp arrives when the move says"
        world.scheduler.step(state)
    assert state.tick == arrive + 1, "arrival is recorded in the step after the last walking day"
