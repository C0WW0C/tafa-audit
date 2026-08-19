from __future__ import annotations

import pytest


def test_parse_float_grid_accepts_positive_numeric_values():
    from scripts.sweep_atr_tp_multiframe import parse_float_grid

    assert parse_float_grid("1.0, 1.2,2") == (1.0, 1.2, 2.0)


def test_parse_float_grid_rejects_empty_or_non_positive_values():
    from scripts.sweep_atr_tp_multiframe import parse_float_grid

    with pytest.raises(ValueError):
        parse_float_grid("")
    with pytest.raises(ValueError):
        parse_float_grid("1.0,0")


def test_sweep_dataset_path_is_deterministic(tmp_path):
    from scripts.sweep_atr_tp_multiframe import dataset_path

    assert dataset_path(tmp_path, "BTC-USDC", "1H", 2000) == tmp_path / "okx_BTC-USDC_1H_2000.csv"
