"""The authoritative, deterministic simulation.

Pure: no I/O, no clock, no randomness except aimpire.sim.rng, integers only in
state. Imports nothing from cognition, persistence, api or cli (ADR-0003)."""
