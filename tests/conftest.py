from __future__ import annotations

from pathlib import Path

import pytest

from epistemic_graph.claims.builder import build_claim_artifacts
from epistemic_graph.claims.serialization import load_jsonl, write_jsonl
from epistemic_graph.ingest import ingest_archive


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
