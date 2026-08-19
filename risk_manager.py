# ============================================================
# TAFA V7 PRO
# RISK MANAGER CORE FINAL
# ============================================================

from datetime import datetime, timezone, date
import threading

from config import (
    INITIAL_CAPITAL,
    RISK_PER_TRADE,
    MAX_DAILY_LOSS,
    MAX_DRAWDOWN,
    STOP_LOSS_PERCENT,
    TAKE_PROFIT_PERCENT,
    TRAILING_PERCENT,
    TRAILING_STOP,
    USE_KELLY,
    KELLY_FRACTION
)

from logger import logger, log_risk


class RiskManager:
    def __init__(self):
        self._lock = threading.RLock()

        self.start_balance = INITIAL_CAPITAL
        self.current_balance = INITIAL_CAPITAL
        self.daily_start_balance = INITIAL_CAPITAL
        self.highest_equity = INITIAL_CAPITAL
        self.current_position = None
        self.daily_loss = 0
        self._last_reset_date = date.today()

        self.risk_per_trade = float(RISK_PER_TRADE)
        self.stop_loss_pct = float(STOP_LOSS_PERCENT)
        self.take_profit_pct = float(TAKE_PROFIT_PERCENT)
        self.trailing_pct = float(TRAILING_PERCENT)
        self.max_daily_loss = float(MAX_DAILY_LOSS)
        self.max_drawdown = float(MAX_DRAWDOWN)

        self.use_trailing_stop = bool(TRAILING_STOP)
        self.trailing_stop_price = None

        logger.info("TAFA V7 PRO Risk Manager Initialized")

    def _reset_daily_if_new_day(self):
        today = date.today()
        if today != self._last_reset_date:
            self.daily_start_balance = self.current_balance
            self.daily_loss = 0
            self._last_reset_date = today
            logger.info(f"Daily risk reset: start_balance={self.daily_start_balance}")

    def update_balance(self, balance):
        with self._lock:
            self._reset_daily_if_new_day()
            self.current_balance = balance
            if balance > self.highest_equity:
                self.highest_equity = balance

    def get_drawdown(self):
        with self._lock:
            if self.highest_equity == 0:
                return 0
            return (self.highest_equity - self.current_balance) / self.highest_equity

    def can_trade(self):
        with self._lock:
            self._reset_daily_if_new_day()
            drawdown = self.get_drawdown()

            if drawdown >= self.max_drawdown:
                log_risk("MAX_DRAWDOWN_REACHED", drawdown)
                return False

            if self.daily_start_balance > 0:
                daily_loss_pct = (self.daily_start_balance - self.current_balance) / self.daily_start_balance
                self.daily_loss = daily_loss_pct
            else:
                daily_loss_pct = 0

            if daily_loss_pct >= self.max_daily_loss:
                log_risk("MAX_DAILY_LOSS_REACHED", daily_loss_pct)
                return False

            return True

    def calculate_position_size(self, price):
        with self._lock:
            if price <= 0:
                return 0
            try:
                from config import ORDER_SIZE_USD, MIN_ORDER_USD
            except Exception:
                ORDER_SIZE_USD, MIN_ORDER_USD = 100, 10

            stop_distance_pct = self.stop_loss_pct / 100.0
            risk_amount = self.current_balance * self.risk_per_trade
            if stop_distance_pct <= 0:
                return 0
            qty_by_risk = risk_amount / (price * stop_distance_pct)

            max_notional = min(ORDER_SIZE_USD, self.current_balance * 0.95)
            qty_by_capital = max_notional / price

            qty = min(qty_by_risk, qty_by_capital)
            qty = round(qty, 6)

            if qty * price < MIN_ORDER_USD:
                return 0
            return qty

    def kelly_size(self, win_rate, reward_ratio):
        if not USE_KELLY:
            return 0
        loss_rate = 1 - win_rate
        kelly = ((reward_ratio * win_rate) - loss_rate) / reward_ratio
        kelly *= KELLY_FRACTION
        if kelly < 0:
            return 0
        return round(kelly, 4)

    def calculate_stop_loss(self, entry_price):
        pct = float(getattr(self, "stop_loss_pct", STOP_LOSS_PERCENT))
        return round(entry_price * (1 - pct / 100), 4)

    def calculate_take_profit(self, entry_price):
        pct = float(getattr(self, "take_profit_pct", TAKE_PROFIT_PERCENT))
        return round(entry_price * (1 + pct / 100), 4)

    def calculate_trailing_stop(self, current_price):
        pct = float(getattr(self, "trailing_pct", TRAILING_PERCENT))
        return round(current_price * (1 - pct / 100), 4)

    def register_position(self, symbol, side, qty, entry):
        with self._lock:
            if self.current_position is not None:
                logger.warning("Attempt to open new position while one is already open")
                return
            entry = float(entry)
            stop = self.calculate_stop_loss(entry)
            take = self.calculate_take_profit(entry)
            self.current_position = {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "entry": entry,
                "stop": stop,
                "take": take,
                "time": datetime.now(timezone.utc),
            }
            if self.use_trailing_stop:
                self.trailing_stop_price = self.calculate_trailing_stop(entry)
            else:
                self.trailing_stop_price = None
            log_risk("POSITION_OPEN", f"{side} {qty} @ {entry} SL={stop} TP={take}")

    def update_trailing_stop(self, current_price):
        if not self.use_trailing_stop or self.current_position is None:
            return
        with self._lock:
            new_stop = self.calculate_trailing_stop(current_price)
            if self.trailing_stop_price is None or new_stop > self.trailing_stop_price:
                self.trailing_stop_price = new_stop
                self.current_position["stop"] = new_stop

    def close_position(self):
        with self._lock:
            if self.current_position:
                log_risk("POSITION_CLOSE", f"closed {self.current_position.get('symbol')}")
            self.current_position = None
            self.trailing_stop_price = None

    def check_exit(self, price):
        with self._lock:
            if not self.current_position:
                return None
            pos = self.current_position
            entry = float(pos["entry"])
            price = float(price)

            if self.use_trailing_stop:
                self.update_trailing_stop(price)
                stop = self.trailing_stop_price if self.trailing_stop_price is not None else float(pos.get("stop"))
            else:
                stop = float(pos.get("stop") or self.calculate_stop_loss(entry))
            target = float(pos.get("take") or self.calculate_take_profit(entry))

            if price <= stop:
                return "STOP_LOSS"
            if price >= target:
                return "TAKE_PROFIT"
            return None


risk_manager = RiskManager()

__all__ = ["RiskManager", "risk_manager"]