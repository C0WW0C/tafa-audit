from ai.foundation_models import FoundationModelConsensus, HttpForecastClient


class Strategy:
    opens = [100.0 + i for i in range(80)]
    highs = [101.0 + i for i in range(80)]
    lows = [99.0 + i for i in range(80)]
    closes = [100.5 + i for i in range(80)]
    volumes = [1_000.0 + i for i in range(80)]


def client(model: str, response: dict) -> HttpForecastClient:
    def transport(endpoint, payload, timeout_s):
        assert endpoint == "http://model.local/predict"
        assert payload["model"] == model
        assert len(payload["candles"]) == 80
        return response

    return HttpForecastClient(model, "UNUSED", endpoint="http://model.local/predict", transport=transport)


def test_consensus_accepts_only_when_both_models_match_strategy():
    gate = FoundationModelConsensus(
        enabled=True,
        paper_only=True,
        min_confidence=0.70,
        kronos=client("NeoQuasar/Kronos-base", {"signal": "BUY", "confidence": 0.80}),
        chronos=client("amazon/chronos-2", {"signal": "BUY", "confidence": 0.75}),
    )

    decision = gate.evaluate(symbol="BTC-USDC", timeframe="4h", strategy=Strategy(), candidate_signal="BUY")

    assert decision.accepted is True
    assert decision.signal == "BUY"
    assert decision.confidence == 0.75


def test_consensus_blocks_when_models_disagree():
    gate = FoundationModelConsensus(
        enabled=True,
        paper_only=True,
        kronos=client("NeoQuasar/Kronos-base", {"signal": "BUY", "confidence": 0.95}),
        chronos=client("amazon/chronos-2", {"signal": "SELL", "confidence": 0.95}),
    )

    decision = gate.evaluate(symbol="BTC-USDC", timeframe="4h", strategy=Strategy(), candidate_signal="BUY")

    assert decision.accepted is False
    assert decision.signal == "HOLD"
    assert decision.state == "blocked"


def test_consensus_is_blocked_outside_paper_mode():
    gate = FoundationModelConsensus(enabled=True, paper_only=False)

    decision = gate.evaluate(symbol="BTC-USDC", timeframe="4h", strategy=Strategy(), candidate_signal="BUY")

    assert decision.signal == "HOLD"
    assert decision.state == "paper_only_blocked"


def test_client_resolves_endpoint_loaded_after_initialization(monkeypatch):
    seen = {}

    def transport(endpoint, payload, timeout_s):
        seen["endpoint"] = endpoint
        return {"signal": "BUY", "confidence": 0.8}

    monkeypatch.delenv("TAFA_TEST_LATE_ENDPOINT", raising=False)
    late_client = HttpForecastClient("test-model", "TAFA_TEST_LATE_ENDPOINT", transport=transport)
    monkeypatch.setenv("TAFA_TEST_LATE_ENDPOINT", "http://127.0.0.1:8787/test")

    vote = late_client.forecast(symbol="BTC-USDC", timeframe="4h", candles=[{"close": 1.0}], timeout_s=1)

    assert vote.state == "ready"
    assert seen["endpoint"] == "http://127.0.0.1:8787/test"
