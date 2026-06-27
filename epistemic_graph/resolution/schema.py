from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..claims.schema import ClaimLifecycle


TERM_FIELD_WHITELIST: dict[str, set[str]] = {
    "claims.jsonl": {"id", "type", "state"},
    "claim_graph.json": {"source_id", "target_id", "edge_type"},
    "bounties.jsonl": {"id", "claim_id", "state", "reward_type"},
}

TERM_FIELD_ALIASES: dict[str, dict[str, str]] = {
    "claims.jsonl": {"id": "claim_id", "type": "claim_type", "state": "lifecycle"},
    "claim_graph.json": {"source_id": "source", "target_id": "target", "edge_type": "edge_type"},
    "bounties.jsonl": {"id": "bounty_id", "claim_id": "claim_id", "state": "status", "reward_type": "claim_type"},
}


class QueryMode(str, Enum):
    claim_id = "claim_id"
    observation_id = "observation_id"
    evidence_id = "evidence_id"
    lifecycle = "lifecycle"
    exact_term = "exact_term"
    unsupported = "unsupported"


class ResolutionState(str, Enum):
    supported = "supported"
    conflicted = "conflicted"
    insufficient_evidence = "insufficient_evidence"
    unanswerable = "unanswerable"
    invalid_query = "invalid_query"


class TraceStepType(str, Enum):
    query_normalization = "query_normalization"
    index_lookup = "index_lookup"
    candidate_retrieval = "candidate_retrieval"
    graph_validation = "graph_validation"
    conflict_detection = "conflict_detection"
    bounty_lookup = "bounty_lookup"
    confidence_calculation = "confidence_calculation"
    state_selection = "state_selection"
    answer_assembly = "answer_assembly"
    graph_safety = "graph_safety"


class MatchReason(str, Enum):
    claim_id = "claim_id"
    observation_id = "observation_id"
    evidence_id = "evidence_id"
    lifecycle = "lifecycle"
    term = "term"


class ConflictBasis(str, Enum):
    explicit_contradiction_edge = "explicit_contradiction_edge"


class GraphSafetyIssueType(str, Enum):
    missing_reference = "missing_reference"
    duplicate_reference = "duplicate_reference"
    malformed_entry = "malformed_entry"
    cyclic_reference = "cyclic_reference"
    empty_inputs = "empty_inputs"


class ExactTermLookup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact: Literal["claims.jsonl", "claim_graph.json", "bounties.jsonl"]
    field: str
    value: str

    @model_validator(mode="after")
    def _validate_field_whitelist(self) -> "ExactTermLookup":
        allowed = TERM_FIELD_WHITELIST[self.artifact]
        if self.field not in allowed:
            raise ValueError(f"field {self.field!r} is not whitelisted for {self.artifact}")
        return self


class ResolutionQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    raw_query: str
    normalized_query: str
    query_mode: QueryMode
    exact_claim_ids: list[str] = Field(default_factory=list)
    exact_observation_ids: list[str] = Field(default_factory=list)
    exact_evidence_ids: list[str] = Field(default_factory=list)
    exact_lifecycle_states: list[ClaimLifecycle] = Field(default_factory=list)
    exact_term_lookups: list[ExactTermLookup] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class RetrievedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    claim_type: str
    claim_label: str
    lifecycle: ClaimLifecycle
    source_observation_ids: list[str]
    source_evidence_ids: list[str]
    source_observation_hashes: list[str]
    support_edge_ids: list[str] = Field(default_factory=list)
    contradiction_edge_ids: list[str] = Field(default_factory=list)
    match_reasons: list[MatchReason] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)


class ConflictReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str
    left_claim_id: str
    right_claim_id: str
    shared_evidence_ids: list[str]
    contradiction_edge_ids: list[str]
    conflict_basis: ConflictBasis
    left_lifecycle: ClaimLifecycle
    right_lifecycle: ClaimLifecycle


class ConfidenceScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula_version: str
    score: int
    supporting_claim_count: int
    contested_claim_count: int
    rejected_claim_count: int
    open_bounty_count: int
    missing_reference_count: int

    @field_validator("score")
    @classmethod
    def _validate_score(cls, value: int) -> int:
        if not 0 <= value <= 100:
            raise ValueError("confidence score must be between 0 and 100")
        return value


class GraphSafetyIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    issue_type: GraphSafetyIssueType
    source_ids: list[str] = Field(default_factory=list)
    detail_code: str
    detail_message: str


class TraceStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    step_type: TraceStepType
    source_ids: list[str] = Field(default_factory=list)
    input_ids: list[str] = Field(default_factory=list)
    output_ids: list[str] = Field(default_factory=list)
    detail_code: str
    detail_message: str


class ResolutionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    question: ResolutionQuestion
    resolution_state: ResolutionState
    retrieved_claims: list[RetrievedClaim]
    conflict_reports: list[ConflictReport]
    confidence: ConfidenceScore
    trace_steps: list[TraceStep]
    input_artifact_hashes: dict[str, str]
    graph_safety_issues: list[GraphSafetyIssue] = Field(default_factory=list)


class ResolutionAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_id: str
    question: ResolutionQuestion
    resolution_state: ResolutionState
    confidence: ConfidenceScore
    retrieved_claim_ids: list[str]
    conflict_report_ids: list[str]
    supporting_claim_ids: list[str]
    missing_reference_ids: list[str]
    open_bounty_ids: list[str]
