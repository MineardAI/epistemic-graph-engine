from __future__ import annotations

import hashlib
from pathlib import Path

from epistemic_graph.publish import build_package


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.relative_to(root).as_posix())
    }


def _hash_frozen_artifacts(frozen_artifact_paths: dict[str, Path]) -> dict[str, str]:
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in sorted(frozen_artifact_paths.items())}


def test_profile_include_exclude_rules_and_upstream_immutability(
    frozen_artifact_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    before = _hash_frozen_artifacts(frozen_artifact_paths)

    executive = build_package("executive", tmp_path / "executive", source_artifacts=frozen_artifact_paths)
    audit = build_package("audit", tmp_path / "audit", source_artifacts=frozen_artifact_paths)

    after = _hash_frozen_artifacts(frozen_artifact_paths)

    assert before == after
    assert executive.archive_path is not None
    assert audit.archive_path is not None
    assert (executive.package_root / "executive_summary.md").exists()
    assert not (executive.package_root / "evidence_report.md").exists()
    assert (audit.package_root / "evidence_report.md").exists()
    assert (audit.package_root / "claim_dossier.md").exists()
    assert (audit.package_root / "timeline_export.md").exists()

    executive_inputs = {item.relative_path for item in executive.manifest.inputs}
    audit_inputs = {item.relative_path for item in audit.manifest.inputs}

    assert "evidence.jsonl" not in executive_inputs
    assert "observations.jsonl" not in executive_inputs
    assert "evidence.jsonl" in audit_inputs
    assert "observations.jsonl" in audit_inputs

    assert executive.manifest.package_identity.profile_name == "executive"
    assert audit.manifest.package_identity.profile_name == "audit"
    assert executive.manifest.verification.schema_valid is True
    assert audit.manifest.verification.hashes_valid is True


def test_manifest_sections_are_present(tmp_path: Path, frozen_artifact_paths: dict[str, Path]) -> None:
    result = build_package("claim", tmp_path / "claim", source_artifacts=frozen_artifact_paths)
    manifest = result.manifest.model_dump(mode="json")

    assert list(manifest) == [
        "package_identity",
        "build_metadata",
        "inputs",
        "outputs",
        "verification",
    ]
    assert manifest["package_identity"]["package_schema_version"] == "005.v0"
    assert manifest["package_identity"]["package_version"] == "0.1.0"
    assert manifest["verification"]["errors"] == []
