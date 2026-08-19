import json
import threading
import urllib.error
import urllib.request

from model_server.server import ModelUnavailable, create_server


class Runtime:
    def health(self):
        return {"ok": True, "models": {"kronos": "fake", "chronos": "fake"}}

    def predict_kronos(self, symbol, timeframe, candles):
        return type("Result", (), {"public": lambda self: {"model": "kronos", "signal": "BUY", "confidence": 0.8}})()

    def predict_chronos(self, symbol, timeframe, candles):
        return type("Result", (), {"public": lambda self: {"model": "chronos", "signal": "BUY", "confidence": 0.8}})()


def candles():
    return [{"open": 100 + i, "high": 101 + i, "low": 99 + i, "close": 100.5 + i, "volume": 1000 + i} for i in range(60)]


def request(url, method="GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_local_server_exposes_health_and_two_forecast_routes():
    httpd = create_server(host="127.0.0.1", port=0, runtime=Runtime())
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    root = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        status, health = request(root + "/health")
        assert status == 200
        assert health["ok"] is True
        for path in ("/kronos/predict", "/chronos/predict"):
            status, payload = request(root + path, method="POST", body={"symbol": "BTC-USDC", "timeframe": "4h", "candles": candles()})
            assert status == 200
            assert payload["signal"] == "BUY"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_local_server_rejects_incomplete_ohlcv_payload():
    httpd = create_server(host="127.0.0.1", port=0, runtime=Runtime())
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    root = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        try:
            request(root + "/kronos/predict", method="POST", body={"symbol": "BTC-USDC", "timeframe": "4h", "candles": candles()[:10]})
        except urllib.error.HTTPError as error:
            assert error.code == 400
        else:
            raise AssertionError("une requête courte doit être refusée")
    finally:
        httpd.shutdown()
        httpd.server_close()
