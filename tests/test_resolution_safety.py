from __future__ import annotations

from epistemic_graph.resolution.engine import resolve_from_records
from epistemic_graph.resolution.schema import ResolutionState


def _claim(claim_id: str, lifecycle: str = "proposed", evidence_id: str = "evidence_shared") -> dict[str, object]:
    return {
        "claim_id": claim_id,
        "claim_type": "proposal",
        "claim_label": "assistant::proposal",
        "lifecycle": lifecycle,
        "builder_version": "claim-layer-v1",
        "source_observation_ids": [f"obs_{claim_id}"],
        "source_evidence_ids": [evidence_id],
        "source_observation_hashes": [f"hash_{claim_id}"],
        "hypotheses": [],
    }


def _bounty(claim_id: str, bounty_id: str | None = None) -> dict[str, object]:
    return {
        "bounty_id": bounty_id or f"bounty_{claim_id}",
        "claim_id": claim_id,
        "claim_type": "proposal",
        "status": "open",
        "missing_evidence": ["missing"],
        "expected_source_types": ["proposal follow-up observation"],
        "potential_resolution_impact": f"Could move claim {claim_id} toward supported status.",
        "source_observation_ids": [f"obs_{claim_id}"],
    }


def test_missing_reference_handling() -> None:
    claims = [_claim("claim_a")]
    graph = {
        "claims": claims,
        "support_edges": [
            {
                "edge_id": "edge_support_a",
                "edge_type": "supports",
                "source": "claim_a",
                "target": "obs_claim_a",
                "target_evidence_id": "evidence_shared",
                "target_observation_hash": "hash_claim_a",
            }
        ],
        "contradiction_edges": [
            {
                "edge_id": "edge_conflict_missing",
                "edge_type": "contradicts",
                "source": "claim_a",
                "target": "claim_missing",
                "shared_evidence_id": "evidence_shared",
            }
        ],
    }
    bounties = [_bounty("claim_a")]

    answer, trace = resolve_from_records("claim:claim_a", claims=claims, claim_graph=graph, bounties=bounties)

    assert answer.resolution_state == ResolutionState.unanswerable
    assert trace.graph_safety_issues
    assert any(issue.issue_type.value == "missing_reference" for issue in trace.graph_safety_issues)


def test_duplicate_reference_handling() -> None:
    claims = [_claim("claim_a")]
    graph = {
        "claims": claims,
        "support_edges": [
            {
                "edge_id": "edge_support_a",
                "edge_type": "supports",
                "source": "claim_a",
                "target": "obs_claim_a",
                "target_evidence_id": "evidence_shared",
                "target_observation_hash": "hash_claim_a",
            },
            {
                "edge_id": "edge_support_a",
                "edge_type": "supports",
                "source": "claim_a",
                "target": "obs_claim_a",
                "target_evidence_id": "evidence_shared",
                "target_observation_hash": "hash_claim_a",
            },
        ],
        "contradiction_edges": [],
    }
    bounties = [_bounty("claim_a"), _bounty("claim_a", "bounty_claim_a_duplicate")]

    first_answer, first_trace = resolve_from_records("claim:claim_a", claims=claims, claim_graph=graph, bounties=bounties)
    second_answer, second_trace = resolve_from_records("claim:claim_a", claims=claims, claim_graph=graph, bounties=bounties)

    assert first_answer == second_answer
    assert first_trace == second_trace
    assert any(issue.issue_type.value == "duplicate_reference" for issue in first_trace.graph_safety_issues)
    assert first_answer.resolution_state in {ResolutionState.insufficient_evidence, ResolutionState.supported}


def test_cycle_detection() -> None:
    claims = [_claim("claim_a"), _claim("claim_b")]
    graph = {
        "claims": claims,
        "support_edges": [
            {
                "edge_id": "edge_support_a",
                "edge_type": "supports",
                "source": "claim_a",
                "target": "obs_claim_a",
                "target_evidence_id": "evidence_shared",
                "target_observation_hash": "hash_claim_a",
            },
            {
                "edge_id": "edge_support_b",
                "edge_type": "supports",
                "source": "claim_b",
                "target": "obs_claim_b",
                "target_evidence_id": "evidence_shared",
                "target_observation_hash": "hash_claim_b",
            },
        ],
        "contradiction_edges": [
            {
                "edge_id": "edge_conflict_ab",
                "edge_type": "contradicts",
                "source": "claim_a",
                "target": "claim_b",
                "shared_evidence_id": "evidence_shared",
            },
            {
                "edge_id": "edge_conflict_ba",
                "edge_type": "contradicts",
                "source": "claim_b",
                "target": "claim_a",
                "shared_evidence_id": "evidence_shared",
            },
        ],
    }
    bounties = [_bounty("claim_a"), _bounty("claim_b")]

    answer, trace = resolve_from_records("term:claims.jsonl.state=proposed", claims=claims, claim_graph=graph, bounties=bounties)

    assert answer.resolution_state == ResolutionState.unanswerable
    assert any(issue.issue_type.value == "cyclic_reference" for issue in trace.graph_safety_issues)


def test_empty_input_behavior() -> None:
    answer, trace = resolve_from_records("claim:claim_a", claims=[], claim_graph={}, bounties=[])

    assert answer.resolution_state == ResolutionState.unanswerable
    assert any(issue.issue_type.value == "empty_inputs" for issue in trace.graph_safety_issues)


def test_malformed_graph_behavior() -> None:
    claims = [_claim("claim_a")]
    graph = {
        "claims": claims,
        "support_edges": [],
        "contradiction_edges": [
            {
                "edge_id": "edge_conflict_bad",
                "edge_type": "contradicts",
                "source": "claim_a",
                "shared_evidence_id": "evidence_shared",
            }
        ],
    }
    bounties = [_bounty("claim_a")]

    answer, trace = resolve_from_records("claim:claim_a", claims=claims, claim_graph=graph, bounties=bounties)

    assert answer.resolution_state == ResolutionState.unanswerable
    assert any(issue.issue_type.value == "malformed_entry" for issue in trace.graph_safety_issues)
