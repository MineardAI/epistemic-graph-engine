from __future__ import annotations

import pytest
from pydantic import ValidationError

from epistemic_graph.claims.builder import CLAIM_BUILDER_VERSION
from epistemic_graph.claims.schema import Bounty, Claim, Hypothesis


def _claim_payload(hypotheses: list[dict[str, object]]) -> dict[str, object]:
    return {
        "claim_id": "claim_1",
        "claim_type": "statement",
        "claim_label": "user::statement",
        "lifecycle": "proposed",
        "builder_version": CLAIM_BUILDER_VERSION,
        "source_observation_ids": ["obs_1"],
        "source_evidence_ids": ["evidence_1"],
        "source_observation_hashes": ["hash_1"],
        "hypotheses": hypotheses,
    }


def test_claim_accepts_five_hypotheses() -> None:
    payload = _claim_payload(
        [
            {
                "hypothesis_id": f"hypothesis_{index}",
                "description": f"description {index}",
                "source_observation_ids": ["obs_1"],
            }
            for index in range(5)
        ]
    )

    claim = Claim.model_validate(payload)

    assert len(claim.hypotheses) == 5


def test_claim_rejects_six_hypotheses() -> None:
    payload = _claim_payload(
        [
            {
                "hypothesis_id": f"hypothesis_{index}",
                "description": f"description {index}",
                "source_observation_ids": ["obs_1"],
            }
            for index in range(6)
        ]
    )

    with pytest.raises(ValidationError):
        Claim.model_validate(payload)


def test_hypothesis_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Hypothesis.model_validate(
            {
                "hypothesis_id": "hypothesis_1",
                "description": "description",
                "source_observation_ids": ["obs_1"],
                "unexpected": True,
            }
        )


def test_bounty_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Bounty.model_validate(
            {
                "bounty_id": "bounty_1",
                "claim_id": "claim_1",
                "claim_type": "statement",
                "status": "open",
                "missing_evidence": ["missing observation"],
                "expected_source_types": ["statement follow-up observation"],
                "potential_resolution_impact": "Would support the claim.",
                "source_observation_ids": ["obs_1"],
                "unexpected": True,
            }
        )
