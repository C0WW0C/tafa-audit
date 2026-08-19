from __future__ import annotations


def test_coingecko_is_used_after_okx_and_before_binance(monkeypatch):
    from exchange.market_data import MarketData

    class NoOkxQuote:
        def get_ticker(self, _symbol):
            return None

    market = MarketData(client=NoOkxQuote())
    now = 1_700_000_000.0
    monkeypatch.setattr("exchange.market_data.time.time", lambda: now)
    monkeypatch.setattr(
        market,
        "_http_json",
        lambda _url: {"bitcoin": {"usd": 62_750.0, "last_updated_at": now}},
    )
    monkeypatch.setattr(market, "_binance_price", lambda _symbol: (_ for _ in ()).throw(AssertionError("Binance must not run")))

    assert market.get_price("BTC-USDC") == 62_750.0
    assert market.source() == "coingecko_usd_proxy"
    assert market.quote_status()["quote_currency"] == "USD"


def test_stale_coingecko_quote_is_rejected_before_binance_fallback(monkeypatch):
    from exchange.market_data import MarketData

    class NoOkxQuote:
        def get_ticker(self, _symbol):
            return None

    market = MarketData(client=NoOkxQuote())
    now = 1_700_000_000.0
    monkeypatch.setattr("exchange.market_data.time.time", lambda: now)
    monkeypatch.setattr(
        market,
        "_http_json",
        lambda _url: {"bitcoin": {"usd": 62_000.0, "last_updated_at": now - 121}},
    )
    monkeypatch.setattr(market, "_binance_price", lambda _symbol: 62_500.0)

    assert market.get_price("BTC-USDC") == 62_500.0
    assert market.source() == "binance"
