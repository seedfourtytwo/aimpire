"""The per-council progress line of ``aimpire run`` for live minds."""

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

from aimpire.experiments.progress import ProgressSink


class _Store:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def record_council(self, tick: int, council: int, settled: Sequence[Any]) -> None:
        self.calls.append(("council", (tick, council, len(settled))))

    def checkpoint(self, state: Any, label: str) -> None:
        self.calls.append(("checkpoint", label))


def _settled(outcome: str) -> Any:
    return SimpleNamespace(record=SimpleNamespace(outcome=outcome))


def test_forwards_and_echoes_one_line_per_council() -> None:
    store, lines = _Store(), []
    sink = ProgressSink(store, councils=12, echo=lines.append)  # type: ignore[arg-type]
    sink.record_council(20, 3, [_settled("VALID")])
    sink.checkpoint(None, "barrier")  # type: ignore[arg-type]
    assert store.calls == [("council", (20, 3, 1)), ("checkpoint", "barrier")]
    assert len(lines) == 1
    assert lines[0].startswith("council 3/12, day 20: VALID (")
