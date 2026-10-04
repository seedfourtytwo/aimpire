"""The derived physics of a variant as report rows (ADR-0020, LAB1).

Why: a twin report must say what the overrides did to the world before it
shows what the world did. Each W0 law (``aimpire.rules.physics.LAWS``) is
listed with its multiplier in ppm of Earth, the same as a factor ("0.975"
x Earth) and as a percent change, plus the ``beyond-model`` flag when its
input lies outside the law's validated range.

Integers only, so the rows are byte-stable: the factor is rounded to the
nearest thousandth and the change to the nearest tenth of a percent, half
away from zero.
"""

from typing import Any

from aimpire.rules.physics import LAWS
from aimpire.sim.derived import DerivedWorld
from aimpire.sim.fixed import PPM


def times_earth(ppm: int) -> str:
    """``ppm`` of Earth as a factor with three decimals: 974_679 gives ``"0.975"``."""
    thousandths = (ppm + 500) // 1000
    return f"{thousandths // 1000}.{thousandths % 1000:03d}"


def change_text(ppm: int) -> str:
    """Percent change from Earth with one decimal, rounded half away from zero."""
    delta = ppm - PPM
    tenths = (abs(delta) + 500) // 1000
    sign = "+" if delta > 0 and tenths else "-" if delta < 0 and tenths else ""
    return f"{sign}{tenths // 10}.{tenths % 10} %"


def physics_rows(derived: DerivedWorld) -> list[dict[str, Any]]:
    """Each W0 law of ``derived``: ppm, x Earth, change and the beyond-model flag."""
    rows: list[dict[str, Any]] = []
    for law in LAWS:
        ppm = int(getattr(derived, law.name))
        rows.append(
            {
                "law": law.name,
                "reads": list(law.reads),
                "ppm": ppm,
                "times_earth": times_earth(ppm),
                "change": change_text(ppm),
                "beyond_model": law.name in derived.beyond_model,
            }
        )
    return rows
