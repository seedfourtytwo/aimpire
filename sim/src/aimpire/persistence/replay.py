"""Compare a recorded replay with the run it replays (ADR-0004).

Recorded replay must reproduce every checkpoint hash. On the first mismatch
``verify_replay`` raises ``ReplayMismatch`` naming the tick, the checkpoint
label and the state parts (``meta``, ``layer:<name>``, ``entities:<kind>``,
...) whose sub-hashes differ, so a divergence points at the subsystem that
caused it.
"""

from collections.abc import Sequence
from typing import Protocol


class ReplayMismatch(RuntimeError):  # noqa: N818 (ADR-0004's word; the acceptance tests use it)
    """A replayed run diverged from its original."""


class _Checkpointed(Protocol):
    run_id: str

    def checkpoints(self) -> list[tuple[int, str, str]]: ...

    def subsystem_hashes(self, index: int) -> dict[str, str]: ...


def _parts_differing(a: dict[str, str], b: dict[str, str]) -> list[str]:
    return sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))


def verify_replay(original: _Checkpointed, replay: _Checkpointed) -> None:
    """Raise ``ReplayMismatch`` unless every checkpoint of ``replay`` matches ``original``."""
    expected: Sequence[tuple[int, str, str]] = original.checkpoints()
    actual: Sequence[tuple[int, str, str]] = replay.checkpoints()
    for index, (want, got) in enumerate(zip(expected, actual, strict=False)):
        if want == got:
            continue
        where = f"checkpoint {index} (tick {want[0]}, {want[1]})"
        if want[:2] != got[:2]:
            raise ReplayMismatch(f"{where}: replay checkpointed tick {got[0]} ({got[1]}) instead")
        parts = _parts_differing(original.subsystem_hashes(index), replay.subsystem_hashes(index))
        raise ReplayMismatch(
            f"replay {replay.run_id!r} diverged from {original.run_id!r} at {where}; "
            f"differing parts: {', '.join(parts)}"
        )
    if len(expected) != len(actual):
        raise ReplayMismatch(
            f"replay has {len(actual)} checkpoints, the original run has {len(expected)}"
        )
