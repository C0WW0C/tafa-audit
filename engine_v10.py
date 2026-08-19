# ============================================================
# TAFA V10 — Production engine wrapper
# Adds: circuit breaker, quality gate, journal, metrics publish
# ============================================================
from __future__ import annotations

import time
import logging
import sys
import threading
from typing import Optional, Tuple, Any

from core.circuit_breaker import breaker
from core.quality_gate_live import gate
try:
    from trading.strategy_policy import apply_to_gate
    apply_to_gate(gate)
except Exception:
    pass
from core.trade_journal import log_event
from core.status_bridge import publish as publish_status

logger = logging.getLogger("TAFA_V10")
if not logger.handlers:
    # FIX Windows CP1252: force UTF-8 sur la console
    import io as _io
    _con = (_io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
            if sys.platform == "win32" else sys.stdout)
    handler = logging.StreamHandler(stream=_con)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def log_engine(msg: str, level=logging.INFO):
    logger.log(level, msg)


class TAFAEngineV10:
    """Wraps TAFAEngine with production fail-safes."""

    def __init__(self, symbol: Optional[str] = None):
        self._lock = threading.RLock()

        from core.engine import TAFAEngine
        self.inner = TAFAEngine(symbol=symbol)

        self._init_ai_components()
        self.version = "TAFA_X_ULTIMATE_FINAL"
        self._last_rest_poll = 0.0
        self._cycle_delay = 0.5

        self._apply_runtime_config()
        log_event("boot", version=self.version, symbol=self.inner.symbol)
        log_engine(f"V10 wrapper ready on {self.inner.symbol}")

    def _init_ai_components(self):
        try:
            from ai.neural_parent_brain import NeuralParentBrain
            self.parent_brain = NeuralParentBrain()
        except Exception as e:
            logger.warning(f"NeuralParentBrain not available: {e}")
            self.parent_brain = None

        try:
            from ai.foundation_models import FoundationModelConsensus
            self.foundation_models = FoundationModelConsensus()
        except Exception as e:
            logger.warning(f"FoundationModelConsensus not available: {e}")
            self.foundation_models = None

    def start(self) -> None:
        with self._lock:
            self.inner.start()
            eq = self._equity()
            breaker.peak_equity = max(breaker.peak_equity, eq)
            breaker.day_start_equity = eq
            log_event("start", equity=eq)

    def stop(self) -> None:
        with self._lock:
            self.inner.stop()
            log_event("stop", equity=self._equity())

    def _equity(self) -> float:
        with self._lock:
            try:
                px = self.inner.last_price
                marks = {self.inner.symbol: px} if px else None
                return float(self.inner.paper.equity(marks))
            except Exception:
                return float(getattr(self.inner.paper, "balance", 1000) or 1000)

    def _apply_runtime_config(self) -> dict:
        from core.runtime_config import apply_to_runtime, get_config

        with self._lock:
            cfg = get_config()
            applied = apply_to_runtime(cfg)

            if hasattr(self.inner.strategy, "apply_config"):
                self.inner.strategy.apply_config(cfg)
                applied["strategy_instance"] = True

            if "min_conf" in cfg:
                threshold = max(0.0, min(1.0, float(cfg["min_conf"])))
                gate.min_confidence = threshold
                if self.parent_brain is not None:
                    self.parent_brain.min_confidence = threshold
                applied["quality_gate_min_confidence"] = threshold

            if self.parent_brain is not None and hasattr(self.parent_brain, "apply_config"):
                self.parent_brain.apply_config(cfg)
                applied["parent_brain"] = "configured"

            if "capital" in cfg:
                target = float(cfg["capital"])
                paper = self.inner.paper
                current_capital = paper.initial_capital
                if abs(current_capital - target) > 0.01:
                    if paper.positions or int(paper.trade_count) > 0:
                        logger.warning("Capital change refused: positions/trades exist")
                        applied["capital_pending_restart"] = target
                    else:
                        paper.initial_capital = target
                        paper.balance = target
                        paper.realized_pnl = 0.0
                        try:
                            from risk.risk_manager import risk_manager
                            risk_manager.start_balance = target
                            risk_manager.current_balance = target
                            risk_manager.daily_start_balance = target
                            risk_manager.highest_equity = target
                        except Exception as e:
                            logger.warning(f"Could not reset risk_manager: {e}")
                        applied["paper_capital"] = target
                        logger.info(f"Capital reset to {target}")
            return applied

    def _fetch_price(self) -> Optional[float]:
        """Centralized price retrieval with multiple fallbacks."""
        with self._lock:
            # 1. resolve_price (vérifie déjà la fraîcheur WS)
            if hasattr(self.inner, "resolve_price"):
                try:
                    price = self.inner.resolve_price()
                    if price is not None and price > 0:
                        return float(price)
                except Exception:
                    pass

            # 2. WebSocket price uniquement si frais (< 10s)
            if hasattr(self.inner, "_ws_price") and self.inner._ws_price:
                ts = getattr(self.inner, "_ws_price_ts", 0)
                if time.time() - ts < 10.0:
                    price = self.inner._ws_price
                    if price > 0:
                        return float(price)

            # 3. REST market
            try:
                price = self.inner.market.get_price(self.inner.symbol)
                if price > 0:
                    return float(price)
            except Exception:
                pass

            # 4. Dernière clôture
            if hasattr(self.inner.strategy, "closes") and self.inner.strategy.closes:
                try:
                    price = float(self.inner.strategy.closes[-1])
                    if price > 0:
                        return price
                except Exception:
                    pass

            logger.warning("No valid price retrieved")
            return None

    def _poll_rest_candles(self) -> None:
        with self._lock:
            now = time.time()
            if now - self._last_rest_poll < 45.0:
                return
            self._last_rest_poll = now

            try:
                bar = str(getattr(self.inner, "timeframe", None) or __import__("config", fromlist=["TIMEFRAME"]).TIMEFRAME)
            except Exception:
                bar = "4H"

            try:
                candles = self.inner.market.load_candles(self.inner.symbol, bar=bar, limit=5) or []
            except Exception as e:
                logger.debug(f"REST candle fetch failed: {e}")
                return

            if not candles:
                return

            known = len(getattr(self.inner.strategy, "closes", []) or [])
            for c in candles:
                try:
                    o = float(c.get("open", c.get("close", 0)))
                    h = float(c.get("high", c.get("close", 0)))
                    l = float(c.get("low", c.get("close", 0)))
                    cl = float(c["close"])
                    v = float(c.get("volume", 0) or 0)
                except Exception:
                    continue
                if known == 0 or not self.inner.strategy.closes or cl != self.inner.strategy.closes[-1]:
                    self.inner.strategy.update_bar(o, h, l, cl, v, confirmed=True)
                    known += 1
                    self.inner._ws_price = cl
                    self.inner.last_price = cl

    def _check_exit_conditions(self, price: float) -> Tuple[bool, Optional[str]]:
        with self._lock:
            try:
                from risk.risk_manager import risk_manager
                exit_signal = risk_manager.check_exit(price)
                if exit_signal in ("STOP_LOSS", "TAKE_PROFIT"):
                    return True, exit_signal
            except Exception as e:
                logger.error(f"Risk manager exit check failed: {e}")
            return False, None

    def _get_signal(self, price: float) -> Tuple[str, float, str]:
        with self._lock:
            base_signal = self.inner.strategy.analyze(self.inner.symbol, price) or "HOLD"
            conf = float(getattr(self.inner.strategy, "last_confidence", 0.5) or 0.5)
            regime = str(getattr(self.inner.strategy, "last_regime", "UNKNOWN") or "UNKNOWN")

            if self.foundation_models is not None:
                try:
                    model_decision = self.foundation_models.evaluate(
                        symbol=self.inner.symbol,
                        timeframe=str(getattr(self.inner, "timeframe", "4h")),
                        strategy=self.inner.strategy,
                        candidate_signal=base_signal,
                    )
                    if hasattr(model_decision, 'state') and model_decision.state not in {"disabled"}:
                        base_signal = model_decision.signal
                        conf = min(conf, float(getattr(model_decision, 'confidence', 0.0) or 0.0))
                except Exception as e:
                    logger.warning(f"Foundation model gate failed: {e}")

            if self.parent_brain is not None:
                try:
                    decision = self.parent_brain.decide(
                        self.inner.strategy, base_signal, price, risk_ok=True
                    )
                    return decision.signal, decision.confidence, decision.regime
                except Exception as e:
                    logger.warning(f"Parent brain decision failed: {e}")

            return base_signal, conf, regime

    def run_cycle(self) -> Optional[str]:
        with self._lock:
            if not self.inner.running:
                return None

            self.inner.cycle_count += 1   # ✅ FIX cycle

            equity = self._equity()
            ok, reason = breaker.allow(equity)
            if not ok:
                log_engine(f"V10 BLOCKED: {reason}", logging.ERROR)
                log_event("block", reason=reason, equity=equity)
                self._publish_status_with_block(reason)
                return "BLOCKED"

            try:
                self._apply_runtime_config()
            except Exception as e:
                logger.warning(f"Runtime config apply failed: {e}")

            try:
                from risk.risk_manager import risk_manager
                if not risk_manager.can_trade():
                    self._publish_status()
                    return "BLOCKED"
            except Exception as e:
                logger.error(f"Risk manager check failed: {e}")
                return "ERROR"

            try:
                price = self._fetch_price()
                if price is None or price <= 0:
                    log_engine("No valid price — cycle skipped")
                    self._publish_status()
                    return None

                self.inner.last_price = price
                self.inner._ws_price = price

                try:
                    self._poll_rest_candles()
                except Exception as e:
                    logger.warning(f"REST poll failed: {e}")

                should_exit, exit_reason = self._check_exit_conditions(price)
                if should_exit:
                    before = equity
                    self.inner.trader.execute(self.inner.symbol, "SELL", price)
                    self.inner.last_signal = exit_reason
                    after = self._equity()
                    pnl = after - before
                    breaker.record_trade(pnl)
                    log_event("trade", side="SELL", reason=exit_reason, price=price, pnl=pnl)
                    self._publish_status()
                    return exit_reason

                signal, conf, regime = self._get_signal(price)
                bars = len(getattr(self.inner.strategy, "closes", []) or [])

                if self.inner.cycle_count % 30 == 0:
                    logger.info(
                        "cycle=%s bars=%s price=%.2f sig=%s conf=%.2f regime=%s equity=%.2f",
                        self.inner.cycle_count, bars, price, signal, conf, regime, equity
                    )

                accept, why = gate.accept(signal, conf, regime, bars)
                self.inner.last_signal = signal if accept else "HOLD"

                if accept and signal in ("BUY", "SELL"):
                    qty = self.inner.paper.position_qty(self.inner.symbol)
                    if signal == "BUY" and qty > 0:
                        self._publish_status()
                        return "HOLD"
                    if signal == "SELL" and qty <= 0:
                        self._publish_status()
                        return "HOLD"

                    before = self._equity()
                    self.inner.trader.execute(self.inner.symbol, signal, price)
                    after = self._equity()
                    pnl = after - before
                    if signal == "SELL":
                        breaker.record_trade(pnl)
                        if self.parent_brain is not None:
                            try:
                                self.parent_brain.feedback(pnl)
                            except Exception as e:
                                logger.warning(f"Parent brain feedback failed: {e}")
                    log_event(
                        "trade", side=signal, price=price, conf=conf, regime=regime,
                        pnl=pnl if signal == "SELL" else 0, why=why,
                    )
                elif signal in ("BUY", "SELL") and not accept:
                    log_event("reject", signal=signal, why=why, conf=conf, regime=regime)

                self._publish_status()
                return self.inner.last_signal

            except Exception as exc:
                breaker.record_error()
                logger.exception("V10 cycle error: %s", exc)
                log_event("error", error=str(exc))
                return "ERROR"

    def _publish_status(self, extra: Optional[dict] = None):
        try:
            st = self.status()
            if extra:
                st.update(extra)
            publish_status(st)
        except Exception as e:
            logger.warning(f"Status publish failed: {e}")

    def _publish_status_with_block(self, reason: str):
        self._publish_status({"blocked": reason, "circuit": breaker.status()})

    def status(self) -> dict:
        with self._lock:
            st = self.inner.status()
            st["version"] = self.version
            st["circuit"] = breaker.status()
            st["neural_parent_brain"] = self.parent_brain.status() if self.parent_brain is not None else {"enabled": False}
            st["foundation_models"] = self.foundation_models.status() if self.foundation_models is not None else {
                "enabled": False,
                "state": "unavailable",
                "reason": "foundation_model_gate_not_loaded",
            }
            st["gate"] = {
                "min_confidence": gate.min_confidence,
                "min_bars": gate.min_bars,
            }
            eq = self._equity()
            capital = float(getattr(self.inner.paper, "initial_capital", 1000) or 1000)
            st["performance"] = {
                "equity": round(eq, 2),
                "session_pnl": round(eq - capital, 2),
                "session_return_pct": round((eq / capital - 1) * 100, 3) if capital else 0,
                "drawdown_pct": round(float(st.get("drawdown") or 0) * 100, 3),
                "cycle": st.get("cycle"),
                "trades": (st.get("paper") or {}).get("trades"),
            }

            if self.parent_brain is not None and hasattr(self.parent_brain, "last"):
                pb_last = self.parent_brain.last
                if pb_last is not None:
                    pb_dict = pb_last.as_dict() if hasattr(pb_last, "as_dict") else {}
                    if pb_dict:
                        ai = dict(st.get("ai") or {})
                        ai["signal"] = pb_dict.get("signal", ai.get("signal", "HOLD"))
                        ai["confidence"] = pb_dict.get("confidence", ai.get("confidence", 0.0))
                        ai["regime"] = pb_dict.get("regime", ai.get("regime", "UNKNOWN"))
                        ai["reason"] = pb_dict.get("reason", "")
                        ai["parent_brain"] = True
                        st["ai"] = ai
                        st["last_signal"] = ai["signal"]

            return st