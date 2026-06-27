from __future__ import annotations

import pytest

from epistemic_graph.claims.builder import CLAIM_BUILDER_VERSION
from epistemic_graph.claims.lifecycle import can_transition_claim_lifecycle, transition_claim_lifecycle
from epistemic_graph.claims.schema import Claim, ClaimLifecycle


def _claim() -> Claim:
    return Claim(
        claim_id="claim_1",
        claim_type="statement",
        claim_label="user::statement",
        lifecycle=ClaimLifecycle.proposed,
        builder_version=CLAIM_BUILDER_VERSION,
        source_observation_ids=["obs_1"],
        source_evidence_ids=["evidence_1"],
        source_observation_hashes=["hash_1"],
        hypotheses=[],
    )


def test_claim_lifecycle_transitions_are_explicit() -> None:
    claim = _claim()
    assert can_transition_claim_lifecycle(claim.lifecycle, ClaimLifecycle.provisional)
    updated = transition_claim_lifecycle(claim, ClaimLifecycle.provisional)
    assert updated.lifecycle == ClaimLifecycle.provisional
    assert claim.lifecycle == ClaimLifecycle.proposed


def test_claim_lifecycle_rejects_invalid_transition() -> None:
    claim = _claim()
    with pytest.raises(ValueError):
        transition_claim_lifecycle(claim, ClaimLifecycle.resolved)
