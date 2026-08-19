from __future__ import annotations

import pytest


def test_multiframe_profile_defaults_to_target_and_net_session_goal():
    from backtesting.multiframe import MultiTimeframeConfig

    profile = MultiTimeframeConfig()
    assert profile.target_tp_pct == 1.8
    assert profile.net_target_usd == 5.0


def test_multiframe_profile_rejects_non_positive_net_target():
    from backtesting.multiframe import MultiTimeframeConfig

    with pytest.raises(ValueError, match="net_target_usd"):
        MultiTimeframeConfig(net_target_usd=0)


def test_elite_launcher_sets_target_profile(monkeypatch):
    import run_elite_final_paper

    monkeypatch.setenv("TAFA_TARGET_TP_PERCENT", "99")
    applied = run_elite_final_paper.configure_elite_final_paper()
    assert applied["TAFA_TARGET_TP_PERCENT"] == "1.8"
    assert applied["TAFA_PAPER_SESSION_NET_TARGET_USD"] == "5"
