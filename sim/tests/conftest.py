"""Suite-wide guard: no test may open a real network connection (CLAUDE.md, ADR-0005).

Live adapters are tested with ``httpx2.MockTransport`` and fake SDK clients.
If any code path reaches a real socket anyway (a missing transport, a test
that forgot its double), ``connect`` raises ``NetworkBlocked`` at once
instead of reaching a provider, spending money or hanging on a timeout.

Only ``AF_INET`` and ``AF_INET6`` connections are blocked. Unix sockets and
the socket pairs an asyncio event loop makes for itself are left alone.
"""

import socket
from collections.abc import Iterator
from typing import Any

import pytest

_BLOCKED_FAMILIES = (socket.AF_INET, socket.AF_INET6)


class NetworkBlocked(RuntimeError):  # noqa: N818 (names what happened, as the error message does)
    """A test tried to open a real network connection."""


def _guarded(original: Any) -> Any:
    def connect(self: socket.socket, address: Any) -> Any:
        if self.family in _BLOCKED_FAMILIES:
            raise NetworkBlocked(f"tests may not open network connections (to {address!r})")
        return original(self, address)

    return connect


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(socket.socket, "connect", _guarded(socket.socket.connect))
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded(socket.socket.connect_ex))
    yield
