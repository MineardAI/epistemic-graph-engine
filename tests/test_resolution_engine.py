from __future__ import annotations

from pathlib import Path

from epistemic_graph.claims.serialization import load_jsonl
from epistemic_graph.claims.schema import ClaimLifecycle
from epistemic_graph.resolution.engine import (
    _confidence_score,
    _select_resolution_state,
    build_resolution_artifacts,
    resolve_from_records,
    resolve_query,
)
from epistemic_graph.resolution.schema import ConflictReport, QueryMode, ResolutionQuestion, ResolutionState, TraceStepType


def test_exact_claim_observation_evidence_and_lifecycle_lookup(contract2_artifacts) -> None:
    claims = load_jsonl(contract2_artifacts.claims_path)
    first_claim = claims[0]
    first_observation_id = first_claim["source_observation_ids"][0]
    first_evidence_id = first_claim["source_evidence_ids"][0]

    claim_answer, _ = resolve_query(
        f"claim:{first_claim['claim_id']}",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
    )
    observation_answer, _ = resolve_query(
        f"observation:{first_observation_id}",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
    )
    evidence_answer, _ = resolve_query(
        f"evidence:{first_evidence_id}",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
    )
    lifecycle_answer, _ = resolve_query(
        "lifecycle:proposed",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
    )

    assert claim_answer.retrieved_claim_ids == [first_claim["claim_id"]]
    assert observation_answer.retrieved_claim_ids == [first_claim["claim_id"]]
    assert evidence_answer.retrieved_claim_ids == [first_claim["claim_id"]]
    assert lifecycle_answer.retrieved_claim_ids == [claim["claim_id"] for claim in claims]


def test_exact_term_lookup_and_bounty_lookup(contract2_artifacts) -> None:
    claims = load_jsonl(contract2_artifacts.claims_path)
    proposal_claim_ids = [claim["claim_id"] for claim in claims if claim["claim_type"] == "proposal"]

    answer, trace = resolve_query(
        "term:claims.jsonl.type=proposal",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
    )
    bounty_answer, _ = resolve_query(
        "term:bounties.jsonl.state=open",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
    )

    assert answer.retrieved_claim_ids == proposal_claim_ids
    assert bounty_answer.open_bounty_ids
    assert len(bounty_answer.open_bounty_ids) == len(claims)
    assert trace.trace_steps


def test_non_whitelisted_exact_term_lookup_returns_invalid_query(contract2_artifacts) -> None:
    answer, trace = resolve_query(
        "term:claims.jsonl.metadata_author=tyrone",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
    )

    assert trace.question.raw_query == "term:claims.jsonl.metadata_author=tyrone"
    assert trace.question.query_mode.value == "unsupported"
    assert trace.question.validation_errors
    assert answer.resolution_state == ResolutionState.invalid_query
    assert trace.resolution_state == ResolutionState.invalid_query
    assert answer.retrieved_claim_ids == []
    assert trace.retrieved_claims == []
    assert any(step.step_type == TraceStepType.state_selection and step.output_ids == ["invalid_query"] for step in trace.trace_steps)


def test_deterministic_answer_and_trace_generation(contract2_artifacts, tmp_path: Path) -> None:
    first = build_resolution_artifacts(
        "claim:claim_00072a8c4116a3a7da7c8366",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
        tmp_path / "first",
    )
    second = build_resolution_artifacts(
        "claim:claim_00072a8c4116a3a7da7c8366",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
        tmp_path / "second",
    )

    assert first.answer_path.read_bytes() == second.answer_path.read_bytes()
    assert first.trace_path.read_bytes() == second.trace_path.read_bytes()


def test_confidence_formula_and_state_precedence() -> None:
    score = _confidence_score(
        supporting_claim_count=2,
        contested_claim_count=1,
        rejected_claim_count=0,
        open_bounty_count=3,
        missing_reference_count=1,
        resolution_state=ResolutionState.insufficient_evidence,
    )
    assert score.score == 5

    invalid_question = ResolutionQuestion(
        question_id="question_1",
        raw_query="",
        normalized_query="",
        query_mode=QueryMode.unsupported,
        exact_claim_ids=[],
        exact_observation_ids=[],
        exact_evidence_ids=[],
        exact_lifecycle_states=[],
        exact_term_lookups=[],
        validation_errors=["empty query"],
    )
    conflicted = ConflictReport(
        conflict_id="conflict_1",
        left_claim_id="claim_1",
        right_claim_id="claim_2",
        shared_evidence_ids=["evidence_1"],
        contradiction_edge_ids=["edge_1"],
        conflict_basis="explicit_contradiction_edge",
        left_lifecycle=ClaimLifecycle.proposed,
        right_lifecycle=ClaimLifecycle.contested,
    )

    assert _select_resolution_state(invalid_question, [], [conflicted], [], []) == ResolutionState.invalid_query

    valid_question = ResolutionQuestion(
        question_id="question_2",
        raw_query="claim:claim_1",
        normalized_query="claim:claim_1",
        query_mode=QueryMode.claim_id,
        exact_claim_ids=["claim_1"],
        exact_observation_ids=[],
        exact_evidence_ids=[],
        exact_lifecycle_states=[],
        exact_term_lookups=[],
        validation_errors=[],
    )
    assert _select_resolution_state(valid_question, [], [], [], []) == ResolutionState.unanswerable


def test_explicit_contradiction_edge_handling() -> None:
    claims = [
        {
            "claim_id": "claim_a",
            "claim_type": "proposal",
            "claim_label": "assistant::proposal",
            "lifecycle": "proposed",
            "builder_version": "claim-layer-v1",
            "source_observation_ids": ["obs_a"],
            "source_evidence_ids": ["evidence_shared"],
            "source_observation_hashes": ["hash_a"],
            "hypotheses": [],
        },
        {
            "claim_id": "claim_b",
            "claim_type": "proposal",
            "claim_label": "assistant::proposal",
            "lifecycle": "contested",
            "builder_version": "claim-layer-v1",
            "source_observation_ids": ["obs_b"],
            "source_evidence_ids": ["evidence_shared"],
            "source_observation_hashes": ["hash_b"],
            "hypotheses": [],
        },
    ]
    graph = {
        "claims": claims,
        "support_edges": [
            {
                "edge_id": "edge_support_a",
                "edge_type": "supports",
                "source": "claim_a",
                "target": "obs_a",
                "target_evidence_id": "evidence_shared",
                "target_observation_hash": "hash_a",
            },
            {
                "edge_id": "edge_support_b",
                "edge_type": "supports",
                "source": "claim_b",
                "target": "obs_b",
                "target_evidence_id": "evidence_shared",
                "target_observation_hash": "hash_b",
            },
        ],
        "contradiction_edges": [
            {
                "edge_id": "edge_conflict_ab",
                "edge_type": "contradicts",
                "source": "claim_a",
                "target": "claim_b",
                "shared_evidence_id": "evidence_shared",
            }
        ],
    }
    bounties = [
        {
            "bounty_id": "bounty_a",
            "claim_id": "claim_a",
            "claim_type": "proposal",
            "status": "open",
            "missing_evidence": ["missing"],
            "expected_source_types": ["proposal follow-up observation"],
            "potential_resolution_impact": "Could move claim claim_a toward supported status.",
            "source_observation_ids": ["obs_a"],
        },
        {
            "bounty_id": "bounty_b",
            "claim_id": "claim_b",
            "claim_type": "proposal",
            "status": "open",
            "missing_evidence": ["missing"],
            "expected_source_types": ["proposal follow-up observation"],
            "potential_resolution_impact": "Could move claim claim_b toward supported status.",
            "source_observation_ids": ["obs_b"],
        },
    ]

    answer, trace = resolve_from_records("term:claims.jsonl.type=proposal", claims=claims, claim_graph=graph, bounties=bounties)

    assert answer.resolution_state == ResolutionState.conflicted
    assert answer.conflict_report_ids
    assert trace.conflict_reports
