"""First divergence of two twin runs, part by part (ADR-0020 section 6, LAB1).

Why part by part: ``hashing.subsystem_hashes`` splits the state into named
parts (tile layers, carry layers, one part per entity kind), so comparing two
runs tick by tick says not only *when* the worlds parted but *where* first:
the food on the tiles, the tribe's stores, its knowledge of the map...

What is compared: every part except ``meta``. ``meta`` holds the rules hash,
and a variant's overrides enter the rules hash by design (LAB0), so ``meta``
differs from tick 0 in every real twin and would hide the answer. The run
seed and tick in ``meta`` are equal in a twin by construction, and ``next_id``
only moves when an entity is added, which an entity part shows too.

Units: ticks (game days). Tick 0 is the state after worldgen, before any step.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

META: Final = "meta"

Hashes = Mapping[str, str]
"""``subsystem_hashes`` of one state: ``{part: hex digest}``."""


def world_parts_differing(a: Hashes, b: Hashes) -> list[str]:
    """Sorted names of the non-``meta`` parts whose digests differ (a missing part differs)."""
    names = (a.keys() | b.keys()) - {META}
    return sorted(name for name in names if a.get(name) != b.get(name))


@dataclass(frozen=True, slots=True)
class Divergence:
    """Where one seed's twin runs first differed, and what still differed at the end."""

    seed: int
    first_tick: int | None
    """First tick at which any world part differs; ``None`` if they never do."""
    first_parts: tuple[str, ...]
    """The parts that differ at ``first_tick``, sorted; empty if never."""
    final_parts: tuple[str, ...]
    """The parts that differ at the last compared tick, sorted."""
    part_first_ticks: tuple[tuple[str, int], ...] = field(default=())
    """Every part that ever differed, with its own first tick, by tick then name."""

    def to_json(self) -> dict[str, Any]:
        """JSON-ready record for ``twin.json``."""
        return {
            "seed": self.seed,
            "first_tick": self.first_tick,
            "first_parts": list(self.first_parts),
            "final_parts": list(self.final_parts),
            "part_first_ticks": {name: tick for name, tick in self.part_first_ticks},
        }


def first_divergence(
    seed: int, ticks: Sequence[int], baseline: Sequence[Hashes], variant: Sequence[Hashes]
) -> Divergence:
    """Compare two runs' per-tick hashes (same ``ticks``, in order) and summarise.

    ``ValueError`` if the three sequences differ in length or are empty: a
    twin compares the same ticks on both sides.
    """
    if not ticks or not len(ticks) == len(baseline) == len(variant):
        raise ValueError("a twin compares the same, non-empty list of ticks on both sides")
    first: dict[str, int] = {}
    first_tick: int | None = None
    first_parts: list[str] = []
    differing: list[str] = []
    for tick, a, b in zip(ticks, baseline, variant, strict=True):
        differing = world_parts_differing(a, b)
        for name in differing:
            first.setdefault(name, tick)
        if differing and first_tick is None:
            first_tick, first_parts = tick, differing
    return Divergence(
        seed=seed,
        first_tick=first_tick,
        first_parts=tuple(first_parts),
        final_parts=tuple(differing),
        part_first_ticks=tuple(sorted(first.items(), key=lambda item: (item[1], item[0]))),
    )
