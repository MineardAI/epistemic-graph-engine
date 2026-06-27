from __future__ import annotations

import re

from ..hash_utils import stable_id
from ..claims.schema import ClaimLifecycle
from .schema import ExactTermLookup, QueryMode, ResolutionQuestion, TERM_FIELD_WHITELIST


_WHITESPACE = re.compile(r"\s+")


def _normalize_query_text(raw_query: str) -> str:
    text = _WHITESPACE.sub(" ", raw_query.strip())
    text = re.sub(r"\s*:\s*", ":", text)
    text = re.sub(r"\s*\.\s*", ".", text)
    text = re.sub(r"\s*=\s*", "=", text)
    return text


def _question_id_payload(
    raw_query: str,
    normalized_query: str,
    query_mode: QueryMode,
    exact_claim_ids: list[str],
    exact_observation_ids: list[str],
    exact_evidence_ids: list[str],
    exact_lifecycle_states: list[ClaimLifecycle],
    exact_term_lookups: list[ExactTermLookup],
    validation_errors: list[str],
) -> dict[str, object]:
    return {
        "raw_query": raw_query,
        "normalized_query": normalized_query,
        "query_mode": query_mode.value,
        "exact_claim_ids": exact_claim_ids,
        "exact_observation_ids": exact_observation_ids,
        "exact_evidence_ids": exact_evidence_ids,
        "exact_lifecycle_states": [state.value for state in exact_lifecycle_states],
        "exact_term_lookups": [lookup.model_dump(mode="json") for lookup in exact_term_lookups],
        "validation_errors": validation_errors,
    }


def plan_resolution_question(raw_query: str) -> ResolutionQuestion:
    normalized_query = _normalize_query_text(raw_query)
    validation_errors: list[str] = []
    exact_claim_ids: list[str] = []
    exact_observation_ids: list[str] = []
    exact_evidence_ids: list[str] = []
    exact_lifecycle_states: list[ClaimLifecycle] = []
    exact_term_lookups: list[ExactTermLookup] = []
    query_mode = QueryMode.unsupported

    if not normalized_query:
        validation_errors.append("empty query")
    else:
        prefix, separator, remainder = normalized_query.partition(":")
        mode = prefix.lower()
        if not separator:
            validation_errors.append("malformed query syntax")
        elif mode in {"claim", "observation", "evidence", "lifecycle"}:
            value = remainder
            if not value or any(char.isspace() for char in value):
                validation_errors.append("exact lookup value must be a single token")
            elif mode == "claim":
                query_mode = QueryMode.claim_id
                exact_claim_ids = [value]
            elif mode == "observation":
                query_mode = QueryMode.observation_id
                exact_observation_ids = [value]
            elif mode == "evidence":
                query_mode = QueryMode.evidence_id
                exact_evidence_ids = [value]
            elif mode == "lifecycle":
                try:
                    lifecycle = ClaimLifecycle(value)
                except ValueError:
                    validation_errors.append(f"unknown lifecycle state: {value}")
                else:
                    query_mode = QueryMode.lifecycle
                    exact_lifecycle_states = [lifecycle]
        elif mode == "term":
            term_prefix, term_sep, term_value = remainder.partition("=")
            artifact_field = term_prefix
            if not term_sep or "." not in artifact_field:
                validation_errors.append("malformed exact term lookup")
            else:
                artifact = ""
                field = ""
                for artifact_name in sorted(TERM_FIELD_WHITELIST, key=len, reverse=True):
                    prefix = f"{artifact_name}."
                    if artifact_field.lower().startswith(prefix):
                        artifact = artifact_name
                        field = artifact_field[len(prefix) :].lower()
                        break
                if not artifact:
                    validation_errors.append(f"unsupported exact-term artifact: {artifact_field.split('.', 1)[0].lower()}")
                elif field not in TERM_FIELD_WHITELIST[artifact]:
                    validation_errors.append(f"unsupported exact-term field: {artifact}.{field}")
                elif not term_value:
                    validation_errors.append("exact term value may not be empty")
                else:
                    query_mode = QueryMode.exact_term
                    exact_term_lookups = [ExactTermLookup(artifact=artifact, field=field, value=term_value)]
        else:
            validation_errors.append(f"unsupported query mode: {mode}")

    normalized_payload = _question_id_payload(
        raw_query=raw_query,
        normalized_query=normalized_query,
        query_mode=query_mode,
        exact_claim_ids=exact_claim_ids,
        exact_observation_ids=exact_observation_ids,
        exact_evidence_ids=exact_evidence_ids,
        exact_lifecycle_states=exact_lifecycle_states,
        exact_term_lookups=exact_term_lookups,
        validation_errors=validation_errors,
    )

    return ResolutionQuestion(
        question_id=stable_id("resolution-question", normalized_payload),
        raw_query=raw_query,
        normalized_query=normalized_query,
        query_mode=query_mode,
        exact_claim_ids=exact_claim_ids,
        exact_observation_ids=exact_observation_ids,
        exact_evidence_ids=exact_evidence_ids,
        exact_lifecycle_states=exact_lifecycle_states,
        exact_term_lookups=exact_term_lookups,
        validation_errors=validation_errors,
    )
