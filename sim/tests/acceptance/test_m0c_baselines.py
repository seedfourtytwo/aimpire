"""M0c acceptance: rule baselines on the calibrated petri dish, and ``aimpire run`` (backlog M0c).

Written in the planning role before the baselines and the run command
(ADR-0016). Read-only for implementers.

The calibration claim under test (``rules/v1/m0.yaml``, ``rules/v1/scale.yaml``):
a tribe that keeps its nearby places near half full lives indefinitely, and
greedy harvesting does worse. "Most seeds" is stated as k of n: seeds 1 to 10,
five game years each, at least 8 of the 10. Baselines run through the public
path a model uses: ``rule:<name>`` resolved by ``resolve_mind``, its provider
from ``build_provider``, councils by the runner every 10 ticks.

``aimpire run`` is tested through ``aimpire.cli.main``: the same arguments give
the same checkpoint hashes, replay, notebook and metrics, byte for byte; and
``--set world.gravity`` reaches both the rules hash and the physics.
"""

import asyncio
import copy
from collections.abc import Sequence
from functools import cache
from pathlib import Path

import pytest

from aimpire.cli.main import main
from aimpire.cognition.budget import BudgetGuard, Caps
from aimpire.cognition.council import Settled
from aimpire.cognition.disclosed import default_disclosed
from aimpire.cognition.m0_baselines import M0_BASELINES, m0_policy
from aimpire.cognition.minds import build_provider, resolve_mind
from aimpire.cognition.render import system_prompt
from aimpire.cognition.runner import run_with_councils
from aimpire.cognition.seats import Seat, seats_for
from aimpire.contracts.mind import MindReply, Observation
from aimpire.experiments.m0_world import build_m0_run
from aimpire.lab.variant import resolve_variant
from aimpire.persistence.store import RunStore
from aimpire.rules import load_calendar, load_m0_rules
from aimpire.sim.state import WorldState
from aimpire.sim.world.m0 import FOOD

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
CALENDAR = load_calendar(RULES_V1)
RULES = load_m0_rules(RULES_V1, CALENDAR)
SEEDS = tuple(range(1, 11))
YEARS = 5
MOST = 8  # k of n: at least 8 of the 10 seeds
EVERY = 10


class _Discard:
    """A council sink that keeps nothing (the calibration runs need only the final state)."""

    def record_council(self, tick: int, council: int, settled: Sequence[Settled]) -> None:
        pass

    def checkpoint(self, state: WorldState, label: str) -> None:
        pass


@cache
def _final_population(rule: str, seed: int) -> int:
    """People alive after ``YEARS`` game years of ``rule:<rule>`` on world ``seed``."""
    world = build_m0_run(seed, RULES_V1)
    mind = resolve_mind(f"rule:{rule}", REPO)
    seats = [Seat(civ, eid, mind, build_provider(mind)) for civ, eid in world.civs]
    build = seats_for(
        seats, calendar=world.calendar, every_ticks=EVERY, renderer="places", system=system_prompt()
    )
    asyncio.run(
        run_with_councils(
            world.state,
            world.scheduler,
            ticks=YEARS * CALENDAR.ticks_per_year,
            every_ticks=EVERY,
            checkpoint_every=CALENDAR.ticks_per_year,
            seats_for=build,
            gate=BudgetGuard(Caps()),
            sink=_Discard(),
        )
    )
    population = world.state.entities[world.civs[0][1]]["population"]
    assert type(population) is int
    return population


# --- Calibration: the baselines behave as the theory says -----------------------------


def test_half_full_survives_five_years_on_most_seeds() -> None:
    """Keeping places near half full feeds the tribe: at least 90 % alive after 5 years."""
    alive = [_final_population("half_full", seed) for seed in SEEDS]
    survived = [n for n in alive if n * 10 >= RULES.start_people * 9]
    assert len(survived) >= MOST, alive


def test_half_full_outlives_greedy_on_most_seeds() -> None:
    """Greedy over-harvest ends with fewer people than half full on at least 8 of 10 seeds."""
    pairs = [(_final_population("half_full", s), _final_population("greedy", s)) for s in SEEDS]
    assert sum(1 for half, greedy in pairs if half > greedy) >= MOST, pairs


# --- What the baselines may see -------------------------------------------------------


def _first_council(state: WorldState, civ: tuple[str, int], rule: str) -> tuple[Observation, str]:
    """The observation of council 1 and the raw reply text of ``rule:<rule>`` to it."""
    mind = resolve_mind(f"rule:{rule}", REPO)
    provider = build_provider(mind)
    build = seats_for(
        [Seat(civ[0], civ[1], mind, provider)],
        calendar=CALENDAR,
        every_ticks=EVERY,
        renderer="places",
        system=system_prompt(),
    )
    call = build(state, 1)[0]
    result = asyncio.run(provider.complete(call.request))
    assert result.status == "ok", (rule, result.status)
    assert result.parsed is not None
    return call.request.observation, result.raw_text


def test_baselines_see_only_observations() -> None:
    """Each baseline replies from the Observation alone, never from the WorldState.

    * Hidden truth changes (every wild food tile emptied after the tribe last
      looked) leave the observation and therefore the reply unchanged.
    * The policies run on an observation with no world behind it at all.
    """
    world = build_m0_run(4, RULES_V1)
    hidden = copy.deepcopy(world.state)
    hidden.layers[FOOD][...] = 0
    for rule in M0_BASELINES:
        obs, reply = _first_council(world.state, world.civs[0], rule)
        obs_hidden, reply_hidden = _first_council(hidden, world.civs[0], rule)
        assert obs == obs_hidden
        assert reply == reply_hidden, rule

        detached = Observation.model_validate_json(obs.model_dump_json())
        answer = m0_policy(rule, default_disclosed())(detached)
        assert isinstance(answer, MindReply)
        assert answer.decision_id == obs.decision_id


# --- aimpire run ------------------------------------------------------------------------


def _run(out: Path, *extra: str) -> tuple[int, Path]:
    code = main(["run", "m0", "--mind", "rule:half_full", "--seed", "3", *extra, "--out", str(out)])
    runs = sorted(out.glob("*/run.db"))
    assert len(runs) == 1
    return code, runs[0].parent


def test_run_cli_is_reproducible(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Same arguments, same checkpoint hashes, replay, notebook and metrics, byte for byte."""
    code_a, a = _run(tmp_path / "a", "--years", "1")
    out = capsys.readouterr().out
    code_b, b = _run(tmp_path / "b", "--years", "1")
    assert code_a == code_b == 0
    assert out.splitlines()[0].startswith("worst-case cost"), "the estimate is printed first"
    assert a.name == b.name
    with RunStore.open(a, read_only=True) as sa, RunStore.open(b, read_only=True) as sb:
        assert sa.checkpoints() == sb.checkpoints()
        assert len(sa.checkpoints()) > 2
        assert len(sa.decisions()) == CALENDAR.ticks_per_year // EVERY
    for name in ("replay.json", "notebook.md", "metrics.csv"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_run_cli_set_gravity_changes_rules_hash(tmp_path: Path) -> None:
    """``--set world.gravity=950000`` changes the rules hash and reaches the physics."""
    _, earth = _run(tmp_path / "earth", "--ticks", "30")
    code, light = _run(tmp_path / "light", "--ticks", "30", "--set", "world.gravity=950000")
    assert code == 0
    with RunStore.open(earth, read_only=True) as se, RunStore.open(light, read_only=True) as sl:
        me, ml = se.manifest(), sl.manifest()
        assert ml["rules_hash"] != me["rules_hash"]
        expected = resolve_variant(RULES_V1, ["world.gravity=950000"]).rules_hash
        assert ml["rules_hash"] == expected
        assert ml["config"]["variant"]["overrides"] == {"world.gravity": 950000}
        assert se.checkpoints()[-1][2] != sl.checkpoints()[-1][2], "the physics changed too"
