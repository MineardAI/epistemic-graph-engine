from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..claims.serialization import write_json, write_jsonl
from .schema import (
    ConceptMaturityEntry,
    ConceptTimelineEntry,
    GapWindow,
    OutstandingBountyEntry,
    SkippedSourceEntry,
    TimelineEvent,
)


def write_timeline_events(path: str | Path, events: Iterable[TimelineEvent]) -> None:
    write_jsonl(path, [event.model_dump(mode="json") for event in events])


def write_concept_timeline(path: str | Path, entries: Iterable[ConceptTimelineEntry]) -> None:
    write_json(path, [entry.model_dump(mode="json") for entry in entries])


def write_concept_maturity(path: str | Path, entries: Iterable[ConceptMaturityEntry]) -> None:
    write_json(path, [entry.model_dump(mode="json") for entry in entries])


def write_gap_windows(path: str | Path, windows: Iterable[GapWindow]) -> None:
    write_jsonl(path, [window.model_dump(mode="json") for window in windows])


def _table_lines(headers: list[str], rows: Iterable[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def _join(values: list[str]) -> str:
    return ", ".join(values)


def _empty_skipped_table() -> list[str]:
    return [
        "| Source Artifact | Record ID | Reason | Observation ID | Evidence ID |",
        "| --- | --- | --- | --- | --- |",
    ]


def _skipped_table_lines(rows: list[SkippedSourceEntry]) -> list[str]:
    lines = _empty_skipped_table()
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.source_artifact,
                    row.record_id,
                    row.reason,
                    row.observation_id or "",
                    row.evidence_id or "",
                ]
            )
            + " |"
        )
    return lines


def render_timeline_report(
    *,
    concept_timeline: list[ConceptTimelineEntry],
    events: list[TimelineEvent],
    maturity: list[ConceptMaturityEntry],
    gap_windows: list[GapWindow],
    outstanding_bounties: list[OutstandingBountyEntry],
    skipped_sources: list[SkippedSourceEntry],
) -> str:
    lines: list[str] = []

    lines.append("## Concept Summary")
    lines.extend(
        _table_lines(
            [
                "concept",
                "first_timestamp",
                "latest_timestamp",
                "total_occurrences",
                "supporting_observation_ids",
                "supporting_claim_ids",
                "supporting_bounty_ids",
            ],
            (
                [
                    entry.concept,
                    str(entry.first_timestamp),
                    str(entry.latest_timestamp),
                    str(entry.total_occurrences),
                    _join(entry.supporting_observation_ids),
                    _join(entry.supporting_claim_ids),
                    _join(entry.supporting_bounty_ids),
                ]
                for entry in concept_timeline
            ),
        )
    )

    lines.append("")
    lines.append("## Chronological Events")
    lines.extend(
        _table_lines(
            [
                "timestamp",
                "concept",
                "action_type",
                "source_observation_id",
                "source_evidence_id",
                "event_id",
            ],
            (
                [
                    str(event.timestamp),
                    event.concept,
                    event.action_type,
                    event.source_observation_id,
                    event.source_evidence_id,
                    event.event_id,
                ]
                for event in events
            ),
        )
    )

    lines.append("")
    lines.append("## Maturity Summary")
    lines.extend(
        _table_lines(
            [
                "concept",
                "maturity_state",
                "state_reason",
                "supporting_source_ids",
                "supporting_observation_ids",
                "supporting_claim_ids",
            ],
            (
                [
                    entry.concept,
                    entry.maturity_state.value,
                    entry.state_reason,
                    _join(entry.supporting_source_ids),
                    _join(entry.supporting_observation_ids),
                    _join(entry.supporting_claim_ids),
                ]
                for entry in maturity
            ),
        )
    )

    lines.append("")
    lines.append("## Detected Gap Windows")
    lines.extend(
        _table_lines(
            [
                "start_timestamp",
                "end_timestamp",
                "duration",
                "previous_observation",
                "next_observation",
            ],
            (
                [
                    str(window.start_timestamp),
                    str(window.end_timestamp),
                    str(window.duration),
                    window.previous_observation,
                    window.next_observation,
                ]
                for window in gap_windows
            ),
        )
    )

    lines.append("")
    lines.append("## Skipped Sources")
    lines.extend(_skipped_table_lines(skipped_sources))

    lines.append("")
    lines.append("## Outstanding Bounties")
    lines.extend(
        _table_lines(
            [
                "bounty_id",
                "claim_id",
                "claim_type",
                "status",
                "expected_source_types",
                "source_observation_ids",
            ],
            (
                [
                    bounty.bounty_id,
                    bounty.claim_id,
                    bounty.claim_type,
                    bounty.status,
                    _join(bounty.expected_source_types),
                    _join(bounty.source_observation_ids),
                ]
                for bounty in outstanding_bounties
            ),
        )
    )

    return "\n".join(lines) + "\n"


def write_timeline_report(
    path: str | Path,
    *,
    concept_timeline: list[ConceptTimelineEntry],
    events: list[TimelineEvent],
    maturity: list[ConceptMaturityEntry],
    gap_windows: list[GapWindow],
    outstanding_bounties: list[OutstandingBountyEntry],
    skipped_sources: list[SkippedSourceEntry],
) -> None:
    Path(path).write_text(
        render_timeline_report(
            concept_timeline=concept_timeline,
            events=events,
            maturity=maturity,
            gap_windows=gap_windows,
            outstanding_bounties=outstanding_bounties,
            skipped_sources=skipped_sources,
        ),
        encoding="utf-8",
    )
