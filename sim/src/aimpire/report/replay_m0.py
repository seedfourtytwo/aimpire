"""The playable replay, format ``aimpire-replay-v2``: v1 plus what a person needs to follow a run.

Why: a v1 replay shows the food map and one camp dot. To *play with* an M0
run the creator also needs the numbers over time, where the people were sent,
and what each council decided, in the mind's own words. Everything added here
comes from the run's own records:

* **frames** (captured during the run, from the state; observer layer, ADR-0019
  section 3): ``metrics``, the run's metric row at that tick (same columns as
  ``series``), and ``civs``, one object per civilization::

      {"civ_id": "C1", "camp": "PL06", "population": 30, "stores_mu": 900000,
       "work": [[activity, place, workers]],         # today's split by the policy
       "trips": [[task_id, kind, place, qty, status]],  # tasks made from orders
       "names": [[place, name]]}                     # the civilization's own names

* **places** (static in M0): ``ids``, ``tiles`` (each tile's index into
  ``ids``, run-length encoded row-major like a layer) and ``centroids``.
* **series**: the per-tick metrics (``metrics.csv``) column by column. A run
  longer than ``MAX_SERIES_POINTS`` ticks is decimated: ``every`` is the
  smallest step that fits, and the series keeps tick 0, every ``every``-th
  tick and the last tick. A five-year game (600 ticks) is not decimated.
* **councils** (from the run store's decision rows only, never from state):
  one object per decision in applied order, with the mind's ``journal`` and
  ``annal`` verbatim, the policy in force after it, its orders with their
  result (``ACCEPTED``, or ``REJECTED`` and the validator's reason), its
  messages, names, beliefs, every rejection and flag. An accepted order is the
  validated ``[kind, place, target, qty, text]``; a rejected one is the item as
  the mind wrote it, re-serialised as canonical JSON text from the recorded
  reply (it may hold values the contract refused, so it stays text).
* **run**: run id, minds by seat, Lab overrides as ``key=value`` text, tags.

Nothing is summarised, paraphrased or invented. Latency, tokens and spend are
left out: they differ between identical runs, and a replay is byte-identical
for identical runs.
"""

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final, cast

from aimpire.cognition.protocol import parse_reply
from aimpire.report.metrics import MetricsRecorder
from aimpire.report.replay import Locate, Replay, ReplayRecorder, rle_encode
from aimpire.report.replay_v2_check import FORMAT_V2
from aimpire.sim.calendar import Calendar
from aimpire.sim.places import places_by_id
from aimpire.sim.state import Entity, Value, WorldState
from aimpire.sim.systems.tribe import camp, civ_entity_ids, civ_id, population, stores_food
from aimpire.sim.systems.work import tasks, work_lines

MAX_SERIES_POINTS: Final = 2000
"""Per-tick series longer than this are decimated (module docstring)."""

BlobGet = Callable[[str], Any]
"""Reads a stored blob by digest (``RunStore.blobs.get``)."""


def civ_frames(state: WorldState) -> list[dict[str, Value]]:
    """The ``civs`` entry of a frame: each civilization's camp, people, work and trips."""
    return [_civ_frame(state.entities[eid]) for eid in civ_entity_ids(state)]


def _civ_frame(entity: Entity) -> dict[str, Value]:
    names = entity.get("names", {})
    assert isinstance(names, dict)
    return {
        "civ_id": civ_id(entity),
        "camp": camp(entity),
        "population": population(entity),
        "stores_mu": stores_food(entity),
        "work": [[a, p, n] for a, p, n in work_lines(entity)],
        "trips": [[t.task_id, t.kind, t.place, t.qty, t.status] for t in tasks(entity)],
        "names": [[pid, cast(str, names[pid])] for pid in sorted(names)],
    }


def places_section(state: WorldState) -> dict[str, Any]:
    """Place ids, each tile's place as an index into ``ids`` (RLE) and the centroids."""
    places = places_by_id(state)
    ids = list(places)
    rows, cols = next(iter(state.layers.values())).shape
    owner = [0] * (int(rows) * int(cols))
    for index, place in enumerate(places.values()):
        for row, col in place.tiles:
            owner[row * int(cols) + col] = index
    return {
        "ids": ids,
        "tiles": rle_encode(owner),
        "centroids": [list(p.centroid) for p in places.values()],
    }


def series_section(metrics: MetricsRecorder, max_points: int = MAX_SERIES_POINTS) -> dict[str, Any]:
    """The metric table column by column, decimated when longer than ``max_points``."""
    rows = metrics.rows
    every = max(1, -(-len(rows) // max_points))
    keep = [i for i in range(len(rows)) if i % every == 0 or i == len(rows) - 1]
    return {
        "columns": list(metrics.names),
        "every": every,
        "ticks": [rows[i][0] for i in keep],
        "values": [[rows[i][c] for i in keep] for c in range(1, len(metrics.columns))],
    }


def metrics_at(metrics: MetricsRecorder, tick: int) -> list[int]:
    """The metric row recorded at ``tick`` (without the tick)."""
    for row in reversed(metrics.rows):
        if row[0] == tick:
            return list(row[1:])
    raise ValueError(f"no metrics were recorded at tick {tick}")


def _as_written(reply: dict[str, Any] | None, index: int) -> str:
    """Order ``index`` of the recorded reply as canonical JSON text, or ``""`` if absent."""
    orders = reply.get("orders") if reply is not None else None
    if not isinstance(orders, list) or not 0 <= index < len(cast(list[Any], orders)):
        return ""
    item = cast(list[Any], orders)[index]
    return json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _orders(record: Mapping[str, Any], reply: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Accepted orders from the record and rejected ones from its rejections, by index."""
    out = [
        {"index": i, "result": "ACCEPTED", "reason": "", "order": [k, p, t, q, x]}
        for i, k, p, t, q, x in record["orders"]
    ]
    for field, reason in record["rejections"]:
        if field.startswith("orders[") and field.endswith("]"):
            index = int(field[len("orders[") : -1])
            out.append(
                {
                    "index": index,
                    "result": "REJECTED",
                    "reason": reason,
                    "order": _as_written(reply, index),
                }
            )
    return sorted(out, key=lambda o: o["index"])


def council_entry(row: Mapping[str, Any], get_blob: BlobGet) -> dict[str, Any]:
    """One decision row of the run store as a replay council (module docstring)."""
    record = row["record"]
    reply = None
    if row["response_blob"]:
        reply = parse_reply(get_blob(row["response_blob"])["raw_text"])[0]
    return {
        "tick": row["tick"],
        "council": row["council"],
        "civ_id": row["civ_id"],
        "decision_id": row["decision_id"],
        "mind": row["model_reported"] or f"{row['provider']}:{row['model']}",
        "status": row["status"],
        "outcome": row["outcome"],
        "journal": record["journal"],
        "annal": record["annal"],
        "policy": record["policy"],
        "orders": _orders(record, reply),
        "messages": record["messages"],
        "names": record["names"],
        "beliefs": record["beliefs"],
        "rejections": record["rejections"],
        "flags": record["flags"],
    }


def councils_section(decisions: Sequence[Mapping[str, Any]], get_blob: BlobGet) -> list[Any]:
    """Every decision row (``RunStore.decisions()``, applied order) as a council entry."""
    return [council_entry(row, get_blob) for row in decisions]


def _override_text(key: str, value: object) -> str:
    shown = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return f"{key}={shown}"


def run_section(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Who played and under which world: from the run store's manifest."""
    config = manifest["config"]
    variant = config.get("variant", {})
    overrides = variant.get("overrides", {})
    return {
        "run_id": manifest["run_id"],
        "minds": [[seat, label] for seat, label in sorted(config.get("seats", {}).items())],
        "overrides": [_override_text(k, overrides[k]) for k in sorted(overrides)],
        "variant_id": variant.get("id", ""),
        "tags": list(config.get("tags", [])),
        "council_every": config.get("council_every", 0),
        "ticks": config.get("ticks", 0),
    }


class M0ReplayRecorder:
    """A v1 recorder plus each frame's ``civs``; ``to_dict`` adds the run-level sections."""

    def __init__(
        self, layer: str, kinds: Sequence[str], calendar: Calendar, locate: Locate
    ) -> None:
        self.base = ReplayRecorder(layer, kinds, calendar, locate=locate)
        self.civs: list[list[dict[str, Value]]] = []
        self.places: dict[str, Any] | None = None

    @property
    def last_tick(self) -> int:
        """The tick of the last captured frame (-1 before the first)."""
        return self.base.frames[-1]["tick"] if self.base.frames else -1

    def capture(self, state: WorldState) -> None:
        """Capture the frame of ``state``'s tick (after the metrics of that tick)."""
        if self.places is None:
            self.places = places_section(state)
        self.base.capture(state)
        self.civs.append(civ_frames(state))

    def to_dict(
        self,
        metrics: MetricsRecorder,
        councils: list[Any],
        run: dict[str, Any],
    ) -> Replay:
        """The whole v2 replay; ``metrics`` must hold a row for every captured tick."""
        base = self.base.to_dict()
        frames = [
            {**frame, "metrics": metrics_at(metrics, frame["tick"]), "civs": civs}
            for frame, civs in zip(base["frames"], self.civs, strict=True)
        ]
        return {
            **base,
            "format": FORMAT_V2,
            "frames": frames,
            "places": self.places,
            "series": series_section(metrics),
            "councils": councils,
            "run": run,
        }
