from __future__ import annotations

import json
import re
from pathlib import Path

from epistemic_graph.ingest import ingest_archive
from epistemic_graph.hash_utils import sha256_hex


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sample_conversations.json"


def _load_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _run_ingest(tmp_path: Path) -> tuple[Path, Path, Path]:
    result = ingest_archive(FIXTURE, tmp_path)
    return result.evidence_path, result.observations_path, result.manifest_path


def test_deterministic_source_hashing(tmp_path: Path) -> None:
    evidence_1, _, _ = _run_ingest(tmp_path / "run1")
    evidence_2, _, _ = _run_ingest(tmp_path / "run2")

    lines_1 = _load_lines(evidence_1)
    lines_2 = _load_lines(evidence_2)

    assert [node["source_hash"] for node in lines_1] == [node["source_hash"] for node in lines_2]
    assert [node["evidence_id"] for node in lines_1] == [node["evidence_id"] for node in lines_2]


def test_naming_detection_from_quoted_capitalized_terms(tmp_path: Path) -> None:
    evidence_path, observations_path, _ = _run_ingest(tmp_path)
    evidence_nodes = _load_lines(evidence_path)
    observations = _load_lines(observations_path)
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))[0]

    evidence_by_node = {node["metadata"]["node_id"]: node for node in evidence_nodes}
    observation_by_source = {node["source_evidence_id"]: node for node in observations}

    for node in fixture["mapping"].values():
        message = node.get("message")
        if not message:
            continue
        text = "\n".join(message.get("content", {}).get("parts") or [])
        quoted_literals = re.findall(r'"([^"]+)"|\'([^\']+)\'', text)
        if any(re.search(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b", first or second) for first, second in quoted_literals if (first or second)):
            source_evidence_id = evidence_by_node[node["id"]]["evidence_id"]
            assert observation_by_source[source_evidence_id]["event_type"] == "naming"
            break
    else:
        raise AssertionError("fixture should contain a quoted capitalized term")


def test_parent_child_topology_preserved(tmp_path: Path) -> None:
    evidence_path, _, _ = _run_ingest(tmp_path)
    nodes = _load_lines(evidence_path)
    by_id = {node["metadata"]["node_id"]: node for node in nodes}

    branch_nodes = [node for node in nodes if len(node["metadata"]["children_ids"]) > 1]
    assert branch_nodes, "expected at least one branching node in the sample fixture"

    for node in nodes:
        parent_id = node["metadata"]["parent_id"]
        if parent_id is not None:
            assert parent_id in by_id
        for child_id in node["metadata"]["children_ids"]:
            assert child_id in by_id


def test_hidden_system_and_tool_messages_preserved(tmp_path: Path) -> None:
    evidence_path, _, _ = _run_ingest(tmp_path)
    nodes = _load_lines(evidence_path)

    hidden_system = [
        node for node in nodes
        if node["metadata"]["actor"] == "system" and not node["metadata"]["is_visible_to_user"]
    ]
    tool_nodes = [node for node in nodes if node["metadata"]["actor"] == "tool"]

    assert hidden_system, "expected at least one hidden system node"
    assert tool_nodes, "expected at least one tool node"


def test_attachment_metadata_preserved(tmp_path: Path) -> None:
    evidence_path, _, _ = _run_ingest(tmp_path)
    nodes = _load_lines(evidence_path)

    attachment_nodes = [node for node in nodes if node["metadata"]["attachments"]]
    assert attachment_nodes, "expected attachment metadata in the sample fixture"

    attachment = attachment_nodes[0]["metadata"]["attachments"][0]
    assert "id" in attachment
    assert "name" in attachment


def test_messageless_mapping_nodes_are_preserved_without_observations(tmp_path: Path) -> None:
    evidence_path, observations_path, _ = _run_ingest(tmp_path)
    evidence_nodes = _load_lines(evidence_path)
    observations = _load_lines(observations_path)
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))[0]

    messageless_nodes = [node_id for node_id, node in fixture["mapping"].items() if node.get("message") is None]
    assert messageless_nodes, "expected at least one messageless mapping node in the fixture"

    evidence_by_node = {node["metadata"]["node_id"]: node for node in evidence_nodes}
    observation_sources = {node["source_evidence_id"] for node in observations}

    for node_id in messageless_nodes:
        assert node_id in evidence_by_node
        evidence = evidence_by_node[node_id]
        assert evidence["metadata"]["children_ids"] == fixture["mapping"][node_id].get("children", [])
        assert evidence["evidence_id"] not in observation_sources


def test_actor_parsing(tmp_path: Path) -> None:
    evidence_path, observations_path, _ = _run_ingest(tmp_path)
    evidence_nodes = _load_lines(evidence_path)
    observation_nodes = _load_lines(observations_path)

    assert {node["metadata"]["actor"] for node in evidence_nodes if node["metadata"]["actor"]} >= {"user", "assistant", "system", "tool"}
    assert {node["actor"] for node in observation_nodes if node["actor"]} >= {"user", "assistant", "system", "tool"}


def test_observation_hash_stability(tmp_path: Path) -> None:
    _, observations_1, _ = _run_ingest(tmp_path / "a")
    _, observations_2, _ = _run_ingest(tmp_path / "b")

    nodes_1 = _load_lines(observations_1)
    nodes_2 = _load_lines(observations_2)

    assert [node["hashes"]["observation_hash"] for node in nodes_1] == [node["hashes"]["observation_hash"] for node in nodes_2]


def test_manifest_stability(tmp_path: Path) -> None:
    _, _, manifest_1 = _run_ingest(tmp_path / "first")
    _, _, manifest_2 = _run_ingest(tmp_path / "second")

    assert manifest_1.read_bytes() == manifest_2.read_bytes()
    manifest = json.loads(manifest_1.read_text(encoding="utf-8"))
    assert manifest["total_enriched_observations"] == 0


def test_repeated_runs_produce_byte_identical_outputs(tmp_path: Path) -> None:
    run_one = tmp_path / "one"
    run_two = tmp_path / "two"
    evidence_1, observations_1, manifest_1 = _run_ingest(run_one)
    evidence_2, observations_2, manifest_2 = _run_ingest(run_two)

    assert evidence_1.read_bytes() == evidence_2.read_bytes()
    assert observations_1.read_bytes() == observations_2.read_bytes()
    assert manifest_1.read_bytes() == manifest_2.read_bytes()


def test_base_ingestion_outputs_only_contract_001_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "base"
    result = ingest_archive(FIXTURE, out)

    expected = {"evidence.jsonl", "observations.jsonl", "manifest.json"}
    assert {path.name for path in out.iterdir()} == expected

    before = {
        "evidence": result.evidence_path.read_bytes(),
        "observations": result.observations_path.read_bytes(),
        "manifest": result.manifest_path.read_bytes(),
    }

    rerun = ingest_archive(FIXTURE, out)
    after = {
        "evidence": rerun.evidence_path.read_bytes(),
        "observations": rerun.observations_path.read_bytes(),
        "manifest": rerun.manifest_path.read_bytes(),
    }

    assert before == after


def test_output_hashes_are_consistent_with_content(tmp_path: Path) -> None:
    evidence_path, observations_path, manifest_path = _run_ingest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["evidence_jsonl_hash"] == sha256_hex(evidence_path.read_bytes())
    assert manifest["observations_jsonl_hash"] == sha256_hex(observations_path.read_bytes())
