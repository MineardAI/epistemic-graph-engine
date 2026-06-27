# Epistemic Graph Engine
A deterministic, evidence-first engine for reconstructing auditable knowledge from conversation archives.

> **Design Guarantee**
>
> Every artifact produced by the Epistemic Graph Engine is traceable to immutable evidence, reproducible from identical inputs, and independently verifiable. No layer invents knowledge beyond its contractual authority.

## Repository Status

Contracts 001-005 are frozen.

Future work extends the architecture through new contracts rather than modifying the frozen foundation, except to correct verified defects.

## Contract Structure

- Contract 001 - Ingestion
- Contract 002 - Claim Layer
- Contract 003 - Evidence Resolution
- Contract 004 - Timeline & Concept Reconstruction
- Contract 005 - Deterministic Publishing, Packaging & Verification

## Architecture Notes

- The repository is organized as a sequence of layers.
- The term `Pass 1`, `Pass 2`, and `Pass 3` is reserved for the three ingestion passes defined by Contract 001.
- Use `immutable artifacts` for frozen upstream outputs.
- Use `derived artifacts` for downstream outputs.
- Use `read-only inputs` for frozen inputs consumed by later contracts.
- Use `deterministic outputs` for regenerated artifacts with stable bytes.
