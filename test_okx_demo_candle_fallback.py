import json

from exchange.websocket import OKXWebSocket


class Socket:
    def __init__(self):
        self.messages = []

    def send(self, message):
        self.messages.append(json.loads(message))


def test_demo_uses_tick_candle_fallback_without_unsupported_subscription(monkeypatch):
    monkeypatch.delenv("TAFA_DEMO_CANDLE_SUBSCRIBE", raising=False)
    stream = OKXWebSocket(symbol="BTC-USDC", timeframe="4H", demo=True)
    stream._should_run = True
    socket = Socket()

    stream._on_open(socket)

    channels = [arg["channel"] for message in socket.messages for arg in message["args"]]
    assert channels == ["tickers", "books5"]


def test_live_keeps_candle_subscription_enabled():
    stream = OKXWebSocket(symbol="BTC-USDC", timeframe="4H", demo=False)
    stream._should_run = True
    socket = Socket()

    stream._on_open(socket)

    channels = [arg["channel"] for message in socket.messages for arg in message["args"]]
    assert "candle4H" in channels
