from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any, Iterable

from ..claims.serialization import load_jsonl
from ..hash_utils import stable_id
from .maturity import DEFAULT_GAP_WINDOW_DAYS, classify_concept_maturity
from .schema import (
    ConceptMaturityEntry,
    ConceptTimelineEntry,
    GapWindow,
    OutstandingBountyEntry,
    SkippedSourceEntry,
    TimelineEvent,
)
from .writer import (
    write_concept_maturity,
    write_concept_timeline,
    write_gap_windows,
    write_timeline_events,
    write_timeline_report,
)


_GAP_WINDOW_SECONDS = DEFAULT_GAP_WINDOW_DAYS * 24 * 60 * 60
_ARTIFACT_PRIORITY = {"observations.jsonl": 0, "claims.jsonl": 1, "bounties.jsonl": 2}


@dataclass(frozen=True)
class TimelineBuildResult:
    timeline_events_path: Path
    concept_timeline_path: Path
    concept_maturity_path: Path
    gap_windows_path: Path
    timeline_report_path: Path


@dataclass(frozen=True)
class TimelineInputs:
    observations: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    bounties: list[dict[str, Any]]
    answer: dict[str, Any]
    resolution_trace: dict[str, Any]


@dataclass(frozen=True)
class ConceptOccurrence:
    event: TimelineEvent
    source_artifact: str
    source_field: str
    source_claim_id: str | None
    source_bounty_id: str | None


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_inputs(
    observations_path: str | Path,
    claims_path: str | Path,
    bounties_path: str | Path,
    answer_path: str | Path,
    resolution_trace_path: str | Path,
) -> TimelineInputs:
    return TimelineInputs(
        observations=load_jsonl(observations_path),
        claims=load_jsonl(claims_path),
        bounties=load_jsonl(bounties_path),
        answer=_load_json(answer_path),
        resolution_trace=_load_json(resolution_trace_path),
    )


def _dedup_preserve_order(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _is_valid_timestamp(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _timestamp_value(value: Any) -> int | float | None:
    if _is_valid_timestamp(value):
        return value
    return None


def _global_latest_observation_timestamp(observations: list[dict[str, Any]]) -> int | float | None:
    valid_timestamps = [
        timestamp
        for timestamp in (_timestamp_value(observation.get("timestamp")) for observation in observations)
        if timestamp is not None
    ]
    if not valid_timestamps:
        return None
    return max(valid_timestamps)


def _record_values(record: dict[str, Any], field: str) -> list[str]:
    value = record.get(field)
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _first_source_pair(source_observation_ids: list[str], source_evidence_ids: list[str]) -> tuple[str, str] | None:
    observations = _dedup_preserve_order(source_observation_ids)
    evidence_ids = _dedup_preserve_order(source_evidence_ids)
    if not observations or not evidence_ids:
        return None
    return observations[0], evidence_ids[0]


def _skip_entry(
    *,
    source_artifact: str,
    record_id: str,
    reason: str,
    observation_id: str | None = None,
    evidence_id: str | None = None,
) -> SkippedSourceEntry:
    return SkippedSourceEntry(
        source_artifact=source_artifact,
        record_id=record_id,
        reason=reason,
        observation_id=observation_id,
        evidence_id=evidence_id,
    )


def _event(
    *,
    source_artifact: str,
    source_field: str,
    concept: str,
    timestamp: int | float,
    source_observation_id: str,
    source_evidence_id: str,
) -> TimelineEvent:
    return TimelineEvent(
        event_id=stable_id(
            "timeline-event",
            {
                "source_artifact": source_artifact,
                "source_field": source_field,
                "concept": concept,
                "timestamp": timestamp,
                "source_observation_id": source_observation_id,
                "source_evidence_id": source_evidence_id,
                "action_type": f"{source_artifact}.{source_field}",
            },
        ),
        timestamp=timestamp,
        concept=concept,
        source_observation_id=source_observation_id,
        source_evidence_id=source_evidence_id,
        action_type=f"{source_artifact}.{source_field}",
    )


def _observation_index(observations: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for observation in observations:
        observation_id = observation.get("observation_id")
        if isinstance(observation_id, str) and observation_id not in indexed:
            indexed[observation_id] = observation
    return indexed


def _claim_index(claims: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for claim in claims:
        claim_id = claim.get("claim_id")
        if isinstance(claim_id, str) and claim_id not in indexed:
            indexed[claim_id] = claim
    return indexed


def _observation_occurrences(observation: dict[str, Any]) -> list[ConceptOccurrence]:
    observation_id = observation.get("observation_id")
    evidence_id = observation.get("source_evidence_id")
    timestamp = _timestamp_value(observation.get("timestamp"))
    if not isinstance(observation_id, str) or not isinstance(evidence_id, str) or timestamp is None:
        return []

    occurrences: list[ConceptOccurrence] = []
    for source_field in ("introduced_terms", "references", "event_type", "actor"):
        for concept in _record_values(observation, source_field):
            occurrences.append(
                ConceptOccurrence(
                    event=_event(
                        source_artifact="observations.jsonl",
                        source_field=source_field,
                        concept=concept,
                        timestamp=timestamp,
                        source_observation_id=observation_id,
                        source_evidence_id=evidence_id,
                    ),
                    source_artifact="observations.jsonl",
                    source_field=source_field,
                    source_claim_id=None,
                    source_bounty_id=None,
                )
            )
    return occurrences


def _claim_occurrences(claim: dict[str, Any], observations_by_id: dict[str, dict[str, Any]]) -> list[ConceptOccurrence]:
    source_pair = _first_source_pair(
        [value for value in claim.get("source_observation_ids", []) if isinstance(value, str)],
        [value for value in claim.get("source_evidence_ids", []) if isinstance(value, str)],
    )
    if source_pair is None:
        return []
    source_observation_id, source_evidence_id = source_pair
    observation = observations_by_id.get(source_observation_id)
    if observation is None:
        return []
    timestamp = _timestamp_value(observation.get("timestamp"))
    if timestamp is None:
        return []

    claim_id = claim.get("claim_id")
    if not isinstance(claim_id, str):
        return []

    occurrences: list[ConceptOccurrence] = []
    for source_field in ("claim_type", "claim_label"):
        for concept in _record_values(claim, source_field):
            occurrences.append(
                ConceptOccurrence(
                    event=_event(
                        source_artifact="claims.jsonl",
                        source_field=source_field,
                        concept=concept,
                        timestamp=timestamp,
                        source_observation_id=source_observation_id,
                        source_evidence_id=source_evidence_id,
                    ),
                    source_artifact="claims.jsonl",
                    source_field=source_field,
                    source_claim_id=claim_id,
                    source_bounty_id=None,
                )
            )
    return occurrences


def _bounty_occurrences(
    bounty: dict[str, Any],
    claims_by_id: dict[str, dict[str, Any]],
    observations_by_id: dict[str, dict[str, Any]],
) -> list[ConceptOccurrence]:
    bounty_id = bounty.get("bounty_id")
    claim_id = bounty.get("claim_id")
    if not isinstance(bounty_id, str) or not isinstance(claim_id, str):
        return []
    claim = claims_by_id.get(claim_id)
    if claim is None:
        return []
    source_pair = _first_source_pair(
        [value for value in bounty.get("source_observation_ids", []) if isinstance(value, str)],
        [value for value in claim.get("source_evidence_ids", []) if isinstance(value, str)],
    )
    if source_pair is None:
        return []
    source_observation_id, source_evidence_id = source_pair
    observation = observations_by_id.get(source_observation_id)
    if observation is None:
        return []
    timestamp = _timestamp_value(observation.get("timestamp"))
    if timestamp is None:
        return []

    occurrences: list[ConceptOccurrence] = []
    for source_field in ("claim_type", "expected_source_types"):
        for concept in _record_values(bounty, source_field):
            occurrences.append(
                ConceptOccurrence(
                    event=_event(
                        source_artifact="bounties.jsonl",
                        source_field=source_field,
                        concept=concept,
                        timestamp=timestamp,
                        source_observation_id=source_observation_id,
                        source_evidence_id=source_evidence_id,
                    ),
                    source_artifact="bounties.jsonl",
                    source_field=source_field,
                    source_claim_id=claim_id,
                    source_bounty_id=bounty_id,
                )
            )
    return occurrences


def _build_occurrences(inputs: TimelineInputs) -> tuple[list[ConceptOccurrence], list[SkippedSourceEntry]]:
    observations_by_id = _observation_index(inputs.observations)
    claims_by_id = _claim_index(inputs.claims)
    occurrences: list[ConceptOccurrence] = []
    skipped_sources: list[SkippedSourceEntry] = []

    for observation in inputs.observations:
        observation_occurrences = _observation_occurrences(observation)
        if not observation_occurrences and isinstance(observation.get("observation_id"), str) and _timestamp_value(observation.get("timestamp")) is None:
            skipped_sources.append(
                _skip_entry(
                    source_artifact="observations.jsonl",
                    record_id=observation["observation_id"],
                    reason="missing_or_malformed_timestamp",
                    observation_id=observation["observation_id"],
                    evidence_id=observation.get("source_evidence_id") if isinstance(observation.get("source_evidence_id"), str) else None,
                )
            )
        occurrences.extend(observation_occurrences)

    for claim in inputs.claims:
        claim_occurrences = _claim_occurrences(claim, observations_by_id)
        if not claim_occurrences and isinstance(claim.get("claim_id"), str):
            source_pair = _first_source_pair(
                [value for value in claim.get("source_observation_ids", []) if isinstance(value, str)],
                [value for value in claim.get("source_evidence_ids", []) if isinstance(value, str)],
            )
            if source_pair is None:
                skipped_sources.append(
                    _skip_entry(
                        source_artifact="claims.jsonl",
                        record_id=claim["claim_id"],
                        reason="untraceable_source_ids",
                        observation_id=claim.get("source_observation_ids", [None])[0] if claim.get("source_observation_ids") else None,
                        evidence_id=claim.get("source_evidence_ids", [None])[0] if claim.get("source_evidence_ids") else None,
                    )
                )
            else:
                skipped_sources.append(
                    _skip_entry(
                        source_artifact="claims.jsonl",
                        record_id=claim["claim_id"],
                        reason="missing_or_malformed_timestamp",
                        observation_id=source_pair[0],
                        evidence_id=source_pair[1],
                    )
                )
        occurrences.extend(claim_occurrences)

    for bounty in inputs.bounties:
        bounty_occurrences = _bounty_occurrences(bounty, claims_by_id, observations_by_id)
        if not bounty_occurrences and isinstance(bounty.get("bounty_id"), str):
            bounty_record_observation_id = bounty.get("source_observation_ids", [None])[0] if bounty.get("source_observation_ids") else None
            bounty_claim = claims_by_id.get(bounty.get("claim_id")) if isinstance(bounty.get("claim_id"), str) else None
            bounty_record_evidence_id = (
                bounty_claim.get("source_evidence_ids", [None])[0]
                if isinstance(bounty_claim, dict) and bounty_claim.get("source_evidence_ids")
                else None
            )
            skipped_sources.append(
                _skip_entry(
                    source_artifact="bounties.jsonl",
                    record_id=bounty["bounty_id"],
                    reason="untraceable_or_missing_timestamp",
                    observation_id=bounty_record_observation_id if isinstance(bounty_record_observation_id, str) else None,
                    evidence_id=bounty_record_evidence_id if isinstance(bounty_record_evidence_id, str) else None,
                )
            )
        occurrences.extend(bounty_occurrences)

    occurrences.sort(
        key=lambda occurrence: (
            occurrence.event.timestamp,
            _ARTIFACT_PRIORITY[occurrence.source_artifact],
            occurrence.event.source_observation_id,
            occurrence.event.source_evidence_id,
            occurrence.event.concept,
            occurrence.event.event_id,
        )
    )
    skipped_sources.sort(
        key=lambda row: (
            _ARTIFACT_PRIORITY[row.source_artifact],
            row.record_id,
            row.reason,
            row.observation_id or "",
            row.evidence_id or "",
        )
    )
    return occurrences, skipped_sources


def _build_concept_timeline(occurrences: list[ConceptOccurrence]) -> list[ConceptTimelineEntry]:
    grouped: dict[str, dict[str, list[str] | list[int | float]]] = defaultdict(
        lambda: {
            "timestamps": [],
            "observation_ids": [],
            "claim_ids": [],
            "bounty_ids": [],
        }
    )
    for occurrence in occurrences:
        group = grouped[occurrence.event.concept]
        group["timestamps"].append(occurrence.event.timestamp)
        group["observation_ids"].append(occurrence.event.source_observation_id)
        if occurrence.source_claim_id is not None:
            group["claim_ids"].append(occurrence.source_claim_id)
        if occurrence.source_bounty_id is not None:
            group["bounty_ids"].append(occurrence.source_bounty_id)

    entries: list[ConceptTimelineEntry] = []
    for concept in sorted(grouped):
        group = grouped[concept]
        timestamps = list(group["timestamps"])
        entries.append(
            ConceptTimelineEntry(
                concept=concept,
                first_timestamp=min(timestamps),
                latest_timestamp=max(timestamps),
                total_occurrences=len(timestamps),
                supporting_observation_ids=sorted(dict.fromkeys(group["observation_ids"])),
                supporting_claim_ids=sorted(dict.fromkeys(group["claim_ids"])),
                supporting_bounty_ids=sorted(dict.fromkeys(group["bounty_ids"])),
            )
        )
    return entries


def _build_gap_windows(observations: list[dict[str, Any]]) -> list[GapWindow]:
    valid_observations = [
        observation
        for observation in observations
        if isinstance(observation.get("observation_id"), str) and _timestamp_value(observation.get("timestamp")) is not None
    ]
    ordered = sorted(
        valid_observations,
        key=lambda observation: (
            _timestamp_value(observation["timestamp"]),
            observation["observation_id"],
        ),
    )
    windows: list[GapWindow] = []
    for previous, current in zip(ordered, ordered[1:]):
        previous_timestamp = _timestamp_value(previous["timestamp"])
        current_timestamp = _timestamp_value(current["timestamp"])
        if previous_timestamp is None or current_timestamp is None:
            continue
        duration = current_timestamp - previous_timestamp
        if duration > _GAP_WINDOW_SECONDS:
            windows.append(
                GapWindow(
                    start_timestamp=previous_timestamp,
                    end_timestamp=current_timestamp,
                    duration=duration,
                    previous_observation=previous["observation_id"],
                    next_observation=current["observation_id"],
                )
            )
    return windows


def _build_maturity(
    concept_timeline: list[ConceptTimelineEntry],
    occurrences: list[ConceptOccurrence],
    *,
    global_latest_observation_timestamp: int | float | None,
) -> list[ConceptMaturityEntry]:
    occurrences_by_concept: dict[str, list[ConceptOccurrence]] = defaultdict(list)
    for occurrence in occurrences:
        occurrences_by_concept[occurrence.event.concept].append(occurrence)

    maturity: list[ConceptMaturityEntry] = []
    for entry in concept_timeline:
        concept_occurrences = sorted(
            occurrences_by_concept[entry.concept],
            key=lambda occurrence: (occurrence.event.timestamp, occurrence.event.event_id),
        )
        maturity.append(
            classify_concept_maturity(
                entry.concept,
                timestamps=[occurrence.event.timestamp for occurrence in concept_occurrences],
                global_latest_observation_timestamp=global_latest_observation_timestamp,
                supporting_source_ids=[
                    *[occurrence.event.source_observation_id for occurrence in concept_occurrences],
                    *[occurrence.event.source_evidence_id for occurrence in concept_occurrences],
                    *[occurrence.source_claim_id for occurrence in concept_occurrences if occurrence.source_claim_id is not None],
                    *[occurrence.source_bounty_id for occurrence in concept_occurrences if occurrence.source_bounty_id is not None],
                ],
                supporting_observation_ids=[occurrence.event.source_observation_id for occurrence in concept_occurrences],
                supporting_claim_ids=[
                    occurrence.source_claim_id
                    for occurrence in concept_occurrences
                    if occurrence.source_claim_id is not None
                ],
            )
        )
    return maturity


def _outstanding_bounties(bounties: list[dict[str, Any]]) -> list[OutstandingBountyEntry]:
    entries: list[OutstandingBountyEntry] = []
    for bounty in sorted(
        (record for record in bounties if isinstance(record, dict)),
        key=lambda record: (record.get("claim_type", ""), record.get("claim_id", ""), record.get("bounty_id", "")),
    ):
        if bounty.get("status") != "open":
            continue
        entries.append(
            OutstandingBountyEntry(
                bounty_id=str(bounty["bounty_id"]),
                claim_id=str(bounty["claim_id"]),
                claim_type=str(bounty["claim_type"]),
                status=str(bounty["status"]),
                expected_source_types=_dedup_preserve_order(
                    [value for value in bounty.get("expected_source_types", []) if isinstance(value, str)]
                ),
                source_observation_ids=_dedup_preserve_order(
                    [value for value in bounty.get("source_observation_ids", []) if isinstance(value, str)]
                ),
            )
        )
    return entries


def build_timeline_artifacts(
    observations_path: str | Path,
    claims_path: str | Path,
    bounties_path: str | Path,
    answer_path: str | Path,
    resolution_trace_path: str | Path,
    output_dir: str | Path,
) -> TimelineBuildResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs = _load_inputs(observations_path, claims_path, bounties_path, answer_path, resolution_trace_path)
    occurrences, _skipped_sources = _build_occurrences(inputs)
    global_latest_observation_timestamp = _global_latest_observation_timestamp(inputs.observations)
    concept_timeline = _build_concept_timeline(occurrences)
    maturity = _build_maturity(
        concept_timeline,
        occurrences,
        global_latest_observation_timestamp=global_latest_observation_timestamp,
    )
    gap_windows = _build_gap_windows(inputs.observations)
    outstanding_bounties = _outstanding_bounties(inputs.bounties)

    timeline_events_path = output_dir / "timeline_events.jsonl"
    concept_timeline_path = output_dir / "concept_timeline.json"
    concept_maturity_path = output_dir / "concept_maturity.json"
    gap_windows_path = output_dir / "gap_windows.jsonl"
    timeline_report_path = output_dir / "timeline_report.md"

    write_timeline_events(timeline_events_path, [occurrence.event for occurrence in occurrences])
    write_concept_timeline(concept_timeline_path, concept_timeline)
    write_concept_maturity(concept_maturity_path, maturity)
    write_gap_windows(gap_windows_path, gap_windows)
    write_timeline_report(
        timeline_report_path,
        concept_timeline=concept_timeline,
        events=[occurrence.event for occurrence in occurrences],
        maturity=maturity,
        gap_windows=gap_windows,
        outstanding_bounties=outstanding_bounties,
        skipped_sources=_skipped_sources,
    )

    return TimelineBuildResult(
        timeline_events_path=timeline_events_path,
        concept_timeline_path=concept_timeline_path,
        concept_maturity_path=concept_maturity_path,
        gap_windows_path=gap_windows_path,
        timeline_report_path=timeline_report_path,
    )
