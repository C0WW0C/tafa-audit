# ============================================================
# TAFA V7 PRO — Performance Monitor (session + historique)
# Agrège status live, trades SQLite et PerformanceAnalytics.
# ============================================================
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DB_CANDIDATES = [
    ROOT / "tafa_v7.db",
    ROOT / "data" / "tafa_v7.db",
    ROOT / "data" / "tafa_fusion_memory.sqlite",
]

# Thread safety
_lock = threading.RLock()


def _find_db() -> Optional[Path]:
    for p in DB_CANDIDATES:
        if p.exists():
            return p
    return None


def _query(sql: str, args: tuple = ()) -> List[dict]:
    db = _find_db()
    if not db:
        return []
    conn = None
    try:
        conn = sqlite3.connect(str(db), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def load_trade_pnls(limit: int = 500) -> List[float]:
    with _lock:
        rows = _query(
            "SELECT pnl FROM trades WHERE pnl IS NOT NULL ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        # Chronological order
        pnls = [float(r["pnl"]) for r in reversed(rows) if r.get("pnl") is not None]
        return pnls


def load_equity_snapshots(limit: int = 200) -> List[dict]:
    with _lock:
        return list(
            reversed(
                _query(
                    "SELECT timestamp, balance, equity, pnl, drawdown "
                    "FROM performance ORDER BY id DESC LIMIT ?",
                    (int(limit),),
                )
            )
        )


def session_from_status(status: Optional[dict] = None) -> dict:
    """Live KPIs from status_bridge payload."""
    with _lock:
        if status is None:
            try:
                from core.status_bridge import read
                status = read() or {}
            except Exception:
                status = {}

        paper = status.get("paper") or {}
        ai = status.get("ai") or {}
        risk = status.get("risk") or {}
        capital = float(
            paper.get("initial_capital")
            or (status.get("params") or {}).get("capital")
            or paper.get("balance")
            or 1000.0
        )
        equity = float(paper.get("equity") or capital)
        balance = float(paper.get("balance") or capital)
        pnl = equity - capital
        ret_pct = (equity / capital - 1.0) * 100.0 if capital else 0.0
        dd = float(status.get("drawdown") or risk.get("drawdown") or 0.0)
        if dd <= 1.0:
            dd_pct = dd * 100.0
        else:
            dd_pct = dd

        positions = paper.get("positions") or {}
        open_n = 0
        if isinstance(positions, dict):
            for v in positions.values():
                qty = float((v or {}).get("qty") or (v or {}).get("quantity") or 0)
                if qty > 0:
                    open_n += 1

        return {
            "running": bool(status.get("running")),
            "mode": status.get("mode", "PAPER"),
            "symbol": status.get("symbol"),
            "cycle": int(status.get("cycle") or 0),
            "last_price": status.get("last_price"),
            "last_signal": status.get("last_signal") or ai.get("signal"),
            "confidence": ai.get("confidence"),
            "regime": ai.get("regime"),
            "capital": round(capital, 2),
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "session_pnl": round(pnl, 2),
            "session_return_pct": round(ret_pct, 3),
            "drawdown_pct": round(dd_pct, 3),
            "open_positions": open_n,
            "can_trade": status.get("can_trade", risk.get("can_trade", True)),
            "updated_at": status.get("updated_at"),
            "version": status.get("version"),
        }


def historical_metrics(initial_capital: float = 1000.0) -> dict:
    with _lock:
        pnls = load_trade_pnls(500)
        try:
            from core.performance_analytics import analytics
            metrics = analytics.compute(pnls, initial_capital=initial_capital)
        except Exception:
            metrics = {
                "trades": len(pnls),
                "total_pnl": round(sum(pnls), 2) if pnls else 0.0,
                "win_rate_pct": None,
            }
        snaps = load_equity_snapshots(100)
        metrics["snapshots"] = len(snaps)
        metrics["last_snapshot"] = snaps[-1] if snaps else None
        metrics["db"] = str(_find_db() or "none")
        return metrics


def full_report(status: Optional[dict] = None) -> Dict[str, Any]:
    with _lock:
        sess = session_from_status(status)
        capital = float(sess.get("capital") or 1000.0)
        hist = historical_metrics(initial_capital=capital)
        health = {
            "bot_running": sess["running"],
            "stale_s": None,
            "ok": True,
        }
        ts = sess.get("updated_at")
        if ts:
            try:
                age = time.time() - float(ts)
                health["stale_s"] = round(age, 1)
                if sess["running"] and age > 30:
                    health["ok"] = False
                    health["note"] = "status stale (>30s)"
            except Exception:
                pass

        return {
            "ok": True,
            "ts": time.time(),
            "session": sess,
            "historical": hist,
            "health": health,
            "kpis": {
                "equity": sess["equity"],
                "session_pnl": sess["session_pnl"],
                "session_return_pct": sess["session_return_pct"],
                "drawdown_pct": sess["drawdown_pct"],
                "trades": hist.get("trades"),
                "win_rate_pct": hist.get("win_rate_pct"),
                "sharpe": hist.get("sharpe"),
                "profit_factor": hist.get("profit_factor"),
                "max_drawdown_pct": hist.get("max_drawdown_pct"),
                "expectancy": hist.get("expectancy"),
            },
        }