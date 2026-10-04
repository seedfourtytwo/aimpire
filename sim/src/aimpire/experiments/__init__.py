"""Experiments: model qualification, pre-registered batches and single runs (F6c, F6d, M0c).

* ``qualify``    — frozen observations through one mind; rates against thresholds;
* ``experiment`` — the pre-registration file and its hash;
* ``plan``       — the runs a file asks for (paired seeds, replicates, rotation);
* ``batch``      — running them, one run store each, and verifying the file later;
* ``preflight``  — the worst-case cost check every command makes before any call;
* ``worlds``     — the preset factories an experiment can name;
* ``play``       — ``aimpire run``: one game, its store, replay and notebook.

This package sits above ``cognition``, ``persistence`` and ``report``; the
simulation never imports it. Importing it registers the built-in worlds:

* ``m0``, the petri dish (``m0_world``), with the repository's current rules;
* ``stub``, the F6 plumbing world. It is no physics; it stays registered only
  because the F6 acceptance tests run their experiments in it.
"""

from aimpire.experiments.m0_world import build_m0_run
from aimpire.experiments.stub_world import STUB, build_stub_world
from aimpire.experiments.worlds import World, register_world
from aimpire.rules import DEFAULT_RULES_DIR

M0: str = "m0"


def _m0(seed: int, seats: int) -> World:
    """The ``m0`` preset factory: the petri dish under ``DEFAULT_RULES_DIR``, no overrides."""
    return build_m0_run(seed, DEFAULT_RULES_DIR, seats=seats)


register_world(M0, _m0)
register_world(STUB, build_stub_world)  # plumbing only: F6 acceptance tests use it
