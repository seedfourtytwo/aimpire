"""Property tests for the reply validator (ADR-0016 section 6: invariants by Hypothesis).

Invariants:
* no reply, however malformed, changes the state hash or raises;
* every decision ends in one outcome, logged once, with reasons from the closed enum;
* whatever is accepted is legal: m0 kinds, known places, labour within head count,
  text within its caps, and a record made only of ints and strings.
"""

from typing import Any

import numpy as np
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from aimpire.contracts.vocabulary import (
    ANNAL_MAX_CHARS,
    JOURNAL_MAX_CHARS,
    MAX_ORDERS,
    MESSAGE_MAX_CHARS,
    ORDER_KINDS,
    ORDER_TEXT_MAX_CHARS,
    PERMILLE,
)
from aimpire.sim.actions import (
    CouncilSeat,
    DecisionLog,
    Outcome,
    PolicyLine,
    Reason,
    StandingPolicy,
    validate_reply,
)
from aimpire.sim.hashing import state_hash
from aimpire.sim.state import WorldState, check_value

PLACES = frozenset({"PL01", "PL02"})
SEAT = CouncilSeat(
    civ_id="C1",
    decision_id="D1",
    council=2,
    observation_version="v2",
    known_places=PLACES,
    people=6,
    known_civs=frozenset({"C2"}),
    evidence_ids=frozenset({"EV1"}),
    policy=StandingPolicy(allocations=(PolicyLine("FORAGE", "PL01", 1000),), ration=1000),
)

json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(-(2**70), 2**70)
    | st.floats(allow_nan=True)
    | st.text(max_size=8),
    lambda inner: (
        st.lists(inner, max_size=4) | st.dictionaries(st.text(max_size=6), inner, max_size=4)
    ),
    max_leaves=12,
)
words = st.sampled_from(["", "PL01", "PL02", "PL99", "FORAGE", "SCOUT", "MOVE_CAMP", "BUILD",
                         "VOICE", "C1", "C2", "EV1", "EV9", "STOCK_AT_LEAST", "BE_AT"])  # fmt: skip
# Field-specific pools: mostly legal values, so replies reach the cumulative
# checks (labour, caps) and not just the first rejection; `words` adds noise.
kinds = st.sampled_from(["FORAGE"] * 4 + ["SCOUT"] * 2 + ["MOVE_CAMP", "BUILD", ""])
places = st.sampled_from(["PL01"] * 3 + ["PL02"] * 3 + ["PL99", ""])
targets = st.sampled_from([""] * 5 + ["P1"])
texts = st.text(max_size=1500) | words
small = st.integers(-3, 12)
order = st.fixed_dictionaries(
    {
        "kind": kinds,
        "place": places,
        "target": targets,
        "qty": st.integers(1, 4) | small,
        "text": texts,
    }
)
reply = st.fixed_dictionaries(
    {
        "decision_id": st.sampled_from(["D1", "D1", "D1", "D2", ""]),
        "policy": st.fixed_dictionaries(
            {
                "allocations": st.lists(
                    st.fixed_dictionaries(
                        {"activity": words, "place": words, "share": st.integers(-10, 1200)}
                    ),
                    max_size=3,
                ),
                "ration": st.integers(-5, 2500),
            }
        ),
        "orders": st.lists(order, max_size=11),
        "messages": st.lists(st.fixed_dictionaries({"to": words, "text": texts}), max_size=5),
        "commitments": st.lists(
            st.fixed_dictionaries(
                {"kind": words, "place": words, "qty": small, "by_council": small}
            ),
            max_size=5,
        ),
        "beliefs": st.lists(
            st.fixed_dictionaries({"statement": texts, "evidence": st.lists(words, max_size=3)}),
            max_size=5,
        ),
        "names": st.lists(st.fixed_dictionaries({"id": words, "name": texts}), max_size=4),
        "journal": texts,
        "annal": texts,
    }
)


def _mutated(base: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    out = dict(base)
    if key == "__drop__":
        out.pop("annal")
    else:
        out[key] = value
    return out


MUTATION_KEYS = ["decision_id", "policy", "orders", "journal", "extra", "__drop__"]
replies = (
    reply | json_values | st.builds(_mutated, reply, st.sampled_from(MUTATION_KEYS), json_values)
)


def _state() -> WorldState:
    state = WorldState(run_seed=3, rules_version="v1", rules_hash="r", tick=20)
    state.add_layer("food", np.arange(9, dtype=np.int64).reshape(3, 3))
    state.add_entity("person", {"civ": "C1"})
    return state


@settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
@given(candidate=replies, version=st.sampled_from(["v2", "v1"]))
def test_no_reply_changes_state_and_acceptance_is_legal(candidate: Any, version: str):
    state = _state()
    before = state_hash(state)
    log = DecisionLog()
    decision = validate_reply(state, "C1", version, candidate, seat=SEAT, log=log)
    assert state_hash(state) == before
    assert log.records == (decision,)
    assert decision.outcome in {Outcome.VALID, Outcome.PARTIAL, Outcome.INVALID}
    assert all(isinstance(r.reason, Reason) for r in decision.rejections)
    assert (decision.outcome is Outcome.VALID) == (decision.rejections == ())
    if decision.outcome is Outcome.INVALID:
        assert decision.orders == () and decision.policy == SEAT.policy
    assert len(decision.orders) <= MAX_ORDERS
    labour = 0
    for o in decision.orders:
        assert o.kind in ORDER_KINDS and o.place in PLACES and o.target == ""
        assert len(o.text) <= ORDER_TEXT_MAX_CHARS
        labour += 0 if o.kind == "MOVE_CAMP" else o.qty
    assert labour <= SEAT.people
    assert sum(line.share for line in decision.policy.allocations) <= PERMILLE
    assert all(
        m.to in {"VOICE", "C2"} and len(m.text) <= MESSAGE_MAX_CHARS for m in decision.messages
    )
    assert all(set(b.evidence) <= {"EV1"} and b.evidence for b in decision.beliefs)
    assert len(decision.journal) <= JOURNAL_MAX_CHARS and len(decision.annal) <= ANNAL_MAX_CHARS
    check_value(decision.to_value())


@settings(max_examples=100)
@given(first=replies, second=replies)
def test_revalidation_returns_the_stored_record(first: Any, second: Any):
    log = DecisionLog()
    state = _state()
    a = validate_reply(state, "C1", "v2", first, seat=SEAT, log=log)
    b = validate_reply(state, "C1", "v2", second, seat=SEAT, log=log)
    assert b is a and len(log) == 1


@settings(max_examples=100)
@given(candidate=replies)
def test_validation_is_deterministic(candidate: Any):
    one = validate_reply(_state(), "C1", "v2", candidate, seat=SEAT, log=DecisionLog())
    two = validate_reply(_state(), "C1", "v2", candidate, seat=SEAT, log=DecisionLog())
    assert one == two and one.to_value() == two.to_value()
