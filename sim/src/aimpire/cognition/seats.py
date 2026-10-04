"""Turn an observation into a council seat and a request (ADR-0013 sections 2 and 5).

Why the seat comes from the observation: the validator may only accept what
the mind could refer to, and the observation is exactly what it was shown.
Known places, head count, evidence ids and the policy in force are therefore
read from the observation, never from world truth, so a reply naming an
unseen place is rejected as ``UNKNOWN_ENTITY`` without a leak. Contacts with
other civilizations arrive with M2; until then ``known_civs`` is empty.

``seats_for`` builds the per-council seats for a world whose civilizations
use the m0 layout (``civ_record``): it is the ``SeatsFor`` the runner calls.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from aimpire.cognition.council import SeatCall, decision_id_for
from aimpire.cognition.minds import MindSpec
from aimpire.cognition.observe import CouncilCall, build_observation, grid_layout
from aimpire.cognition.protocol import CognitionRequest, Provider
from aimpire.cognition.render import render_grid, render_places
from aimpire.contracts.mind import CONTRACT_VERSION, MindReply, Observation
from aimpire.sim.actions import CouncilSeat, PolicyLine, StandingPolicy
from aimpire.sim.calendar import Calendar
from aimpire.sim.state import WorldState

Renderer = Literal["places", "grid"]
RENDERERS: Final[frozenset[str]] = frozenset({"places", "grid"})
REPLY_SCHEMA: Final = MindReply.model_json_schema()


def seat_from_observation(obs: Observation) -> CouncilSeat:
    """What a reply to ``obs`` may refer to: only what ``obs`` showed."""
    policy = obs.standing.policy
    return CouncilSeat(
        civ_id=obs.civ_id,
        decision_id=obs.decision_id,
        council=obs.calendar.council,
        observation_version=obs.version,
        known_places=frozenset(p.place_id for p in obs.places),
        people=obs.status.population,
        known_civs=frozenset(),
        evidence_ids=frozenset(e.event_id for e in obs.events),
        policy=StandingPolicy(
            allocations=tuple(PolicyLine(a.activity, a.place, a.share) for a in policy.allocations),
            ration=policy.ration,
        ),
    )


def request_for(obs: Observation, text: str, system: str, mind: MindSpec) -> CognitionRequest:
    """The request for ``obs`` rendered as ``text``, sized by the mind's limits."""
    return CognitionRequest(
        decision_id=obs.decision_id,
        civ_id=obs.civ_id,
        contract=CONTRACT_VERSION,
        system=system,
        observation=obs,
        observation_text=text,
        reply_schema=REPLY_SCHEMA,
        max_output_tokens=mind.max_output_tokens,
        timeout_s=mind.timeout_s,
        effort=mind.effort,
        temperature=mind.temperature,
    )


def render(obs: Observation, state: WorldState, renderer: Renderer) -> str:
    """Prompt text for ``obs``: named places, or the block grid (the M0 comparison)."""
    if renderer == "grid":
        return render_grid(obs, grid_layout(state))
    return render_places(obs)


@dataclass(frozen=True, slots=True)
class Seat:
    """One civilization's chair for a whole run: the mind that sits in it, and its provider."""

    civ_id: str
    entity_id: int
    mind: MindSpec
    provider: Provider


def seats_for(
    seats: Sequence[Seat], *, calendar: Calendar, every_ticks: int, renderer: Renderer, system: str
) -> Callable[[WorldState, int], list[SeatCall]]:
    """The runner's ``SeatsFor``: one call per seat at each council, in seat order."""

    def build(state: WorldState, council: int) -> list[SeatCall]:
        calls: list[SeatCall] = []
        for seat in seats:
            call = CouncilCall(
                civ_id=seat.civ_id,
                council=council,
                decision_id=decision_id_for(seat.civ_id, council),
                next_council_tick=state.tick + every_ticks,
            )
            obs = build_observation(state, call, calendar)
            request = request_for(obs, render(obs, state, renderer), system, seat.mind)
            seat_view = seat_from_observation(obs)
            calls.append(
                SeatCall(seat.entity_id, seat_view, request, seat.provider, seat.mind.price)
            )
        return calls

    return build
