from __future__ import annotations


def test_split_values_requires_nonempty_inputs():
    from scripts.run_multidataset_walkforward import split_values

    assert split_values("BTC-USDC, ETH-USDC") == ("BTC-USDC", "ETH-USDC")
    try:
        split_values("")
    except ValueError:
        pass
    else:
        raise AssertionError("an empty selection must fail")
