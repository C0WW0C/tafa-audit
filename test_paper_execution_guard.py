from __future__ import annotations


def test_duplicate_buy_is_blocked_but_sell_keeps_exit_priority():
    from core.paper_execution_guard import PaperExecutionGuard

    now = [100.0]
    guard = PaperExecutionGuard(duplicate_buy_window_seconds=15, clock=lambda: now[0])

    assert guard.check_entry("btc-usdc", "BUY").allowed is True
    guard.record_trade("BTC-USDC", "BUY")
    assert guard.check_entry("BTC-USDC", "BUY").reason == "duplicate_buy_cooldown"
    assert guard.check_entry("BTC-USDC", "SELL").reason == "sell_exit_priority"

    now[0] += 15.0
    assert guard.check_entry("BTC-USDC", "BUY").allowed is True


def test_cancel_budget_is_bounded_per_symbol_and_recovers_after_window():
    from core.paper_execution_guard import PaperExecutionGuard

    now = [50.0]
    guard = PaperExecutionGuard(cancel_window_seconds=30, max_cancels_per_symbol=2, clock=lambda: now[0])

    assert guard.request_cancel("SOL-USDC").allowed is True
    assert guard.request_cancel("SOL-USDC").allowed is True
    assert guard.request_cancel("SOL-USDC").reason == "cancel_budget_exhausted"
    assert guard.status()["blocked_cancels"] == 1

    now[0] += 30.0
    assert guard.request_cancel("SOL-USDC").allowed is True


def test_trade_manager_journals_a_blocked_duplicate_paper_buy(monkeypatch):
    from core.paper_execution_guard import PaperExecutionGuard
    from trading.paper_trading import PaperTrading
    from trading import trade_manager

    now = [10.0]
    events: list[tuple[str, dict]] = []
    monkeypatch.setattr(trade_manager, "PAPER_TRADING", True)
    monkeypatch.setattr(trade_manager, "ENABLE_LIVE", False)
    monkeypatch.setattr(trade_manager.risk_manager, "can_trade", lambda: True)
    monkeypatch.setattr(trade_manager.risk_manager, "calculate_position_size", lambda price: 1.0)
    monkeypatch.setattr(trade_manager.risk_manager, "register_position", lambda *args: None)
    monkeypatch.setattr(trade_manager.risk_manager, "update_balance", lambda *args: None)
    monkeypatch.setattr(trade_manager, "save_trade", lambda *args: None)
    monkeypatch.setattr(trade_manager, "save_performance", lambda *args: None)
    monkeypatch.setattr(trade_manager, "log_event", lambda kind, **payload: events.append((kind, payload)))

    manager = trade_manager.TradeManager(
        paper=PaperTrading(capital=500),
        guard=PaperExecutionGuard(duplicate_buy_window_seconds=15, clock=lambda: now[0]),
    )
    assert manager.execute("BTC-USDC", "BUY", 100) is True
    assert manager.execute("BTC-USDC", "BUY", 100) is False
    assert events[-1][0] == "paper_guard_block"
    assert events[-1][1]["reason"] == "duplicate_buy_cooldown"
