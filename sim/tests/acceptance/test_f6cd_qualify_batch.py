"""F6c/F6d acceptance: ``aimpire qualify`` and ``aimpire batch`` (ADR-0005, ADR-0014, ADR-0018).

Written in the planning role before implementation (ADR-0016). Read-only.

* ``qualify`` feeds the frozen observations (``experiments/data``) to one
  provider and reports schema adherence, order validity, latency, tokens and
  cost, judged against a versioned thresholds file. The mock replies stored
  with the cases are scripted so the rates are known in advance:
  6 cases; 3 parse; 5 orders proposed in those 3, 4 accepted.
* Both commands print the worst-case cost first and refuse, before any
  provider is built or called and before any run store exists, when it would
  cross the remaining budget. Mock and rule minds are free.
* ``batch`` runs a pre-registered experiment file: paired seeds across arms,
  replicates, and seat rotation so every model plays every seat. Each run
  has its own run store whose manifest carries the experiment file's hash;
  a later edit of the file is detected. The same file gives the same run
  ids, seeds, checkpoint hashes and report, byte for byte.

No network: only mock and rule minds are run. The world is the placeholder
``stub`` preset until M0 registers ``m0``.
"""

import json
from pathlib import Path

import pytest

from aimpire.cli.main import main
from aimpire.experiments.batch import ExperimentChanged, run_batch, verify_batch
from aimpire.experiments.experiment import ExperimentError, file_hash, load_experiment
from aimpire.experiments.preflight import OverBudget
from aimpire.experiments.qualify import run_qualify
from aimpire.persistence.store import RunStore

pytestmark = pytest.mark.acceptance

# $100 per million tokens in and out: 8,000 + 1,000 tokens = 900,000 micro-dollars a call.
PRICEY_TOML = """
kind = "openai_compat"
model = "vendor/expensive-model"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "AIMPIRE_F6CD_UNSET_KEY"
structured_output = "json_schema"
timeout_s = 30.0
max_output_tokens = 1000

[price]
input_micro_usd_per_mtok = 100_000_000
output_micro_usd_per_mtok = 100_000_000
source = "test fixture"
as_of = "2026-10-04"

[budget]
max_input_tokens_per_call = 8000
"""

EXPERIMENT = """\
id: e-f6cd
hypothesis: "Rule baselines give usable replies at every council of the stub world."
metrics:
  primary: usable_share_ppm
  secondary: [valid_share_ppm]
world: stub
ticks: 30
council_every: 10
checkpoint_every: 10
seats: {seats}
seeds: [11, 12]
replicates: 3
arms:
  - id: places
    knowledge_arm: A0
    renderer: places
    prompt: base
    models: {models}
  - id: grid
    knowledge_arm: A2
    renderer: grid
    prompt: base
    models: {models}
"""

TWO_RULES = '["rule:forage_nearest", "rule:hold"]'


def _write_experiment(folder: Path, seats: int = 3, models: str = TWO_RULES) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "experiment.yaml"
    path.write_text(EXPERIMENT.format(seats=seats, models=models), encoding="utf-8")
    return path


def _manifests(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for db in sorted(root.glob("*/run.db")):
        with RunStore.open(db.parent, read_only=True) as store:
            manifest = store.manifest()
            manifest["checkpoints"] = store.checkpoints()
            manifest["decisions"] = [
                (r["decision_id"], r["civ_id"], r["model"], r["outcome"]) for r in store.decisions()
            ]
            out[manifest["run_id"]] = manifest
    return out


# --- qualify -------------------------------------------------------------------------


def test_qualify_mock_gives_expected_rates(tmp_path: Path):
    lines: list[str] = []
    result = run_qualify("mock", runs_root=tmp_path / "runs", echo=lines.append)
    assert lines[0].startswith("worst-case cost"), "the estimate is printed first"
    m = result.metrics
    assert (m.cases, m.parseable) == (6, 3)
    assert m.schema_adherence_ppm == 500_000
    assert (m.orders_proposed, m.orders_accepted) == (5, 4)
    assert m.order_validity_ppm == 800_000
    assert m.outcomes == {"VALID": 2, "PARTIAL": 1, "INVALID": 2, "REFUSAL": 1}
    assert (m.input_tokens, m.output_tokens, m.reasoning_tokens) == (0, 0, 0)
    assert m.priced_cost_micro_usd == 0
    assert m.reported_cost_micro_usd is None  # the mock reports no cost of its own
    assert not result.passed  # 500,000 ppm is under the schema adherence mark

    report = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert report["thresholds"]["version"] == "qualify-thresholds-v1"
    assert report["metrics"]["schema_adherence_ppm"] == 500_000
    assert report["passed"] is False
    checks = {c["name"]: c["passed"] for c in report["checks"]}
    assert checks["schema_adherence_ppm"] is False
    assert checks["order_validity_ppm"] is True
    text = result.markdown_path.read_text(encoding="utf-8")
    assert "FAIL" in text and "500000" in text.replace(",", "").replace("_", "")
    # Every case is a decision in a real run store, so the spend ledger sees it.
    with RunStore.open(result.run_dir, read_only=True) as store:
        assert len(store.decisions()) == 6


def test_qualify_rule_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    code = main(["qualify", "rule", "--runs", str(tmp_path / "runs")])
    out = capsys.readouterr().out
    assert code == 0
    assert out.splitlines()[0].startswith("worst-case cost")
    reports = sorted((tmp_path / "runs").glob("*/qualify.json"))
    assert len(reports) == 1
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    assert report["mind"] == "rule:forage_nearest"
    assert report["metrics"]["schema_adherence_ppm"] == 1_000_000
    assert report["metrics"]["order_validity_ppm"] == 1_000_000
    assert report["metrics"]["priced_cost_micro_usd"] == 0
    assert report["passed"] is True


def test_qualify_refuses_over_budget_before_any_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("AIMPIRE_F6CD_UNSET_KEY", raising=False)
    profile = tmp_path / "pricey.toml"
    profile.write_text(PRICEY_TOML, encoding="utf-8")
    runs = tmp_path / "runs"
    lines: list[str] = []
    # 6 cases at 900,000 micro-dollars each is 5.4 dollars, over the 2-dollar run cap.
    with pytest.raises(OverBudget) as refused:
        run_qualify(str(profile), runs_root=runs, echo=lines.append)
    assert refused.value.worst_case_micro_usd == 6 * 900_000
    assert lines and lines[0].startswith("worst-case cost")
    # Refused before the key was read, a provider built, or a run store created.
    assert not list(runs.glob("*/run.db"))

    code = main(["qualify", str(profile), "--runs", str(runs)])
    out = capsys.readouterr().out
    assert code == 3
    assert out.splitlines()[0].startswith("worst-case cost")
    assert "refused" in out
    assert not list(runs.glob("*/run.db"))


# --- batch ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def batch_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, dict[str, dict]]:
    base = tmp_path_factory.mktemp("batch")
    path = _write_experiment(base / "exp")
    out = base / "runs"
    run_batch(path, out_root=out, echo=lambda _line: None)
    return path, out, _manifests(out)


def test_batch_design_pairs_seeds_and_replicates(batch_run: tuple[Path, Path, dict]):
    path, _, manifests = batch_run
    experiment = load_experiment(path)
    # 2 arms x 2 seeds x 2 rotations (2 models) x 3 replicates.
    assert len(manifests) == 24
    for arm in ("places", "grid"):
        seeds = sorted(m["seed"] for m in manifests.values() if m["config"]["arm"] == arm)
        assert seeds == [11] * 6 + [12] * 6, "every arm runs on the same seeds"
    for manifest in manifests.values():
        cfg = manifest["config"]
        assert cfg["experiment"]["id"] == experiment.id == "e-f6cd"
        assert cfg["experiment"]["file_hash"] == file_hash(path)
        assert cfg["knowledge_arm"] == {"places": "A0", "grid": "A2"}[cfg["arm"]]
        assert cfg["renderer"] == cfg["arm"]
        assert cfg["prompt"]["name"] == "base"
        assert len(manifest["checkpoints"]) == 7  # 3 barriers, 3 periodic, 1 final


def test_seat_rotation_covers_every_seat_model_pairing(batch_run: tuple[Path, Path, dict]):
    _, _, manifests = batch_run
    for arm in ("places", "grid"):
        for seed in (11, 12):
            runs = [
                m for m in manifests.values() if m["config"]["arm"] == arm and m["seed"] == seed
            ]
            pairs = {(civ, model) for m in runs for civ, model in m["config"]["seats"].items()}
            civs = {civ for civ, _ in pairs}
            assert len(civs) == 3
            assert pairs == {
                (civ, model) for civ in civs for model in ("rule:forage_nearest", "rule:hold")
            }
            # The decisions were really made by the model assigned to the seat.
            for m in runs:
                for _, civ, model, _ in m["decisions"]:
                    assert f"rule:{model}" == m["config"]["seats"][civ]


def test_batch_is_reproducible(tmp_path: Path):
    path = _write_experiment(tmp_path / "exp", seats=2)
    first, second = tmp_path / "a", tmp_path / "b"
    run_batch(path, out_root=first, echo=lambda _line: None)
    run_batch(path, out_root=second, echo=lambda _line: None)
    a, b = _manifests(first), _manifests(second)
    assert sorted(a) == sorted(b)
    for run_id in a:
        assert a[run_id]["seed"] == b[run_id]["seed"]
        assert a[run_id]["checkpoints"] == b[run_id]["checkpoints"]
        assert a[run_id]["decisions"] == b[run_id]["decisions"]
        assert a[run_id]["config"] == b[run_id]["config"]
    hashes = {h for m in a.values() for *_, h in m["checkpoints"]}
    assert len(hashes) > 2, "seeds and decisions must move the state hash"
    for name in ("report.md", "report.json"):
        assert (first / "e-f6cd" / name).read_bytes() == (second / "e-f6cd" / name).read_bytes()
    assert list((first / "e-f6cd" / "charts").glob("*.svg")), "small-multiple charts"


def test_edited_experiment_file_is_detected(tmp_path: Path):
    path = _write_experiment(tmp_path / "exp", seats=1)
    out = tmp_path / "runs"
    run_batch(path, out_root=out, echo=lambda _line: None)
    assert verify_batch(path, out_root=out) == []
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace("usable replies", "valid replies"), encoding="utf-8")
    changed = verify_batch(path, out_root=out)
    assert sorted(changed) == sorted(_manifests(out)), "every run of the experiment is flagged"
    with pytest.raises(ExperimentChanged):
        run_batch(path, out_root=out, echo=lambda _line: None)
    assert main(["batch", str(path), "--out", str(out), "--verify"]) == 1


def test_batch_refuses_over_budget_before_any_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.delenv("AIMPIRE_F6CD_UNSET_KEY", raising=False)
    folder = tmp_path / "exp"
    folder.mkdir()
    (folder / "pricey.toml").write_text(PRICEY_TOML, encoding="utf-8")
    path = _write_experiment(folder, seats=1, models='["pricey.toml"]')
    out = tmp_path / "runs"
    lines: list[str] = []
    with pytest.raises(OverBudget):
        run_batch(path, out_root=out, echo=lines.append)
    assert lines[0].startswith("worst-case cost")
    assert not list(out.glob("*/run.db"))
    assert main(["batch", str(path), "--out", str(out)]) == 3
    assert capsys.readouterr().out.splitlines()[0].startswith("worst-case cost")


def test_experiment_must_be_pre_registered(tmp_path: Path):
    path = _write_experiment(tmp_path / "exp")
    text = path.read_text(encoding="utf-8")
    for edit in (
        text.replace(
            'hypothesis: "Rule baselines give usable replies at every council'
            ' of the stub world."\n',
            "",
        ),
        text.replace("  primary: usable_share_ppm\n", ""),
        text.replace("replicates: 3", "replicates: 1"),
        text.replace("knowledge_arm: A2", "knowledge_arm: A9"),
        text.replace("world: stub", "world: no-such-world"),
    ):
        path.write_text(edit, encoding="utf-8")
        with pytest.raises(ExperimentError):
            load_experiment(path)
