"""The playable replay ``aimpire-replay-v2`` written by ``aimpire run`` (F4d).

The run here is real M0 play with the fixture's scripted mock mind
(``scripts/m0_fixture.py``, a test double): its replies go through the same
parser, validator and run store as a model's.
"""

import importlib.util
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from aimpire.cognition.baselines import rule_provider
from aimpire.cognition.disclosed import load_disclosed
from aimpire.experiments.play import PlayOptions, play
from aimpire.persistence.store import RunStore
from aimpire.report.metrics import MetricsRecorder
from aimpire.report.replay import FORMAT, ReplayError, load_replay
from aimpire.report.replay_m0 import run_section, series_section
from aimpire.report.replay_v2_check import FORMAT_V2, validate_any
from aimpire.rules import DEFAULT_RULES_DIR
from aimpire.sim.state import WorldState

SIM = Path(__file__).resolve().parents[2]
FIXTURES = SIM.parent / "client" / "replay" / "fixtures"


def _fixture_module() -> Any:
    spec = importlib.util.spec_from_file_location("m0_fixture", SIM / "scripts" / "m0_fixture.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _fixture_module()


def _play(out: Path, ticks: int = 50) -> Path:
    opts = PlayOptions(
        world="m0",
        mind="mock",
        seed=7,
        ticks=ticks,
        settings=(),
        renderer="places",
        out_root=out,
        rules_dir=DEFAULT_RULES_DIR,
        council_every=10,
        frame_every=10,
        base_dir=out,
        reproduce="test",
    )
    inner = rule_provider("half_full", load_disclosed(DEFAULT_RULES_DIR))
    mind = FIXTURE.ScriptedFixtureMind(inner)
    return play(opts, month="2026-01", echo=lambda _l: None, provider=mind).run_dir


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _play(tmp_path_factory.mktemp("a"))


def _strings(value: object, where: str = "") -> Iterator[tuple[str, str]]:
    """Every string in a JSON value with the path it sits at."""
    if isinstance(value, str):
        yield where, value
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _strings(item, f"{where}[{i}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{where}.{key}")


def test_run_writes_a_deterministic_v2_replay(run_dir: Path, tmp_path: Path) -> None:
    again = _play(tmp_path)
    assert (run_dir / "replay.json").read_bytes() == (again / "replay.json").read_bytes()
    replay = load_replay(run_dir / "replay.json")
    assert replay["format"] == FORMAT_V2
    assert replay["run"]["minds"] == [["C1", "mock"]]
    assert [f["tick"] for f in replay["frames"]] == [0, 10, 20, 30, 40, 50]
    assert replay["series"]["ticks"] == list(range(51))
    assert replay["series"]["columns"][:2] == ["population", "deaths"]
    assert len(replay["places"]["ids"]) == len(replay["places"]["centroids"]) == 16


def test_frames_carry_metrics_camp_and_work(run_dir: Path) -> None:
    replay = load_replay(run_dir / "replay.json")
    csv = (run_dir / "metrics.csv").read_text().splitlines()
    by_tick = {int(line.split(",")[0]): [int(v) for v in line.split(",")[1:]] for line in csv[1:]}
    for frame in replay["frames"]:
        assert frame["metrics"] == by_tick[frame["tick"]], "frame metrics are the CSV row"
        (civ,) = frame["civs"]
        assert civ["camp"] in replay["places"]["ids"]
        assert civ["population"] == frame["metrics"][0]
    later = replay["frames"][1]["civs"][0]
    assert later["work"] and sum(n for _, _, n in later["work"]) <= later["population"]
    assert later["names"] == [[later["work"][0][1], "Fixture Meadow"]]


def test_councils_come_verbatim_from_the_decision_records(run_dir: Path) -> None:
    replay = load_replay(run_dir / "replay.json")
    with RunStore.open(run_dir, read_only=True) as store:
        rows = store.decisions()
    assert [c["decision_id"] for c in replay["councils"]] == [r["decision_id"] for r in rows]
    for council, row in zip(replay["councils"], rows, strict=True):
        record = row["record"]
        for key in ("journal", "annal", "policy", "messages", "names", "rejections", "flags"):
            assert council[key] == record[key], key
        assert council["outcome"] == row["outcome"]
    first, third = replay["councils"][0], replay["councils"][2]
    assert first["journal"].startswith("Fixture journal, council 1.")
    assert '"like these", <angle brackets> & accents (é)' in first["journal"]
    results = [(o["index"], o["result"], o["reason"]) for o in third["orders"]]
    assert results == [
        (0, "ACCEPTED", ""),
        (1, "REJECTED", "UNKNOWN_ENTITY"),
        (2, "REJECTED", "UNKNOWN_ACTION"),
    ]
    assert json.loads(third["orders"][1]["order"])["place"] == "PL99"
    assert replay["councils"][4]["outcome"] == "INVALID"


def test_mind_text_appears_only_in_councils(run_dir: Path) -> None:
    """The civ state also holds the journal; the replay must show it only from the record."""
    replay = load_replay(run_dir / "replay.json")
    hits = [where for where, text in _strings(replay) if "Fixture journal" in text]
    assert hits and all(where.startswith(".councils[") for where in hits), hits
    messages = [w for w, t in _strings(replay) if "Fixture message to the voice." in t]
    assert messages == [".councils[2].messages[0][2]"]


def test_series_are_decimated_when_long() -> None:
    metrics = MetricsRecorder({"n": lambda s: s.tick})
    state = WorldState(run_seed=1, rules_version="v1", rules_hash="t")
    for tick in range(4501):
        state.tick = tick
        metrics.record(state)
    series = series_section(metrics, max_points=2000)
    assert series["every"] == 3
    assert series["ticks"][:3] == [0, 3, 6] and series["ticks"][-1] == 4500
    assert series["values"] == [series["ticks"]]
    short = series_section(metrics, max_points=5000)
    assert short["every"] == 1 and len(short["ticks"]) == 4501


def test_run_section_shows_overrides_and_tags() -> None:
    manifest = {
        "run_id": "r",
        "config": {
            "seats": {"C1": "rule:greedy"},
            "variant": {"id": "abc", "overrides": {"world.gravity": 950000}},
            "tags": ["exploratory"],
            "council_every": 10,
            "ticks": 30,
        },
    }
    run = run_section(manifest)
    assert run["overrides"] == ["world.gravity=950000"]
    assert run["tags"] == ["exploratory"]
    assert run["minds"] == [["C1", "rule:greedy"]]


def test_validation_rejects_bad_v2_and_still_reads_v1(run_dir: Path) -> None:
    assert load_replay(FIXTURES / "wander.json")["format"] == FORMAT
    assert load_replay(FIXTURES / "m0.json")["format"] == FORMAT_V2
    good = json.loads((run_dir / "replay.json").read_text())
    cases = [
        lambda d: d["frames"][1]["metrics"].append(1),
        lambda d: d["frames"][1]["civs"][0].update(camp="PL99"),
        lambda d: d["councils"][0].update(journal=None),
        lambda d: d["councils"][0].update(tick=1.5),
        lambda d: d["councils"][0]["orders"].append({"index": 0, "result": "MAYBE"}),
        lambda d: d["series"]["values"][0].pop(),
        lambda d: d["run"].pop("tags"),
        lambda d: d["places"]["tiles"].extend([0, 1]),
        lambda d: d.update(councils=list(reversed(d["councils"]))),
    ]
    for change in cases:
        data = json.loads(json.dumps(good))
        change(data)
        with pytest.raises(ReplayError):
            validate_any(data)
