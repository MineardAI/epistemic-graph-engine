# Contract 003 Implementation Spec
## Evidence Resolution Engine

## Scope

Contract 003 is a deterministic, read-only evidence resolution layer.

It consumes only frozen outputs from Contracts 001 and 002:

- `claims.jsonl`
- `claim_graph.json`
- `bounties.jsonl`

It must not reopen `conversations.json`.
It must not create evidence, observations, claims, or downstream artifacts.

## Public Entry Point

The public engine accepts a raw query string.

Callers do not pass pre-normalized `ResolutionQuestion` objects.

The planner owns:

- trimming whitespace
- collapsing internal whitespace
- detecting query mode
- validating exact lookup fields
- generating deterministic `question_id`
- producing `invalid_query` when query shape is unsupported

## Outputs

Contract 003 emits exactly two files:

- `answer.json`
- `resolution_trace.json`

No additional artifacts are required.

## Schemas

All models use Pydantic v2 with `extra="forbid"` and explicit enums/literals.

### `ResolutionState`

Canonical states:

- `supported`
- `conflicted`
- `insufficient_evidence`
- `unanswerable`
- `invalid_query`

### `QueryMode`

Allowed modes:

- `claim_id`
- `observation_id`
- `evidence_id`
- `lifecycle`
- `exact_term`
- `unsupported`

### `TraceStepType`

Allowed step types:

- `query_normalization`
- `index_lookup`
- `candidate_retrieval`
- `graph_validation`
- `conflict_detection`
- `bounty_lookup`
- `confidence_calculation`
- `state_selection`
- `answer_assembly`
- `graph_safety`

### `MatchReason`

Allowed reasons:

- `claim_id`
- `observation_id`
- `evidence_id`
- `lifecycle`
- `term`

### `ConflictBasis`

Allowed basis:

- `explicit_contradiction_edge`

### `ResolutionQuestion`

Required fields:

- `question_id`
- `raw_query`
- `normalized_query`
- `query_mode`
- `exact_claim_ids`
- `exact_observation_ids`
- `exact_evidence_ids`
- `exact_lifecycle_states`
- `exact_term_lookups`
- `validation_errors`

`exact_term_lookups` is a list of structured exact-term requests.

### `ExactTermLookup`

Required fields:

- `artifact`
- `field`
- `value`

Allowed artifacts:

- `claims.jsonl`
- `claim_graph.json`
- `bounties.jsonl`

Allowed field whitelist:

For `claims.jsonl`:

- `id`
- `type`
- `state`

For `claim_graph.json`:

- `source_id`
- `target_id`
- `edge_type`

For `bounties.jsonl`:

- `id`
- `claim_id`
- `state`
- `reward_type`

`reward_type` is a deterministic alias for the bounty's structural reward classification and is resolved against the existing bounty record fields only.

Any query that targets a field outside this whitelist must resolve to `invalid_query`.

### `RetrievedClaim`

Required fields:

- `claim_id`
- `claim_type`
- `claim_label`
- `lifecycle`
- `source_observation_ids`
- `source_evidence_ids`
- `source_observation_hashes`
- `support_edge_ids`
- `contradiction_edge_ids`
- `match_reasons`
- `matched_terms`

### `ConflictReport`

Required fields:

- `conflict_id`
- `left_claim_id`
- `right_claim_id`
- `shared_evidence_ids`
- `contradiction_edge_ids`
- `conflict_basis`
- `left_lifecycle`
- `right_lifecycle`

### `ConfidenceScore`

Required fields:

- `formula_version`
- `score`
- `supporting_claim_count`
- `contested_claim_count`
- `rejected_claim_count`
- `open_bounty_count`
- `missing_reference_count`

Confidence formula:

```
raw = 50
raw += 10 * supporting_claim_count
raw -= 20 * contested_claim_count
raw -= 30 * rejected_claim_count
raw -= 10 * open_bounty_count
raw -= 15 * missing_reference_count
score = clamp(raw, 0, 100)
```

If the resolution state is `invalid_query` or `unanswerable`, score must be `0`.

### `TraceStep`

Required fields:

- `step_id`
- `step_type`
- `source_ids`
- `input_ids`
- `output_ids`
- `detail_code`
- `detail_message`

Every trace step must reference source IDs.

### `ResolutionTrace`

Required fields:

- `trace_id`
- `question`
- `resolution_state`
- `retrieved_claims`
- `conflict_reports`
- `confidence`
- `trace_steps`
- `input_artifact_hashes`
- `graph_safety_issues`

### `ResolutionAnswer`

Required fields:

- `answer_id`
- `question`
- `resolution_state`
- `confidence`
- `retrieved_claim_ids`
- `conflict_report_ids`
- `supporting_claim_ids`
- `missing_reference_ids`
- `open_bounty_ids`

## Resolution State Criteria

State precedence:

1. `invalid_query`
2. `unanswerable`
3. `conflicted`
4. `insufficient_evidence`
5. `supported`

Criteria:

- `invalid_query`
  - empty normalized query
  - malformed query syntax
  - unsupported query mode
  - attempts to query non-whitelisted fields
- `unanswerable`
  - structurally valid query with no exact match
  - empty input artifacts
  - graph corruption after safety filtering
  - missing references that prevent a supported answer
  - cyclic or malformed graph structure that leaves no valid resolvable path
- `conflicted`
  - at least one explicit contradiction edge exists among retrieved claims
- `insufficient_evidence`
  - retrieved claims exist, but support is incomplete or open bounties / missing references remain
- `supported`
  - retrieved claims exist
  - at least one supporting claim exists
  - no conflicts exist
  - no required references are missing
  - no open bounties remain for the answer set

## Query Syntax

The planner accepts these raw query forms:

- `claim:<claim_id>`
- `observation:<observation_id>`
- `evidence:<evidence_id>`
- `lifecycle:<state>`
- `term:<artifact>.<field>=<value>`

Whitespace may surround the separators and is normalized away.

No semantic matching is allowed.
No fuzzy matching is allowed.
No embeddings are allowed.

## Retrieval Rules

Retrieval is exact-match only.

Allowed exact lookup targets:

- claim IDs
- observation IDs
- evidence IDs
- lifecycle states
- exact structured term lookups on the whitelisted fields above

If the query is structurally valid but yields no exact match, the state is `unanswerable`.

## Conflict Rules

Conflict detection is structural only.

Only explicit contradiction edges from `claim_graph.json` may create a conflict report.

No semantic contradiction inference is allowed.

## Graph Safety

Deterministic handling is required for:

- missing references
- duplicate references
- malformed graph entries
- empty input artifacts
- cyclic graph references

Cycles must be detected using a deterministic visited / recursion-stack strategy.
No infinite traversal is allowed.

Malformed graph data must be recorded in the trace as a graph-safety issue.

## Complexity Bound

Resolution must be linear or log-linear relative to claim and edge count.

Expected complexity:

- index construction: `O(C + E + B)`
- lookup: `O(1)` or `O(log n)` per exact match type
- trace generation: linear in the size of the retrieved subgraph

No all-pairs claim comparison is allowed.

## Serialization

All Contract 003 outputs must reuse the canonical JSON helpers established by Contract 001.

Required behavior:

- UTF-8
- LF newlines
- sorted keys
- `ensure_ascii=False`
- compact separators

## Non-Goals

Contract 003 must not:

- create evidence
- create observations
- create claims
- mutate Contract 001 artifacts
- mutate Contract 002 artifacts
- perform semantic search
- use embeddings
- use LLM reasoning
- add UI, agents, or publishing logic
- implement Contract 004 or Contract 005 behavior
