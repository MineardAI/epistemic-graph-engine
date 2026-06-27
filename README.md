# Epistemic Graph Engine

Turn your ChatGPT conversation history into a deterministic, searchable, auditable knowledge graph.

The Epistemic Graph Engine transforms exported AI conversations into structured evidence, claims, timelines, and verifiable reports without using LLM reasoning or inventing conclusions.

Upload a ChatGPT export, run the pipeline, and receive reproducible artifacts that answer:

- What projects did I work on?
- When did an idea first appear?
- What evidence supports this claim?
- Where are contradictions?
- What changed over time?
- What is still unresolved?

Everything is traceable back to the original conversation.

## Quick Start

1. Export your ChatGPT history

Download your ChatGPT data from OpenAI.

Locate:

`conversations.json`

2. Install

```bash
git clone https://github.com/<your-org>/epistemic-graph-engine.git
cd epistemic-graph-engine
pip install -e .
```

3. Ingest your archive

```bash
python -m epistemic_graph.ingest path/to/conversations.json
```

This creates immutable evidence artifacts.

4. Build the graph

Run the remaining contracts:

- 001 -> Ingestion
- 002 -> Claims
- 003 -> Evidence Resolution
- 004 -> Timeline Reconstruction
- 005 -> Publishing

## Output

The engine produces deterministic artifacts including:

- `evidence.jsonl`
- `observations.jsonl`
- `claims.jsonl`
- `claim_graph.json`
- `answer.json`
- `timeline_events.jsonl`
- `concept_timeline.json`
- `package_manifest.json`

Every file can be regenerated from the same input archive.

## Example Questions

Once your archive is processed you can answer questions like:

- Which project appeared first?
- Show all evidence supporting a claim.
- Find contradictory claims.
- When did a concept become a specification?
- Which ideas became dormant?
- What evidence is still missing?

## Why This Is Different

Most AI memory systems summarize.

The Epistemic Graph Engine preserves evidence.

It never:

- invents conclusions
- rewrites conversations
- infers psychology
- performs semantic search
- hides provenance

Every result includes traceable source IDs.

## Architecture

```text
ChatGPT Export
      │
      ▼
001 Ingestion
      ▼
002 Claims
      ▼
003 Resolution
      ▼
004 Timeline
      ▼
005 Publishing
```

Each layer is deterministic and read-only with respect to every layer above it.

## Repository Status

Contracts 001-005 are verified and frozen.

Future capabilities extend the engine through new contracts rather than modifying the frozen architecture.

## Documentation

- README
- Contract 001 - Ingestion
- Contract 002 - Claim Layer
- Contract 003 - Evidence Resolution
- Contract 004 - Timeline Reconstruction
- Contract 005 - Publishing & Verification

Each contract includes an implementation specification and verification record.
