"""Build a live provider from a profile (ADR-0005): the one entry point for live calls.

``provider_from_profile`` checks the key before it returns, so a run, a
``qualify`` or a ``batch`` refuses to start with a clear message naming the
missing variable, before any call is made. The adapters check again at call
time, because the environment can change during a long run.

Test doubles (``transport``, ``anthropic_client_factory``) are passed through
to the adapter; production code passes neither.
"""

import httpx2

from aimpire.cognition.anthropic_provider import AnthropicProvider, ClientFactory
from aimpire.cognition.openai_compat import OpenAICompatProvider
from aimpire.cognition.profiles import Profile, read_key


def provider_from_profile(
    profile: Profile,
    *,
    transport: httpx2.AsyncBaseTransport | None = None,
    anthropic_client_factory: ClientFactory | None = None,
) -> OpenAICompatProvider | AnthropicProvider:
    """The live provider for ``profile``. Raises ``MissingCredential`` if its key is unset.

    Both adapters implement ``aimpire.cognition.protocol.Provider``.
    """
    read_key(profile)  # fail before any call; the value is not kept
    if profile.kind == "anthropic":
        return AnthropicProvider(profile, client_factory=anthropic_client_factory)
    return OpenAICompatProvider(profile, transport=transport)
