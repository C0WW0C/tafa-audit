# Shared live status for Web / Streamlit dashboard ↔ Engine (multi-process)
from __future__ import annotations

import json
import logging
import errno
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
STATUS_FILE = ROOT / "data" / "live_status.json"
_lock = threading.Lock()
_log = logging.getLogger("status_bridge")
_REPLACE_RETRIES = 6
_REPLACE_DELAY_SECONDS = 0.05

_status: Dict[str, Any] = {
    "running": False,
    "updated_at": None,
    "symbol": "BTC-USDC",
    "last_price": None,
    "last_signal": "HOLD",
    "cycle": 0,
    "paper": {},
    "ai": {},
    "ws": {},
    "risk": {},
    "drawdown": 0,
    "mode": "PAPER",
    "state": "STOPPED",
}


def _is_retryable_replace_error(exc: OSError) -> bool:
    """Return whether Windows/POSIX may release the destination shortly."""
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {5, 32} or getattr(exc, "errno", None) in {
        errno.EACCES,
        errno.EBUSY,
        errno.EPERM,
    }


def _write_file(data: Dict[str, Any]) -> None:
    """Atomically publish status, retrying transient destination-file locks.

    Windows can reject ``os.replace`` while antivirus, Explorer, or another
    local reader briefly holds ``live_status.json``.  Each writer gets a
    unique temporary file, then retries the atomic replacement with bounded
    backoff.  No non-atomic overwrite fallback is used.
    """
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_FILE.with_name(
        f".{STATUS_FILE.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, default=str))
            handle.flush()
            os.fsync(handle.fileno())

        for attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(tmp, STATUS_FILE)
                return
            except OSError as exc:
                if not _is_retryable_replace_error(exc) or attempt == _REPLACE_RETRIES - 1:
                    raise
                time.sleep(_REPLACE_DELAY_SECONDS * (attempt + 1))
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            # A failed cleanup must never hide the original publishing error.
            pass


def publish(payload: Dict[str, Any], *, merge: bool = False) -> None:
    """Publish status to memory + data/live_status.json.

    merge=True keeps previous keys (stop / partial updates must not wipe
    equity/paper/ai for the dashboard).
    """
    global _status
    incoming = dict(payload or {})
    with _lock:
        if merge:
            base = dict(_status)
            try:
                if STATUS_FILE.exists():
                    file_data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
                    if isinstance(file_data, dict):
                        fts = file_data.get("updated_at") or 0
                        mts = base.get("updated_at") or 0
                        if fts >= mts:
                            base = dict(file_data)
            except Exception:
                pass
            for k, v in incoming.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    nested = dict(base[k])
                    nested.update(v)
                    base[k] = nested
                else:
                    base[k] = v
            data = base
        else:
            data = incoming
        data["updated_at"] = time.time()
        _status = data
        try:
            _write_file(data)
        except Exception as exc:
            _log.warning("publish failed: %s", exc)


def read() -> Dict[str, Any]:
    """Prefer freshest of memory vs data/live_status.json (cross-process)."""
    global _status
    try:
        if STATUS_FILE.exists():
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                with _lock:
                    file_ts = data.get("updated_at") or 0
                    mem_ts = _status.get("updated_at") or 0
                    if file_ts >= mem_ts:
                        _status = data
                        return dict(data)
                    return dict(_status)
    except Exception as exc:
        _log.warning("read failed: %s", exc)
    with _lock:
        return dict(_status)


def age_seconds() -> Optional[float]:
    data = read()
    ts = data.get("updated_at")
    if not isinstance(ts, (int, float)) or ts <= 0:
        return None
    return max(0.0, time.time() - float(ts))


def is_stale(max_age: float = 30.0) -> bool:
    age = age_seconds()
    return True if age is None else age > max_age


def get(key: str, default=None):
    """Accès direct à une clé du statut courant (thread-safe, sans I/O)."""
    with _lock:
        return _status.get(key, default)


def reset() -> None:
    """Réinitialise le statut en mémoire ET supprime le fichier JSON (utile pour les tests)."""
    global _status
    with _lock:
        _status = {"running": False, "updated_at": None}
        try:
            if STATUS_FILE.exists():
                STATUS_FILE.unlink()
        except OSError:
            pass
