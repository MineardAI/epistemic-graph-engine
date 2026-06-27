# Epistemic Graph Engine

**Turn ChatGPT conversation history into a deterministic, auditable knowledge graph.**

The Epistemic Graph Engine ingests exported conversations and produces structured, traceable artifacts: evidence, claims, resolutions, timelines, and verifiable packages, without LLM reasoning, summaries, or invented conclusions.

Everything is regenerable from the same input and fully traceable to source IDs.

## What It Answers

- What claims does the evidence actually support?
- Where are contradictions or gaps?
- When did concepts appear, mature, or go dormant?
- What is unresolved?
- What can be confidently concluded?

It does not infer psychology, intent, causation, or narrative.

## Quick Start

1. Export data

   Download your ChatGPT `conversations.json` from OpenAI.

2. Install

   ```bash
   git clone https://github.com/MineardAI/epistemic-graph-engine.git
   cd epistemic-graph-engine
   pip install -e .
   ```

3. Run the full pipeline

   ```bash
   # Ingest (Contract 001)
   python -m epistemic_graph.ingest path/to/conversations.json

   # Claims (002), Resolution (003), Timeline (004), Publishing (005)
   # Run individual modules or use the top-level pipeline runner if available.
   ```

4. Ask questions

   Use exact IDs or whitelisted terms for best results. Broad queries correctly return low confidence.

5. Export

   Generate sealed audit, executive, and research packages with manifests.

## Core Principles

- Deterministic: Delete derived artifacts and rerun them to get identical byte-for-byte outputs.
- Read-only layers: Each contract consumes prior artifacts without mutation.
- Traceability: Every answer includes a full execution trace with source references.
- Honest confidence: Zero or low scores mean insufficient structured evidence, not a failure.
- No magic: No semantic search, embeddings, intent inference, or narrative generation.
- Frozen architecture: Contracts 001-005 are immutable. Extend via new contracts.

## Architecture

```text
ChatGPT Export
      |
      v
001 Ingestion (immutable evidence + observations)
      |
      v
002 Claims (projections, graph, bounties)
      |
      v
003 Resolution (structural answer + trace)
      |
      v
004 Timeline (events, maturity, gaps)
      |
      v
005 Publishing (deterministic packages + verifier)
```

All layers are rule-based and source-gated.

## Repository Status

Contracts 001-005 are verified and frozen.

Future capabilities extend the engine through new contracts rather than modifying the frozen architecture.

## Documentation

- README
- [`Docs/Contract 001 - Epistemic Graph v0.md`](Docs/Contract%20001%20-%20Epistemic%20Graph%20v0.md)
- [`Docs/Contract 002 - Claim Layer V1.md`](Docs/Contract%20002%20-%20Claim%20Layer%20V1.md)
- [`Docs/Contract 003 - Evidence Resolution.md`](Docs/Contract%20003%20-%20Evidence%20Resolution.md)
- [`Docs/Contract 004 - Timeline & Contract Res.md`](Docs/Contract%20004%20-%20Timeline%20%26%20Contract%20Res.md)
- [`Docs/Contract 005 - Deterministic Publishing.md`](Docs/Contract%20005%20-%20Deterministic%20Publishing.md)
- [`Docs/CONTRACT_001_VERIFIED.md`](Docs/CONTRACT_001_VERIFIED.md)
- [`Docs/CONTRACT_002_VERIFIED.md`](Docs/CONTRACT_002_VERIFIED.md)
- [`Docs/CONTRACT_003_IMPLEMENTATION_SPEC.md`](Docs/CONTRACT_003_IMPLEMENTATION_SPEC.md)
- [`Docs/CONTRACT_003_VERIFIED.md`](Docs/CONTRACT_003_VERIFIED.md)
- [`Docs/CONTRACT_004_IMPLEMENTATION_SPEC.md`](Docs/CONTRACT_004_IMPLEMENTATION_SPEC.md)
- [`Docs/CONTRACT_004_VERIFIED.md`](Docs/CONTRACT_004_VERIFIED.md)
- [`Docs/CONTRACT_005_IMPLEMENTATION_SPEC.md`](Docs/CONTRACT_005_IMPLEMENTATION_SPEC.md)
- [`Docs/CONTRACT_005_VERIFIED.md`](Docs/CONTRACT_005_VERIFIED.md)

Each contract includes an implementation specification and verification record.

## Getting Started with Real Data

Run the pipeline on your archive, generate an audit package with Contract 005, and inspect one `resolution_trace.json`. This shows exactly how the system reaches its output from evidence.

Warning: raw, uncurated archives produce many low-maturity concepts and zero-confidence answers. This is expected and correct.
