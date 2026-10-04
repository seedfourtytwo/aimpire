"""Unit tests for qualify and batch parts beyond the F6c/F6d acceptance tests."""

import asyncio
from pathlib import Path

import httpx2
import pytest

from aimpire.cognition.baselines import forage_nearest, hold
from aimpire.cognition.live_common import reported_cost_micro_usd
from aimpire.cognition.minds import MindError, resolve_mind
from aimpire.cognition.openai_compat import OpenAICompatProvider
from aimpire.cognition.profiles import parse_profile
from aimpire.cognition.render import system_prompt
from aimpire.cognition.seats import request_for, seat_from_observation
from aimpire.experiments.experiment import ExperimentError, load_experiment
from aimpire.experiments.plan import rotate
from aimpire.experiments.preflight import CostPlan, OverBudget, check_budget, usd
from aimpire.experiments.qualify import run_qualify
from aimpire.experiments.qualify_data import load_cases
from aimpire.experiments.stub_world import build_stub_world
from aimpire.sim.hashing import state_hash

FIRST = load_cases().cases[0].observation

OPENROUTER = """
kind = "openai_compat"
model = "vendor/model"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "AIMPIRE_UNIT_KEY"
timeout_s = 30.0
max_output_tokens = 500

[price]
input_micro_usd_per_mtok = 1_000_000
output_micro_usd_per_mtok = 2_000_000
source = "test"
as_of = "2026-10-04"

[budget]
max_input_tokens_per_call = 4000
"""


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.000123, 123), (1e-7, 1), (0, 0), (2, 2_000_000), (-1.0, None), ("0.1", None)],
)
def test_reported_cost_is_whole_micro_dollars_rounded_up(value: object, expected: int | None):
    assert reported_cost_micro_usd(value) == expected
    assert reported_cost_micro_usd(True) is None
    assert reported_cost_micro_usd(float("nan")) is None


def test_openai_compat_keeps_the_provider_reported_cost(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AIMPIRE_UNIT_KEY", "k")
    reply = forage_nearest(FIRST).model_dump_json()
    envelope = {
        "model": "vendor/model",
        "choices": [{"message": {"content": reply}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.00042},
    }
    transport = httpx2.MockTransport(lambda _req: httpx2.Response(200, json=envelope))
    profile = parse_profile(OPENROUTER, name="or")
    mind = resolve_mind("rule", Path.cwd())
    request = request_for(FIRST, "text", system_prompt(), mind)
    result = asyncio.run(OpenAICompatProvider(profile, transport=transport).complete(request))
    assert result.status == "ok"
    assert result.reported_cost_micro_usd == 420


def test_budget_check_refuses_over_the_monthly_cap_and_never_free_work(tmp_path: Path):
    lines: list[str] = []
    # Each run fits its 2-dollar cap, but 15 of them do not fit the 20-dollar month.
    plan = CostPlan(
        total_micro_usd=15 * 1_500_000, largest_run_micro_usd=1_500_000, run_cap_micro_usd=2_000_000
    )
    with pytest.raises(OverBudget) as refused:
        check_budget(plan, runs_root=tmp_path / "none", month="2026-10", echo=lines.append)
    assert "monthly" in str(refused.value)
    assert refused.value.remaining_micro_usd == 20_000_000
    check_budget(CostPlan(0, 0, 0), runs_root=tmp_path, month="2026-10", echo=lines.append)
    assert len(lines) == 2 and all(line.startswith("worst-case cost") for line in lines)
    assert usd(1_234_567) == "$1.234567" and usd(5) == "$0.000005"


def test_rotation_puts_every_mind_in_every_seat():
    a, b = (resolve_mind(f"rule:{n}", Path.cwd()) for n in ("hold", "forage_nearest"))
    shifts = [rotate((a, b), seats=3, rotation=r) for r in range(2)]
    assert [[m.label for m in s] for s in shifts] == [
        ["rule:hold", "rule:forage_nearest", "rule:hold"],
        ["rule:forage_nearest", "rule:hold", "rule:forage_nearest"],
    ]


def test_rule_baselines_answer_from_the_observation_only():
    nearest = forage_nearest(FIRST)
    assert nearest.decision_id == FIRST.decision_id
    assert [(a.place, a.share) for a in nearest.policy.allocations] == [("PL01", 1000)]
    assert [(o.kind, o.place, o.qty) for o in nearest.orders] == [("SCOUT", "PL03", 1)]
    still = hold(FIRST)
    assert (still.policy.allocations, still.policy.ration, still.orders) == ([], 0, [])
    nowhere = FIRST.model_copy(update={"places": []})
    assert forage_nearest(nowhere).orders == []


def test_seat_knows_only_what_the_observation_showed():
    seat = seat_from_observation(FIRST)
    assert seat.known_places == frozenset({"PL01", "PL02", "PL03"})
    assert seat.people == FIRST.status.population
    assert seat.observation_version == FIRST.version
    assert seat.known_civs == frozenset()


def test_minds_are_resolved_without_reading_keys(tmp_path: Path):
    assert resolve_mind("rule", tmp_path).label == "rule:forage_nearest"
    assert resolve_mind("mock", tmp_path).worst_case_call_micro_usd == 0
    (tmp_path / "or.toml").write_text(OPENROUTER, encoding="utf-8")
    priced = resolve_mind("or.toml", tmp_path)  # AIMPIRE_UNIT_KEY need not be set
    assert (
        priced.label == "or" and priced.worst_case_call_micro_usd == 5_000
    )  # 4000 x $1 + 500 x $2 per MTok
    for bad in ("rule:no_such_rule", "missing.toml", "gpt"):
        with pytest.raises(MindError):
            resolve_mind(bad, tmp_path)


def test_order_validity_with_no_orders_has_no_value_and_fails(tmp_path: Path):
    result = run_qualify("rule:hold", runs_root=tmp_path, echo=lambda _line: None)
    assert result.metrics.schema_adherence_ppm == 1_000_000
    assert result.metrics.orders_proposed == 0
    assert result.metrics.order_validity_ppm is None
    checks = {c.name: c.passed for c in result.checks}
    assert checks == {
        "schema_adherence_ppm": True,
        "order_validity_ppm": False,
        "latency_p50_ms": True,
        "latency_max_ms": True,
    }
    assert not result.passed
    assert "no value" in result.markdown_path.read_text(encoding="utf-8")


def test_stub_world_is_deterministic_and_seeded():
    assert state_hash(build_stub_world(5, 2).state) == state_hash(build_stub_world(5, 2).state)
    first, other = build_stub_world(5, 2), build_stub_world(6, 2)
    for world in (first, other):
        world.scheduler.step(world.state)
    assert [c for c, _ in first.civs] == ["C1", "C2"]
    assert state_hash(first.state) != state_hash(other.state)


EXPERIMENT = """\
id: e-unit
hypothesis: "h"
metrics: {primary: valid_share_ppm}
world: stub
ticks: 10
council_every: 10
checkpoint_every: 10
seats: 1
seeds: [1]
replicates: 3
arms:
  - {id: a, knowledge_arm: A0, renderer: places, prompt: base, models: [rule:hold]}
"""


def test_experiment_file_is_strict(tmp_path: Path):
    path = tmp_path / "e.yaml"
    for broken in (
        EXPERIMENT + "budget: 3\n",  # unknown key
        EXPERIMENT.replace("[rule:hold]", "[rule:hold, rule:hold]"),  # a mind twice
        EXPERIMENT.replace("prompt: base", "prompt: missing.txt"),
        EXPERIMENT.replace("seeds: [1]", "seeds: [1, 1]"),
        EXPERIMENT.replace("renderer: places", "renderer: tiles"),
        "id: [",  # not YAML
    ):
        path.write_text(broken, encoding="utf-8")
        with pytest.raises(ExperimentError):
            load_experiment(path)
    (tmp_path / "p2.txt").write_text("You decide for a group of people.\n", encoding="utf-8")
    path.write_text(EXPERIMENT.replace("prompt: base", "prompt: p2.txt"), encoding="utf-8")
    arm = load_experiment(path).arms[0]
    assert arm.prompt_text.startswith("You decide") and len(arm.prompt_hash) == 64
