from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from ..hash_utils import sha256_hex, stable_id
from .schema import Claim, ClaimLifecycle
from .serialization import write_json


def _as_claim_record(claim: Claim | dict[str, Any]) -> dict[str, Any]:
    if isinstance(claim, Claim):
        return claim.model_dump(mode="json")
    return dict(claim)


def compile_claim_graph(claims: Iterable[Claim | dict[str, Any]], builder_version: str) -> dict[str, Any]:
    claim_records = sorted((_as_claim_record(claim) for claim in claims), key=lambda record: record["claim_id"])

    support_edges: list[dict[str, Any]] = []
    claims_by_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for claim in claim_records:
        for observation_id, evidence_id, observation_hash in zip(
            claim["source_observation_ids"],
            claim["source_evidence_ids"],
            claim["source_observation_hashes"],
            strict=True,
        ):
            support_edges.append(
                {
                    "edge_id": stable_id(
                        "edge",
                        {
                            "edge_type": "supports",
                            "claim_id": claim["claim_id"],
                            "observation_id": observation_id,
                        },
                    ),
                    "edge_type": "supports",
                    "source": claim["claim_id"],
                    "target": observation_id,
                    "target_evidence_id": evidence_id,
                    "target_observation_hash": observation_hash,
                }
            )
            claims_by_evidence[evidence_id].append(claim)

    contradiction_edges: list[dict[str, Any]] = []
    for evidence_id in sorted(claims_by_evidence):
        group = sorted(claims_by_evidence[evidence_id], key=lambda record: record["claim_id"])
        if len(group) < 2:
            continue
        for left, right in combinations(group, 2):
            if left["claim_type"] == right["claim_type"] and left["lifecycle"] == right["lifecycle"]:
                continue
            contradiction_edges.append(
                {
                    "edge_id": stable_id(
                        "edge",
                        {
                            "edge_type": "contradicts",
                            "left_claim_id": left["claim_id"],
                            "right_claim_id": right["claim_id"],
                            "evidence_id": evidence_id,
                        },
                    ),
                    "edge_type": "contradicts",
                    "source": left["claim_id"],
                    "target": right["claim_id"],
                    "shared_evidence_id": evidence_id,
                }
            )

    claim_ids = [record["claim_id"] for record in claim_records]
    unresolved_claim_ids = [
        record["claim_id"]
        for record in claim_records
        if ClaimLifecycle(record["lifecycle"]) in {
            ClaimLifecycle.proposed,
            ClaimLifecycle.provisional,
            ClaimLifecycle.supported,
            ClaimLifecycle.contested,
        }
    ]

    graph = {
        "schema_version": "1.0",
        "builder_version": builder_version,
        "graph_id": stable_id(
            "claim-graph",
            {
                "builder_version": builder_version,
                "claim_ids": claim_ids,
                "support_edge_ids": [edge["edge_id"] for edge in support_edges],
                "contradiction_edge_ids": [edge["edge_id"] for edge in contradiction_edges],
            },
        ),
        "claim_count": len(claim_records),
        "claims": claim_records,
        "support_edges": support_edges,
        "contradiction_edges": contradiction_edges,
        "summary": {
            "claim_count": len(claim_records),
            "support_edge_count": len(support_edges),
            "contradiction_edge_count": len(contradiction_edges),
            "unresolved_claim_count": len(unresolved_claim_ids),
            "unresolved_claim_ids": unresolved_claim_ids,
        },
        "hashes": {
            "graph_hash": sha256_hex(
                {
                    "claim_count": len(claim_records),
                    "claims": claim_records,
                    "support_edges": support_edges,
                    "contradiction_edges": contradiction_edges,
                    "summary": {
                        "claim_count": len(claim_records),
                        "support_edge_count": len(support_edges),
                        "contradiction_edge_count": len(contradiction_edges),
                        "unresolved_claim_count": len(unresolved_claim_ids),
                        "unresolved_claim_ids": unresolved_claim_ids,
                    },
                }
            )
        },
    }
    return graph


def write_claim_graph(path: str | Path, claims: Iterable[Claim | dict[str, Any]], builder_version: str) -> dict[str, Any]:
    graph = compile_claim_graph(claims, builder_version)
    write_json(path, graph)
    return graph
