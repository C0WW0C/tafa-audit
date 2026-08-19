from __future__ import annotations

import pytest


def test_local_storage_profile_is_safe_default():
    from core.storage_profile import resolve_storage_profile

    profile = resolve_storage_profile({"TAFA_MODE": "DEMO", "TAFA_PAPER_ONLY": "true"})

    assert profile.name == "local"
    assert profile.state_backend == "sqlite"
    assert profile.market_backend == "filesystem"
    assert profile.cache_backend == "memory"
    assert profile.cache_is_authoritative is False


def test_scaled_storage_requires_paper_demo_and_complete_endpoints():
    from core.storage_profile import StorageProfileError, resolve_storage_profile

    with pytest.raises(StorageProfileError, match="paper/demo"):
        resolve_storage_profile({"TAFA_STORAGE_PROFILE": "scaled", "TAFA_MODE": "LIVE", "TAFA_PAPER_ONLY": "false"})

    with pytest.raises(StorageProfileError, match="missing"):
        resolve_storage_profile({"TAFA_STORAGE_PROFILE": "scaled", "TAFA_MODE": "DEMO", "TAFA_PAPER_ONLY": "true"})


def test_scaled_storage_is_declarative_and_uses_expected_endpoints():
    from core.storage_profile import resolve_storage_profile

    profile = resolve_storage_profile(
        {
            "TAFA_STORAGE_PROFILE": "scaled",
            "TAFA_MODE": "DEMO",
            "TAFA_PAPER_ONLY": "true",
            "TAFA_POSTGRES_DSN": "postgresql://state_user:secret@db:5432/tafa",
            "TAFA_TIMESCALE_DSN": "postgresql://market_user:secret@db:5432/tafa",
            "TAFA_REDIS_URL": "redis://cache:6379/0",
        }
    )

    assert profile.state_backend == "postgresql"
    assert profile.market_backend == "timescaledb"
    assert profile.cache_backend == "redis"
    assert profile.paper_only is True
