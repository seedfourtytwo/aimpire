"""Unit tests for the F4c lab notebook beyond the acceptance tests."""

from pathlib import Path

from aimpire.report.charts import line_chart_svg
from aimpire.report.metrics import MetricsRecorder
from aimpire.report.notebook import RunInfo, write_notebook
from aimpire.sim.ledger import Ledger
from aimpire.sim.scheduler import Preset, SystemSpec
from aimpire.sim.state import WorldState


def _info(preset: Preset) -> RunInfo:
    return RunInfo("r1", 1, "v1", "h", preset, 0, "aimpire --version")


def test_empty_run_still_has_every_section(tmp_path: Path) -> None:
    path = write_notebook(
        tmp_path / "notebook.md", _info(Preset("empty", [])), MetricsRecorder({}), Ledger()
    )
    text = path.read_text(encoding="utf-8")
    assert text.count("No metrics recorded.") == 2
    assert "No ledger entries." in text
    assert "  (none)" in text
    assert list(tmp_path.glob("*.svg")) == []


def test_params_pipes_and_chart_names(tmp_path: Path) -> None:
    preset = Preset("p", [SystemSpec("regrow", {"rate": 20, "per": "season"})])
    metrics = MetricsRecorder({"food|land": lambda s: 1, "Food Land!": lambda s: 2})
    ledger = Ledger()
    ledger.begin("regrow", 0)
    ledger.record("food", 5, "REGROWTH")
    metrics.record(WorldState(run_seed=1, rules_version="v1", rules_hash="h"))
    text = write_notebook(tmp_path / "nb.md", _info(preset), metrics, ledger).read_text()
    assert '`regrow` {"per": "season", "rate": 20}' in text
    assert "| food\\|land | 1 | 1 | 1 | 1 |" in text
    assert sorted(p.name for p in tmp_path.glob("*.svg")) == [
        "chart-01-food-land.svg",
        "chart-02-food-land.svg",
    ]


def test_chart_edge_labels_anchor_inward() -> None:
    svg = line_chart_svg([0, 5, 10], [1, 5, 9], label="up")
    assert 'text-anchor="start">1<' in svg  # min at the left edge
    assert 'text-anchor="end">9<' in svg  # max at the right edge
    assert 'text-anchor="middle">5<' in line_chart_svg([0, 5, 10], [1, 5, 1], label="peak")
