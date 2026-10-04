"""Experiments: model qualification and pre-registered batches (backlog F6c, F6d, ADR-0014).

* ``qualify``    — frozen observations through one mind; rates against thresholds;
* ``experiment`` — the pre-registration file and its hash;
* ``plan``       — the runs a file asks for (paired seeds, replicates, rotation);
* ``batch``      — running them, one run store each, and verifying the file later;
* ``preflight``  — the worst-case cost check both commands make before any call;
* ``worlds``     — the preset factories an experiment can name.

This package sits above ``cognition``, ``persistence`` and ``report``; the
simulation never imports it. Importing it registers the built-in worlds.
"""

from aimpire.experiments.stub_world import STUB, build_stub_world
from aimpire.experiments.worlds import register_world

register_world(STUB, build_stub_world)  # PLACEHOLDER until M0 registers "m0"
