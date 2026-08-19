# ============================================================
# TAFA V8 — MODULAR DASHBOARD SERVER
# ✅ Refactored: routes, payloads, handlers separated
# ============================================================

from __future__ import annotations

import http.server
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("TAFA_V8_Dashboard")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Configuration
WEB_DIR = Path(__file__).resolve().parent
ROOT_DIR = WEB_DIR.parent
PORT = 8765
BIND_HOST = os.getenv("TAFA_DASHBOARD_HOST", "127.0.0.1")
MAX_BODY_BYTES = 65_536


class PayloadBuilder:
    """Generate API responses."""
    
    @staticmethod
    def status() -> Dict[str, Any]:
        """Bot status payload."""
        return {
            "ok": True,
            "timestamp": time.time(),
            "running": True,
            "symbol": "BTC-USDC",
            "mode": "PAPER",
            "version": "TAFA_V8_PRODUCTION",
        }
    
    @staticmethod
    def health() -> Dict[str, Any]:
        """Health check payload."""
        return {
            "ok": True,
            "server": "tafa_v8",
            "bot_running": True,
            "uptime_s": 0,
            "ts": time.time(),
        }
    
    @staticmethod
    def error(msg: str, code: int = -1) -> Dict[str, Any]:
        """Error payload."""
        return {"ok": False, "code": code, "error": msg}


class RouteHandler:
    """Route API endpoints to handlers."""
    
    def __init__(self, bot=None):
        self.bot = bot
    
    def route(self, path: str, method: str = "GET") -> tuple[Optional[Dict], int]:
        """Route to handler. Returns (payload, status_code)."""
        path = path.rstrip("/") or "/"
        
        # Status endpoints
        if path in ("/api/status", "/api/bot/status", "/api/data"):
            return PayloadBuilder.status(), 200
        
        # Health endpoint
        if path == "/api/health":
            return PayloadBuilder.health(), 200
        
        # 404
        return PayloadBuilder.error(f"Not found: {path}", -1), 404


class DashboardV8(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for dashboard."""
    
    route_handler: RouteHandler = None  # Set by server
    
    def log_message(self, fmt: str, *args) -> None:
        """Quieter logs."""
        pass  # Suppress default logging
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            payload, status = self.route_handler.route(path, "GET")
            self._json_response(status, payload)
        except Exception as e:
            logger.error(f"GET error: {e}")
            self._json_response(500, PayloadBuilder.error(str(e)))
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length > MAX_BODY_BYTES:
                self._json_response(413, PayloadBuilder.error("Payload too large"))
                return
            
            body_data = self.rfile.read(length) if length > 0 else b"{}"
            body = json.loads(body_data.decode("utf-8")) if body_data else {}
            
            # Route POST
            payload, status = self.route_handler.route(path, "POST")
            self._json_response(status, payload)
        
        except Exception as e:
            logger.error(f"POST error: {e}")
            self._json_response(500, PayloadBuilder.error(str(e)))
    
    def _json_response(self, code: int, payload: dict):
        """Send JSON response."""
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def start_dashboard(port: int = PORT, bind_host: str = BIND_HOST):
    """Start dashboard server."""
    DashboardV8.route_handler = RouteHandler()
    
    server = http.server.ThreadingHTTPServer(
        (bind_host, port),
        DashboardV8,
    )
    
    thread = threading.Thread(
        target=server.serve_forever,
        name="tafa-v8-dashboard",
        daemon=True,
    )
    thread.start()
    
    logger.info(f"Dashboard started: http://{bind_host}:{port}/api/health")
    return server


if __name__ == "__main__":
    server = start_dashboard()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
