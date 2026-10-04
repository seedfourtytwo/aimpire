"""Property tests for the M0b work split, tile harvest and exact chance (Hypothesis)."""

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from aimpire.experiments.m0_world import build_m0_run
from aimpire.sim.fixed import chance_fraction
from aimpire.sim.places import places_by_id
from aimpire.sim.systems.forage import take_food
from aimpire.sim.systems.work import apportion
from aimpire.sim.world.m0 import FOOD

RULES_V1 = Path(__file__).resolve().parents[3] / "rules" / "v1"
WORLD = build_m0_run(1, RULES_V1)
PLACE_IDS = sorted(places_by_id(WORLD.state))


@st.composite
def policies(draw: st.DrawFn) -> list[tuple[str, str, int]]:
    """Distinct (activity, place) lines whose shares sum to at most 1000."""
    keys = draw(
        st.lists(
            st.tuples(st.sampled_from(["FORAGE", "SCOUT"]), st.sampled_from(PLACE_IDS)),
            unique=True,
            max_size=6,
        )
    )
    left, lines = 1000, []
    for activity, place in keys:
        share = draw(st.integers(0, left))
        left -= share
        lines.append((activity, place, share))
    return lines


@given(st.integers(0, 10_000), policies())
def test_apportion_is_exact_and_fair(workers: int, lines: list[tuple[str, str, int]]) -> None:
    split = apportion(workers, lines)
    total_share = sum(s for *_, s in lines)
    assert sum(n for *_, n in split) == workers * total_share // 1000
    shares = {(a, p): s for a, p, s in lines}
    for activity, place, n in split:
        exact = workers * shares[(activity, place)]
        assert exact // 1000 <= n <= exact // 1000 + 1
    assert apportion(workers, list(reversed(lines))) == split, "input order never matters"


@settings(max_examples=50)
@given(st.sampled_from(PLACE_IDS), st.integers(0, 10**10))
def test_take_food_conserves_and_never_goes_negative(place_id: str, wanted: int) -> None:
    state = WORLD.state
    layer = state.layers[FOOD]
    saved = layer.copy()
    try:
        place = places_by_id(state)[place_id]
        before = int(layer.sum())
        taken = take_food(state, place, wanted)
        assert 0 <= taken <= wanted
        assert int(layer.sum()) == before - taken
        assert int(layer.min()) >= 0
    finally:
        layer[...] = saved


@given(st.integers(0, 2**64 - 1), st.integers(1, 2**40))
def test_chance_fraction_bounds(u: int, denom: int) -> None:
    assert not chance_fraction(u, 0, denom)
    assert chance_fraction(u, denom, denom)
