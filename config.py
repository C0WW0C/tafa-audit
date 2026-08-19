# ============================================================
# TAFA V7 PRO - CONFIGURATION ULTIMATE (corrigée)
# ============================================================
import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

_log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
_logger = logging.getLogger("TAFA_CONFIG")
# ✅ FIX Windows CP1252 : forcer UTF-8 sur la console
if sys.platform == "win32":
    import io as _io
    _stream = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
else:
    _stream = sys.stdout
_handler = logging.StreamHandler(stream=_stream)
_handler.setFormatter(logging.Formatter(_log_format))
_logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.propagate = False

def _get_env_str(key: str, default: str = "", required: bool = False) -> str:
    value = os.getenv(key, default).strip()
    if required and not value:
        _logger.error(f"❌ Variable requise manquante: {key}")
    return value

def _get_env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key, str(default)).lower().strip()
    return value in ("true", "1", "yes", "on", "y")

def _get_env_int(key: str, default: int, min_val: Optional[int] = None,
                 max_val: Optional[int] = None) -> int:
    try:
        value = int(os.getenv(key, str(default)))
        if min_val is not None and value < min_val:
            _logger.warning(f"⚠️  {key}={value} < {min_val} → fallback à {default}")
            return default
        if max_val is not None and value > max_val:
            _logger.warning(f"⚠️  {key}={value} > {max_val} → fallback à {default}")
            return default
        return value
    except (ValueError, TypeError):
        _logger.warning(f"⚠️  {key} invalide → fallback à {default}")
        return default

def _get_env_float(key: str, default: float, min_val: Optional[float] = None,
                   max_val: Optional[float] = None) -> float:
    try:
        value = float(os.getenv(key, str(default)))
        if min_val is not None and value < min_val:
            _logger.warning(f"⚠️  {key}={value} < {min_val} → fallback à {default}")
            return default
        if max_val is not None and value > max_val:
            _logger.warning(f"⚠️  {key}={value} > {max_val} → fallback à {default}")
            return default
        return value
    except (ValueError, TypeError):
        _logger.warning(f"⚠️  {key} invalide → fallback à {default}")
        return default

def _get_env_list(key: str, default: List[str], separator: str = ",") -> List[str]:
    raw = os.getenv(key, "")
    if not raw:
        return default
    items = [x.strip() for x in raw.split(separator) if x.strip()]
    return items if items else default

_BASE_DIR = Path(__file__).resolve().parent
_ENV_PATH = _BASE_DIR / ".env"

def _load_env_file() -> bool:
    if not _ENV_PATH.exists():
        _logger.warning(f"⚠️  Fichier .env non trouvé: {_ENV_PATH}")
        return False
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH)
        _logger.info(f"✅ Configuration chargée depuis {_ENV_PATH}")
        return True
    except ImportError:
        _logger.warning("⚠️  python-dotenv non installé → lecture directe des variables système")
        return False
    except Exception as e:
        _logger.error(f"❌ Erreur lors du chargement de .env: {e}")
        return False

_load_env_file()

APP_NAME = "TAFA_V7_PRO"
VERSION = "TAFA_V7_PRO_REFACTORED"

MODE = _get_env_str("TAFA_MODE", "DEMO").upper()
if MODE not in ("DEMO", "LIVE"):
    _logger.warning(f"⚠️  MODE={MODE} invalide → fallback à DEMO")
    MODE = "DEMO"

TAFA_ENGINE = _get_env_str("TAFA_ENGINE", "native").lower()
if TAFA_ENGINE not in ("native", "freqtrade", "passivbot", "hummingbot"):
    _logger.warning(f"⚠️  TAFA_ENGINE={TAFA_ENGINE} invalide → fallback à native")
    TAFA_ENGINE = "native"

DEBUG = _get_env_bool("TAFA_DEBUG", False)

OKX_API_KEY = _get_env_str("OKX_API_KEY", "")
OKX_SECRET_KEY = _get_env_str("OKX_SECRET_KEY", "")
OKX_PASSPHRASE = _get_env_str("OKX_PASSPHRASE", "")
OKX_DEMO = (MODE == "DEMO")

if MODE == "DEMO":
    OKX_WS_PUBLIC_DEFAULT = "wss://wspap.okx.com:8443/ws/v5/public"
    OKX_WS_PRIVATE_DEFAULT = "wss://wspap.okx.com:8443/ws/v5/private"
else:
    OKX_WS_PUBLIC_DEFAULT = "wss://ws.okx.com:8443/ws/v5/public"
    OKX_WS_PRIVATE_DEFAULT = "wss://ws.okx.com:8443/ws/v5/private"

OKX_WS_PUBLIC = _get_env_str("TAFA_OKX_WS_PUBLIC", OKX_WS_PUBLIC_DEFAULT)
OKX_WS_PRIVATE = _get_env_str("TAFA_OKX_WS_PRIVATE", OKX_WS_PRIVATE_DEFAULT)

def _validate_api_keys() -> bool:
    if MODE != "LIVE":
        return True
    errors = []
    if len(OKX_API_KEY) < 10:
        errors.append("OKX_API_KEY trop courte")
    if len(OKX_SECRET_KEY) < 10:
        errors.append("OKX_SECRET_KEY trop courte")
    if len(OKX_PASSPHRASE) < 4:
        errors.append("OKX_PASSPHRASE trop courte")
    if errors:
        for err in errors:
            _logger.critical(f"🔒 Clé API invalide: {err}")
        return False
    _logger.info("✅ Clés API OKX validées")
    return True

_DEFAULT_SYMBOLS = ["BTC-USDC", "ETH-USDC", "SOL-USDC", "XRP-USDC", "DOGE-USDC"]
SYMBOLS = _get_env_list("TAFA_SYMBOLS", _DEFAULT_SYMBOLS)
if not SYMBOLS:
    SYMBOLS = _DEFAULT_SYMBOLS

DEFAULT_SYMBOL = _get_env_str("TAFA_DEFAULT_SYMBOL", "BTC-USDC")
if DEFAULT_SYMBOL not in SYMBOLS:
    _logger.warning(f"⚠️  {DEFAULT_SYMBOL} non dans SYMBOLS → fallback à {SYMBOLS[0]}")
    DEFAULT_SYMBOL = SYMBOLS[0]

QUOTE_CURRENCY = _get_env_str("TAFA_QUOTE_CURRENCY", "USDC").upper()
if QUOTE_CURRENCY not in ("USDC", "USDT", "USD"):
    QUOTE_CURRENCY = "USDC"

INITIAL_CAPITAL = _get_env_float("TAFA_PAPER_CAPITAL", 1000.0, min_val=10.0, max_val=1_000_000.0)
ORDER_SIZE_USD = _get_env_float("TAFA_ORDER_SIZE_USD", 100.0, min_val=10.0, max_val=10000.0)
MIN_ORDER_USD = _get_env_float("TAFA_MIN_ORDER_USD", 10.0, min_val=1.0)
PAPER_SESSION_NET_TARGET_USD = _get_env_float("TAFA_PAPER_SESSION_NET_TARGET_USD", 0.0, min_val=0.0)

MAX_OPEN_POSITIONS = _get_env_int("TAFA_MAX_OPEN_POSITIONS", 5, min_val=1, max_val=20)
_AUTO_POSITIONS = max(1, int(INITIAL_CAPITAL / (ORDER_SIZE_USD * 1.5)))
if MAX_OPEN_POSITIONS > _AUTO_POSITIONS and INITIAL_CAPITAL < 5000:
    _logger.info(f"ℹ️  MAX_OPEN_POSITIONS réduit de {MAX_OPEN_POSITIONS} à {_AUTO_POSITIONS} (capital limité)")
    MAX_OPEN_POSITIONS = _AUTO_POSITIONS

GRID_ENABLED = _get_env_bool("TAFA_GRID_ENABLED", True)
ENABLE_GRID = GRID_ENABLED

GRID_MODE = _get_env_str("TAFA_GRID_MODE", "ADAPTIVE").upper()
if GRID_MODE not in ("ADAPTIVE", "FIXED", "VOLATILITY"):
    GRID_MODE = "ADAPTIVE"

GRID_LEVELS = _get_env_int("TAFA_GRID_LEVELS", 12, min_val=2, max_val=50)
GRID_STEP_PERCENT = _get_env_float("TAFA_GRID_STEP_PERCENT", 0.35, min_val=0.05, max_val=5.0)
GRID_MIN_STEP = _get_env_float("TAFA_GRID_MIN_STEP", 0.15, min_val=0.05, max_val=1.0)
GRID_MAX_STEP = _get_env_float("TAFA_GRID_MAX_STEP", 1.20, min_val=0.5, max_val=5.0)

AUTO_ATR_GRID = _get_env_bool("TAFA_AUTO_ATR_GRID", True)
ATR_PERIOD = _get_env_int("TAFA_ATR_PERIOD", 14, min_val=5, max_val=50)
ATR_MULTIPLIER = _get_env_float("TAFA_ATR_MULTIPLIER", 1.8, min_val=0.5, max_val=5.0)

STRATEGY_MODE = _get_env_str("TAFA_STRATEGY_MODE", "FUSION").upper()
if STRATEGY_MODE not in ("FUSION", "TREND", "MEAN_REVERSION", "MOMENTUM"):
    STRATEGY_MODE = "FUSION"

ENABLE_DCA = _get_env_bool("TAFA_ENABLE_DCA", True)
ENABLE_TREND_FILTER = _get_env_bool("TAFA_ENABLE_TREND_FILTER", True)
ENABLE_LIQUIDITY_DETECTOR = _get_env_bool("TAFA_ENABLE_LIQUIDITY_DETECTOR", True)

EMA_FAST = _get_env_int("TAFA_EMA_FAST", 12, min_val=5, max_val=50)
EMA_SLOW = _get_env_int("TAFA_EMA_SLOW", 55, min_val=20, max_val=200)
EMA_TREND = _get_env_int("TAFA_EMA_TREND", 50, min_val=20, max_val=200)

RSI_PERIOD = _get_env_int("TAFA_RSI_PERIOD", 14, min_val=5, max_val=50)
RSI_BUY_ZONE = _get_env_int("TAFA_RSI_BUY_ZONE", 35, min_val=10, max_val=45)
RSI_SELL_ZONE = _get_env_int("TAFA_RSI_SELL_ZONE", 65, min_val=55, max_val=90)

REGIME_ENABLED = _get_env_bool("TAFA_REGIME_ENABLED", True)
REGIME_LOOKBACK = _get_env_int("TAFA_REGIME_LOOKBACK", 200, min_val=50, max_val=500)
REGIMES = ["RANGE", "TREND_UP", "TREND_DOWN"]

RISK_ENABLED = _get_env_bool("TAFA_RISK_ENABLED", True)
RISK_PER_TRADE = _get_env_float("TAFA_RISK_PER_TRADE", 0.02, min_val=0.001, max_val=0.10)
MAX_DAILY_LOSS = _get_env_float("TAFA_MAX_DAILY_LOSS", 0.05, min_val=0.01, max_val=0.20)
MAX_DRAWDOWN = _get_env_float("TAFA_MAX_DRAWDOWN", 0.10, min_val=0.02, max_val=0.30)

STOP_LOSS_PERCENT = _get_env_float("TAFA_STOP_LOSS_PERCENT", 1.2, min_val=0.1, max_val=10.0)
TAKE_PROFIT_PERCENT = _get_env_float("TAFA_TAKE_PROFIT_PERCENT", 3.6, min_val=0.1, max_val=20.0)

TRAILING_STOP = _get_env_bool("TAFA_TRAILING_STOP", True)
TRAILING_PERCENT = _get_env_float("TAFA_TRAILING_PERCENT", 0.45, min_val=0.05, max_val=3.0)

USE_KELLY = _get_env_bool("TAFA_USE_KELLY", True)
KELLY_FRACTION = _get_env_float("TAFA_KELLY_FRACTION", 0.25, min_val=0.05, max_val=0.50)

AI_ENABLED = _get_env_bool("TAFA_AI_ENABLED", True)

FOUNDATION_MODELS_ENABLED = _get_env_bool("TAFA_FOUNDATION_MODELS_ENABLED", False)
FOUNDATION_MIN_CONFIDENCE = _get_env_float("TAFA_FOUNDATION_MIN_CONFIDENCE", 0.70, min_val=0.0, max_val=1.0)
FOUNDATION_CONTEXT = _get_env_int("TAFA_FOUNDATION_CONTEXT", 240, min_val=60, max_val=512)
FOUNDATION_TIMEOUT_S = _get_env_float("TAFA_FOUNDATION_TIMEOUT_S", 4.0, min_val=0.5, max_val=15.0)

MODEL_NAME = _get_env_str("TAFA_MODEL_NAME", "TAFA_NEURAL_BRAIN")
SEQUENCE_LEN = _get_env_int("TAFA_SEQUENCE_LEN", 100, min_val=20, max_val=500)
FEATURE_DIM = _get_env_int("TAFA_FEATURE_DIM", 32, min_val=8, max_val=128)
RETRAIN_ENABLED = _get_env_bool("TAFA_RETRAIN_ENABLED", True)
RETRAIN_EVERY = _get_env_int("TAFA_RETRAIN_EVERY", 500, min_val=50, max_val=10000)

QUALITY_GATE = _get_env_bool("TAFA_QUALITY_GATE", True)
MIN_MODEL_ACCURACY = _get_env_float("TAFA_MIN_MODEL_ACCURACY", 0.60, min_val=0.30, max_val=0.95)
MIN_EDGE = _get_env_float("TAFA_MIN_EDGE", 0.05, min_val=0.01, max_val=0.50)

TIMEFRAME = _get_env_str("TAFA_TIMEFRAME", "4h").lower()
_VALID_TF = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w", "1M"]
if TIMEFRAME not in _VALID_TF:
    _logger.warning(f"⚠️  TIMEFRAME={TIMEFRAME} invalide → fallback à 4h")
    TIMEFRAME = "4h"

CANDLE_LIMIT = _get_env_int("TAFA_CANDLE_LIMIT", 5000, min_val=100, max_val=10000)

WS_ENABLED = _get_env_bool("TAFA_WS_ENABLED", True)

DATABASE_FILE = _get_env_str("TAFA_DATABASE_FILE", "tafa_v7.db")
if not Path(DATABASE_FILE).is_absolute():
    DATABASE_FILE = str(_BASE_DIR / DATABASE_FILE)

LOG_LEVEL = _get_env_str("TAFA_LOG_LEVEL", "INFO").upper()
if LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    LOG_LEVEL = "INFO"

LOG_FOLDER = _get_env_str("TAFA_LOG_FOLDER", "logs")
if not Path(LOG_FOLDER).is_absolute():
    LOG_FOLDER = str(_BASE_DIR / LOG_FOLDER)

try:
    Path(LOG_FOLDER).mkdir(parents=True, exist_ok=True)
except Exception as e:
    _logger.warning(f"⚠️  Impossible de créer {LOG_FOLDER}: {e}")

DASHBOARD_ENABLED = _get_env_bool("TAFA_DASHBOARD_ENABLED", True)
DASHBOARD_PORT = _get_env_int("TAFA_DASHBOARD_PORT", 8501, min_val=1024, max_val=65535)

ENABLE_LIVE = _get_env_bool("ENABLE_LIVE", False)
LIVE_CONFIRM = _get_env_str("LIVE_CONFIRM", "")
_LIVE_PHRASE = "I_UNDERSTAND_THE_RISK"

_keys_valid = _validate_api_keys() if MODE == "LIVE" else True
_has_keys = bool(OKX_API_KEY and OKX_SECRET_KEY and OKX_PASSPHRASE)

_gates_passed = (
    ENABLE_LIVE
    and LIVE_CONFIRM == _LIVE_PHRASE
    and _has_keys
    and MODE == "LIVE"
    and _keys_valid
)

if not _gates_passed:
    PAPER_TRADING = True
    if ENABLE_LIVE or MODE == "LIVE":
        _logger.critical("")
        _logger.critical("=" * 75)
        _logger.critical("🔒  MODE LIVE BLOQUÉ - GARDE-FOU DE SÉCURITÉ ACTIF")
        _logger.critical("-" * 75)
        _logger.critical(f"   ENABLE_LIVE          : {'✅' if ENABLE_LIVE else '❌'}")
        _logger.critical(f"   LIVE_CONFIRM         : {'✅' if LIVE_CONFIRM == _LIVE_PHRASE else '❌'}")
        _logger.critical(f"   Clés API OKX         : {'✅' if _has_keys else '❌'}")
        _logger.critical(f"   TAFA_MODE            : {'✅' if MODE == 'LIVE' else '❌'}")
        _logger.critical(f"   Validation clés      : {'✅' if _keys_valid else '❌'}")
        _logger.critical("-" * 75)
        _logger.critical("   → Le bot reste en mode PAPER (simulation)")
        _logger.critical("=" * 75)
        _logger.critical("")
else:
    PAPER_TRADING = False
    _logger.info("🚀  MODE LIVE ACTIVÉ - Trades réels possibles")

SIMULATED_BALANCE = INITIAL_CAPITAL if PAPER_TRADING else None

RUNTIME_CONFIG_PATH = _BASE_DIR / "data" / "runtime_config.json"
RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

def validate_config() -> Dict[str, Any]:
    result = {"valid": True, "errors": [], "warnings": []}

    if INITIAL_CAPITAL < MIN_ORDER_USD * 2:
        result["errors"].append(
            f"Capital ({INITIAL_CAPITAL:.2f}) insuffisant pour MIN_ORDER_USD ({MIN_ORDER_USD:.2f})"
        )

    if STOP_LOSS_PERCENT >= TAKE_PROFIT_PERCENT:
        result["warnings"].append(
            f"SL ({STOP_LOSS_PERCENT:.2f}%) >= TP ({TAKE_PROFIT_PERCENT:.2f}%) → stratégie non rentable"
        )

    if EMA_FAST >= EMA_SLOW:
        result["warnings"].append(
            f"EMA_FAST ({EMA_FAST}) >= EMA_SLOW ({EMA_SLOW}) → indicateur inversé"
        )

    if RSI_BUY_ZONE >= RSI_SELL_ZONE:
        result["warnings"].append(
            f"RSI_BUY_ZONE ({RSI_BUY_ZONE}) >= RSI_SELL_ZONE ({RSI_SELL_ZONE})"
        )

    if RISK_PER_TRADE * INITIAL_CAPITAL < MIN_ORDER_USD:
        result["warnings"].append(
            f"Risque par trade ({RISK_PER_TRADE*100:.2f}%) trop faible vs capital"
        )

    if MODE == "LIVE" and not PAPER_TRADING and not _has_keys:
        result["errors"].append("Mode LIVE activé mais clés API manquantes")

    for w in result["warnings"]:
        _logger.warning(f"⚠️  {w}")
    for e in result["errors"]:
        _logger.error(f"❌  {e}")
        result["valid"] = False
    return result

_CONFIG_VALIDATION = validate_config()
CONFIG_VALID = _CONFIG_VALIDATION["valid"]

def export_runtime_config() -> Dict[str, Any]:
    return {
        "initial_capital": INITIAL_CAPITAL,
        "order_size_usd": ORDER_SIZE_USD,
        "min_order_usd": MIN_ORDER_USD,
        "risk_per_trade": RISK_PER_TRADE,
        "max_daily_loss": MAX_DAILY_LOSS,
        "max_drawdown": MAX_DRAWDOWN,
        "stop_loss_percent": STOP_LOSS_PERCENT,
        "take_profit_percent": TAKE_PROFIT_PERCENT,
        "trailing_percent": TRAILING_PERCENT,
        "grid_levels": GRID_LEVELS,
        "grid_step_percent": GRID_STEP_PERCENT,
        "atr_period": ATR_PERIOD,
        "atr_multiplier": ATR_MULTIPLIER,
        "ema_fast": EMA_FAST,
        "ema_slow": EMA_SLOW,
        "rsi_buy_zone": RSI_BUY_ZONE,
        "rsi_sell_zone": RSI_SELL_ZONE,
        "max_open_positions": MAX_OPEN_POSITIONS,
        "kelly_fraction": KELLY_FRACTION,
        "foundation_min_confidence": FOUNDATION_MIN_CONFIDENCE,
        "foundation_context": FOUNDATION_CONTEXT,
        "symbols": SYMBOLS,
        "default_symbol": DEFAULT_SYMBOL,
        "timeframe": TIMEFRAME,
        "candle_limit": CANDLE_LIMIT,
        "paper_mode": PAPER_TRADING,
        "mode": MODE,
        "version": VERSION,
        "config_valid": CONFIG_VALID,
        "last_validation": datetime.now().isoformat(),
    }

def _show_banner():
    if CONFIG_VALID:
        status_icon = "🔓" if not PAPER_TRADING else "🔒"
        print("")
        print("=" * 75)
        print(f"  {VERSION}")
        print("=" * 75)
        print(f"  {status_icon}  MODE        : {'LIVE (RÉEL)' if not PAPER_TRADING else 'PAPER (SIMULATION)'}")
        print(f"  📊  SYMBOLE     : {DEFAULT_SYMBOL}")
        print(f"  📈  TIMEFRAME   : {TIMEFRAME}")
        print(f"  🧠  IA          : {'ON' if AI_ENABLED else 'OFF'}")
        print(f"  🛡️  RISK        : {'ON' if RISK_ENABLED else 'OFF'}")
        print(f"  🎯  GRID        : {'ON' if ENABLE_GRID else 'OFF'}")
        print(f"  💰  CAPITAL     : ${INITIAL_CAPITAL:,.2f}")
        print(f"  ⚙️  TP/SL       : {TAKE_PROFIT_PERCENT:.2f}% / {STOP_LOSS_PERCENT:.2f}%")
        print(f"  🔢  POSITIONS   : {MAX_OPEN_POSITIONS} max")
        print(f"  📁  LOGS        : {LOG_FOLDER}/")
        print("=" * 75)
        if PAPER_TRADING:
            print("  🔒  PAPER MODE ACTIF - Aucun ordre réel ne sera exécuté")
        else:
            print("  🔓  MODE LIVE ACTIF - Les trades sont RÉELS")
        print("=" * 75)
        print("")
    else:
        print("")
        print("=" * 75)
        print("❌  ERREUR DE CONFIGURATION")
        print("=" * 75)
        for err in _CONFIG_VALIDATION["errors"]:
            print(f"   - {err}")
        print("=" * 75)
        print("")
        sys.exit(1)

if __name__ == "__main__":
    _show_banner()

if os.getenv("TAFA_SHOW_BANNER", "0") == "1":
    _show_banner()

if DEBUG:
    _logger.setLevel(logging.DEBUG)
    _logger.debug("🔍 Mode DEBUG activé")
    _logger.debug(f"Configuration: {export_runtime_config()}")