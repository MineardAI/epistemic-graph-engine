from __future__ import annotations

from epistemic_graph.claims.builder import build_claim_artifacts, build_claims
from epistemic_graph.claims.lifecycle import ClaimLifecycle
from epistemic_graph.claims.query import (
    active_bounties,
    contradictory_observations,
    find_claims,
    hypotheses,
    unresolved_claims,
    supporting_observations,
)
from epistemic_graph.claims.serialization import load_jsonl


def test_claim_query_helpers(contract1_artifacts, tmp_path):
    claim_dir = tmp_path / "claims"
    result = build_claim_artifacts(contract1_artifacts.observations_path, claim_dir)
    observations = load_jsonl(contract1_artifacts.observations_path)
    claims = load_jsonl(result.claims_path)
    bounties = load_jsonl(result.bounties_path)

    first_claim = claims[0]
    found = find_claims(claims, claim_ids={first_claim["claim_id"]})
    assert found == [first_claim]
    assert len(unresolved_claims(claims)) == len(claims)
    assert supporting_observations(first_claim, observations)
    assert contradictory_observations(first_claim, claims, observations) == []
    assert hypotheses(first_claim) == []
    assert len(active_bounties(bounties)) == len(claims)


def test_claim_query_status_filter(contract1_artifacts, tmp_path):
    claims = build_claims(contract1_artifacts.observations_path)
    filtered = find_claims(claims, lifecycle=ClaimLifecycle.proposed)
    assert len(filtered) == len(claims)
