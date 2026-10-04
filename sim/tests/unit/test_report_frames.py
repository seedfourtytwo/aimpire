"""Unit tests for the F4a report helpers beyond the acceptance tests."""

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from aimpire.report import frames
from aimpire.report.charts import line_chart_svg
from aimpire.report.metrics import MetricsRecorder
from aimpire.report.png import SIGNATURE, encode_png
from aimpire.sim.state import WorldState


def _state() -> WorldState:
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="t")
    s.add_layer("food", np.array([[0, 7], [3, -2]], dtype=np.int64))
    return s


def test_upscale_is_nearest_neighbour() -> None:
    frame = frames.frame_array(_state(), "food", ())
    big = frames.upscale(frame, 3)
    assert big.shape == (6, 6, 3)
    assert (big[0:3, 3:6] == frame[0, 1]).all()
    with pytest.raises(ValueError):
        frames.upscale(frame, 0)


def test_negative_values_clip_to_low_and_default_scale_is_max() -> None:
    frame = frames.frame_array(_state(), "food", ())
    assert tuple(frame[1, 1]) == frames.RAMP_LOW
    assert tuple(frame[0, 1]) == frames.RAMP_HIGH  # 7 is the layer max


def test_newest_entity_drawn_on_top_and_bad_positions_skipped() -> None:
    s = _state()
    s.add_entity("a", {"pos": [0, 0]})
    s.add_entity("b", {"pos": [0, 0]})
    s.add_entity("a", {"pos": ["x", 0]})
    s.add_entity("a", {"pos": [1]})
    frame = frames.frame_array(s, "food", ("a", "b"))
    assert tuple(frame[0, 0]) == frames.PALETTE[1]
    with pytest.raises(ValueError):
        frames.frame_array(s, "food", ("a", "a"))


def test_png_single_pixel() -> None:
    data = encode_png(np.zeros((1, 1, 3), dtype=np.uint8))
    assert data.startswith(SIGNATURE)
    with pytest.raises(ValueError):
        encode_png(np.zeros((0, 1, 3), dtype=np.uint8))


def test_metrics_names_and_bad_name() -> None:
    rec = MetricsRecorder({"a": lambda s: 1, "b": lambda s: 2})
    assert rec.names == ("a", "b")
    assert rec.to_csv() == "tick,a,b\n"
    with pytest.raises(ValueError):
        MetricsRecorder({"a,b": lambda s: 1})


def test_chart_min_max_text_and_no_float_values() -> None:
    svg = line_chart_svg([0, 10], [-5, 5], label="x<y")
    root = ET.fromstring(svg)
    texts = [t.text for t in root.iter("{http://www.w3.org/2000/svg}text")]
    assert "-5" in texts and "5" in texts and "x<y 5" in texts
