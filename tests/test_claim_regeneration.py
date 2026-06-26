from __future__ import annotations

from epistemic_graph.claims.builder import build_claim_artifacts


def test_claim_layer_regeneration_is_byte_identical(contract1_artifacts, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    result1 = build_claim_artifacts(contract1_artifacts.observations_path, first)
    first_claims = result1.claims_path.read_bytes()
    first_graph = result1.claim_graph_path.read_bytes()
    first_bounties = result1.bounties_path.read_bytes()

    result1.claims_path.unlink()
    result1.claim_graph_path.unlink()
    result1.bounties_path.unlink()

    result2 = build_claim_artifacts(contract1_artifacts.observations_path, first)
    assert first_claims == result2.claims_path.read_bytes()
    assert first_graph == result2.claim_graph_path.read_bytes()
    assert first_bounties == result2.bounties_path.read_bytes()

    result3 = build_claim_artifacts(contract1_artifacts.observations_path, second)
    assert result2.claims_path.read_bytes() == result3.claims_path.read_bytes()
    assert result2.claim_graph_path.read_bytes() == result3.claim_graph_path.read_bytes()
    assert result2.bounties_path.read_bytes() == result3.bounties_path.read_bytes()

