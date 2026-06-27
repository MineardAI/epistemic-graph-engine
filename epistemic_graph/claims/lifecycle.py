from __future__ import annotations

from .schema import Claim, ClaimLifecycle


_ALLOWED_TRANSITIONS: dict[ClaimLifecycle, set[ClaimLifecycle]] = {
    ClaimLifecycle.proposed: {
        ClaimLifecycle.provisional,
        ClaimLifecycle.supported,
        ClaimLifecycle.contested,
        ClaimLifecycle.rejected,
        ClaimLifecycle.archived,
    },
    ClaimLifecycle.provisional: {
        ClaimLifecycle.supported,
        ClaimLifecycle.contested,
        ClaimLifecycle.resolved,
        ClaimLifecycle.rejected,
        ClaimLifecycle.archived,
    },
    ClaimLifecycle.supported: {
        ClaimLifecycle.contested,
        ClaimLifecycle.resolved,
        ClaimLifecycle.archived,
    },
    ClaimLifecycle.contested: {
        ClaimLifecycle.supported,
        ClaimLifecycle.resolved,
        ClaimLifecycle.rejected,
        ClaimLifecycle.archived,
    },
    ClaimLifecycle.resolved: {ClaimLifecycle.archived},
    ClaimLifecycle.rejected: {ClaimLifecycle.archived},
    ClaimLifecycle.archived: set(),
}

_UNRESOLVED_STATES = {
    ClaimLifecycle.proposed,
    ClaimLifecycle.provisional,
    ClaimLifecycle.supported,
    ClaimLifecycle.contested,
}


def can_transition_claim_lifecycle(current: ClaimLifecycle, next_state: ClaimLifecycle) -> bool:
    return next_state in _ALLOWED_TRANSITIONS[current]


def transition_claim_lifecycle(claim: Claim, next_state: ClaimLifecycle) -> Claim:
    if not can_transition_claim_lifecycle(claim.lifecycle, next_state):
        raise ValueError(f"invalid claim lifecycle transition: {claim.lifecycle.value} -> {next_state.value}")
    return claim.model_copy(update={"lifecycle": next_state})


def is_unresolved_claim_lifecycle(state: ClaimLifecycle) -> bool:
    return state in _UNRESOLVED_STATES
