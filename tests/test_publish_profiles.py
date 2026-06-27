from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from epistemic_graph.publish import AVAILABLE_PROFILE_NAMES, load_profile, load_profiles


ROOT = Path(__file__).resolve().parents[1]


def test_profiles_load_with_expected_names_and_versions() -> None:
    profiles = load_profiles()

    assert [profile.profile_name for profile in profiles] == list(AVAILABLE_PROFILE_NAMES)
    assert all(profile.package_version == "0.1.0" for profile in profiles)
    assert all(profile.package_schema_version == "005.v0" for profile in profiles)


def test_profile_json_rejects_unknown_fields(tmp_path: Path) -> None:
    profile_path = ROOT / "profiles" / "executive.json"
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    payload["views"][0]["columns"][0]["unexpected"] = True

    invalid_profiles_dir = tmp_path / "profiles"
    invalid_profiles_dir.mkdir()
    (invalid_profiles_dir / "executive.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_profile("executive", invalid_profiles_dir)
