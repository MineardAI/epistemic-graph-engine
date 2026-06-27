from __future__ import annotations

import json
from pathlib import Path

from .schema import PublishProfile, PublishProfileName


ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = ROOT / "profiles"
AVAILABLE_PROFILE_NAMES = ("executive", "audit", "research", "timeline", "claim")


def profile_path(profile_name: PublishProfileName, profiles_dir: str | Path | None = None) -> Path:
    base_dir = Path(profiles_dir) if profiles_dir is not None else PROFILES_DIR
    return base_dir / f"{profile_name}.json"


def load_profile(profile_name: PublishProfileName, profiles_dir: str | Path | None = None) -> PublishProfile:
    path = profile_path(profile_name, profiles_dir)
    payload = json.loads(path.read_text(encoding="utf-8"))
    profile = PublishProfile.model_validate(payload)
    if profile.profile_name != profile_name:
        raise ValueError(f"profile file {path.name} declared {profile.profile_name!r}")
    return profile


def load_profiles(profiles_dir: str | Path | None = None) -> list[PublishProfile]:
    base_dir = Path(profiles_dir) if profiles_dir is not None else PROFILES_DIR
    profiles: list[PublishProfile] = []
    for profile_name in AVAILABLE_PROFILE_NAMES:
        profiles.append(load_profile(profile_name, base_dir))
    return profiles
