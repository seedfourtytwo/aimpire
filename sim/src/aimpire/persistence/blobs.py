"""Content-addressed blob store with credential redaction (ADR-0004, CLAUDE.md "credentials").

Blobs hold what is too large or too raw for a table row: model requests and
responses, and full-state checkpoints. Each is canonical JSON (sorted keys,
ASCII), compressed with zstd from the standard library (``compression.zstd``,
Python 3.14), and stored at ``blobs/<sha256>.json.zst``, the digest being of
the uncompressed bytes. Identical content is stored once.

Why redaction lives here: every byte that reaches a run directory passes
through ``redact`` first, the manifest's config included. Credentials must
never be in saves, run databases, blobs or exports, even when a prompt or a
config was written carelessly. Redacted are:

* the value of any environment variable whose name ends in ``API_KEY``,
  ``TOKEN``, ``SECRET`` or ``PASSWORD`` (8 characters or longer);
* anything shaped like a provider key (``sk-...``), a bearer token, or
  credentials in a URL (``scheme://user:pass@``).

A recorded reply that itself contained such a string is stored redacted, so
replaying that one decision would differ and the replay check would say so.
That trade is deliberate: a leaked key is worse than a loud mismatch.
"""

import hashlib
import json
import os
import re
from compression import zstd
from pathlib import Path
from typing import Any, Final

REDACTED: Final = "[REDACTED]"
_SECRET_NAME: Final = re.compile(r"(API_KEY|TOKEN|SECRET|PASSWORD)$")
_MIN_SECRET_LEN: Final = 8
# Character classes exclude quotes and backslashes so redaction never breaks JSON text.
_SHAPES: Final = (
    re.compile(r"sk-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=\-]+"),
    re.compile(r"(://)[^/\s:@\"\\]+:[^/\s@\"\\]+@"),
)


def redact(text: str) -> str:
    """Return ``text`` with credential values and credential-shaped strings replaced."""
    secrets = sorted(
        (
            value
            for name, value in os.environ.items()
            if _SECRET_NAME.search(name.upper()) and len(value) >= _MIN_SECRET_LEN
        ),
        key=len,
        reverse=True,  # longest first, so a key containing another is fully removed
    )
    for value in secrets:
        text = text.replace(value, REDACTED)
        escaped = json.dumps(value, ensure_ascii=True)[1:-1]
        if escaped != value:
            text = text.replace(escaped, REDACTED)
    for pattern in _SHAPES:
        text = pattern.sub(lambda m: (m.group(1) if m.lastindex else "") + REDACTED, text)
    return text


def canonical_json(value: Any) -> str:
    """Sorted keys, no whitespace, ASCII only, then redacted."""
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return redact(text)


class BlobStore:
    """Write-once JSON blobs under one run directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"not a blob digest: {digest!r}")
        return self.root / f"{digest}.json.zst"

    def put(self, value: Any) -> str:
        """Store ``value`` (redacted) and return its sha256 hex digest."""
        data = canonical_json(value).encode("ascii")
        digest = hashlib.sha256(data).hexdigest()
        path = self._path(digest)
        if not path.exists():
            partial = path.with_suffix(".partial")
            partial.write_bytes(zstd.compress(data))
            partial.replace(path)  # atomic: a reader never sees half a blob
        return digest

    def get(self, digest: str) -> Any:
        """Load a blob and check that its content still matches its name."""
        data = zstd.decompress(self._path(digest).read_bytes())
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"blob {digest} is corrupt")
        return json.loads(data)
