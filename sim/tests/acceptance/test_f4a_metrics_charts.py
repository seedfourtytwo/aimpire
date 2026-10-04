"""F4a acceptance: per-tick integer metrics and Tufte-style SVG line charts (ADR-0010).

Written by the planning model before implementation (ADR-0016). Read-only.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from aimpire.report.charts import line_chart_svg
from aimpire.report.metrics import MetricsRecorder
from aimpire.sim.ledger import layer_total
from aimpire.sim.state import WorldState

pytestmark = pytest.mark.acceptance

SVG = "{http://www.w3.org/2000/svg}"


def _world() -> WorldState:
    s = WorldState(run_seed=3, rules_version="v1", rules_hash="test")
    s.add_layer("food", np.full((2, 2), 1_000, dtype=np.int64))
    s.add_entity("person", {"pos": [0, 0]})
    return s


def _people(state: WorldState) -> int:
    return sum(1 for e in state.entities.values() if e["kind"] == "person")


def test_metrics_record_one_row_per_tick(tmp_path: Path) -> None:
    state = _world()
    rec = MetricsRecorder({"food": layer_total("food"), "people": _people})
    for _ in range(3):
        rec.record(state)
        state.layers["food"][0, 0] += 10
        state.add_entity("person", {"pos": [1, 1]})
        state.tick += 1
    assert rec.columns == ("tick", "food", "people")
    assert rec.rows == [(0, 4_000, 1), (1, 4_010, 2), (2, 4_020, 3)]
    assert rec.series("people") == [1, 2, 3]
    csv = rec.to_csv()
    assert csv == "tick,food,people\n0,4000,1\n1,4010,2\n2,4020,3\n"
    path = tmp_path / "metrics.csv"
    rec.write_csv(path)
    assert path.read_bytes() == csv.encode("ascii")


def test_metrics_reject_non_int_and_repeated_tick() -> None:
    state = _world()
    with pytest.raises(TypeError):
        MetricsRecorder({"bad": lambda s: 0.5}).record(state)  # type: ignore[arg-type,return-value]
    with pytest.raises(TypeError):
        MetricsRecorder({"bad": lambda s: True}).record(state)
    rec = MetricsRecorder({"people": _people})
    rec.record(state)
    with pytest.raises(ValueError):
        rec.record(state)  # same tick twice: rows must move forward in time
    with pytest.raises(ValueError):
        MetricsRecorder({"tick": _people})  # reserved column name


def test_chart_svg_well_formed_tufte() -> None:
    svg = line_chart_svg([0, 1, 2, 3, 4], [5, 9, 2, 7, 6], label="food & water")
    root = ET.fromstring(svg)  # well-formed XML, label escaped
    assert root.tag == f"{SVG}svg"
    texts = [t.text or "" for t in root.iter(f"{SVG}text")]
    assert any("food & water" in t for t in texts)  # direct label, no legend
    assert any(t.strip() == "9" for t in texts)  # max annotated
    assert any(t.strip() == "2" for t in texts)  # min annotated
    assert len(list(root.iter(f"{SVG}polyline"))) == 1
    assert not list(root.iter(f"{SVG}rect"))  # no boxes or backgrounds
    assert "grid" not in svg.lower()


def test_chart_handles_flat_and_single_point() -> None:
    for ticks, values in (([0, 1, 2], [4, 4, 4]), ([7], [3])):
        ET.fromstring(line_chart_svg(ticks, values, label="flat"))
    with pytest.raises(ValueError):
        line_chart_svg([], [], label="empty")
    with pytest.raises(ValueError):
        line_chart_svg([0, 1], [1], label="mismatch")
