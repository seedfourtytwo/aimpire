"""M0e acceptance: experiment E0, its pre-registration and its free dry run (ADR-0014, ADR-0018).

Written in the planning role (ADR-0016) before the batch changes. Read-only
for implementers.

E0 asks whether a model-driven mind keeps a group fed, scored against the
four M0 baselines on paired seeds. Its arms cross the renderer (``places`` or
``grid``) with the regrowth rule (``hidden`` or ``disclosed``), all in
knowledge arm A0. The design is written down in
``docs/experiments/e0-preregistration.md`` and every batch file of E0 names
that document:

* the dry run (``experiments/e0-dry-run.yaml``) uses mock and rule minds
  only, so it is free and CI runs it on a few seeds;
* the live files (``experiments/e0-*.yaml``) name model profiles and are run
  by hand, each within the run cap and the monthly cap.

What is pinned here:

1. the pre-registration's hash is stored in every run manifest of the dry run;
2. editing the pre-registration after the runs is detected (``--verify``
   fails and a new batch into the same folder is refused);
3. "disclosed" adds the rule text to the system prompt and nothing else; the
   text is rules data, neutral (ADR-0019), and suggests no strategy;
4. the live files share the dry run's arms and pre-registration and fit the
   budget before anything is spent.
"""

import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from aimpire.cli.main import main
from aimpire.cognition.disclosed import disclosure_text, load_disclosed
from aimpire.cognition.render import system_prompt
from aimpire.experiments.batch import ExperimentChanged, run_batch, verify_batch
from aimpire.experiments.experiment import file_hash, load_experiment
from aimpire.experiments.plan import cost_plan, plan_runs
from aimpire.persistence.store import RunStore

pytestmark = pytest.mark.acceptance

REPO = Path(__file__).resolve().parents[3]
RULES_V1 = REPO / "rules" / "v1"
EXPERIMENTS = REPO / "experiments"
PREREG = REPO / "docs" / "experiments" / "e0-preregistration.md"
DRY = EXPERIMENTS / "e0-dry-run.yaml"
LIVE = tuple(p for p in sorted(EXPERIMENTS.glob("e0-*.yaml")) if p != DRY)
BASELINES = ("rule:random", "rule:greedy", "rule:half_full", "rule:msy")
MODEL_ARMS = {
    ("places", "hidden"),
    ("places", "disclosed"),
    ("grid", "hidden"),
    ("grid", "disclosed"),
}
RUN_CAP_MICRO_USD = 2_000_000
MONTH_CAP_MICRO_USD = 20_000_000

# ADR-0019 section 4, as in tests/unit/test_observe.py, plus words that would hint a strategy.
BANNED = frozenset(
    {
        "king", "chief", "priest", "tax", "law", "religion", "god", "democracy", "market",
        "tribe", "leader", "ruler", "worship", "temple", "prophet", "scripture", "trade",
        "money", "state", "government",
    }
)  # fmt: skip
STRATEGY = frozenset({"half", "optimal", "optimum", "best", "should", "sustainable", "maximum"})


def _copy_design(root: Path) -> Path:
    """The dry-run file and the pre-registration, at the same relative paths, under ``root``."""
    (root / "experiments").mkdir(parents=True)
    (root / "docs" / "experiments").mkdir(parents=True)
    shutil.copy2(DRY, root / "experiments" / DRY.name)
    shutil.copy2(PREREG, root / "docs" / "experiments" / PREREG.name)
    return root / "experiments" / DRY.name


def _manifests(out: Path) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for db in sorted(out.glob("*/run.db")):
        with RunStore.open(db.parent, read_only=True) as store:
            manifest = store.manifest()
        found[manifest["run_id"]] = manifest
    return found


@pytest.fixture(scope="module")
def dry_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """The dry run, batched once from a copy of the design: ``(experiment file, runs folder)``."""
    root = tmp_path_factory.mktemp("e0")
    path = _copy_design(root)
    out = root / "runs"
    run_batch(path, out_root=out, echo=lambda _line: None)
    return path, out


def test_dry_run_is_free_and_covers_the_arms() -> None:
    exp = load_experiment(DRY)
    minds = {m.label: m for arm in exp.arms for m in arm.models}
    assert {m.kind for m in minds.values()} <= {"mock", "rule"}
    assert cost_plan(exp, plan_runs(exp)).total_micro_usd == 0
    assert exp.primary_metric == "survival_ppm"
    assert {arm.knowledge_arm for arm in exp.arms} == {"A0"}
    model_arms = [a for a in exp.arms if any(m.kind != "rule" for m in a.models)]
    assert {(a.renderer, a.rules) for a in model_arms} == MODEL_ARMS
    baseline_arms = [a for a in exp.arms if all(m.kind == "rule" for m in a.models)]
    assert [tuple(m.label for m in a.models) for a in baseline_arms] == [BASELINES]


def test_preregistration_hash_in_every_run_manifest(dry_run: tuple[Path, Path]) -> None:
    path, out = dry_run
    manifests = _manifests(out)
    assert len(manifests) == len(plan_runs(load_experiment(path)))
    expected = file_hash(PREREG)
    for manifest in manifests.values():
        assert manifest["config"]["preregistration"]["hash"] == expected


def test_edited_preregistration_is_detected(
    dry_run: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source, _ = dry_run
    root = tmp_path / "copy"
    shutil.copytree(source.parents[1], root)
    path, out = root / "experiments" / DRY.name, root / "runs"
    assert verify_batch(path, out_root=out) == []
    prereg = root / "docs" / "experiments" / PREREG.name
    prereg.write_text(prereg.read_text(encoding="utf-8") + "\nA line added after the run.\n")
    assert sorted(verify_batch(path, out_root=out)) == sorted(_manifests(out))
    assert main(["batch", str(path), "--out", str(out), "--verify"]) == 1
    assert "edited after run" in capsys.readouterr().out
    with pytest.raises(ExperimentChanged):
        run_batch(path, out_root=out, echo=lambda _line: None)


def test_disclosed_rule_is_rule_text_only(dry_run: tuple[Path, Path]) -> None:
    text = disclosure_text(load_disclosed(RULES_V1))
    words = set(re.findall(r"[a-z]+", text.lower()))
    assert not words & BANNED
    assert not words & STRATEGY
    assert "0.08" in text and "0.001" in text  # r and s a day, from rules/v1/m0.yaml
    exp = load_experiment(DRY)
    for arm in exp.arms:
        expected = system_prompt() + text if arm.rules == "disclosed" else system_prompt()
        assert arm.prompt_text == expected
    _, out = dry_run
    recorded = {m["config"]["arm"]: m["config"]["rules"] for m in _manifests(out).values()}
    assert recorded == {a.id: a.rules for a in exp.arms}


def test_live_files_share_the_design_and_fit_the_budget() -> None:
    assert LIVE, "E0 needs at least one live batch file"
    dry = load_experiment(DRY)
    dry_arms = {a.id: (a.knowledge_arm, a.renderer, a.rules) for a in dry.arms}
    dry_raw = yaml.safe_load(DRY.read_text(encoding="utf-8"))
    for path in LIVE:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert raw["preregistration"] == dry_raw["preregistration"], path.name
        profiles = [str(m) for a in raw["arms"] for m in a["models"] if str(m).endswith(".toml")]
        assert profiles, f"{path.name} names no model profile"
        if not all((path.parent / p).is_file() for p in profiles):
            continue  # a profile the creator makes from a template first (see the file)
        exp = load_experiment(path)
        for arm in exp.arms:
            assert dry_arms[arm.id] == (arm.knowledge_arm, arm.renderer, arm.rules), path.name
        plan = cost_plan(exp, plan_runs(exp))
        assert plan.largest_run_micro_usd <= RUN_CAP_MICRO_USD, path.name
        assert plan.total_micro_usd <= MONTH_CAP_MICRO_USD, path.name
