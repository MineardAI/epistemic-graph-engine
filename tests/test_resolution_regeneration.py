from __future__ import annotations

import hashlib
from pathlib import Path

from epistemic_graph.resolution.engine import build_resolution_artifacts


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_regeneration_and_upstream_immutability(contract1_artifacts, contract2_artifacts, tmp_path: Path) -> None:
    before = {
        "evidence.jsonl": _sha(contract1_artifacts.evidence_path),
        "observations.jsonl": _sha(contract1_artifacts.observations_path),
        "manifest.json": _sha(contract1_artifacts.manifest_path),
        "claims.jsonl": _sha(contract2_artifacts.claims_path),
        "claim_graph.json": _sha(contract2_artifacts.claim_graph_path),
        "bounties.jsonl": _sha(contract2_artifacts.bounties_path),
    }

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    result1 = build_resolution_artifacts(
        "claim:claim_00072a8c4116a3a7da7c8366",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
        first_dir,
    )
    first_answer = result1.answer_path.read_bytes()
    first_trace = result1.trace_path.read_bytes()

    result1.answer_path.unlink()
    result1.trace_path.unlink()

    result2 = build_resolution_artifacts(
        "claim:claim_00072a8c4116a3a7da7c8366",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
        first_dir,
    )
    result3 = build_resolution_artifacts(
        "claim:claim_00072a8c4116a3a7da7c8366",
        contract2_artifacts.claims_path,
        contract2_artifacts.claim_graph_path,
        contract2_artifacts.bounties_path,
        second_dir,
    )

    after = {
        "evidence.jsonl": _sha(contract1_artifacts.evidence_path),
        "observations.jsonl": _sha(contract1_artifacts.observations_path),
        "manifest.json": _sha(contract1_artifacts.manifest_path),
        "claims.jsonl": _sha(contract2_artifacts.claims_path),
        "claim_graph.json": _sha(contract2_artifacts.claim_graph_path),
        "bounties.jsonl": _sha(contract2_artifacts.bounties_path),
    }

    assert before == after
    assert first_answer == result2.answer_path.read_bytes() == result3.answer_path.read_bytes()
    assert first_trace == result2.trace_path.read_bytes() == result3.trace_path.read_bytes()
    assert {path.name for path in first_dir.iterdir()} == {"answer.json", "resolution_trace.json"}

