# Contract 002 Verified

- Verification date: 2026-06-26
- Repository commit SHA: `fb083573811ad498ca9e7d7c96b0762170ef5167`
- Contract version: `claim-layer-v1`

## Generated Artifact Hashes

- `claims.jsonl`: `127875cf7feda311e37ab1fb05494d3fac797d02bd9c4dcea4965908125c1697`
- `claim_graph.json`: `9a07a762db80d916f853c4eb443219f2961e7fe6762e7cfe7b0741e56dd7ebd1`
- `bounties.jsonl`: `38d1c83eac4a956a24653a461b2d17e6e6205b807000728f27a5dfcf8db3043b`

## Contract 001 Input Hashes

- `evidence.jsonl` before Contract 002 build: `0ca82794da38e099e9b7bf326a12b0f228d06d4d0fbe458b31f48cc72885b527`
- `observations.jsonl` before Contract 002 build: `fb3e26d79e3a068583f1643bea3a94193dc4dcd3ac01854f5512a535573dbdb7`
- `manifest.json` before Contract 002 build: `3c3293b15b924ce888bc07a8accb177fe3c2ef339ab7de82e2414930ce93a441`
- `evidence.jsonl` after Contract 002 build: `0ca82794da38e099e9b7bf326a12b0f228d06d4d0fbe458b31f48cc72885b527`
- `observations.jsonl` after Contract 002 build: `fb3e26d79e3a068583f1643bea3a94193dc4dcd3ac01854f5512a535573dbdb7`
- `manifest.json` after Contract 002 build: `3c3293b15b924ce888bc07a8accb177fe3c2ef339ab7de82e2414930ce93a441`
- Optional `enriched_observations.jsonl`: not present

## Pytest Result

- `python -m pytest -q`: `29 passed in 2.61s`

## Implementation Decisions

- Contract 002 remains inside the canonical `epistemic_graph.claims` namespace.
- Claims are deterministic projections over Contract 001 observations.
- Artifact serialization reuses the canonical JSON path established by Contract 001.
- Pydantic v2 is used for strict schema validation and unknown-field rejection.
- Hypothesis, claim, and bounty schemas reject unknown fields.

## Known Deviations

- `git diff --check` emits a line-ending normalization warning for `pyproject.toml` under the current Windows git configuration, but no semantic content differs.

## Documented Ambiguities

- No optional enrichment overlay exists in this repository state, so Contract 002 verification treated enrichment as absent.

## Verification Summary

Contract 002 passed schema, determinism, immutability, and regeneration checks. Contract 001 artifacts remained byte-identical before and after Contract 002 generation. The claim layer is ready for freeze.
