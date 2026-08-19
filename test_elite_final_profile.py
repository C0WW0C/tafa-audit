from __future__ import annotations

import pytest


def test_elite_final_launcher_forces_paper_capital(monkeypatch):
    import run_elite_final_paper

    monkeypatch.setenv("TAFA_MODE", "LIVE")
    monkeypatch.setenv("ENABLE_LIVE", "true")
    monkeypatch.setenv("TAFA_PAPER_CAPITAL", "99999")
    applied = run_elite_final_paper.configure_elite_final_paper()

    assert applied["TAFA_MODE"] == "DEMO"
    assert applied["ENABLE_LIVE"] == "false"
    assert applied["TAFA_PAPER_CAPITAL"] == "500"


def test_multiframe_config_requires_usable_window():
    from backtesting.multiframe import MultiTimeframeConfig

    with pytest.raises(ValueError, match="at least 200"):
        MultiTimeframeConfig(bars=199)


def test_dashboard_prefers_elite_paper_launcher():
    from web import server

    assert server.RUN_SCRIPT.name == "run_elite_final_paper.py"
