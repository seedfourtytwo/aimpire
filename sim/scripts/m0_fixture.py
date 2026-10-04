"""The M0 fixture replay (``aimpire-replay-v2``) for the player's tests (F4d).

It is a real ``aimpire run`` of the M0 petri dish (``experiments.play.play``),
short, with the ``mock`` mind. Its provider is a TEST DOUBLE: each council it
takes the ``half_full`` rule's reply and, at a few councils, adds scripted
text, orders, a message and a name, so the player has every council field to
show. Every scripted string says it is fixture text, not a model's words. The
replies go through the same parser, validator and run store as a model's, so
the fixture's councils are exactly what the export reads from a run store.

Two orders are meant to be refused (an unknown place and an unknown kind), and
council 5 is not JSON at all, so the fixture shows ``REJECTED`` orders and an
``INVALID`` council next to ``VALID`` ones.
"""

import dataclasses
import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

from aimpire.cognition.baselines import rule_provider
from aimpire.cognition.disclosed import load_disclosed
from aimpire.cognition.protocol import (
    CognitionRequest,
    CognitionResult,
    ModelIdentity,
    Provider,
    parse_reply,
)
from aimpire.experiments.play import PlayOptions, play
from aimpire.rules import DEFAULT_RULES_DIR

SEED: Final = 7
TICKS: Final = 60
COUNCIL_EVERY: Final = 10
FRAME_EVERY: Final = 10
MONTH: Final = "2026-01"  # spend month of the throwaway store; not in the replay

Reply = dict[str, Any]


def _first_place(reply: Reply) -> str:
    """A place the rule itself chose, so it is one the civilization knows."""
    return str(reply["policy"]["allocations"][0]["place"])


def _council_1(reply: Reply) -> Reply:
    return {
        "journal": (
            "Fixture journal, council 1. Scripted test text, not a model: the player must "
            'show quotes "like these", <angle brackets> & accents (é) exactly as written.'
        ),
        "annal": "Fixture annal: the first council.",
        "names": [{"id": _first_place(reply), "name": "Fixture Meadow"}],
    }


def _council_3(reply: Reply) -> Reply:
    place = _first_place(reply)
    return {
        "journal": "Fixture journal, council 3: one order to accept and two to refuse.",
        "orders": [
            {"kind": "FORAGE", "place": place, "target": "", "qty": 3, "text": "fixture trip"},
            {"kind": "FORAGE", "place": "PL99", "target": "", "qty": 2, "text": ""},
            {"kind": "BUILD", "place": place, "target": "", "qty": 1, "text": ""},
        ],
        "messages": [{"to": "VOICE", "text": "Fixture message to the voice."}],
    }


SCRIPT: Final[dict[int, Callable[[Reply], Reply]]] = {1: _council_1, 3: _council_3}
NOT_JSON: Final = frozenset({5})


class ScriptedFixtureMind:
    """Test double: the ``half_full`` rule's reply plus the scripted additions above."""

    def __init__(self, inner: Provider) -> None:
        self._inner = inner

    async def complete(self, req: CognitionRequest) -> CognitionResult:
        """The rule's reply, changed at the scripted councils, re-parsed like live text."""
        result = await self._inner.complete(req)
        council = int(req.decision_id.rsplit("K", 1)[1])
        reply: Reply = json.loads(result.raw_text)
        if council in SCRIPT:
            reply.update(SCRIPT[council](reply))
        raw = "fixture: this reply is not JSON" if council in NOT_JSON else json.dumps(reply)
        parsed, status = parse_reply(raw)
        return dataclasses.replace(
            result, raw_text=raw, parsed=parsed, status=status, model_reported="mock:fixture"
        )

    def describe(self) -> ModelIdentity:
        """Identify as the mock provider: these are scripted replies."""
        return ModelIdentity(provider="mock", model="fixture", digest="")

    def estimate_max_cost_micro_usd(self, req: CognitionRequest) -> int | None:
        """Free, like every offline provider."""
        return 0


def m0_fixture_text() -> str:
    """Play the fixture run in a temporary folder and return its ``replay.json`` text."""
    inner = rule_provider("half_full", load_disclosed(DEFAULT_RULES_DIR))
    with tempfile.TemporaryDirectory() as tmp:
        opts = PlayOptions(
            world="m0",
            mind="mock",
            seed=SEED,
            ticks=TICKS,
            settings=(),
            renderer="places",
            out_root=Path(tmp),
            rules_dir=DEFAULT_RULES_DIR,
            council_every=COUNCIL_EVERY,
            frame_every=FRAME_EVERY,
            base_dir=Path(tmp),
            reproduce="scripts/make_fixture_replay.py",
        )
        result = play(
            opts, month=MONTH, echo=lambda _line: None, provider=ScriptedFixtureMind(inner)
        )
        return (result.run_dir / "replay.json").read_text(encoding="ascii")
