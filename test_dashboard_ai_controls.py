from __future__ import annotations


def test_runtime_config_accepts_bounded_expert_controls():
    from core import runtime_config

    accepted, rejected = runtime_config._normalize_payload(
        {
            "learner_eta": 0.12,
            "expert_tsmom_enabled": True,
            "expert_tsmom_weight": 0.70,
            "expert_ema_cross_enabled": False,
            "expert_ema_cross_weight": 0.25,
        }
    )

    assert not rejected
    assert accepted["learner_eta"] == 0.12
    assert accepted["expert_tsmom_weight"] == 0.70
    assert accepted["expert_ema_cross_enabled"] is False


def test_strategy_applies_expert_controls_and_publishes_runtime_state():
    from trading.intelligent_strategy import IntelligentStrategy

    strategy = IntelligentStrategy()
    strategy.apply_config(
        {
            "ai_on": True,
            "learner_eta": 0.12,
            "expert_tsmom_enabled": True,
            "expert_tsmom_weight": 0.80,
            "expert_ema_cross_enabled": False,
            "expert_ema_cross_weight": 0.20,
        }
    )

    state = strategy.get_state()

    assert state["learner_eta"] == 0.12
    assert state["expert_components"]["tsmom"]["enabled"] is True
    assert state["expert_components"]["ema_cross"]["enabled"] is False
    assert state["weights"]["ema_cross"] == 0.0

    strategy.learner.weights["tsmom"] = 0.42
    strategy.apply_config(
        {
            "ai_on": True,
            "learner_eta": 0.12,
            "expert_tsmom_enabled": True,
            "expert_tsmom_weight": 0.80,
            "expert_ema_cross_enabled": False,
            "expert_ema_cross_weight": 0.20,
        }
    )
    assert strategy.learner.weights["tsmom"] == 0.42


def test_strategy_keeps_a_tsmom_component_when_all_experts_are_disabled():
    from trading.intelligent_strategy import IntelligentStrategy

    strategy = IntelligentStrategy()
    strategy.apply_config(
        {
            f"expert_{name}_enabled": False
            for name in ("tsmom", "ema_cross", "rsi_filter", "momentum", "volume")
        }
    )

    assert strategy.get_state()["expert_components"]["tsmom"]["enabled"] is True


def test_parent_brain_applies_bounded_weights_without_reapplying_unchanged_config():
    from ai.neural_parent_brain import NeuralParentBrain

    brain = NeuralParentBrain()
    cfg = {
        "parent_brain_eta": 0.04,
        "parent_weight_base_signal": 0.50,
        "parent_weight_regime": 0.20,
        "parent_weight_expert_agreement": 0.15,
        "parent_weight_momentum": 0.10,
        "parent_weight_volatility": 0.05,
    }
    brain.apply_config(cfg)
    initial = brain.status()

    assert initial["eta"] == 0.04
    assert round(sum(initial["weights"].values()), 3) == 1.0

    brain._weights["base_signal"] = 0.44
    brain.apply_config(cfg)
    assert brain._weights["base_signal"] == 0.44


def test_equity_endpoint_uses_persisted_points_in_chronological_order(monkeypatch):
    from web import server

    monkeypatch.setattr(
        server,
        "_query_table",
        lambda _table, _limit: [
            {"id": 3, "timestamp": "2026-08-14T12:03:00", "equity": 510.0, "balance": 500.0, "pnl": 10.0, "drawdown": 1.0},
            {"id": 2, "timestamp": "2026-08-14T12:02:00", "equity": 505.0, "balance": 500.0, "pnl": 5.0, "drawdown": 0.0},
        ],
    )

    payload = server._equity_payload(limit=20)

    assert payload["source"] == "sqlite_performance"
    assert [point["equity"] for point in payload["points"]] == [505.0, 510.0]


def test_dashboard_declares_public_okx_chart_and_has_no_execution_controls():
    from web import server

    html = (server.WEB_DIR / "index.html").read_text(encoding="utf-8")

    assert "/api/equity" in html
    assert "/api/candles" in html
    assert "wss://ws.okx.com:8443/ws/v5/public" in html
    assert "place_order" not in html
    assert "ENABLE_LIVE" not in html
