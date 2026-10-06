"""The reply schema lists the allowed words, so a constrained provider cannot invent one."""

from typing import Any

from aimpire.contracts.reply import Commitment, MindReply, Order
from aimpire.contracts.vocabulary import COMMITMENT_KINDS, ORDER_KINDS


def _defs() -> dict[str, Any]:
    return MindReply.model_json_schema(mode="validation")["$defs"]


def test_schema_enumerates_order_and_commitment_kinds() -> None:
    defs = _defs()
    assert defs["Order"]["properties"]["kind"]["enum"] == sorted(ORDER_KINDS)
    assert defs["Commitment"]["properties"]["kind"]["enum"] == sorted(COMMITMENT_KINDS)
    assert defs["Allocation"]["properties"]["activity"]["enum"] == ["FORAGE", "SCOUT"]


def test_python_type_stays_open_so_the_validator_reports_a_closed_reason() -> None:
    # An unconstrained provider may still send "move"; it must parse, so that the
    # validator can reject it as UNKNOWN_ACTION instead of failing the whole reply.
    order = Order(kind="move", place="PL04", target="", qty=3, text="")
    assert order.kind == "move"
    assert Commitment(kind="x", place="", qty=0, by_council=1).kind == "x"
