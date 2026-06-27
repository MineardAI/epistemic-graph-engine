from __future__ import annotations

import hashlib
from pathlib import Path

from epistemic_graph.publish import build_package


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.relative_to(root).as_posix())
    }


def test_repeated_runs_are_byte_identical(
    frozen_artifact_paths: dict[str, Path],
    tmp_path: Path,
) -> None:
    first = build_package("audit", tmp_path / "first", source_artifacts=frozen_artifact_paths)
    second = build_package("audit", tmp_path / "second", source_artifacts=frozen_artifact_paths)

    assert first.manifest.package_identity.package_id == second.manifest.package_identity.package_id
    assert first.manifest_path.read_bytes() == second.manifest_path.read_bytes()
    assert first.archive_path is not None and second.archive_path is not None
    assert first.archive_path.read_bytes() == second.archive_path.read_bytes()
    assert _tree_hashes(first.package_root) == _tree_hashes(second.package_root)
    assert first.output_paths and second.output_paths
