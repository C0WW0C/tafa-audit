# tests/test_manual_paper_orders.py
import time
from pathlib import Path
from core.manual_paper_orders import enqueue, claim, complete, clear_all

def test_full_flow():
    clear_all()
    # 1. Enqueue
    req = enqueue("BTC-USDC", "BUY", 100.0)
    assert "id" in req

    # 2. Claim
    claimed = claim(limit=1)
    assert len(claimed) == 1
    assert claimed[0]["symbol"] == "BTC-USDC"
    assert claimed[0]["notional"] == 100.0

    # 3. Complete
    complete(claimed[0])
    pending_count = len(list(Path("data/manual_paper_orders/pending").glob("*.json")))
    processing_count = len(list(Path("data/manual_paper_orders/processing").glob("*.json")))
    assert pending_count == 0
    assert processing_count == 0

def test_invalid_notional():
    try:
        enqueue("BTC-USDC", "BUY", 999.0)  # > max
        assert False
    except ValueError as e:
        assert "maximum" in str(e).lower()