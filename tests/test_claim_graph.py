from __future__ import annotations

import json

from epistemic_graph.claims.builder import build_claim_artifacts
from epistemic_graph.claims.serialization import load_jsonl
from epistemic_graph.hash_utils import canonical_json


def test_claim_graph_compilation_and_regeneration(contract1_artifacts, tmp_path):
    out1 = tmp_path / "graph1"
    out2 = tmp_path / "graph2"

    result1 = build_claim_artifacts(contract1_artifacts.observations_path, out1)
    result2 = build_claim_artifacts(contract1_artifacts.observations_path, out2)

    graph1 = result1.claim_graph_path.read_bytes()
    graph2 = result2.claim_graph_path.read_bytes()
    assert graph1 == graph2

    graph = json.loads(result1.claim_graph_path.read_text(encoding="utf-8"))
    assert graph["claim_count"] == len(load_jsonl(result1.claims_path))


def test_claim_graph_contains_support_edges(contract1_artifacts, tmp_path):
    result = build_claim_artifacts(contract1_artifacts.observations_path, tmp_path)
    graph = json.loads(result.claim_graph_path.read_text(encoding="utf-8"))
    claims = load_jsonl(result.claims_path)

    assert graph["support_edges"]
    assert "contradiction_edges" in graph
    assert len(claims) > 0
    assert result.claim_graph_path.read_text(encoding="utf-8") == canonical_json(graph) + "\n"
