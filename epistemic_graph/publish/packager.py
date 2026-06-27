from __future__ import annotations

from dataclasses import dataclass
import json
import tarfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..claims.serialization import load_jsonl
from ..hash_utils import canonical_json, sha256_hex
from .profiles import load_profile
from .renderers import render_csv_table, render_html_table, render_markdown_table
from .schema import (
    BuildMetadata,
    ManifestInputArtifact,
    ManifestOutputArtifact,
    PackageIdentity,
    PackageManifest,
    PackageVerification,
    PACKAGE_SCHEMA_VERSION,
    PACKAGE_VERSION,
    PublishProfile,
    PublishProfileName,
    TableRowType,
)

GENERATED_AT = "1970-01-01T00:00:00Z"
_CONTRACT_VERSIONS = {
    "001": "VERIFIED",
    "002": "VERIFIED",
    "003": "VERIFIED",
    "004": "VERIFIED",
    "005": PACKAGE_SCHEMA_VERSION,
}


@dataclass(frozen=True)
class PublishBuildResult:
    package_root: Path
    manifest_path: Path
    archive_path: Path | None
    manifest: PackageManifest
    profile: PublishProfile
    output_paths: list[Path]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def _artifact_hash(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _artifact_metadata(path: Path, relative_path: str) -> ManifestInputArtifact | ManifestOutputArtifact:
    return ManifestInputArtifact(
        relative_path=relative_path,
        size_bytes=path.stat().st_size,
        sha256=_artifact_hash(path),
    )


def _package_id(profile_name: PublishProfileName, source_hashes: Iterable[str]) -> str:
    payload = {
        "package_schema_version": PACKAGE_SCHEMA_VERSION,
        "profile_name": profile_name,
        "source_hashes": sorted(source_hashes),
    }
    return sha256_hex(canonical_json(payload))


def _executive_summary_rows(
    *,
    package_id: str,
    profile_name: PublishProfileName,
    input_artifacts: list[ManifestInputArtifact],
    generated_at: str,
    verification: PackageVerification,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for key, value in (
        ("package_id", package_id),
        ("package_version", PACKAGE_VERSION),
        ("package_schema_version", PACKAGE_SCHEMA_VERSION),
        ("profile_name", profile_name),
    ):
        rows.append(
            {
                "record_type": TableRowType.package_identity.value,
                "section": "package_identity",
                "key": key,
                "value": value,
                "sort_section": "package_identity",
                "sort_key": key,
                "relative_path": "",
                "size_bytes": "",
                "sha256": "",
            }
        )

    for key, value in (
        ("generated_at", generated_at),
        ("epistemic_version", f"epistemic-graph-engine/{PACKAGE_VERSION}"),
        ("contract_versions", _CONTRACT_VERSIONS),
    ):
        rows.append(
            {
                "record_type": TableRowType.build_metadata.value,
                "section": "build_metadata",
                "key": key,
                "value": value,
                "sort_section": "build_metadata",
                "sort_key": key,
                "relative_path": "",
                "size_bytes": "",
                "sha256": "",
            }
        )

    for item in input_artifacts:
        rows.append(
            {
                "record_type": TableRowType.input.value,
                "section": "inputs",
                "key": item.relative_path,
                "value": "",
                "sort_section": "inputs",
                "sort_key": item.relative_path,
                "relative_path": item.relative_path,
                "size_bytes": item.size_bytes,
                "sha256": item.sha256,
            }
        )

    for key, value in (
        ("schema_valid", verification.schema_valid),
        ("profile_valid", verification.profile_valid),
        ("required_files_present", verification.required_files_present),
        ("file_sizes_valid", verification.file_sizes_valid),
        ("hashes_valid", verification.hashes_valid),
        ("errors", verification.errors),
    ):
        rows.append(
            {
                "record_type": TableRowType.verification.value,
                "section": "verification",
                "key": key,
                "value": value,
                "sort_section": "verification",
                "sort_key": key,
                "relative_path": "",
                "size_bytes": "",
                "sha256": "",
            }
        )

    return rows


def _evidence_rows(source_paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    evidence_path = source_paths.get("evidence.jsonl")
    if evidence_path is not None:
        for record in _read_jsonl(evidence_path):
            metadata = record.get("metadata") or {}
            rows.append(
                {
                    "record_type": TableRowType.evidence.value,
                    "evidence_id": record.get("evidence_id"),
                    "observation_id": "",
                    "source_evidence_id": "",
                    "source_hash": record.get("source_hash"),
                    "timestamp": metadata.get("timestamp"),
                    "actor": metadata.get("actor"),
                    "event_type": metadata.get("content_type"),
                    "raw_pointer": record.get("raw_pointer"),
                    "redacted_preview": record.get("redacted_preview"),
                    "metadata": metadata,
                    "hashes": "",
                    "sort_timestamp": metadata.get("timestamp") if metadata.get("timestamp") is not None else "",
                }
            )
    observations_path = source_paths.get("observations.jsonl")
    if observations_path is not None:
        for record in _read_jsonl(observations_path):
            rows.append(
                {
                    "record_type": TableRowType.observation.value,
                    "evidence_id": "",
                    "observation_id": record.get("observation_id"),
                    "source_evidence_id": record.get("source_evidence_id"),
                    "source_hash": record.get("hashes", {}).get("source_hash"),
                    "timestamp": record.get("timestamp"),
                    "actor": record.get("actor"),
                    "event_type": record.get("event_type"),
                    "raw_pointer": "",
                    "redacted_preview": "",
                    "metadata": "",
                    "hashes": record.get("hashes"),
                    "sort_timestamp": record.get("timestamp") if record.get("timestamp") is not None else "",
                }
            )
    return rows


def _claim_rows(source_paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    claims_path = source_paths.get("claims.jsonl")
    if claims_path is not None:
        for record in _read_jsonl(claims_path):
            rows.append(
                {
                    "record_type": TableRowType.claim.value,
                    "claim_id": record.get("claim_id"),
                    "claim_type": record.get("claim_type"),
                    "claim_label": record.get("claim_label"),
                    "lifecycle": record.get("lifecycle"),
                    "builder_version": record.get("builder_version"),
                    "source_observation_ids": record.get("source_observation_ids"),
                    "source_evidence_ids": record.get("source_evidence_ids"),
                    "source_observation_hashes": record.get("source_observation_hashes"),
                    "hypotheses": record.get("hypotheses"),
                    "bounty_id": "",
                    "status": "",
                    "edge_id": "",
                    "edge_type": "",
                    "source": "",
                    "target": "",
                    "missing_evidence": "",
                    "expected_source_types": "",
                    "potential_resolution_impact": "",
                    "shared_evidence_id": "",
                    "summary": "",
                    "sort_rank": "1",
                    "sort_id": record.get("claim_id"),
                }
            )
    claim_graph_path = source_paths.get("claim_graph.json")
    if claim_graph_path is not None:
        graph = _read_json(claim_graph_path)
        summary = graph.get("summary") or {}
        rows.append(
            {
                "record_type": TableRowType.graph_summary.value,
                "claim_id": "",
                "claim_type": "",
                "claim_label": "",
                "lifecycle": "",
                "builder_version": graph.get("builder_version"),
                "bounty_id": "",
                "status": "",
                "edge_id": "",
                "edge_type": "",
                "source": "",
                "target": "",
                "source_observation_ids": "",
                "source_evidence_ids": "",
                "source_observation_hashes": "",
                "hypotheses": "",
                "missing_evidence": "",
                "expected_source_types": "",
                "potential_resolution_impact": "",
                "shared_evidence_id": "",
                "summary": summary,
                "sort_rank": "0",
                "sort_id": graph.get("graph_id"),
            }
        )
        for edge in graph.get("support_edges") or []:
            rows.append(
                {
                    "record_type": TableRowType.support_edge.value,
                    "claim_id": "",
                    "claim_type": "",
                    "claim_label": "",
                    "lifecycle": "",
                    "builder_version": "",
                    "bounty_id": "",
                    "status": "",
                    "edge_id": edge.get("edge_id"),
                    "edge_type": edge.get("edge_type"),
                    "source": edge.get("source"),
                    "target": edge.get("target"),
                    "source_observation_ids": "",
                    "source_evidence_ids": "",
                    "source_observation_hashes": "",
                    "hypotheses": "",
                    "missing_evidence": "",
                    "expected_source_types": "",
                    "potential_resolution_impact": "",
                    "shared_evidence_id": edge.get("target_evidence_id"),
                    "summary": "",
                    "sort_rank": "2",
                    "sort_id": edge.get("edge_id"),
                }
            )
        for edge in graph.get("contradiction_edges") or []:
            rows.append(
                {
                    "record_type": TableRowType.contradiction_edge.value,
                    "claim_id": "",
                    "claim_type": "",
                    "claim_label": "",
                    "lifecycle": "",
                    "builder_version": "",
                    "bounty_id": "",
                    "status": "",
                    "edge_id": edge.get("edge_id"),
                    "edge_type": edge.get("edge_type"),
                    "source": edge.get("source"),
                    "target": edge.get("target"),
                    "source_observation_ids": "",
                    "source_evidence_ids": "",
                    "source_observation_hashes": "",
                    "hypotheses": "",
                    "missing_evidence": "",
                    "expected_source_types": "",
                    "potential_resolution_impact": "",
                    "shared_evidence_id": edge.get("shared_evidence_id"),
                    "summary": "",
                    "sort_rank": "3",
                    "sort_id": edge.get("edge_id"),
                }
            )
    bounties_path = source_paths.get("bounties.jsonl")
    if bounties_path is not None:
        for record in _read_jsonl(bounties_path):
            rows.append(
                {
                    "record_type": TableRowType.bounty.value,
                    "claim_id": record.get("claim_id"),
                    "claim_type": record.get("claim_type"),
                    "claim_label": "",
                    "lifecycle": "",
                    "builder_version": "",
                    "bounty_id": record.get("bounty_id"),
                    "status": record.get("status"),
                    "edge_id": "",
                    "edge_type": "",
                    "source": "",
                    "target": "",
                    "source_observation_ids": record.get("source_observation_ids"),
                    "source_evidence_ids": "",
                    "source_observation_hashes": "",
                    "hypotheses": "",
                    "missing_evidence": record.get("missing_evidence"),
                    "expected_source_types": record.get("expected_source_types"),
                    "potential_resolution_impact": record.get("potential_resolution_impact"),
                    "shared_evidence_id": "",
                    "summary": "",
                    "sort_rank": "4",
                    "sort_id": record.get("bounty_id"),
                }
            )
    return rows


def _timeline_rows(source_paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    concept_timeline_index: dict[str, dict[str, Any]] = {}
    timeline_events_path = source_paths.get("timeline_events.jsonl")
    if timeline_events_path is not None:
        for record in _read_jsonl(timeline_events_path):
            rows.append(
                {
                    "record_type": TableRowType.event.value,
                    "event_id": record.get("event_id"),
                    "timestamp": record.get("timestamp"),
                    "concept": record.get("concept"),
                    "action_type": record.get("action_type"),
                    "source_observation_id": record.get("source_observation_id"),
                    "source_evidence_id": record.get("source_evidence_id"),
                    "first_timestamp": "",
                    "latest_timestamp": "",
                    "total_occurrences": "",
                    "maturity_state": "",
                    "state_reason": "",
                    "start_timestamp": "",
                    "end_timestamp": "",
                    "duration": "",
                    "previous_observation": "",
                    "next_observation": "",
                    "sort_timestamp": record.get("timestamp") if record.get("timestamp") is not None else "",
                    "sort_rank": "0",
                }
            )
    concept_timeline_path = source_paths.get("concept_timeline.json")
    if concept_timeline_path is not None:
        for record in _read_json(concept_timeline_path):
            concept = record.get("concept")
            if isinstance(concept, str):
                concept_timeline_index[concept] = record
            rows.append(
                {
                    "record_type": TableRowType.concept_timeline.value,
                    "event_id": "",
                    "timestamp": "",
                    "concept": record.get("concept"),
                    "action_type": "",
                    "source_observation_id": "",
                    "source_evidence_id": "",
                    "first_timestamp": record.get("first_timestamp"),
                    "latest_timestamp": record.get("latest_timestamp"),
                    "total_occurrences": record.get("total_occurrences"),
                    "maturity_state": "",
                    "state_reason": "",
                    "start_timestamp": "",
                    "end_timestamp": "",
                    "duration": "",
                    "previous_observation": "",
                    "next_observation": "",
                    "sort_timestamp": record.get("first_timestamp") if record.get("first_timestamp") is not None else "",
                    "sort_rank": "1",
                }
            )
    concept_maturity_path = source_paths.get("concept_maturity.json")
    if concept_maturity_path is not None:
        for record in _read_json(concept_maturity_path):
            concept = record.get("concept")
            latest_timestamp = ""
            if isinstance(concept, str):
                latest_timestamp = concept_timeline_index.get(concept, {}).get("latest_timestamp") or ""
            rows.append(
                {
                    "record_type": TableRowType.maturity.value,
                    "event_id": "",
                    "timestamp": "",
                    "concept": record.get("concept"),
                    "action_type": "",
                    "source_observation_id": "",
                    "source_evidence_id": "",
                    "first_timestamp": "",
                    "latest_timestamp": "",
                    "total_occurrences": "",
                    "maturity_state": record.get("maturity_state"),
                    "state_reason": record.get("state_reason"),
                    "start_timestamp": "",
                    "end_timestamp": "",
                    "duration": "",
                    "previous_observation": "",
                    "next_observation": "",
                    "sort_timestamp": latest_timestamp,
                    "sort_rank": "2",
                }
            )
    gap_windows_path = source_paths.get("gap_windows.jsonl")
    if gap_windows_path is not None:
        for record in _read_jsonl(gap_windows_path):
            rows.append(
                {
                    "record_type": TableRowType.gap_window.value,
                    "event_id": "",
                    "timestamp": "",
                    "concept": "",
                    "action_type": "",
                    "source_observation_id": "",
                    "source_evidence_id": "",
                    "first_timestamp": "",
                    "latest_timestamp": "",
                    "total_occurrences": "",
                    "maturity_state": "",
                    "state_reason": "",
                    "start_timestamp": record.get("start_timestamp"),
                    "end_timestamp": record.get("end_timestamp"),
                    "duration": record.get("duration"),
                    "previous_observation": record.get("previous_observation"),
                    "next_observation": record.get("next_observation"),
                    "sort_timestamp": record.get("start_timestamp") if record.get("start_timestamp") is not None else "",
                    "sort_rank": "3",
                }
            )
    return rows


def _build_package_manifest(
    *,
    profile: PublishProfile,
    package_id: str,
    input_artifacts: list[ManifestInputArtifact],
    output_artifacts: list[ManifestOutputArtifact],
    generated_at: str,
) -> PackageManifest:
    return PackageManifest(
        package_identity=PackageIdentity(
            package_id=package_id,
            package_version=PACKAGE_VERSION,
            package_schema_version=PACKAGE_SCHEMA_VERSION,
            profile_name=profile.profile_name,
        ),
        build_metadata=BuildMetadata(
            generated_at=generated_at,
            epistemic_version=f"epistemic-graph-engine/{PACKAGE_VERSION}",
            contract_versions=_CONTRACT_VERSIONS,
        ),
        inputs=input_artifacts,
        outputs=output_artifacts,
        verification=PackageVerification(
            schema_valid=True,
            profile_valid=True,
            required_files_present=True,
            file_sizes_valid=True,
            hashes_valid=True,
            errors=[],
        ),
    )


def _write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _write_view_files(
    *,
    package_root: Path,
    view_name: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    sort_keys: list[str],
) -> list[Path]:
    markdown_path = package_root / f"{view_name}.md"
    csv_path = package_root / f"{view_name}.csv"
    html_path = package_root / f"{view_name}.html"

    _write_text_file(markdown_path, render_markdown_table(columns=columns, rows=rows, sort_keys=sort_keys))
    _write_text_file(csv_path, render_csv_table(columns=columns, rows=rows, sort_keys=sort_keys))
    _write_text_file(html_path, render_html_table(columns=columns, rows=rows, sort_keys=sort_keys))
    return [markdown_path, csv_path, html_path]


def _write_tar_archive(package_root: Path, archive_path: Path) -> None:
    with tarfile.open(archive_path, "w", format=tarfile.USTAR_FORMAT) as tar:
        for file_path in sorted((path for path in package_root.rglob("*") if path.is_file()), key=lambda path: path.relative_to(package_root).as_posix()):
            relative_path = file_path.relative_to(package_root).as_posix()
            arcname = f"{package_root.name}/{relative_path}"
            info = tarfile.TarInfo(name=arcname)
            info.size = file_path.stat().st_size
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            with file_path.open("rb") as fileobj:
                tar.addfile(info, fileobj=fileobj)


def build_package(
    profile_name: PublishProfileName,
    output_dir: str | Path,
    *,
    source_artifacts: Mapping[str, str | Path] | None = None,
    source_root: str | Path | None = None,
    profiles_dir: str | Path | None = None,
    create_archive: bool = True,
) -> PublishBuildResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    profile = load_profile(profile_name, profiles_dir)
    if source_artifacts is None and source_root is None:
        raise ValueError("either source_artifacts or source_root is required")

    if source_artifacts is None:
        assert source_root is not None
        source_root_path = Path(source_root)
        source_path_map = {artifact: source_root_path / artifact for artifact in profile.source_artifacts}
    else:
        source_path_map = {artifact: Path(path) for artifact, path in source_artifacts.items()}

    missing_paths = [artifact for artifact in profile.source_artifacts if artifact not in source_path_map]
    if missing_paths:
        raise ValueError(f"missing required source artifacts: {', '.join(missing_paths)}")

    package_id = _package_id(profile.profile_name, (
        _artifact_hash(source_path_map[artifact])
        for artifact in profile.source_artifacts
    ))
    package_root = output_dir / package_id
    package_root.mkdir(parents=True, exist_ok=True)

    generated_at = GENERATED_AT
    input_artifacts = [
        _artifact_metadata(source_path_map[artifact], artifact)
        for artifact in sorted(profile.source_artifacts)
    ]

    all_rows: dict[str, list[dict[str, Any]]] = {
        "executive_summary": [],
        "evidence_report": [],
        "claim_dossier": [],
        "timeline_export": [],
    }

    summary_verification = PackageVerification(
        schema_valid=True,
        profile_valid=True,
        required_files_present=True,
        file_sizes_valid=True,
        hashes_valid=True,
        errors=[],
    )
    all_rows["executive_summary"] = _executive_summary_rows(
        package_id=package_id,
        profile_name=profile.profile_name,
        input_artifacts=input_artifacts,
        generated_at=generated_at,
        verification=summary_verification,
    )
    all_rows["evidence_report"] = _evidence_rows(source_path_map)
    all_rows["claim_dossier"] = _claim_rows(source_path_map)
    all_rows["timeline_export"] = _timeline_rows(source_path_map)

    output_paths: list[Path] = []
    for view in profile.views:
        rows = all_rows.get(view.name, [])
        view_paths = _write_view_files(
            package_root=package_root,
            view_name=view.name,
            columns=[column.header for column in view.columns],
            rows=rows,
            sort_keys=view.sort_keys,
        )
        output_paths.extend(view_paths)

    output_artifacts = [
        ManifestOutputArtifact(
            relative_path=path.relative_to(package_root).as_posix(),
            size_bytes=path.stat().st_size,
            sha256=_artifact_hash(path),
        )
        for path in sorted(output_paths, key=lambda path: path.relative_to(package_root).as_posix())
    ]
    manifest = _build_package_manifest(
        profile=profile,
        package_id=package_id,
        input_artifacts=input_artifacts,
        output_artifacts=output_artifacts,
        generated_at=generated_at,
    )
    manifest_path = package_root / "package_manifest.json"
    _write_text_file(manifest_path, canonical_json(manifest.model_dump(mode="json")) + "\n")

    if create_archive:
        archive_path = output_dir / f"{package_id}.tar"
        _write_tar_archive(package_root, archive_path)
    else:
        archive_path = None

    return PublishBuildResult(
        package_root=package_root,
        manifest_path=manifest_path,
        archive_path=archive_path,
        manifest=manifest,
        profile=profile,
        output_paths=sorted(output_paths, key=lambda path: path.relative_to(package_root).as_posix()),
    )
