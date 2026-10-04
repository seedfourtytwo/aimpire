"""Unit tests for the knob registry, overrides and variants (LAB0) beyond the acceptance set."""

import argparse
from pathlib import Path

import pytest

from aimpire.lab.knobs import KNOBS, Knob, KnobError, Layer, get_knob
from aimpire.lab.overrides import add_set_option, parse_sets
from aimpire.lab.variant import resolve_variant
from aimpire.rules import RulesError, load_world
from aimpire.rules.physics import validated_range
from aimpire.rules.world import EARTH, NAMES, apply_overrides

RULES_V1 = Path(__file__).resolve().parents[3] / "rules" / "v1"


def test_world_knob_ranges_follow_the_laws() -> None:
    """A world knob's validated range is where every law reading it is validated."""
    for name in NAMES:
        knob = get_knob(f"world.{name}")
        assert knob.allowed is not None
        assert (knob.validated or knob.allowed) == (validated_range(name) or knob.allowed)


def test_unknown_knob_message_lists_the_layer() -> None:
    with pytest.raises(KnobError, match=r"world knobs: world\.gravity"):
        get_knob("world.gravityy")
    with pytest.raises(KnobError, match=r"unknown knob 'nothing'"):
        get_knob("nothing")


def test_display_knob_is_not_hashed() -> None:
    """A display knob parses like any other but never enters the rules hash."""
    knob = Knob(
        path="display.frame_rate",
        layer=Layer.DISPLAY,
        kind="int",
        unit="frames per second",
        default=30,
        allowed=(1, 120),
        description="Replay frame rate.",
    )
    assert not knob.in_rules_hash
    assert knob.parse("60") == 60
    assert all(k.layer is not Layer.DISPLAY for k in KNOBS)  # none registered yet


def test_layer_values_strip_the_prefix() -> None:
    variant = parse_sets(["world.gravity=950000", "mind.renderer=grid"])
    assert variant.layer_values(Layer.WORLD) == {"gravity": 950_000}
    assert variant.layer_values(Layer.MIND) == {"renderer": "grid"}
    assert variant.hashed_overrides() == {"world.gravity": 950_000}


def test_tags() -> None:
    assert resolve_variant(RULES_V1, []).tags == ()
    assert resolve_variant(RULES_V1, ["mind.renderer=grid"]).tags == ("exploratory",)
    steep = resolve_variant(RULES_V1, ["world.tilt=60000"])
    assert steep.tags == ("beyond-model", "exploratory")
    assert steep.manifest_config()["laws_beyond_model"] == ["season_strength"]


def test_set_option_collects_repeats() -> None:
    parser = argparse.ArgumentParser()
    add_set_option(parser)
    args = parser.parse_args(["--set", "world.gravity=950000", "--set", "world.rain=900000"])
    assert args.set == ["world.gravity=950000", "world.rain=900000"]
    assert parser.parse_args([]).set == []


def test_world_overrides_are_checked_by_the_loader() -> None:
    with pytest.raises(ValueError, match="unknown world constant"):
        apply_overrides(EARTH, {"moons": 1})
    with pytest.raises(RulesError, match="gravity must be > 0"):
        load_world(RULES_V1, {"gravity": 0})
    assert load_world(RULES_V1, {"tilt": 0}).tilt == 0
