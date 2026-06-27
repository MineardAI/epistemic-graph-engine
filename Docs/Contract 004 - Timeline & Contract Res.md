# Contract 004 — Timeline & Concept Reconstruction (v0)

You are implementing **Contract 004** of the Epistemic Graph architecture.

Assume **no prior knowledge** beyond this prompt.

Your task is to build a **deterministic, read-only timeline reconstruction layer**.

This contract reconstructs **how concepts evolve over time** from previously generated artifacts.

It does **not** generate evidence, observations, claims, or resolutions.

It only produces chronological projections.

---

# Existing Contracts

## Contract 001 (already complete)

Produces immutable:

* evidence.jsonl
* observations.jsonl
* enriched_observations.jsonl (optional)

These files are read-only.

Never modify them.

---

## Contract 002 (already complete)

Produces derived:

* claims.jsonl
* bounties.jsonl
* claim_graph.json

These are also read-only inputs for this contract.

---

## Contract 003 (already complete)

Produces evidence-backed answers from claims.

This contract MUST NOT duplicate Contract 003.

---

# Purpose

Build a deterministic temporal reconstruction engine.

Questions this contract answers include:

* When did a concept first appear?
* How often did it appear?
* When did it mature?
* When did it become a project?
* When did it become a specification?
* Where are the gaps in the archive?
* Which concepts became dormant?

The engine must answer these using timestamps and existing artifacts only.

Never infer motivation.

Never infer psychology.

Never infer intent.

Never diagnose.

---

# Inputs

Read only:

* observations.jsonl
* claims.jsonl
* bounties.jsonl

Do not modify any input.

---

# Outputs

Generate only:

* timeline_events.jsonl
* concept_timeline.json
* concept_maturity.json
* gap_windows.jsonl
* timeline_report.md

Optionally:

* phase_map.json

If implemented, every phase must default to:

status = "proposed"

Never present phases as factual unless explicitly supported.

---

# Repository Layout

Create:

epistemic_graph/
timeline/
**init**.py
schemas.py
tracker.py
maturity.py
compiler.py

tests/
test_timeline.py
test_gap_detection.py
test_maturity.py

---

# Timeline Events

Timeline events are chronological records.

Each event references existing artifacts.

Every event must include:

* event_id
* timestamp
* concept
* source_observation_id
* source_evidence_id
* action_type

Examples:

introduced

reintroduced

implemented

specified

verified

No narrative descriptions beyond what is supported.

---

# Concept Timeline

For every concept build:

* first appearance
* latest appearance
* total occurrences
* supporting observations
* supporting claims

Everything must reference source IDs.

---

# Concept Maturity

Implement a deterministic finite state machine.

Allowed states:

Mention

Theme

Metaphor

Project

Component

Specification

Implementation

Verified

Dormant

Abandoned

---

# Promotion Rules

Promotion MUST be evidence-gated.

Examples:

Mention

First occurrence.

Theme

Three or more observations across separate timestamps.

Metaphor

Requires explicit metaphor or analogy evidence.

Do not infer.

Project

Requires explicit project evidence.

Examples include:

repository

workspace

folder

project declaration

configuration

Do not promote merely because a claim contains the word "project."

Component

Requires explicit structural component evidence.

Specification

Requires specification documents, schemas, interfaces, or structured definitions.

Implementation

Requires implementation evidence such as code artifacts or implementation claims.

Verified

Requires explicit verification evidence.

Examples:

tests passed

validation completed

integration confirmed

Dormant

Must NOT occur immediately.

Requires:

* previous activity
* no activity for a configurable inactivity window

Abandoned

Never infer.

Requires explicit archival, deprecation, removal, or abandonment evidence.

---

# Gap Detection

Implement chronological gap detection.

Input:

ordered observations

Output:

gap_windows.jsonl

Each gap contains:

* start timestamp
* end timestamp
* duration
* previous observation
* next observation

Never fill gaps with speculation.

---

# Timeline Report

Generate:

timeline_report.md

Include only:

Concept Summary

Chronological Events

Maturity Summary

Detected Gap Windows

Outstanding Bounties

Every statement must reference existing IDs.

No narrative summaries.

No interpretation.

No psychology.

---

# Determinism

Given identical inputs:

Outputs must be byte-identical.

Chronological ordering must depend only on timestamps.

Never depend on file ordering.

---

# Testing

Write pytest coverage for:

chronological ordering

stable sorting

gap detection

maturity promotion

dormant detection

report generation

deterministic regeneration

Tests must verify identical output across repeated executions.

---

# Implementation Constraints

Do not use LLMs.

Do not perform semantic reasoning.

Do not introduce embeddings.

Do not infer concepts beyond existing artifacts.

This contract is entirely rule-based.

---

# Success Criteria

Contract 004 is complete when:

* timeline events are generated deterministically
* concept timelines are reproducible
* maturity transitions follow explicit rules
* gap windows are detected correctly
* reports contain only source-backed chronology
* repeated executions produce identical outputs
* all tests pass

If an implementation decision is ambiguous, prefer the most conservative interpretation and preserve auditability over convenience.
