"""``--set path=value`` overrides and the variant they define (ADR-0020, LAB0).

A **variant** is a preset plus canonical overrides. Canonical means: each
value checked and normalised by its knob (``950_000`` and ``950000`` are the
same integer), one entry per path, sorted by path. The variant id is a hash of
that canonical form, so the order and spelling of ``--set`` flags never
change it.

Routing (by knob layer):
    * ``world``, ``rules``, ``tribe``: ``hashed_overrides()``, which enter the
      rules hash, because they change the world itself;
    * ``mind``, ``god``: recorded in the manifest only; the world is the same;
    * ``display``: never recorded and not part of the variant id.
"""

import argparse
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Final

from aimpire.lab.knobs import RECORDED_LAYERS, KnobError, Layer, Value, get_knob

__all__ = ["KnobError", "Variant", "add_set_option", "parse_sets"]

VARIANT_ID_BYTES: Final = 8
"""Variant ids are 16 hex characters: short enough to read, ample for a lab notebook."""


@dataclass(frozen=True, slots=True)
class Variant:
    """Canonical overrides, their id and the knobs set beyond their validated range."""

    overrides: tuple[tuple[str, Value], ...]
    """``(path, value)`` pairs sorted by path; display knobs excluded."""
    variant_id: str
    beyond_model: tuple[str, ...]
    """Paths of knobs set outside their validated range, sorted."""

    def layer_values(self, layer: Layer) -> dict[str, Value]:
        """This layer's overrides keyed by bare name: ``{"gravity": 950_000}``."""
        prefix = f"{layer.value}."
        return {
            path.removeprefix(prefix): v for path, v in self.overrides if path.startswith(prefix)
        }

    def hashed_overrides(self) -> dict[str, Value]:
        """The overrides that enter the rules hash, keyed by full path."""
        return {path: v for path, v in self.overrides if get_knob(path).in_rules_hash}

    def manifest_entry(self) -> dict[str, Any]:
        """The JSON-ready record of this variant for the run manifest."""
        return {
            "id": self.variant_id,
            "overrides": dict(self.overrides),
            "beyond_model": list(self.beyond_model),
        }


def _split(setting: str) -> tuple[str, str]:
    path, sep, text = setting.partition("=")
    if not sep or not path.strip() or not text.strip():
        raise KnobError(f"expected --set path=value, got {setting!r}")
    return path.strip(), text


def variant_id(overrides: Iterable[tuple[str, Value]]) -> str:
    """BLAKE2b hash of the canonical JSON of ``overrides`` (sorted, compact)."""
    canonical = json.dumps(sorted(overrides), separators=(",", ":"))
    digest = hashlib.blake2b(
        b"aimpire-variant-v1\0" + canonical.encode(), digest_size=VARIANT_ID_BYTES
    )
    return digest.hexdigest()


def parse_sets(settings: Iterable[str]) -> Variant:
    """Parse ``path=value`` strings into a canonical ``Variant``.

    Refuses (``KnobError``): a malformed setting, an unknown knob, a path set
    more than once, and a value outside the knob's allowed range or choices.
    A value inside the allowed but outside the validated range is accepted and
    listed in ``beyond_model``.
    """
    values: dict[str, Value] = {}
    for setting in settings:
        path, text = _split(setting)
        knob = get_knob(path)
        if path in values:
            raise KnobError(f"{path} is set more than once")
        values[path] = knob.parse(text)
    recorded = sorted(
        (path, value) for path, value in values.items() if get_knob(path).layer in RECORDED_LAYERS
    )
    beyond = tuple(sorted(p for p, v in values.items() if get_knob(p).beyond_validated(v)))
    return Variant(overrides=tuple(recorded), variant_id=variant_id(recorded), beyond_model=beyond)


def add_set_option(parser: argparse.ArgumentParser) -> None:
    """Add the repeatable ``--set path=value`` option to a run-starting command.

    The parsed list lands in ``args.set``; pass it to ``parse_sets`` or
    ``aimpire.lab.variant.resolve_variant``.
    """
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="PATH=VALUE",
        help=(
            "override a knob, e.g. world.gravity=950000 "
            "(repeatable; see schema/lab-knobs.schema.json)"
        ),
    )
