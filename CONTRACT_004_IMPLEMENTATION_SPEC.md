# Contract 004 Implementation Spec
## Timeline and Concept Reconstruction

## Scope

Contract 004 is a deterministic, read-only timeline reconstruction layer.

It consumes only frozen outputs from Contracts 001, 002, and 003:

- `observations.jsonl`
- `claims.jsonl`
- `bounties.jsonl`
- `answer.json`
- `resolution_trace.json`

It must not reopen `conversations.json`.
It must not create evidence, observations, claims, answers, or publishing artifacts.
It must not infer meaning beyond source-backed structure.

## Output Artifacts

Contract 004 emits exactly these artifacts:

- `timeline_events.jsonl`
- `concept_timeline.json`
- `concept_maturity.json`
- `gap_windows.jsonl`
- `timeline_report.md`

`phase_map.json` is omitted for v0.

Reason:
- Contract 004 does not require it.
- Optional artifacts increase freeze surface.
- Concept maturity is represented by `concept_maturity.json`.

## Serialization

All Contract 004 JSON outputs must reuse the canonical JSON helpers established by Contract 001.

Required behavior:
- UTF-8
- LF newlines
- sorted keys
- `ensure_ascii=False`
- compact separators

## Schema Rules

All schema models use Pydantic v2 with `extra="forbid"`.

Unknown fields must be rejected.

No unvalidated metadata bags are allowed.

## Core Types

### TimelineEvent

Required fields:
- `event_id`
- `timestamp`
- `concept`
- `source_observation_id`
- `source_evidence_id`
- `action_type`

### ConceptTimelineEntry

Required fields:
- `concept`
- `first_timestamp`
- `latest_timestamp`
- `total_occurrences`
- `supporting_observation_ids`
- `supporting_claim_ids`
- `supporting_bounty_ids`

### ConceptMaturityEntry

Required fields:
- `concept`
- `maturity_state`
- `state_reason`
- `supporting_source_ids`
- `supporting_observation_ids`
- `supporting_claim_ids`

### GapWindow

Required fields:
- `start_timestamp`
- `end_timestamp`
- `duration`
- `previous_observation`
- `next_observation`

### TimelineReport

Required sections only:
- `Concept Summary`
- `Chronological Events`
- `Maturity Summary`
- `Detected Gap Windows`
- `Outstanding Bounties`
- `Skipped Sources`

## Concept Derivation Rule

A `concept` is any exact string value already emitted in a structured upstream field.

Contract 004 must never inspect raw message bodies, apply regex to prose, infer themes, or invent new topics.

The concept universe is the union of only these fields:

- `observations.jsonl.introduced_terms`
- `observations.jsonl.references`
- `observations.jsonl.event_type`
- `observations.jsonl.actor`
- `claims.jsonl.claim_type`
- `claims.jsonl.claim_label`
- `bounties.jsonl.claim_type`
- `bounties.jsonl.expected_source_types`

A concept key is the exact stored string after the same conservative normalization already used by the upstream artifact that produced it.

Do not add new normalization in Contract 004 unless Contract 004 explicitly requires it.

If a value is not already present in one of those structured fields, it is not a concept.

Treat concept values as opaque identifiers.

## Event Generation Granularity

Generate one timeline event per qualifying concept occurrence.

A qualifying concept occurrence is:
- one whitelisted concept value appearing in one upstream artifact record
- with a traceable source observation ID and source evidence ID

No synthetic multi-event chapters.
No narrative milestones.
No merged inferred events.

Every `timeline_events.jsonl` record must include:
- `event_id`
- `timestamp`
- `concept`
- `source_observation_id`
- `source_evidence_id`
- `action_type`

If a claim or bounty produces a concept but cannot be traced back to a source observation ID and source evidence ID, skip it and record the skip deterministically in the report/test path.

`TimelineEvent.timestamp` is required and non-null.

If an upstream record has a missing, malformed, or non-sortable timestamp, skip timeline event emission for that record.

Do not emit `timestamp = null`.

## Timestamp Ordering

Deterministic ordering is:

1. valid timestamp, ascending
2. artifact priority:
   - `observations.jsonl`
   - `claims.jsonl`
   - `bounties.jsonl`
3. source observation ID
4. source evidence ID
5. concept string
6. event ID

Missing or malformed timestamps:
- do not fabricate timestamps
- skip timeline event emission for that record
- record the skipped source ID in the relevant report/test path

Prefer preserving auditability over forcing chronology.

`DEFAULT_GAP_WINDOW_DAYS = 30`

A gap exists only when the duration between consecutive valid observation timestamps is strictly greater than 30 days.

No runtime-configurable threshold is allowed for v0.

## Maturity Promotion Rules

Maturity promotion must be deterministic and source-backed only.

Allowed states:
- `Mention`
- `Theme`
- `Metaphor`
- `Project`
- `Component`
- `Specification`
- `Implementation`
- `Verified`
- `Dormant`
- `Abandoned`

Rules:
- `Mention`: first valid occurrence of a concept.
- `Theme`: three or more valid occurrences across at least three distinct timestamps.
- `Dormant`: previous valid activity exists and the concept's latest valid activity is more than `DEFAULT_GAP_WINDOW_DAYS` before the global latest valid observation timestamp.
- All other states may be assigned only if explicit structured upstream evidence already supports them.
- Do not infer `Metaphor`, `Project`, `Component`, `Specification`, `Implementation`, `Verified`, or `Abandoned` from loose text.
- All state transitions must be reproducible from the same input artifacts.

## Gap Detection

Gap detection is computed over ordered observations only.

Use observation timestamps only.

Gap output fields:
- `start_timestamp`
- `end_timestamp`
- `duration`
- `previous_observation`
- `next_observation`

Never fill gaps with speculation.

## Report Rules

`timeline_report.md` must use a strict deterministic markdown template.

Allowed sections only:
- `Concept Summary`
- `Chronological Events`
- `Maturity Summary`
- `Detected Gap Windows`
- `Outstanding Bounties`

No narrative paragraphs.
Tables only.
Every row must include source IDs where applicable.
Empty sections must render as deterministic empty markdown tables.
Stable column order is required for every table.
Every report table must be sorted deterministically by:
1. timestamp, if present
2. concept
3. source_observation_id
4. source_evidence_id
5. event_id or stable row ID
No unsupported claims.
No prose conclusions.

`Skipped Sources` must always render a deterministic table with columns:

| Source Artifact | Record ID | Reason | Observation ID | Evidence ID |
| --- | --- | --- | --- | --- |

If no rows were skipped, the table must contain only the header and separator rows.
Skipped rows must be ordered deterministically using the same artifact-priority discipline as the timeline compiler.

## Determinism

Given identical inputs, outputs must be byte-identical.

Chronological ordering must depend only on timestamps and the pinned tie-breakers above.
Never depend on filesystem ordering.
Never depend on dictionary insertion order.
Never depend on wall-clock time.

## Non-Goals

Contract 004 must not:
- create evidence
- create observations
- create claims
- create answers
- mutate upstream artifacts
- infer concepts beyond the pinned whitelist
- perform semantic reasoning
- use LLMs
- use embeddings
- add UI, agents, or publishing logic
- implement Contract 005 behavior
