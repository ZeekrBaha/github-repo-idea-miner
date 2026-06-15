"""Search-profile loading from ``configs/profiles.yaml``.

A profile is a named set of GitHub search queries. Loading is deliberately
strict: empty query lists are a configuration bug, so we fail loudly.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# configs/ lives at the package root, two levels up from this file's parent.
DEFAULT_PROFILES_PATH = Path(__file__).resolve().parents[2] / "configs" / "profiles.yaml"


class ProfileNotFoundError(KeyError):
    """Raised when a requested profile name is not present in the config."""


class SearchProfile(BaseModel):
    name: str
    description: str = ""
    queries: list[str] = Field(min_length=1)


def load_profiles(path: Path | None = None) -> dict[str, SearchProfile]:
    """Load all profiles from ``path`` (defaults to the bundled config).

    Raises ``ValueError`` if the file is malformed or a profile has no queries.
    """

    profiles_path = path or DEFAULT_PROFILES_PATH
    if not profiles_path.exists():
        raise FileNotFoundError(f"Profiles file not found: {profiles_path}")

    raw = yaml.safe_load(profiles_path.read_text(encoding="utf-8")) or {}
    profiles_section = raw.get("profiles")
    if not isinstance(profiles_section, dict) or not profiles_section:
        raise ValueError(f"No 'profiles' mapping found in {profiles_path}")

    profiles: dict[str, SearchProfile] = {}
    for name, body in profiles_section.items():
        body = body or {}
        queries = body.get("queries") or []
        if not queries:
            raise ValueError(f"Profile '{name}' has no queries")
        profiles[name] = SearchProfile(
            name=name,
            description=body.get("description", ""),
            queries=list(queries),
        )
    return profiles


def load_profile(name: str, path: Path | None = None) -> SearchProfile:
    """Load a single profile by name, raising ``ProfileNotFoundError`` if absent."""

    profiles = load_profiles(path)
    if name not in profiles:
        available = ", ".join(sorted(profiles)) or "(none)"
        raise ProfileNotFoundError(f"Unknown profile '{name}'. Available profiles: {available}")
    return profiles[name]
