# Contract 002 — Claim Layer (v1)

## Objective

Implement the **Claim Layer** on top of the completed Contract 001 ingestion pipeline.

This contract creates the first interpretive layer while preserving the immutability of the evidence foundation.

Contract 001 is frozen.

Nothing in this contract may modify, regenerate, rewrite, or reinterpret Contract 001 outputs.

---

# Repository Law

The following artifacts are immutable inputs:

* evidence.jsonl
* observations.jsonl
* enriched_observations.jsonl (optional)

These files are read-only.

Contract 002 may only create new derived artifacts.

---

# Purpose

The Claim Layer converts immutable observations into structured claims.

Claims are **projections**, not facts.

Claims are disposable.

Claims are completely regenerable.

Deleting every claim artifact and rebuilding from the same observations must produce identical results.

---

# Architectural Rules

## Rule 1

Evidence is the only source of truth.

Claims never become evidence.

---

## Rule 2

Observations are immutable.

Claims may reference observations.

Claims may never modify observations.

---

## Rule 3

Every claim must reference one or more observation IDs.

No orphan claims are permitted.

---

## Rule 4

Claims never reference raw archive text.

Claims reference:

* observation_id
* evidence_id (through observations)

only.

---

## Rule 5

Claims never infer:

* psychology
* intent
* motivation
* causation
* emotional state
* authorship
* ownership

unless explicitly represented by observations.

---

## Rule 6

Contradiction detection must remain deterministic.

No LLM reasoning.

No semantic debate.

Only structural relationships derived from observations.

---

## Rule 7

Hypotheses exist only inside Claim objects.

Hypotheses never fork the global timeline.

Maximum hypotheses per claim:

5

---

## Rule 8

Claims are regenerable.

Delete:

* claims.jsonl
* claim_graph.json
* bounties.jsonl

Rebuild.

Outputs must be deterministic.

---

# Deliverables

Create a new package:

```text
epistemic_graph/claims/
```

containing:

```text
schema.py
builder.py
graph.py
query.py
bounties.py
lifecycle.py
```

Create tests:

```text
tests/
    test_claim_builder.py
    test_claim_graph.py
    test_claim_query.py
    test_claim_lifecycle.py
    test_claim_regeneration.py
    test_claim_immutability.py
```

---

# Schema

Implement strongly typed Pydantic v2 models.

Minimum models:

* Claim
* Hypothesis
* Bounty

Use Enums (or Literal types) for lifecycle states.

Reject unknown fields.

No free-form status strings.

---

# Claim Lifecycle

Implement explicit lifecycle states.

Suggested:

* proposed
* provisional
* supported
* contested
* resolved
* rejected
* archived

Lifecycle transitions must be explicit and testable.

---

# Claim Builder

Implement deterministic claim generation.

Builder reads:

observations.jsonl

optionally

enriched_observations.jsonl

Builder writes:

claims.jsonl

Builder must never modify its inputs.

Builder version should be embedded in every claim.

---

# Graph Compiler

Compile:

claim_graph.json

Graph is derived only.

Never authoritative.

Graph compiler must not alter claims.

---

# Query Engine

Read-only.

No mutation APIs.

Provide functions such as:

* find claims
* unresolved claims
* supporting observations
* contradictory observations
* hypotheses
* active bounties

---

# Bounties

Generate evidence requests for unresolved claims.

Bounties must describe:

* missing evidence
* affected claim
* expected source types
* potential resolution impact

Bounties are also derived artifacts.

---

# Verification Requirements

The following must be proven by automated tests.

## 1

evidence.jsonl hash unchanged

before build

after build

---

## 2

observations.jsonl hash unchanged

before build

after build

---

## 3

enriched_observations.jsonl hash unchanged

before build

after build

(if present)

---

## 4

claims.jsonl is deterministic.

Delete.

Rebuild.

Hashes must match.

---

## 5

claim_graph.json is deterministic.

Delete.

Rebuild.

Hashes must match.

---

## 6

Every claim references one or more observation IDs.

---

## 7

No claim contains embedded raw conversation text.

---

## 8

No claim modifies timestamps.

---

## 9

No claim modifies evidence IDs.

---

## 10

All pytest tests pass.

---

# Engineering Constraints

Python 3.12

Pydantic v2

Full typing

No placeholder code

No TODO comments

No mock providers

No global mutable state

Small cohesive modules

Follow existing repository conventions.

---

# Definition of Done

Contract 002 is complete only when:

* all derived artifacts are generated
* all regeneration tests pass
* all immutability tests pass
* all lifecycle tests pass
* all graph tests pass
* all query tests pass

Contract 001 remains byte-for-byte unchanged.

Only then may Contract 002 be considered **Verified**.
