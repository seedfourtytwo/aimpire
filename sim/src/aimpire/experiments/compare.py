"""What a batch report adds when its world records measures: bands per group, paired comparisons.

* ``group_bands``: for one group (arm, mind), each measure at every
  checkpoint as the 10th percentile, lower median and 90th percentile over
  its runs. These are the same bands as a reference ensemble's, so a mind
  can be laid beside the baselines.
* ``paired_comparisons``: ADR-0014 makes the world seed the unit of analysis.
  Every group whose mind is not a rule is compared with every rule-baseline
  group of the same experiment, on the primary metric, seed by seed. A
  group's value on a seed is the lower median over its runs on that seed
  (replicates and rotations), so each seed counts once. The statistics are
  exact (``stats.paired``): wins, ties, losses, the median difference with
  its order-statistic 95 % interval, and the probability of superiority.

* ``arm_comparisons``: the same model under two arms (renderer, rule
  disclosure), seed by seed, with the same statistics.

Rule groups are not compared with one another here; the reference
ensemble does that over many more seeds.
"""

from collections.abc import Sequence
from typing import Any

from aimpire.experiments.experiment import Experiment
from aimpire.experiments.measures import MEASURE_NAMES
from aimpire.experiments.stats import HIGH_PERMILLE, LOW_PERMILLE, PERMILLE, paired, quantile
from aimpire.experiments.summary import RunSummary


def seated(runs: Sequence[RunSummary], arm: str, mind: str) -> list[RunSummary]:
    """The runs of ``arm`` in which ``mind`` held a seat."""
    return [r for r in runs if r.arm == arm and mind in r.minds()]


def group_bands(runs: Sequence[RunSummary], mind: str) -> dict[str, Any] | None:
    """Checkpoints and per-measure bands of ``mind`` over ``runs``; ``None`` without measures."""
    all_series = [s for r in runs if (s := r.series(mind)) is not None]
    if not all_series or len(all_series) != len(runs):
        return None
    checkpoints: list[int] = runs[0].measures["checkpoints"]  # pyright: ignore[reportOptionalSubscript]
    bands: dict[str, dict[str, list[int]]] = {}
    for name in MEASURE_NAMES:
        columns = [[s[name][i] for s in all_series] for i in range(len(checkpoints))]
        bands[name] = {
            "q10": [quantile(c, LOW_PERMILLE) for c in columns],
            "median": [quantile(c, PERMILLE // 2) for c in columns],
            "q90": [quantile(c, HIGH_PERMILLE) for c in columns],
        }
    return {"checkpoints": list(checkpoints), "bands": bands}


def _per_seed(runs: Sequence[RunSummary], mind: str, metric: str) -> dict[int, int]:
    """The lower median of ``metric`` over ``mind``'s runs on each seed."""
    values: dict[int, list[int]] = {}
    for run in runs:
        values.setdefault(run.seed, []).append(run.metrics(mind)[metric])
    return {seed: quantile(v, PERMILLE // 2) for seed, v in sorted(values.items())}


def paired_comparisons(exp: Experiment, runs: Sequence[RunSummary]) -> list[dict[str, Any]]:
    """Each model group against each rule-baseline group, on the primary metric."""
    groups = [(arm.id, m.label, m.kind) for arm in exp.arms for m in arm.models]
    rules = [(a, m) for a, m, kind in groups if kind == "rule"]
    found: list[dict[str, Any]] = []
    for arm, mind, kind in groups:
        if kind == "rule":
            continue
        mine = _per_seed(seated(runs, arm, mind), mind, exp.primary_metric)
        for rule_arm, rule in rules:
            theirs = _per_seed(seated(runs, rule_arm, rule), rule, exp.primary_metric)
            if set(mine) & set(theirs):
                found.append(
                    {
                        "arm": arm,
                        "mind": mind,
                        "baseline_arm": rule_arm,
                        "baseline": rule,
                        "metric": exp.primary_metric,
                        **paired(mine, theirs),
                    }
                )
    return found


def arm_comparisons(exp: Experiment, runs: Sequence[RunSummary]) -> list[dict[str, Any]]:
    """The same model under two arms, seed by seed, on the primary metric.

    Arms are paired in file order (earlier arm as ``arm_a``), so the renderer
    and disclosure contrasts of E0 read as "places minus grid" and "hidden
    minus disclosed" when the file lists them that way.
    """
    found: list[dict[str, Any]] = []
    for i, first in enumerate(exp.arms):
        for second in exp.arms[i + 1 :]:
            labels = {m.label for m in second.models}
            shared = [m for m in first.models if m.kind != "rule" and m.label in labels]
            for mind in shared:
                a = _per_seed(seated(runs, first.id, mind.label), mind.label, exp.primary_metric)
                b = _per_seed(seated(runs, second.id, mind.label), mind.label, exp.primary_metric)
                if set(a) & set(b):
                    found.append(
                        {
                            "mind": mind.label,
                            "arm_a": first.id,
                            "arm_b": second.id,
                            "metric": exp.primary_metric,
                            **paired(a, b),
                        }
                    )
    return found
