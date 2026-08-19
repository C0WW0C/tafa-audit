"""Contrat de persistance TAFA, sans connexion ni ordre réel.

Philosophie de ce module : le profil local SQLite reste le défaut de la
release paper/demo. Le profil ``scaled`` ne décrit qu'une cible PostgreSQL /
TimescaleDB / Redis et refuse toute configuration hors paper/demo. La connexion
aux services externes est volontairement hors de ce module afin de conserver un
démarrage déterministe et local tant qu'une migration n'a pas été validée.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


class StorageProfileError(RuntimeError):
    """Raised when a storage profile would weaken TAFA paper/demo safeguards."""


@dataclass(frozen=True)
class StorageProfile:
    """Resolved storage topology with durable state separated from cache."""

    name: str
    state_backend: str
    market_backend: str
    cache_backend: str
    state_dsn: str | None
    market_dsn: str | None
    cache_url: str | None
    paper_only: bool

    @property
    def cache_is_authoritative(self) -> bool:
        """Redis/in-memory data must never be the source of record."""
        return False


def _is_true(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def resolve_storage_profile(environ: Mapping[str, str] | None = None) -> StorageProfile:
    """Resolve the declared profile without opening a network connection.

    ``local`` is the release default. ``scaled`` may be selected only for a
    paper/demo deployment after PostgreSQL, the TimescaleDB extension and Redis
    have been provisioned separately. Redis is modeled strictly as a
    reconstructible cache for position/risk snapshots.
    """

    env = os.environ if environ is None else environ
    name = str(env.get("TAFA_STORAGE_PROFILE", "local")).strip().lower()
    mode = str(env.get("TAFA_MODE", "DEMO")).strip().upper()
    paper_only = _is_true(env.get("TAFA_PAPER_ONLY", "true"))

    if name not in {"local", "scaled"}:
        raise StorageProfileError("TAFA_STORAGE_PROFILE must be 'local' or 'scaled'.")
    if mode != "DEMO" or not paper_only:
        raise StorageProfileError("Storage profiles are restricted to TAFA paper/demo mode.")

    if name == "local":
        return StorageProfile(
            name="local",
            state_backend="sqlite",
            market_backend="filesystem",
            cache_backend="memory",
            state_dsn=None,
            market_dsn=None,
            cache_url=None,
            paper_only=True,
        )

    state_dsn = str(env.get("TAFA_POSTGRES_DSN", "")).strip()
    market_dsn = str(env.get("TAFA_TIMESCALE_DSN", state_dsn)).strip()
    cache_url = str(env.get("TAFA_REDIS_URL", "")).strip()
    missing = [
        label
        for label, value in (
            ("TAFA_POSTGRES_DSN", state_dsn),
            ("TAFA_TIMESCALE_DSN", market_dsn),
            ("TAFA_REDIS_URL", cache_url),
        )
        if not value
    ]
    if missing:
        raise StorageProfileError(f"Scaled storage profile missing: {', '.join(missing)}.")
    if not state_dsn.startswith(("postgres://", "postgresql://")):
        raise StorageProfileError("TAFA_POSTGRES_DSN must use a PostgreSQL URL.")
    if not market_dsn.startswith(("postgres://", "postgresql://")):
        raise StorageProfileError("TAFA_TIMESCALE_DSN must use a PostgreSQL URL.")
    if not cache_url.startswith(("redis://", "rediss://")):
        raise StorageProfileError("TAFA_REDIS_URL must use a Redis URL.")

    return StorageProfile(
        name="scaled",
        state_backend="postgresql",
        market_backend="timescaledb",
        cache_backend="redis",
        state_dsn=state_dsn,
        market_dsn=market_dsn,
        cache_url=cache_url,
        paper_only=True,
    )
