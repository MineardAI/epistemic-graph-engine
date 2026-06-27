from __future__ import annotations

from typing import Iterable

from .schema import ConceptMaturityEntry, ConceptMaturityState


DEFAULT_GAP_WINDOW_DAYS = 30
_DEFAULT_GAP_WINDOW_SECONDS = DEFAULT_GAP_WINDOW_DAYS * 24 * 60 * 60


def classify_concept_maturity(
    concept: str,
    *,
    timestamps: Iterable[int | float],
    global_latest_observation_timestamp: int | float | None,
    supporting_source_ids: Iterable[str],
    supporting_observation_ids: Iterable[str],
    supporting_claim_ids: Iterable[str],
) -> ConceptMaturityEntry:
    ordered_timestamps = sorted(dict.fromkeys(timestamps))
    source_ids = sorted(dict.fromkeys(supporting_source_ids))
    observation_ids = sorted(dict.fromkeys(supporting_observation_ids))
    claim_ids = sorted(dict.fromkeys(supporting_claim_ids))

    if not ordered_timestamps:
        raise ValueError("concept maturity requires at least one timestamp")

    maturity_state = ConceptMaturityState.Mention
    state_reason = f"first valid occurrence at {ordered_timestamps[0]}"

    if len(ordered_timestamps) >= 3:
        maturity_state = ConceptMaturityState.Theme
        state_reason = (
            f"theme threshold met with {len(ordered_timestamps)} valid occurrences "
            f"across {len(ordered_timestamps)} distinct timestamps"
        )

    latest_activity_timestamp = ordered_timestamps[-1]
    if (
        global_latest_observation_timestamp is not None
        and global_latest_observation_timestamp - latest_activity_timestamp > _DEFAULT_GAP_WINDOW_SECONDS
    ):
        maturity_state = ConceptMaturityState.Dormant
        state_reason = (
            "dormant after trailing inactivity of "
            f"{global_latest_observation_timestamp - latest_activity_timestamp} seconds"
        )

    return ConceptMaturityEntry(
        concept=concept,
        maturity_state=maturity_state,
        state_reason=state_reason,
        supporting_source_ids=source_ids,
        supporting_observation_ids=observation_ids,
        supporting_claim_ids=claim_ids,
    )
