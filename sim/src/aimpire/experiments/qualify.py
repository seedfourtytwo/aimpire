"""``aimpire qualify``: put one mind through the frozen observations (backlog F6c, ADR-0014).

Why each case goes through the council barrier: qualification must measure
the path a real run takes, not a shortcut. Every case is one council with one
seat (``cognition.council.hold_council``): the budget gate reserves before the
call, the validator judges the reply against what the observation showed,
and the run store keeps the request, the response and the spend. So the
monthly ledger sees qualification spend, and live calls are kept for audit.

Measured (integers; rates in parts per million):
    schema adherence   replies that parse as a ``MindReply`` / cases
    order validity     orders accepted / orders proposed in parseable replies
    latency            lower median and maximum of the calls made, in ms
    tokens             input, output and reasoning, summed
    cost               the profile-priced charge, and the provider's own figure
                       when it reports one

The verdict compares these with a versioned thresholds file. Order validity
with no orders proposed has no value and fails its mark.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from aimpire import __version__
from aimpire.cognition.budget import Caps
from aimpire.cognition.council import SeatCall, Settled, hold_council
from aimpire.cognition.minds import MindSpec, build_provider, resolve_mind
from aimpire.cognition.protocol import Provider
from aimpire.cognition.reachability import check_reachable
from aimpire.cognition.render import render_places, system_prompt
from aimpire.cognition.seats import request_for, seat_from_observation
from aimpire.contracts.mind import Observation
from aimpire.experiments.preflight import CostPlan, Echo, check_budget, spent_this_month
from aimpire.experiments.qualify_data import (
    DEFAULT_CASES,
    DEFAULT_THRESHOLDS,
    Cases,
    load_cases,
    load_thresholds,
)
from aimpire.experiments.qualify_verdict import (
    Check,
    QualifyMetrics,
    judge,
    measure,
    verdict_data,
)
from aimpire.persistence.spend import DB_NAME, current_month
from aimpire.persistence.store import RunStore
from aimpire.report.qualify import qualify_markdown
from aimpire.sim.actions import DecisionLog
from aimpire.sim.actions.commit import CIV_KIND
from aimpire.sim.state import WorldState

QUALIFY_RULES: Final = "qualify"


@dataclass(frozen=True, slots=True)
class QualifyResult:
    """The verdict and where it was written."""

    run_id: str
    run_dir: Path
    mind: str
    metrics: QualifyMetrics
    checks: tuple[Check, ...]
    passed: bool
    markdown_path: Path
    json_path: Path


def _run_id(runs_root: Path, label: str) -> str:
    """``qualify-<mind>-<n>``: the first number not yet used under ``runs_root``."""
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    n = 1
    while (runs_root / f"qualify-{slug}-{n:03d}" / DB_NAME).exists():
        n += 1
    return f"qualify-{slug}-{n:03d}"


def _case_world(obs: Observation, cases_hash: str) -> tuple[WorldState, int]:
    """A one-civilization state for the barrier to commit into; it holds no world."""
    state = WorldState(run_seed=0, rules_version=QUALIFY_RULES, rules_hash=cases_hash)
    state.tick = obs.calendar.tick
    policy = seat_from_observation(obs).policy.to_value()
    entity_id = state.add_entity(
        CIV_KIND, {"civ_id": obs.civ_id, "policy": policy, "journal": obs.journal}
    )
    return state, entity_id


async def _ask_all(
    cases: Cases, mind: MindSpec, provider: Provider, store: RunStore, spent_month: int
) -> list[Settled]:
    """One council per case, in file order, gated by the store's budget guard."""
    guard = store.budget_guard(spent_month)
    log = DecisionLog()
    settled: list[Settled] = []
    for council, case in enumerate(cases.cases, start=1):
        obs = case.observation
        state, entity_id = _case_world(obs, cases.file_hash)
        request = request_for(obs, render_places(obs), system_prompt(), mind)
        call = SeatCall(entity_id, seat_from_observation(obs), request, provider, mind.price)
        result = await hold_council(state, [call], gate=guard, log=log)
        store.record_council(state.tick, council, result)
        settled.extend(result)
    return settled


def _open_store(runs_root: Path, mind: MindSpec, cases: Cases, month: str) -> RunStore:
    run_id = _run_id(runs_root, mind.label)
    return RunStore.create(
        runs_root / run_id,
        run_id=run_id,
        seed=0,
        rules_version=QUALIFY_RULES,
        rules_hash=cases.file_hash,
        caps=Caps(run_micro_usd=mind.run_cap_micro_usd),
        month=month,
        config={"qualify": {"mind": mind.label, "cases": cases.version}},
        code_version=__version__,
    )


def run_qualify(  # noqa: PLR0913 (each is a separate input file or folder)
    mind_name: str,
    *,
    runs_root: Path,
    cases_path: Path = DEFAULT_CASES,
    thresholds_path: Path = DEFAULT_THRESHOLDS,
    month: str | None = None,
    echo: Echo = print,
) -> QualifyResult:
    """Qualify ``mind_name`` (``mock``, ``rule[:name]`` or a profile path); write the report.

    Prints the worst case first and raises ``OverBudget`` before any provider
    is built when it does not fit the remaining budget.
    """
    mind = resolve_mind(mind_name, Path.cwd())
    cases, thresholds = load_cases(cases_path), load_thresholds(thresholds_path)
    month = month or current_month()
    worst = len(cases.cases) * mind.worst_case_call_micro_usd
    plan = CostPlan(worst, worst, mind.run_cap_micro_usd)
    check_budget(plan, runs_root=runs_root, month=month, echo=echo)
    if mind.kind == "profile":
        check_reachable(mind)  # before the cases, so FAIL always means the model, not the server
    mocks = {c.observation.decision_id: c.mock for c in cases.cases}
    provider = build_provider(mind, mocks)
    spent_month = spent_this_month(runs_root, month)
    with _open_store(runs_root, mind, cases, month) as store:
        settled = asyncio.run(_ask_all(cases, mind, provider, store, spent_month))
        run_id, run_dir = store.run_id, store.run_dir
    metrics = measure(settled)
    checks = judge(metrics, thresholds)
    data = verdict_data(
        run_id=run_id,
        mind=mind.label,
        cases=cases,
        thresholds=thresholds,
        metrics=metrics,
        checks=checks,
    )
    md, js = _write_report(run_dir, data)
    echo(f"{'PASS' if data['passed'] else 'FAIL'}: {mind.label}; report {md}")
    if metrics.outcomes.get("PROVIDER_ERROR", 0) == metrics.cases:
        echo(
            "every call failed with PROVIDER_ERROR: a provider problem, not a verdict on the model"
        )
    return QualifyResult(run_id, run_dir, mind.label, metrics, checks, data["passed"], md, js)


def _write_report(run_dir: Path, data: dict[str, Any]) -> tuple[Path, Path]:
    """``qualify.md`` and ``qualify.json`` beside the run store."""
    md, js = run_dir / "qualify.md", run_dir / "qualify.json"
    md.write_text(qualify_markdown(data), encoding="utf-8")
    js.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return md, js
