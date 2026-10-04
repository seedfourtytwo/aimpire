"""Validation of ``aimpire-replay-v1`` documents (F4b).

Why separate: the player trusts what it loads, so every file is checked
before use, both when written and when read. Unknown keys, floats, booleans in
place of ints, frames that go back in time, layer data that does not fill the
grid, and dots of unknown kinds or off the grid are all errors. Kept apart from
``replay.py`` so each module stays small.
"""

from typing import Any, Final, cast

FORMAT: Final = "aimpire-replay-v1"
_HEADER: Final = {
    "format",
    "run_seed",
    "rules_version",
    "rules_hash",
    "calendar",
    "layers",
    "layer",
    "grid",
    "scale_max",
    "kinds",
    "palette",
    "frames",
}
_FRAME: Final = {"tick", "hash", "layer", "dots"}
_HEX: Final = frozenset("0123456789abcdef")


class ReplayError(ValueError):
    """A replay file is missing, unreadable or not a valid ``aimpire-replay-v1`` document."""


def _is_int(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ReplayError(message)


def _int_list(value: object, length: int | None = None) -> list[int]:
    _require(isinstance(value, list), f"expected a list, got {value!r}")
    items = cast(list[object], value)
    _require(all(type(v) is int for v in items), f"expected ints only in {items!r}")
    _require(length is None or len(items) == length, f"expected {length} ints in {items!r}")
    return cast(list[int], items)


def _rgb(value: object) -> None:
    _require(all(0 <= c <= 255 for c in _int_list(value, 3)), f"bad colour {value!r}")


def _check_keys(data: dict[str, object], expected: set[str], where: str) -> None:
    keys = set(data)
    _require(
        keys == expected,
        f"{where}: missing {sorted(expected - keys)}, unknown {sorted(keys - expected)}",
    )


def _check_header(data: dict[str, object]) -> tuple[int, int, list[str]]:
    _require(data.get("format") == FORMAT, f"format must be {FORMAT!r}")
    _check_keys(data, set(_HEADER), "replay")
    _require(_is_int(data["run_seed"]), "run_seed must be a non-negative int")
    for key in ("rules_version", "rules_hash", "layer"):
        _require(isinstance(data[key], str), f"{key} must be a string")
    calendar = data["calendar"]
    _require(isinstance(calendar, dict), "calendar must be an object")
    cal = cast(dict[str, object], calendar)
    _check_keys(cal, {"ticks_per_season", "seasons_per_year"}, "calendar")
    _require(all(_is_int(v, 1) for v in cal.values()), "calendar lengths must be positive ints")
    layers = data["layers"]
    _require(isinstance(layers, list), "layers must be a list")
    names = cast(list[object], layers)
    _require(all(isinstance(n, str) for n in names), "layer names must be strings")
    _require(data["layer"] in names, "the chosen layer must be one of layers")
    rows, cols = _int_list(data["grid"], 2)
    _require(rows >= 1 and cols >= 1, "grid must be at least 1x1")
    _require(_is_int(data["scale_max"], 1), "scale_max must be an int >= 1")
    kinds_value = data["kinds"]
    _require(isinstance(kinds_value, list), "kinds must be a list")
    kinds = cast(list[object], kinds_value)
    _require(all(isinstance(k, str) for k in kinds), "kinds must be strings")
    _require(len(set(cast(list[str], kinds))) == len(kinds), "kinds must not repeat")
    palette = data["palette"]
    _require(isinstance(palette, dict), "palette must be an object")
    pal = cast(dict[str, object], palette)
    _check_keys(pal, {"ramp_low", "ramp_high", "kinds"}, "palette")
    _rgb(pal["ramp_low"])
    _rgb(pal["ramp_high"])
    kind_colours = pal["kinds"]
    _require(
        isinstance(kind_colours, list) and len(cast(list[object], kind_colours)) == len(kinds),
        "palette.kinds needs one colour per kind",
    )
    for colour in cast(list[object], kind_colours):
        _rgb(colour)
    return rows, cols, cast(list[str], kinds)


def _check_frame(frame: object, i: int, rows: int, cols: int, kinds: list[str]) -> int:
    _require(isinstance(frame, dict), f"frame {i} must be an object")
    f = cast(dict[str, object], frame)
    _check_keys(f, set(_FRAME), f"frame {i}")
    _require(_is_int(f["tick"]), f"frame {i}: tick must be a non-negative int")
    digest = f["hash"]
    _require(
        isinstance(digest, str) and len(digest) == 64 and set(digest) <= _HEX,
        f"frame {i}: hash must be 64 lowercase hex characters",
    )
    pairs = _int_list(f["layer"])
    counts = pairs[1::2]
    _require(len(pairs) % 2 == 0 and all(c >= 1 for c in counts), f"frame {i}: bad layer runs")
    _require(sum(counts) == rows * cols, f"frame {i}: layer does not fill the {rows}x{cols} grid")
    dots = f["dots"]
    _require(isinstance(dots, list), f"frame {i}: dots must be a list")
    last_id = 0
    for dot in cast(list[object], dots):
        _require(isinstance(dot, list) and len(cast(list[object], dot)) == 4, f"frame {i}: bad dot")
        eid, kind, row, col = cast(list[object], dot)
        _require(_is_int(eid, last_id + 1), f"frame {i}: dot ids must be ascending ints")
        _require(kind in kinds, f"frame {i}: dot kind {kind!r} is not in kinds")
        _require(_is_int(row) and _is_int(col), f"frame {i}: dot position must be ints")
        _require(cast(int, row) < rows and cast(int, col) < cols, f"frame {i}: dot off the grid")
        last_id = cast(int, eid)
    return cast(int, f["tick"])


def validate_replay(data: object) -> dict[str, Any]:
    """Check a parsed replay document; return it unchanged or raise ``ReplayError``."""
    _require(isinstance(data, dict), "a replay must be a JSON object")
    doc = cast(dict[str, object], data)
    rows, cols, kinds = _check_header(doc)
    frames = doc["frames"]
    _require(isinstance(frames, list) and len(cast(list[object], frames)) > 0, "no frames")
    last_tick = -1
    for i, frame in enumerate(cast(list[object], frames)):
        tick = _check_frame(frame, i, rows, cols, kinds)
        _require(tick > last_tick, f"frame {i}: ticks must strictly increase")
        last_tick = tick
    return cast(dict[str, Any], doc)
