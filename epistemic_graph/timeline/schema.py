from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConceptMaturityState(str, Enum):
    Mention = "Mention"
    Theme = "Theme"
    Metaphor = "Metaphor"
    Project = "Project"
    Component = "Component"
    Specification = "Specification"
    Implementation = "Implementation"
    Verified = "Verified"
    Dormant = "Dormant"
    Abandoned = "Abandoned"


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    timestamp: int | float
    concept: str
    source_observation_id: str
    source_evidence_id: str
    action_type: str


class ConceptTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str
    first_timestamp: int | float
    latest_timestamp: int | float
    total_occurrences: int
    supporting_observation_ids: list[str] = Field(default_factory=list)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    supporting_bounty_ids: list[str] = Field(default_factory=list)

    @field_validator("total_occurrences")
    @classmethod
    def _validate_total_occurrences(cls, value: int) -> int:
        if value < 0:
            raise ValueError("total_occurrences may not be negative")
        return value


class ConceptMaturityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str
    maturity_state: ConceptMaturityState
    state_reason: str
    supporting_source_ids: list[str] = Field(default_factory=list)
    supporting_observation_ids: list[str] = Field(default_factory=list)
    supporting_claim_ids: list[str] = Field(default_factory=list)


class SkippedSourceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_artifact: str
    record_id: str
    reason: str
    observation_id: str | None = None
    evidence_id: str | None = None


class GapWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_timestamp: int | float
    end_timestamp: int | float
    duration: int | float
    previous_observation: str
    next_observation: str


class OutstandingBountyEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bounty_id: str
    claim_id: str
    claim_type: str
    status: Literal["open", "closed"]
    expected_source_types: list[str] = Field(default_factory=list)
    source_observation_ids: list[str] = Field(default_factory=list)


class TimelineReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_summary: list[ConceptTimelineEntry] = Field(default_factory=list)
    chronological_events: list[TimelineEvent] = Field(default_factory=list)
    maturity_summary: list[ConceptMaturityEntry] = Field(default_factory=list)
    detected_gap_windows: list[GapWindow] = Field(default_factory=list)
    outstanding_bounties: list[OutstandingBountyEntry] = Field(default_factory=list)
    skipped_sources: list[SkippedSourceEntry] = Field(default_factory=list)
