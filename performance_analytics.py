# ============================================================
# TAFA V7 PRO — Performance Analytics (INNOVATION)
# Sharpe, Sortino, Calmar, Expectancy, Consecutive stats.
# ============================================================
from __future__ import annotations

import math
from typing import Optional


class PerformanceAnalytics:
    """
    Advanced performance metrics from trade list.
    All metrics computed from realized PnL list.
    """

    def __init__(self, risk_free_rate: float = 0.04):
        self.rfr = risk_free_rate  # annual

    def compute(self, pnls: list[float], initial_capital: float = 1000.0) -> dict:
        if not pnls:
            return self._empty()

        n = len(pnls)
        wins   = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        total_pnl   = sum(pnls)
        win_rate    = len(wins) / n
        avg_win     = sum(wins) / len(wins) if wins else 0.0
        avg_loss    = abs(sum(losses) / len(losses)) if losses else 0.0
        profit_factor = (sum(wins) / abs(sum(losses))) if (losses and wins) else None
        expectancy  = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

        # Equity curve
        equity = [initial_capital]
        for p in pnls:
            equity.append(equity[-1] + p)

        # Returns per trade
        returns = [pnls[i] / equity[i] for i in range(n) if equity[i] > 0]

        # Sharpe (annualised assuming ~252 trades/year)
        if returns and len(returns) > 1:
            mean_r = sum(returns) / len(returns)
            std_r  = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1))
            daily_rfr = self.rfr / 252
            sharpe = (mean_r - daily_rfr) / std_r * math.sqrt(252) if std_r > 0 else 0.0
        else:
            sharpe = 0.0

        # Sortino (downside deviation only)
        down = [r for r in returns if r < 0]
        if down and len(down) > 1:
            down_std = math.sqrt(sum(r ** 2 for r in down) / len(down))
            mean_r = sum(returns) / len(returns)
            sortino = (mean_r - self.rfr / 252) / down_std * math.sqrt(252) if down_std > 0 else 0.0
        else:
            sortino = 0.0

        # Max drawdown
        peak = initial_capital
        max_dd = 0.0
        for eq in equity:
            peak = max(peak, eq)
            if peak > 0:
                max_dd = max(max_dd, (peak - eq) / peak)

        # Calmar
        annual_return = (equity[-1] / initial_capital - 1) * (252 / max(n, 1))
        calmar = annual_return / max_dd if max_dd > 0 else None

        # Consecutive wins/losses
        max_consec_wins   = self._max_consecutive(pnls, positive=True)
        max_consec_losses = self._max_consecutive(pnls, positive=False)

        # Recovery factor
        recovery = total_pnl / (max_dd * initial_capital) if max_dd > 0 else None

        return {
            "trades":            n,
            "win_rate_pct":      round(win_rate * 100, 2),
            "total_pnl":         round(total_pnl, 2),
            "profit_factor":     round(profit_factor, 3) if profit_factor is not None else None,
            "expectancy":        round(expectancy, 2),
            "avg_win":           round(avg_win, 2),
            "avg_loss":          round(avg_loss, 2),
            "sharpe":            round(sharpe, 3),
            "sortino":           round(sortino, 3),
            "calmar":            round(calmar, 3) if calmar is not None else None,
            "max_drawdown_pct":  round(max_dd * 100, 2),
            "recovery_factor":   round(recovery, 3) if recovery is not None else None,
            "max_consec_wins":   max_consec_wins,
            "max_consec_losses": max_consec_losses,
            "final_equity":      round(equity[-1], 2),
            "return_pct":        round((equity[-1] / initial_capital - 1) * 100, 2),
        }

    @staticmethod
    def _max_consecutive(pnls: list[float], positive: bool) -> int:
        best = cur = 0
        for p in pnls:
            if (positive and p > 0) or (not positive and p <= 0):
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        return best

    @staticmethod
    def _empty() -> dict:
        return {k: None for k in [
            "trades", "win_rate_pct", "total_pnl", "profit_factor",
            "expectancy", "avg_win", "avg_loss", "sharpe", "sortino",
            "calmar", "max_drawdown_pct", "recovery_factor",
            "max_consec_wins", "max_consec_losses", "final_equity", "return_pct",
        ]}


analytics = PerformanceAnalytics()