from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ..hash_utils import sha256_hex, stable_id
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
    TERM_FIELD_ALIASES,
)
from .serialization import load_json, load_jsonl, write_json
from .trace import build_trace_step
from ..claims.schema import ClaimLifecycle


@dataclass(frozen=True)
class ResolutionResult:
    answer_path: Path
    trace_path: Path
    answer: ResolutionAnswer
    trace: ResolutionTrace


def _canonical_sort(records: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return sorted(records, key=lambda record: record[key])


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _artifact_hash(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _load_claims(claims_path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(claims_path)


def _load_bounties(bounties_path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(bounties_path)


def _load_graph(graph_path: str | Path) -> dict[str, Any]:
    graph = load_json(graph_path)
    if not isinstance(graph, dict):
        return {}
    return graph


def _is_claim_record(record: dict[str, Any]) -> bool:
    return all(field in record for field in ("claim_id", "claim_type", "claim_label", "lifecycle"))


def _make_issue(issue_type: GraphSafetyIssueType, source_ids: Iterable[str], detail_code: str, detail_message: str) -> GraphSafetyIssue:
    source_ids_list = sorted(dict.fromkeys(source_ids))
    return GraphSafetyIssue(
        issue_id=stable_id(
            "graph-issue",
            {
                "issue_type": issue_type.value,
                "source_ids": source_ids_list,
                "detail_code": detail_code,
                "detail_message": detail_message,
            },
        ),
        issue_type=issue_type,
        source_ids=source_ids_list,
        detail_code=detail_code,
        detail_message=detail_message,
    )


@dataclass(frozen=True)
class ResolutionIndexes:
    claims_by_id: dict[str, dict[str, Any]]
    claims_by_observation_id: dict[str, list[str]]
    claims_by_evidence_id: dict[str, list[str]]
    claims_by_lifecycle: dict[str, list[str]]
    claims_by_type: dict[str, list[str]]
    support_edges_by_claim_id: dict[str, list[dict[str, Any]]]
    contradiction_edges_by_claim_id: dict[str, list[dict[str, Any]]]
    contradiction_edges_by_pair: dict[tuple[str, str], dict[str, Any]]
    bounties_by_id: dict[str, dict[str, Any]]
    bounties_by_claim_id: dict[str, list[dict[str, Any]]]
    bounties_by_state: dict[str, list[dict[str, Any]]]
    bounties_by_reward_type: dict[str, list[dict[str, Any]]]
    graph_safety_issues: list[GraphSafetyIssue]
    graph_claim_ids: set[str]


def _build_indexes(
    claims: list[dict[str, Any]],
    graph: dict[str, Any],
    bounties: list[dict[str, Any]],
) -> ResolutionIndexes:
    graph_safety_issues: list[GraphSafetyIssue] = []
    claims_by_id: dict[str, dict[str, Any]] = {}
    claims_by_observation_id: dict[str, list[str]] = defaultdict(list)
    claims_by_evidence_id: dict[str, list[str]] = defaultdict(list)
    claims_by_lifecycle: dict[str, list[str]] = defaultdict(list)
    claims_by_type: dict[str, list[str]] = defaultdict(list)

    for claim in sorted((record for record in claims if _is_claim_record(record)), key=lambda record: record["claim_id"]):
        claim_id = claim["claim_id"]
        if claim_id in claims_by_id:
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.duplicate_reference,
                    [claim_id],
                    "duplicate_claim_id",
                    f"duplicate claim_id {claim_id}",
                )
            )
            continue
        claims_by_id[claim_id] = claim
        claims_by_lifecycle[claim["lifecycle"]].append(claim_id)
        claims_by_type[claim["claim_type"]].append(claim_id)
        for observation_id in claim.get("source_observation_ids", []):
            claims_by_observation_id[observation_id].append(claim_id)
        for evidence_id in claim.get("source_evidence_ids", []):
            claims_by_evidence_id[evidence_id].append(claim_id)

    support_edges_by_claim_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    contradiction_edges_by_claim_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    contradiction_edges_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    graph_claim_ids: set[str] = set()
    graph_claim_records = graph.get("claims") or []
    if not claims or not graph_claim_records or not bounties:
        graph_safety_issues.append(
            _make_issue(
                GraphSafetyIssueType.empty_inputs,
                [],
                "empty_inputs",
                "one or more input artifacts are empty",
            )
        )

    for claim_record in graph_claim_records:
        claim_id = claim_record.get("claim_id")
        if isinstance(claim_id, str):
            graph_claim_ids.add(claim_id)

    edge_ids_seen: set[str] = set()
    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in graph.get("support_edges") or []:
        edge_id = edge.get("edge_id")
        source = edge.get("source")
        target = edge.get("target")
        edge_type = edge.get("edge_type")
        if not isinstance(edge_id, str) or not isinstance(source, str) or not isinstance(target, str) or not isinstance(edge_type, str):
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.malformed_entry,
                    [value for value in (edge_id, source, target) if isinstance(value, str)],
                    "malformed_support_edge",
                    "support edge is missing required fields",
                )
            )
            continue
        if edge_id in edge_ids_seen:
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.duplicate_reference,
                    [edge_id],
                    "duplicate_edge_id",
                    f"duplicate edge_id {edge_id}",
                )
            )
            continue
        edge_ids_seen.add(edge_id)
        if source not in claims_by_id:
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.missing_reference,
                    [edge_id, source],
                    "missing_support_source",
                    f"support edge source {source} is not present in claims.jsonl",
                )
            )
            continue
        support_edges_by_claim_id[source].append(edge)

    for edge in graph.get("contradiction_edges") or []:
        edge_id = edge.get("edge_id")
        source = edge.get("source")
        target = edge.get("target")
        edge_type = edge.get("edge_type")
        if not isinstance(edge_id, str) or not isinstance(source, str) or not isinstance(target, str) or not isinstance(edge_type, str):
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.malformed_entry,
                    [value for value in (edge_id, source, target) if isinstance(value, str)],
                    "malformed_contradiction_edge",
                    "contradiction edge is missing required fields",
                )
            )
            continue
        if edge_id in edge_ids_seen:
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.duplicate_reference,
                    [edge_id],
                    "duplicate_edge_id",
                    f"duplicate edge_id {edge_id}",
                )
            )
            continue
        edge_ids_seen.add(edge_id)
        if source not in claims_by_id or target not in claims_by_id:
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.missing_reference,
                    [edge_id, source, target],
                    "missing_contradiction_reference",
                    "contradiction edge references a missing claim",
                )
            )
            continue
        contradiction_edges_by_claim_id[source].append(edge)
        contradiction_edges_by_pair[(source, target)] = edge
        adjacency[source].add(target)

    visited: set[str] = set()
    recursion_stack: set[str] = set()
    cycle_nodes: set[str] = set()

    def visit(node: str) -> None:
        visited.add(node)
        recursion_stack.add(node)
        for neighbor in sorted(adjacency.get(node, set())):
            if neighbor not in visited:
                visit(neighbor)
            elif neighbor in recursion_stack:
                cycle_nodes.update({node, neighbor})
        recursion_stack.remove(node)

    for node in sorted(adjacency):
        if node not in visited:
            visit(node)

    if cycle_nodes:
        graph_safety_issues.append(
            _make_issue(
                GraphSafetyIssueType.cyclic_reference,
                sorted(cycle_nodes),
                "cyclic_contradiction_edges",
                "contradiction edge cycle detected",
            )
        )

    bounties_by_id: dict[str, dict[str, Any]] = {}
    bounties_by_claim_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    bounties_by_state: dict[str, list[dict[str, Any]]] = defaultdict(list)
    bounties_by_reward_type: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for bounty in sorted((record for record in bounties if isinstance(record, dict)), key=lambda record: record.get("bounty_id", "")):
        bounty_id = bounty.get("bounty_id")
        claim_id = bounty.get("claim_id")
        status = bounty.get("status")
        reward_type = bounty.get("claim_type")
        if not isinstance(bounty_id, str) or not isinstance(claim_id, str) or not isinstance(status, str) or not isinstance(reward_type, str):
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.malformed_entry,
                    [value for value in (bounty_id, claim_id) if isinstance(value, str)],
                    "malformed_bounty",
                    "bounty record is missing required fields",
                )
            )
            continue
        if bounty_id in bounties_by_id:
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.duplicate_reference,
                    [bounty_id],
                    "duplicate_bounty_id",
                    f"duplicate bounty_id {bounty_id}",
                )
            )
            continue
        bounties_by_id[bounty_id] = bounty
        bounties_by_claim_id[claim_id].append(bounty)
        bounties_by_state[status].append(bounty)
        bounties_by_reward_type[reward_type].append(bounty)
        if claim_id not in claims_by_id:
            graph_safety_issues.append(
                _make_issue(
                    GraphSafetyIssueType.missing_reference,
                    [bounty_id, claim_id],
                    "missing_bounty_claim",
                    f"bounty {bounty_id} references missing claim {claim_id}",
                )
            )

    for mapping in (claims_by_lifecycle, claims_by_type, claims_by_observation_id, claims_by_evidence_id):
        for key in list(mapping):
            mapping[key] = sorted(dict.fromkeys(mapping[key]))

    for mapping, sort_key in (
        (support_edges_by_claim_id, "edge_id"),
        (contradiction_edges_by_claim_id, "edge_id"),
        (bounties_by_claim_id, "bounty_id"),
        (bounties_by_state, "bounty_id"),
        (bounties_by_reward_type, "bounty_id"),
    ):
        for key in list(mapping):
            mapping[key] = sorted(mapping[key], key=lambda record: record[sort_key])

    return ResolutionIndexes(
        claims_by_id=claims_by_id,
        claims_by_observation_id=dict(claims_by_observation_id),
        claims_by_evidence_id=dict(claims_by_evidence_id),
        claims_by_lifecycle=dict(claims_by_lifecycle),
        claims_by_type=dict(claims_by_type),
        support_edges_by_claim_id=dict(support_edges_by_claim_id),
        contradiction_edges_by_claim_id=dict(contradiction_edges_by_claim_id),
        contradiction_edges_by_pair=contradiction_edges_by_pair,
        bounties_by_id=bounties_by_id,
        bounties_by_claim_id=dict(bounties_by_claim_id),
        bounties_by_state=dict(bounties_by_state),
        bounties_by_reward_type=dict(bounties_by_reward_type),
        graph_safety_issues=graph_safety_issues,
        graph_claim_ids=graph_claim_ids,
    )


def _claim_to_retrieved(
    claim: dict[str, Any],
    *,
    match_reasons: Iterable[MatchReason],
    matched_terms: Iterable[str],
    support_edge_ids: Iterable[str],
    contradiction_edge_ids: Iterable[str],
) -> RetrievedClaim:
    return RetrievedClaim(
        claim_id=claim["claim_id"],
        claim_type=claim["claim_type"],
        claim_label=claim["claim_label"],
        lifecycle=ClaimLifecycle(claim["lifecycle"]),
        source_observation_ids=list(claim.get("source_observation_ids", [])),
        source_evidence_ids=list(claim.get("source_evidence_ids", [])),
        source_observation_hashes=list(claim.get("source_observation_hashes", [])),
        support_edge_ids=sorted(dict.fromkeys(support_edge_ids)),
        contradiction_edge_ids=sorted(dict.fromkeys(contradiction_edge_ids)),
        match_reasons=sorted(dict.fromkeys(match_reasons), key=lambda item: item.value),
        matched_terms=sorted(dict.fromkeys(matched_terms)),
    )


def _term_match_claim_ids(indexes: ResolutionIndexes, lookup: ExactTermLookup) -> tuple[list[str], list[str], list[str]]:
    if lookup.artifact == "claims.jsonl":
        field = TERM_FIELD_ALIASES[lookup.artifact][lookup.field]
        if field == "claim_id":
            claim_ids = [claim_id for claim_id, claim in indexes.claims_by_id.items() if claim["claim_id"] == lookup.value]
        elif field == "claim_type":
            claim_ids = list(indexes.claims_by_type.get(lookup.value, []))
        elif field == "lifecycle":
            claim_ids = list(indexes.claims_by_lifecycle.get(lookup.value, []))
        else:
            claim_ids = []
        return sorted(dict.fromkeys(claim_ids)), [], [f"{lookup.artifact}.{lookup.field}={lookup.value}"]

    if lookup.artifact == "claim_graph.json":
        matched_claim_ids: list[str] = []
        matched_edge_ids: list[str] = []
        for edge in indexes.contradiction_edges_by_pair.values():
            if edge.get(TERM_FIELD_ALIASES[lookup.artifact][lookup.field]) == lookup.value:
                matched_edge_ids.append(edge["edge_id"])
                source = edge.get("source")
                target = edge.get("target")
                if isinstance(source, str) and source in indexes.claims_by_id:
                    matched_claim_ids.append(source)
                if isinstance(target, str) and target in indexes.claims_by_id:
                    matched_claim_ids.append(target)
        for claim_id, edges in indexes.support_edges_by_claim_id.items():
            for edge in edges:
                if edge.get(TERM_FIELD_ALIASES[lookup.artifact][lookup.field]) == lookup.value:
                    matched_edge_ids.append(edge["edge_id"])
                    matched_claim_ids.append(claim_id)
        return sorted(dict.fromkeys(matched_claim_ids)), sorted(dict.fromkeys(matched_edge_ids)), [f"{lookup.artifact}.{lookup.field}={lookup.value}"]

    matched_claim_ids = []
    matched_bounty_ids = []
    field = TERM_FIELD_ALIASES[lookup.artifact][lookup.field]
    if field == "bounty_id":
        bounty = indexes.bounties_by_id.get(lookup.value)
        if bounty:
            matched_bounty_ids.append(bounty["bounty_id"])
            matched_claim_ids.append(bounty["claim_id"])
    elif field == "claim_id":
        for bounty in indexes.bounties_by_claim_id.get(lookup.value, []):
            matched_bounty_ids.append(bounty["bounty_id"])
            matched_claim_ids.append(bounty["claim_id"])
    elif field == "status":
        for bounty in indexes.bounties_by_state.get(lookup.value, []):
            matched_bounty_ids.append(bounty["bounty_id"])
            matched_claim_ids.append(bounty["claim_id"])
    elif field == "claim_type":
        for bounty in indexes.bounties_by_reward_type.get(lookup.value, []):
            matched_bounty_ids.append(bounty["bounty_id"])
            matched_claim_ids.append(bounty["claim_id"])
    return sorted(dict.fromkeys(matched_claim_ids)), sorted(dict.fromkeys(matched_bounty_ids)), [f"{lookup.artifact}.{lookup.field}={lookup.value}"]


@dataclass(frozen=True)
class RetrievalOutcome:
    retrieved_claims: list[RetrievedClaim]
    matched_bounty_ids: list[str]
    matched_edge_ids: list[str]
    graph_safety_issues: list[GraphSafetyIssue]


def _retrieve_claims(question: ResolutionQuestion, indexes: ResolutionIndexes) -> RetrievalOutcome:
    claim_ids: list[str] = []
    matched_bounty_ids: list[str] = []
    matched_edge_ids: list[str] = []
    matched_terms: list[str] = []
    claim_reasons: dict[str, set[MatchReason]] = defaultdict(set)
    claim_terms: dict[str, set[str]] = defaultdict(set)
    claim_support_edges: dict[str, set[str]] = defaultdict(set)
    claim_contradiction_edges: dict[str, set[str]] = defaultdict(set)

    def add_claim(claim_id: str, reason: MatchReason, term: str | None = None) -> None:
        if claim_id not in indexes.claims_by_id:
            return
        claim_ids.append(claim_id)
        claim_reasons[claim_id].add(reason)
        if term is not None:
            claim_terms[claim_id].add(term)

    if question.query_mode == QueryMode.claim_id:
        for claim_id in question.exact_claim_ids:
            add_claim(claim_id, MatchReason.claim_id)
    elif question.query_mode == QueryMode.observation_id:
        for observation_id in question.exact_observation_ids:
            for claim_id in indexes.claims_by_observation_id.get(observation_id, []):
                add_claim(claim_id, MatchReason.observation_id)
    elif question.query_mode == QueryMode.evidence_id:
        for evidence_id in question.exact_evidence_ids:
            for claim_id in indexes.claims_by_evidence_id.get(evidence_id, []):
                add_claim(claim_id, MatchReason.evidence_id)
    elif question.query_mode == QueryMode.lifecycle:
        for lifecycle in question.exact_lifecycle_states:
            for claim_id in indexes.claims_by_lifecycle.get(lifecycle.value, []):
                add_claim(claim_id, MatchReason.lifecycle)
    elif question.query_mode == QueryMode.exact_term:
        for lookup in question.exact_term_lookups:
            claim_ids_for_lookup, edge_ids_for_lookup, terms_for_lookup = _term_match_claim_ids(indexes, lookup)
            matched_terms.extend(terms_for_lookup)
            matched_edge_ids.extend(edge_ids_for_lookup)
            for claim_id in claim_ids_for_lookup:
                add_claim(claim_id, MatchReason.term, terms_for_lookup[0])

    if not claim_ids:
        return RetrievalOutcome([], [], [], indexes.graph_safety_issues)

    unique_claim_ids = sorted(dict.fromkeys(claim_ids))
    retrieved_claims: list[RetrievedClaim] = []
    for claim_id in unique_claim_ids:
        claim = indexes.claims_by_id[claim_id]
        support_edge_ids = [edge["edge_id"] for edge in indexes.support_edges_by_claim_id.get(claim_id, [])]
        contradiction_edge_ids = [edge["edge_id"] for edge in indexes.contradiction_edges_by_claim_id.get(claim_id, [])]
        if claim_id in claim_reasons:
            if claim_id in indexes.support_edges_by_claim_id:
                claim_support_edges[claim_id].update(support_edge_ids)
            if claim_id in indexes.contradiction_edges_by_claim_id:
                claim_contradiction_edges[claim_id].update(contradiction_edge_ids)
        retrieved_claims.append(
            _claim_to_retrieved(
                claim,
                match_reasons=claim_reasons[claim_id],
                matched_terms=claim_terms[claim_id] or matched_terms,
                support_edge_ids=support_edge_ids,
                contradiction_edge_ids=contradiction_edge_ids,
            )
        )

    return RetrievalOutcome(
        retrieved_claims=sorted(retrieved_claims, key=lambda record: record.claim_id),
        matched_bounty_ids=sorted(dict.fromkeys(matched_bounty_ids)),
        matched_edge_ids=sorted(dict.fromkeys(matched_edge_ids)),
        graph_safety_issues=indexes.graph_safety_issues,
    )


def _conflict_reports(retrieved_claims: list[RetrievedClaim], indexes: ResolutionIndexes) -> list[ConflictReport]:
    claim_ids = {claim.claim_id for claim in retrieved_claims}
    reports: list[ConflictReport] = []
    seen_edge_ids: set[str] = set()
    for left_id in sorted(claim_ids):
        for edge in indexes.contradiction_edges_by_claim_id.get(left_id, []):
            edge_id = edge["edge_id"]
            if edge_id in seen_edge_ids:
                continue
            target = edge.get("target")
            if not isinstance(target, str) or target not in claim_ids:
                continue
            seen_edge_ids.add(edge_id)
            left = indexes.claims_by_id[left_id]
            right = indexes.claims_by_id[target]
            shared_evidence_ids = sorted(set(left.get("source_evidence_ids", [])).intersection(right.get("source_evidence_ids", [])))
            reports.append(
                ConflictReport(
                    conflict_id=stable_id(
                        "conflict",
                        {
                            "left_claim_id": left_id,
                            "right_claim_id": target,
                            "contradiction_edge_id": edge_id,
                        },
                    ),
                    left_claim_id=left_id,
                    right_claim_id=target,
                    shared_evidence_ids=shared_evidence_ids,
                    contradiction_edge_ids=[edge_id],
                    conflict_basis=ConflictBasis.explicit_contradiction_edge,
                    left_lifecycle=ClaimLifecycle(left["lifecycle"]),
                    right_lifecycle=ClaimLifecycle(right["lifecycle"]),
                )
            )
    return sorted(reports, key=lambda report: report.conflict_id)


def _relevant_issue_ids(question: ResolutionQuestion, retrieved_claim_ids: set[str], indexes: ResolutionIndexes) -> list[str]:
    relevant: list[str] = []
    for issue in indexes.graph_safety_issues:
        if issue.issue_type in {
            GraphSafetyIssueType.empty_inputs,
            GraphSafetyIssueType.missing_reference,
            GraphSafetyIssueType.malformed_entry,
            GraphSafetyIssueType.cyclic_reference,
        }:
            if issue.issue_type == GraphSafetyIssueType.empty_inputs:
                relevant.append(issue.issue_id)
                continue
            if retrieved_claim_ids.intersection(issue.source_ids):
                relevant.append(issue.issue_id)
        else:
            continue
    return sorted(dict.fromkeys(relevant))


def _open_bounties_for_claims(retrieved_claim_ids: set[str], indexes: ResolutionIndexes) -> list[dict[str, Any]]:
    bounties: list[dict[str, Any]] = []
    for claim_id in sorted(retrieved_claim_ids):
        for bounty in indexes.bounties_by_claim_id.get(claim_id, []):
            if bounty.get("status") == "open":
                bounties.append(bounty)
    return sorted(bounties, key=lambda record: record["bounty_id"])


def _confidence_score(
    *,
    supporting_claim_count: int,
    contested_claim_count: int,
    rejected_claim_count: int,
    open_bounty_count: int,
    missing_reference_count: int,
    resolution_state: ResolutionState,
) -> ConfidenceScore:
    if resolution_state in {ResolutionState.invalid_query, ResolutionState.unanswerable}:
        score = 0
    else:
        score = _clamp_score(
            50
            + 10 * supporting_claim_count
            - 20 * contested_claim_count
            - 30 * rejected_claim_count
            - 10 * open_bounty_count
            - 15 * missing_reference_count
        )
    return ConfidenceScore(
        formula_version="resolution-confidence-v1",
        score=score,
        supporting_claim_count=supporting_claim_count,
        contested_claim_count=contested_claim_count,
        rejected_claim_count=rejected_claim_count,
        open_bounty_count=open_bounty_count,
        missing_reference_count=missing_reference_count,
    )


def _select_resolution_state(
    question: ResolutionQuestion,
    retrieved_claims: list[RetrievedClaim],
    conflict_reports: list[ConflictReport],
    open_bounties: list[dict[str, Any]],
    missing_reference_ids: list[str],
) -> ResolutionState:
    if question.query_mode == QueryMode.unsupported or question.validation_errors:
        return ResolutionState.invalid_query
    if not retrieved_claims:
        return ResolutionState.unanswerable
    if missing_reference_ids:
        return ResolutionState.unanswerable
    if conflict_reports:
        return ResolutionState.conflicted

    supporting_claim_count = sum(1 for claim in retrieved_claims if claim.lifecycle == ClaimLifecycle.supported)
    contested_claim_count = sum(1 for claim in retrieved_claims if claim.lifecycle == ClaimLifecycle.contested)
    rejected_claim_count = sum(1 for claim in retrieved_claims if claim.lifecycle == ClaimLifecycle.rejected)
    if supporting_claim_count > 0 and contested_claim_count == 0 and rejected_claim_count == 0 and not open_bounties and not missing_reference_ids:
        return ResolutionState.supported
    return ResolutionState.insufficient_evidence


def _build_trace_steps(
    *,
    question: ResolutionQuestion,
    retrieval: RetrievalOutcome,
    conflict_reports: list[ConflictReport],
    open_bounties: list[dict[str, Any]],
    confidence: ConfidenceScore,
    resolution_state: ResolutionState,
    missing_reference_ids: list[str],
) -> list[TraceStep]:
    steps: list[TraceStep] = []
    steps.append(
        build_trace_step(
            TraceStepType.query_normalization,
            source_ids=[question.question_id],
            input_ids=[sha256_hex(question.raw_query)],
            output_ids=[question.question_id],
            detail_code="normalized_query",
            detail_message=f"normalized query mode={question.query_mode.value}",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.index_lookup,
            source_ids=[claim.claim_id for claim in retrieval.retrieved_claims] or [question.question_id],
            input_ids=[
                *question.exact_claim_ids,
                *question.exact_observation_ids,
                *question.exact_evidence_ids,
                *[lookup.value for lookup in question.exact_term_lookups],
            ],
            output_ids=[claim.claim_id for claim in retrieval.retrieved_claims],
            detail_code="index_lookup",
            detail_message="performed exact structural lookup",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.candidate_retrieval,
            source_ids=[claim.claim_id for claim in retrieval.retrieved_claims],
            input_ids=[question.question_id],
            output_ids=[claim.claim_id for claim in retrieval.retrieved_claims],
            detail_code="candidate_retrieval",
            detail_message=f"retrieved {len(retrieval.retrieved_claims)} candidate claims",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.graph_validation,
            source_ids=[issue.issue_id for issue in retrieval.graph_safety_issues] or [question.question_id],
            input_ids=[question.question_id],
            output_ids=[issue.issue_id for issue in retrieval.graph_safety_issues],
            detail_code="graph_validation",
            detail_message=f"graph safety issues={len(retrieval.graph_safety_issues)}",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.conflict_detection,
            source_ids=[report.conflict_id for report in conflict_reports] or [question.question_id],
            input_ids=[claim.claim_id for claim in retrieval.retrieved_claims],
            output_ids=[report.conflict_id for report in conflict_reports],
            detail_code="conflict_detection",
            detail_message=f"conflicts detected={len(conflict_reports)}",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.bounty_lookup,
            source_ids=[bounty["bounty_id"] for bounty in open_bounties] or [question.question_id],
            input_ids=[claim.claim_id for claim in retrieval.retrieved_claims],
            output_ids=[bounty["bounty_id"] for bounty in open_bounties],
            detail_code="bounty_lookup",
            detail_message=f"open bounties={len(open_bounties)}",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.confidence_calculation,
            source_ids=[claim.claim_id for claim in retrieval.retrieved_claims] + [bounty["bounty_id"] for bounty in open_bounties],
            input_ids=[question.question_id],
            output_ids=[str(confidence.score)],
            detail_code="confidence_calculation",
            detail_message=f"confidence score={confidence.score}",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.state_selection,
            source_ids=[question.question_id] + missing_reference_ids,
            input_ids=[question.question_id],
            output_ids=[resolution_state.value],
            detail_code="state_selection",
            detail_message=f"selected state={resolution_state.value}",
            question_id=question.question_id,
        )
    )
    steps.append(
        build_trace_step(
            TraceStepType.answer_assembly,
            source_ids=[question.question_id] + [claim.claim_id for claim in retrieval.retrieved_claims],
            input_ids=[question.question_id],
            output_ids=[resolution_state.value],
            detail_code="answer_assembly",
            detail_message="assembled deterministic answer and trace",
            question_id=question.question_id,
        )
    )
    return steps


def _build_result(
    *,
    question: ResolutionQuestion,
    indexes: ResolutionIndexes,
    retrieval: RetrievalOutcome,
) -> tuple[ResolutionAnswer, ResolutionTrace]:
    retrieved_claim_ids = [claim.claim_id for claim in retrieval.retrieved_claims]
    conflict_reports = _conflict_reports(retrieval.retrieved_claims, indexes)
    open_bounties = _open_bounties_for_claims(set(retrieved_claim_ids), indexes)
    supporting_claim_ids = [claim.claim_id for claim in retrieval.retrieved_claims if claim.lifecycle == ClaimLifecycle.supported]
    missing_reference_ids = _relevant_issue_ids(question, set(retrieved_claim_ids), indexes)
    resolution_state = _select_resolution_state(question, retrieval.retrieved_claims, conflict_reports, open_bounties, missing_reference_ids)
    confidence = _confidence_score(
        supporting_claim_count=len(supporting_claim_ids),
        contested_claim_count=sum(1 for claim in retrieval.retrieved_claims if claim.lifecycle == ClaimLifecycle.contested),
        rejected_claim_count=sum(1 for claim in retrieval.retrieved_claims if claim.lifecycle == ClaimLifecycle.rejected),
        open_bounty_count=len(open_bounties),
        missing_reference_count=len(missing_reference_ids),
        resolution_state=resolution_state,
    )
    trace_steps = _build_trace_steps(
        question=question,
        retrieval=retrieval,
        conflict_reports=conflict_reports,
        open_bounties=open_bounties,
        confidence=confidence,
        resolution_state=resolution_state,
        missing_reference_ids=missing_reference_ids,
    )
    answer = ResolutionAnswer(
        answer_id=stable_id(
            "resolution-answer",
            {
                "question_id": question.question_id,
                "resolution_state": resolution_state.value,
                "retrieved_claim_ids": retrieved_claim_ids,
                "conflict_report_ids": [report.conflict_id for report in conflict_reports],
                "supporting_claim_ids": supporting_claim_ids,
                "missing_reference_ids": missing_reference_ids,
                "open_bounty_ids": [bounty["bounty_id"] for bounty in open_bounties],
            },
        ),
        question=question,
        resolution_state=resolution_state,
        confidence=confidence,
        retrieved_claim_ids=retrieved_claim_ids,
        conflict_report_ids=[report.conflict_id for report in conflict_reports],
        supporting_claim_ids=supporting_claim_ids,
        missing_reference_ids=missing_reference_ids,
        open_bounty_ids=[bounty["bounty_id"] for bounty in open_bounties],
    )
    trace = ResolutionTrace(
        trace_id=stable_id(
            "resolution-trace",
            {
                "question_id": question.question_id,
                "resolution_state": resolution_state.value,
                "answer_id": answer.answer_id,
                "retrieved_claim_ids": retrieved_claim_ids,
                "conflict_report_ids": [report.conflict_id for report in conflict_reports],
                "open_bounty_ids": [bounty["bounty_id"] for bounty in open_bounties],
            },
        ),
        question=question,
        resolution_state=resolution_state,
        retrieved_claims=retrieval.retrieved_claims,
        conflict_reports=conflict_reports,
        confidence=confidence,
        trace_steps=trace_steps,
        input_artifact_hashes={},
        graph_safety_issues=retrieval.graph_safety_issues,
    )
    return answer, trace


def resolve_from_records(
    raw_query: str,
    *,
    claims: list[dict[str, Any]],
    claim_graph: dict[str, Any],
    bounties: list[dict[str, Any]],
) -> tuple[ResolutionAnswer, ResolutionTrace]:
    question = plan_resolution_question(raw_query)
    indexes = _build_indexes(claims, claim_graph, bounties)
    retrieval = _retrieve_claims(question, indexes)
    answer, trace = _build_result(question=question, indexes=indexes, retrieval=retrieval)
    return answer, trace


def resolve_query(
    raw_query: str,
    claims_path: str | Path,
    claim_graph_path: str | Path,
    bounties_path: str | Path,
) -> tuple[ResolutionAnswer, ResolutionTrace]:
    claims_path = Path(claims_path)
    claim_graph_path = Path(claim_graph_path)
    bounties_path = Path(bounties_path)
    claims = _load_claims(claims_path)
    graph = _load_graph(claim_graph_path)
    bounties = _load_bounties(bounties_path)
    answer, trace = resolve_from_records(raw_query, claims=claims, claim_graph=graph, bounties=bounties)
    trace = trace.model_copy(
        update={
            "input_artifact_hashes": {
                "claims.jsonl": _artifact_hash(claims_path),
                "claim_graph.json": _artifact_hash(claim_graph_path),
                "bounties.jsonl": _artifact_hash(bounties_path),
            }
        }
    )
    return answer, trace


def build_resolution_artifacts(
    raw_query: str,
    claims_path: str | Path,
    claim_graph_path: str | Path,
    bounties_path: str | Path,
    output_dir: str | Path,
) -> ResolutionResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    answer, trace = resolve_query(raw_query, claims_path, claim_graph_path, bounties_path)
    answer_path = output_dir / "answer.json"
    trace_path = output_dir / "resolution_trace.json"
    write_json(answer_path, answer.model_dump(mode="json"))
    write_json(trace_path, trace.model_dump(mode="json"))
    return ResolutionResult(answer_path=answer_path, trace_path=trace_path, answer=answer, trace=trace)
