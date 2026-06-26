from __future__ import annotations

import hashlib
from pathlib import Path

from epistemic_graph.claims.builder import build_claim_artifacts


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_contract_001_artifacts_remain_unchanged_by_contract_002(contract1_artifacts, enriched_observations_path, tmp_path):
    before = {
        "evidence": _sha(contract1_artifacts.evidence_path),
        "observations": _sha(contract1_artifacts.observations_path),
        "manifest": _sha(contract1_artifacts.manifest_path),
        "enriched": _sha(enriched_observations_path),
    }

    build_claim_artifacts(
        contract1_artifacts.observations_path,
        tmp_path / "claims",
        enriched_observations_path=enriched_observations_path,
    )

    after = {
        "evidence": _sha(contract1_artifacts.evidence_path),
        "observations": _sha(contract1_artifacts.observations_path),
        "manifest": _sha(contract1_artifacts.manifest_path),
        "enriched": _sha(enriched_observations_path),
    }

    assert before == after
    assert {p.name for p in (tmp_path / "claims").iterdir()} == {
        "claims.jsonl",
        "claim_graph.json",
        "bounties.jsonl",
    }
