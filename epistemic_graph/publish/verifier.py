from __future__ import annotations

from dataclasses import dataclass
import json
import tarfile
from pathlib import Path

from pydantic import ValidationError

from ..hash_utils import canonical_json, sha256_hex
from .profiles import load_profile
from .schema import (
    PackageIdentity,
    PackageManifest,
)


@dataclass(frozen=True)
class PackageVerificationResult:
    schema_valid: bool
    manifest_valid: bool
    profile_valid: bool
    required_files_present: bool
    file_sizes_valid: bool
    hashes_valid: bool
    package_id_valid: bool
    archive_valid: bool
    errors: list[str]


def _load_manifest(manifest_path: Path) -> PackageManifest | None:
    try:
        return PackageManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (ValidationError, json.JSONDecodeError):
        return None


def _artifact_hash(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _recompute_package_id(identity: PackageIdentity, input_hashes: list[str]) -> str:
    payload = {
        "package_schema_version": identity.package_schema_version,
        "profile_name": identity.profile_name,
        "source_hashes": sorted(input_hashes),
    }
    return sha256_hex(canonical_json(payload))


def _check_archive(archive_path: Path | None) -> bool:
    if archive_path is None:
        return True
    if not archive_path.exists():
        return False
    try:
        with tarfile.open(archive_path, "r:") as tar:
            tar.getmembers()
        return True
    except tarfile.TarError:
        return False


def verify_package(
    package_root: str | Path,
    *,
    archive_path: str | Path | None = None,
    profiles_dir: str | Path | None = None,
) -> PackageVerificationResult:
    package_root = Path(package_root)
    manifest_path = package_root / "package_manifest.json"
    errors: list[str] = []

    manifest = _load_manifest(manifest_path)
    schema_valid = manifest is not None
    manifest_valid = manifest is not None
    profile_valid = False
    required_files_present = False
    file_sizes_valid = False
    hashes_valid = False
    package_id_valid = False
    archive_valid = _check_archive(Path(archive_path) if archive_path is not None else None)

    if manifest is None:
        errors.append("manifest_invalid")
        return PackageVerificationResult(
            schema_valid=False,
            manifest_valid=False,
            profile_valid=False,
            required_files_present=False,
            file_sizes_valid=False,
            hashes_valid=False,
            package_id_valid=False,
            archive_valid=archive_valid,
            errors=errors,
        )

    try:
        profile = load_profile(manifest.package_identity.profile_name, profiles_dir)
        profile_valid = (
            profile.package_version == manifest.package_identity.package_version
            and profile.package_schema_version == manifest.package_identity.package_schema_version
        )
    except Exception as exc:  # pragma: no cover - defensive
        profile_valid = False
        errors.append(f"profile_invalid:{exc.__class__.__name__}")

    input_hashes = [item.sha256 for item in manifest.inputs]

    missing_outputs = [
        item.relative_path
        for item in manifest.outputs
        if not (package_root / item.relative_path).exists()
    ]
    required_files_present = not missing_outputs

    if required_files_present:
        file_sizes_valid = True
        hashes_valid = True
        for item in manifest.outputs:
            output_path = package_root / item.relative_path
            if output_path.stat().st_size != item.size_bytes:
                file_sizes_valid = False
                errors.append(f"size_mismatch:{item.relative_path}")
            if _artifact_hash(output_path) != item.sha256:
                hashes_valid = False
                errors.append(f"hash_mismatch:{item.relative_path}")
    else:
        file_sizes_valid = False
        hashes_valid = False
        for relative_path in sorted(missing_outputs):
            errors.append(f"missing_output:{relative_path}")

    package_id_valid = _recompute_package_id(manifest.package_identity, input_hashes) == manifest.package_identity.package_id

    return PackageVerificationResult(
        schema_valid=schema_valid,
        manifest_valid=manifest_valid,
        profile_valid=profile_valid,
        required_files_present=required_files_present,
        file_sizes_valid=file_sizes_valid,
        hashes_valid=hashes_valid,
        package_id_valid=package_id_valid,
        archive_valid=archive_valid,
        errors=sorted(dict.fromkeys(errors)),
    )
