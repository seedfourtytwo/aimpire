"""Small multiples of bands: one panel per group, the same scales in every panel (Tufte).

Why: a reference ensemble or an experiment is read as "how does this mind
compare with those", so each group gets one panel, side by side, with the
same x and y scales, and the eye compares shapes without reading axes twice.

Each panel shows:
    * a pale band from the 10th to the 90th percentile over runs;
    * the lower median as one thin dark line;
    * the group's name above the panel, and the median's last value at its end.

The y scale starts at zero (counts and stores are amounts), and only the
first panel of each row labels its top value. The x axis is the first and
last tick (or the two ``x_labels``), in grey, under every panel. No
gridlines, frame or legend. Panels wrap after ``columns`` per row.

Values are integers. ``divisor`` turns milli-units into whole units for the
labels (``1000``); floats appear only as SVG coordinates, with one decimal.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final
from xml.sax.saxutils import escape

_INK: Final = "#333"
_MUTED: Final = "#888"
_BAND: Final = "#ddd"
_FONT: Final = 'font-family="sans-serif" font-size="9"'
_GAP: Final = 14  # px between panels, across and down
_LEFT, _RIGHT, _TOP, _BOTTOM = 4, 30, 16, 14


@dataclass(frozen=True, slots=True)
class Panel:
    """One group's band: equal-length series over the shared ticks."""

    label: str
    low: Sequence[int]
    median: Sequence[int]
    high: Sequence[int]


@dataclass(frozen=True, slots=True)
class _Frame:
    """The shared scales: ticks, the top value, and one panel's plot size in px."""

    t0: int
    t1: int
    top: int
    plot_w: int
    plot_h: int


def _f(x: float) -> str:
    return f"{x:.1f}"


def _panel(  # noqa: PLR0913 (one panel's place and labels)
    p: Panel,
    ticks: Sequence[int],
    frame: _Frame,
    *,
    left: int,
    top_px: int,
    labels: tuple[str, str],
    divisor: int,
    show_top: bool,
) -> list[str]:
    """The SVG elements of one panel whose top-left corner is at ``(left, top_px)``."""

    def x(tick: int) -> float:
        return left + _LEFT + frame.plot_w * (tick - frame.t0) / (frame.t1 - frame.t0)

    def y(value: int) -> float:
        return top_px + _TOP + frame.plot_h * (frame.top - value) / frame.top

    upper = [f"{_f(x(t))},{_f(y(v))}" for t, v in zip(ticks, p.high, strict=True)]
    lower = [f"{_f(x(t))},{_f(y(v))}" for t, v in zip(ticks, p.low, strict=True)]
    line = " ".join(f"{_f(x(t))},{_f(y(v))}" for t, v in zip(ticks, p.median, strict=True))
    end = p.median[-1]
    bottom = top_px + _TOP + frame.plot_h + _BOTTOM - 2
    parts = [
        f'<text x="{left + _LEFT}" y="{top_px + 9}" {_FONT} fill="{_INK}">{escape(p.label)}</text>',
        f'<polygon fill="{_BAND}" stroke="none" points="{" ".join(upper + lower[::-1])}"/>',
        f'<polyline fill="none" stroke="{_INK}" stroke-width="1" points="{line}"/>',
        f'<text x="{_f(x(frame.t1) + 3)}" y="{_f(y(end) + 3)}" {_FONT} fill="{_INK}">'
        f"{end // divisor}</text>",
        f'<text x="{left + _LEFT}" y="{bottom}" {_FONT} fill="{_MUTED}">{escape(labels[0])}</text>',
        f'<text x="{_f(x(frame.t1))}" y="{bottom}" {_FONT} fill="{_MUTED}" '
        f'text-anchor="end">{escape(labels[1])}</text>',
    ]
    if show_top:
        parts.append(
            f'<text x="{_f(x(frame.t0) + 2)}" y="{_f(y(frame.top) + 8)}" {_FONT} '
            f'fill="{_MUTED}">{frame.top // divisor}</text>'
        )
    return parts


def band_panels_svg(  # noqa: PLR0913 (layout settings, all keyword-only)
    ticks: Sequence[int],
    panels: Sequence[Panel],
    *,
    divisor: int = 1,
    panel_width: int = 150,
    panel_height: int = 90,
    columns: int = 4,
    x_labels: tuple[str, str] | None = None,
) -> str:
    """A standalone SVG with one band panel per group, sharing both scales."""
    if len(ticks) < 2 or not panels or columns < 1:
        raise ValueError("need at least two ticks, one panel and one column")
    for p in panels:
        if not len(p.low) == len(p.median) == len(p.high) == len(ticks):
            raise ValueError(f"panel {p.label!r}: series and ticks differ in length")
    frame = _Frame(
        t0=ticks[0],
        t1=ticks[-1],
        top=max(1, *(v for p in panels for v in p.high)),
        plot_w=panel_width - _LEFT - _RIGHT,
        plot_h=panel_height - _TOP - _BOTTOM,
    )
    labels = x_labels or (str(frame.t0), str(frame.t1))
    across = min(columns, len(panels))
    rows = -(-len(panels) // across)
    width = across * panel_width + (across - 1) * _GAP
    height = rows * panel_height + (rows - 1) * _GAP
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    ]
    for index, p in enumerate(panels):
        row, col = divmod(index, across)
        left, top_px = col * (panel_width + _GAP), row * (panel_height + _GAP)
        parts += _panel(
            p,
            ticks,
            frame,
            left=left,
            top_px=top_px,
            labels=labels,
            divisor=divisor,
            show_top=col == 0,
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
