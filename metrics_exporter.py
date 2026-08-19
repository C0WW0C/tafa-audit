#!/usr/bin/env python3
"""
TAFA V10 — Prometheus metrics exporter
Scrape: http://127.0.0.1:9108/metrics
Source: dashboard API http://127.0.0.1:8765/api/performance/summary + /api/status
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

DEFAULT_API = "http://127.0.0.1:8765"
DEFAULT_PORT = 9108

_lock = threading.Lock()
_cache: dict[str, Any] = {"ts": 0.0, "text": ""}


def _fetch(url: str, timeout: float = 2.5) -> dict:
    req = urllib.request.Request(url, headers={"Cache-Control": "no-store"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def build_metrics(api_base: str) -> str:
    api = api_base.rstrip("/")
    lines: list[str] = []
    lines.append("# HELP tafa_up 1 if metrics scrape of TAFA API succeeded")
    lines.append("# TYPE tafa_up gauge")
    try:
        summary = _fetch(api + "/api/performance/summary")
        status = _fetch(api + "/api/status")
        ok = 1
    except Exception as e:
        lines.append("tafa_up 0")
        lines.append(f"# scrape_error {e!r}")
        return "\n".join(lines) + "\n"

    sess = summary.get("session") or {}
    hist = summary.get("historical") or {}
    health = summary.get("health") or {}
    kpis = summary.get("kpis") or {}
    paper = status.get("paper") or {}
    circuit = status.get("circuit") or {}
    perf = status.get("performance") or {}

    def g(name: str, help_: str, val: float, labels: str = "") -> None:
        lines.append(f"# HELP {name} {help_}")
        lines.append(f"# TYPE {name} gauge")
        if labels:
            lines.append(f"{name}{{{labels}}} {val}")
        else:
            lines.append(f"{name} {val}")

    g("tafa_up", "1 if TAFA API scrape succeeded", float(ok))

    mode = str(sess.get("mode") or status.get("mode") or "PAPER").replace('"', "")
    version = str(sess.get("version") or status.get("version") or "unknown").replace('"', "")
    symbol = str(sess.get("symbol") or status.get("symbol") or "BTC-USDC").replace('"', "")
    labels = f'mode="{mode}",version="{version}",symbol="{symbol}"'

    g("tafa_bot_running", "Bot process running (1/0)", 1.0 if (health.get("bot_running") or status.get("running")) else 0.0, labels)
    g("tafa_stale_seconds", "Age of status bridge payload", _f(health.get("stale_s") if health.get("stale_s") is not None else status.get("stale_s")), labels)
    g("tafa_cycle", "Engine cycle counter", _f(sess.get("cycle") or status.get("cycle")), labels)
    g("tafa_last_price", "Last seen price", _f(sess.get("last_price") or status.get("last_price")), labels)
    g("tafa_equity", "Current equity", _f(kpis.get("equity") or sess.get("equity") or paper.get("equity") or perf.get("equity")), labels)
    g("tafa_balance", "Cash balance", _f(sess.get("balance") or paper.get("balance")), labels)
    g("tafa_session_pnl", "Session PnL", _f(kpis.get("session_pnl") or sess.get("session_pnl") or perf.get("session_pnl")), labels)
    g("tafa_session_return_pct", "Session return percent", _f(kpis.get("session_return_pct") or sess.get("session_return_pct")), labels)
    g("tafa_drawdown_pct", "Current drawdown percent", _f(kpis.get("drawdown_pct") or sess.get("drawdown_pct")), labels)
    g("tafa_open_positions", "Open positions count", _f(sess.get("open_positions")), labels)
    g("tafa_can_trade", "Risk allows trading", 1.0 if sess.get("can_trade", status.get("can_trade", True)) else 0.0, labels)
    g("tafa_confidence", "Model confidence 0-1", _f(sess.get("confidence") or (status.get("ai") or {}).get("confidence")), labels)

    sig = str(sess.get("last_signal") or status.get("last_signal") or "HOLD").upper()
    sig_map = {"BUY": 1.0, "SELL": -1.0, "HOLD": 0.0, "WATCH": 0.0, "BLOCKED": -2.0}
    g("tafa_signal", "Signal mapped BUY=1 SELL=-1 HOLD=0 BLOCKED=-2", sig_map.get(sig, 0.0), labels + f',signal="{sig}"')

    g("tafa_trades_total", "Closed trades count (historical)", _f(hist.get("trades") or kpis.get("trades")), labels)
    g("tafa_win_rate_pct", "Win rate percent", _f(hist.get("win_rate_pct") or kpis.get("win_rate_pct")), labels)
    g("tafa_profit_factor", "Profit factor", _f(hist.get("profit_factor") or kpis.get("profit_factor"), default=float("nan")), labels)
    g("tafa_sharpe", "Sharpe ratio", _f(hist.get("sharpe") or kpis.get("sharpe"), default=float("nan")), labels)
    g("tafa_sortino", "Sortino ratio", _f(hist.get("sortino"), default=float("nan")), labels)
    g("tafa_calmar", "Calmar ratio", _f(hist.get("calmar"), default=float("nan")), labels)
    g("tafa_max_drawdown_pct", "Max historical drawdown percent", _f(hist.get("max_drawdown_pct") or kpis.get("max_drawdown_pct")), labels)
    g("tafa_expectancy", "Expectancy per trade", _f(hist.get("expectancy") or kpis.get("expectancy"), default=float("nan")), labels)
    g("tafa_total_pnl", "Total realized PnL", _f(hist.get("total_pnl")), labels)

    g("tafa_circuit_tripped", "Circuit breaker tripped", 1.0 if circuit.get("tripped") else 0.0, labels)
    g("tafa_circuit_consec_losses", "Consecutive losses", _f(circuit.get("consec_losses")), labels)

    # sanitize NaN for Prometheus text format
    out = []
    for ln in lines:
        if " nan" in ln or ln.endswith(" nan"):
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


class Handler(BaseHTTPRequestHandler):
    api_base = DEFAULT_API
    cache_ttl = 2.0

    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path.split("?")[0] not in ("/metrics", "/"):
            self.send_response(404)
            self.end_headers()
            return
        now = time.time()
        with _lock:
            if now - _cache["ts"] > self.cache_ttl or not _cache["text"]:
                _cache["text"] = build_metrics(self.api_base)
                _cache["ts"] = now
            body = _cache["text"].encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default=DEFAULT_API, help="TAFA dashboard base URL")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    Handler.api_base = args.api
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"TAFA metrics exporter → http://127.0.0.1:{args.port}/metrics  (api={args.api})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("stop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
