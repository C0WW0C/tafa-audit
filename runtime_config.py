# ============================================================
# TAFA V10 — Runtime Configuration (Dashboard ↔ Bot)
# ============================================================
from __future__ import annotations

import errno
import json
import logging
import sys
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Set, Union

# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger("runtime_config")
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

# ============================================================
# CONSTANTES
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
CFG_FILE = ROOT / "data" / "runtime_config.json"
LOCK_FILE = CFG_FILE.with_suffix(".lock")

# Retry settings for atomic writes
_REPLACE_RETRIES = 6
_REPLACE_DELAY_SECONDS = 0.05

# Local thread lock for in-process operations
_local_lock = threading.RLock()

# ============================================================
# VERROU INTER-PROCESSEUR (cross-platform)
# ============================================================

try:
    import fcntl

    def _acquire_file_lock():
        """Acquire an exclusive inter-process file lock (Unix)."""
        _lock_file = open(LOCK_FILE, "w")
        fcntl.flock(_lock_file, fcntl.LOCK_EX)
        return _lock_file

    def _release_file_lock(_lock_file):
        """Release the inter-process file lock (Unix)."""
        fcntl.flock(_lock_file, fcntl.LOCK_UN)
        _lock_file.close()

except ImportError:
    import msvcrt

    def _acquire_file_lock():
        """Acquire an exclusive inter-process file lock (Windows)."""
        _lock_file = open(LOCK_FILE, "w+b")  # mode binaire requis pour msvcrt
        _lock_file.seek(0)
        msvcrt.locking(_lock_file.fileno(), msvcrt.LK_LOCK, 1)
        return _lock_file

    def _release_file_lock(_lock_file):
        """Release the inter-process file lock (Windows)."""
        _lock_file.seek(0)
        msvcrt.locking(_lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        _lock_file.close()


# ============================================================
# VALEURS PAR DÉFAUT
# ============================================================

DEFAULTS: Dict[str, Any] = {
    "symbol": "BTC-USDC",
    "capital": 1000.0,
    "risk_per_trade_pct": 2.0,
    "leverage": 1,
    "sl_pct": 1.2,
    "tp_ratio": 3.0,
    "trail_pct": 0.8,
    "use_trail": True,
    "max_open": 1,
    "min_conf": 0.40,
    "ma_fast": 12,
    "ma_slow": 55,
    "rsi_period": 14,
    "rsi_max": 60.0,
    "confirm_bars": 3,
    "min_slope": 0.01,
    "vol_mult": 1.15,
    "tsmom_lookback": 120,
    "tsmom_vol_span": 20,
    "ai_on": True,
    "learner_eta": 0.08,
    "expert_tsmom_enabled": True,
    "expert_tsmom_weight": 1.0,
    "expert_ema_cross_enabled": True,
    "expert_ema_cross_weight": 1.0,
    "expert_rsi_filter_enabled": True,
    "expert_rsi_filter_weight": 1.0,
    "expert_momentum_enabled": True,
    "expert_momentum_weight": 1.0,
    "expert_volume_enabled": True,
    "expert_volume_weight": 1.0,
    "parent_brain_eta": 0.02,
    "parent_weight_base_signal": 0.42,
    "parent_weight_regime": 0.23,
    "parent_weight_expert_agreement": 0.20,
    "parent_weight_momentum": 0.10,
    "parent_weight_volatility": 0.05,
    "lr": 0.01,
    "ai_conf": 0.70,
    "lookback": 60,
    "epochs": 50,
    "m_lstm": True,
    "m_trans": True,
    "m_rf": True,
    "m_gb": True,
    "pf_on": True,
    "pf_max": 0.45,
    "pf_rebal": 30,
    "foundation_models_on": False,
    "foundation_min_conf": 0.70,
    "foundation_context": 240,
    "foundation_timeout_s": 4.0,
}

# Définition des bornes pour les valeurs numériques
NUMERIC_LIMITS: Dict[str, Tuple[float, float]] = {
    "capital": (10.0, 10_000_000.0),
    "risk_per_trade_pct": (0.01, 5.0),
    "leverage": (1.0, 1.0),
    "sl_pct": (0.05, 25.0),
    "tp_ratio": (0.1, 20.0),
    "trail_pct": (0.0, 25.0),
    "max_open": (1.0, 1.0),
    "min_conf": (0.0, 1.0),
    "ma_fast": (3.0, 250.0),
    "ma_slow": (8.0, 500.0),
    "rsi_period": (5.0, 100.0),
    "rsi_max": (30.0, 95.0),
    "confirm_bars": (1.0, 20.0),
    "min_slope": (0.0, 1.0),
    "vol_mult": (0.1, 10.0),
    "tsmom_lookback": (5.0, 2000.0),
    "tsmom_vol_span": (5.0, 500.0),
    "lr": (0.000001, 1.0),
    "ai_conf": (0.0, 1.0),
    "lookback": (10.0, 2000.0),
    "epochs": (1.0, 10000.0),
    "pf_max": (0.01, 1.0),
    "pf_rebal": (1.0, 10000.0),
    "foundation_min_conf": (0.0, 1.0),
    "foundation_context": (60.0, 512.0),
    "foundation_timeout_s": (0.5, 15.0),
    "learner_eta": (0.001, 0.5),
    "expert_tsmom_weight": (0.0, 1.0),
    "expert_ema_cross_weight": (0.0, 1.0),
    "expert_rsi_filter_weight": (0.0, 1.0),
    "expert_momentum_weight": (0.0, 1.0),
    "expert_volume_weight": (0.0, 1.0),
    "parent_brain_eta": (0.001, 0.1),
    "parent_weight_base_signal": (0.0, 1.0),
    "parent_weight_regime": (0.0, 1.0),
    "parent_weight_expert_agreement": (0.0, 1.0),
    "parent_weight_momentum": (0.0, 1.0),
    "parent_weight_volatility": (0.0, 1.0),
}

# Clés booléennes
BOOL_KEYS: Set[str] = {
    "use_trail", "ai_on", "m_lstm", "m_trans", "m_rf", "m_gb", "pf_on",
    "foundation_models_on",
    "expert_tsmom_enabled", "expert_ema_cross_enabled", "expert_rsi_filter_enabled",
    "expert_momentum_enabled", "expert_volume_enabled",
}

# Clés entières
INTEGER_KEYS: Set[str] = {
    "leverage", "max_open", "ma_fast", "ma_slow", "rsi_period", "confirm_bars",
    "lookback", "epochs", "pf_rebal", "foundation_context", "tsmom_lookback",
    "tsmom_vol_span",
}

# ============================================================
# FONCTIONS DE CHARGEMENT / SAUVEGARDE (sans verrou)
# ============================================================

def _load_file_unlocked() -> Dict[str, Any]:
    """Charge le fichier JSON de configuration s'il existe (sans verrou)."""
    if not CFG_FILE.exists():
        return {}
    try:
        with CFG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        logger.warning(f"Contenu invalide dans {CFG_FILE}, utilisation des defaults")
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Échec de lecture de {CFG_FILE}: {exc}")
        return {}


def _save_file_unlocked(data: Dict[str, Any]) -> bool:
    """Écriture atomique avec retries (sans verrou)."""
    CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CFG_FILE.with_name(f".{CFG_FILE.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        for attempt in range(_REPLACE_RETRIES):
            try:
                os.replace(tmp, CFG_FILE)
                return True
            except OSError as exc:
                if not _is_retryable_os_error(exc) or attempt == _REPLACE_RETRIES - 1:
                    raise
                time.sleep(_REPLACE_DELAY_SECONDS * (attempt + 1))
    except OSError as exc:
        logger.error(f"Échec d'écriture de {CFG_FILE}: {exc}")
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return False


def _is_retryable_os_error(exc: OSError) -> bool:
    """Détermine si l'erreur OSError est transitoire."""
    if isinstance(exc, PermissionError):
        return True
    winerror = getattr(exc, "winerror", None)
    if winerror in {5, 32, 33}:
        return True
    err = getattr(exc, "errno", None)
    return err in {errno.EACCES, errno.EBUSY, errno.EPERM, errno.ETXTBSY}


# ============================================================
# NORMALISATION / VALIDATION
# ============================================================

def _normalize_payload(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Valide et normalise chaque champ du payload.
    Retourne (accepted, rejected).
    """
    accepted: Dict[str, Any] = {}
    rejected: Dict[str, str] = {}

    for key, value in (payload or {}).items():
        if key not in DEFAULTS:
            rejected[key] = "paramètre non pris en charge par le moteur actuel"
            continue

        # Traitement spécial pour 'symbol'
        if key == "symbol":
            symbol = str(value or "").upper().replace("/", "-").strip()
            if not symbol or len(symbol) > 24 or "-" not in symbol:
                rejected[key] = "symbole invalide, format attendu ex. BTC-USDC"
            else:
                accepted[key] = symbol
            continue

        # Booléens
        if key in BOOL_KEYS:
            if isinstance(value, bool):
                accepted[key] = value
            else:
                rejected[key] = "booléen attendu"
            continue

        # Numériques
        if key in NUMERIC_LIMITS:
            try:
                number = float(value)
                low, high = NUMERIC_LIMITS[key]
                if not (low <= number <= high):
                    raise ValueError(f"plage autorisée : {low} à {high}")
                # Type final
                if key in INTEGER_KEYS:
                    accepted[key] = int(number)
                else:
                    accepted[key] = number
            except (TypeError, ValueError) as exc:
                rejected[key] = str(exc) or "nombre invalide"
            continue

        # Autres (fallback)
        accepted[key] = value

    # Cohérence interne : ma_slow > ma_fast
    if "ma_fast" in accepted and "ma_slow" in accepted:
        if accepted["ma_slow"] <= accepted["ma_fast"]:
            rejected["ma_slow"] = "doit être strictement supérieur à ma_fast"
            accepted.pop("ma_slow", None)

    if "tp_ratio" in accepted and accepted.get("tp_ratio", 0) <= 1.0:
        rejected["tp_ratio"] = "doit être supérieur à 1.0 pour un ratio TP/SL positif"
        accepted.pop("tp_ratio", None)

    return accepted, rejected


# ============================================================
# API PUBLIQUE
# ============================================================

def get_config() -> Dict[str, Any]:
    """
    Retourne la configuration complète (defaults + config.py + fichier runtime).
    Utilise un verrou de fichier pour assurer la cohérence multi-process.
    """
    out = dict(DEFAULTS)

    # Surcharger avec config.py
    try:
        import config as C
        with _local_lock:
            out["symbol"] = getattr(C, "DEFAULT_SYMBOL", out["symbol"])
            out["capital"] = float(getattr(C, "INITIAL_CAPITAL", out["capital"]))
            out["risk_per_trade_pct"] = float(getattr(C, "RISK_PER_TRADE", 0.02)) * 100.0
            out["sl_pct"] = float(getattr(C, "STOP_LOSS_PERCENT", out["sl_pct"]))
            sl = max(float(getattr(C, "STOP_LOSS_PERCENT", 1.2)), 0.01)
            out["tp_ratio"] = float(getattr(C, "TAKE_PROFIT_PERCENT", 3.6)) / sl
            out["trail_pct"] = float(getattr(C, "TRAILING_PERCENT", out["trail_pct"]))
            out["ma_fast"] = int(getattr(C, "EMA_FAST", out["ma_fast"]))
            out["ma_slow"] = int(getattr(C, "EMA_SLOW", out["ma_slow"]))
            out["rsi_period"] = int(getattr(C, "RSI_PERIOD", out["rsi_period"]))
            out["foundation_models_on"] = bool(getattr(C, "FOUNDATION_MODELS_ENABLED", out["foundation_models_on"]))
            out["foundation_min_conf"] = float(getattr(C, "FOUNDATION_MIN_CONFIDENCE", out["foundation_min_conf"]))
            out["foundation_context"] = int(getattr(C, "FOUNDATION_CONTEXT", out["foundation_context"]))
            out["foundation_timeout_s"] = float(getattr(C, "FOUNDATION_TIMEOUT_S", out["foundation_timeout_s"]))
    except Exception as exc:
        logger.debug(f"Impossible de charger config.py: {exc}")

    # Acquérir le verrou de fichier et lire la configuration runtime
    lock = _acquire_file_lock()
    try:
        file_data = _load_file_unlocked()
        out.update(file_data)
    finally:
        _release_file_lock(lock)

    return out


def save_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sauvegarde un nouveau payload dans le fichier runtime et applique les changements.
    Retourne un statut granulaire.
    """
    clean, rejected = _normalize_payload(payload)

    lock = _acquire_file_lock()
    try:
        # Charger et normaliser tout le fichier existant
        cur = _load_file_unlocked()
        normalized_cur, cur_rejected = _normalize_payload(cur)
        # Fusionner les valeurs validées existantes avec les nouvelles
        merged = normalized_cur.copy()
        merged.update(clean)
        # Sauvegarder
        success = _save_file_unlocked(merged)
    finally:
        _release_file_lock(lock)

    # Appliquer les changements au runtime
    applied = apply_to_runtime(merged)

    # Déterminer le statut global
    if not success:
        status = "failed"
    elif rejected or cur_rejected:
        status = "partial"
    else:
        status = "ok"

    result = {
        "ok": success and not rejected,
        "status": status,
        "config": get_config(),
        "accepted": clean,
        "rejected": rejected,
        "existing_rejected": cur_rejected,
        "applied": applied,
    }
    return result


def apply_to_runtime(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Applique la configuration aux objets du runtime (risk_manager, strategy, config).
    Ne modifie que les paramètres présents dans cfg.
    """
    cfg = cfg or get_config()
    applied: Dict[str, Any] = {}

    # ========================
    # 1. Risk Manager
    # ========================
    try:
        from risk.risk_manager import risk_manager
        with _local_lock:
            if "risk_per_trade_pct" in cfg:
                val = float(cfg["risk_per_trade_pct"]) / 100.0
                risk_manager.risk_per_trade = val
                applied["risk_per_trade"] = val
            if "sl_pct" in cfg:
                val = float(cfg["sl_pct"])
                risk_manager.stop_loss_pct = val
                applied["stop_loss_pct"] = val
            if "tp_ratio" in cfg:
                sl = float(getattr(risk_manager, "stop_loss_pct", 1.2))
                tp = sl * float(cfg["tp_ratio"])
                risk_manager.take_profit_pct = tp
                applied["take_profit_pct"] = tp
            if "trail_pct" in cfg:
                val = float(cfg["trail_pct"])
                risk_manager.trailing_pct = val
                applied["trailing_pct"] = val
            if "capital" in cfg:
                applied["capital"] = float(cfg["capital"])
            if "use_trail" in cfg:
                risk_manager.use_trailing_stop = bool(cfg["use_trail"])
                applied["use_trailing_stop"] = bool(cfg["use_trail"])
    except Exception as exc:
        applied["risk_error"] = str(exc)
        logger.warning(f"Impossible d'appliquer au risk_manager: {exc}")

    # ========================
    # 2. Intelligent Strategy
    # ========================
    try:
        from trading.intelligent_strategy import IntelligentStrategy
        mapping = [
            ("ma_fast", "EMA_FAST", int),
            ("ma_slow", "EMA_SLOW", int),
            ("rsi_period", "RSI_PERIOD", int),
            ("rsi_max", "RSI_MAX_ENTRY", float),
            ("confirm_bars", "CONFIRM_BARS", int),
            ("min_slope", "MIN_SLOPE", float),
            ("vol_mult", "VOL_MULT", float),
            ("tsmom_lookback", "TSMOM_LOOKBACK", int),
            ("tsmom_vol_span", "TSMOM_VOL_SPAN", int),
            ("min_conf", "MIN_CONF", float),
        ]
        with _local_lock:
            for cfg_key, attr_name, converter in mapping:
                if cfg_key in cfg:
                    val = converter(cfg[cfg_key])
                    setattr(IntelligentStrategy, attr_name, val)
                    applied[cfg_key] = val
    except Exception as exc:
        applied["strategy_error"] = str(exc)
        logger.warning(f"Impossible d'appliquer à IntelligentStrategy: {exc}")

    # ========================
    # 3. Module config.py
    # ========================
    try:
        import config as C
        with _local_lock:
            if "symbol" in cfg:
                C.DEFAULT_SYMBOL = str(cfg["symbol"]).replace("/", "-")
                applied["symbol"] = C.DEFAULT_SYMBOL
            if "sl_pct" in cfg:
                C.STOP_LOSS_PERCENT = float(cfg["sl_pct"])
                applied["sl_pct"] = C.STOP_LOSS_PERCENT
            if "tp_ratio" in cfg and "sl_pct" in cfg:
                C.TAKE_PROFIT_PERCENT = float(cfg["sl_pct"]) * float(cfg["tp_ratio"])
                applied["take_profit_pct"] = C.TAKE_PROFIT_PERCENT
            if "risk_per_trade_pct" in cfg:
                C.RISK_PER_TRADE = float(cfg["risk_per_trade_pct"]) / 100.0
                applied["risk_per_trade"] = C.RISK_PER_TRADE
            if "ma_fast" in cfg:
                C.EMA_FAST = int(cfg["ma_fast"])
                applied["ema_fast"] = C.EMA_FAST
            if "ma_slow" in cfg:
                C.EMA_SLOW = int(cfg["ma_slow"])
                applied["ema_slow"] = C.EMA_SLOW
            if "rsi_period" in cfg:
                C.RSI_PERIOD = int(cfg["rsi_period"])
                applied["rsi_period"] = C.RSI_PERIOD
            if "trail_pct" in cfg:
                C.TRAILING_PERCENT = float(cfg["trail_pct"])
                applied["trail_pct"] = C.TRAILING_PERCENT
            if "use_trail" in cfg:
                C.TRAILING_STOP = bool(cfg["use_trail"])
                applied["use_trail"] = C.TRAILING_STOP
    except Exception as exc:
        applied["config_error"] = str(exc)
        logger.debug(f"Impossible de mettre à jour config.py: {exc}")

    # ========================
    # 4. Publier le statut
    # ========================
    try:
        from core.status_bridge import read, publish
        st = read() or {}
        st["params"] = dict(cfg)
        st["params_applied"] = dict(applied)
        publish(st, merge=True)
    except Exception as exc:
        logger.debug(f"Impossible de publier le statut: {exc}")

    return applied


# ============================================================
# INITIALISATION
# ============================================================

CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

if not CFG_FILE.exists():
    _save_file_unlocked(DEFAULTS)
    logger.info("Fichier runtime_config.json créé avec les valeurs par défaut.")

logger.info(f"Runtime config chargé depuis {CFG_FILE}")

# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_config",
    "save_config",
    "apply_to_runtime",
    "CFG_FILE",
]