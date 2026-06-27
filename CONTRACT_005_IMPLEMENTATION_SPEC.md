# Contract 005 Implementation Spec

Contract 005 is a deterministic publishing, packaging, and verification layer.
It consumes frozen outputs from Contracts 001-004 and does not reopen
`conversations.json`.

## Scope

- Canonical namespace: `epistemic_graph/publish/`
- v0 profile format: JSON files in `profiles/*.json`
- v0 archive format: optional uncompressed `.tar`
- v0 package schema version: `005.v0`
- v0 package version: `0.1.0`
- Canonical JSON writes must reuse the Contract 001 helper path with sorted
  keys, `ensure_ascii=False`, compact separators, UTF-8 encoding, and LF
  newlines.

## Inputs

Contract 005 may read only frozen outputs from Contracts 001-004, including:

- `evidence.jsonl`
- `observations.jsonl`
- `enriched_observations.jsonl` when present
- `claims.jsonl`
- `claim_graph.json`
- `bounties.jsonl`
- `answer.json`
- `resolution_trace.json`
- `timeline_events.jsonl`
- `concept_timeline.json`
- `concept_maturity.json`
- `gap_windows.jsonl`
- `timeline_report.md`

## Output Artifacts

The package build may emit:

- `package_manifest.json`
- `evidence_report.md`
- `executive_summary.md`
- `claim_dossier.md`
- `timeline_export.md`
- CSV exports
- HTML exports
- optional sealed package archive as an uncompressed `.tar`

## Deterministic Package Identity

`package_id` is the SHA-256 hex digest of canonical JSON containing only:

- the export profile name
- the sorted source artifact hashes
- the package schema version string (`005.v0`)

`generated_at` is metadata only and must not affect `package_id`.
For v0, it is pinned to the deterministic sentinel timestamp
`1970-01-01T00:00:00Z` so repeated builds remain byte-identical.

## Profile Rules

Profiles are declarative JSON files and must reject unknown fields.

Each profile defines:

- `profile_name`
- `package_version`
- `package_schema_version`
- `source_artifacts`
- `views`

Each view defines a single deterministic table.
Rows are sorted by the declared stable key list.
Empty tables render as a single row of explicit `None` values.

`record_types` is descriptive metadata only.

It lists the intended upstream record families for a profile view.

It is not enforced by the v0 runtime packager.

The v0 packager selects outputs from explicit profile include/exclude rules
and declared views, not from `record_types`.

## Manifest Rules

`package_manifest.json` must contain exactly these sections:

1. `package_identity`
2. `build_metadata`
3. `inputs`
4. `outputs`
5. `verification`

`package_identity` includes:

- `package_id`
- `package_version`
- `package_schema_version`
- `profile_name`

`build_metadata` includes:

- `generated_at`
- `ibos_version`
- `contract_versions`

`inputs` and `outputs` list relative paths, file sizes in bytes, and SHA-256
hashes.

`verification` includes:

- `schema_valid`
- `profile_valid`
- `required_files_present`
- `file_sizes_valid`
- `hashes_valid`
- `errors`

## Archive Rules

The optional archive must be:

- uncompressed `.tar`
- lexicographically ordered by relative path
- written with fixed timestamps and fixed file metadata
- reproducible byte-for-byte across runs

## Verification Rules

The standalone verifier must check:

- manifest presence
- profile validity
- declared file presence
- file sizes
- file hashes
- deterministic package identity recomputation
- archive readability when an archive is provided

## Conservative v0 Policy

- No gzip or zip compression.
- No random IDs.
- No UUIDs.
- No filesystem-order dependence.
- No new knowledge creation.
- No narrative conclusions beyond source-backed tables.
