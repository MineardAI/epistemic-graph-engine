# Contract 003 — Evidence Resolution Engine

You are implementing **Contract 003** of the IBOS architecture.

Contracts 001 and 002 already exist and are considered complete.

Your task is to build the **Evidence Resolution Engine**.

## Purpose

This contract answers questions using existing artifacts.

It does not create new evidence.

It does not create new observations.

It does not create new claims.

It evaluates what can be concluded from the existing knowledge graph.

---

## Inputs

Use the artifacts produced by previous contracts.

* claims
* claim graph
* bounties

These are read-only inputs.

---

## Outputs

Generate a structured answer for a user question.

Also generate a complete execution trace showing how the answer was reached.

The trace should allow another engineer to follow every decision made by the engine.

---

## Responsibilities

Build:

* query normalization
* claim retrieval
* conflict detection
* confidence calculation
* resolution classification
* answer assembly
* execution tracing

---

## Resolution States

Implement canonical resolution states appropriate for evidence-backed reasoning.

The engine should distinguish between situations where evidence supports a conclusion, conflicts with itself, is missing, or cannot answer the question.

---

## Principles

The engine should:

* remain read-only
* be deterministic
* operate only on existing artifacts
* preserve traceability
* expose uncertainty instead of hiding it
* prefer evidence over narrative

If multiple claims conflict, report the conflict rather than attempting to resolve it through inference.

If supporting information is missing, identify the gap.

If the available artifacts cannot answer the question, report that outcome explicitly.

---

## Deliverables

Implement the complete Contract 003 module including:

* schemas
* retrieval
* classifier
* confidence calculation
* resolver
* execution trace
* unit tests

Follow the architecture established by Contracts 001 and 002.

Do not redesign earlier contracts unless required to resolve an actual implementation incompatibility, and document any such incompatibility before changing it.
