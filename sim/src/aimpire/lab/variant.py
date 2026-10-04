"""Resolve a variant into what a run needs: constants, derived rates, rules hash, manifest (LAB0).

This is the one call a run command makes (M0c's ``aimpire run``):

    resolved = resolve_variant(rules_dir, args.set)
    state = WorldState(run_seed=seed, rules_version="v1", rules_hash=resolved.rules_hash)
    store = RunStore.create(..., rules_hash=resolved.rules_hash, config=resolved.manifest_config())
    # systems read resolved.derived (aimpire.sim.derived.DerivedWorld), never the constants

Tags (ADR-0020): a run with any recorded override is a Lab run, tagged
``exploratory``; a knob set beyond its validated range, or a law used beyond
its own, adds ``beyond-model``. Tags go in the manifest and the report.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aimpire.lab.knobs import Layer
from aimpire.lab.overrides import Variant, parse_sets
from aimpire.rules import load_world, rules_hash
from aimpire.rules.physics import derive_world
from aimpire.rules.world import WorldConstants
from aimpire.sim.derived import DerivedWorld

EXPLORATORY = "exploratory"
BEYOND_MODEL = "beyond-model"


@dataclass(frozen=True, slots=True)
class ResolvedVariant:
    """A variant applied to a rules version directory."""

    variant: Variant
    world: WorldConstants
    """The constants after world overrides."""
    derived: DerivedWorld
    """The rates systems read (ppm of Earth)."""
    rules_hash: str
    """Rules files plus world, rules and tribe overrides."""

    @property
    def tags(self) -> tuple[str, ...]:
        """Run tags, sorted: ``exploratory`` and ``beyond-model`` when they apply."""
        tags: set[str] = set()
        if self.variant.overrides:
            tags.add(EXPLORATORY)
        if self.variant.beyond_model or self.derived.beyond_model:
            tags.add(BEYOND_MODEL)
        return tuple(sorted(tags))

    def manifest_config(self) -> dict[str, Any]:
        """JSON-ready entries for ``RunStore.create(config=...)``.

        Holds every recorded override (mind and god included), the laws used
        beyond their validated range, and the tags.
        """
        return {
            "variant": self.variant.manifest_entry(),
            "laws_beyond_model": list(self.derived.beyond_model),
            "tags": list(self.tags),
        }


def resolve_variant(rules_dir: Path, settings: Iterable[str]) -> ResolvedVariant:
    """Parse ``--set`` strings and apply them to the rules in ``rules_dir``.

    Raises ``KnobError`` for a refused override and ``RulesError`` for bad
    rules files.
    """
    variant = parse_sets(settings)
    world = load_world(rules_dir, variant.layer_values(Layer.WORLD))
    return ResolvedVariant(
        variant=variant,
        world=world,
        derived=derive_world(world),
        rules_hash=rules_hash(rules_dir, variant.hashed_overrides()),
    )
