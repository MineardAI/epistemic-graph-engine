You are working in a fresh repository.

Project:
Epistemic Graph v0 — a deterministic ingestion engine for exported ChatGPT conversations and other future evidence sources.

Goal:
Build Contract 001: Epistemic Graph Ingestion.

This contract must create an auditable foundation for later cognitive timeline, project reconstruction, evidence resolution, and claim analysis. Do not generate claims yet. Do not summarize. Do not infer psychology. Do not build UI. This is only the ingestion foundation.

Core Architecture:
Raw Archive
→ evidence.jsonl
→ observations.jsonl
→ enriched_observations.jsonl
→ manifest.json

Hard rule:
Pass 1 and Pass 2 are deterministic and immutable.
Pass 3 is optional, probabilistic, and must never mutate evidence.jsonl or observations.jsonl.

Phase 0 — Repo Setup
Create a small Python package with:

* pyproject.toml
* README.md
* epistemic_graph/
* epistemic_graph/ingest.py
* epistemic_graph/schemas.py
* epistemic_graph/hash_utils.py
* tests/test_ingestion.py
* tests/fixtures/sample_conversations.json

Use pytest.

Phase 1 — Deterministic Evidence Parser
Input:
A ChatGPT conversations.json export.

Parse:

* top-level conversation metadata
* conversation_id
* title
* create_time
* update_time
* mapping tree
* node id
* parent id
* children ids
* message payload
* author role/name
* create_time/update_time
* content_type
* content parts
* metadata
* attachments
* tool messages
* hidden/system messages

Output:
evidence.jsonl

Each EvidenceNode must include:

* evidence_id
* source_hash
* raw_pointer
* redacted_preview
* metadata.conversation_id
* metadata.node_id
* metadata.parent_id
* metadata.children_ids
* metadata.timestamp
* metadata.actor
* metadata.content_type
* metadata.is_visible_to_user
* metadata.attachments
* metadata.tool_name if present
* metadata.message_status
* metadata.model_slug if present

Rules:

* Do not embed full raw payload in evidence.jsonl.
* Store only pointer, hash, preview, and metadata.
* raw_pointer must include conversation and node scope, e.g.
  raw/conversations.json#conversation.<conversation_id>.mapping.<node_id>
* Use stable hash serialization: json.dumps(..., sort_keys=True, ensure_ascii=False)
* Evidence IDs must be stable and safe even if conversation IDs or node IDs contain underscores.
* Prefer hash-based IDs or slug-safe IDs.

Phase 2 — Deterministic Observation Extractor
Input:
EvidenceNodes + referenced raw message text.

Output:
observations.jsonl

Each ObservationNode must include:

* observation_id
* source_evidence_id
* timestamp
* actor
* event_type
* introduced_terms
* literal_phrases
* actions
* references
* quote_pointer
* quote_hash
* redacted_quote
* hashes.source_hash
* hashes.observation_hash

Rules:

* No claims.
* No summaries.
* No psychology.
* No causality.
* No “this means.”
* Extract literal phrases before concepts.
* Treat naming as its own event_type.
* Separate user seed from assistant expansion.
* Preserve system/tool/hidden messages with visibility metadata.
* Branches must be preserved, not flattened.
* If a message has multiple children, preserve all children in topology.
* Minimal literal extraction is acceptable for v0, but tests must document it.

Event types for v0:

* statement
* question
* proposal
* naming
* correction
* attachment
* tool_event
* system_event
* implementation
* unknown

Phase 3 — Optional Enrichment Overlay
Create enriched_observations.jsonl as a separate overlay.

Each EnrichedObservation must include:

* enrichment_id
* target_observation_id
* target_observation_hash
* surface_domain
* concepts
* certainty_markers
* expansion_markers
* generated_at
* enrichment_engine
* enrichment_version

Hard rule:
This pass must never modify evidence.jsonl or observations.jsonl.
Tests must prove the base observation hash remains unchanged after enrichment.

Phase 4 — Manifest Compiler
Create manifest.json with:

* schema_version
* generated_at
* input_archive_hash
* evidence_jsonl_hash
* observations_jsonl_hash
* enriched_observations_jsonl_hash if generated
* total_conversations
* total_evidence_nodes
* total_observations
* total_enriched_observations
* topology summary
* root evidence nodes
* branch counts
* hidden/system/tool message counts

Phase 5 — Tests
Create pytest coverage for:

1. Evidence parsing from a sample ChatGPT export.
2. Stable source_hash generation.
3. Parent/child topology preservation.
4. Hidden system message preservation.
5. Assistant/user/tool/system actor parsing.
6. Attachment metadata preservation.
7. Naming detection from quoted capitalized terms.
8. Observation hash stability.
9. Pass 3 enrichment cannot mutate evidence or observations.
10. Manifest counts and hashes are stable.

Fixture must include:

* user seed message
* assistant naming message
* assistant expansion message
* hidden system message
* tool message
* attachment metadata
* branching children

Done Criteria:

* python -m pytest -q passes
* evidence.jsonl generated
* observations.jsonl generated
* enriched_observations.jsonl generated only when explicitly requested
* manifest.json generated
* no claims layer
* no summaries
* no therapy/psychology inference
* no UI
* no Epistemic Graph Engine runtime
* no provider code
* README explains the three-pass architecture and immutability rules

Important:
This is Contract 001 only. Do not build Contract 002 yet.
Contract 002 will later handle Observation Querying and Claim Generation.
