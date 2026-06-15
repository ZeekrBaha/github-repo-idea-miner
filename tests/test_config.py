from pathlib import Path

import pytest

from reporadar.config import (
    DEFAULT_PROFILES_PATH,
    ProfileNotFoundError,
    load_profile,
    load_profiles,
)


def test_default_profiles_file_exists():
    assert DEFAULT_PROFILES_PATH.exists()


def test_load_profiles_includes_baha_ai_qa():
    profiles = load_profiles()
    assert "baha-ai-qa" in profiles
    assert len(profiles["baha-ai-qa"].queries) >= 5


def test_load_profile_returns_named_profile():
    profile = load_profile("baha-ai-qa")
    assert profile.name == "baha-ai-qa"
    assert all(isinstance(q, str) and q for q in profile.queries)


def test_unknown_profile_raises_clear_error():
    with pytest.raises(ProfileNotFoundError) as exc:
        load_profile("does-not-exist")
    assert "does-not-exist" in str(exc.value)


def test_load_profiles_from_custom_path(tmp_path: Path):
    custom = tmp_path / "p.yaml"
    custom.write_text(
        "profiles:\n  demo:\n    queries:\n      - 'foo bar'\n",
        encoding="utf-8",
    )
    profiles = load_profiles(custom)
    assert "demo" in profiles
    assert profiles["demo"].queries == ["foo bar"]


def test_empty_queries_profile_rejected(tmp_path: Path):
    custom = tmp_path / "p.yaml"
    custom.write_text("profiles:\n  bad:\n    queries: []\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_profiles(custom)
