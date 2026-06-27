from __future__ import annotations

import hashlib
from pathlib import Path

from epistemic_graph.timeline import build_timeline_artifacts


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_timeline_regeneration_is_byte_identical(contract1_artifacts, contract2_artifacts, contract3_artifacts, tmp_path: Path) -> None:
    output_one = tmp_path / "timeline-1"
    output_two = tmp_path / "timeline-2"

    first = build_timeline_artifacts(
        contract1_artifacts.observations_path,
        contract2_artifacts.claims_path,
        contract2_artifacts.bounties_path,
        contract3_artifacts.answer_path,
        contract3_artifacts.trace_path,
        output_one,
    )
    second = build_timeline_artifacts(
        contract1_artifacts.observations_path,
        contract2_artifacts.claims_path,
        contract2_artifacts.bounties_path,
        contract3_artifacts.answer_path,
        contract3_artifacts.trace_path,
        output_two,
    )

    first_hashes = {path.name: _sha(path) for path in output_one.iterdir()}
    second_hashes = {path.name: _sha(path) for path in output_two.iterdir()}

    assert first_hashes == second_hashes

    expected_files = {
        "timeline_events.jsonl",
        "concept_timeline.json",
        "concept_maturity.json",
        "gap_windows.jsonl",
        "timeline_report.md",
    }
    assert {path.name for path in output_one.iterdir()} == expected_files
    assert {path.name for path in output_two.iterdir()} == expected_files
    assert first.timeline_events_path.read_bytes() == second.timeline_events_path.read_bytes()
    assert first.concept_timeline_path.read_bytes() == second.concept_timeline_path.read_bytes()
    assert first.concept_maturity_path.read_bytes() == second.concept_maturity_path.read_bytes()
    assert first.gap_windows_path.read_bytes() == second.gap_windows_path.read_bytes()
    assert first.timeline_report_path.read_bytes() == second.timeline_report_path.read_bytes()


def test_contract_001_to_003_artifacts_remain_byte_identical(contract1_artifacts, contract2_artifacts, contract3_artifacts, tmp_path: Path) -> None:
    before = {
        "evidence.jsonl": _sha(contract1_artifacts.evidence_path),
        "observations.jsonl": _sha(contract1_artifacts.observations_path),
        "manifest.json": _sha(contract1_artifacts.manifest_path),
        "claims.jsonl": _sha(contract2_artifacts.claims_path),
        "claim_graph.json": _sha(contract2_artifacts.claim_graph_path),
        "bounties.jsonl": _sha(contract2_artifacts.bounties_path),
        "answer.json": _sha(contract3_artifacts.answer_path),
        "resolution_trace.json": _sha(contract3_artifacts.trace_path),
    }

    build_timeline_artifacts(
        contract1_artifacts.observations_path,
        contract2_artifacts.claims_path,
        contract2_artifacts.bounties_path,
        contract3_artifacts.answer_path,
        contract3_artifacts.trace_path,
        tmp_path / "timeline",
    )

    after = {
        "evidence.jsonl": _sha(contract1_artifacts.evidence_path),
        "observations.jsonl": _sha(contract1_artifacts.observations_path),
        "manifest.json": _sha(contract1_artifacts.manifest_path),
        "claims.jsonl": _sha(contract2_artifacts.claims_path),
        "claim_graph.json": _sha(contract2_artifacts.claim_graph_path),
        "bounties.jsonl": _sha(contract2_artifacts.bounties_path),
        "answer.json": _sha(contract3_artifacts.answer_path),
        "resolution_trace.json": _sha(contract3_artifacts.trace_path),
    }

    assert before == after
