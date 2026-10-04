"""Tufte-style SVG line charts built as plain strings (F4a, ADR-0010).

Why no plotting library: a chart here is one thin line and a handful of
labels, and string building keeps the output byte-stable and dependency free.

Style rules (CLAUDE.md "Tufte-style output"):
    * no gridlines, no frame, no background box, no legend;
    * one thin dark line; the series is labelled directly at its end, with
      its last value;
    * the minimum and maximum are marked with a small dot and their value;
    * the x axis is just the first and last tick, in grey.

The data are integers (milli-units or counts). Floats appear only as SVG
display coordinates, formatted with one decimal.
"""

from collections.abc import Sequence
from typing import Final
from xml.sax.saxutils import escape

_INK: Final = "#333"
_MUTED: Final = "#888"
_FONT: Final = 'font-family="sans-serif" font-size="9"'
_LEFT, _RIGHT, _TOP, _BOTTOM = 6, 110, 12, 24


def _fmt(x: float) -> str:
    return f"{x:.1f}"


def line_chart_svg(
    ticks: Sequence[int],
    values: Sequence[int],
    label: str,
    width: int = 360,
    height: int = 96,
) -> str:
    """Return a standalone SVG document plotting ``values`` against ``ticks``."""
    if not ticks or len(ticks) != len(values):
        raise ValueError("ticks and values must be non-empty and the same length")
    plot_w, plot_h = width - _LEFT - _RIGHT, height - _TOP - _BOTTOM
    if plot_w < 1 or plot_h < 1:
        raise ValueError("chart is too small for its margins")
    t0, t1 = ticks[0], ticks[-1]
    lo, hi = min(values), max(values)

    def x(tick: int) -> float:
        return _LEFT + (plot_w * (tick - t0) / (t1 - t0) if t1 != t0 else plot_w / 2)

    def y(value: int) -> float:
        return _TOP + (plot_h * (hi - value) / (hi - lo) if hi != lo else plot_h / 2)

    points = " ".join(f"{_fmt(x(t))},{_fmt(y(v))}" for t, v in zip(ticks, values, strict=True))
    i_max, i_min = values.index(hi), values.index(lo)
    end_x, end_y = x(t1), y(values[-1])
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<polyline fill="none" stroke="{_INK}" stroke-width="1" points="{points}"/>',
        _marker(x(ticks[i_max]), y(hi), hi, dy=-3),
        _marker(x(ticks[i_min]), y(lo), lo, dy=10) if hi != lo else "",
        f'<text x="{_fmt(end_x + 4)}" y="{_fmt(end_y + 3)}" {_FONT} fill="{_INK}">'
        f"{escape(label)} {values[-1]}</text>",
        f'<text x="{_LEFT}" y="{height - 3}" {_FONT} fill="{_MUTED}">{t0}</text>',
        f'<text x="{_fmt(_LEFT + plot_w)}" y="{height - 3}" {_FONT} fill="{_MUTED}" '
        f'text-anchor="end">{t1}</text>'
        if t1 != t0
        else "",
        "</svg>",
    ]
    return "\n".join(p for p in parts if p) + "\n"


def _marker(cx: float, cy: float, value: int, dy: int) -> str:
    """A small dot with its value just above (max) or below (min)."""
    return (
        f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="1.5" fill="{_INK}"/>'
        f'<text x="{_fmt(cx)}" y="{_fmt(cy + dy)}" {_FONT} fill="{_MUTED}" '
        f'text-anchor="middle">{value}</text>'
    )
