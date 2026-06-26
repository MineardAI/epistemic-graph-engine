from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClaimLifecycle(str, Enum):
    proposed = "proposed"
    provisional = "provisional"
    supported = "supported"
    contested = "contested"
    resolved = "resolved"
    rejected = "rejected"
    archived = "archived"


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    description: str
    source_observation_ids: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str
    claim_type: str
    claim_label: str
    lifecycle: ClaimLifecycle = ClaimLifecycle.proposed
    builder_version: str
    source_observation_ids: list[str]
    source_evidence_ids: list[str]
    source_observation_hashes: list[str]
    hypotheses: list[Hypothesis] = Field(default_factory=list)

    @field_validator("source_observation_ids", "source_evidence_ids", "source_observation_hashes")
    @classmethod
    def _validate_non_empty_lists(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("claim source references may not be empty")
        return value

    @field_validator("hypotheses")
    @classmethod
    def _validate_hypothesis_count(cls, value: list[Hypothesis]) -> list[Hypothesis]:
        if len(value) > 5:
            raise ValueError("maximum hypotheses per claim is 5")
        return value


class Bounty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bounty_id: str
    claim_id: str
    claim_type: str
    status: Literal["open", "closed"] = "open"
    missing_evidence: list[str]
    expected_source_types: list[str]
    potential_resolution_impact: str
    source_observation_ids: list[str]

    @field_validator("missing_evidence", "expected_source_types", "source_observation_ids")
    @classmethod
    def _validate_non_empty_lists(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("bounty lists may not be empty")
        return value
