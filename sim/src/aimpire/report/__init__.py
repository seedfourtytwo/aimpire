"""Reports on runs: metric tables, dot frames, PNG and SVG output, replays, notebooks (F4).

Why a separate package: reporting writes files, and ``aimpire.sim`` does no
I/O. This package reads ``WorldState`` and ledger data; the simulation never
imports it (import-linter contract ``sim-is-pure``).

Everything derived from state stays integer. Floats appear only as display
coordinates inside SVG text.
"""
