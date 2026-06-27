from __future__ import annotations

import json
from pathlib import Path

from epistemic_graph.claims.serialization import write_json, write_jsonl
from epistemic_graph.timeline import DEFAULT_GAP_WINDOW_DAYS, build_timeline_artifacts
from epistemic_graph.timeline.maturity import DEFAULT_GAP_WINDOW_DAYS as MATURITY_GAP_WINDOW_DAYS


SECONDS_PER_DAY = 24 * 60 * 60


def _timestamp(days: int) -> int:
    return days * SECONDS_PER_DAY


def _write_inputs(
    base_dir: Path,
    *,
    observations: list[dict[str, object]],
    claims: list[dict[str, object]],
    bounties: list[dict[str, object]],
    answer: dict[str, object] | None = None,
    trace: dict[str, object] | None = None,
) -> tuple[Path, Path, Path, Path, Path]:
    observations_path = base_dir / "observations.jsonl"
    claims_path = base_dir / "claims.jsonl"
    bounties_path = base_dir / "bounties.jsonl"
    answer_path = base_dir / "answer.json"
    trace_path = base_dir / "resolution_trace.json"

    write_jsonl(observations_path, observations)
    write_jsonl(claims_path, claims)
    write_jsonl(bounties_path, bounties)
    write_json(answer_path, answer or {"answer_id": "answer_1", "resolution_state": "unanswerable"})
    write_json(trace_path, trace or {"trace_id": "trace_1", "resolution_state": "unanswerable"})
    return observations_path, claims_path, bounties_path, answer_path, trace_path


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _report_section(report: str, title: str) -> str:
    start = report.index(title)
    remainder = report[start + len(title) :]
    next_heading = remainder.find("\n## ")
    if next_heading == -1:
        return remainder.strip()
    return remainder[:next_heading].strip()


def test_closed_whitelist_and_no_raw_text_extraction(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_1",
                "source_evidence_id": "evidence_1",
                "timestamp": _timestamp(0),
                "introduced_terms": [],
                "references": [],
                "event_type": "statement",
                "actor": "user",
                "raw_text": 'Quoted "Forbidden Concept" should not be mined.',
                "metadata_author": "tyrone",
            }
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    events = _load_jsonl(result.timeline_events_path)
    concepts = {event["concept"] for event in events}

    assert concepts == {"statement", "user"}
    assert "Forbidden Concept" not in concepts
    assert "metadata_author" not in concepts


def test_event_generation_granularity_and_missing_timestamp_skip(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_valid",
                "source_evidence_id": "evidence_valid",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha", "Beta"],
                "references": ["https://example.com"],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_skip",
                "source_evidence_id": "evidence_skip",
                "timestamp": None,
                "introduced_terms": ["Skipped"],
                "references": ["https://skip.invalid"],
                "event_type": "statement",
                "actor": "system",
            },
        ],
        claims=[
            {
                "claim_id": "claim_valid",
                "claim_type": "proposal",
                "claim_label": "assistant::proposal",
                "lifecycle": "proposed",
                "source_observation_ids": ["obs_valid"],
                "source_evidence_ids": ["evidence_valid"],
            },
            {
                "claim_id": "claim_skip",
                "claim_type": "proposal",
                "claim_label": "assistant::proposal",
                "lifecycle": "proposed",
                "source_observation_ids": ["obs_skip"],
                "source_evidence_ids": ["evidence_skip"],
            },
        ],
        bounties=[
            {
                "bounty_id": "bounty_valid",
                "claim_id": "claim_valid",
                "claim_type": "proposal",
                "status": "open",
                "missing_evidence": ["missing"],
                "expected_source_types": ["proposal follow-up observation", "archive note"],
                "potential_resolution_impact": "Could support the claim.",
                "source_observation_ids": ["obs_valid"],
            }
        ],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    events = _load_jsonl(result.timeline_events_path)
    concepts = [event["concept"] for event in events]

    assert len(events) == 10
    assert "Skipped" not in concepts
    assert "proposal follow-up observation" in concepts
    assert "archive note" in concepts


def test_timestamp_ordering_and_artifact_priority(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_b",
                "source_evidence_id": "evidence_b",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Beta"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_a",
                "source_evidence_id": "evidence_a",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[
            {
                "claim_id": "claim_a",
                "claim_type": "proposal",
                "claim_label": "assistant::proposal",
                "lifecycle": "proposed",
                "source_observation_ids": ["obs_a"],
                "source_evidence_ids": ["evidence_a"],
            }
        ],
        bounties=[
            {
                "bounty_id": "bounty_a",
                "claim_id": "claim_a",
                "claim_type": "proposal",
                "status": "open",
                "missing_evidence": ["missing"],
                "expected_source_types": ["proposal follow-up observation"],
                "potential_resolution_impact": "Could support the claim.",
                "source_observation_ids": ["obs_a"],
            }
        ],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    events = _load_jsonl(result.timeline_events_path)
    action_types = [event["action_type"] for event in events]
    concepts = [event["concept"] for event in events]

    observation_indices = [index for index, action_type in enumerate(action_types) if action_type.startswith("observations.jsonl.")]
    claim_indices = [index for index, action_type in enumerate(action_types) if action_type.startswith("claims.jsonl.")]
    bounty_indices = [index for index, action_type in enumerate(action_types) if action_type.startswith("bounties.jsonl.")]

    assert observation_indices
    assert claim_indices
    assert bounty_indices
    assert max(observation_indices) < min(claim_indices)
    assert max(claim_indices) < min(bounty_indices)
    assert concepts.index("Alpha") < concepts.index("Beta")


def test_gap_detection_and_default_window(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_1",
                "source_evidence_id": "evidence_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_2",
                "source_evidence_id": "evidence_2",
                "timestamp": _timestamp(DEFAULT_GAP_WINDOW_DAYS + 1),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_3",
                "source_evidence_id": "evidence_3",
                "timestamp": _timestamp(DEFAULT_GAP_WINDOW_DAYS + 2),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    windows = _load_jsonl(result.gap_windows_path)
    assert MATURITY_GAP_WINDOW_DAYS == 30
    assert len(windows) == 1
    window = windows[0]
    assert window["previous_observation"] == "obs_1"
    assert window["next_observation"] == "obs_2"
    assert window["duration"] > DEFAULT_GAP_WINDOW_DAYS * SECONDS_PER_DAY


def test_maturity_theme_and_dormant_states_are_source_gated(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_alpha_1",
                "source_evidence_id": "evidence_alpha_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_alpha_2",
                "source_evidence_id": "evidence_alpha_2",
                "timestamp": _timestamp(1),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_alpha_3",
                "source_evidence_id": "evidence_alpha_3",
                "timestamp": _timestamp(2),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_spec_1",
                "source_evidence_id": "evidence_spec_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Specification"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_spec_2",
                "source_evidence_id": "evidence_spec_2",
                "timestamp": _timestamp(1),
                "introduced_terms": ["Specification"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_spec_3",
                "source_evidence_id": "evidence_spec_3",
                "timestamp": _timestamp(2),
                "introduced_terms": ["Specification"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    maturity = {entry["concept"]: entry["maturity_state"] for entry in _load_json(result.concept_maturity_path)}
    assert maturity["Alpha"] == "Theme"
    assert maturity["Specification"] == "Theme"
    assert set(maturity.values()) <= {"Mention", "Theme", "Dormant"}
    assert maturity["Specification"] != "Specification"


def test_dormant_requires_trailing_inactivity_not_internal_gap_day_0_day_1_day_100(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_alpha_1",
                "source_evidence_id": "evidence_alpha_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_alpha_2",
                "source_evidence_id": "evidence_alpha_2",
                "timestamp": _timestamp(1),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_alpha_3",
                "source_evidence_id": "evidence_alpha_3",
                "timestamp": _timestamp(100),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    maturity = {entry["concept"]: entry["maturity_state"] for entry in _load_json(result.concept_maturity_path)}
    assert maturity["Alpha"] == "Theme"


def test_dormant_requires_trailing_inactivity_single_concept_day_0_and_global_day_31_plus(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_alpha",
                "source_evidence_id": "evidence_alpha",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_beta",
                "source_evidence_id": "evidence_beta",
                "timestamp": _timestamp(DEFAULT_GAP_WINDOW_DAYS + 1),
                "introduced_terms": ["Beta"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    maturity = {entry["concept"]: entry["maturity_state"] for entry in _load_json(result.concept_maturity_path)}
    assert maturity["Alpha"] == "Dormant"


def test_dormant_requires_trailing_inactivity_day_0_day_45_day_46_is_not_dormant(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_alpha_1",
                "source_evidence_id": "evidence_alpha_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_alpha_2",
                "source_evidence_id": "evidence_alpha_2",
                "timestamp": _timestamp(45),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_alpha_3",
                "source_evidence_id": "evidence_alpha_3",
                "timestamp": _timestamp(46),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    maturity = {entry["concept"]: entry["maturity_state"] for entry in _load_json(result.concept_maturity_path)}
    assert maturity["Alpha"] == "Theme"


def test_dormant_requires_trailing_inactivity_day_0_day_45_global_day_90_is_dormant(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_alpha_1",
                "source_evidence_id": "evidence_alpha_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_alpha_2",
                "source_evidence_id": "evidence_alpha_2",
                "timestamp": _timestamp(45),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_beta",
                "source_evidence_id": "evidence_beta",
                "timestamp": _timestamp(90),
                "introduced_terms": ["Beta"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    maturity = {entry["concept"]: entry["maturity_state"] for entry in _load_json(result.concept_maturity_path)}
    assert maturity["Alpha"] == "Dormant"


def test_unsupported_maturity_states_are_not_assigned_without_explicit_evidence(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_spec_1",
                "source_evidence_id": "evidence_spec_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Specification"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_spec_2",
                "source_evidence_id": "evidence_spec_2",
                "timestamp": _timestamp(1),
                "introduced_terms": ["Specification"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_spec_3",
                "source_evidence_id": "evidence_spec_3",
                "timestamp": _timestamp(2),
                "introduced_terms": ["Specification"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    maturity = {entry["concept"]: entry["maturity_state"] for entry in _load_json(result.concept_maturity_path)}
    assert maturity["Specification"] == "Theme"
    assert maturity["Specification"] not in {"Metaphor", "Project", "Component", "Specification", "Implementation", "Verified", "Abandoned"}


def test_skipped_sources_are_reported_and_deterministic(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_missing",
                "source_evidence_id": "evidence_missing",
                "timestamp": None,
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
            {
                "observation_id": "obs_malformed",
                "source_evidence_id": "evidence_malformed",
                "timestamp": "not-a-date",
                "introduced_terms": ["Beta"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            },
        ],
        claims=[],
        bounties=[],
    )

    first = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "first",
    )
    second = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "second",
    )

    report = first.timeline_report_path.read_text(encoding="utf-8")
    skipped_section = _report_section(report, "## Skipped Sources")

    assert "| Source Artifact | Record ID | Reason | Observation ID | Evidence ID |" in skipped_section
    assert "missing_or_malformed_timestamp" in skipped_section
    assert first.timeline_report_path.read_bytes() == second.timeline_report_path.read_bytes()
    assert first.timeline_events_path.read_bytes() == second.timeline_events_path.read_bytes()
    assert first.concept_timeline_path.read_bytes() == second.concept_timeline_path.read_bytes()
    assert first.concept_maturity_path.read_bytes() == second.concept_maturity_path.read_bytes()
    assert first.gap_windows_path.read_bytes() == second.gap_windows_path.read_bytes()
    assert skipped_section.count("\n| ") == 3


def test_empty_section_rendering_and_report_sorting(tmp_path: Path) -> None:
    observations_path, claims_path, bounties_path, answer_path, trace_path = _write_inputs(
        tmp_path,
        observations=[
            {
                "observation_id": "obs_1",
                "source_evidence_id": "evidence_1",
                "timestamp": _timestamp(0),
                "introduced_terms": ["Alpha"],
                "references": [],
                "event_type": "statement",
                "actor": "user",
            }
        ],
        claims=[],
        bounties=[],
    )

    result = build_timeline_artifacts(
        observations_path,
        claims_path,
        bounties_path,
        answer_path,
        trace_path,
        tmp_path / "out",
    )

    report = result.timeline_report_path.read_text(encoding="utf-8")
    assert report.index("## Concept Summary") < report.index("## Chronological Events") < report.index("## Maturity Summary")
    assert report.index("## Maturity Summary") < report.index("## Detected Gap Windows") < report.index("## Skipped Sources")
    assert report.index("## Skipped Sources") < report.index("## Outstanding Bounties")
    assert "| concept | first_timestamp | latest_timestamp | total_occurrences | supporting_observation_ids | supporting_claim_ids | supporting_bounty_ids |" in report
    assert "| start_timestamp | end_timestamp | duration | previous_observation | next_observation |" in report
    assert "| Source Artifact | Record ID | Reason | Observation ID | Evidence ID |" in report
    assert "| bounty_id | claim_id | claim_type | status | expected_source_types | source_observation_ids |" in report

    gap_section = _report_section(report, "## Detected Gap Windows")
    skipped_section = _report_section(report, "## Skipped Sources")
    outstanding_section = _report_section(report, "## Outstanding Bounties")
    assert gap_section.count("\n| ") == 1
    assert skipped_section.count("\n| ") == 1
    assert outstanding_section.count("\n| ") == 1
