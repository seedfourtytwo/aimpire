"""Experiments: qualification, pre-registered batches, reference ensembles, single runs.

Backlog items F6c, F6d, M0c, M0d and M0e.

* ``qualify``    — frozen observations through one mind; rates against thresholds;
* ``experiment`` — the pre-registration file and its hash;
* ``plan``       — the runs a file asks for (paired seeds, replicates, rotation);
* ``batch``      — running them, one run store each, and verifying the file later;
* ``preflight``  — the worst-case cost check every command makes before any call;
* ``worlds``     — the preset factories an experiment can name;
* ``play``       — ``aimpire run``: one game, its store, replay and notebook;
* ``measures``   — observer measures of each seat at checkpoints (M0d, M0e);
* ``reference``  — reference ensembles of rule baselines and their bands (M0d):
  the file (``reference_file``), the runs, and the page (``reference_report``);
* ``compare``    — bands per group and paired comparisons in a batch report;
* ``stats``      — exact, integer quantiles, intervals and paired differences.

This package sits above ``cognition``, ``persistence`` and ``report``; the
simulation never imports it. Importing it registers the built-in worlds:

* ``m0``, the petri dish (``m0_world``), with the repository's current rules,
  and its observer measures (``report.m0_run.m0_measures``);
* ``stub``, the F6 plumbing world. It is no physics; it stays registered only
  because the F6 acceptance tests run their experiments in it.
"""

from collections.abc import Mapping

from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.measures import register_measures
from aimpire.experiments.stub_world import STUB, build_stub_world
from aimpire.experiments.worlds import World, register_world
from aimpire.report.m0_run import m0_measures
from aimpire.report.metrics import MetricFn
from aimpire.rules import DEFAULT_RULES_DIR
from aimpire.sim.state import WorldState
from aimpire.sim.systems.tribe import population

M0: str = "m0"


def _m0(seed: int, seats: int) -> World:
    """The ``m0`` preset factory: the petri dish under ``DEFAULT_RULES_DIR``, no overrides."""
    return build_m0_run(seed, DEFAULT_RULES_DIR, seats=seats)


def _m0_measures(state: WorldState, entity_id: int) -> Mapping[str, MetricFn]:
    """The ``m0`` measures of one seat, counting deaths from its people at tick 0."""
    return m0_measures(entity_id, population(state.entities[entity_id]))


register_world(M0, _m0)
register_measures(M0, _m0_measures)
register_world(STUB, build_stub_world)  # plumbing only: F6 acceptance tests use it
