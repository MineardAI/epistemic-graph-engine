from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from epistemic_graph.claims.builder import CLAIM_BUILDER_VERSION, build_claim_artifacts
from epistemic_graph.claims.schema import Claim
from epistemic_graph.claims.serialization import load_jsonl
from epistemic_graph.hash_utils import canonical_json


def test_claim_builder_generates_deterministic_claims(contract1_artifacts, tmp_path: Path) -> None:
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    result1 = build_claim_artifacts(contract1_artifacts.observations_path, out1)
    result2 = build_claim_artifacts(contract1_artifacts.observations_path, out2)

    assert result1.claims_path.read_bytes() == result2.claims_path.read_bytes()
    assert result1.claim_graph_path.read_bytes() == result2.claim_graph_path.read_bytes()
    assert result1.bounties_path.read_bytes() == result2.bounties_path.read_bytes()


def test_claim_builder_uses_only_observations_and_not_raw_text(contract1_artifacts, tmp_path: Path) -> None:
    claims_path = build_claim_artifacts(contract1_artifacts.observations_path, tmp_path).claims_path
    claims_text = claims_path.read_text(encoding="utf-8")
    observations = load_jsonl(contract1_artifacts.observations_path)

    for observation in observations:
        if len(observation["redacted_quote"]) > 20:
            assert observation["redacted_quote"] not in claims_text


def test_claim_builder_no_orphan_claims(contract1_artifacts, tmp_path: Path) -> None:
    claims_path = build_claim_artifacts(contract1_artifacts.observations_path, tmp_path).claims_path
    claims = load_jsonl(claims_path)
    observations = load_jsonl(contract1_artifacts.observations_path)
    observation_ids = {observation["observation_id"] for observation in observations}

    assert claims
    for claim in claims:
        assert claim["source_observation_ids"]
        assert set(claim["source_observation_ids"]).issubset(observation_ids)


def test_claim_builder_claims_are_canonically_serialized(contract1_artifacts, tmp_path: Path) -> None:
    claims_path = build_claim_artifacts(contract1_artifacts.observations_path, tmp_path).claims_path
    raw = claims_path.read_bytes()

    assert raw.endswith(b"\n")
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        assert canonical_json(json.loads(line)) == line


def test_claim_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Claim.model_validate(
            {
                "claim_id": "claim_1",
                "claim_type": "statement",
                "claim_label": "user::statement",
                "lifecycle": "proposed",
                "builder_version": CLAIM_BUILDER_VERSION,
                "source_observation_ids": ["obs_1"],
                "source_evidence_ids": ["evidence_1"],
                "source_observation_hashes": ["hash_1"],
                "unexpected": True,
            }
        )
