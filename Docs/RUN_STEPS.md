# Local Run Steps

This runbook keeps everything local. It does not require GitHub once the repository is cloned.

## Input

Use the ChatGPT export stored at:

```text
Docs/conversations.json
```

## One-Shot E2E Walkthrough

From the repository root:

```powershell
python -m pip install -e .
```

Then run this pipeline script:

```powershell
@'
from pathlib import Path

from epistemic_graph.claims import build_claim_artifacts
from epistemic_graph.claims.serialization import load_jsonl
from epistemic_graph.ingest import ingest_archive
from epistemic_graph.publish import build_package
from epistemic_graph.resolution import build_resolution_artifacts
from epistemic_graph.timeline import build_timeline_artifacts

root = Path.cwd()
source = root / "Docs" / "conversations.json"
output_root = root / "out"

# Contract 001 - Ingestion
contract1 = ingest_archive(source, output_root / "contract1")

# Contract 002 - Claim Layer
contract2 = build_claim_artifacts(
    contract1.observations_path,
    output_root / "contract2",
)

# Contract 003 - Evidence Resolution
claims = load_jsonl(contract2.claims_path)
first_claim_id = claims[0]["claim_id"]
contract3 = build_resolution_artifacts(
    f"claim:{first_claim_id}",
    contract2.claims_path,
    contract2.claim_graph_path,
    contract2.bounties_path,
    output_root / "contract3",
)

# Contract 004 - Timeline Reconstruction
contract4 = build_timeline_artifacts(
    contract1.observations_path,
    contract2.claims_path,
    contract2.bounties_path,
    contract3.answer_path,
    contract3.trace_path,
    output_root / "contract4",
)

# Contract 005 - Deterministic Publishing, Packaging & Verification
build_package(
    "audit",
    output_root / "publish",
    source_artifacts={
        "evidence.jsonl": contract1.evidence_path,
        "observations.jsonl": contract1.observations_path,
        "claims.jsonl": contract2.claims_path,
        "claim_graph.json": contract2.claim_graph_path,
        "bounties.jsonl": contract2.bounties_path,
        "answer.json": contract3.answer_path,
        "resolution_trace.json": contract3.trace_path,
        "timeline_events.jsonl": contract4.timeline_events_path,
        "concept_timeline.json": contract4.concept_timeline_path,
        "concept_maturity.json": contract4.concept_maturity_path,
        "gap_windows.jsonl": contract4.gap_windows_path,
        "timeline_report.md": contract4.timeline_report_path,
    },
)

print("E2E run complete. Outputs are under:", output_root)
'@ | python -
```

## Expected Outputs

After the run, you should have these contract outputs:

- Contract 001
  - `evidence.jsonl`
  - `observations.jsonl`
  - `manifest.json`
- Contract 002
  - `claims.jsonl`
  - `claim_graph.json`
  - `bounties.jsonl`
- Contract 003
  - `answer.json`
  - `resolution_trace.json`
- Contract 004
  - `timeline_events.jsonl`
  - `concept_timeline.json`
  - `concept_maturity.json`
  - `gap_windows.jsonl`
  - `timeline_report.md`
- Contract 005
  - `package_manifest.json`
  - rendered Markdown, CSV, and HTML views
  - optional `.tar` archive

## Notes

- The pipeline is deterministic.
- The repository never needs to reopen `conversations.json` after Contract 001.
- Keep the generated `out/` directory local unless you explicitly want to publish it.
