"""Unit tests for the F4b replay export beyond the acceptance tests."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from aimpire.report.replay import ReplayError, ReplayRecorder, rle_decode, rle_encode
from aimpire.sim.calendar import Calendar
from aimpire.sim.state import WorldState

SIM = Path(__file__).resolve().parents[2]
CAL = Calendar(ticks_per_season=2, seasons_per_year=2)


@given(st.lists(st.integers(min_value=0, max_value=5), max_size=60))
def test_rle_roundtrip(values: list[int]) -> None:
    pairs = rle_encode(values)
    assert rle_decode(pairs) == values
    assert all(c >= 1 for c in pairs[1::2])
    assert all(a != b for a, b in zip(pairs[0:-2:2], pairs[2::2], strict=False))  # maximal runs


def test_rle_decode_rejects_odd_length() -> None:
    with pytest.raises(ReplayError):
        rle_decode([1, 2, 3])


def _state() -> WorldState:
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="t")
    s.add_layer("food", np.zeros((2, 3), dtype=np.int64))
    s.add_entity("person", {"pos": [1, 2]})
    s.add_entity("person", {"pos": [9, 9]})  # off the grid: no dot, and no error
    return s


def test_recorder_rejects_going_back_and_other_runs() -> None:
    rec = ReplayRecorder("food", ("person",), CAL)
    state = _state()
    rec.capture(state)
    with pytest.raises(ValueError):
        rec.capture(state)
    other = _state()
    other.run_seed, other.tick = 2, 5
    with pytest.raises(ValueError):
        rec.capture(other)
    with pytest.raises(ValueError):
        ReplayRecorder("food", ("a", "a"), CAL)
    with pytest.raises(ValueError):
        ReplayRecorder("food", (), CAL).to_dict()


def test_off_grid_entities_are_not_dots() -> None:
    rec = ReplayRecorder("food", ("person",), CAL)
    frame = rec.capture(_state())
    assert frame["dots"] == [[1, "person", 1, 2]]
    assert rec.to_dict()["scale_max"] == 1  # all-zero layer: default scale is at least 1


def test_fixture_replay_is_current() -> None:
    """The committed player fixture matches what the generator makes today."""
    out = subprocess.run(
        [sys.executable, str(SIM / "scripts" / "make_fixture_replay.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, out.stderr
