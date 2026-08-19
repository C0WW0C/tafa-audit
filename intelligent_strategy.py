# ============================================================
# TAFA V7 PRO — Intelligent Strategy + Time Series Momentum
# TSMOM core: Moskowitz, Ooi, Pedersen (2012) JFE
#   sign(past k-bar excess return) → long if + / exit if −
#   ex-ante vol (EWMA) for confidence scaling (paper §2.4 / §3.2)
# Closed-bars only. Secondary experts: EMA, RSI, volume, regime.
# ============================================================

from __future__ import annotations

import logging
import sys
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple, Any

# Setup logger
logger = logging.getLogger("TAFA_V10.Strategy")
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
# UTILITY FUNCTIONS
# ============================================================

def ema(series: List[float], period: int) -> Optional[float]:
    """Exponential Moving Average (EMA) with fallback."""
    if not series or len(series) < period:
        return None
    k = 2.0 / (period + 1.0)
    e = series[-period]
    for x in series[-period + 1:]:
        e = x * k + e * (1 - k)
    return e


def rsi(series: List[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index (RSI)."""
    if len(series) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(-period, 0):
        d = series[i] - series[i - 1]
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))


def atr_last(highs: List[float], lows: List[float], closes: List[float],
             period: int = 14) -> Optional[float]:
    """Average True Range (ATR) for the most recent period."""
    if len(closes) < period + 1 or len(highs) < period + 1 or len(lows) < period + 1:
        return None
    trs = []
    for i in range(-period, 0):
        # True Range: max of (high-low, |high - prev_close|, |low - prev_close|)
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    return sum(trs) / period


# ============================================================
# ONLINE LEARNER (Expert Weighting)
# ============================================================

@dataclass
class OnlineLearner:
    """Online learning for expert weighting using reward feedback."""
    names: List[str] = field(
        default_factory=lambda: ["tsmom", "ema_cross", "rsi_filter", "momentum", "volume"]
    )
    weights: Dict[str, float] = field(default_factory=dict)
    enabled: Dict[str, bool] = field(default_factory=dict)
    eta: float = 0.08
    history: Deque = field(default_factory=lambda: deque(maxlen=300))

    def __post_init__(self):
        self.weights = {n: 1.0 for n in self.names}
        self.enabled = {n: True for n in self.names}

    def configure(self, cfg: Dict[str, Any]) -> None:
        """Apply expert controls from runtime config."""
        if "learner_eta" in cfg:
            self.eta = max(0.001, min(0.5, float(cfg["learner_eta"])))
        for name in self.names:
            enabled_key = f"expert_{name}_enabled"
            weight_key = f"expert_{name}_weight"
            if enabled_key in cfg:
                self.enabled[name] = bool(cfg[enabled_key])
            if weight_key in cfg:
                self.weights[name] = max(0.0, min(1.0, float(cfg[weight_key])))
        # Ensure at least one expert is enabled
        if not any(self.enabled.values()):
            self.enabled["tsmom"] = True
            logger.warning("All experts disabled; tsmom re-enabled")

    def update(self, expert: str, reward: float) -> None:
        """Update weight for an expert based on reward."""
        if expert not in self.weights or not self.enabled.get(expert, False):
            return
        reward = max(-1.0, min(1.0, reward))
        self.history.append((expert, reward))
        self.weights[expert] *= math.exp(self.eta * reward)
        total = sum(self.weights.values()) or 1.0
        n = len(self.weights)
        for k in list(self.weights):
            self.weights[k] = max(0.1, self.weights[k] / total * n)

    def normalized(self) -> Dict[str, float]:
        """Return normalized weights for enabled experts only."""
        active = {
            name: weight
            for name, weight in self.weights.items()
            if self.enabled.get(name, False)
        }
        total = sum(active.values())
        if total <= 0 and active:
            total = float(len(active))
            active = {name: 1.0 for name in active}
        return {
            name: (active.get(name, 0.0) / total if total else 0.0)
            for name in self.weights
        }

    def status(self) -> Dict[str, Any]:
        """Return current status for dashboard."""
        return {
            "weights": self.weights,
            "enabled": self.enabled,
            "normalized": self.normalized(),
            "eta": self.eta,
            "history_len": len(self.history),
        }


# ============================================================
# INTELLIGENT STRATEGY - CORE
# ============================================================

class IntelligentStrategy:
    """
    V7 + TSMOM (Moskowitz–Ooi–Pedersen): own-return sign as primary trend.

    TSMOM lookback determines trend direction. Secondary experts (EMA, RSI,
    momentum, volume) act as filters and confidence modifiers.
    All decisions are based on CLOSED bars only (confirmed=True).
    """

    # Defaults from BTC 4h walk-forward research + paper-style TSMOM
    EMA_FAST: int = 12
    EMA_SLOW: int = 55
    RSI_PERIOD: int = 14
    RSI_MAX_ENTRY: float = 78.0
    RSI_MIN_ENTRY: float = 35.0   # Below 35 is considered oversold
    ATR_SL: float = 1.2
    ATR_TP: float = 4.0
    CONFIRM_BARS: int = 3
    MIN_SLOPE: float = 0.01
    SLOPE_LOOK: int = 20
    VOL_MULT: float = 1.15
    MIN_CONF: float = 0.40
    # TSMOM: lookback k bars (paper uses months; here bar-horizon for live TF)
    TSMOM_LOOKBACK: int = 120
    TSMOM_VOL_SPAN: int = 20      # EWMA center-of-mass proxy for ex-ante vol
    TSMOM_MIN_RET: float = 0.0    # require strictly positive/negative cum ret

    def __init__(self):
        self.name = "TAFA_TSMOM_V7_REFACTORED"
        self._reset_buffers()
        self.learner = OnlineLearner()
        self.ai_on = True
        self._expert_config_signature: Optional[tuple] = None

        # Last values for status and logging
        self.last_signal: str = "HOLD"
        self.last_confidence: float = 0.0
        self.last_regime: str = "UNKNOWN"
        self.last_experts: Dict[str, str] = {}
        self.last_atr: Optional[float] = None
        self.last_price: Optional[float] = None
        self.last_tsmom_ret: Optional[float] = None
        self.last_ex_ante_vol: Optional[float] = None

        # Internal state
        self._forming: Optional[Dict[str, float]] = None
        self._cross_streak: int = 0
        self._bar_returns_cache: Optional[List[float]] = None
        self._bar_returns_cache_len: int = 0

        self.min_bars = max(60, self.TSMOM_LOOKBACK + 5, self.EMA_SLOW + 10)
        self._cycle_count: int = 0

        logger.info(
            f"Intelligent Strategy {self.name} ready "
            f"(lookback={self.TSMOM_LOOKBACK} "
            f"EMA {self.EMA_FAST}/{self.EMA_SLOW} "
            f"confirm={self.CONFIRM_BARS} bars)"
        )

    def _reset_buffers(self) -> None:
        """Reset all OHLC buffers."""
        self.opens: List[float] = []
        self.closes: List[float] = []
        self.highs: List[float] = []
        self.lows: List[float] = []
        self.volumes: List[float] = []
        self._bar_returns_cache = None
        self._bar_returns_cache_len = 0

    # ============================================================
    # CONFIGURATION
    # ============================================================

    def apply_config(self, cfg: Dict[str, Any]) -> None:
        """Apply runtime configuration with validation."""
        if not cfg:
            return

        # Core parameters
        if "ma_fast" in cfg:
            self.EMA_FAST = max(3, int(cfg["ma_fast"]))
        if "ma_slow" in cfg:
            self.EMA_SLOW = max(self.EMA_FAST + 5, int(cfg["ma_slow"]))
        if "rsi_period" in cfg:
            self.RSI_PERIOD = max(5, int(cfg["rsi_period"]))
        if "min_conf" in cfg:
            self.MIN_CONF = max(0.05, min(0.95, float(cfg["min_conf"])))
        if "ai_on" in cfg:
            self.ai_on = bool(cfg["ai_on"])

        # Research knobs
        if "confirm_bars" in cfg:
            self.CONFIRM_BARS = max(1, int(cfg["confirm_bars"]))
        if "rsi_max" in cfg:
            self.RSI_MAX_ENTRY = max(50.0, min(90.0, float(cfg["rsi_max"])))
        if "rsi_min" in cfg:
            self.RSI_MIN_ENTRY = max(10.0, min(50.0, float(cfg["rsi_min"])))
        if "min_slope" in cfg:
            self.MIN_SLOPE = max(0.001, float(cfg["min_slope"]))
        if "vol_mult" in cfg:
            self.VOL_MULT = max(0.5, min(3.0, float(cfg["vol_mult"])))
        if "tsmom_lookback" in cfg:
            self.TSMOM_LOOKBACK = max(5, int(cfg["tsmom_lookback"]))
        if "tsmom_vol_span" in cfg:
            self.TSMOM_VOL_SPAN = max(5, int(cfg["tsmom_vol_span"]))

        # Online learner config - only reconfigure on actual changes
        expert_keys = ["learner_eta"] + [
            f"expert_{name}_{field}"
            for name in self.learner.names
            for field in ("enabled", "weight")
        ]
        signature = tuple((key, cfg.get(key)) for key in expert_keys if key in cfg)
        if signature != self._expert_config_signature:
            self.learner.configure(cfg)
            self._expert_config_signature = signature

        # Recalculate min_bars
        self.min_bars = max(60, self.EMA_SLOW + 10, self.TSMOM_LOOKBACK + 5)

    # ============================================================
    # DATA FEED
    # ============================================================

    def update_bar(self, o: float, h: float, l: float, c: float,
                   v: float = 0.0, confirmed: bool = True) -> None:
        """
        Append OHLC only when the bar is closed (confirmed=True).

        Unconfirmed / forming candles go to _forming and never feed indicators.
        """
        o, h, l, c, v = float(o), float(h), float(l), float(c), float(v)
        self.last_price = c

        if not confirmed:
            self._forming = {"o": o, "h": h, "l": l, "c": c, "v": v}
            return

        self._forming = None
        self.opens.append(o)
        self.closes.append(c)
        self.highs.append(h)
        self.lows.append(l)
        self.volumes.append(v)

        # Limit memory usage
        max_bars = 8000
        if len(self.closes) > max_bars:
            self.opens.pop(0)
            self.closes.pop(0)
            self.highs.pop(0)
            self.lows.pop(0)
            self.volumes.pop(0)

        # Invalidate returns cache
        self._bar_returns_cache = None
        self._bar_returns_cache_len = 0

        # Update cross streak
        f = ema(self.closes, self.EMA_FAST)
        s = ema(self.closes, self.EMA_SLOW)
        if f is not None and s is not None and f > s:
            self._cross_streak += 1
        else:
            self._cross_streak = 0

    def update_price(self, price: float) -> None:
        """Tick update: last_price only. Never creates fake OHLC bars."""
        self.last_price = float(price)

    # ============================================================
    # INDICATORS
    # ============================================================

    def _bar_returns(self) -> List[float]:
        """Simple closed-bar returns r_t = c_t/c_{t-1} - 1."""
        if len(self.closes) < 2:
            return []

        # Use cache if available
        if self._bar_returns_cache is not None and self._bar_returns_cache_len == len(self.closes):
            return self._bar_returns_cache

        out = []
        for i in range(1, len(self.closes)):
            prev = self.closes[i - 1]
            out.append((self.closes[i] / prev - 1.0) if prev and prev > 0 else 0.0)

        self._bar_returns_cache = out
        self._bar_returns_cache_len = len(self.closes)
        return out

    def _ex_ante_vol(self) -> Optional[float]:
        """
        Ex-ante volatility (paper §2.4 simplified EWMA of squared returns).

        Uses only past closed bars. Annualization skipped for intra-day bars;
        relative scale is what matters for confidence.
        """
        rets = self._bar_returns()
        span = self.TSMOM_VOL_SPAN
        if len(rets) < span:
            return None

        # EWMA variance, center of mass ~ span
        alpha = 2.0 / (span + 1.0)
        var = rets[-span] ** 2
        for r in rets[-span + 1:]:
            var = alpha * (r ** 2) + (1.0 - alpha) * var
        return math.sqrt(max(var, 1e-16))

    def _tsmom(self) -> str:
        """Time series momentum (Moskowitz–Ooi–Pedersen §3.2)."""
        k = self.TSMOM_LOOKBACK
        if len(self.closes) < k + 1:
            self.last_tsmom_ret = None
            return "HOLD"

        c_now = self.closes[-1]
        c_past = self.closes[-1 - k]
        if not c_past or c_past <= 0:
            self.last_tsmom_ret = None
            return "HOLD"

        ret = c_now / c_past - 1.0
        self.last_tsmom_ret = ret
        self.last_ex_ante_vol = self._ex_ante_vol()

        if ret > self.TSMOM_MIN_RET:
            return "BUY"
        if ret < -self.TSMOM_MIN_RET:
            return "SELL"
        return "HOLD"

    def _ema_cross(self) -> str:
        """EMA crossover signal with confirmation bars."""
        f = ema(self.closes, self.EMA_FAST)
        s = ema(self.closes, self.EMA_SLOW)
        if f is None or s is None:
            return "HOLD"

        if f > s and self._cross_streak >= self.CONFIRM_BARS:
            return "BUY"
        if f < s:
            return "SELL"
        return "HOLD"

    def _rsi_filter(self) -> str:
        """RSI-based filter: extreme overbought/oversold."""
        r = rsi(self.closes, self.RSI_PERIOD)
        if r is None:
            return "HOLD"

        if r >= self.RSI_MAX_ENTRY:
            return "SELL"
        if r < self.RSI_MIN_ENTRY:
            return "BUY"
        return "HOLD"

    def _momentum(self) -> str:
        """Simple momentum over CONFIRM_BARS."""
        look = max(5, self.CONFIRM_BARS)
        if len(self.closes) < look + 1:
            return "HOLD"
        if self.closes[-1] > self.closes[-look]:
            return "BUY"
        if self.closes[-1] < self.closes[-look]:
            return "SELL"
        return "HOLD"

    def _volume(self) -> str:
        """Volume surge confirmation."""
        if len(self.volumes) < 20:
            return "HOLD"
        avg = sum(self.volumes[-20:]) / 20.0
        if avg <= 0:
            return "HOLD"
        ratio = self.volumes[-1] / avg
        f = ema(self.closes, self.EMA_FAST)
        s = ema(self.closes, self.EMA_SLOW)
        if ratio >= self.VOL_MULT and f is not None and s is not None:
            if f > s:
                return "BUY"
            if f < s:
                return "SELL"
        return "HOLD"

    def detect_regime(self) -> str:
        """Detect market regime: TREND_UP, TREND_DOWN, RANGE, VOLATILE."""
        if len(self.closes) < max(50, self.SLOPE_LOOK + 5):
            return "UNKNOWN"

        f = ema(self.closes, self.EMA_FAST)
        s = ema(self.closes, self.EMA_SLOW)
        if f is None or s is None:
            return "UNKNOWN"

        look = min(self.SLOPE_LOOK, len(self.closes) - 1)
        slope = (self.closes[-1] - self.closes[-look]) / (self.closes[-look] if self.closes[-look] else 1)

        # Volatility check
        atr_val = atr_last(self.highs, self.lows, self.closes, 14)
        if atr_val and self.closes[-1] > 0:
            atr_pct = atr_val / self.closes[-1]
            if atr_pct > 0.04:
                return "VOLATILE"

        # Trend detection
        if f > s * 1.001 and slope >= self.MIN_SLOPE:
            return "TREND_UP"
        if f < s * 0.999 and slope <= -self.MIN_SLOPE:
            return "TREND_DOWN"

        return "RANGE"

    # ============================================================
    # SIGNAL GENERATION
    # ============================================================

    def analyze(self, symbol: str, price: float, already_updated: bool = False) -> str:
        """
        Generate trading signal based on TSMOM + expert consensus.

        Returns: "BUY", "SELL", or "HOLD"
        """
        self._cycle_count += 1

        # Update price if not already done
        if not already_updated and price is not None:
            self.update_price(price)

        # Early exits: AI off or insufficient bars
        if not self.ai_on:
            self.last_signal = "HOLD"
            self.last_confidence = 0.0
            return "HOLD"

        if len(self.closes) < self.min_bars:
            self.last_signal = "HOLD"
            self.last_confidence = 0.0
            return "HOLD"

        # Calculate ATR and regime
        self.last_atr = atr_last(self.highs, self.lows, self.closes, 14)
        regime = self.detect_regime()
        self.last_regime = regime

        # Get expert signals
        experts = {
            "tsmom": self._tsmom(),
            "ema_cross": self._ema_cross(),
            "rsi_filter": self._rsi_filter(),
            "momentum": self._momentum(),
            "volume": self._volume(),
        }
        self.last_experts = experts

        # Weighted aggregation
        w = self.learner.normalized()

        # Hard regime gate: never open long in TREND_DOWN / VOLATILE
        if regime in ("TREND_DOWN", "VOLATILE"):
            buys = 0.0
        else:
            buys = sum(w[k] for k, v in experts.items() if v == "BUY")
        sells = sum(w[k] for k, v in experts.items() if v == "SELL")

        # ============================================================
        # CONFIDENCE SCALING (Paper §3.2)
        # ============================================================

        # Base confidence: expert agreement
        agreement = max(buys, sells)
        conf = float(agreement)

        # TSMOM strength scaling
        tsm = experts["tsmom"]
        if tsm == "BUY" and self.last_tsmom_ret is not None:
            conf = min(1.0, conf + 0.12)
            if self.last_ex_ante_vol and self.last_ex_ante_vol > 0:
                strength = min(1.5, abs(self.last_tsmom_ret) / self.last_ex_ante_vol)
                conf = min(1.0, conf + 0.06 * strength)

        # Regime bonus
        if regime == "TREND_UP" and buys > sells:
            conf = min(1.0, conf + 0.06)

        # Cross confirmation bonus
        if self._cross_streak >= self.CONFIRM_BARS:
            conf = min(1.0, conf + 0.04)

        # ============================================================
        # SIGNAL DECISION
        # ============================================================

        signal = "HOLD"

        # Entry: TSMOM sign is primary (paper §3.2)
        if tsm == "BUY" and regime != "TREND_DOWN" and conf >= self.MIN_CONF:
            # Apply expert penalties
            if experts["rsi_filter"] == "SELL":
                conf *= 0.85
            if experts["ema_cross"] != "BUY":
                conf *= 0.92
            if experts["volume"] != "BUY":
                conf *= 0.95
            if regime == "VOLATILE":
                conf *= 0.90

            if conf >= self.MIN_CONF:
                signal = "BUY"

        # Exit: TSMOM flip down, or strong sell consensus
        elif tsm == "SELL" and conf >= 0.35:
            signal = "SELL"
        elif sells > buys and experts["ema_cross"] == "SELL" and conf >= 0.45:
            signal = "SELL"

        self.last_signal = signal
        self.last_confidence = round(conf, 3)

        # Log signal changes (reduced spam)
        if self._cycle_count % 10 == 0 or self.last_signal != "HOLD":
            logger.debug(
                f"Signal: {signal} | conf={conf:.3f} | regime={regime} | "
                f"tsmom={tsm} | buys={buys:.2f} sells={sells:.2f}"
            )

        return signal

    # ============================================================
    # POSITION SIZING
    # ============================================================

    def get_sl_tp(self, entry: float) -> Tuple[float, float]:
        """Calculate stop-loss and take-profit levels based on ATR."""
        atr = self.last_atr
        if atr is None or atr <= 0:
            atr = entry * 0.01  # Fallback: 1% of entry
        sl = entry - self.ATR_SL * atr
        tp = entry + self.ATR_TP * atr
        return sl, tp

    # ============================================================
    # STATUS / STATE
    # ============================================================

    def get_state(self) -> Dict[str, Any]:
        """Return current state for dashboard."""
        weights = self.learner.normalized()
        components = {
            name: {
                "enabled": bool(self.learner.enabled.get(name, False)),
                "weight": weights.get(name, 0.0),
                "raw_weight": self.learner.weights.get(name, 0.0),
                "vote": self.last_experts.get(name, "HOLD"),
            }
            for name in self.learner.names
        }

        return {
            "signal": self.last_signal,
            "confidence": self.last_confidence,
            "regime": self.last_regime,
            "experts": dict(self.last_experts or {}),
            "weights": weights,
            "expert_components": components,
            "ai_on": self.ai_on,
            "learner_eta": self.learner.eta,
            "name": self.name,
            "bars": len(self.closes),
            "last_price": self.last_price,
            "last_atr": self.last_atr,
            "cross_streak": self._cross_streak,
            "forming": self._forming is not None,
            "tsmom_ret": self.last_tsmom_ret,
            "ex_ante_vol": self.last_ex_ante_vol,
            "tsmom_lookback": self.TSMOM_LOOKBACK,
            "min_bars": self.min_bars,
            "cycle_count": self._cycle_count,
        }

    def get_learner_status(self) -> Dict[str, Any]:
        """Return learner status for debugging."""
        return self.learner.status()