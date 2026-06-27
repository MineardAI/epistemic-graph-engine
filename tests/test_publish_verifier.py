from __future__ import annotations

import json
from pathlib import Path

from epistemic_graph.publish import build_package, verify_package


def _copy_profiles_dir(source: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.json")):
        destination.joinpath(path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def test_verifier_accepts_valid_package_and_archive(
    frozen_artifact_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    result = build_package("audit", tmp_path / "audit", source_artifacts=frozen_artifact_paths)
    verification = verify_package(result.package_root, archive_path=result.archive_path)

    assert verification.schema_valid is True
    assert verification.manifest_valid is True
    assert verification.profile_valid is True
    assert verification.required_files_present is True
    assert verification.file_sizes_valid is True
    assert verification.hashes_valid is True
    assert verification.package_id_valid is True
    assert verification.archive_valid is True
    assert verification.errors == []


def test_verifier_flags_hash_mismatch(
    frozen_artifact_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    result = build_package("audit", tmp_path / "audit", source_artifacts=frozen_artifact_paths)
    tampered = result.package_root / "executive_summary.md"
    tampered.write_bytes(tampered.read_bytes().replace(b"package_identity", b"package_identitx", 1))

    verification = verify_package(result.package_root, archive_path=result.archive_path)

    assert verification.hashes_valid is False
    assert verification.file_sizes_valid is True
    assert any(error.startswith("hash_mismatch:executive_summary.md") for error in verification.errors)


def test_verifier_flags_size_mismatch(
    frozen_artifact_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    result = build_package("audit", tmp_path / "audit", source_artifacts=frozen_artifact_paths)
    tampered = result.package_root / "executive_summary.md"
    tampered.write_text(tampered.read_text(encoding="utf-8") + " ", encoding="utf-8")

    verification = verify_package(result.package_root, archive_path=result.archive_path)

    assert verification.file_sizes_valid is False
    assert any(error.startswith("size_mismatch:executive_summary.md") for error in verification.errors)


def test_verifier_flags_invalid_profile(
    frozen_artifact_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    result = build_package("claim", tmp_path / "claim", source_artifacts=frozen_artifact_paths)

    profiles_dir = _copy_profiles_dir(Path(__file__).resolve().parents[1] / "profiles", tmp_path / "profiles")
    invalid_profile = json.loads((profiles_dir / "claim.json").read_text(encoding="utf-8"))
    invalid_profile["unexpected"] = True
    (profiles_dir / "claim.json").write_text(json.dumps(invalid_profile), encoding="utf-8")

    verification = verify_package(result.package_root, archive_path=result.archive_path, profiles_dir=profiles_dir)

    assert verification.profile_valid is False
    assert any(error.startswith("profile_invalid") for error in verification.errors)


def test_verifier_reports_missing_declared_output(
    frozen_artifact_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    result = build_package("audit", tmp_path / "audit", source_artifacts=frozen_artifact_paths)

    baseline = verify_package(result.package_root, archive_path=result.archive_path)
    assert baseline.required_files_present is True
    assert baseline.hashes_valid is True
    assert baseline.errors == []

    missing_relative_path = result.manifest.outputs[0].relative_path
    missing_output = result.package_root / missing_relative_path
    missing_output.unlink()

    verification = verify_package(result.package_root, archive_path=result.archive_path)

    assert verification.required_files_present is False
    assert verification.hashes_valid is False
    assert verification.file_sizes_valid is False
    assert any(missing_relative_path in error for error in verification.errors)
