"""Unit tests for ``m0.yaml`` and the typed ``M0Rules`` record (backlog M0a)."""

import copy
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from aimpire.rules import RulesError, load_calendar, load_m0_rules, rules_hash
from aimpire.sim.calendar import Calendar, Flow, Rate
from aimpire.sim.fixed import PPM
from aimpire.sim.world import M0Rules

RULES_V1 = Path(__file__).resolve().parents[3] / "rules" / "v1"
CALENDAR = Calendar(ticks_per_season=30, seasons_per_year=4)


def _raw() -> dict[str, Any]:
    data = yaml.safe_load((RULES_V1 / "m0.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write(tmp_path: Path, data: dict[str, Any]) -> Path:
    for name in ("calendar.yaml", "world.yaml"):
        shutil.copy(RULES_V1 / name, tmp_path / name)
    (tmp_path / "m0.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return tmp_path


def test_v1_values_load_as_documented() -> None:
    rules = load_m0_rules(RULES_V1, load_calendar(RULES_V1))
    assert (rules.rows, rules.cols, rules.place_block) == (64, 64, 16)
    assert rules.food_ceiling == 10_000
    assert rules.initial_food == PPM
    assert (rules.fertility_min, rules.fertility_max, rules.fertility_cell) == (
        300_000,
        1_000_000,
        16,
    )
    assert rules.regrowth_rate == Rate(2_400_000, "season")
    assert rules.regrowth_seed == Rate(30_000, "season")
    assert rules.food_need == Flow(1_000, "tick")
    assert (rules.start_people, rules.start_stores) == (30, 900_000)
    assert rules.starvation_death == Rate(50_000, "tick")
    assert rules.store_spoilage == Rate(600_000, "season")
    assert rules.carry_per_trip == 10_000
    assert rules.walk_energy == Flow(500, "tick")
    assert rules.scout_sight == 16


def test_every_value_is_an_int_or_a_period_record() -> None:
    rules = load_m0_rules(RULES_V1, CALENDAR)
    for name in M0Rules.__slots__:  # pyright: ignore[reportAttributeAccessIssue]
        value = getattr(rules, name)
        assert type(value) is int or isinstance(value, Rate | Flow), name


def test_rules_hash_covers_m0_yaml(tmp_path: Path) -> None:
    base = rules_hash(_write(tmp_path, _raw()))
    changed = _raw()
    changed["food"]["ceiling"] = 10_001
    assert rules_hash(_write(tmp_path, changed)) != base
    assert rules_hash(_write(tmp_path, _raw())) == base


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("food", "ceiling", 10.5, "integer"),
        ("food", "ceiling", "10000", "integer"),
        ("food", "ceiling", True, "integer"),
        ("food", "ceiling", -1, "non-negative"),
        ("food", "initial", PPM + 1, "ppm"),
        ("map", "rows", 0, "positive"),
        ("map", "place_block", 65, "larger than the map"),
        ("fertility", "min", 1_000_001, "ppm"),
        ("regrowth", "rate", {"ppm": 2.5, "per": "season"}, "ppm must be an int"),
        ("regrowth", "rate", {"ppm": 2_400_000, "per": "week"}, "per must be"),
        ("regrowth", "rate", {"ppm": 31_000_000, "per": "season"}, "at most 1_000_000"),
        ("people", "starvation_death", {"ppm": 1_000_001, "per": "tick"}, "at most"),
        ("people", "need", {"ppm": 1_000, "per": "tick"}, "expected keys"),
    ],
)
def test_bad_values_are_refused(
    tmp_path: Path, section: str, key: str, value: object, message: str
) -> None:
    data = _raw()
    data[section][key] = value
    with pytest.raises(RulesError, match=message):
        load_m0_rules(_write(tmp_path, data), CALENDAR)


def test_fertility_range_must_be_ordered(tmp_path: Path) -> None:
    data = _raw()
    data["fertility"]["min"], data["fertility"]["max"] = 900_000, 400_000
    with pytest.raises(RulesError, match="must not exceed"):
        load_m0_rules(_write(tmp_path, data), CALENDAR)


def test_unknown_or_missing_keys_are_refused(tmp_path: Path) -> None:
    extra = _raw()
    extra["food"]["colour"] = 3
    with pytest.raises(RulesError, match=r"unknown \['colour'\]"):
        load_m0_rules(_write(tmp_path, extra), CALENDAR)
    missing = copy.deepcopy(_raw())
    del missing["scout"]
    with pytest.raises(RulesError, match=r"missing \['scout'\]"):
        load_m0_rules(_write(tmp_path, missing), CALENDAR)


def test_missing_file_is_a_rules_error(tmp_path: Path) -> None:
    with pytest.raises(RulesError, match="cannot read"):
        load_m0_rules(tmp_path, CALENDAR)


def test_flow_resolves_its_period() -> None:
    assert Flow(1_000, "tick").resolve(CALENDAR) == (1_000, 1)
    assert Flow(1_000, "season").resolve(CALENDAR) == (1_000, 30)
    assert Flow(1_000, "year").resolve(CALENDAR) == (1_000, 120)
    with pytest.raises(ValueError, match="non-negative"):
        Flow(-1, "tick")
