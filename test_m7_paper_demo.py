from __future__ import annotations


def test_paper_demo_launcher_forces_safe_environment(monkeypatch):
    import run_paper_demo

    monkeypatch.setenv("TAFA_MODE", "LIVE")
    monkeypatch.setenv("ENABLE_LIVE", "true")
    monkeypatch.setenv("LIVE_CONFIRM", "I_UNDERSTAND_THE_RISK")
    applied = run_paper_demo.configure_paper_demo()

    assert applied["TAFA_MODE"] == "DEMO"
    assert applied["ENABLE_LIVE"] == "false"
    assert applied["LIVE_CONFIRM"] == ""


def test_dashboard_start_path_prefers_paper_demo_launcher():
    from web import server

    assert server.RUN_SCRIPT.name in {"run_paper_demo.py", "run_elite_final_paper.py"}
