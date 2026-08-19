from ai.neural_parent_brain import NeuralParentBrain


class Strategy:
    name = "TAFA_INTEL_V6"
    last_regime = "TREND_UP"
    last_confidence = 0.9
    last_atr = 100.0
    closes = [10000.0 + i * 10 for i in range(20)]
    last_experts = {"ema_cross": "BUY", "rsi_filter": "BUY", "momentum": "BUY", "volume": "BUY"}


def test_parent_accepts_strong_trend_signal():
    d = NeuralParentBrain().decide(Strategy(), "BUY", 10200.0)
    assert d.signal == "BUY"
    assert d.confidence >= 0.62


def test_parent_vetoes_downtrend_buy():
    s = Strategy()
    s.last_regime = "TREND_DOWN"
    d = NeuralParentBrain().decide(s, "BUY", 10200.0)
    assert d.signal == "HOLD"
    assert "regime_veto" in d.reason


def test_parent_never_bypasses_risk():
    d = NeuralParentBrain().decide(Strategy(), "BUY", 10200.0, risk_ok=False)
    assert d.signal == "HOLD"
