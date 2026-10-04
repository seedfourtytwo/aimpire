"""Validation of ``aimpire-replay-v2`` documents, and the reader's format dispatch.

v2 is v1 (``replay_check.check_base``) plus header keys ``run``, ``places``,
``series`` and ``councils`` and frame keys ``metrics`` and ``civs`` (layout in
``aimpire.report.replay_m0``). Every value is an int, a string, a list or an
object: no floats, booleans or nulls, so the file hashes the same everywhere.
Place ids used by frames and the place grid must exist; metric rows must match
the series columns; councils come in applied order.

``validate_any`` accepts both formats, so files written before v2 stay readable.
"""

from itertools import pairwise
from typing import Any, Final, cast

from aimpire.report.replay_check import FORMAT, ReplayError, check_base, validate_replay

FORMAT_V2: Final = "aimpire-replay-v2"
FORMATS: Final = (FORMAT, FORMAT_V2)
_HEADER_V2: Final = frozenset({"run", "places", "series", "councils"})
_FRAME_V2: Final = frozenset({"metrics", "civs"})
_RUN: Final = {"run_id", "minds", "overrides", "variant_id", "tags", "council_every", "ticks"}
_CIV: Final = {"civ_id", "camp", "population", "stores_mu", "work", "trips", "names"}
_COUNCIL: Final = {
    "tick",
    "council",
    "civ_id",
    "decision_id",
    "mind",
    "status",
    "outcome",
    "journal",
    "annal",
    "policy",
    "orders",
    "messages",
    "names",
    "beliefs",
    "rejections",
    "flags",
}
_ORDER: Final = {"index", "result", "reason", "order"}


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ReplayError(message)


def _plain(value: object, where: str) -> None:
    """Only ints, strings, lists and string-keyed objects, all the way down."""
    if type(value) is int or isinstance(value, str):
        return
    if isinstance(value, list):
        for i, item in enumerate(cast(list[object], value)):
            _plain(item, f"{where}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in cast(dict[object, object], value).items():
            _require(isinstance(key, str), f"{where}: object keys must be strings")
            _plain(item, f"{where}.{key}")
        return
    raise ReplayError(f"{where}: only ints, strings, lists and objects, got {value!r}")


def _obj(value: object, keys: set[str], where: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{where} must be an object")
    data = cast(dict[str, Any], value)
    have = set(data)
    _require(have == keys, f"{where}: missing {sorted(keys - have)}, unknown {sorted(have - keys)}")
    return data


def _list(value: object, where: str) -> list[Any]:
    _require(isinstance(value, list), f"{where} must be a list")
    return cast(list[Any], value)


def _check_places(places: object, rows: int, cols: int) -> set[str]:
    data = _obj(places, {"ids", "tiles", "centroids"}, "places")
    ids = _list(data["ids"], "places.ids")
    _require(all(isinstance(i, str) for i in ids) and len(set(ids)) == len(ids), "bad place ids")
    pairs = _list(data["tiles"], "places.tiles")
    counts = pairs[1::2]
    _require(len(pairs) % 2 == 0 and all(c >= 1 for c in counts), "places.tiles: bad runs")
    _require(sum(counts) == rows * cols, "places.tiles does not fill the grid")
    _require(all(0 <= v < len(ids) for v in pairs[0::2]), "places.tiles: index out of range")
    centroids = _list(data["centroids"], "places.centroids")
    _require(len(centroids) == len(ids), "places.centroids: one per place")
    for r, c in centroids:
        _require(0 <= r < rows and 0 <= c < cols, "places.centroids: off the grid")
    return set(cast(list[str], ids))


def _check_series(series: object) -> int:
    data = _obj(series, {"columns", "every", "ticks", "values"}, "series")
    columns = _list(data["columns"], "series.columns")
    _require(all(isinstance(c, str) for c in columns), "series.columns must be strings")
    _require(data["every"] >= 1, "series.every must be >= 1")
    ticks = _list(data["ticks"], "series.ticks")
    _require(all(a < b for a, b in pairwise(ticks)), "series ticks repeat")
    values = _list(data["values"], "series.values")
    _require(len(values) == len(columns), "series.values: one list per column")
    _require(all(len(v) == len(ticks) for v in values), "series.values: one value per tick")
    return len(columns)


def _check_civs(civs: object, i: int, places: set[str]) -> None:
    for civ in _list(civs, f"frame {i}: civs"):
        data = _obj(civ, set(_CIV), f"frame {i}: civ")
        _require(data["camp"] in places, f"frame {i}: unknown camp {data['camp']!r}")
        for _, place, _ in data["work"]:
            _require(place in places, f"frame {i}: work at unknown place {place!r}")
        for _, _, place, _, _ in data["trips"]:
            _require(place in places, f"frame {i}: trip to unknown place {place!r}")


def _check_council(council: object, i: int) -> int:
    data = _obj(council, set(_COUNCIL), f"council {i}")
    for key in ("journal", "annal", "mind", "outcome", "civ_id", "decision_id"):
        _require(isinstance(data[key], str), f"council {i}: {key} must be a string")
    for order in _list(data["orders"], f"council {i}: orders"):
        o = _obj(order, set(_ORDER), f"council {i}: order")
        _require(o["result"] in ("ACCEPTED", "REJECTED"), f"council {i}: bad order result")
        accepted = o["result"] == "ACCEPTED"
        _require(isinstance(o["order"], list) == accepted, f"council {i}: bad order body")
    return cast(int, data["tick"])


def check_v2(doc: dict[str, Any]) -> dict[str, Any]:
    """Check a parsed ``aimpire-replay-v2`` document; return it unchanged."""
    _plain(doc, "replay")
    rows, cols = check_base(doc, FORMAT_V2, _HEADER_V2, _FRAME_V2)
    _obj(doc["run"], set(_RUN), "run")
    places = _check_places(doc["places"], rows, cols)
    width = _check_series(doc["series"])
    for i, frame in enumerate(doc["frames"]):
        _require(len(_list(frame["metrics"], f"frame {i}: metrics")) == width, "metrics width")
        _check_civs(frame["civs"], i, places)
    last = -1
    for i, council in enumerate(_list(doc["councils"], "councils")):
        tick = _check_council(council, i)
        _require(tick >= last, f"council {i}: councils must be in applied order")
        last = tick
    return doc


def validate_any(data: object) -> dict[str, Any]:
    """Check a replay of any readable format (v1 or v2); return it or raise ``ReplayError``."""
    _require(isinstance(data, dict), "a replay must be a JSON object")
    fmt = cast(dict[str, object], data).get("format")
    if fmt == FORMAT_V2:
        try:
            return check_v2(cast(dict[str, Any], data))
        except ReplayError:
            raise
        except (TypeError, ValueError, KeyError) as exc:  # a malformed nested item
            raise ReplayError(f"malformed {FORMAT_V2} replay: {exc!r}") from exc
    if fmt == FORMAT:
        return validate_replay(data)
    raise ReplayError(f"format must be one of {list(FORMATS)}, got {fmt!r}")
