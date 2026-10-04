"""M0a acceptance: the petri dish world and food regrowth (backlog M0a).

Written before the code, in the planning role (ADR-0016). Read-only for implementers.

The rule under test, per tick and per tile, with r and s per tick:
    dF = r F (K - F) / K + s (K - F),   never above K,
computed in integers with a carried remainder. The tests compare it with the
theory it claims: its own exact recurrence, the continuous closed form, the
time to fill an empty map, and where the steady yield under a constant
harvest fraction peaks. Floats appear only here, in the reference
calculations, never in the simulation.
"""

import dataclasses
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from aimpire.lab.variant import resolve_variant
from aimpire.rules import load_calendar, load_m0_rules
from aimpire.sim.calendar import Calendar
from aimpire.sim.fixed import PPM, apply_rate_array
from aimpire.sim.hashing import state_hash
from aimpire.sim.ledger import layer_total
from aimpire.sim.places import places_by_id
from aimpire.sim.presets import PRESETS, m0_quantities, system_registry
from aimpire.sim.scheduler import Cadence, Preset, Scheduler, SystemSpec, TickContext
from aimpire.sim.state import WorldState
from aimpire.sim.world import M0Rules
from aimpire.sim.world.m0 import CEILING, FERTILITY, FOOD, build_m0_world

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
CALENDAR = load_calendar(RULES_V1)
RULES = load_m0_rules(RULES_V1, CALENDAR)


def _per_tick(rules: M0Rules, calendar: Calendar) -> tuple[float, float]:
    """r and s as plain per-tick fractions, for the reference calculations only."""
    r_ppm, r_per = rules.regrowth_rate.resolve(calendar)
    s_ppm, s_per = rules.regrowth_seed.resolve(calendar)
    return r_ppm / (PPM * r_per), s_ppm / (PPM * s_per)


def _world(seed: int = 1, settings: tuple[str, ...] = (), rules: M0Rules = RULES) -> WorldState:
    resolved = resolve_variant(RULES_V1, settings)
    return build_m0_world(
        seed, rules, resolved.derived, rules_version="v1", rules_hash=resolved.rules_hash
    )


def _set_food(state: WorldState, fraction_ppm: int) -> None:
    """Set every tile to a fraction of its ceiling (floor), with zero carries."""
    state.layers[FOOD][...] = state.layers[CEILING] * fraction_ppm // PPM
    state.carries[FOOD][...] = 0


@dataclass
class _Harvest:
    """Test-only rule: take a fixed fraction of every tile's food each tick."""

    fraction_ppm: int
    taken: int = 0
    carry: np.ndarray | None = None
    name: str = "test_harvest"
    cadence: Cadence = "tick"
    sequential: bool = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        if self.carry is None:
            self.carry = np.zeros_like(state.layers[FOOD])
        take, self.carry = apply_rate_array(state.layers[FOOD], self.fraction_ppm, 1, self.carry)
        state.layers[FOOD] -= take
        self.taken += int(take.sum())
        ctx.ledger.record("food", -int(take.sum()), "HARVEST")


def _scheduler(extra: tuple[_Harvest, ...] = (), checked: bool = False) -> Scheduler:
    registry = dict(system_registry(RULES))
    names = [spec.name for spec in PRESETS["m0"].systems]
    for system in extra:
        registry[system.name] = lambda _params, s=system: s
        names.append(system.name)
    preset = Preset("m0-test", [SystemSpec(n) for n in names])
    return Scheduler(preset, registry, CALENDAR, quantities=m0_quantities() if checked else None)


def test_m0_preset_is_registered() -> None:
    """The preset names regrowth, and the registry can build every system it names."""
    preset = PRESETS["m0"]
    assert preset.name == "m0"
    assert "regrowth" in [spec.name for spec in preset.systems]
    Scheduler(preset, system_registry(RULES), CALENDAR)


def test_worldgen_is_deterministic() -> None:
    """Same seed, same world hash; different seeds, different fertility."""
    a, b, c = _world(1), _world(1), _world(2)
    assert state_hash(a) == state_hash(b)
    assert state_hash(a) != state_hash(c)
    assert not np.array_equal(a.layers[FERTILITY], c.layers[FERTILITY])
    assert a.layers[FOOD].shape == (RULES.rows, RULES.cols)
    fert = a.layers[FERTILITY]
    assert RULES.fertility_min <= int(fert.min()) <= int(fert.max()) <= RULES.fertility_max
    assert len(places_by_id(a)) == (RULES.rows // RULES.place_block) * (
        RULES.cols // RULES.place_block
    )
    assert np.array_equal(a.layers[FOOD], a.layers[CEILING] * RULES.initial_food // PPM)


def test_empty_map_settles_at_ceiling() -> None:
    """From zero food, every tile is within 1 % of K by the predicted time.

    Prediction: the continuous solution of dx/dt = (1 - x)(r x + s) from x = 0
    gives (r x + s) / (1 - x) = s e^((r + s) t), so x reaches 0.99 at
    T = ln((0.99 r + s) / (0.01 s)) / (r + s). The integer rule may take 5 %
    longer; and it must not be done at 0.9 T, so the prediction is not loose.
    """
    r, s = _per_tick(RULES, CALENDAR)
    predicted = math.log((0.99 * r + s) / (0.01 * s)) / (r + s)
    state = _world(3)
    _set_food(state, 0)
    sched = _scheduler()
    early = math.floor(0.9 * predicted)
    sched.run(state, early)
    ceiling = state.layers[CEILING]
    assert int(state.layers[FOOD].sum()) < 0.99 * int(ceiling.sum())
    sched.run(state, math.ceil(1.05 * predicted) - early)
    food = state.layers[FOOD]
    assert np.all(food * 100 >= ceiling * 99)
    assert np.all(food <= ceiling)


def test_regrowth_matches_closed_form() -> None:
    """One tile follows the exact integer recurrence, the real recurrence and the closed form.

    * Exactly: an independent pure-int implementation of the stated rule,
      numerator (K - F)(r F + s K) over denominator K * PPM * ticks, with the
      remainder carried.
    * Within 3 milli-units: the same recurrence in real numbers (the carry
      keeps rounding from accumulating).
    * Within 2 % of K: the continuous logistic-plus-seed solution
      x(t) = (A e^((r+s)t) - s) / (r + A e^((r+s)t)), A = (r x0 + s) / (1 - x0).
    """
    state = _world(4)
    _set_food(state, 100_000)
    row, col = 21, 42
    k = int(state.layers[CEILING][row, col])
    food = int(state.layers[FOOD][row, col])
    carry = 0
    real = float(food)
    x0 = food / k
    r_ppm, r_per = RULES.regrowth_rate.resolve(CALENDAR)
    s_ppm, s_per = RULES.regrowth_seed.resolve(CALENDAR)
    assert r_per == s_per, "this reference assumes one period for r and s"
    denom = k * PPM * r_per
    r, s = _per_tick(RULES, CALENDAR)
    a = (r * x0 + s) / (1 - x0)
    sched = _scheduler()
    for t in range(1, 361):
        sched.step(state)
        gap = k - food
        delta, carry = divmod(gap * (r_ppm * food + s_ppm * k) + carry, denom)
        food += min(delta, gap)
        real += (k - real) * (r * real + s * k) / k
        growth = a * math.exp((r + s) * t)
        closed = k * (growth - s) / (r + growth)
        got = int(state.layers[FOOD][row, col])
        assert got == food, f"tick {t}"
        assert abs(got - real) <= 3, f"tick {t}"
        assert abs(got - closed) <= 0.02 * k, f"tick {t}"
    assert food == k


def test_constant_harvest_sweep_peaks_near_half_full() -> None:
    """The steady yield of a constant harvest fraction peaks at x* = (1 - s/r) / 2.

    Theory: at steady state the harvest equals regrowth at the stock left
    after harvest, Y(x) = K (r x (1 - x) + s (1 - x)), which is largest at
    x* = (1 - s / r) / 2 (49.4 % with the v1 rules), giving Y* = K (r + s)^2 / (4 r).
    Sweep: fractions from 2 % to 7 % a tick in steps of 0.1 %, on one 16 x 16
    place, 600 ticks to settle and 120 to measure. Tolerance: the stock at
    the best fraction is within 2 percentage points of x*, and its yield
    within 1 % of Y*. One sweep step moves the steady stock by about 1.25
    points, so the tolerance allows for the step but not for a wrong peak.
    """
    rules = dataclasses.replace(RULES, rows=16, cols=16)
    r, s = _per_tick(rules, CALENDAR)
    x_star = (1 - s / r) / 2
    best: tuple[int, int, float] = (-1, 0, 0.0)
    total_k = 0
    fractions = range(20_000, 70_001, 1_000)
    for fraction in fractions:
        state = _world(5, rules=rules)
        total_k = int(state.layers[CEILING].sum())
        harvest = _Harvest(fraction)
        sched = _scheduler((harvest,))
        sched.run(state, 600)
        harvest.taken = 0
        stock = 0
        for _ in range(120):
            sched.step(state)
            stock += int(state.layers[FOOD].sum())
        if harvest.taken > best[0]:
            best = (harvest.taken, fraction, stock / 120 / total_k)
    taken, fraction, x_best = best
    assert fraction not in (fractions[0], fractions[-1]), "the peak must be inside the sweep"
    assert abs(x_best - x_star) <= 0.02
    y_star = total_k * (r + s) ** 2 / (4 * r)
    assert abs(taken / 120 - y_star) <= 0.01 * y_star


def test_ledger_balances_every_tick() -> None:
    """Checked mode: every change to food is recorded as REGROWTH, and the totals agree."""
    state = _world(6)
    _set_food(state, 100_000)
    start = int(state.layers[FOOD].sum())
    sched = _scheduler(checked=True)
    sched.run(state, 240)
    assert {e.kind for e in sched.ledger.entries} == {"REGROWTH"}
    assert {e.material for e in sched.ledger.entries} == {"food"}
    assert sched.ledger.net("food") == layer_total(FOOD)(state) - start
    assert sched.ledger.net("food") > 0


def test_gravity_changes_ceiling_only_through_w0() -> None:
    """K = ceiling x W0 plant_ceiling x fertility / PPM^2 (floor); gravity is not in it.

    Rain and sunlight move the ceiling through W0's law of the minimum;
    gravity changes neither the ceiling nor the fertility map.
    """
    earth = _world(7)
    fert = earth.layers[FERTILITY]

    def expected(plant_ceiling: int) -> np.ndarray:
        return RULES.food_ceiling * plant_ceiling * fert // (PPM * PPM)

    assert np.array_equal(earth.layers[CEILING], expected(PPM))
    heavy = _world(7, ("world.gravity=1500000",))
    assert np.array_equal(heavy.layers[FERTILITY], fert)
    assert np.array_equal(heavy.layers[CEILING], earth.layers[CEILING])
    dry = _world(7, ("world.rain=600000",))
    assert np.array_equal(dry.layers[CEILING], expected(600_000))
    dim_dry = _world(7, ("world.sunlight=800000", "world.rain=600000"))
    assert np.array_equal(dim_dry.layers[CEILING], dry.layers[CEILING])
    bright = _world(7, ("world.sunlight=1500000", "world.rain=1500000"))
    assert np.array_equal(bright.layers[CEILING], expected(1_500_000))
