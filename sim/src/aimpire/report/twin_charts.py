"""Tufte-style SVG charts for twin reports: small multiples and a paired-difference band (LAB1).

Why a module beside ``charts``: ``line_chart_svg`` draws one series; a twin
compares two per seed and summarises the difference across seeds. Same
rules as ``charts`` (CLAUDE.md "Tufte-style output"):
    * no gridlines, frame, background or legend box;
    * thin lines; the baseline thin grey, the variant in one colour;
    * direct labels at the line ends (names on the first panel only);
    * small multiples share one y scale, stated once in the title line;
    * the x axis is just the first and last tick, in grey.

Data are integers in display units (the caller converts milli-units);
floats appear only as SVG coordinates, with one decimal, so the output is
byte-stable.
"""

from collections.abc import Sequence
from typing import Final
from xml.sax.saxutils import escape

from aimpire.report.bands import Band

INK: Final = "#333"
MUTED: Final = "#888"
BASELINE_STROKE: Final = "#aaa"
VARIANT_STROKE: Final = "#2a78d6"
BAND_FILL: Final = "#cde2fb"
_FONT: Final = 'font-family="sans-serif" font-size="9"'
_PANEL_W, _PANEL_H = 180, 64
_PLOT_RIGHT: Final = 44  # px kept free right of each plot for end labels
_TITLE_H, _SEED_H, _AXIS_H = 16, 14, 12
_MAX_COLS: Final = 4
_MIN_GAP: Final = 9  # px between two end labels before they are pushed apart


def _fmt(x: float) -> str:
    return f"{x:.1f}"


def _sample(n: int, points: int = 150) -> list[int]:
    """Indices to draw: every ``step``-th point and always the last."""
    step = max(1, n // points)
    indices = list(range(0, n, step))
    return indices if indices[-1] == n - 1 else [*indices, n - 1]


class _Frame:
    """Maps ticks and values into one plot box."""

    def __init__(
        self, box: tuple[float, float, float, float], ticks: Sequence[int], lo: int, hi: int
    ):
        self.left, self.top, self.width, self.height = box
        self.t0, self.t1, self.lo, self.hi = ticks[0], ticks[-1], lo, hi

    def x(self, tick: int) -> float:
        span = self.t1 - self.t0
        return self.left + (self.width * (tick - self.t0) / span if span else self.width / 2)

    def y(self, value: int) -> float:
        span = self.hi - self.lo
        return self.top + (self.height * (self.hi - value) / span if span else self.height / 2)

    def polyline(self, ticks: Sequence[int], values: Sequence[int], stroke: str, width: str) -> str:
        pts = " ".join(
            f"{_fmt(self.x(ticks[i]))},{_fmt(self.y(values[i]))}" for i in _sample(len(ticks))
        )
        return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}" points="{pts}"/>'


def _text(x: float, y: float, text: str, fill: str = INK, anchor: str = "start") -> str:
    return (
        f'<text x="{_fmt(x)}" y="{_fmt(y)}" {_FONT} fill="{fill}" text-anchor="{anchor}">'
        f"{escape(text)}</text>"
    )


def _end_labels(y_var: float, y_base: float) -> tuple[float, float]:
    """Baselines for the two end labels, pushed apart when they would overlap."""
    if abs(y_var - y_base) >= _MIN_GAP:
        return y_var + 3, y_base + 3
    mid = (y_var + y_base) / 2
    upper, lower = mid - _MIN_GAP / 2 + 3, mid + _MIN_GAP / 2 + 3
    return (upper, lower) if y_var <= y_base else (lower, upper)


def _svg(width: int, height: int, body: list[str]) -> str:
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    return "\n".join([head, *(p for p in body if p), "</svg>"]) + "\n"


def small_multiples_svg(
    ticks: Sequence[int],
    panels: Sequence[tuple[int, Sequence[int], Sequence[int]]],
    title: str,
    variant_name: str,
) -> str:
    """One panel per ``(seed, baseline, variant)``; all panels share one y scale."""
    if not panels or not ticks:
        raise ValueError("small multiples need ticks and at least one panel")
    every = [v for _, base, var in panels for v in (*base, *var)]
    lo, hi = min(every), max(every)
    cols = min(_MAX_COLS, len(panels))
    rows = -(-len(panels) // cols)
    cell_h = _SEED_H + _PANEL_H + _AXIS_H
    width, height = cols * _PANEL_W, _TITLE_H + rows * cell_h
    body = [_text(0, 10, f"{title}; every panel {lo} to {hi}")]
    for i, (seed, base, var) in enumerate(panels):
        left, top = (i % cols) * _PANEL_W, _TITLE_H + (i // cols) * cell_h
        plot_w = _PANEL_W - _PLOT_RIGHT - 6
        frame = _Frame((left + 2, top + _SEED_H, plot_w, _PANEL_H - 4), ticks, lo, hi)
        y_var, y_base = _end_labels(frame.y(var[-1]), frame.y(base[-1]))
        end_x = frame.x(ticks[-1]) + 3
        named = i == 0
        body += [
            _text(left + 2, top + 8, f"seed {seed}", MUTED),
            frame.polyline(ticks, base, BASELINE_STROKE, "1"),
            frame.polyline(ticks, var, VARIANT_STROKE, "1.25"),
            _text(end_x, y_var, f"{variant_name} {var[-1]}" if named else str(var[-1])),
            _text(end_x, y_base, f"baseline {base[-1]}" if named else str(base[-1]), MUTED),
        ]
        if i // cols == rows - 1 or i + cols >= len(panels):
            axis_y = top + _SEED_H + _PANEL_H + 7
            body += [
                _text(frame.left, axis_y, str(ticks[0]), MUTED),
                _text(frame.left + plot_w, axis_y, str(ticks[-1]), MUTED, "end"),
            ]
    return _svg(width, height, body)


def paired_difference_svg(ticks: Sequence[int], spread: Band, title: str) -> str:
    """Variant minus baseline: the median line on a 10-90 % band, with a zero line."""
    if not ticks or len(spread.median) != len(ticks):
        raise ValueError("the band must have one value per tick")
    lo = min(0, *spread.low)
    hi = max(0, *spread.high)
    width, height = 2 * _PANEL_W, _TITLE_H + 96 + _AXIS_H
    plot_w = width - 70
    frame = _Frame((2, _TITLE_H + 4, plot_w, 88), ticks, lo, hi)
    idx = _sample(len(ticks))
    upper = [f"{_fmt(frame.x(ticks[i]))},{_fmt(frame.y(spread.high[i]))}" for i in idx]
    lower = [f"{_fmt(frame.x(ticks[i]))},{_fmt(frame.y(spread.low[i]))}" for i in reversed(idx)]
    end_x = frame.x(ticks[-1]) + 3
    median_y = frame.y(spread.median[-1]) + 3
    body = [
        _text(0, 10, f"{title}; median and 10-90 % band across seeds"),
        f'<polygon fill="{BAND_FILL}" stroke="none" points="{" ".join(upper + lower)}"/>',
        f'<line x1="{_fmt(frame.left)}" y1="{_fmt(frame.y(0))}" x2="{_fmt(frame.left + plot_w)}" '
        f'y2="{_fmt(frame.y(0))}" stroke="{MUTED}" stroke-width="0.5"/>',
        _text(frame.left, frame.y(0) - 2, "0", MUTED),
        frame.polyline(ticks, spread.median, VARIANT_STROKE, "1.25"),
        _text(end_x, median_y, f"median {spread.median[-1]:+d}"),
    ]
    for value in (spread.high[-1], spread.low[-1]):
        y = frame.y(value) + 3
        if abs(y - median_y) >= _MIN_GAP:
            body.append(_text(end_x, y, f"{value:+d}", MUTED))
    axis_y = height - 3
    body += [
        _text(frame.left, axis_y, str(ticks[0]), MUTED),
        _text(frame.left + plot_w, axis_y, str(ticks[-1]), MUTED, "end"),
    ]
    return _svg(width, height, body)
