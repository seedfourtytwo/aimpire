"""The local-model reachability check (no socket is opened: every call uses a MockTransport)."""

from pathlib import Path

import httpx2
import pytest

from aimpire.cognition.minds import resolve_mind
from aimpire.cognition.reachability import ProviderUnreachable, check_reachable

REPO = Path(__file__).resolve().parents[3]
OLLAMA = REPO / "profiles" / "ollama-example.toml"


def _transport(handler):  # type: ignore[no-untyped-def]
    return httpx2.MockTransport(handler)


def test_offline_minds_are_never_probed() -> None:
    def boom(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("no request expected")

    for name in ("mock", "rule:half_full"):
        check_reachable(resolve_mind(name, REPO), transport=_transport(boom))


def test_up_server_with_the_model_passes() -> None:
    seen: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(str(request.url))
        return httpx2.Response(200, json={"data": [{"id": "qwen3:8b"}]})

    check_reachable(resolve_mind(str(OLLAMA), REPO), transport=_transport(handler))
    assert seen == ["http://localhost:11434/v1/models"]


def test_dead_server_says_so() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused")

    with pytest.raises(ProviderUnreachable, match="ollama serve"):
        check_reachable(resolve_mind(str(OLLAMA), REPO), transport=_transport(handler))


def test_missing_model_says_how_to_pull_it() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"data": [{"id": "llama3:8b"}]})

    with pytest.raises(ProviderUnreachable, match="ollama pull qwen3:8b"):
        check_reachable(resolve_mind(str(OLLAMA), REPO), transport=_transport(handler))


def test_http_error_status_is_reported() -> None:
    with pytest.raises(ProviderUnreachable, match="HTTP 500"):
        check_reachable(
            resolve_mind(str(OLLAMA), REPO),
            transport=_transport(lambda r: httpx2.Response(500)),
        )


def test_remote_profiles_are_not_contacted() -> None:
    haiku = REPO / "profiles" / "anthropic-haiku-4-5.toml"

    def boom(request: httpx2.Request) -> httpx2.Response:
        raise AssertionError("a remote endpoint must not be probed")

    check_reachable(resolve_mind(str(haiku), REPO), transport=_transport(boom))
