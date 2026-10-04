"""F2c acceptance: the calendar is data and rates state their period (ADR-0011).

Written by the planning model before implementation (ADR-0016). Read-only.
"""

import ast
from pathlib import Path

import pytest

from aimpire.rules import RulesError, load_calendar
from aimpire.sim.calendar import Calendar, Rate
from aimpire.sim.fixed import PPM, apply_rate

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
SIM_PACKAGE = REPO / "sim" / "src" / "aimpire" / "sim"


def test_default_calendar_is_120_ticks() -> None:
    """rules/v1 sets 30-tick seasons and 4 seasons: a 120-tick year."""
    cal = load_calendar(RULES_V1)
    assert cal == Calendar(ticks_per_season=30, seasons_per_year=4)
    assert cal.ticks_per_year == 120


def test_calendar_loaded_from_rules() -> None:
    """The loader reads the rules file; the simulation package holds no calendar literal."""
    assert load_calendar(RULES_V1).ticks_per_season == 30
    found = [hit for p in sorted(SIM_PACKAGE.rglob("*.py")) for hit in _calendar_literals(p)]
    assert not found, f"season or year length hardcoded in aimpire.sim: {found}"


def _calendar_literals(path: Path) -> list[str]:
    """Integer literals 30 or 120 in code, ignoring bit-shift amounts such as ``z >> 30``
    or ``z >> np.uint64(30)``."""
    tree = ast.parse(path.read_text())
    shifts = {
        id(sub)
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.RShift | ast.LShift)
        for sub in ast.walk(node.right)
    }
    return [
        f"{path.name}:{node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and type(node.value) is int
        and node.value in (30, 120)
        and id(node) not in shifts
    ]


def test_calendar_positions() -> None:
    cal = Calendar(ticks_per_season=30, seasons_per_year=4)
    assert [cal.season_of(t) for t in (0, 29, 30, 119, 120)] == [0, 0, 1, 3, 0]
    assert [cal.year_of(t) for t in (0, 119, 120, 359, 360)] == [0, 0, 1, 2, 3]
    assert [t for t in range(250) if cal.is_season_start(t)] == [
        0,
        30,
        60,
        90,
        120,
        150,
        180,
        210,
        240,
    ]
    assert [t for t in range(400) if cal.is_year_start(t)] == [0, 120, 240, 360]
    with pytest.raises(ValueError):
        cal.season_of(-1)


@pytest.mark.parametrize("bad", [(0, 4), (30, 0), (-1, 4)])
def test_calendar_rejects_bad_lengths(bad: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        Calendar(ticks_per_season=bad[0], seasons_per_year=bad[1])


def test_rate_resolution() -> None:
    cal = Calendar(ticks_per_season=30, seasons_per_year=4)
    assert Rate(ppm=10_000, per="year").resolve(cal) == (10_000, 120)
    assert Rate(ppm=10_000, per="season").resolve(cal) == (10_000, 30)
    assert Rate(ppm=10_000, per="tick").resolve(cal) == (10_000, 1)
    with pytest.raises(ValueError):
        Rate(ppm=-1, per="year")
    with pytest.raises(ValueError):
        Rate(ppm=1, per="month")  # pyright: ignore[reportArgumentType]


def test_yearly_rate_applied_over_a_year_is_exact() -> None:
    """A 1% per-year rate on 1,000 milli-units yields exactly 10 over one calendar year."""
    cal = Calendar(ticks_per_season=30, seasons_per_year=4)
    ppm, per_ticks = Rate(ppm=PPM // 100, per="year").resolve(cal)
    carry, total = 0, 0
    for _ in range(cal.ticks_per_year):
        delta, carry = apply_rate(1_000, ppm, per_ticks, carry)
        total += delta
    assert total == 10


def test_rate_from_rules_mapping() -> None:
    assert Rate.from_mapping({"ppm": 2_500, "per": "season"}) == Rate(ppm=2_500, per="season")
    with pytest.raises(ValueError):
        Rate.from_mapping({"ppm": 2_500})
    with pytest.raises(ValueError):
        Rate.from_mapping({"ppm": 2.5, "per": "year"})  # floats never enter state


def test_loader_rejects_unknown_or_missing_keys(tmp_path: Path) -> None:
    (tmp_path / "calendar.yaml").write_text("ticks_per_season: 30\nseasons_per_year: 4\nextra: 1\n")
    with pytest.raises(RulesError):
        load_calendar(tmp_path)
    (tmp_path / "calendar.yaml").write_text("ticks_per_season: 30\n")
    with pytest.raises(RulesError):
        load_calendar(tmp_path)
