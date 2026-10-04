"""Model providers (ADR-0005): one import point for the protocol and offline adapters.

* ``protocol`` — ``CognitionRequest``, ``CognitionResult``, ``Usage``,
  ``ModelIdentity``, the ``Provider`` protocol and ``parse_reply``;
* ``offline``  — ``MockProvider``, ``RuleProvider``, ``RecordedProvider``;
* ``recording`` — record and JSON Lines format for recorded results.

Live adapters implement the same protocol and live in their own modules, so
importing this one never loads an HTTP client: ``openai_compat``,
``anthropic_provider``, and ``live.provider_from_profile`` to build either
from a ``profiles`` TOML file. Nothing here performs network I/O.
"""

from aimpire.cognition.offline import (
    MockFailure,
    MockProvider,
    RecordedProvider,
    RulePolicy,
    RuleProvider,
)
from aimpire.cognition.protocol import (
    NO_USAGE,
    STATUSES,
    CognitionRequest,
    CognitionResult,
    ModelIdentity,
    Provider,
    Status,
    Usage,
    parse_reply,
)

__all__ = [
    "NO_USAGE",
    "STATUSES",
    "CognitionRequest",
    "CognitionResult",
    "MockFailure",
    "MockProvider",
    "ModelIdentity",
    "Provider",
    "RecordedProvider",
    "RulePolicy",
    "RuleProvider",
    "Status",
    "Usage",
    "parse_reply",
]
