# ============================================================
# TAFA V7 PRO — Dashboard Web Server (finalisé)
# Port 8765 · API complète alignée sur web/app.js
# ============================================================
from __future__ import annotations

import http.server
import hmac
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

WEB_DIR = Path(__file__).resolve().parent
ROOT_DIR = WEB_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from core import status_bridge
except ImportError:
    status_bridge = None

PORT = 8765
SERVER_NAME = "tafa_x_ultimate"
BIND_HOST = os.getenv("TAFA_DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_TOKEN = os.getenv("TAFA_DASHBOARD_TOKEN", "").strip()
MAX_BODY_BYTES = 65_536

PID_FILE = ROOT_DIR / "data" / "bot.pid"
CONFIG_FILE = ROOT_DIR / "data" / "config.json"
RUNTIME_CONFIG = ROOT_DIR / "data" / "runtime_config.json"
ELITE_PAPER_RUN_SCRIPT = ROOT_DIR / "run_elite_final_paper.py"
PAPER_RUN_SCRIPT = ROOT_DIR / "run_paper_demo.py"
RUN_SCRIPT = ELITE_PAPER_RUN_SCRIPT if ELITE_PAPER_RUN_SCRIPT.exists() else (PAPER_RUN_SCRIPT if PAPER_RUN_SCRIPT.exists() else (ROOT_DIR / "run_v10.py" if (ROOT_DIR / "run_v10.py").exists() else ROOT_DIR / "run.py"))
DB_CANDIDATES = [
    ROOT_DIR / "tafa_v7.db",
    ROOT_DIR / "data" / "tafa_v7.db",
    ROOT_DIR / "data" / "tafa_fusion_memory.sqlite",
]
LOG_DIR = ROOT_DIR / "logs"
_LOG_SECRET = re.compile(r"(?i)(OKX_(?:API_KEY|SECRET_KEY|PASSPHRASE)|OK-ACCESS-(?:KEY|SIGN|PASSPHRASE))([:=]\s*)([^\s,;]+)")
_httpd: http.server.ThreadingHTTPServer | None = None
_server_thread: threading.Thread | None = None


def _json_response(handler: http.server.BaseHTTPRequestHandler, code: int, payload: dict) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Referrer-Policy", "same-origin")
    handler.end_headers()
    handler.wfile.write(body)


def _static_response(
    handler: http.server.BaseHTTPRequestHandler,
    code: int,
    body: bytes,
    content_type: str,
) -> None:
    """Serve a small same-origin static response with safe browser headers."""
    handler.send_response(code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "public, max-age=86400")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    if body:
        handler.wfile.write(body)


def _bot_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        if os.name == "nt":
            res = subprocess.run(
                f'tasklist /fi "PID eq {pid}"',
                capture_output=True,
                text=True,
                shell=True,
            )
            return str(pid) in res.stdout
        os.kill(pid, 0)
        # Avoid trusting a stale PID which now belongs to another process.
        try:
            args = Path(f"/proc/{pid}/cmdline").read_text(encoding="utf-8", errors="ignore")
            return RUN_SCRIPT.name in args
        except Exception:
            return True
    except Exception:
        return False


def _find_db() -> Optional[Path]:
    for p in DB_CANDIDATES:
        if p.exists():
            return p
    return None


def _rows_to_dicts(rows) -> List[dict]:
    out = []
    for r in rows:
        if hasattr(r, "keys"):
            out.append({k: r[k] for k in r.keys()})
        elif isinstance(r, dict):
            out.append(r)
        else:
            out.append(dict(r))
    return out


def _query_table(table: str, limit: int = 100) -> List[dict]:
    if table not in {"trades", "signals", "performance"}:
        return []
    db = _find_db()
    if not db:
        return []
    try:
        limit = max(1, min(int(limit), 500))
        conn = sqlite3.connect(str(db), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        rows = _rows_to_dicts(cur.fetchall())
        return rows
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _is_loopback_bind() -> bool:
    return BIND_HOST in {"127.0.0.1", "::1", "localhost"}


def _mutation_authorized(handler: http.server.BaseHTTPRequestHandler) -> bool:
    """Control endpoints are local-only unless an explicit token is configured."""
    if _is_loopback_bind():
        return True
    supplied = handler.headers.get("X-TAFA-Token", "")
    ok = bool(DASHBOARD_TOKEN and hmac.compare_digest(supplied, DASHBOARD_TOKEN))
    if not ok:
        # ✅ FIX: journaliser les tentatives d'accès non autorisées (sans exposer le token)
        client = getattr(handler, "client_address", ("?", 0))
        _logger_server = __import__("logging").getLogger("tafa.server.auth")
        _logger_server.warning(
            "Accès mutation refusé depuis %s:%s — token absent ou invalide [%s]",
            client[0], client[1], handler.path,
        )
    return ok


def _load_config() -> dict:
    cfg: Dict[str, Any] = {}
    for path in (RUNTIME_CONFIG, CONFIG_FILE):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    cfg.update(data)
            except Exception:
                pass
    return cfg


def _redact_log_line(line: str) -> str:
    return _LOG_SECRET.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", line)


def _tail_logs(limit: int = 160) -> dict:
    """Provide a bounded, redacted local log tail for observability only."""
    limit = max(10, min(int(limit), 500))
    try:
        candidates = sorted(LOG_DIR.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True)[:4]
    except Exception:
        candidates = []
    files = []
    for path in candidates:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
            files.append({"file": path.name, "lines": [_redact_log_line(line) for line in lines]})
        except Exception as exc:
            files.append({"file": path.name, "lines": [], "error": str(exc)})
    return {"updated_at": time.time(), "files": files, "limit": limit}


def _observability_payload() -> dict:
    status = _status_payload()
    execution = status.get("execution") if isinstance(status.get("execution"), dict) else {}
    market = status.get("market") if isinstance(status.get("market"), dict) else {}
    ws = status.get("ws") if isinstance(status.get("ws"), dict) else {}
    return {
        "updated_at": time.time(),
        "execution": execution,
        "market_data": market,
        "neural": status.get("neural") or {},
        "remote_preflight": status.get("remote_preflight") or {"status": "PAPER_ONLY", "read_only": True},
        "bot": {key: status.get(key) for key in ("running", "mode", "last_signal", "last_error", "stale_s")},
        "ws": {"connected": bool(ws.get("connected")), "symbol": ws.get("symbol") or status.get("symbol")},
    }


def _save_config(params: dict) -> dict:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_config()
    existing.update(params)
    CONFIG_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    # Mirror to runtime_config for the engine
    try:
        RUNTIME_CONFIG.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        pass
    return existing


def _perf_report(status: dict | None = None) -> dict:
    try:
        from core.performance_monitor import full_report
        return full_report(status)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _equity_payload(limit: int = 360) -> dict:
    """Return the persisted paper-equity curve, newest records rendered chronologically."""
    rows = _query_table("performance", limit)
    points: List[dict] = []
    for row in reversed(rows):
        try:
            equity = float(row.get("equity"))
            if equity <= 0:
                continue
            points.append(
                {
                    "time": row.get("timestamp") or row.get("ts") or row.get("id"),
                    "equity": equity,
                    "balance": row.get("balance"),
                    "pnl": row.get("pnl"),
                    "drawdown": row.get("drawdown"),
                }
            )
        except (TypeError, ValueError):
            continue
    if not points:
        status = _status_payload()
        paper = status.get("paper") if isinstance(status.get("paper"), dict) else {}
        equity = paper.get("equity") or (status.get("performance") or {}).get("equity")
        try:
            if equity is not None and float(equity) > 0:
                points.append(
                    {
                        "time": status.get("updated_at") or time.time(),
                        "equity": float(equity),
                        "balance": paper.get("balance"),
                        "pnl": paper.get("session_pnl"),
                        "drawdown": status.get("drawdown"),
                    }
                )
        except (TypeError, ValueError):
            pass
    return {"ok": True, "mode": "PAPER", "source": "sqlite_performance" if rows else "status_snapshot", "points": points}


def _status_payload() -> dict:
    data: Dict[str, Any] = {}
    if status_bridge:
        try:
            data = status_bridge.read() or {}
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    data = dict(data)
    bot_alive = _bot_running()
    # FIX: also trust bridge heartbeat during startup race (PID not yet written)
    bridge_ts = data.get("updated_at")
    bridge_fresh = (
        bool(data.get("running"))
        and isinstance(bridge_ts, (int, float))
        and bridge_ts > 0
        and (time.time() - float(bridge_ts)) < 45  # FIX: align with bot_process.status_snapshot (45s)
    )
    data["running"] = bool(bot_alive or bridge_fresh)
    data["server_profile"] = SERVER_NAME
    data["run_script"] = RUN_SCRIPT.name
    data.setdefault("mode", "PAPER")
    data.setdefault("cycle", 0)
    data.setdefault("symbol", "BTC-USDC")
    data.setdefault("drawdown", 0)
    data.setdefault("can_trade", True)
    data.setdefault("ai", {})
    data.setdefault("paper", {})
    data.setdefault("ws", {})
    data.setdefault("neural", {})
    data.setdefault("execution", {"mode": "LOCAL_PAPER", "remote": False, "credentials_present": False})
    data.setdefault("remote_preflight", {"status": "PAPER_ONLY", "read_only": True, "orders_submitted": 0})
    # The dashboard reads market.book while the native engine publishes the
    # freshest public levels under ws.book. Mirror that verified WebSocket
    # book when the generic market adapter has no levels, so the interface
    # does not incorrectly display an empty market panel.
    market = data.get("market") if isinstance(data.get("market"), dict) else {}
    ws = data.get("ws") if isinstance(data.get("ws"), dict) else {}
    market_book = market.get("book") if isinstance(market.get("book"), dict) else {}
    ws_book = ws.get("book") if isinstance(ws.get("book"), dict) else {}
    if not (market_book.get("bids") or market_book.get("asks")) and (ws_book.get("bids") or ws_book.get("asks")):
        market = dict(market)
        market["book"] = dict(ws_book)
        market["source"] = "okx-websocket"
        data["market"] = market
    else:
        data.setdefault("market", market)
    try:
        from core.runtime_config import get_config
        data.setdefault("params", get_config())
    except Exception:
        data.setdefault("params", _load_config())
    data.setdefault("version", "TAFA_X_ULTIMATE_FINAL")

    # Stale detection (bridge file age)
    updated_at = data.get("updated_at")
    stale_s = None
    if isinstance(updated_at, (int, float)) and updated_at > 0:
        stale_s = max(0.0, time.time() - float(updated_at))
    # A dead bot is STOPPED, not a stale-running bot. Keep the raw heartbeat age
    # separately for diagnostics, but do not surface it as an active stale alert.
    data["heartbeat_age_s"] = stale_s
    data["stale_s"] = stale_s if data["running"] else 0.0  # FIX: use composite running, not bare bot_alive
    data["state"] = "RUNNING" if data["running"] else "STOPPED"  # FIX: idem

    # Preserve engine performance block; enrich from monitor without clobber
    engine_perf = data.get("performance") if isinstance(data.get("performance"), dict) else {}
    try:
        rep = _perf_report(data)
        mon_kpis = rep.get("kpis") if isinstance(rep.get("kpis"), dict) else {}
        merged = dict(engine_perf)
        for k, v in (mon_kpis or {}).items():
            if k not in merged or merged.get(k) in (None, {}, []):
                merged[k] = v
        # Prefer live paper equity if monitor left gaps
        paper = data.get("paper") or {}
        if merged.get("equity") in (None, 0) and paper.get("equity") is not None:
            merged["equity"] = paper.get("equity")
        data["performance"] = merged
        data["session"] = rep.get("session") or data.get("session") or {}
        health = rep.get("health") if isinstance(rep.get("health"), dict) else {}
        _running = bool(data["running"])  # FIX: use composite running (PID OR bridge_fresh)
        if stale_s is not None:
            health["stale_s"] = stale_s if _running else 0.0
            health["heartbeat_age_s"] = stale_s
            health["stale"] = bool(_running and stale_s > 30)
        health["bot_running"] = _running
        health["bridge"] = "ok" if status_bridge else "missing"
        data["health"] = health
    except Exception:
        if engine_perf:
            data["performance"] = engine_perf
        else:
            data.setdefault("performance", {})
        data.setdefault("health", {"stale_s": stale_s, "bot_running": bool(data["running"])})
    return data


def _candles_payload(symbol: str = "BTC-USDC", bar: str = "15m", limit: int = 200) -> dict:
    """OHLCV for desk chart — OKX public first, local CSV fallback. Closed bars only."""
    from core.candles_feed import candles_payload
    return candles_payload(symbol=symbol, bar=bar, limit=limit)



class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        # quieter logs
        sys.stderr.write("[web] %s\n" % (fmt % args))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        limit = 100
        try:
            limit = int(qs.get("limit", ["100"])[0])
        except Exception:
            pass

        try:
            # Browser favicon request: return a compact inline SVG rather than
            # a 404. The dashboard remains entirely local and dependency-free.
            if path == "/favicon.ico":
                _static_response(
                    self,
                    200,
                    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#0f1d1b"/><path d="M13 18h38v8H36v26h-8V26H13z" fill="#37d4a2"/></svg>',
                    "image/svg+xml; charset=utf-8",
                )
                return

            # The hosted development UI may inject this optional collector.
            # A harmless no-op avoids a console 404 on the standalone local
            # dashboard without granting any access to TAFA state or APIs.
            if path == "/__manus__/debug-collector.js":
                _static_response(
                    self,
                    200,
                    b"/* no-op: optional host debug collector is unavailable in the local TAFA dashboard. */\n",
                    "application/javascript; charset=utf-8",
                )
                return

            if path == "/api/stream":
                # The stdlib server exposes a same-origin SSE stream for bot
                # state. Market ticks remain on the exchange public WebSocket.
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache, no-store")
                self.send_header("Connection", "keep-alive")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                try:
                    while True:
                        payload = json.dumps(_status_payload(), default=str, separators=(",", ":"))
                        self.wfile.write(f"event: status\ndata: {payload}\n\n".encode("utf-8"))
                        self.wfile.flush()
                        time.sleep(1.0)
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    return

            if path in ("/api/status", "/api/bot/status", "/api/data"):
                _json_response(self, 200, _status_payload())
                return

            if path in ("/api/models/status", "/api/foundation-models"):
                status = _status_payload()
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "paper_only": True,
                        "models": status.get("foundation_models") or {
                            "enabled": False,
                            "state": "waiting_for_bot",
                            "reason": "aucun état publié par le moteur",
                        },
                    },
                )
                return

            if path == "/api/trades":
                rows = _query_table("trades", limit)
                _json_response(self, 200, rows)
                return

            if path == "/api/signals":
                rows = _query_table("signals", limit)
                _json_response(self, 200, rows)
                return

            if path == "/api/performance":
                rows = _query_table("performance", limit)
                _json_response(self, 200, rows)
                return

            if path in ("/api/equity", "/api/performance/equity"):
                _json_response(self, 200, _equity_payload(limit))
                return

            if path in ("/api/config", "/api/settings", "/api/params"):
                try:
                    from core.runtime_config import get_config
                    config = get_config()
                except Exception:
                    config = _load_config()
                _json_response(
                    self,
                    200,
                    {"ok": True, "success": True, "config": config},
                )
                return

            if path in ("/api/logs", "/api/logs/tail"):
                _json_response(self, 200, _tail_logs(qs.get("limit", ["160"])[0]))
                return

            if path in ("/api/observability", "/api/telemetry"):
                _json_response(self, 200, _observability_payload())
                return

            if path == "/api/health":
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "server": SERVER_NAME,
                        "bot_running": _bot_running(),
                        "db": str(_find_db() or "none"),
                        "ts": time.time(),
                    },
                )
                return

            if path == "/api/market/book":
                status = _status_payload()
                _json_response(
                    self,
                    200,
                    {
                        "ok": True,
                        "symbol": status.get("symbol"),
                        "market": status.get("market") or {},
                        "ws": status.get("ws") or {},
                    },
                )
                return

            if path in ("/api/candles", "/api/market/candles", "/api/ohlcv"):
                status = _status_payload()
                sym = (qs.get("symbol") or [status.get("symbol") or "BTC-USDC"])[0]
                bar = (qs.get("bar") or qs.get("tf") or ["15m"])[0]
                try:
                    lim = int((qs.get("limit") or ["200"])[0])
                except Exception:
                    lim = 200
                payload = _candles_payload(symbol=str(sym), bar=str(bar), limit=lim)
                _json_response(self, 200, payload)
                return

            if path in ("/api/market/binance/candles", "/api/binance/candles"):
                config = _load_config()
                symbol = (qs.get("symbol") or [config.get("binance_symbol") or "BTCUSDT"])[0]
                interval = (qs.get("interval") or [config.get("binance_interval") or "1h"])[0]
                try:
                    lim = int((qs.get("limit") or ["250"])[0])
                except Exception:
                    lim = 250
                payload = _candles_payload(symbol=str(symbol), bar=str(interval), limit=max(20, min(lim, 500)))
                payload.setdefault("source", "public_market")
                payload.setdefault("symbol", symbol)
                payload.setdefault("interval", interval)
                _json_response(self, 200, payload)
                return

            if path == "/api/manual-orders":
                status = _status_payload()
                # engine.status() publishes "manual_orders"; fallback to tape alias
                orders = (
                    status.get("manual_orders")
                    or status.get("manual_order_tape")
                    or []
                )
                _json_response(self, 200, {"ok": True, "orders": orders})
                return

            if path in ("/api/engines", "/api/engine"):
                _json_response(self, 501, {
                    "ok": False,
                    "error": "Sélection de moteur externe non incluse dans cette version.",
                })
                return

            if path in ("/api/performance/summary", "/api/perf", "/api/metrics"):
                st = _status_payload()
                report = _perf_report(st)
                report["server"] = SERVER_NAME
                _json_response(self, 200, report)
                return

            # The legacy desk contained manual-paper controls. The supported
            # dashboard is intentionally observation and configuration only.
            if path in ("/desk", "/tv", "/blotter"):
                _json_response(self, 403, {"ok": False, "error": "Desk manuel désactivé sur cette surface de dashboard."})
                return

            # Default: static files (index.html, app.js, …)
            super().do_GET()
        except Exception as exc:
            _json_response(
                self,
                500,
                {"ok": False, "success": False, "error": str(exc)},
            )

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length < 0 or length > MAX_BODY_BYTES:
                _json_response(self, 413, {"ok": False, "success": False, "error": "Charge utile trop volumineuse."})
                return
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except Exception:
                body = {}

            if path.startswith("/api/") and not _mutation_authorized(self):
                _json_response(self, 401, {
                    "ok": False,
                    "success": False,
                    "error": "Contrôle distant refusé : définissez TAFA_DASHBOARD_TOKEN.",
                })
                return

            # Browser access is restricted to safe configuration and
            # observability. Process, engine and order operations are blocked.
            if path in (
                "/api/start", "/api/bot/start", "/start", "/api/stop", "/api/bot/stop", "/stop",
                "/api/engines/select", "/api/engine/select", "/api/paper/order",
            ):
                _json_response(
                    self,
                    403,
                    {"ok": False, "success": False, "error": "Opération indisponible depuis le dashboard."},
                )
                return

            # ── Engine select (native|freqtrade|passivbot) ─────
            if path in ("/api/engines/select", "/api/engine/select"):
                _json_response(self, 501, {
                    "ok": False,
                    "success": False,
                    "error": "Sélection de moteur externe non incluse dans cette version.",
                })
                return

            # ── Config / params ────────────────────────────────
            if path in ("/api/config", "/api/settings", "/api/params", "/api/update"):
                if not isinstance(body, dict):
                    body = {}
                try:
                    from core.runtime_config import save_config
                    result = save_config(body)
                except Exception as exc:
                    _json_response(self, 500, {"ok": False, "success": False, "error": f"Configuration refusée : {exc}"})
                    return
                code = 200 if result.get("ok") else 422
                _json_response(
                    self,
                    code,
                    {
                        "ok": bool(result.get("ok")),
                        "success": bool(result.get("ok")),
                        "server": SERVER_NAME,
                        "message": "Paramètres appliqués." if result.get("ok") else "Certains paramètres ont été refusés.",
                        **result,
                    },
                )
                return

            _json_response(
                self,
                404,
                {
                    "ok": False,
                    "success": False,
                    "server": SERVER_NAME,
                    "error": f"Route introuvable : {self.path}",
                },
            )
        except Exception as exc:
            _json_response(
                self,
                500,
                {
                    "ok": False,
                    "success": False,
                    "error": str(exc),
                },
            )


def start_server(background: bool = False) -> http.server.ThreadingHTTPServer:
    """Start one local dashboard server per process."""
    global _httpd, _server_thread
    if _httpd is not None:
        return _httpd
    (ROOT_DIR / "data").mkdir(parents=True, exist_ok=True)
    server_address = (BIND_HOST, PORT)
    _httpd = http.server.ThreadingHTTPServer(server_address, DashboardHandler)
    if background:
        _server_thread = threading.Thread(target=_httpd.serve_forever, name="tafa-dashboard", daemon=True)
        _server_thread.start()
        return _httpd
    print(f"Serveur [{SERVER_NAME}] actif → http://127.0.0.1:{PORT}")
    print(f"  Desk TV   : http://127.0.0.1:{PORT}/desk")
    print(f"  Elite UI  : http://127.0.0.1:{PORT}/")
    print(f"  Health    : http://127.0.0.1:{PORT}/api/health")
    try:
        _httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur web.")
    return _httpd


def main() -> None:
    start_server(background=False)


if __name__ == "__main__":
    main()
