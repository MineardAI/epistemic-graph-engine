"""Contract 003 evidence resolution layer."""

from .engine import build_resolution_artifacts, resolve_from_records, resolve_query
from .planner import plan_resolution_question
from .schema import (
    ConflictBasis,
    ConflictReport,
    ConfidenceScore,
    ExactTermLookup,
    GraphSafetyIssue,
    GraphSafetyIssueType,
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

__all__ = [
    "ConflictBasis",
    "ConflictReport",
    "ConfidenceScore",
    "ExactTermLookup",
    "GraphSafetyIssue",
    "GraphSafetyIssueType",
    "MatchReason",
    "QueryMode",
    "RetrievedClaim",
    "ResolutionAnswer",
    "ResolutionQuestion",
    "ResolutionState",
    "ResolutionTrace",
    "TraceStep",
    "TraceStepType",
    "build_resolution_artifacts",
    "plan_resolution_question",
    "resolve_from_records",
    "resolve_query",
]

