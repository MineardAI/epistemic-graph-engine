from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class EvidenceMetadata(TypedDict, total=False):
    conversation_id: str | None
    node_id: str
    parent_id: str | None
    children_ids: list[str]
    timestamp: float | int | None
    actor: str | None
    content_type: str | None
    is_visible_to_user: bool
    attachments: list[dict[str, Any]]
    tool_name: str | None
    message_status: str | None
    model_slug: str | None


class EvidenceNode(TypedDict):
    evidence_id: str
    source_hash: str
    raw_pointer: str
    redacted_preview: str
    metadata: EvidenceMetadata


class ObservationHashes(TypedDict):
    source_hash: str
    observation_hash: str


class ObservationNode(TypedDict):
    observation_id: str
    source_evidence_id: str
    timestamp: float | int | None
    actor: str | None
    event_type: str
    introduced_terms: list[str]
    literal_phrases: list[str]
    actions: list[str]
    references: list[str]
    quote_pointer: str
    quote_hash: str
    redacted_quote: str
    hashes: ObservationHashes


class Manifest(TypedDict, total=False):
    schema_version: str
    generated_at: str
    input_archive_hash: str
    evidence_jsonl_hash: str
    observations_jsonl_hash: str
    enriched_observations_jsonl_hash: NotRequired[str | None]
    total_conversations: int
    total_evidence_nodes: int
    total_observations: int
    topology_summary: dict[str, Any]
    root_evidence_nodes: list[str]
    branch_counts: dict[str, int]
    message_counts: dict[str, int]

