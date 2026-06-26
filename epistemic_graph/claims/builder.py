from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..hash_utils import stable_id
from .bounties import write_bounties
from .graph import write_claim_graph
from .schema import Claim, ClaimLifecycle
from .serialization import load_jsonl, write_jsonl


CLAIM_BUILDER_VERSION = "claim-layer-v1"


@dataclass(frozen=True)
class ClaimLayerResult:
    claims_path: Path
    claim_graph_path: Path
    bounties_path: Path


def load_observations(path: str | Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def load_enriched_observations(path: str | Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    return load_jsonl(path)


def _claim_label(observation: dict[str, Any]) -> str:
    actor = observation.get("actor") or "unknown"
    event_type = observation.get("event_type") or "unknown"
    return f"{actor}::{event_type}"


def _claim_type(observation: dict[str, Any]) -> str:
    event_type = observation.get("event_type") or "unknown"
    return str(event_type)


def _claim_from_observation(observation: dict[str, Any], builder_version: str) -> Claim:
    claim_type = _claim_type(observation)
    claim_id = stable_id(
        "claim",
        {
            "builder_version": builder_version,
            "claim_type": claim_type,
            "source_observation_id": observation["observation_id"],
        },
    )
    return Claim(
        claim_id=claim_id,
        claim_type=claim_type,
        claim_label=_claim_label(observation),
        lifecycle=ClaimLifecycle.proposed,
        builder_version=builder_version,
        source_observation_ids=[observation["observation_id"]],
        source_evidence_ids=[observation["source_evidence_id"]],
        source_observation_hashes=[observation["hashes"]["observation_hash"]],
        hypotheses=[],
    )


def build_claims(
    observations_path: str | Path,
    enriched_observations_path: str | Path | None = None,
    *,
    builder_version: str = CLAIM_BUILDER_VERSION,
) -> list[Claim]:
    observations = load_observations(observations_path)
    _ = load_enriched_observations(enriched_observations_path)

    claims = [
        _claim_from_observation(observation, builder_version)
        for observation in observations
    ]
    claims.sort(key=lambda claim: claim.claim_id)
    return claims


def _claim_record(claim: Claim) -> dict[str, Any]:
    return claim.model_dump(mode="json")


def write_claims(path: str | Path, claims: list[Claim]) -> None:
    write_jsonl(path, [_claim_record(claim) for claim in sorted(claims, key=lambda claim: claim.claim_id)])


def build_claim_artifacts(
    observations_path: str | Path,
    output_dir: str | Path,
    enriched_observations_path: str | Path | None = None,
    *,
    builder_version: str = CLAIM_BUILDER_VERSION,
) -> ClaimLayerResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    claims = build_claims(
        observations_path,
        enriched_observations_path,
        builder_version=builder_version,
    )

    claims_path = output_dir / "claims.jsonl"
    claim_graph_path = output_dir / "claim_graph.json"
    bounties_path = output_dir / "bounties.jsonl"

    write_claims(claims_path, claims)
    write_claim_graph(claim_graph_path, claims, builder_version)
    write_bounties(bounties_path, claims, builder_version)

    return ClaimLayerResult(
        claims_path=claims_path,
        claim_graph_path=claim_graph_path,
        bounties_path=bounties_path,
    )
