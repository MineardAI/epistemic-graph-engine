from __future__ import annotations

from pathlib import Path

import pytest

from epistemic_graph.claims.builder import build_claim_artifacts
from epistemic_graph.claims.serialization import load_jsonl, write_jsonl
from epistemic_graph.ingest import ingest_archive
from epistemic_graph.resolution import build_resolution_artifacts
from epistemic_graph.timeline import build_timeline_artifacts


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_conversations.json"


@pytest.fixture()
def contract1_artifacts(tmp_path: Path):
    output_dir = tmp_path / "contract1"
    return ingest_archive(FIXTURE, output_dir)


@pytest.fixture()
def contract2_artifacts(contract1_artifacts, tmp_path: Path):
    output_dir = tmp_path / "contract2"
    return build_claim_artifacts(contract1_artifacts.observations_path, output_dir)


@pytest.fixture()
def contract3_artifacts(contract2_artifacts, tmp_path: Path):
    claims = load_jsonl(contract2_artifacts.claims_path)
    first_claim_id = claims[0]["claim_id"]
    output_dir = tmp_path / "contract3"
    return build_resolution_artifacts(
        f"claim:{first_claim_id}",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
        output_dir,
    )


@pytest.fixture()
def contract4_artifacts(contract1_artifacts, contract2_artifacts, contract3_artifacts, tmp_path: Path):
    output_dir = tmp_path / "contract4"
    return build_timeline_artifacts(
        contract1_artifacts.observations_path,
        contract2_artifacts.claims_path,
        contract2_artifacts.bounties_path,
        contract3_artifacts.answer_path,
        contract3_artifacts.trace_path,
        output_dir,
    )


@pytest.fixture()
def enriched_observations_path(contract1_artifacts, tmp_path: Path) -> Path:
    observations = load_jsonl(contract1_artifacts.observations_path)
    first = observations[0]
    enriched_path = tmp_path / "enriched_observations.jsonl"
    write_jsonl(
        enriched_path,
        [
            {
                "enrichment_id": "enrichment_0001",
                "target_observation_id": first["observation_id"],
                "target_observation_hash": first["hashes"]["observation_hash"],
                "surface_domain": "test",
                "concepts": ["alpha"],
                "certainty_markers": ["deterministic"],
                "expansion_markers": ["overlay"],
                "generated_at": "2026-06-26T00:00:00Z",
                "enrichment_engine": "test",
                "enrichment_version": "1.0",
            }
        ],
    )
    return enriched_path


@pytest.fixture()
def frozen_artifact_paths(contract1_artifacts, contract2_artifacts, contract3_artifacts, contract4_artifacts) -> dict[str, Path]:
    return {
        "evidence.jsonl": contract1_artifacts.evidence_path,
        "observations.jsonl": contract1_artifacts.observations_path,
        "claims.jsonl": contract2_artifacts.claims_path,
        "claim_graph.json": contract2_artifacts.claim_graph_path,
        "bounties.jsonl": contract2_artifacts.bounties_path,
        "answer.json": contract3_artifacts.answer_path,
        "resolution_trace.json": contract3_artifacts.trace_path,
        "timeline_events.jsonl": contract4_artifacts.timeline_events_path,
        "concept_timeline.json": contract4_artifacts.concept_timeline_path,
        "concept_maturity.json": contract4_artifacts.concept_maturity_path,
        "gap_windows.jsonl": contract4_artifacts.gap_windows_path,
        "timeline_report.md": contract4_artifacts.timeline_report_path,
    }
