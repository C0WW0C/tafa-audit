# ============================================================
# TAFA V10 — Manual Paper Orders (Cross‑process queue)
# ============================================================
from __future__ import annotations

import json
import logging
import sys
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from threading import RLock

logger = logging.getLogger("manual_paper_orders")
if not logger.handlers:
    # FIX Windows CP1252: force UTF-8 sur la console
    import io as _io
    _con = (_io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
            if sys.platform == "win32" else sys.stdout)
    handler = logging.StreamHandler(stream=_con)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

ROOT_DIR = Path(__file__).resolve().parents[1]
PENDING_DIR = ROOT_DIR / "data" / "manual_paper_orders" / "pending"
PROCESSING_DIR = ROOT_DIR / "data" / "manual_paper_orders" / "processing"
ERROR_DIR = ROOT_DIR / "data" / "manual_paper_orders" / "error"

DEFAULT_MIN_NOTIONAL_USD = 5.0
DEFAULT_MAX_NOTIONAL_USD = 250.0
MIN_NOTIONAL_USD = float(os.getenv("TAFA_MIN_PAPER_ORDER_USD", str(DEFAULT_MIN_NOTIONAL_USD)))
MAX_NOTIONAL_USD = float(os.getenv("TAFA_MAX_PAPER_ORDER_USD", str(DEFAULT_MAX_NOTIONAL_USD)))

PENDING_TTL_SECONDS = 300
PROCESSING_TTL_SECONDS = 60

_lock = RLock()  # ✅ verrou réentrant global


def _validate(symbol: Any, side: Any, notional: Any) -> Tuple[str, str, float]:
    symbol = str(symbol or "").upper().strip()
    side = str(side or "").upper().strip()

    try:
        notional = float(notional)
    except (TypeError, ValueError) as exc:
        raise ValueError("notional doit être un nombre") from exc

    if not symbol:
        raise ValueError("symbole vide")
    if "-" not in symbol:
        raise ValueError("symbole doit contenir '-' (ex: BTC-USDC)")
    if len(symbol) > 24:
        raise ValueError(f"symbole trop long: {len(symbol)} > 24")

    if side not in {"BUY", "SELL"}:
        raise ValueError(f"côté invalide: {side} (doit être BUY ou SELL)")

    if not math.isfinite(notional):
        raise ValueError("notional n'est pas un nombre fini")
    if notional < MIN_NOTIONAL_USD:
        raise ValueError(f"notional ({notional:.2f}) < minimum {MIN_NOTIONAL_USD:.2f} USD")
    if notional > MAX_NOTIONAL_USD:
        raise ValueError(f"notional ({notional:.2f}) > maximum {MAX_NOTIONAL_USD:.2f} USD")

    return symbol, side, round(notional, 8)


def enqueue(symbol: Any, side: Any, notional: Any) -> Dict[str, Any]:
    with _lock:
        symbol, side, notional = _validate(symbol, side, notional)

        request = {
            "id": uuid.uuid4().hex,
            "symbol": symbol,
            "side": side,
            "notional": notional,
            "source": "dashboard_manual_paper",
            "created_at": time.time(),
        }

        PENDING_DIR.mkdir(parents=True, exist_ok=True)

        tmp = PENDING_DIR / f".{request['id']}.tmp"
        target = PENDING_DIR / f"{request['id']}.json"

        try:
            tmp.write_text(json.dumps(request, separators=(",", ":")), encoding="utf-8")
            os.replace(tmp, target)
            logger.info(f"📥 Ordre papier enqueued: {symbol} {side} ${notional:.2f} (id={request['id']})")
        except OSError as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise OSError(f"Impossible d'écrire la requête: {exc}") from exc

        return request


def claim(limit: int = 5) -> List[Dict[str, Any]]:
    with _lock:
        limit = max(1, min(int(limit), 20))
        claimed: List[Dict[str, Any]] = []

        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
        ERROR_DIR.mkdir(parents=True, exist_ok=True)

        _cleanup_stale_files()

        pending_files = sorted(PENDING_DIR.glob("*.json"))[:limit]

        for pending in pending_files:
            processing = PROCESSING_DIR / pending.name
            try:
                os.replace(pending, processing)
                payload = json.loads(processing.read_text(encoding="utf-8"))
                payload["_processing_path"] = str(processing)
                claimed.append(payload)
                logger.debug(f"📦 Claimed order {pending.name}")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning(f"⚠️  Échec claim de {pending.name}: {exc}")
                if isinstance(exc, (json.JSONDecodeError, ValueError)):
                    try:
                        os.replace(pending, ERROR_DIR / pending.name)
                        logger.warning(f"📁 Fichier corrompu déplacé vers error/")
                    except OSError:
                        pass
                continue

        return claimed


def complete(request: Dict[str, Any]) -> None:
    with _lock:
        path_str = request.get("_processing_path")
        if not path_str:
            logger.warning("complete() appelé sans _processing_path")
            return

        try:
            path = Path(path_str)
            if path.exists():
                path.unlink()
                logger.debug(f"✅ Order completed: {path.name}")
            else:
                logger.debug(f"ℹ️  Order already removed: {path.name}")
        except OSError as exc:
            logger.warning(f"⚠️  Échec suppression {path_str}: {exc}")


def _cleanup_stale_files() -> None:
    now = time.time()
    for f in PENDING_DIR.glob("*.json"):
        if _is_stale(f, PENDING_TTL_SECONDS):
            try:
                f.unlink()
                logger.debug(f"🗑️  Suppression pending stale: {f.name}")
            except OSError:
                pass
    for f in PROCESSING_DIR.glob("*.json"):
        if _is_stale(f, PROCESSING_TTL_SECONDS):
            try:
                f.unlink()
                logger.debug(f"🗑️  Suppression processing stale: {f.name}")
            except OSError:
                pass


def _is_stale(filepath: Path, ttl: float) -> bool:
    try:
        mtime = filepath.stat().st_mtime
        return (time.time() - mtime) > ttl
    except OSError:
        return True


def get_pending_count() -> int:
    with _lock:
        try:
            return len(list(PENDING_DIR.glob("*.json")))
        except OSError:
            return 0


def get_processing_count() -> int:
    with _lock:
        try:
            return len(list(PROCESSING_DIR.glob("*.json")))
        except OSError:
            return 0


def clear_all() -> int:
    with _lock:
        count = 0
        for f in list(PENDING_DIR.glob("*.json")) + list(PROCESSING_DIR.glob("*.json")):
            try:
                f.unlink()
                count += 1
            except OSError:
                pass
        if count:
            logger.info(f"🧹 Nettoyage manuel: {count} fichiers supprimés")
        return count


# Initialisation
PENDING_DIR.mkdir(parents=True, exist_ok=True)
PROCESSING_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)

_cleanup_stale_files()

logger.info(
    f"✅ Manual Paper Orders ready "
    f"(min=${MIN_NOTIONAL_USD:.2f}, max=${MAX_NOTIONAL_USD:.2f})"
)

__all__ = [
    "enqueue",
    "claim",
    "complete",
    "get_pending_count",
    "get_processing_count",
    "clear_all",
    "MIN_NOTIONAL_USD",
    "MAX_NOTIONAL_USD",
]