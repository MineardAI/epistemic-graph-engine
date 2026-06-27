from __future__ import annotations

from typing import Any, Iterable, Mapping

from .lifecycle import is_unresolved_claim_lifecycle
from .schema import ClaimLifecycle


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return value
    raise TypeError(f"unsupported claim-like object: {type(value)!r}")


def find_claims(
    claims: Iterable[Any],
    *,
    claim_ids: set[str] | None = None,
    claim_type: str | None = None,
    lifecycle: ClaimLifecycle | None = None,
    source_observation_id: str | None = None,
) -> list[Mapping[str, Any]]:
    matches: list[Mapping[str, Any]] = []
    for claim in claims:
        record = _as_mapping(claim)
        if claim_ids is not None and record["claim_id"] not in claim_ids:
            continue
        if claim_type is not None and record["claim_type"] != claim_type:
            continue
        if lifecycle is not None and ClaimLifecycle(record["lifecycle"]) != lifecycle:
            continue
        if source_observation_id is not None and source_observation_id not in record["source_observation_ids"]:
            continue
        matches.append(record)
    return sorted(matches, key=lambda record: record["claim_id"])


def unresolved_claims(claims: Iterable[Any]) -> list[Mapping[str, Any]]:
    return [
        record
        for record in find_claims(claims)
        if is_unresolved_claim_lifecycle(ClaimLifecycle(record["lifecycle"]))
    ]


def supporting_observations(
    claim: Any,
    observations: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    record = _as_mapping(claim)
    observation_ids = set(record["source_observation_ids"])
    return [observation for observation in observations if observation["observation_id"] in observation_ids]


def contradictory_observations(
    claim: Any,
    claims: Iterable[Any],
    observations: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    record = _as_mapping(claim)
    shared_evidence_ids = set(record["source_evidence_ids"])
    if not shared_evidence_ids:
        return []
    contradictory_observation_ids: set[str] = set()
    for other in claims:
        other_record = _as_mapping(other)
        if other_record["claim_id"] == record["claim_id"]:
            continue
        if not shared_evidence_ids.intersection(other_record["source_evidence_ids"]):
            continue
        if other_record["claim_type"] == record["claim_type"] and other_record["lifecycle"] == record["lifecycle"]:
            continue
        contradictory_observation_ids.update(other_record["source_observation_ids"])
    return [
        observation
        for observation in observations
        if observation["observation_id"] in contradictory_observation_ids
    ]


def hypotheses(claim: Any) -> list[Mapping[str, Any]]:
    record = _as_mapping(claim)
    return list(record.get("hypotheses", []))


def active_bounties(bounties: Iterable[Any]) -> list[Mapping[str, Any]]:
    matches: list[Mapping[str, Any]] = []
    for bounty in bounties:
        if hasattr(bounty, "model_dump"):
            record = bounty.model_dump(mode="json")
        elif isinstance(bounty, Mapping):
            record = bounty
        else:
            raise TypeError(f"unsupported bounty-like object: {type(bounty)!r}")
        if record["status"] == "open":
            matches.append(record)
    return sorted(matches, key=lambda record: record["bounty_id"])
