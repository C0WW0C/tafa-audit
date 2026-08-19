# ============================================================
# TAFA V7 PRO — Smart Alert System (INNOVATION)
# Rule-based + threshold alerts with cooldown dedup.
# ============================================================
from __future__ import annotations

import time
import threading
from typing import Callable, Optional

from logger import logger


class AlertRule:
    def __init__(self, name: str, condition: Callable, message: str,
                 level: str = "WARNING", cooldown: float = 300.0):
        self.name      = name
        self.condition = condition
        self.message   = message
        self.level     = level.upper()
        self.cooldown  = cooldown
        self._last_fired: float = 0.0
        self._lock = threading.Lock()   # ✅ thread safety

    def check(self, ctx: dict) -> Optional[dict]:
        with self._lock:
            if time.time() - self._last_fired < self.cooldown:
                return None
            try:
                triggered = self.condition(ctx)
            except Exception:
                return None
            if triggered:
                self._last_fired = time.time()
                msg = self.message.format(**ctx)
                return {"rule": self.name, "level": self.level, "message": msg, "ts": time.time()}
            return None


class SmartAlerts:
    """
    Evaluates alert rules on every engine cycle.
    Built-in rules: drawdown warning, daily loss, price spike,
                    no-signal timeout, equity new high.
    """

    def __init__(self):
        self._rules: list[AlertRule] = []
        self._fired: list[dict] = []
        self._lock = threading.RLock()
        self._setup_default_rules()
        logger.info("Smart Alerts initialized")

    def _setup_default_rules(self) -> None:
        self.add_rule(AlertRule(
            name="DD_WARNING",
            condition=lambda ctx: ctx.get("drawdown", 0) >= 0.07,
            message="⚠️ Drawdown {drawdown:.1%} — approaching max limit",
            level="WARNING",
            cooldown=600,
        ))
        self.add_rule(AlertRule(
            name="DD_CRITICAL",
            condition=lambda ctx: ctx.get("drawdown", 0) >= 0.09,
            message="🚨 CRITICAL drawdown {drawdown:.1%} — near circuit breaker",
            level="CRITICAL",
            cooldown=300,
        ))
        self.add_rule(AlertRule(
            name="STRONG_BUY",
            condition=lambda ctx: ctx.get("signal") == "BUY" and ctx.get("confidence", 0) >= 0.70,
            message="🟢 STRONG BUY signal on {symbol} @ {price:.2f} conf={confidence:.0%}",
            level="INFO",
            cooldown=1800,
        ))
        self.add_rule(AlertRule(
            name="STRONG_SELL",
            condition=lambda ctx: ctx.get("signal") == "SELL" and ctx.get("confidence", 0) >= 0.65,
            message="🔴 STRONG SELL signal on {symbol} @ {price:.2f} conf={confidence:.0%}",
            level="INFO",
            cooldown=1800,
        ))
        self.add_rule(AlertRule(
            name="PRICE_SPIKE",
            condition=lambda ctx: abs(ctx.get("price_change_pct", 0)) >= 3.0,
            message="⚡ Price spike {price_change_pct:+.1f}% on {symbol} @ {price:.2f}",
            level="WARNING",
            cooldown=900,
        ))
        self.add_rule(AlertRule(
            name="EQUITY_HIGH",
            condition=lambda ctx: ctx.get("new_equity_high", False),
            message="🏆 New equity high: ${equity:.2f} on {symbol}",
            level="INFO",
            cooldown=3600,
        ))
        self.add_rule(AlertRule(
            name="RISK_BLOCKED",
            condition=lambda ctx: not ctx.get("can_trade", True),
            message="🛑 Risk Manager BLOCKED trading — drawdown={drawdown:.1%}",
            level="CRITICAL",
            cooldown=600,
        ))

    def add_rule(self, rule: AlertRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def evaluate(self, ctx: dict) -> list[dict]:
        fired = []
        with self._lock:
            # Copie locale pour éviter les modifications concurrentes
            rules = list(self._rules)

        for rule in rules:
            alert = rule.check(ctx)
            if alert:
                fired.append(alert)
                with self._lock:
                    self._fired.append(alert)
                    if len(self._fired) > 1000:
                        self._fired.pop(0)
                lvl = alert["level"]
                msg = alert["message"]
                if lvl == "CRITICAL":
                    logger.error(f"[ALERT] {msg}")
                elif lvl == "WARNING":
                    logger.warning(f"[ALERT] {msg}")
                else:
                    logger.info(f"[ALERT] {msg}")
        return fired

    def get_recent(self, n: int = 50) -> list[dict]:
        with self._lock:
            return list(self._fired[-n:])

    def clear(self) -> None:
        with self._lock:
            self._fired.clear()


alerts = SmartAlerts()