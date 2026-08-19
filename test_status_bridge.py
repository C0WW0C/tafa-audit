# tests/test_status_bridge.py
import time
from core.status_bridge import publish, read, get, is_stale, reset

def test_publish_read():
    reset()
    publish({"running": True, "last_price": 68000})
    data = read()
    assert data["running"] is True
    assert data["last_price"] == 68000

def test_merge():
    reset()
    publish({"paper": {"balance": 1000}}, merge=False)
    publish({"paper": {"pnl": 50}}, merge=True)
    data = read()
    assert data["paper"]["balance"] == 1000
    assert data["paper"]["pnl"] == 50

def test_stale():
    reset()
    assert is_stale(max_age=0.1) is True
    publish({"last_price": 68000})
    time.sleep(0.2)
    assert is_stale(max_age=0.1) is True
    assert is_stale(max_age=5.0) is False