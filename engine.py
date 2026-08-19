# ============================================================
# TAFA V7 PRO — Engine Core (Production)
# Refactored: logging, error handling, modular cycle, clean shutdown
# ============================================================

from __future__ import annotations

import sys
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

# Path setup for imports
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ============================================================
# LOGGING
# ============================================================

_logger = logging.getLogger("TAFA_V7.Engine")
if not _logger.handlers:
    # FIX Windows CP1252: force UTF-8 sur la console
    import io as _io
    _con = (_io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
            if sys.platform == "win32" else sys.stdout)
    handler = logging.StreamHandler(stream=_con)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)

def log_engine(msg: str, level=logging.INFO):
    _logger.log(level, msg)

def log_signal(strategy: str, signal: str, **kwargs):
    _logger.info(f"SIGNAL {strategy}: {signal} {kwargs}")

# ============================================================
# IMPORTS (after logging setup)
# ============================================================

from config import (
    DEFAULT_SYMBOL,
    PAPER_TRADING,
    TIMEFRAME,
    INITIAL_CAPITAL,
)
from core.database import save_signal, save_performance
from risk.risk_manager import risk_manager

from trading.strategy import Strategy
from trading.trade_manager import TradeManager
from trading.paper_trading import PaperTrading
from exchange.market_data import MarketData
from exchange.okx_client import OKXClient
from exchange.websocket import OKXWebSocket
from core.status_bridge import publish as publish_status
from core.manual_paper_orders import claim as claim_manual_paper_orders, complete as complete_manual_paper_order

# Optional modules
try:
    from core.smart_alerts import alerts as _alerts
    _HAS_ALERTS = True
except Exception:
    _HAS_ALERTS = False

try:
    from core.performance_analytics import analytics as _analytics
    _HAS_ANALYTICS = True
except Exception:
    _HAS_ANALYTICS = False

# ============================================================
# HELPERS
# ============================================================

def _runtime_params() -> dict:
    """Get runtime parameters from config bridge."""
    try:
        from core.runtime_config import get_config
        return get_config()
    except Exception:
        return {}

def _load_candles(symbol: str, timeframe: str, market) -> List[Dict]:
    """Load candles from CSV or market API with fallback."""
    candles = []
    try:
        from data.loader import load_csv_candles, default_dataset
        csv_path = default_dataset(timeframe if timeframe in ("5m", "15m", "1h", "4h") else "1h")
        candles = load_csv_candles(csv_path)
        if len(candles) > 200:
            candles = candles[-200:]
        log_engine(f"Warmed from local CSV {csv_path.name} ({len(candles)} bars)")
        return candles
    except Exception as exc:
        log_engine(f"Local CSV warm-up skipped: {exc}")

    try:
        candles = market.load_candles(symbol, bar=timeframe, limit=120)
        if candles:
            log_engine(f"Warmed from market API ({len(candles)} bars)")
            return candles
    except Exception as exc:
        log_engine(f"Market API warm-up failed: {exc}")

    # ✅ FIX: le warm-up synthétique est autorisé uniquement en mode PAPER/DEMO.
    # En production (LIVE), l'absence de données réelles est une erreur fatale.
    try:
        from config import PAPER_TRADING as _paper
    except Exception:
        _paper = True  # fallback sécuritaire

    if not _paper:
        raise RuntimeError(
            "TAFA LIVE: aucune donnée historique disponible pour le warm-up "
            "(CSV absent, API échouée). Arrêt — ne jamais démarrer en LIVE "
            "sans données réelles. Vérifiez la connectivité OKX et les datasets."
        )

    log_engine(
        "AVERTISSEMENT : warm-up synthétique activé (PAPER/DEMO uniquement). "
        "Les 120 premières bougies sont simulées — ne pas utiliser en LIVE."
    )
    import random
    seed = 65000.0
    synthetic = []
    for _ in range(120):
        seed *= (1 + random.uniform(-0.003, 0.003))
        synthetic.append({
            "open": seed, "high": seed * 1.001, "low": seed * 0.999,
            "close": seed, "volume": 100.0
        })
    return synthetic

# ============================================================
# TAFAEngine CLASS
# ============================================================

class TAFAEngine:
    """Main trading loop: price → strategy → risk → execution → memory."""

    def __init__(self, symbol: Optional[str] = None):
        self.symbol = symbol or DEFAULT_SYMBOL
        self.timeframe = TIMEFRAME
        self.cycle_count = 0
        self.running = False
        self.last_price: Optional[float] = None
        self.last_signal: Optional[str] = None
        self.last_error: Optional[str] = None
        self._ws_price: Optional[float] = None
        self._ws_price_ts: float = 0.0
        self._last_book_refresh: float = 0.0
        self._last_cycle_time: float = 0.0
        self._cycle_delay: float = 0.5
        self._last_config_apply: float = 0.0
        self._config_apply_interval: float = 5.0

        self._lock = threading.RLock()

        self._init_components()
        self._warmup_strategy()

        log_engine(f"TAFAEngine initialized on {self.symbol} ({TIMEFRAME})")

    def _init_components(self) -> None:
        try:
            from core.runtime_config import apply_to_runtime
            apply_to_runtime()
        except Exception as e:
            log_engine(f"Runtime config apply failed: {e}")

        self.client = OKXClient(demo=PAPER_TRADING)
        self.market = MarketData(client=self.client)
        self.paper = PaperTrading(capital=INITIAL_CAPITAL)
        self.strategy = Strategy()
        self._apply_strategy_config()

        self.trader = TradeManager(paper=self.paper, client=self.client)
        self.trader.strategy_ref = self.strategy

        self.ws = OKXWebSocket(
            symbol=self.symbol,
            timeframe=self.timeframe,
            demo=PAPER_TRADING,   # ✅ FIX: cohérent avec le REST
            on_price=self._on_ws_price,
            on_candle=self._on_ws_candle,
        )

        self.manual_order_tape: List[Dict] = []

        self.market_book: Dict[str, Any] = {
            "bids": [], "asks": [],
            "best_bid": None, "best_ask": None,
            "spread": None, "source": "none"
        }

    def _apply_strategy_config(self) -> None:
        try:
            params = _runtime_params()
            if hasattr(self.strategy, "apply_config"):
                self.strategy.apply_config(params)
        except Exception as exc:
            log_engine(f"Strategy config apply failed: {exc}")

    def _warmup_strategy(self) -> None:
        candles = _load_candles(self.symbol, self.timeframe, self.market)

        if not candles:
            # _load_candles lève RuntimeError en LIVE — on arrive ici uniquement en PAPER/DEMO.
            log_engine(
                "WARM-UP SYNTHÉTIQUE ACTIF [PAPER/DEMO] — "
                "données réelles indisponibles, 120 bougies simulées injectées. "
                "Ce comportement est interdit en LIVE (RuntimeError levée avant ce point)."
            )
            import random
            seed = 65000.0
            for _ in range(120):
                seed *= (1 + random.uniform(-0.003, 0.003))
                self.strategy.update_bar(seed, seed, seed, seed, 0.0, confirmed=True)
                self.market.prices.append(seed)
            if self.strategy.closes:
                self._ws_price = float(self.strategy.closes[-1])
                self._ws_price_ts = time.time()
                self.last_price = self._ws_price
            log_engine("Warmed with 120 synthetic candles [PAPER/DEMO only]")
            return

        for c in candles:
            if isinstance(c, dict):
                self.strategy.update_bar(
                    c.get("open", c["close"]),
                    c.get("high", c["close"]),
                    c.get("low", c["close"]),
                    c["close"],
                    c.get("volume", 0),
                    confirmed=True,
                )
                self.market.prices.append(float(c["close"]))
            else:
                if isinstance(c, (tuple, list)) and len(c) >= 4:
                    o, h, l, cl = c[0], c[1], c[2], c[3]
                    v = c[4] if len(c) > 4 else 0.0
                else:
                    o = h = l = cl = c
                    v = 0.0
                self.strategy.update_bar(o, h, l, cl, v, confirmed=True)
                self.market.prices.append(float(cl))

        if self.strategy.closes:
            self._ws_price = float(self.strategy.closes[-1])
            self._ws_price_ts = time.time()
            self.last_price = self._ws_price

        log_engine(f"Strategy ready with {len(self.strategy.closes)} closed bars")

    def _on_ws_price(self, price: float) -> None:
        with self._lock:
            self._ws_price = float(price)
            self._ws_price_ts = time.time()
            try:
                self.strategy.update_price(price)
            except Exception as e:
                _logger.debug(f"Strategy update_price failed: {e}")

    def _on_ws_candle(self, candle: Dict) -> None:
        with self._lock:
            try:
                confirmed = str(candle.get("confirm", "0")) == "1"
                self.strategy.update_bar(
                    candle["open"], candle["high"], candle["low"], candle["close"],
                    candle.get("volume", 0),
                    confirmed=confirmed,
                )
                self._ws_price = float(candle["close"])
                self._ws_price_ts = time.time()
                if confirmed:
                    log_engine(f"WS candle CLOSED c={candle['close']}")
            except Exception as exc:
                _logger.error(f"WS candle feed error: {exc}")

    def resolve_price(self) -> Optional[float]:
        with self._lock:
            if self._ws_price is not None and float(self._ws_price) > 0:
                if time.time() - self._ws_price_ts < 10.0:
                    return float(self._ws_price)

            if self.last_price is not None and float(self.last_price) > 0:
                return float(self.last_price)

            if hasattr(self.strategy, "last_price"):
                try:
                    p = float(self.strategy.last_price)
                    if p > 0:
                        return p
                except Exception:
                    pass

            try:
                px = self.market.get_price(self.symbol)
                if px and float(px) > 0:
                    self.last_price = float(px)
                    return float(px)
            except Exception:
                pass

            if self.strategy.closes:
                try:
                    return float(self.strategy.closes[-1])
                except Exception:
                    pass

            if self.market.prices:
                try:
                    return float(self.market.prices[-1])
                except Exception:
                    pass

            return None

    def _refresh_market_book(self) -> Dict:
        with self._lock:
            if hasattr(self, "ws"):
                ws_book = self.ws.get_book() if hasattr(self.ws, "get_book") else {}
                if ws_book.get("best_bid") is not None and ws_book.get("best_ask") is not None:
                    self.market_book = {**ws_book, "source": "okx_public_ws"}
                    return self.market_book

            now = time.time()
            if now - self._last_book_refresh >= 5.0:
                self._last_book_refresh = now
                try:
                    rest_book = self.client.get_order_book(self.symbol, depth=5)
                    if rest_book.get("best_bid") is not None and rest_book.get("best_ask") is not None:
                        self.market_book = rest_book
                        self.market_book["source"] = "okx_rest"
                except Exception as exc:
                    log_engine(f"Public book refresh skipped: {exc}")

            return self.market_book

    def _process_manual_paper_orders(self, price: float) -> None:
        with self._lock:
            book = self._refresh_market_book()
            for request in claim_manual_paper_orders(limit=3):
                side = request.get("side", "")
                symbol = request.get("symbol", "")
                notional = request.get("notional", 0.0)
                execution_price = book.get("best_ask") if side == "BUY" else book.get("best_bid")
                execution_price = float(execution_price or price or 0)

                if symbol != self.symbol:
                    result = {"ok": False, "reason": "symbol_not_active", "price": execution_price}
                else:
                    result = self.trader.execute_manual_paper(symbol, side, execution_price, notional)

                event = {
                    "id": request.get("id"),
                    "symbol": symbol,
                    "side": side,
                    "created_at": request.get("created_at"),
                    "processed_at": time.time(),
                    **result
                }
                self.manual_order_tape.append(event)
                if len(self.manual_order_tape) > 30:
                    self.manual_order_tape = self.manual_order_tape[-30:]

                if result.get("ok", False):
                    complete_manual_paper_order(request)
                else:
                    log_engine(f"Manual paper order failed: {result}")

    def run_cycle(self) -> Optional[str]:
        if not self.running:
            return None

        self.cycle_count += 1
        self._last_cycle_time = time.time()

        try:
            now = time.time()
            if now - self._last_config_apply >= self._config_apply_interval:
                self._last_config_apply = now
                self._apply_runtime_config()

            if not risk_manager.can_trade():
                if self.cycle_count % 30 == 0:
                    log_engine("Trading blocked by Risk Manager")
                self._publish_status()
                return "BLOCKED"

            price = self.resolve_price()
            if price is None or price <= 0:
                self.last_error = "no_price"
                if self.cycle_count % 10 == 0:
                    log_engine(f"No price for {self.symbol}")
                self._publish_status()
                return None

            self.last_price = price
            self.last_error = None

            self._refresh_market_book()
            self._process_manual_paper_orders(price)

            exit_signal = self._check_exit(price)
            if exit_signal:
                return exit_signal

            signal = self._generate_signal(price)

            if signal in ("BUY", "SELL"):
                self._execute_signal(signal, price)
            else:
                self._update_performance(price)

            self._publish_status()

            # time.sleep(self._cycle_delay)

            return signal

        except Exception as exc:
            self.last_error = str(exc)
            _logger.exception(f"ENGINE CYCLE ERROR: {exc}")
            return "ERROR"

    def _apply_runtime_config(self) -> None:
        try:
            from core.runtime_config import apply_to_runtime
            apply_to_runtime()
            self._apply_strategy_config()
        except Exception as e:
            _logger.debug(f"Runtime config apply failed: {e}")

    def _check_exit(self, price: float) -> Optional[str]:
        with self._lock:
            if self.paper.position_qty(self.symbol) <= 0:
                return None
            try:
                exit_signal = risk_manager.check_exit(price)
                if exit_signal in ("STOP_LOSS", "TAKE_PROFIT"):
                    log_engine(f"Exit trigger: {exit_signal} @ {price}")
                    self.trader.execute(self.symbol, "SELL", price)
                    self.last_signal = exit_signal
                    self._publish_status()
                    return exit_signal
            except Exception as e:
                _logger.warning(f"Exit check failed: {e}")
            return None

    def _generate_signal(self, price: float) -> str:
        try:
            signal = self.strategy.analyze(self.symbol, price) or "HOLD"
        except Exception as e:
            _logger.error(f"Strategy analyze failed: {e}")
            signal = "HOLD"

        self.last_signal = signal

        if signal != "HOLD":
            confidence = getattr(self.strategy, "last_confidence", 0.75)
            log_signal("TAFA_FUSION", signal, confidence=confidence)
            regime = getattr(self.strategy, "last_regime", "UNKNOWN")
            save_signal(strategy="TAFA_FUSION", signal=signal, confidence=confidence, regime=str(regime))

            if _HAS_ALERTS:
                self._evaluate_alerts(price, signal)

        return signal

    def _evaluate_alerts(self, price: float, signal: str) -> None:
        try:
            eq = self.paper.equity({self.symbol: price}) if price else None
            _alerts.evaluate({
                "symbol": self.symbol,
                "price": price,
                "signal": signal,
                "confidence": getattr(self.strategy, "last_confidence", 0.5),
                "drawdown": risk_manager.get_drawdown(),
                "can_trade": risk_manager.can_trade(),
                "equity": eq,
                "price_change_pct": 0.0,
                "new_equity_high": False,
            })
        except Exception as e:
            _logger.debug(f"Alerts evaluation failed: {e}")

    def _execute_signal(self, signal: str, price: float) -> None:
        with self._lock:
            if signal == "BUY" and self.paper.position_qty(self.symbol) > 0:
                return
            if signal == "SELL" and self.paper.position_qty(self.symbol) <= 0:
                return

            self.trader.execute(self.symbol, signal, price)
            log_engine(f"Executed {signal} @ {price}")

    def _update_performance(self, price: float) -> None:
        if self.cycle_count % 15 == 0:
            try:
                eq = self.paper.equity({self.symbol: price})
                risk_manager.update_balance(eq)
                save_performance(
                    self.paper.balance,
                    eq,
                    eq - self.paper.initial_capital,
                    risk_manager.get_drawdown(),
                )
            except Exception as e:
                _logger.debug(f"Performance update failed: {e}")

    def _publish_status(self) -> None:
        try:
            st = self.status()
            publish_status(st)
        except Exception as e:
            _logger.warning(f"Status publish failed: {e}")

    def status(self) -> Dict[str, Any]:
        with self._lock:
            marks = {self.symbol: self.last_price} if self.last_price else None
            paper_status = self.paper.status(marks)
            ai_state = self.strategy.get_state() if hasattr(self.strategy, 'get_state') else {}

            risk_status = {
                "can_trade": risk_manager.can_trade(),
                "drawdown": risk_manager.get_drawdown(),
                "balance": getattr(risk_manager, "balance", None),
                "peak": getattr(risk_manager, "peak_balance", getattr(risk_manager, "peak", None)),
                "daily_pnl": getattr(risk_manager, "daily_pnl", None),
                "open_position": getattr(risk_manager, "open_position", None) is not None,
            }

            return {
                "running": self.running,
                "ws": self.ws.status() if hasattr(self, "ws") else {},
                "market": {"book": dict(self.market_book), "source": self.market_book.get("source", "none")},
                "ai": ai_state,
                "symbol": self.symbol,
                "cycle": self.cycle_count,
                "last_price": self.last_price,
                "last_signal": self.last_signal,
                "last_error": self.last_error,
                "paper": paper_status,
                "paper_guard": self.trader.guard_status() if hasattr(self, "trader") else {},
                "risk": risk_status,
                "can_trade": risk_status["can_trade"],
                "drawdown": risk_status["drawdown"],
                "mode": "PAPER" if PAPER_TRADING else "LIVE",
                "version": "TAFA_V7_PRO_BEST",
                "alerts": _alerts.get_recent(10) if _HAS_ALERTS else [],
                "manual_orders": list(self.manual_order_tape[-12:]),
                "params": _runtime_params(),
            }

    def start(self) -> None:
        self.running = True
        try:
            self.ws.connect()
            log_engine("OKX WebSocket started")
        except Exception as exc:
            log_engine(f"WebSocket start skipped: {exc}")

        log_engine("ENGINE STARTED")
        self._publish_status()

    def stop(self) -> None:
        self.running = False
        try:
            self.ws.stop()
        except Exception:
            pass
        log_engine("ENGINE STOPPED")
        self._publish_status()

    def run_forever(self) -> None:
        self.running = True
        try:
            while self.running:
                self.run_cycle()
                time.sleep(self._cycle_delay)
        except KeyboardInterrupt:
            self.stop()