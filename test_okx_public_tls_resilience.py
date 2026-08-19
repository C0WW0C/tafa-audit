from __future__ import annotations

import requests


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_public_request_retries_transient_tls_eof_and_recovers(monkeypatch):
    from exchange.okx_client import OKXClient

    client = OKXClient()
    attempts = {"count": 0}
    waits: list[float] = []

    def flaky_get(*_args, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise requests.exceptions.SSLError("EOF occurred in violation of protocol")
        return _Response({"code": "0", "data": [{"last": "62750"}]})

    monkeypatch.setattr(client.session, "get", flaky_get)
    monkeypatch.setattr("exchange.okx_client.time.sleep", lambda delay: waits.append(delay))

    result = client._get_public("/api/v5/market/ticker", {"instId": "BTC-USDC"})

    assert result["code"] == "0"
    assert attempts["count"] == 3
    assert waits == [0.25, 0.5]


def test_market_data_falls_back_to_local_candles_after_public_failure(monkeypatch):
    from exchange.market_data import MarketData

    class FailedPublicClient:
        def get_candles(self, *_args, **_kwargs):
            return []

    monkeypatch.setattr("data.loader.default_dataset", lambda _bar: "ignored.csv")
    monkeypatch.setattr(
        "data.loader.load_csv_candles",
        lambda _path: [
            {
                "ts": 1,
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 4.0,
            }
        ],
    )

    candles = MarketData(client=FailedPublicClient()).load_candles("BTC-USDC", bar="4h", limit=10)

    assert candles[0]["close"] == 1.5
