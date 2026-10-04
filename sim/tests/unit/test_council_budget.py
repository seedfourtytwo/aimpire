"""Unit tests for the council barrier's failure paths and the budget guard (F5e)."""

import asyncio
import json
from dataclasses import replace

import pytest

from aimpire.cognition.budget import BudgetGuard, Caps, Grant, Price, RecordedRefusals, Refusal
from aimpire.cognition.council import council_order, decision_id_for, hold_council
from aimpire.cognition.provider import (
    CognitionRequest,
    CognitionResult,
    MockFailure,
    MockProvider,
    ModelIdentity,
    Provider,
    Usage,
)
from aimpire.sim.actions import DecisionLog, Outcome, Reason, StandingPolicy
from aimpire.sim.actions.commit import CIV_KIND, commit_decision, standing_policy_of
from tests.acceptance.test_f5e_council import _reply, _seats_for, _world


class _Slow:
    """Never answers within its request's timeout."""

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        await asyncio.sleep(3600)
        raise AssertionError("unreachable")

    def describe(self) -> ModelIdentity:
        return ModelIdentity(provider="mock", model="slow", digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        return 0


class _Broken(_Slow):
    async def complete(self, req: CognitionRequest) -> CognitionResult:
        raise RuntimeError("adapter bug")


def _hold(providers: dict[str, Provider], timeout_s: float = 30.0):
    state, entity_ids = _world(tuple(sorted(providers)))
    calls = [
        replace(c, request=replace(c.request, timeout_s=timeout_s))
        for c in _seats_for(providers, entity_ids)(state, 1)
    ]
    settled = asyncio.run(hold_council(state, calls, gate=BudgetGuard(Caps()), log=DecisionLog()))
    return state, entity_ids, settled


def test_timeout_and_exceptions_become_recorded_outcomes():
    state, entity_ids, settled = _hold({"C1": _Slow(), "C2": _Broken()}, timeout_s=0.01)
    by_civ = {s.record.civ_id: s for s in settled}
    assert by_civ["C1"].record.outcome is Outcome.TIMEOUT
    assert by_civ["C1"].record.rejections[0].reason is Reason.TIMEOUT
    assert by_civ["C2"].record.outcome is Outcome.PROVIDER_ERROR
    for civ in ("C1", "C2"):
        policy = standing_policy_of(state.entities[entity_ids[civ]])
        assert policy == StandingPolicy(allocations=(), ration=1000)


def test_unparseable_text_and_refusal_are_not_replaced():
    d1 = decision_id_for("C1", 1)
    d2 = decision_id_for("C2", 1)
    mock = MockProvider({d1: "plain prose", d2: MockFailure(status="refusal", raw_text="no")})
    state, entity_ids, settled = _hold({"C1": mock, "C2": mock})
    by_civ = {s.record.civ_id: s.record for s in settled}
    assert by_civ["C1"].outcome is Outcome.INVALID
    assert by_civ["C1"].rejections[0].reason is Reason.PARSE_FAILED
    assert by_civ["C2"].outcome is Outcome.REFUSAL
    for civ in ("C1", "C2"):
        assert state.entities[entity_ids[civ]]["journal"] == ""


def test_hold_council_rejects_miswired_seats():
    state, entity_ids = _world()
    mock = MockProvider({})
    calls = list(_seats_for({"C1": mock, "C2": mock}, entity_ids)(state, 1))
    with pytest.raises(ValueError, match="one seat"):
        asyncio.run(
            hold_council(state, [calls[0], calls[0]], gate=BudgetGuard(Caps()), log=DecisionLog())
        )
    swapped = replace(calls[0], request=calls[1].request)
    with pytest.raises(ValueError, match="disagree"):
        asyncio.run(hold_council(state, [swapped], gate=BudgetGuard(Caps()), log=DecisionLog()))


def test_reservations_are_held_until_settled():
    guard = BudgetGuard(Caps(run_micro_usd=1_000, monthly_micro_usd=10_000))
    first = guard.reserve("D1", 600)
    assert first == Grant("D1", 600, None) and guard.held == 600
    assert guard.reserve("D2", 600).refused is Refusal.RUN_CAP  # the hold counts
    guard.settle(first, 100)
    assert (guard.held, guard.spent_run, guard.spent_month) == (0, 100, 100)
    assert guard.reserve("D3", 900).refused is None


def test_unpriced_and_malformed_estimates_fail_closed():
    guard = BudgetGuard(Caps())
    assert guard.reserve("D1", None).refused is Refusal.UNPRICED
    assert guard.reserve("D2", 1.5).refused is Refusal.UNPRICED  # pyright: ignore[reportArgumentType]
    assert guard.reserve("D3", -5).refused is Refusal.UNPRICED
    assert guard.reserve("D4", True).refused is Refusal.UNPRICED  # pyright: ignore[reportArgumentType]
    assert BudgetGuard(Caps(), allow_unpriced=True).reserve("D5", None).refused is None
    with pytest.raises(TypeError):
        BudgetGuard(Caps(), spent_run=1.0)  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError):
        guard.settle(Grant("D1", 0, None), -1)


def test_price_worst_case_rounds_up():
    price = Price(input_micro_usd_per_mtok=3_000_000, output_micro_usd_per_mtok=15_000_000)
    assert price.worst_case(input_tokens=2_000, max_output_tokens=1_000) == 21_000
    assert Price(1, 1).worst_case(1, 0) == 1
    assert Price(0, 0).cost(Usage(10**9, 10**9, 10**9)) == 0


def test_recorded_refusals_gate():
    gate = RecordedRefusals({"D1": Refusal.MONTHLY_CAP})
    assert gate.reserve("D1", 0).refused is Refusal.MONTHLY_CAP
    assert gate.reserve("D2", None) == Grant("D2", 0, None)


def test_council_order_ignores_input_order():
    assert council_order(1, 5, [3, 1, 2]) == council_order(1, 5, [2, 3, 1])
    assert sorted(council_order(1, 5, [3, 1, 2])) == [1, 2, 3]


def test_decision_id_format():
    assert decision_id_for("C1", 3) == "C1-K0003"
    with pytest.raises(ValueError):
        decision_id_for("C1", -1)


def test_commit_keeps_journal_when_unused_and_checks_wiring():
    state, entity_ids = _world()
    state.entities[entity_ids["C1"]]["journal"] = "old notes"
    d1 = decision_id_for("C1", 1)
    raw = json.dumps({**_reply(d1, 200, "PL01", ""), "journal": ""})
    mock = MockProvider({d1: raw})
    calls = _seats_for({"C1": mock}, entity_ids)(state, 1)
    settled = asyncio.run(hold_council(state, calls, gate=BudgetGuard(Caps()), log=DecisionLog()))
    entity = state.entities[entity_ids["C1"]]
    assert entity["journal"] == "old notes"
    assert standing_policy_of(entity).allocations[0].share == 200
    with pytest.raises(ValueError, match="does not hold"):
        commit_decision(state, entity_ids["C2"], settled[0].record)
    other = state.add_entity("person", {"civ_id": "C1"})
    with pytest.raises(ValueError, match="not a civilization"):
        commit_decision(state, other, settled[0].record)
    assert CIV_KIND == "civ"
