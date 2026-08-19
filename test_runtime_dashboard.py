"""Regression coverage for the dashboard-to-engine control boundary."""

from __future__ import annotations

import json
import re
import urllib.request


def test_runtime_config_rejects_unsupported_and_out_of_range_values(monkeypatch, tmp_path):
    from core import runtime_config

    config_file = tmp_path / "runtime.json"
    monkeypatch.setattr(runtime_config, "CFG_FILE", config_file)

    result = runtime_config.save_config(
        {
            "min_conf": 0.70,
            "confirm_bars": 4,
            "watchlist": "BTC-USDC,ETH-USDC",
            "risk_per_trade_pct": 20,
        }
    )

    assert result["ok"] is False
    assert result["accepted"]["min_conf"] == 0.70
    assert result["accepted"]["confirm_bars"] == 4
    assert "watchlist" in result["rejected"]
    assert "risk_per_trade_pct" in result["rejected"]
    stored = json.loads(config_file.read_text(encoding="utf-8"))
    assert stored == {"min_conf": 0.70, "confirm_bars": 4}


def test_status_stream_returns_first_event(monkeypatch):
    from web import server

    monkeypatch.setattr(server, "PORT", 0)
    monkeypatch.setattr(server, "BIND_HOST", "127.0.0.1")
    server._httpd = None
    httpd = server.start_server(background=True)
    port = httpd.server_address[1]
    response = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stream", timeout=3)
    try:
        first_line = response.readline().decode("utf-8")
        second_line = response.readline().decode("utf-8")
        assert first_line == "event: status\n"
        assert second_line.startswith("data: {")
    finally:
        response.close()
        httpd.shutdown()
        httpd.server_close()
        server._httpd = None


def test_status_publish_retries_a_transient_windows_file_lock(monkeypatch, tmp_path):
    from core import status_bridge

    status_file = tmp_path / "live_status.json"
    monkeypatch.setattr(status_bridge, "STATUS_FILE", status_file)
    monkeypatch.setattr(status_bridge, "_status", {"running": False, "updated_at": None})
    monkeypatch.setattr(status_bridge.time, "sleep", lambda _delay: None)

    real_replace = status_bridge.os.replace
    attempts = {"count": 0}

    def replace_after_temporary_lock(source, destination):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError(5, "Access is denied", str(destination))
        return real_replace(source, destination)

    monkeypatch.setattr(status_bridge.os, "replace", replace_after_temporary_lock)

    status_bridge.publish({"running": True, "mode": "PAPER", "cycle": 7})

    assert attempts["count"] == 3
    assert json.loads(status_file.read_text(encoding="utf-8"))["cycle"] == 7
    assert list(tmp_path.glob("*.tmp")) == []


def test_dashboard_static_fallbacks_avoid_browser_404s(monkeypatch):
    from web import server

    monkeypatch.setattr(server, "PORT", 0)
    monkeypatch.setattr(server, "BIND_HOST", "127.0.0.1")
    server._httpd = None
    httpd = server.start_server(background=True)
    port = httpd.server_address[1]
    try:
        favicon = urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico", timeout=3)
        collector = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/__manus__/debug-collector.js", timeout=3
        )
        assert favicon.status == 200
        assert favicon.headers["Content-Type"].startswith("image/svg+xml")
        assert collector.status == 200
        assert b"no-op" in collector.read()
    finally:
        httpd.shutdown()
        httpd.server_close()
        server._httpd = None


def test_status_payload_uses_websocket_book_when_market_adapter_is_empty(monkeypatch):
    from web import server

    bridge_status = {
        "market": {"book": {"bids": [], "asks": [], "source": "none"}},
        "ws": {
            "book": {
                "bids": [{"price": 100.0, "size": 1.0}],
                "asks": [{"price": 101.0, "size": 1.0}],
                "best_bid": 100.0,
                "best_ask": 101.0,
            }
        },
    }
    monkeypatch.setattr(server, "_bot_running", lambda: True)
    monkeypatch.setattr(server.status_bridge, "read", lambda: bridge_status)

    payload = server._status_payload()

    assert payload["market"]["source"] == "okx-websocket"
    assert payload["market"]["book"]["best_bid"] == 100.0


def test_dashboard_serves_static_control_panel_and_tab_read_routes(monkeypatch):
    from web import server

    monkeypatch.setattr(server, "PORT", 0)
    monkeypatch.setattr(server, "BIND_HOST", "127.0.0.1")
    server._httpd = None
    httpd = server.start_server(background=True)
    port = httpd.server_address[1]
    root = f"http://127.0.0.1:{port}"
    try:
        html = urllib.request.urlopen(root + "/", timeout=3).read().decode("utf-8")
        assert "Neural AI · Trading Dashboard · TAFA" in html
        assert '<script src="vendor/chart.umd.min.js"></script>' in html
        chart_asset = urllib.request.urlopen(root + "/vendor/chart.umd.min.js", timeout=3)
        assert chart_asset.status == 200
        for path in ("/api/status", "/api/config", "/api/health", "/api/performance/summary", "/api/market/book", "/api/manual-orders", "/api/models/status"):
            response = urllib.request.urlopen(root + path, timeout=3)
            assert response.status == 200
            assert isinstance(json.loads(response.read().decode("utf-8")), dict)

        models_page = urllib.request.urlopen(root + "/foundation_models.html", timeout=3)
        page_body = models_page.read().decode("utf-8")
        assert models_page.status == 200
        assert "Consensus Kronos + Chronos" in page_body
    finally:
        httpd.shutdown()
        httpd.server_close()
        server._httpd = None


def test_local_dashboard_static_assets_have_no_webdev_storage_dependencies():
    from web import server

    html = (server.WEB_DIR / "index.html").read_text(encoding="utf-8")
    asset = (server.WEB_DIR / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8")
    assert "/manus-storage/" not in html
    assert "/manus-storage/" not in asset
