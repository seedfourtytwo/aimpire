"""The rules hash: one digest for everything that makes two worlds the same (ADR-0007, ADR-0020).

What it covers:
    * the exact bytes of every ``*.yaml`` file in the rules version directory,
      in file-name order (so ``calendar.yaml`` and ``world.yaml``, and any rules
      file added later, without a list to keep up to date);
    * the Lab's rules-layer overrides (``world``, ``rules`` and ``tribe`` knobs),
      as canonical JSON, when there are any.

Why bytes and not parsed values: a hash that ignores a byte would let two
different files claim to be the same rules. Editing a comment therefore
changes the hash too, which is the safe direction.

Why no overrides means no suffix: a run without ``--set`` keeps the plain
file hash, so baseline runs before and after the Lab existed compare equal.
Mind and god overrides never reach this function; they belong in the run
manifest only.
"""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from aimpire.rules.errors import RulesError

FORMAT: Final = b"aimpire-rules-hash-v1"
"""Domain tag. Changing the byte layout below means changing this tag."""


def _field(data: bytes) -> bytes:
    """Length-prefix ``data`` so no two field sequences share bytes."""
    return len(data).to_bytes(8, "little") + data


def rules_hash(rules_dir: Path, overrides: Mapping[str, int | str] | None = None) -> str:
    """Return the BLAKE2b-256 hex digest of the rules files plus rules-layer overrides.

    ``overrides`` maps knob paths (``"world.gravity"``) to canonical values; the
    caller (``aimpire.lab``) has already checked them against the registry.
    """
    rules_dir = Path(rules_dir)
    files = sorted(rules_dir.glob("*.yaml"), key=lambda p: p.name)
    if not files:
        raise RulesError(f"no rules files in {rules_dir}")
    digest = hashlib.blake2b(digest_size=32)
    digest.update(_field(FORMAT))
    for path in files:
        try:
            body = path.read_bytes()
        except OSError as exc:
            raise RulesError(f"cannot read {path}: {exc}") from exc
        digest.update(_field(path.name.encode("utf-8")) + _field(body))
    if overrides:
        canonical = json.dumps(dict(overrides), sort_keys=True, separators=(",", ":"))
        digest.update(_field(b"overrides") + _field(canonical.encode("utf-8")))
    return digest.hexdigest()
