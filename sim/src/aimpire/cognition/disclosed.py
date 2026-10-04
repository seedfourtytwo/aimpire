"""The disclosed M0 rule: the numbers a rule baseline may know besides its observation.

Why a separate record: a baseline must decide from its observation only,
never from world truth (CLAUDE.md, truth / evidence / belief). But a harvest
policy also needs the rule it is playing under: how much a person eats, how
much a forager carries home per trip and, for ``msy``, the regrowth law. Those
are rules data, the same for every world of a rules version, not facts about
one world. The M0 experiment calls this "the rule disclosed" (backlog M0e);
this record is exactly that disclosure and nothing more.

What it deliberately leaves out: tile ceilings and fertility (a baseline
estimates each place's ceiling from what it has seen), the W0 rates of a Lab
variant (a baseline plans with Earth's carry load, as people would who never
measured their own world), the starvation chance and spoilage.

Units: food in milli-units (mu); ``need`` and ``carry`` per tick and per trip;
the regrowth ``r`` and ``s`` as exact per-tick fractions (``Fraction``, so the
analytic optimum is computed without floats).
"""

from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Final

from aimpire.rules import DEFAULT_RULES_DIR, load_calendar, load_m0_rules
from aimpire.sim.calendar import Calendar
from aimpire.sim.fixed import PPM
from aimpire.sim.world import M0Rules

MILLI: Final = 1000
"""Milli-units per whole unit, as the observation counts food."""


@dataclass(frozen=True, slots=True)
class Disclosed:
    """The M0 rule as a baseline may know it."""

    need_mu: Fraction
    """Food one person eats in one tick on a full ration, mu."""
    carry_mu: int
    """Food one forager brings home per trip at Earth gravity, mu."""
    regrowth_r: Fraction
    """Logistic regrowth rate per tick (ADR-0012 regrowth law)."""
    regrowth_s: Fraction
    """Seed term per tick: growth per unit of the gap to the ceiling."""

    def msy_stock(self) -> Fraction:
        """Stock share x* = (1 - s/r) / 2 at which the steady yield peaks."""
        return (1 - self.regrowth_s / self.regrowth_r) / 2

    def msy_yield(self, ceiling_mu: int) -> Fraction:
        """Steady yield per tick at x*: K (r + s)^2 / (4 r), mu."""
        r, s = self.regrowth_r, self.regrowth_s
        return ceiling_mu * (r + s) ** 2 / (4 * r)


def disclosed_from_rules(rules: M0Rules, calendar: Calendar) -> Disclosed:
    """The disclosure of ``rules`` under ``calendar`` (periods resolved to ticks)."""
    need_mu, need_per = rules.food_need.resolve(calendar)
    r_ppm, r_per = rules.regrowth_rate.resolve(calendar)
    s_ppm, s_per = rules.regrowth_seed.resolve(calendar)
    return Disclosed(
        need_mu=Fraction(need_mu, need_per),
        carry_mu=rules.carry_per_trip,
        regrowth_r=Fraction(r_ppm, PPM * r_per),
        regrowth_s=Fraction(s_ppm, PPM * s_per),
    )


def load_disclosed(rules_dir: Path) -> Disclosed:
    """Read the disclosure from a rules version directory."""
    calendar = load_calendar(rules_dir)
    return disclosed_from_rules(load_m0_rules(rules_dir, calendar), calendar)


@cache
def default_disclosed() -> Disclosed:
    """The disclosure of the repository's current rules (``DEFAULT_RULES_DIR``), read once."""
    return load_disclosed(DEFAULT_RULES_DIR)
