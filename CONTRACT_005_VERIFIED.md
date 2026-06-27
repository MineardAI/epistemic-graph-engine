# Contract 005 Verified

- Verification date: 2026-06-26
- Repository Commit SHA: `45c846e742bf707368b1b85cbc5981de7e3d45de`
- Contract 005 version: `publish-v1`
- Implementation spec reference: [`CONTRACT_005_IMPLEMENTATION_SPEC.md`](C:/Users/Tyrone/OneDrive/Desktop/Epistemic Graph Engine/CONTRACT_005_IMPLEMENTATION_SPEC.md)

## Pytest Result

- `python -m pytest -q`
- Result: `81 passed`

## Generated Artifact Hashes

- `package_id`: `1c26d19099eb46afc309203d812d756c51ffad3358eabb20c1bf62d329a80745`
- `package_manifest.json`: `78e4ddf56ec96273168414bfa906bc73fc92d7bd253bd3bf1527c65aa562ccbf`
- `archive (.tar)`: `252140e2e8f0831b24fa6d95572e875a3b9a5939dd44d255e34611b0671fdf0f`
- `executive_summary.md`: `6717af09e744d2888fb59cfc8dba319a9aeea7b2b3b0f71710eb81206b35f81a`
- `executive_summary.csv`: `755d8238bc953a75f0c90c39b98538b115bf45aac3705713fb997be258248a91`
- `executive_summary.html`: `ec7ee5ba0c4aaca5b71e10fd7c64be8b6c0c9c7a639def46eed4de4a18eeacd6`
- `evidence_report.md`: `8c494a47d1b34f3718c419232bcbdfc4c7dc9811a7154268e7b84d975aafc1f1`
- `evidence_report.csv`: `c56fd0f9ec9d55ee29ac7ecc672a5b9199979a2a4a784af005a06a41a84c74dc`
- `evidence_report.html`: `280346f4958b5026e0c1e2bda6bbf6922cb42fc486bc7554e08af0ce0886d58a`
- `claim_dossier.md`: `6199f1cf7b404f513c5d0be82fbe450aaa26289570434e891bcf69fe20685f9c`
- `claim_dossier.csv`: `3abc38f267a924a1bc6f64c8029b4a0e299e1bec229bf2640037b044c84cfc9f`
- `claim_dossier.html`: `20def676bd62bef4a4bcaa21fe7fae60a7fdefd1ea22910a390e6daaac38656c`
- `timeline_export.md`: `420510b47bfc9b46c6e99eb85ff91d26aecee3ea54c2af37bb44b31472f4d8b6`
- `timeline_export.csv`: `46524165df2f8f164bd61217ec4122e795838c4260364f8f3dbfe1e6d1f6605a`
- `timeline_export.html`: `115b29cfa6c13376b6971576fddba4bfe1f91aef4a8d5c3c8dc7074ca4460ddc`

## Upstream Artifact Hashes

Before Contract 005 build:

- `evidence.jsonl` `0ca82794da38e099e9b7bf326a12b0f228d06d4d0fbe458b31f48cc72885b527`
- `observations.jsonl` `fb3e26d79e3a068583f1643bea3a94193dc4dcd3ac01854f5512a535573dbdb7`
- `claims.jsonl` `127875cf7feda311e37ab1fb05494d3fac797d02bd9c4dcea4965908125c1697`
- `claim_graph.json` `9a07a762db80d916f853c4eb443219f2961e7fe6762e7cfe7b0741e56dd7ebd1`
- `bounties.jsonl` `38d1c83eac4a956a24653a461b2d17e6e6205b807000728f27a5dfcf8db3043b`
- `answer.json` `347466fe7c4e0e0511ad4ea36d6a6717bbfbe2ef0d0c226a07ffe9e9c752509c`
- `resolution_trace.json` `f8e435e1e58a8846526706c15eb4b6e2dfb01fc26182c0f46a03d4d2c35939d8`
- `timeline_events.jsonl` `0120634f7f83cebc51f0ecb332d01bbf05ea5d03447ccd8c9593e51e6745183c`
- `concept_timeline.json` `7dfabafca81fd4c6d7df0d52c5db7472cd74a906df4f646edc894e620f5c4466`
- `concept_maturity.json` `de1e02b02fc5c6d77c7ee3f2d475e2128146ba904d7350ad071d304c3329d52c`
- `gap_windows.jsonl` `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `timeline_report.md` `9eacc0b0449caf723ba48ce8ca3bfeb5257cf08d94577f3273d39b4c94f89722`

After Contract 005 build:

- `evidence.jsonl` unchanged
- `observations.jsonl` unchanged
- `claims.jsonl` unchanged
- `claim_graph.json` unchanged
- `bounties.jsonl` unchanged
- `answer.json` unchanged
- `resolution_trace.json` unchanged
- `timeline_events.jsonl` unchanged
- `concept_timeline.json` unchanged
- `concept_maturity.json` unchanged
- `gap_windows.jsonl` unchanged
- `timeline_report.md` unchanged

## Implementation Decisions

- Contract 005 remains under the canonical `epistemic_graph.publish` namespace.
- Profiles are declarative JSON files and reject unknown fields.
- `package_id` is derived only from the profile name, sorted source hashes, and `package_schema_version`.
- `generated_at` is metadata only and does not affect package identity.
- Markdown, CSV, and HTML views are deterministic tables only.
- The optional archive is an uncompressed `.tar` with normalized metadata.
- `record_types` is descriptive metadata only and is not enforced by the v0 runtime packager.

## Known Deviations

- None.

## Documented Ambiguities

- None remaining after remediation and review.

## Verification Summary

Contract 005 passed final verification. The package directory and optional `.tar` archive are byte-identical across repeated builds, the freeze record matches the implemented interface, and Contracts 001-004 remain unchanged.
