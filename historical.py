# ============================================================
# TAFA V7 PRO — Historical Backtester (CSV / OHLCV)
# ============================================================
"""Replay strategy on real historical candles with fees, ATR SL/TP, metrics.

Imports of project modules are LAZY so pytest collection on Windows
does not require `trading` / `data` on sys.path at import time.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]


def _ensure_root_on_path() -> Path:
    root = str(_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return _ROOT


def _get_strategy_class():
    _ensure_root_on_path()
    from trading.intelligent_strategy import IntelligentStrategy
    return IntelligentStrategy


def _load_csv_candles(path):
    _ensure_root_on_path()
    from data.loader import load_csv_candles
    return load_csv_candles(path)


def _default_dataset(timeframe: str = "15m"):
    _ensure_root_on_path()
    from data.loader import default_dataset
    return default_dataset(timeframe)


def _capital_defaults():
    _ensure_root_on_path()
    try:
        from config import DEFAULT_SYMBOL, INITIAL_CAPITAL
        return float(INITIAL_CAPITAL), str(DEFAULT_SYMBOL)
    except Exception:
        return 1000.0, "BTC-USDC"


def atr_series(candles: List[dict], period: int = 14) -> List[Optional[float]]:
    atr: List[Optional[float]] = [None] * len(candles)
    trs: List[float] = []
    for i, c in enumerate(candles):
        if i == 0:
            tr = c["high"] - c["low"]
        else:
            prev = candles[i - 1]["close"]
            tr = max(
                c["high"] - c["low"],
                abs(c["high"] - prev),
                abs(c["low"] - prev),
            )
        trs.append(tr)
        if i >= period - 1:
            atr[i] = sum(trs[i - period + 1 : i + 1]) / period
    return atr


@dataclass
class BacktestConfig:
    capital: float = 1000.0
    pos_frac: float = 0.15
    fee_bps: float = 8.0
    train_ratio: float = 0.2
    atr_sl: float = 2.0
    atr_tp: float = 3.5
    symbol: str = "BTC-USDC"
    target_tp_pct: Optional[float] = None
    net_target_usd: Optional[float] = None

    def __post_init__(self) -> None:
        # Fill from config only when instance is created (not at import)
        if self.capital == 1000.0 and self.symbol == "BTC-USDC":
            cap, sym = _capital_defaults()
            # only override if user left defaults — still ok to refresh from config
            object.__setattr__(self, "capital", float(self.capital if self.capital != 1000.0 else cap) if False else float(self.capital))
            # Keep explicit constructor values; defaults already match config typical values
            pass


@dataclass
class BacktestResult:
    source: Optional[str] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    bars: int = 0
    from_ts: Optional[str] = None
    to_ts: Optional[str] = None
    trades: int = 0
    winrate_pct: float = 0.0
    total_pnl: float = 0.0
    final_equity: float = 0.0
    return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: Optional[float] = None
    exit_reasons: Dict[str, int] = field(default_factory=dict)
    learner_weights: Dict[str, float] = field(default_factory=dict)
    equity_curve: List[float] = field(default_factory=list)
    trade_log: List[dict] = field(default_factory=list)
    target_tp_pct: Optional[float] = None
    net_target_usd: Optional[float] = None
    net_target_reached: bool = False

    def to_dict(self, include_curve: bool = False) -> dict:
        d = asdict(self)
        d["from"] = d.pop("from_ts")
        d["to"] = d.pop("to_ts")
        if not include_curve:
            d.pop("equity_curve", None)
            d.pop("trade_log", None)
        return d


class HistoricalBacktester:
    """Full historical replay of IntelligentStrategy on OHLCV candles."""

    def __init__(self, cfg: Optional[BacktestConfig] = None) -> None:
        _ensure_root_on_path()
        if cfg is None:
            cap, sym = _capital_defaults()
            cfg = BacktestConfig(capital=cap, symbol=sym)
        self.cfg = cfg

    @staticmethod
    def load_candles(path: str | Path | None = None, timeframe: str = "15m") -> List[dict]:
        _ensure_root_on_path()
        if path is None:
            path = _default_dataset(timeframe)
        p = Path(path)
        if p.suffix.lower() == ".csv":
            return _load_csv_candles(p)
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "candles" in data:
            return data["candles"]
        if isinstance(data, list):
            return data
        raise ValueError(f"Unsupported data format: {p}")

    def run(self, candles: List[dict]) -> BacktestResult:
        if not candles:
            return BacktestResult(final_equity=self.cfg.capital)

        IntelligentStrategy = _get_strategy_class()
        cfg = self.cfg
        strat = IntelligentStrategy()
        balance = float(cfg.capital)
        qty = 0.0
        entry = 0.0
        stop = 0.0
        take = 0.0
        entry_fee = 0.0
        target_reached = False
        trades: List[dict] = []
        equity: List[float] = []
        atrs = atr_series(candles)
        warm = max(int(len(candles) * cfg.train_ratio), getattr(strat, "min_bars", 50))

        for i, c in enumerate(candles):
            strat.update_bar(
                c["open"], c["high"], c["low"], c["close"], c.get("volume", 0),
                confirmed=True,
            )
            px = float(c["close"])
            equity.append(balance + qty * px)

            if qty > 0:
                hit_sl = c["low"] <= stop
                hit_tp = c["high"] >= take
                signal = (
                    strat.analyze(cfg.symbol, px, already_updated=True)
                    if i >= warm
                    else "HOLD"
                )
                exit_px = exit_reason = None
                if hit_sl:
                    exit_px, exit_reason = stop, "SL"
                elif hit_tp:
                    exit_px, exit_reason = take, "TP"
                elif signal == "SELL":
                    exit_px, exit_reason = px, "SIGNAL"
                if exit_px is not None:
                    proceeds = qty * float(exit_px)
                    fee = proceeds * cfg.fee_bps / 10_000
                    pnl = proceeds - fee - entry_fee - qty * entry
                    balance += proceeds - fee
                    trades.append(
                        {
                            "side": "SELL",
                            "price": float(exit_px),
                            "qty": qty,
                            "pnl": pnl,
                            "reason": exit_reason,
                            "i": i,
                            "ts": c.get("ts"),
                        }
                    )
                    if hasattr(strat, "feedback"):
                        try:
                            strat.feedback(pnl > 0)
                        except TypeError:
                            pass
                    qty = 0.0
                    entry_fee = 0.0
                    continue

            if qty == 0 and cfg.net_target_usd is not None and balance - cfg.capital >= cfg.net_target_usd:
                target_reached = True
                break

            if qty == 0 and i >= warm:
                signal = strat.analyze(cfg.symbol, px, already_updated=True)
                if signal == "BUY":
                    notional = balance * cfg.pos_frac
                    if notional <= 0:
                        continue
                    fee = notional * cfg.fee_bps / 10_000
                    if notional + fee > balance:
                        continue
                    qty = notional / px
                    entry = px
                    balance -= notional + fee
                    entry_fee = fee
                    a = atrs[i] or (px * 0.01)
                    stop = entry - cfg.atr_sl * a
                    take = (
                        entry * (1 + cfg.target_tp_pct / 100)
                        if cfg.target_tp_pct is not None
                        else entry + cfg.atr_tp * a
                    )
                    trades.append(
                        {
                            "side": "BUY",
                            "price": px,
                            "qty": qty,
                            "i": i,
                            "ts": c.get("ts"),
                            "stop": stop,
                            "take": take,
                        }
                    )

        if qty > 0:
            px = float(candles[-1]["close"])
            proceeds = qty * px
            fee = proceeds * cfg.fee_bps / 10_000
            pnl = proceeds - fee - entry_fee - qty * entry
            balance += proceeds - fee
            trades.append(
                {
                    "side": "SELL",
                    "price": px,
                    "qty": qty,
                    "pnl": pnl,
                    "reason": "EOD",
                    "i": len(candles) - 1,
                    "ts": candles[-1].get("ts"),
                }
            )
            qty = 0.0
            entry_fee = 0.0

        sells = [t for t in trades if t["side"] == "SELL" and "pnl" in t]
        wins = [t for t in sells if t["pnl"] > 0]
        losses = [t for t in sells if t["pnl"] <= 0]
        peak = cfg.capital
        max_dd = 0.0
        for eq in equity:
            peak = max(peak, eq)
            if peak:
                max_dd = max(max_dd, (peak - eq) / peak)
        gross_win = sum(t["pnl"] for t in wins) if wins else 0.0
        gross_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0.0
        weights = {}
        if hasattr(strat, "learner") and hasattr(strat.learner, "normalized"):
            weights = {k: round(v, 3) for k, v in strat.learner.normalized().items()}

        return BacktestResult(
            source=candles[0].get("source"),
            symbol=candles[0].get("symbol") or cfg.symbol,
            timeframe=candles[0].get("timeframe"),
            bars=len(candles),
            from_ts=candles[0].get("ts"),
            to_ts=candles[-1].get("ts"),
            trades=len(sells),
            winrate_pct=round(len(wins) / len(sells) * 100, 2) if sells else 0.0,
            total_pnl=round(sum(t["pnl"] for t in sells), 2),
            final_equity=round(balance, 2),
            return_pct=round((balance / cfg.capital - 1) * 100, 2),
            max_drawdown_pct=round(max_dd * 100, 2),
            avg_win=round(sum(t["pnl"] for t in wins) / len(wins), 2) if wins else 0.0,
            avg_loss=round(sum(t["pnl"] for t in losses) / len(losses), 2) if losses else 0.0,
            profit_factor=round(gross_win / gross_loss, 3) if gross_loss else None,
            exit_reasons={
                r: sum(1 for t in sells if t.get("reason") == r)
                for r in ("SL", "TP", "SIGNAL", "EOD")
            },
            learner_weights=weights,
            equity_curve=equity,
            trade_log=trades,
            target_tp_pct=cfg.target_tp_pct,
            net_target_usd=cfg.net_target_usd,
            net_target_reached=target_reached,
        )

    def run_file(
        self,
        path: str | Path | None = None,
        timeframe: str = "15m",
    ) -> BacktestResult:
        candles = self.load_candles(path, timeframe=timeframe)
        return self.run(candles)

    def save_report(
        self,
        result: BacktestResult,
        out: str | Path | None = None,
        include_curve: bool = False,
    ) -> Path:
        out_path = Path(out) if out else _ROOT / "data" / "datasets" / "last_backtest_report.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result.to_dict(include_curve=include_curve), indent=2),
            encoding="utf-8",
        )
        return out_path


def run_historical(
    csv: str | None = None,
    timeframe: str = "15m",
    capital: float | None = None,
    **kwargs: Any,
) -> dict:
    """Convenience API used by CLI and other modules."""
    _ensure_root_on_path()
    fields = set(BacktestConfig.__dataclass_fields__)
    cfg_kwargs = {k: v for k, v in kwargs.items() if k in fields}
    if capital is not None:
        cfg_kwargs["capital"] = float(capital)
    elif "capital" not in cfg_kwargs:
        cap, _ = _capital_defaults()
        cfg_kwargs["capital"] = cap
    cfg = BacktestConfig(**cfg_kwargs)
    bt = HistoricalBacktester(cfg)
    result = bt.run_file(csv, timeframe=timeframe)
    bt.save_report(result)
    return result.to_dict()
