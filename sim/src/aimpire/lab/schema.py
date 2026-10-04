"""The knob registry as JSON Schema, for ``schema/lab-knobs.schema.json`` (ADR-0020).

The schema validates an overrides object (``{"world.gravity": 950000}``):
types, allowed ranges and choices are standard JSON Schema keywords, so any
validator refuses what ``parse_sets`` refuses. What standard keywords cannot
say (layer, unit, validated range, whether it enters the rules hash) goes in
an ``x-aimpire`` block per knob, for the CLI, the reports and the workshop page.

Written by ``python -m aimpire.contracts.export`` like the mind contract;
never hand-edit the file.
"""

from typing import Any

from aimpire.lab.knobs import KNOBS, Knob

SCHEMA_FILE = "lab-knobs.schema.json"


def _property(knob: Knob) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "layer": knob.layer.value,
        "unit": knob.unit,
        "in_rules_hash": knob.in_rules_hash,
    }
    prop: dict[str, Any] = {"description": knob.description, "default": knob.default}
    if knob.kind == "enum":
        prop |= {"type": "string", "enum": list(knob.choices)}
    else:
        assert knob.allowed is not None
        low, high = knob.allowed
        prop |= {"type": "integer", "minimum": low, "maximum": high}
        v_low, v_high = knob.validated or knob.allowed
        meta["validated"] = {"minimum": v_low, "maximum": v_high}
    prop["x-aimpire"] = meta
    return prop


def knob_schema() -> dict[str, Any]:
    """The registry as a JSON Schema document (plain dict; the exporter serialises it)."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Aimpire Lab overrides",
        "description": (
            "Knobs settable with --set path=value. Values outside a knob's validated "
            "range are allowed but tag the run beyond-model (ADR-0020)."
        ),
        "type": "object",
        "additionalProperties": False,
        "properties": {knob.path: _property(knob) for knob in KNOBS},
    }
