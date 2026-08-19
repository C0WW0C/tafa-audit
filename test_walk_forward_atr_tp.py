from __future__ import annotations

import pytest


def test_chronological_split_preserves_order_and_has_no_overlap():
    from scripts.walk_forward_atr_tp import chronological_split

    candles = [{"ts": str(index)} for index in range(500)]
    train, test = chronological_split(candles, 0.6)
    assert len(train) == 300
    assert len(test) == 200
    assert train[-1]["ts"] == "299"
    assert test[0]["ts"] == "300"


def test_chronological_split_rejects_invalid_ratio_or_small_windows():
    from scripts.walk_forward_atr_tp import chronological_split

    with pytest.raises(ValueError):
        chronological_split([{}] * 500, 0.4)
    with pytest.raises(ValueError):
        chronological_split([{}] * 300, 0.6)


def test_rank_train_requires_positive_train_evidence():
    from scripts.walk_forward_atr_tp import rank_train

    rows = [
        {"train": {"trades": 10, "net_pnl_usdc": -0.1, "profit_factor": 1.5, "max_drawdown_pct": 0.1}},
        {"train": {"trades": 10, "net_pnl_usdc": 0.1, "profit_factor": 1.1, "max_drawdown_pct": 0.2}},
    ]
    ranked = rank_train(rows, min_trades=8, min_profit_factor=1.0)
    assert ranked[0]["train_eligible"] is True
    assert ranked[1]["train_eligible"] is False
