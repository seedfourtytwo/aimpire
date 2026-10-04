"""W0 acceptance: world constants in, derived rates out (ADR-0020).

Written before the code, in the planning role (ADR-0016). Read-only for implementers.

The laws are pure integer functions: at Earth constants every derived rate is
exactly 1_000_000 ppm, each law moves in the direction physics says, and a
constant outside a law's validated range is flagged ``beyond_model``.
"""

import ast
import dataclasses
import shutil
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aimpire.rules import RulesError, load_world, rules_hash
from aimpire.rules.physics import derive_world
from aimpire.rules.world import EARTH, WorldConstants

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
SRC = REPO / "sim" / "src" / "aimpire"

# Rates that rise with gravity, and rates that fall with it (research note 90).
RISE_WITH_G = ("walk_speed", "walk_energy", "water_speed", "fall_harm")
FALL_WITH_G = ("carry_load", "tree_height", "throw_range")

# Allowed ranges from the knob registry: wide enough to probe every law.
GRAVITY = st.integers(min_value=100_000, max_value=10_000_000)
TILT = st.integers(min_value=0, max_value=90_000)
LIGHT = st.integers(min_value=0, max_value=5_000_000)


def _rates(derived: object) -> dict[str, int]:
    """Every ppm field of a ``DerivedWorld``, by name (``beyond_model`` excluded)."""
    assert dataclasses.is_dataclass(derived)
    return {
        f.name: getattr(derived, f.name)
        for f in dataclasses.fields(derived)
        if f.name != "beyond_model"
    }


def _world(**changes: int) -> WorldConstants:
    return dataclasses.replace(EARTH, **changes)


def test_earth_constants_are_identity() -> None:
    """rules/v1/world.yaml is Earth, and Earth gives exactly 1_000_000 for every law."""
    world = load_world(RULES_V1)
    assert world == EARTH
    assert world == WorldConstants(
        gravity=1_000_000, sunlight=1_000_000, rain=1_000_000, tilt=23_440
    )
    derived = derive_world(world)
    rates = _rates(derived)
    assert set(RISE_WITH_G + FALL_WITH_G) | {"season_strength", "plant_ceiling"} <= set(rates)
    assert rates == dict.fromkeys(rates, 1_000_000)
    assert derived.beyond_model == ()


def test_known_values_at_0_95_g() -> None:
    """√0.95 = 0.974679…; 1/0.95 = 1.052631…; to within one ppm of rounding."""
    derived = derive_world(_world(gravity=950_000))
    assert abs(derived.walk_speed - 974_679) <= 1
    assert abs(derived.carry_load - 1_052_631) <= 1
    assert derived.walk_energy == 950_000
    assert derived.fall_harm == 950_000
    # g^(-1/3) at 0.95 g is 1.017244…
    assert abs(derived.tree_height - 1_017_244) <= 1


def _pair(values: st.SearchStrategy[int]) -> st.SearchStrategy[tuple[int, int]]:
    """Two draws, smaller first."""
    return st.tuples(values, values).map(lambda p: (min(p), max(p)))


@given(_pair(GRAVITY), _pair(TILT), _pair(LIGHT), _pair(LIGHT))
def test_laws_are_monotonic(
    gravity: tuple[int, int], tilt: tuple[int, int], sun: tuple[int, int], rain: tuple[int, int]
) -> None:
    """Each law moves one way only, so a bigger constant never reverses a trade-off."""
    (lo_g, hi_g), (lo_t, hi_t), (lo_s, hi_s), (lo_r, hi_r) = gravity, tilt, sun, rain
    low = _rates(derive_world(_world(gravity=lo_g)))
    high = _rates(derive_world(_world(gravity=hi_g)))
    for name in RISE_WITH_G:
        assert low[name] <= high[name], name
    for name in FALL_WITH_G:
        assert low[name] >= high[name], name

    assert (
        derive_world(_world(tilt=lo_t)).season_strength
        <= derive_world(_world(tilt=hi_t)).season_strength
    )

    ceiling = derive_world(_world(sunlight=lo_s, rain=lo_r)).plant_ceiling
    assert ceiling <= derive_world(_world(sunlight=hi_s, rain=lo_r)).plant_ceiling
    assert ceiling <= derive_world(_world(sunlight=lo_s, rain=hi_r)).plant_ceiling
    assert ceiling == min(lo_s, lo_r)


def test_derivation_uses_no_floats() -> None:
    """No float literal, true division, ``float`` or float maths anywhere in the derivation.

    Derived values are hashed, so they must be bit-exact on every platform
    (ADR-0007, ADR-0020): ``math.isqrt``, an integer cube root and a sine table only.
    """
    modules = [*sorted((SRC / "rules").glob("*.py")), SRC / "sim" / "derived.py"]
    float_maths = {"sqrt", "pow", "sin", "cos", "tan", "exp", "log", "cbrt", "radians", "fsum"}
    problems: list[str] = []
    for path in modules:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            where = f"{path.name}:{getattr(node, 'lineno', '?')}"
            if isinstance(node, ast.Constant) and type(node.value) in (float, complex):
                problems.append(f"{where} float literal")
            elif isinstance(node, ast.BinOp | ast.AugAssign) and isinstance(node.op, ast.Div):
                problems.append(f"{where} true division")
            elif isinstance(node, ast.Name) and node.id in {"float", "Decimal", "Fraction"}:
                problems.append(f"{where} {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr in float_maths:
                problems.append(f"{where} {node.attr}")
    assert not problems, problems

    for rate in _rates(derive_world(_world(gravity=950_000, tilt=30_000))).values():
        assert type(rate) is int


def test_beyond_validated_range_is_flagged() -> None:
    """Outside a law's validated range the value is still derived, and named in beyond_model."""
    low_g = derive_world(_world(gravity=300_000))  # below walking's 0.4 g
    assert "walk_speed" in low_g.beyond_model
    assert "walk_energy" in low_g.beyond_model
    assert "water_speed" not in low_g.beyond_model  # Chézy and Manning: any g
    assert low_g.walk_speed > 0

    steep = derive_world(_world(tilt=60_000))  # the sine law is validated to 45 degrees
    assert steep.beyond_model == ("season_strength",)

    inside = derive_world(_world(gravity=900_000, tilt=30_000))
    assert inside.beyond_model == ()


def test_rules_hash_covers_world_yaml(tmp_path: Path) -> None:
    """Editing world.yaml changes the rules hash; the same files give the same hash."""
    copy = tmp_path / "v1"
    shutil.copytree(RULES_V1, copy)
    assert rules_hash(copy) == rules_hash(RULES_V1)
    world_file = copy / "world.yaml"
    text = world_file.read_text(encoding="utf-8")
    world_file.write_text(text.replace("gravity: 1_000_000", "gravity: 950_000"), encoding="utf-8")
    assert load_world(copy).gravity == 950_000
    assert rules_hash(copy) != rules_hash(RULES_V1)


@pytest.mark.parametrize(
    "line",
    ["gravity: 0.95", "gravity: true", "gravity: -1", "gravity: '1000000'", "moons: 1"],
)
def test_loader_refuses_bad_constants(tmp_path: Path, line: str) -> None:
    """Integers only, no negatives, no unknown or missing names: refused, never coerced."""
    base = {"gravity": "1_000_000", "sunlight": "1_000_000", "rain": "1_000_000", "tilt": "23_440"}
    key = line.split(":", 1)[0]
    lines = [f"{k}: {v}" for k, v in base.items() if k != key] + [line]
    (tmp_path / "world.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(RulesError):
        load_world(tmp_path)
