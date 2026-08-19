from __future__ import annotations

import json


def test_manual_paper_queue_validates_claims_and_completes(monkeypatch, tmp_path):
    from core import manual_paper_orders as queue

    monkeypatch.setattr(queue, "PENDING_DIR", tmp_path / "pending")
    monkeypatch.setattr(queue, "PROCESSING_DIR", tmp_path / "processing")

    request = queue.enqueue("BTC-USDC", "BUY", 25)
    assert request["source"] == "dashboard_manual_paper"
    assert len(list(queue.PENDING_DIR.glob("*.json"))) == 1
    claimed = queue.claim()
    assert len(claimed) == 1
    assert claimed[0]["id"] == request["id"]
    queue.complete(claimed[0])
    assert not list(queue.PROCESSING_DIR.glob("*.json"))


def test_manual_paper_queue_rejects_invalid_requests():
    from core import manual_paper_orders as queue

    for invalid in (("BTCUSDC", "BUY", 25), ("BTC-USDC", "HOLD", 25), ("BTC-USDC", "BUY", 2), ("BTC-USDC", "BUY", 251)):
        try:
            queue.enqueue(*invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"request should be rejected: {invalid}")


def test_manual_paper_trade_never_uses_live_client(monkeypatch):
    from core.paper_execution_guard import PaperExecutionGuard
    from trading.paper_trading import PaperTrading
    from trading import trade_manager

    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(trade_manager, "PAPER_TRADING", True)
    monkeypatch.setattr(trade_manager, "ENABLE_LIVE", False)
    monkeypatch.setattr(trade_manager.risk_manager, "can_trade", lambda: True)
    monkeypatch.setattr(trade_manager.risk_manager, "register_position", lambda *args: None)
    monkeypatch.setattr(trade_manager.risk_manager, "update_balance", lambda *args: None)
    monkeypatch.setattr(trade_manager, "save_trade", lambda *args: None)
    monkeypatch.setattr(trade_manager, "save_performance", lambda *args: None)
    monkeypatch.setattr(trade_manager, "log_event", lambda kind, **payload: events.append((kind, payload)))

    manager = trade_manager.TradeManager(paper=PaperTrading(capital=100), client=object(), guard=PaperExecutionGuard())
    result = manager.execute_manual_paper("BTC-USDC", "BUY", 100, 25)
    assert result["ok"] is True
    assert manager.paper.position_qty("BTC-USDC") == 0.25
    assert events[-1][0] == "manual_paper_order"


def test_public_book_parser_exposes_bid_ask_and_spread():
    from exchange.websocket import OKXWebSocket

    ws = OKXWebSocket(symbol="BTC-USDC")
    ws._handle_book({"ts": "123", "bids": [["100", "2"], ["99", "1"]], "asks": [["101", "3"], ["102", "4"]]})
    book = ws.get_book()
    assert book["best_bid"] == 100.0
    assert book["best_ask"] == 101.0
    assert book["spread"] == 1.0
    assert book["bids"][0]["price"] == 100.0


def test_public_rest_book_parser_uses_no_private_credentials(monkeypatch):
    from exchange.okx_client import OKXClient

    client = OKXClient(api_key="", secret_key="", passphrase="")
    monkeypatch.setattr(
        client,
        "_get_public",
        lambda path, params: {"code": "0", "data": [{"ts": "456", "bids": [["100", "2"]], "asks": [["101", "3"]]}]},
    )
    book = client.get_order_book("BTC-USDC")
    assert book["source"] == "okx_public_rest"
    assert book["best_bid"] == 100.0
    assert book["best_ask"] == 101.0


def test_dashboard_rejects_manual_paper_order_requests(monkeypatch, tmp_path):
    import urllib.request
    from core import manual_paper_orders as queue
    from web import server

    monkeypatch.setattr(queue, "PENDING_DIR", tmp_path / "pending")
    monkeypatch.setattr(queue, "PROCESSING_DIR", tmp_path / "processing")
    monkeypatch.setattr(server, "PORT", 0)
    monkeypatch.setattr(server, "BIND_HOST", "127.0.0.1")
    server._httpd = None
    httpd = server.start_server(background=True)
    try:
        payload = json.dumps({"symbol": "BTC-USDC", "side": "BUY", "notional": 25}).encode("utf-8")
        request = urllib.request.Request(
            f"http://127.0.0.1:{httpd.server_address[1]}/api/paper/order",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(request, timeout=3)
        except urllib.error.HTTPError as error:
            assert error.code == 403
            body = json.loads(error.read().decode("utf-8"))
            assert body["ok"] is False
        else:
            raise AssertionError("le dashboard ne doit pas mettre un ordre PAPER en file")
        assert not list(queue.PENDING_DIR.glob("*.json"))
    finally:
        httpd.shutdown()
        httpd.server_close()
        server._httpd = None


def test_engine_consumes_manual_paper_request_without_exchange(monkeypatch):
    from core import engine as engine_module

    class FakeTrader:
        def execute_manual_paper(self, symbol, side, price, notional):
            return {"ok": True, "reason": "filled", "qty": notional / price, "notional": notional, "price": price}

    import threading
    engine = engine_module.TAFAEngine.__new__(engine_module.TAFAEngine)
    engine._lock = threading.RLock()   # ✅ FIX: requis par _process_manual_paper_orders
    engine.symbol = "BTC-USDC"
    engine.trader = FakeTrader()
    engine.manual_order_tape = []
    engine._refresh_market_book = lambda: {"best_bid": 99.0, "best_ask": 101.0}
    request = {"id": "queued", "symbol": "BTC-USDC", "side": "BUY", "notional": 25, "created_at": 1.0}
    completed: list[dict] = []
    monkeypatch.setattr(engine_module, "claim_manual_paper_orders", lambda limit: [request])
    monkeypatch.setattr(engine_module, "complete_manual_paper_order", lambda item: completed.append(item))

    engine._process_manual_paper_orders(100.0)
    assert engine.manual_order_tape[-1]["ok"] is True
    assert engine.manual_order_tape[-1]["price"] == 101.0
    assert completed == [request]
