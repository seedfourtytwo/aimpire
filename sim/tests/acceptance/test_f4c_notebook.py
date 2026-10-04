"""F4c acceptance: a Markdown lab notebook per finished run (ADR-0010, ADR-0013 section 8).

Written by the planning model before implementation (ADR-0016). Read-only.
The system below is a test double, not a simulation rule.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from aimpire.report.metrics import MetricsRecorder
from aimpire.report.notebook import OUTCOMES, RunInfo, write_notebook
from aimpire.sim.calendar import Calendar
from aimpire.sim.ledger import layer_total
from aimpire.sim.scheduler import Cadence, Preset, Scheduler, SystemSpec, TickContext
from aimpire.sim.state import WorldState

pytestmark = pytest.mark.acceptance

CAL = Calendar(ticks_per_season=5, seasons_per_year=4)
SECTIONS = ["Run", "Metrics", "Charts", "Ledger", "Outcomes", "Reproduce"]
ADR_0013_OUTCOMES = (
    "VALID",
    "PARTIAL",
    "INVALID",
    "REFUSAL",
    "TRUNCATED",
    "TIMEOUT",
    "PROVIDER_ERROR",
    "BUDGET",
)
COMMAND = "uv run python scripts/example_run.py --seed 7"


@dataclass
class Grow:
    """Every tile gains 3; on odd ticks tile (0, 0) also loses 5 to spoilage."""

    name: str = "grow"
    cadence: Cadence = "tick"
    sequential: bool = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        food = state.layers["food"]
        food += 3
        ctx.ledger.record("food", 3 * food.size, "REGROWTH")
        if ctx.tick % 2:
            food[0, 0] -= 5
            ctx.ledger.record("food", -5, "SPOIL")


def _finished_run() -> tuple[RunInfo, MetricsRecorder, Scheduler]:
    state = WorldState(run_seed=7, rules_version="v1", rules_hash="abc123")
    state.add_layer("food", np.full((2, 2), 100, dtype=np.int64))
    preset = Preset("m0-test", [SystemSpec("grow")])
    scheduler = Scheduler(preset, {"grow": lambda _p: Grow()}, CAL, {"food": layer_total("food")})
    metrics = MetricsRecorder(
        {"food": layer_total("food"), "tile_00": lambda s: int(s.layers["food"][0, 0])}
    )
    metrics.record(state)
    for _ in range(10):
        scheduler.step(state)
        metrics.record(state)
    info = RunInfo(
        run_id="run-0007",
        seed=7,
        rules_version="v1",
        rules_hash="abc123",
        preset=preset,
        ticks=state.tick,
        reproduce=COMMAND,
    )
    return info, metrics, scheduler


def _sections(text: str) -> dict[str, str]:
    """Map each level-2 heading to the text under it."""
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}


def test_notebook_lists_required_sections(tmp_path: Path) -> None:
    info, metrics, scheduler = _finished_run()
    path = tmp_path / "runs" / info.run_id / "notebook.md"
    write_notebook(path, info, metrics, scheduler.ledger)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# ")
    assert re.findall(r"^## (.+)$", text, flags=re.MULTILINE) == SECTIONS
    sec = _sections(text)

    for needle in ("run-0007", "7", "v1", "abc123", "m0-test", "grow", "10"):
        assert needle in sec["Run"]

    # Metrics: first, last, min and max per metric. food: 400 -> 400 + 10*12 - 5*5 = 495.
    assert re.search(r"\|\s*food\s*\|\s*400\s*\|\s*495\s*\|\s*400\s*\|\s*495\s*\|", sec["Metrics"])
    assert re.search(r"\|\s*tile_00\s*\|\s*100\s*\|", sec["Metrics"])

    # Charts: one SVG file per metric, next to the notebook, linked relatively and well-formed.
    links = re.findall(r"!\[[^\]]*\]\(([^)]+\.svg)\)", sec["Charts"])
    assert len(links) == 2
    for link in links:
        assert "/" not in link
        ET.fromstring((path.parent / link).read_text(encoding="utf-8"))

    # Ledger: totals by material and kind equal the ledger itself.
    assert re.search(r"\|\s*food\s*\|\s*REGROWTH\s*\|\s*10\s*\|\s*120\s*\|", sec["Ledger"])
    assert re.search(r"\|\s*food\s*\|\s*SPOIL\s*\|\s*5\s*\|\s*-25\s*\|", sec["Ledger"])

    # Outcomes: the eight ADR-0013 categories, zero until decisions exist.
    assert OUTCOMES == ADR_0013_OUTCOMES
    for category in ADR_0013_OUTCOMES:
        assert re.search(rf"\|\s*{category}\s*\|\s*0\s*\|", sec["Outcomes"])

    assert f"```\n{COMMAND}\n```" in sec["Reproduce"]


def test_notebook_is_deterministic_and_counts_outcomes(tmp_path: Path) -> None:
    info, metrics, scheduler = _finished_run()
    a, b = tmp_path / "a" / "notebook.md", tmp_path / "b" / "notebook.md"
    write_notebook(a, info, metrics, scheduler.ledger, outcomes={"VALID": 3, "REFUSAL": 1})
    write_notebook(b, info, metrics, scheduler.ledger, outcomes={"REFUSAL": 1, "VALID": 3})
    assert a.read_bytes() == b.read_bytes()
    sec = _sections(a.read_text(encoding="utf-8"))
    assert re.search(r"\|\s*VALID\s*\|\s*3\s*\|", sec["Outcomes"])
    assert re.search(r"\|\s*REFUSAL\s*\|\s*1\s*\|", sec["Outcomes"])
    with pytest.raises(ValueError):
        write_notebook(a, info, metrics, scheduler.ledger, outcomes={"MAYBE": 1})
