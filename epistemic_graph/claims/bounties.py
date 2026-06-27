from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..hash_utils import stable_id
from .lifecycle import is_unresolved_claim_lifecycle
from .schema import Bounty, Claim, ClaimLifecycle
from .serialization import write_jsonl


def _as_claim_record(claim: Claim | dict[str, Any]) -> dict[str, Any]:
    if isinstance(claim, Claim):
        return claim.model_dump(mode="json")
    return dict(claim)


def _expected_source_types(claim_type: str) -> list[str]:
    return [f"{claim_type} follow-up observation"]


def build_bounties(claims: Iterable[Claim | dict[str, Any]], builder_version: str) -> list[Bounty]:
    bounty_records: list[Bounty] = []
    for claim in sorted((_as_claim_record(claim) for claim in claims), key=lambda record: record["claim_id"]):
        lifecycle = ClaimLifecycle(claim["lifecycle"])
        if not is_unresolved_claim_lifecycle(lifecycle):
            continue
        bounty_records.append(
            Bounty(
                bounty_id=stable_id(
                    "bounty",
                    {
                        "builder_version": builder_version,
                        "claim_id": claim["claim_id"],
                    },
                ),
                claim_id=claim["claim_id"],
                claim_type=claim["claim_type"],
                status="open",
                missing_evidence=[
                    f"additional observation corroborating {claim['claim_type']} claim {claim['claim_id']}"
                ],
                expected_source_types=_expected_source_types(claim["claim_type"]),
                potential_resolution_impact=f"Could move claim {claim['claim_id']} toward supported status.",
                source_observation_ids=list(claim["source_observation_ids"]),
            )
        )
    return bounty_records


def write_bounties(path: str | Path, claims: Iterable[Claim | dict[str, Any]], builder_version: str) -> list[Bounty]:
    bounties = build_bounties(claims, builder_version)
    write_jsonl(path, [bounty.model_dump(mode="json") for bounty in bounties])
    return bounties
