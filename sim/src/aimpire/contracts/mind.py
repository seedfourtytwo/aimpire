"""The mind contract, version ``m0`` (ADR-0013): one import point for its parts.

* ``reply``       — ``MindReply`` and its parts: what a mind sends back;
* ``observation`` — ``Observation`` and its sections: what a mind is shown;
* ``vocabulary``  — order, commitment and activity words, list and text caps.

The JSON schemas in ``schema/`` are generated from these models by
``aimpire.contracts.export``; never edit them by hand.
"""

from aimpire.contracts.observation import (
    CalendarSection,
    ClaimView,
    CommitmentView,
    EventView,
    KnowledgeSection,
    MessageView,
    Observation,
    OrderResult,
    PlaceView,
    StandingSection,
    StatusSection,
    StockLine,
    TaskView,
)
from aimpire.contracts.reply import (
    Allocation,
    Belief,
    Commitment,
    Message,
    MindReply,
    Name,
    Order,
    Policy,
)
from aimpire.contracts.vocabulary import CONTRACT_VERSION

__all__ = [
    "CONTRACT_VERSION",
    "Allocation",
    "Belief",
    "CalendarSection",
    "ClaimView",
    "Commitment",
    "CommitmentView",
    "EventView",
    "KnowledgeSection",
    "Message",
    "MessageView",
    "MindReply",
    "Name",
    "Observation",
    "Order",
    "OrderResult",
    "PlaceView",
    "Policy",
    "StandingSection",
    "StatusSection",
    "StockLine",
    "TaskView",
]
