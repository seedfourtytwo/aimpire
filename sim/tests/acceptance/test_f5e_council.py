"""F5e acceptance: the council barrier, budgets and the run store (ADR-0004, ADR-0005, ADR-0013).

Written in the planning role before implementation (ADR-0016). Read-only.

* Recorded replay: a run recorded with mock and rule providers is replayed
  from its run store with ``RecordedProvider``; every checkpoint hash matches,
  and a tampered recording fails loudly, naming the part that diverged.
* Budgets: caps are integer micro-dollars. A call whose worst case would cross
  the per-run or the monthly cap is refused before it is made; the refusal is
  a ``BUDGET`` decision, not a crash. A free provider (Ollama) is never
  refused for cost.
* The barrier: every seat due at a council is answered before anything is
  applied, and records are applied in the ``turn_order`` permutation whatever
  order the replies arrive in.
* No credentials ever reach the run store.

No network. Observations are minimal stubs built here; the real builder is
``cognition/observe.py`` (F5c).
"""

import asyncio
import json
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from compression import zstd
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from aimpire.cognition.budget import (
    DEFAULT_MONTHLY_CAP_MICRO_USD,
    DEFAULT_RUN_CAP_MICRO_USD,
    BudgetGuard,
    Caps,
    Price,
    Refusal,
)
from aimpire.cognition.council import SeatCall, Settled, decision_id_for, hold_council
from aimpire.cognition.provider import (
    NO_USAGE,
    CognitionRequest,
    CognitionResult,
    MockFailure,
    MockProvider,
    ModelIdentity,
    Provider,
    RecordedProvider,
    RuleProvider,
    Usage,
)
from aimpire.cognition.runner import run_with_councils
from aimpire.contracts.mind import MindReply, Observation
from aimpire.persistence.store import ReplayMismatch, RunStore, month_spent, verify_replay
from aimpire.sim.actions import CouncilSeat, DecisionLog, Outcome, Reason, StandingPolicy
from aimpire.sim.actions.commit import CIV_KIND, standing_policy_of
from aimpire.sim.calendar import Calendar
from aimpire.sim.hashing import state_hash
from aimpire.sim.rng import SITES, Stream, draw, permutation, stream_key, uniform_int
from aimpire.sim.scheduler import Preset, Scheduler, System, SystemSpec, TickContext
from aimpire.sim.state import Value, WorldState

pytestmark = pytest.mark.acceptance

SEED = 4242
MONTH = "2026-10"
CALENDAR = Calendar(ticks_per_season=30, seasons_per_year=4)
PLACES = frozenset({"PL01", "PL02", "PL03"})
CIVS = ("C1", "C2", "C3")


# --- A toy world: one drawing system, civilizations as entities ---------------


class _Drift:
    """Adds a seeded amount to one tile each tick, so hashes depend on the seed."""

    name = "drift"
    cadence = "tick"
    sequential = False

    def step(self, state: WorldState, ctx: TickContext) -> None:
        u = draw(ctx.key(Stream.GROWTH), 0, 0)
        state.layers["food"][0, 0] += uniform_int(u, 7)


def _drift(_params: Mapping[str, Value]) -> System:
    return _Drift()  # pyright: ignore[reportReturnType]


def _scheduler() -> Scheduler:
    return Scheduler(Preset("f5e", [SystemSpec("drift")]), {"drift": _drift}, CALENDAR)


def _world(civs: Sequence[str] = CIVS[:2]) -> tuple[WorldState, dict[str, int]]:
    state = WorldState(run_seed=SEED, rules_version="v1", rules_hash="rules-hash")
    state.add_layer("food", np.zeros((4, 4), dtype=np.int64))
    entity_ids: dict[str, int] = {}
    for civ in civs:
        policy: Value = {"allocations": [], "ration": 1000}
        fields: dict[str, Value] = {"civ_id": civ, "policy": policy, "journal": ""}
        entity_ids[civ] = state.add_entity(CIV_KIND, fields)
    return state, entity_ids


def _observation(civ: str, decision_id: str, version: str, tick: int, council: int) -> Observation:
    return Observation.model_validate(
        {
            "contract": "m0",
            "civ_id": civ,
            "decision_id": decision_id,
            "version": version,
            "calendar": {
                "tick": tick,
                "season": "S0",
                "year": 0,
                "council": council,
                "ticks_to_next_council": 10,
            },
            "status": {
                "population": 10,
                "population_change": 0,
                "food_days": 5,
                "food_days_change": 0,
                "stores": [],
            },
            "places": [],
            "events": [],
            "messages": [],
            "standing": {
                "policy": {"allocations": [], "ration": 1000},
                "tasks": [],
                "commitments": [],
            },
            "last_results": [],
            "knowledge": {"claims": [], "beliefs": []},
            "journal": "",
        }
    )


SeatsFor = Callable[[WorldState, int], Sequence[SeatCall]]


def _seats_for(
    providers: Mapping[str, Provider],
    entity_ids: Mapping[str, int],
    prices: Mapping[str, Price] | None = None,
    system: str = "You are a council.",
) -> SeatsFor:
    def build(state: WorldState, council: int) -> list[SeatCall]:
        calls: list[SeatCall] = []
        for civ in sorted(providers):
            entity_id = entity_ids[civ]
            decision_id = decision_id_for(civ, council)
            version = f"{civ}:c{council:03d}"
            observation = _observation(civ, decision_id, version, state.tick, council)
            seat = CouncilSeat(
                civ_id=civ,
                decision_id=decision_id,
                council=council,
                observation_version=version,
                known_places=PLACES,
                people=10,
                known_civs=frozenset(c for c in entity_ids if c != civ),
                evidence_ids=frozenset(),
                policy=standing_policy_of(state.entities[entity_id]),
            )
            request = CognitionRequest(
                decision_id=decision_id,
                civ_id=civ,
                contract="m0",
                system=system,
                observation=observation,
                observation_text=f"tick {state.tick}",
                reply_schema=MindReply.model_json_schema(),
                max_output_tokens=1000,
                timeout_s=30.0,
                effort=None,
                temperature=None,
            )
            price = (prices or {}).get(civ, Price(0, 0))
            calls.append(SeatCall(entity_id, seat, request, providers[civ], price))
        return calls

    return build


def _reply(decision_id: str, share: int, place: str, journal: str) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "policy": {
            "allocations": [{"activity": "FORAGE", "place": place, "share": share}],
            "ration": 900,
        },
        "orders": [{"kind": "FORAGE", "place": place, "target": "", "qty": 3, "text": ""}],
        "messages": [],
        "commitments": [],
        "beliefs": [],
        "names": [],
        "journal": journal,
        "annal": "",
    }


def _mock_fixture(civ: str, councils: int) -> dict[str, str | MockFailure]:
    replies: dict[str, str | MockFailure] = {}
    for council in range(1, councils + 1):
        decision_id = decision_id_for(civ, council)
        place = sorted(PLACES)[council % 3]
        share = 100 * council % 1000
        replies[decision_id] = json.dumps(_reply(decision_id, share, place, f"k{council}"))
    replies[decision_id_for(civ, 3)] = MockFailure(status="refusal", raw_text="No.")
    replies[decision_id_for(civ, 5)] = "this is not json"
    replies[decision_id_for(civ, 7)] = json.dumps(_reply(decision_id_for(civ, 7), 1500, "PL09", ""))
    return replies


def _rule(obs: Observation) -> MindReply:
    share = 50 * obs.calendar.council % 1000
    journal = f"rule {obs.calendar.council}"
    return MindReply.model_validate(_reply(obs.decision_id, share, "PL02", journal))


def _create(root: Path, run_id: str, **extra: Any) -> RunStore:
    options: dict[str, Any] = {"caps": Caps(), **extra}
    return RunStore.create(
        root / run_id,
        run_id=run_id,
        seed=SEED,
        rules_version="v1",
        rules_hash="rules-hash",
        month=MONTH,
        **options,
    )


def _drive(state: WorldState, ticks: int, seats_for: SeatsFor, gate: Any, sink: RunStore) -> None:
    asyncio.run(
        run_with_councils(
            state,
            _scheduler(),
            ticks=ticks,
            every_ticks=10,
            checkpoint_every=10,
            seats_for=seats_for,
            gate=gate,
            sink=sink,
        )
    )


def _record_run(root: Path, run_id: str, ticks: int = 120) -> tuple[RunStore, WorldState]:
    state, entity_ids = _world()
    providers: dict[str, Provider] = {
        "C1": MockProvider(_mock_fixture("C1", ticks // 10 + 1)),
        "C2": RuleProvider(_rule, name="steady"),
    }
    store = _create(root, run_id)
    guard = store.budget_guard(month_spent(root, MONTH))
    _drive(state, ticks, _seats_for(providers, entity_ids), guard, store)
    return store, state


def _replay_run(
    root: Path, original: RunStore, run_id: str, provider: Provider, ticks: int
) -> RunStore:
    state, entity_ids = _world()
    replay = _create(root, run_id, replay_of=original)
    seats = _seats_for({"C1": provider, "C2": provider}, entity_ids)
    _drive(state, ticks, seats, original.replay_gate(), replay)
    return replay


def _decided(store: RunStore) -> list[tuple[Any, ...]]:
    return [(r["decision_id"], r["outcome"], r["record"]) for r in store.decisions()]


# --- Recorded replay ------------------------------------------------------------


def test_recorded_replay_matches_every_checkpoint_hash(tmp_path: Path):
    root = tmp_path / "runs"
    original, final_state = _record_run(root, "r1")
    replay = _replay_run(root, original, "r1-replay", original.recorded_provider(), 120)

    recorded = original.checkpoints()
    replayed = replay.checkpoints()
    assert len(recorded) >= 13  # each council barrier plus every 10 ticks over 120 ticks
    assert recorded == replayed
    assert recorded[-1][-1] == state_hash(final_state)
    assert len({h for *_, h in recorded}) > 2, "decisions and draws must move the hash"
    verify_replay(original, replay)  # raises on any mismatch

    # The decisions themselves replay too, outcome by outcome, in the same order.
    assert _decided(original) == _decided(replay)
    outcomes = {row[1] for row in _decided(original)}
    assert {"VALID", "PARTIAL", "INVALID", "REFUSAL"} <= outcomes
    assert replay.manifest()["replay_of_run_id"] == "r1"


def test_replay_mismatch_fails_loudly_naming_the_part(tmp_path: Path):
    root = tmp_path / "runs"
    original, _ = _record_run(root, "r1", ticks=40)
    # The recording is altered: one decision now sets a different policy.
    tampered = decision_id_for("C2", 2)
    records = original.recorded_records()
    raw = json.dumps(_reply(tampered, 999, "PL01", "tampered"))
    records[tampered] = {**records[tampered], "raw_text": raw}
    replay = _replay_run(root, original, "bad", RecordedProvider(records), 40)
    with pytest.raises(ReplayMismatch) as error:
        verify_replay(original, replay)
    assert "entities:civ" in str(error.value)


# --- Budgets ----------------------------------------------------------------------


class _Priced:
    """A provider with a fixed worst-case estimate and real-looking usage. Counts calls."""

    def __init__(self, estimate: int | None, kind: str = "openrouter") -> None:
        self.estimate = estimate
        self.kind = kind
        self.calls: list[str] = []

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        self.calls.append(req.decision_id)
        raw = json.dumps(_reply(req.decision_id, 500, "PL01", "paid"))
        return CognitionResult(
            raw_text=raw,
            parsed=json.loads(raw),
            status="ok",
            usage=Usage(input_tokens=1000, output_tokens=500, reasoning_tokens=0),
            model_reported=f"{self.kind}-model",
            latency_ms=5,
            attempts=1,
        )

    def describe(self) -> ModelIdentity:
        return ModelIdentity(provider=self.kind, model=f"{self.kind}-model", digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        return self.estimate


# 3 dollars per million input tokens, 15 per million output: 1000 in + 500 out = 10,500 micro-USD.
PRICE = Price(input_micro_usd_per_mtok=3_000_000, output_micro_usd_per_mtok=15_000_000)


def _council(
    providers: Mapping[str, Provider], guard: Any, prices: Mapping[str, Price] | None = None
) -> tuple[WorldState, dict[str, int], DecisionLog, Sequence[Settled]]:
    state, entity_ids = _world(tuple(sorted(providers)))
    log = DecisionLog()
    calls = _seats_for(providers, entity_ids, prices)(state, 1)
    settled = asyncio.run(hold_council(state, calls, gate=guard, log=log))
    return state, entity_ids, log, settled


def test_budget_refuses_over_cap():
    # Defaults per the creator's budget rules: 20 dollars a month, 2 per run, in micro-dollars.
    assert DEFAULT_MONTHLY_CAP_MICRO_USD == 20_000_000
    assert DEFAULT_RUN_CAP_MICRO_USD == 2_000_000
    assert Caps() == Caps(run_micro_usd=2_000_000, monthly_micro_usd=20_000_000)
    for bad in (2.0, True, "2000000", -1):
        with pytest.raises((TypeError, ValueError)):
            Caps(run_micro_usd=bad)  # pyright: ignore[reportArgumentType]
        with pytest.raises((TypeError, ValueError)):
            Price(input_micro_usd_per_mtok=bad, output_micro_usd_per_mtok=0)  # pyright: ignore[reportArgumentType]
    assert PRICE.cost(Usage(input_tokens=1000, output_tokens=500, reasoning_tokens=0)) == 10_500
    assert PRICE.cost(Usage(1, 1, 1)) == 33  # reasoning tokens bill as output
    # 33 millionths of a micro-dollar round up to 1, never down to 0 and never to a float.
    assert Price(3, 15).cost(Usage(1, 1, 1)) == 1

    # Per-run cap: two seats each worth 600,000 at worst; only one fits under 1,000,000.
    a, b = _Priced(600_000), _Priced(600_000)
    guard = BudgetGuard(Caps(run_micro_usd=1_000_000, monthly_micro_usd=20_000_000))
    state, entity_ids, log, settled = _council(
        {"C1": a, "C2": b}, guard, {"C1": PRICE, "C2": PRICE}
    )
    assert sorted(s.record.outcome for s in settled) == [Outcome.BUDGET, Outcome.VALID]
    refused = next(s for s in settled if s.record.outcome is Outcome.BUDGET)
    paid = next(s for s in settled if s.record.outcome is Outcome.VALID)
    assert refused.grant.refused is Refusal.RUN_CAP
    assert refused.result is None and refused.charged == 0
    assert refused.record.rejections[0].reason is Reason.BUDGET_EXHAUSTED
    # The refused seat's provider was never called, and its policy is unchanged.
    assert (a if refused.record.civ_id == "C1" else b).calls == []
    refused_entity = state.entities[entity_ids[refused.record.civ_id]]
    assert standing_policy_of(refused_entity) == StandingPolicy(allocations=(), ration=1000)
    # The call that went ahead is charged its actual cost, as an int.
    assert paid.charged == 10_500 and type(paid.charged) is int
    assert guard.spent_run == 10_500 and guard.spent_month == 10_500
    assert len(log) == 2

    # Reaching a cap exactly is allowed; crossing it by one micro-dollar is not.
    assert BudgetGuard(Caps(run_micro_usd=600_000)).reserve("D1", 600_000).refused is None
    over = BudgetGuard(Caps(run_micro_usd=599_999)).reserve("D1", 600_000)
    assert over.refused is Refusal.RUN_CAP

    # Monthly cap: earlier runs this month already spent most of the 20 dollars.
    c = _Priced(600_000)
    _, _, _, settled = _council(
        {"C1": c}, BudgetGuard(Caps(), spent_month=19_500_000), {"C1": PRICE}
    )
    assert settled[0].record.outcome is Outcome.BUDGET
    assert settled[0].grant.refused is Refusal.MONTHLY_CAP
    assert c.calls == []

    # An unpriced call fails closed.
    unpriced = _Priced(None)
    _, _, _, settled = _council({"C1": unpriced}, BudgetGuard(Caps()))
    assert settled[0].record.outcome is Outcome.BUDGET
    assert settled[0].grant.refused is Refusal.UNPRICED
    assert unpriced.calls == []

    # Ollama costs nothing and is never refused for cost, even with every cap spent.
    ollama = _Priced(0, kind="ollama")
    spent = BudgetGuard(
        Caps(run_micro_usd=1_000, monthly_micro_usd=1_000), spent_run=1_000, spent_month=1_000
    )
    _, _, _, settled = _council({"C1": ollama}, spent)
    assert settled[0].record.outcome is Outcome.VALID
    assert ollama.calls == [decision_id_for("C1", 1)]
    assert settled[0].charged == 0


def test_spend_ledger_lives_in_the_run_store(tmp_path: Path):
    root = tmp_path / "runs"
    store = _create(root, "paid", caps=Caps(run_micro_usd=1_000_000))
    guard = store.budget_guard(month_spent(root, MONTH))
    state, entity_ids = _world()
    a, b = _Priced(600_000), _Priced(600_000)
    seats = _seats_for({"C1": a, "C2": b}, entity_ids, {"C1": PRICE, "C2": PRICE})
    _drive(state, 1, seats, guard, store)
    rows = store.decisions()
    assert sorted(r["outcome"] for r in rows) == ["BUDGET", "VALID"]
    assert all(type(r["charged_micro_usd"]) is int for r in rows)
    assert store.run_spent() == 10_500
    store.close()
    # The monthly total is summed over every run store of that month.
    assert month_spent(root, MONTH) == 10_500
    assert month_spent(root, "2026-11") == 0
    reopened = RunStore.open(root / "paid")
    assert reopened.run_spent() == 10_500
    assert reopened.budget_guard(month_spent(root, MONTH)).spent_run == 10_500
    reopened.close()


# --- The council barrier ----------------------------------------------------------


class _Gated:
    """Waits until every seat has been called, then notes the state hash it sees."""

    def __init__(self, state: WorldState, started: list[str], total: int, delay: float) -> None:
        self.state = state
        self.started = started
        self.total = total
        self.delay = delay
        self.seen_hash = ""

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        self.started.append(req.decision_id)
        while len(self.started) < self.total:
            await asyncio.sleep(0)
        await asyncio.sleep(self.delay)
        self.seen_hash = state_hash(self.state)
        raw = json.dumps(_reply(req.decision_id, 300, "PL03", f"from {req.civ_id}"))
        return CognitionResult(
            raw_text=raw,
            parsed=json.loads(raw),
            status="ok",
            usage=NO_USAGE,
            model_reported="gated",
            latency_ms=0,
            attempts=1,
        )

    def describe(self) -> ModelIdentity:
        return ModelIdentity(provider="mock", model="gated", digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        return 0


BarrierRun = tuple[WorldState, dict[str, int], DecisionLog, str, dict[str, _Gated]]


def _barrier_run(delays: Mapping[str, float]) -> BarrierRun:
    state, entity_ids = _world(CIVS)
    started: list[str] = []
    providers = {civ: _Gated(state, started, len(CIVS), delays[civ]) for civ in CIVS}
    before = state_hash(state)
    log = DecisionLog()
    calls = _seats_for(providers, entity_ids)(state, 1)
    asyncio.run(hold_council(state, calls, gate=BudgetGuard(Caps()), log=log))
    return state, entity_ids, log, before, providers


def test_barrier_collects_every_seat_before_applying():
    state, entity_ids, log, before, providers = _barrier_run({"C1": 0.0, "C2": 0.01, "C3": 0.02})
    # Every provider, even the slowest, saw the world exactly as it was before the council.
    assert all(p.seen_hash == before for p in providers.values())
    assert state_hash(state) != before
    for civ in CIVS:
        entity = state.entities[entity_ids[civ]]
        assert entity["journal"] == f"from {civ}"
        assert standing_policy_of(entity).ration == 900
    assert len(log) == len(CIVS)


def test_apply_order_is_turn_order_not_arrival_order():
    state_a, entity_ids, log_a, *_ = _barrier_run({"C1": 0.0, "C2": 0.01, "C3": 0.02})
    state_b, _, log_b, *_ = _barrier_run({"C1": 0.02, "C2": 0.01, "C3": 0.0})

    turn_stream, turn_n = SITES["turn_order"]
    by_entity = {entity_id: civ for civ, entity_id in entity_ids.items()}
    ids = sorted(entity_ids.values())
    expected = [by_entity[i] for i in permutation(stream_key(SEED, 0, turn_stream), ids, turn_n)]
    assert [r.civ_id for r in log_a.records] == expected
    assert [r.civ_id for r in log_b.records] == expected
    assert [r.to_value() for r in log_a.records] == [r.to_value() for r in log_b.records]
    assert state_hash(state_a) == state_hash(state_b)


# --- Credentials ------------------------------------------------------------------


def _all_bytes(run_dir: Path) -> list[tuple[Path, bytes]]:
    out: list[tuple[Path, bytes]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        out.append((path, data))
        if path.suffix == ".zst":
            out.append((path, zstd.decompress(data)))
    return out


def test_run_store_never_contains_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    secret = "sk-test-SECRET"
    other = "sk-ant-test-OTHERSECRET"
    monkeypatch.setenv("OPENROUTER_API_KEY", secret)
    monkeypatch.setenv("ANTHROPIC_API_KEY", other)
    root = tmp_path / "runs"
    state, entity_ids = _world()
    # A careless prompt that leaks a key must still never reach the store.
    leaky = f"You are a council. Authorization: Bearer {secret} key={other}"
    providers: dict[str, Provider] = {
        "C1": MockProvider(_mock_fixture("C1", 4)),
        "C2": RuleProvider(_rule, name="steady"),
    }
    store = _create(root, "leak", config={"profile": "test", "note": f"api key {secret}"})
    _drive(state, 30, _seats_for(providers, entity_ids, system=leaky), store.budget_guard(0), store)
    assert store.decisions(), "the run must have recorded something"
    store.close()
    files = _all_bytes(root / "leak")
    assert any(p.name == "run.db" for p, _ in files)
    assert any(p.suffix == ".zst" for p, _ in files), "requests and checkpoints go to blobs"
    for path, data in files:
        for needle in (secret, other, "SECRET"):
            assert needle.encode() not in data, f"{needle!r} found in {path}"
    # The database is a real SQLite run store with the ADR-0004 settings.
    db = sqlite3.connect(root / "leak" / "run.db")
    try:
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        tables = {row[0] for row in db.execute(query)}
        assert {"manifest", "inputs", "decisions", "checkpoints"} <= tables
        assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        db.close()
