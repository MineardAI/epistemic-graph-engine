# Contract 005 — Deterministic Publishing, Packaging, and Verification

You are working in a fresh Codex session.

Assume no prior context beyond this prompt.

You are implementing **Contract 005** of the Epistemic Graph architecture.

Contracts 001–004 already exist.

Do not redesign them.

Do not modify their source artifacts.

Your task is to build a deterministic publishing layer that converts existing artifacts into audience-specific, cryptographically verifiable export packages.

---

# Purpose

Contract 005 is a publisher, not an author.

It packages and renders existing evidence graph artifacts.

It must not create new knowledge.

It must not create evidence.

It must not create observations.

It must not create claims.

It must not resolve questions.

It must not infer meaning.

It must not write narrative conclusions not already present in source artifacts.

---

# Read-Only Inputs

Contract 005 may read existing artifacts such as:

* evidence.jsonl
* observations.jsonl
* enriched_observations.jsonl
* claims.jsonl
* bounties.jsonl
* claim_graph.json
* answer.json
* resolution_trace.json
* timeline_events.jsonl
* concept_timeline.json
* concept_maturity.json
* gap_windows.jsonl
* timeline_report.md

All inputs are read-only.

Never mutate them.

---

# Outputs

Contract 005 may generate:

* package_manifest.json
* evidence_report.md
* executive_summary.md
* claim_dossier.md
* timeline_export.md
* csv exports
* html exports
* sealed package archives

Generated outputs must be deterministic except for build metadata explicitly marked as non-identity metadata.

---

# Core Boundary

Contract 005 converts validated artifacts from Contracts 001–004 into deterministic, audience-specific, cryptographically verifiable packages without creating, modifying, or interpreting knowledge.

---

# Required Package Structure

Create modules:

```text
ibos/
    publish/
        __init__.py
        assembler.py
        profiles.py
        manifests.py
        sealer.py

    renderers/
        __init__.py
        markdown.py
        csv.py
        html.py

    verification/
        __init__.py
        verify_package.py

profiles/
    executive.yaml
    audit.yaml
    research.yaml
    timeline.yaml
    claim.yaml
```

Create tests:

```text
tests/
    test_publish_profiles.py
    test_publish_assembler.py
    test_publish_manifest.py
    test_publish_sealer.py
    test_publish_verifier.py
    test_publish_determinism.py
```

---

# Export Profiles

Export profiles must be declarative.

Do not hard-code profile behavior in Python if it can be expressed in YAML.

Each profile should define:

* profile name
* included artifacts
* excluded artifacts
* included sections
* redaction rules
* whether hashes are included
* whether traces are included
* whether observations are included
* whether source artifacts are included

Example profile behavior:

## executive

High-level only.

No raw evidence.

No observations.

No internal trace hashes.

No tool telemetry.

## audit

Maximum provenance.

Include hashes, traces, claims, observations, timelines, bounties, and manifests.

## research

Include structured artifacts, claims, timelines, and provenance.

May exclude raw evidence.

## timeline

Timeline and concept maturity only.

## claim

Claims, hypotheses, contradictions, bounties, and supporting IDs.

---

# Manifest Requirements

Every package must include:

```text
package_manifest.json
```

Manifest must separate:

## Package Identity

* package_id
* package_version
* export_profile

## Build Metadata

* generated_at
* ibos_version
* contract_versions

## Inputs

* source_artifacts
* source hashes
* source file sizes

## Outputs

* generated_views
* output hashes
* output file sizes

## Verification

* manifest schema version
* required artifacts present
* profile validation result

---

# Deterministic Package Identity

package_id must be deterministic.

It must be derived from:

* export profile name
* sorted source artifact hashes
* package schema version

Do not include generated_at in package_id.

Do not include current time in package_id.

Do not use random IDs.

Do not use UUIDs.

Same profile + same source hashes + same schema version must produce the same package_id.

---

# Build Metadata

generated_at may use current UTC time.

generated_at must not affect package_id.

Build metadata may vary between builds.

Package identity must not vary if source contents are identical.

---

# Sealing Rules

Sealing must follow this order:

1. Assemble selected artifacts.
2. Render selected views.
3. Generate package_manifest.json.
4. Verify manifest and file hashes.
5. Create archive.

The archive step must only wrap already-verified artifacts.

---

# Archive Rules

Do not always include all source artifacts.

The profile decides what gets included.

Executive packages should not include raw evidence.

Audit packages may include full provenance artifacts.

Research packages may include structured artifacts but not raw evidence.

---

# Renderers

Renderers produce views only.

They must not invent narrative.

They may display measurable fields, such as:

* resolution status
* confidence
* evidence count
* observation count
* claim count
* contradiction count
* open bounty count
* concept maturity stage
* gap window count
* source IDs
* hashes when profile allows

Markdown, CSV, and HTML renderers should be deterministic.

---

# Report Language Rule

Reports may organize existing data.

Reports may label sections.

Reports may present tables.

Reports must not add conclusions that are not present in source artifacts.

Do not write phrases like:

“the project evolved from mythology into architecture”

unless that exact claim or source-backed timeline statement already exists in the upstream artifacts.

---

# Verification Utility

Implement a standalone verifier:

```text
ibos/verification/verify_package.py
```

The verifier should validate:

* archive can be opened
* package_manifest.json exists
* manifest schema is valid
* export profile is valid
* required files are present
* declared files exist
* hashes match manifest
* file sizes match manifest
* package_id recomputes correctly from identity inputs

Verifier output should include:

* schema_valid
* manifest_valid
* profile_valid
* required_files_present
* hashes_valid
* package_id_valid
* errors[]

---

# Tests

Test the following:

1. Profile YAML files load and validate.
2. Assembler respects include/exclude rules.
3. Executive profile excludes raw evidence and internal traces.
4. Audit profile includes provenance artifacts.
5. Manifest contains identity, metadata, inputs, outputs, and verification sections.
6. package_id is deterministic.
7. generated_at does not affect package_id.
8. Sealed package contains package_manifest.json.
9. Standalone verifier catches missing files.
10. Standalone verifier catches hash mismatch.
11. Rebuilding same package produces same package_id.
12. Rendered Markdown/CSV/HTML do not mutate upstream artifacts.
13. No upstream source artifacts are modified.

---

# Non-Goals

Do not build UI.

Do not build a web server.

Do not build an LLM layer.

Do not build semantic search.

Do not build new claims.

Do not build new timelines.

Do not build new resolution logic.

Do not build agents.

This is publishing, packaging, rendering, sealing, and verification only.

---

# Definition of Done

Contract 005 is complete when:

* export profiles are declarative and validated
* packages are deterministic by identity
* build metadata is separated from identity
* reports are source-backed and non-interpretive
* sealed packages include manifests
* verifier independently validates packages
* all tests pass
* upstream artifacts remain unchanged

Prefer conservative output over expressive output.

If uncertain, preserve auditability.
