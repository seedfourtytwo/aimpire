"""The Tinkering Lab (ADR-0020): knobs, overrides and variants.

Sits above the simulation: ``aimpire.sim`` never imports it. Modules:
    * ``knobs``: the registry of every tunable;
    * ``overrides``: ``--set path=value`` parsing into a canonical ``Variant``;
    * ``variant``: ``resolve_variant``, the call a run command makes;
    * ``schema``: the registry as JSON Schema for ``schema/``;
    * ``twin``, ``twin_side``, ``divergence``, ``physics_view``: ``aimpire lab
      twin``, the baseline and a variant on paired seeds (LAB1).
"""
