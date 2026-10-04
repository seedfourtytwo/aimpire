"""Vocabulary and caps of the mind contract, version ``m0`` (ADR-0013 sections 3 and 4).

Why a separate module: the reply schema, the observation builder (F5c) and the
validator in ``aimpire.sim.actions`` all need the same words and limits. One
source keeps them from drifting.

Why kinds are plain strings and not JSON-schema ``enum``s
-----------------------------------------------------------
``kind`` (orders, commitments) and ``activity`` (policy allocations) are typed
``str`` in the reply schema and checked against the sets below by the validator.
Reasons, against ADR-0013 ("the same schema works on every provider"):

* **Partial acceptance.** An enum makes one unknown order kind fail the whole
  reply at the schema stage (``INVALID``). As a string, the validator drops just
  that order with ``UNKNOWN_ACTION`` (research note 50 section 3) and keeps the
  rest, which is what ADR-0013 section 5 asks for.
* **Measurement.** Constrained decoding with an enum hides what a mind tried to
  do. A rejected ``"BUILD"`` in M0 is data about the model; an enum would erase it.
* **Portability.** Every route supports plain strings; enum support and grammar
  compilation differ between small local models and hosted endpoints.
* **Stable shape.** Milestones add kinds (ADR-0013 section 4). With strings the
  reply schema's structure is the same for every contract version; only the
  descriptions list the words in force.

Why caps are not JSON-schema keywords
-------------------------------------
Anthropic structured output does not support ``maxLength``, ``minimum`` or
``maximum``, and supports ``maxItems`` only for the values 0 and 1 (research
note 30 section 3). So the caps live here and the validator enforces them:
excess list items are dropped with ``CAP_EXCEEDED``; over-long text is cut and
flagged ``TEXT_TRUNCATED`` (never a rejection, ADR-0013 section 3).

Units: shares and ration are permille (1000 = all workers / a full ration).
"""

from typing import Final

CONTRACT_VERSION: Final = "m0"

# --- Vocabulary (ADR-0013 section 4, milestone M0) -------------------------
ORDER_KINDS: Final = frozenset({"FORAGE", "MOVE_CAMP", "SCOUT"})
COMMITMENT_KINDS: Final = frozenset({"STOCK_AT_LEAST", "BE_AT"})
# Standing labour activities a policy may allocate shares to. ADR-0013 names
# FORAGE in its example; SCOUT is the other ongoing M0 task. MOVE_CAMP is a
# one-off and is not an activity.
ACTIVITIES: Final = frozenset({"FORAGE", "SCOUT"})
# Messages go to another civilization's id or to the voice (ADR-0017).
VOICE: Final = "VOICE"

# --- List caps (ADR-0013 section 3) ---------------------------------------
MAX_ORDERS: Final = 8
MAX_MESSAGES: Final = 3
MAX_COMMITMENTS: Final = 3
MAX_BELIEFS: Final = 3
# Not set by the ADR; chosen so one reply cannot rename the whole map.
MAX_NAMES: Final = 8
# Evidence ids a single belief may cite (not set by the ADR).
MAX_EVIDENCE_PER_BELIEF: Final = 8

# --- Text caps, in characters (Unicode code points) -----------------------
JOURNAL_MAX_CHARS: Final = 1200
ANNAL_MAX_CHARS: Final = 200
# The ADR fixes only journal and annal; the rest follow nearby precedents:
# messages match the voice's 280 (ADR-0017); belief statements match note 50's
# 200; order text and names are short labels.
MESSAGE_MAX_CHARS: Final = 280
BELIEF_MAX_CHARS: Final = 200
ORDER_TEXT_MAX_CHARS: Final = 200
NAME_MAX_CHARS: Final = 40
# The decision id is echoed from the observation; a longer one is a schema failure.
DECISION_ID_MAX_CHARS: Final = 64

# --- Numeric ranges --------------------------------------------------------
PERMILLE: Final = 1000
# Ration in permille of a full daily ration. Above 1000 lets a society feast.
MAX_RATION_PERMILLE: Final = 2000

# --- Observation limits ----------------------------------------------------
MAX_EVENTS: Final = 20


def words(kinds: frozenset[str]) -> str:
    """Render a vocabulary as a sorted, comma-separated list for schema descriptions."""
    return ", ".join(sorted(kinds))
