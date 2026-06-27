# Contract 001 Verified

- Verification date: 2026-06-26
- Repository commit hash: `1e7060707b2bcd976f00d1f90a75fe0ebcfb9821`
- Contract 001 version: v0 / deterministic ingestion foundation

## Generated Artifact Hashes

Generated from `tests/fixtures/sample_conversations.json`:

- `evidence.jsonl`: `0ca82794da38e099e9b7bf326a12b0f228d06d4d0fbe458b31f48cc72885b527`
- `observations.jsonl`: `fb3e26d79e3a068583f1643bea3a94193dc4dcd3ac01854f5512a535573dbdb7`
- `manifest.json`: `3c3293b15b924ce888bc07a8accb177fe3c2ef339ab7de82e2414930ce93a441`

## Manifest Hashes

- `input_archive_hash`: `ebebad6523e8800afe5fd0da819f86e0833f75a5a80033a623d1e1e5e53b0648`
- `evidence_jsonl_hash`: `0ca82794da38e099e9b7bf326a12b0f228d06d4d0fbe458b31f48cc72885b527`
- `observations_jsonl_hash`: `fb3e26d79e3a068583f1643bea3a94193dc4dcd3ac01854f5512a535573dbdb7`
- `total_enriched_observations`: `0`

## Pytest Result

- `python -m pytest -q`
- Result: `12 passed`

## Verification Summary

- Deterministic regeneration verified across two fresh output directories.
- `evidence.jsonl`, `observations.jsonl`, and `manifest.json` were byte-identical across repeated runs.
- Manifest-declared hashes matched the actual file hashes.
- `git diff --check` passed.

## Implementation Decisions

- Naming classification is rule-based and only triggers when a message contains quoted capitalized terms.
- `generated_at` is derived from archive timestamps rather than wall-clock time to preserve byte-identical regeneration.
- Messageless mapping nodes are retained as evidence-only nodes and do not generate observations.
- The ingest path writes only the three base Contract 001 artifacts when enrichment is absent.

## Known Deviations

- No enrichment overlay is implemented, so `total_enriched_observations` is always `0`.
- The repository keeps a small deterministic fixture generator under `scripts/` to derive the minimal sample fixture from the archive.

## Documented Ambiguities

- The spec requires naming to be a distinct event type but does not prescribe a complete naming heuristic. The implementation uses the most conservative deterministic rule available: quoted capitalized terms.
- The spec allows optional enrichment but does not require any enrichment output when the overlay is absent. This review freezes the base ingest contract only.

