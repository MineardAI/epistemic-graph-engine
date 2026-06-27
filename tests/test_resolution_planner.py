from __future__ import annotations

import pytest
from pydantic import ValidationError

from epistemic_graph.claims.schema import ClaimLifecycle
from epistemic_graph.resolution.planner import plan_resolution_question
from epistemic_graph.resolution.schema import (
    ConflictBasis,
    ConflictReport,
    ConfidenceScore,
    ExactTermLookup,
    GraphSafetyIssue,
    MatchReason,
    QueryMode,
    RetrievedClaim,
    ResolutionAnswer,
    ResolutionQuestion,
    ResolutionState,
    ResolutionTrace,
    TraceStep,
    TraceStepType,
)


def test_raw_string_query_normalization() -> None:
    question = plan_resolution_question("  term: claims.jsonl . type = proposal  ")

    assert question.raw_query == "  term: claims.jsonl . type = proposal  "
    assert question.normalized_query == "term:claims.jsonl.type=proposal"
    assert question.query_mode == QueryMode.exact_term
    assert question.exact_term_lookups[0].artifact == "claims.jsonl"
    assert question.exact_term_lookups[0].field == "type"
    assert question.exact_term_lookups[0].value == "proposal"


@pytest.mark.parametrize(
    ("raw_query", "artifact", "field", "value"),
    [
        ("term:claims.jsonl.state=proposed", "claims.jsonl", "state", "proposed"),
        ("term:claim_graph.json.edge_type=supports", "claim_graph.json", "edge_type", "supports"),
        ("term:bounties.jsonl.claim_id=claim_123", "bounties.jsonl", "claim_id", "claim_123"),
    ],
)
def test_whitelisted_field_lookup(raw_query: str, artifact: str, field: str, value: str) -> None:
    question = plan_resolution_question(raw_query)

    assert question.query_mode == QueryMode.exact_term
    assert question.validation_errors == []
    assert question.exact_term_lookups[0].artifact == artifact
    assert question.exact_term_lookups[0].field == field
    assert question.exact_term_lookups[0].value == value


@pytest.mark.parametrize(
    "raw_query",
    [
        "term:claims.jsonl.body=proposal",
        "term:claim_graph.json.label=proposal",
        "term:bounties.jsonl.reward=proposal",
    ],
)
def test_rejection_of_non_whitelisted_fields(raw_query: str) -> None:
    question = plan_resolution_question(raw_query)

    assert question.query_mode == QueryMode.unsupported
    assert question.validation_errors


@pytest.mark.parametrize(
    "model, payload",
    [
        (
            ResolutionQuestion,
            {
                "question_id": "question_1",
                "raw_query": "claim:claim_1",
                "normalized_query": "claim:claim_1",
                "query_mode": "claim_id",
                "exact_claim_ids": ["claim_1"],
                "exact_observation_ids": [],
                "exact_evidence_ids": [],
                "exact_lifecycle_states": [],
                "exact_term_lookups": [],
                "validation_errors": [],
                "unexpected": True,
            },
        ),
        (
            ExactTermLookup,
            {"artifact": "claims.jsonl", "field": "id", "value": "claim_1", "unexpected": True},
        ),
        (
            RetrievedClaim,
            {
                "claim_id": "claim_1",
                "claim_type": "proposal",
                "claim_label": "assistant::proposal",
                "lifecycle": "proposed",
                "source_observation_ids": ["observation_1"],
                "source_evidence_ids": ["evidence_1"],
                "source_observation_hashes": ["hash_1"],
                "unexpected": True,
            },
        ),
        (
            ConflictReport,
            {
                "conflict_id": "conflict_1",
                "left_claim_id": "claim_1",
                "right_claim_id": "claim_2",
                "shared_evidence_ids": ["evidence_1"],
                "contradiction_edge_ids": ["edge_1"],
                "conflict_basis": "explicit_contradiction_edge",
                "left_lifecycle": "proposed",
                "right_lifecycle": "contested",
                "unexpected": True,
            },
        ),
        (
            ConfidenceScore,
            {
                "formula_version": "resolution-confidence-v1",
                "score": 50,
                "supporting_claim_count": 1,
                "contested_claim_count": 0,
                "rejected_claim_count": 0,
                "open_bounty_count": 0,
                "missing_reference_count": 0,
                "unexpected": True,
            },
        ),
        (
            TraceStep,
            {
                "step_id": "step_1",
                "step_type": "query_normalization",
                "source_ids": ["question_1"],
                "input_ids": ["raw_query"],
                "output_ids": ["question_1"],
                "detail_code": "normalized_query",
                "detail_message": "normalized query mode=claim_id",
                "unexpected": True,
            },
        ),
        (
            GraphSafetyIssue,
            {
                "issue_id": "issue_1",
                "issue_type": "missing_reference",
                "source_ids": ["claim_1"],
                "detail_code": "missing_support_source",
                "detail_message": "missing source",
                "unexpected": True,
            },
        ),
        (
            ResolutionAnswer,
            {
                "answer_id": "answer_1",
                "question": {
                    "question_id": "question_1",
                    "raw_query": "claim:claim_1",
                    "normalized_query": "claim:claim_1",
                    "query_mode": "claim_id",
                    "exact_claim_ids": ["claim_1"],
                    "exact_observation_ids": [],
                    "exact_evidence_ids": [],
                    "exact_lifecycle_states": [],
                    "exact_term_lookups": [],
                    "validation_errors": [],
                },
                "resolution_state": "supported",
                "confidence": {
                    "formula_version": "resolution-confidence-v1",
                    "score": 50,
                    "supporting_claim_count": 1,
                    "contested_claim_count": 0,
                    "rejected_claim_count": 0,
                    "open_bounty_count": 0,
                    "missing_reference_count": 0,
                },
                "retrieved_claim_ids": ["claim_1"],
                "conflict_report_ids": [],
                "supporting_claim_ids": [],
                "missing_reference_ids": [],
                "open_bounty_ids": [],
                "unexpected": True,
            },
        ),
        (
            ResolutionTrace,
            {
                "trace_id": "trace_1",
                "question": {
                    "question_id": "question_1",
                    "raw_query": "claim:claim_1",
                    "normalized_query": "claim:claim_1",
                    "query_mode": "claim_id",
                    "exact_claim_ids": ["claim_1"],
                    "exact_observation_ids": [],
                    "exact_evidence_ids": [],
                    "exact_lifecycle_states": [],
                    "exact_term_lookups": [],
                    "validation_errors": [],
                },
                "resolution_state": "supported",
                "retrieved_claims": [],
                "conflict_reports": [],
                "confidence": {
                    "formula_version": "resolution-confidence-v1",
                    "score": 50,
                    "supporting_claim_count": 1,
                    "contested_claim_count": 0,
                    "rejected_claim_count": 0,
                    "open_bounty_count": 0,
                    "missing_reference_count": 0,
                },
                "trace_steps": [],
                "input_artifact_hashes": {},
                "graph_safety_issues": [],
                "unexpected": True,
            },
        ),
    ],
)
def test_schema_rejects_unknown_fields(model, payload) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)
