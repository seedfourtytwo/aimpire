"""One-file JSON replay export, format ``aimpire-replay-v1`` (F4b, ADR-0004, ADR-0010).

``ReplayRecorder`` writes v1, the generic format any world can produce. M0 runs
write ``aimpire-replay-v2`` (``aimpire.report.replay_m0``), which adds metrics,
places and councils to the same frames. ``load_replay`` reads both.

Why: the creator watches runs in a static Canvas2D page (``client/replay/``),
on any device, with no server. So a replay is a single JSON file that holds
everything the player draws: one tile layer and the entity dots per captured
tick, plus the state hash of that tick so a replay can be checked against a
re-run. It is a viewing format, not the replay source of truth (that is the
inputs log, ADR-0004).

Layout (only ints, strings, lists and objects; never floats)::

    {"format": "aimpire-replay-v1", "run_seed": 11, "rules_version": "v1",
     "rules_hash": "...", "calendar": {"ticks_per_season": .., "seasons_per_year": ..},
     "layers": [all layer names, sorted], "layer": "food", "grid": [rows, cols],
     "scale_max": 1000, "kinds": ["person", ...],
     "palette": {"ramp_low": [r,g,b], "ramp_high": [r,g,b], "kinds": [[r,g,b], ...]},
     "frames": [{"tick": 0, "hash": "<hex>", "layer": [value, count, ...],
                 "dots": [[id, kind, row, col], ...]}, ...]}

``layer`` is run-length encoded in row-major order as ``value, count`` pairs:
food layers are mostly flat, so this keeps fixtures small. Dots are in
ascending id order. The file is written with sorted keys and no spaces, so
identical runs give identical bytes.
"""

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from aimpire.report.frames import PALETTE, RAMP_HIGH, RAMP_LOW, default_scale, entity_pos
from aimpire.report.replay_check import FORMAT, ReplayError, validate_replay
from aimpire.report.replay_v2_check import validate_any
from aimpire.sim.calendar import Calendar
from aimpire.sim.hashing import state_hash
from aimpire.sim.state import Entity, WorldState

Locate = Callable[[WorldState, Entity], tuple[int, int] | None]
"""Where an entity is drawn, ``(row, col)``, or ``None`` to leave it out."""

__all__ = [
    "FORMAT",
    "Locate",
    "ReplayError",
    "ReplayRecorder",
    "decode_layer",
    "load_replay",
    "rle_decode",
    "rle_encode",
    "write_replay",
    "write_replay_doc",
]

Replay = dict[str, Any]


def rle_encode(values: Sequence[int]) -> list[int]:
    """Run-length encode ints as a flat ``[value, count, value, count, ...]`` list."""
    out: list[int] = []
    for v in values:
        if out and out[-2] == v:
            out[-1] += 1
        else:
            out += [int(v), 1]
    return out


def rle_decode(pairs: Sequence[int]) -> list[int]:
    """Inverse of ``rle_encode``."""
    if len(pairs) % 2:
        raise ReplayError("run-length data must be value, count pairs")
    out: list[int] = []
    for i in range(0, len(pairs), 2):
        out += [pairs[i]] * pairs[i + 1]
    return out


def _own_pos(_state: WorldState, entity: Entity) -> tuple[int, int] | None:
    return entity_pos(entity)


class ReplayRecorder:
    """Collects frames during a run. Call ``capture(state)`` at tick 0 and after each step.

    ``locate`` places a dot for an entity; by default its own ``"pos"`` field.
    A world whose entities have no tile position (the M0 tribe lives at a
    place) passes its own, such as the camp's centroid.
    """

    def __init__(
        self,
        layer: str,
        kinds: Sequence[str],
        calendar: Calendar,
        scale_max: int | None = None,
        locate: Locate = _own_pos,
    ) -> None:
        if len(kinds) > len(PALETTE) or len(set(kinds)) != len(kinds):
            raise ValueError(f"kinds must be distinct and at most {len(PALETTE)}")
        self.layer = layer
        self.kinds = tuple(kinds)
        self.calendar = calendar
        self.scale_max = scale_max
        self.locate = locate
        self.header: Replay | None = None
        self.frames: list[Replay] = []

    def _start(self, state: WorldState) -> Replay:
        grid = state.layers[self.layer]
        scale = default_scale(grid) if self.scale_max is None else self.scale_max
        return {
            "format": FORMAT,
            "run_seed": state.run_seed,
            "rules_version": state.rules_version,
            "rules_hash": state.rules_hash,
            "calendar": {
                "ticks_per_season": self.calendar.ticks_per_season,
                "seasons_per_year": self.calendar.seasons_per_year,
            },
            "layers": sorted(state.layers),
            "layer": self.layer,
            "grid": [int(grid.shape[0]), int(grid.shape[1])],
            "scale_max": scale,
            "kinds": list(self.kinds),
            "palette": {
                "ramp_low": list(RAMP_LOW),
                "ramp_high": list(RAMP_HIGH),
                "kinds": [list(PALETTE[i]) for i in range(len(self.kinds))],
            },
        }

    def capture(self, state: WorldState) -> Replay:
        """Append the frame for ``state``'s current tick and return it."""
        if self.header is None:
            self.header = self._start(state)
        elif state.run_seed != self.header["run_seed"]:
            raise ValueError("all frames of a replay must come from one run")
        if self.frames and state.tick <= self.frames[-1]["tick"]:
            raise ValueError(f"tick {state.tick} is not after the last captured tick")
        grid = state.layers[self.layer]
        if [int(n) for n in grid.shape] != self.header["grid"]:
            raise ValueError("the layer changed shape during the run")
        frame: Replay = {
            "tick": state.tick,
            "hash": state_hash(state),
            "layer": rle_encode([int(v) for v in grid.ravel().tolist()]),
            "dots": self._dots(state),
        }
        self.frames.append(frame)
        return frame

    def _dots(self, state: WorldState) -> list[list[int | str]]:
        """``[id, kind, row, col]`` in id order; same selection rules as ``frame_array``."""
        rows, cols = state.layers[self.layer].shape
        dots: list[list[int | str]] = []
        for eid in sorted(state.entities):
            entity = state.entities[eid]
            kind = entity.get("kind")
            if not isinstance(kind, str) or kind not in self.kinds:
                continue
            pos = self.locate(state, entity)
            if pos is None:
                continue
            if 0 <= pos[0] < rows and 0 <= pos[1] < cols:
                dots.append([eid, kind, pos[0], pos[1]])
        return dots

    def to_dict(self) -> Replay:
        """The whole replay as a JSON-ready dict."""
        if self.header is None:
            raise ValueError("nothing captured yet")
        return {**self.header, "frames": self.frames}


def dumps(replay: Replay) -> str:
    """Canonical JSON text: sorted keys, no spaces, ASCII, trailing newline."""
    return json.dumps(replay, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def write_replay(recorder: ReplayRecorder, path: Path) -> None:
    """Validate and write the recorder's replay to ``path``."""
    replay = recorder.to_dict()
    validate_replay(replay)
    Path(path).write_bytes(dumps(replay).encode("ascii"))


def write_replay_doc(replay: Replay, path: Path) -> None:
    """Validate a replay document of any readable format and write it to ``path``."""
    validate_any(replay)
    Path(path).write_bytes(dumps(replay).encode("ascii"))


def _no_floats(text: str) -> float:
    raise ReplayError(f"replays hold no floats, found {text}")


def load_replay(path: Path) -> Replay:
    """Read a v1 or v2 replay file, reject floats, validate the header and every frame."""
    try:
        data: object = json.loads(Path(path).read_text(encoding="utf-8"), parse_float=_no_floats)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"cannot read replay {path}: {exc}") from exc
    return validate_any(data)


def decode_layer(replay: Replay, index: int) -> list[list[int]]:
    """The chosen layer of frame ``index`` as a list of rows."""
    rows, cols = replay["grid"]
    flat = rle_decode(replay["frames"][index]["layer"])
    return [flat[r * cols : (r + 1) * cols] for r in range(rows)]
