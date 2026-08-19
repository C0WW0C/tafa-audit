#!/usr/bin/env python3
"""TAFA V10 — Monitor production metrics (API :8765)."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime

DEFAULT_BASE = "http://127.0.0.1:8765"

# Seuils d'alerte (paper / prod)
THRESHOLDS = {
    "stale_s_warn": 15,
    "stale_s_crit": 30,
    "max_dd_warn_pct": 10.0,
    "max_dd_crit_pct": 20.0,
    "sharpe_warn": 0.0,
    "profit_factor_warn": 1.0,
    "session_dd_warn_pct": 8.0,
}


def get_json(url: str, timeout: float = 3.0) -> dict | list:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-store"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def flag(ok: bool, warn: bool = False) -> str:
    if not ok:
        return "CRIT"
    if warn:
        return "WARN"
    return "OK"


def line(label: str, value, status: str = "OK") -> str:
    return f"  [{status:4}] {label:<28} {value}"


def render(summary: dict, health: dict | None = None) -> tuple[str, int]:
    """Return (text, exit_code). exit 0=ok, 1=warn, 2=crit."""
    sess = summary.get("session") or {}
    hist = summary.get("historical") or {}
    kpis = summary.get("kpis") or {}
    h = summary.get("health") or health or {}

    exit_code = 0
    alerts: list[str] = []

    stale = h.get("stale_s")
    bot = h.get("bot_running", sess.get("running"))
    if not bot:
        alerts.append("bot not running")
        exit_code = max(exit_code, 2)
    if stale is not None:
        if stale > THRESHOLDS["stale_s_crit"]:
            alerts.append(f"status stale {stale}s")
            exit_code = max(exit_code, 2)
        elif stale > THRESHOLDS["stale_s_warn"]:
            alerts.append(f"status aging {stale}s")
            exit_code = max(exit_code, 1)

    dd_sess = float(kpis.get("drawdown_pct") or sess.get("drawdown_pct") or 0)
    dd_max = hist.get("max_drawdown_pct")
    if dd_max is not None and float(dd_max) > THRESHOLDS["max_dd_crit_pct"]:
        alerts.append(f"max DD {dd_max}%")
        exit_code = max(exit_code, 2)
    elif dd_max is not None and float(dd_max) > THRESHOLDS["max_dd_warn_pct"]:
        alerts.append(f"max DD {dd_max}%")
        exit_code = max(exit_code, 1)
    if dd_sess > THRESHOLDS["session_dd_warn_pct"]:
        alerts.append(f"session DD {dd_sess}%")
        exit_code = max(exit_code, 1)

    sharpe = hist.get("sharpe")
    if sharpe is not None and float(sharpe) < THRESHOLDS["sharpe_warn"]:
        alerts.append(f"sharpe {sharpe}")
        exit_code = max(exit_code, 1)

    pf = hist.get("profit_factor")
    if pf is not None and float(pf) < THRESHOLDS["profit_factor_warn"]:
        alerts.append(f"profit_factor {pf}")
        exit_code = max(exit_code, 1)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out = []
    out.append(f"=== TAFA PROD METRICS  {ts} ===")
    out.append("")
    out.append("HEALTH")
    out.append(line("bot_running", bot, flag(bool(bot))))
    out.append(line("stale_s", stale if stale is not None else "—",
                    flag(stale is None or stale <= THRESHOLDS["stale_s_crit"],
                         stale is not None and stale > THRESHOLDS["stale_s_warn"])))
    out.append(line("mode", sess.get("mode", "?")))
    out.append(line("version", sess.get("version") or summary.get("server") or "—"))
    out.append(line("symbol", sess.get("symbol", "—")))
    out.append(line("cycle", sess.get("cycle", "—")))
    out.append("")
    out.append("SESSION")
    out.append(line("price", sess.get("last_price")))
    out.append(line("signal", sess.get("last_signal")))
    out.append(line("confidence", sess.get("confidence")))
    out.append(line("regime", sess.get("regime")))
    out.append(line("equity", kpis.get("equity") if kpis.get("equity") is not None else sess.get("equity")))
    out.append(line("session_pnl", kpis.get("session_pnl") if kpis.get("session_pnl") is not None else sess.get("session_pnl")))
    out.append(line("session_return_%", kpis.get("session_return_pct") if kpis.get("session_return_pct") is not None else sess.get("session_return_pct")))
    out.append(line("drawdown_%", dd_sess,
                    flag(dd_sess <= THRESHOLDS["session_dd_warn_pct"], dd_sess > THRESHOLDS["session_dd_warn_pct"] * 0.7)))
    out.append(line("open_positions", sess.get("open_positions")))
    out.append(line("can_trade", sess.get("can_trade")))
    out.append("")
    out.append("HISTORICAL")
    out.append(line("trades", hist.get("trades") if hist.get("trades") is not None else kpis.get("trades")))
    out.append(line("win_rate_%", hist.get("win_rate_pct") if hist.get("win_rate_pct") is not None else kpis.get("win_rate_pct")))
    out.append(line("profit_factor", pf, flag(pf is None or float(pf) >= THRESHOLDS["profit_factor_warn"])))
    out.append(line("sharpe", sharpe, flag(sharpe is None or float(sharpe) >= THRESHOLDS["sharpe_warn"])))
    out.append(line("sortino", hist.get("sortino")))
    out.append(line("calmar", hist.get("calmar")))
    out.append(line("max_drawdown_%", dd_max,
                    flag(dd_max is None or float(dd_max) <= THRESHOLDS["max_dd_crit_pct"],
                         dd_max is not None and float(dd_max) > THRESHOLDS["max_dd_warn_pct"])))
    out.append(line("expectancy", hist.get("expectancy") if hist.get("expectancy") is not None else kpis.get("expectancy")))
    out.append(line("total_pnl", hist.get("total_pnl")))
    out.append("")
    if alerts:
        out.append("ALERTS: " + " | ".join(alerts))
    else:
        out.append("ALERTS: none")
    out.append("")
    return "\n".join(out), exit_code


def main() -> int:
    ap = argparse.ArgumentParser(description="Monitor TAFA production metrics")
    ap.add_argument("--base", default=DEFAULT_BASE, help="Dashboard base URL")
    ap.add_argument("--watch", type=float, default=0, help="Refresh interval seconds (0=once)")
    ap.add_argument("--json", action="store_true", help="Raw JSON dump of /api/performance/summary")
    args = ap.parse_args()
    url = args.base.rstrip("/") + "/api/performance/summary"

    def once() -> int:
        try:
            data = get_json(url)
        except Exception as e:
            print(f"[CRIT] cannot reach {url}: {e}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(data, indent=2, default=str))
            return 0 if data.get("ok", True) else 1
        text, code = render(data if isinstance(data, dict) else {})
        print(text)
        return code

    if args.watch and args.watch > 0:
        while True:
            # clear-ish
            print("\033[2J\033[H", end="")
            code = once()
            try:
                time.sleep(args.watch)
            except KeyboardInterrupt:
                print("\nstop")
                return code
    return once()


if __name__ == "__main__":
    raise SystemExit(main())
