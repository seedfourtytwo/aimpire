"""Is a local model server up, and does it have the model? Asked once, before a run.

Why: with Ollama not running, every council fails with ``PROVIDER_ERROR``, and
a whole run used to play out with a tribe nobody was steering. That wastes
minutes and reads like a bad model. One cheap ``GET {base_url}/models`` tells
the person what is actually wrong, in one line, before anything is played.

Only loopback (local) profiles are probed. A remote endpoint is never
contacted before the first real, budgeted call (no network in default paths).
The probe sends no key and no observation, and is never priced.
"""

from typing import Any

import httpx2

from aimpire.cognition.minds import MindError, MindSpec

PROBE_TIMEOUT_S = 5.0  # seconds: a local server answers a model list at once


class ProviderUnreachable(MindError):  # noqa: N818 (names the condition, like MissingCredential)
    """The mind's local server did not answer, or does not hold its model."""


def _model_ids(body: Any) -> list[str] | None:
    """Model ids from an OpenAI-style ``/models`` reply, or None if it has another shape."""
    data = body.get("data") if isinstance(body, dict) else None  # pyright: ignore[reportUnknownMemberType]
    if not isinstance(data, list):
        return None
    ids = [m.get("id") for m in data if isinstance(m, dict)]  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    return [i for i in ids if isinstance(i, str)]  # pyright: ignore[reportUnknownVariableType]


def check_reachable(mind: MindSpec, *, transport: httpx2.BaseTransport | None = None) -> None:
    """Raise ``ProviderUnreachable`` if ``mind`` is a local model that cannot answer now.

    Does nothing for offline minds, remote profiles and the anthropic kind.
    ``transport`` replaces the network, for tests only.
    """
    profile = mind.profile
    if profile is None or not profile.is_local or profile.kind != "openai_compat":
        return
    url = f"{profile.base_url}/models"
    try:
        with httpx2.Client(transport=transport, timeout=PROBE_TIMEOUT_S) as client:
            response = client.get(url)
    except httpx2.HTTPError as exc:
        raise ProviderUnreachable(
            f"cannot reach {profile.base_url} ({type(exc).__name__}). "
            "Is the model server running? For Ollama: install it, then `ollama serve`."
        ) from exc
    if response.status_code != httpx2.codes.OK:
        raise ProviderUnreachable(f"{url} answered HTTP {response.status_code}, not a model list")
    try:
        ids = _model_ids(response.json())
    except ValueError:
        ids = None
    if ids is not None and profile.model not in ids:
        raise ProviderUnreachable(
            f"the server is up but has no model {profile.model!r} "
            f"(it has: {', '.join(sorted(ids)) or 'none'}). "
            f"For Ollama: `ollama pull {profile.model}`."
        )
