"""F2d acceptance: world state, entity ids and the canonical state hash (ADR-0007, ADR-0012).

Written by the planning model before implementation (ADR-0016). Read-only.
GOLDEN_HASH pins the hash format: changing it invalidates every stored run.
"""

import os
import subprocess
import sys

import numpy as np
import pytest

from aimpire.sim.hashing import diff_parts, state_hash, subsystem_hashes
from aimpire.sim.state import WorldState

pytestmark = pytest.mark.acceptance

GOLDEN_HASH = "309c58ccaeae4f5bf2849be231bdc956e7fd8fdc0d81ad4b71dcb6d31d3fb92f"

BUILD = """
import numpy as np
from aimpire.sim.state import WorldState

def build(layer_order=("food", "moisture"), entity_order=(0, 1, 2)):
    s = WorldState(run_seed=42, rules_version="v1", rules_hash="abc", tick=7)
    grids = {
        "food": np.arange(12, dtype=np.int64).reshape(3, 4) * 1000,
        "moisture": np.full((3, 4), 500, dtype=np.int64),
    }
    for name in layer_order:
        s.add_layer(name, grids[name])
    specs = [
        ("person", {"energy": 5000, "name": "Ana", "alive": True, "carry": {"food": 3}}),
        ("person", {"energy": 4200, "name": "Bo", "alive": True, "carry": {}}),
        ("place", {"tiles": [[0, 0], [0, 1]], "label": None}),
    ]
    ids = {i: s.allocate_id() for i in range(3)}
    for i in entity_order:
        kind, fields = specs[i]
        s.entities[ids[i]] = {"kind": kind, **fields}
    s.carries["food"][1, 2] = 17
    return s
"""

_ns: dict[str, object] = {}
exec(BUILD, _ns)  # the same builder runs in this process and in fresh interpreters
build = _ns["build"]  # type: ignore[assignment]


def _hash_in_fresh_process(hashseed: str) -> str:
    code = BUILD + "\nfrom aimpire.sim.hashing import state_hash\nprint(state_hash(build()))\n"
    env = {**os.environ, "PYTHONHASHSEED": hashseed}
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def test_hash_stable_across_processes() -> None:
    """Two fresh interpreters with different hash seeds give the same hash as this one."""
    here = state_hash(build())  # type: ignore[operator]
    assert _hash_in_fresh_process("1") == here
    assert _hash_in_fresh_process("12345") == here


def test_hash_matches_golden_value() -> None:
    """Pins the format across machines, Python and numpy versions."""
    assert state_hash(build()) == GOLDEN_HASH  # type: ignore[operator]


def test_hash_ignores_insertion_order() -> None:
    a = build()  # type: ignore[operator]
    b = build(layer_order=("moisture", "food"), entity_order=(2, 0, 1))  # type: ignore[operator]
    assert list(a.entities) != list(b.entities) and list(a.layers) != list(b.layers)
    assert state_hash(a) == state_hash(b)


def test_hash_changes_with_any_field() -> None:
    base = build()  # type: ignore[operator]
    base_hash = state_hash(base)

    def changed(mutate: str) -> tuple[str, list[str]]:
        s = build()  # type: ignore[operator]
        exec(mutate, {"s": s, "np": np})
        return state_hash(s), diff_parts(base, s)

    cases = {
        "s.tick += 1": ["meta"],
        "s.next_id += 1": ["meta"],
        "s.run_seed = 43": ["meta"],
        "s.rules_version = 'v2'": ["meta"],
        "s.rules_hash = 'abd'": ["meta"],
        "s.layers['food'][0, 0] += 1": ["layer:food"],
        "s.carries['moisture'][2, 3] = 1": ["carry:moisture"],
        "s.entities[1]['energy'] = 5001": ["entities:person"],
        "s.entities[3]['tiles'][1][1] = 2": ["entities:place"],
        "s.add_entity('person', {'energy': 1})": ["entities:person", "meta"],
    }
    for mutate, parts in cases.items():
        new_hash, diff = changed(mutate)
        assert new_hash != base_hash, mutate
        assert diff == parts, mutate


def test_float_in_state_rejected() -> None:
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="x")
    with pytest.raises(TypeError):
        s.add_entity("person", {"energy": 1.5})  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        s.add_entity("person", {"pos": [1, 2.0]})  # type: ignore[list-item]
    with pytest.raises(TypeError):
        s.add_layer("food", np.zeros((2, 2), dtype=np.float64))  # type: ignore[arg-type]
    # Bypassing add_entity: the hash must still refuse a float.
    s.entities[s.allocate_id()] = {"kind": "person", "energy": 0.5}  # type: ignore[dict-item]
    with pytest.raises(TypeError):
        state_hash(s)


def test_numpy_scalars_rejected() -> None:
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="x")
    with pytest.raises(TypeError):
        s.add_entity("person", {"energy": np.int64(3)})  # type: ignore[dict-item]


def test_ids_are_monotonic_and_never_reused() -> None:
    s = WorldState(run_seed=1, rules_version="v1", rules_hash="x")
    first = s.add_entity("person", {})
    second = s.add_entity("person", {})
    del s.entities[first]
    third = s.add_entity("person", {})
    assert (first, second, third) == (1, 2, 3)
    s.entities[99] = {"kind": "person"}  # an id the allocator never issued
    with pytest.raises(ValueError):
        state_hash(s)


def test_subsystem_hash_names() -> None:
    names = list(subsystem_hashes(build()))  # type: ignore[operator]
    assert names == sorted(names)
    assert set(names) == {
        "meta", "layer:food", "carry:food", "layer:moisture", "carry:moisture",
        "entities:person", "entities:place",
    }  # fmt: skip
