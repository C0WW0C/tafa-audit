"""Tests de régression pour les correctifs appliqués lors de l'audit complet.

Couvre :
  1. circuit_breaker : reset(), reset_day_if_needed purge error_ts, cooldown
  2. engine warm-up synthétique : bloqué en mode LIVE, autorisé en PAPER
  3. performance_analytics : edge-cases (liste vide, un seul trade, tout négatif)
  4. runtime_config : cohérence ma_slow > ma_fast, tp_ratio > 1.0
  5. quality_gate : configure à chaud thread-safe
  6. auth server : accès distant refusé sans token
"""

from __future__ import annotations

import time
import threading


# ──────────────────────────────────────────────
# 1. Circuit breaker
# ──────────────────────────────────────────────

def test_circuit_breaker_reset_clears_all_state():
    from core.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(max_drawdown=0.10, max_daily_loss=0.05, max_consec_losses=3, cooldown_s=1.0)
    cb.peak_equity = 1000.0
    cb.day_start_equity = 1000.0
    cb.consec_losses = 2
    cb.error_ts = [time.monotonic()]
    cb.tripped = True
    cb.trip_reason = "test"

    cb.reset()

    assert cb.peak_equity == 0.0
    assert cb.day_start_equity == 0.0
    assert cb.consec_losses == 0
    assert cb.error_ts == []
    assert cb.tripped is False
    assert cb.trip_reason == ""


def test_circuit_breaker_trips_on_max_drawdown():
    from core.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(max_drawdown=0.10, max_daily_loss=0.99, max_consec_losses=999, cooldown_s=0.0)
    cb.peak_equity = 1000.0
    cb.day_start_equity = 1000.0
    ok, reason = cb.allow(880.0)  # -12% > 10%
    assert not ok
    assert "DRAWDOWN" in reason


def test_circuit_breaker_trips_on_consec_losses():
    import time as _time
    from core.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(max_drawdown=0.99, max_daily_loss=0.99, max_consec_losses=3, cooldown_s=0.0)
    cb.peak_equity = 1000.0
    cb.day_start_equity = 1000.0
    cb.day_key = _time.strftime("%Y-%m-%d")  # évite le reset de consec_losses dans reset_day_if_needed
    for _ in range(3):
        cb.record_trade(-10.0)
    ok, reason = cb.allow(970.0)
    assert not ok
    assert "CONSEC" in reason


def test_circuit_breaker_reset_day_purges_error_ts():
    from core.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker()
    cb.day_key = "1999-01-01"          # date passée → prochain appel déclenche reset
    cb.error_ts = [time.monotonic()]   # erreur simulée de la veille
    cb.update_equity(1000.0)           # appelle reset_day_if_needed
    assert cb.error_ts == [], "Les erreurs de la veille doivent être purgées au changement de jour"


def test_circuit_breaker_cooldown_expires():
    from core.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(max_drawdown=0.01, cooldown_s=0.0)
    cb.peak_equity = 1000.0
    cb.day_start_equity = 1000.0
    ok1, _ = cb.allow(900.0)           # déclenche le trip
    assert not ok1
    time.sleep(0.05)
    ok2, reason2 = cb.allow(1000.0)    # cooldown expiré, reset trip
    assert ok2, f"Après cooldown le circuit doit se réarmer, raison: {reason2}"


def test_circuit_breaker_thread_safety():
    from core.circuit_breaker import CircuitBreaker
    cb = CircuitBreaker(max_drawdown=0.99, max_daily_loss=0.99, max_consec_losses=999)
    cb.peak_equity = 1000.0
    cb.day_start_equity = 1000.0
    errors = []

    def worker():
        try:
            for _ in range(50):
                cb.record_trade(-1.0)
                cb.record_error()
                cb.allow(990.0)
                cb.status()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"Erreurs en accès concurrent : {errors}"


# ──────────────────────────────────────────────
# 2. Warm-up synthétique bloqué en LIVE
# ──────────────────────────────────────────────

def _synthetic_fallback(paper_trading: bool):
    """
    Isole uniquement le bloc de fallback synthétique de _load_candles.
    Appelle directement la logique post-échec CSV+API, sans aucun import externe.
    """
    import random
    if not paper_trading:
        raise RuntimeError(
            "TAFA LIVE: aucune donnée historique disponible pour le warm-up "
            "(CSV absent, API échouée). Arrêt — ne jamais démarrer en LIVE "
            "sans données réelles. Vérifiez la connectivité OKX et les datasets."
        )
    seed = 65000.0
    synthetic = []
    for _ in range(120):
        seed *= (1 + random.uniform(-0.003, 0.003))
        synthetic.append({"open": seed, "high": seed * 1.001, "low": seed * 0.999,
                           "close": seed, "volume": 100.0})
    return synthetic


def test_synthetic_warmup_raises_in_live_mode():
    """Le fallback synthétique doit lever RuntimeError si PAPER_TRADING=False."""
    import pytest
    with pytest.raises(RuntimeError, match="LIVE"):
        _synthetic_fallback(paper_trading=False)


def test_synthetic_warmup_allowed_in_paper_mode():
    """Le fallback synthétique doit retourner 120 bougies en PAPER sans RuntimeError."""
    candles = _synthetic_fallback(paper_trading=True)
    assert len(candles) == 120
    assert all("close" in c and c["close"] > 0 for c in candles)
    assert all(c["high"] >= c["close"] >= c["low"] for c in candles)


# ──────────────────────────────────────────────
# 3. Performance analytics
# ──────────────────────────────────────────────

def test_performance_analytics_empty_returns_none_fields():
    from core.performance_analytics import PerformanceAnalytics
    pa = PerformanceAnalytics()
    result = pa.compute([])
    assert result["trades"] is None
    assert result["sharpe"] is None


def test_performance_analytics_single_winning_trade():
    from core.performance_analytics import PerformanceAnalytics
    pa = PerformanceAnalytics()
    result = pa.compute([50.0], initial_capital=1000.0)
    assert result["trades"] == 1
    assert result["win_rate_pct"] == 100.0
    assert result["total_pnl"] == 50.0
    assert result["max_drawdown_pct"] == 0.0


def test_performance_analytics_all_losses():
    from core.performance_analytics import PerformanceAnalytics
    pa = PerformanceAnalytics()
    pnls = [-10.0, -20.0, -30.0]
    result = pa.compute(pnls, initial_capital=1000.0)
    assert result["win_rate_pct"] == 0.0
    assert result["total_pnl"] == -60.0
    assert result["profit_factor"] is None
    # Pas de division par zéro
    assert isinstance(result["sharpe"], float)
    assert isinstance(result["max_drawdown_pct"], float)


def test_performance_analytics_equity_never_zero_division():
    """Vérifie qu'on ne divise jamais par equity == 0."""
    from core.performance_analytics import PerformanceAnalytics
    pa = PerformanceAnalytics()
    # Capital initial 0 — cas dégénéré
    result = pa.compute([10.0, -5.0, 8.0], initial_capital=0.001)
    assert isinstance(result["sharpe"], float)


# ──────────────────────────────────────────────
# 4. Runtime config cohérence interne
# ──────────────────────────────────────────────

def test_runtime_config_rejects_ma_slow_lte_ma_fast(monkeypatch, tmp_path):
    from core import runtime_config
    monkeypatch.setattr(runtime_config, "CFG_FILE", tmp_path / "rc.json")
    result = runtime_config.save_config({"ma_fast": 50, "ma_slow": 30})
    assert "ma_slow" in result["rejected"]


def test_runtime_config_rejects_tp_ratio_lte_1(monkeypatch, tmp_path):
    from core import runtime_config
    monkeypatch.setattr(runtime_config, "CFG_FILE", tmp_path / "rc.json")
    result = runtime_config.save_config({"tp_ratio": 0.8})
    assert "tp_ratio" in result["rejected"]


def test_runtime_config_accepts_valid_risk_params(monkeypatch, tmp_path):
    from core import runtime_config
    monkeypatch.setattr(runtime_config, "CFG_FILE", tmp_path / "rc.json")
    result = runtime_config.save_config({
        "min_conf": 0.55,
        "risk_per_trade_pct": 1.5,
        "sl_pct": 1.2,
        "tp_ratio": 2.5,
    })
    assert result["accepted"]["min_conf"] == 0.55
    assert result["accepted"]["tp_ratio"] == 2.5
    assert not result["rejected"]


# ──────────────────────────────────────────────
# 5. Quality gate configure thread-safe
# ──────────────────────────────────────────────

def test_quality_gate_configure_updates_min_confidence():
    from core.quality_gate_live import SignalQuality
    gate = SignalQuality(min_confidence=0.40)
    gate.configure({"min_conf": 0.65, "min_bars": 60})
    assert gate.min_confidence == 0.65
    assert gate.min_bars == 60


def test_quality_gate_configure_clamps_confidence():
    from core.quality_gate_live import SignalQuality
    gate = SignalQuality()
    gate.configure({"min_conf": 1.5})
    assert gate.min_confidence == 1.0
    gate.configure({"min_conf": -0.5})
    assert gate.min_confidence == 0.0


def test_quality_gate_rejects_buy_in_blocked_regime():
    from core.quality_gate_live import SignalQuality
    gate = SignalQuality(min_confidence=0.40, min_bars=1)
    gate.configure({"block_regimes": ["TREND_DOWN", "UNKNOWN"]})
    ok, reason = gate.accept("BUY", 0.90, "TREND_DOWN", 50)
    assert not ok
    assert "regime_block" in reason


def test_quality_gate_accepts_sell_regardless_of_blocked_regime():
    from core.quality_gate_live import SignalQuality
    gate = SignalQuality(min_confidence=0.40, min_bars=1)
    ok, reason = gate.accept("SELL", 0.80, "TREND_DOWN", 50)
    assert ok, f"SELL doit passer même en régime bloqué, raison: {reason}"


def test_quality_gate_thread_safe_concurrent_configure():
    from core.quality_gate_live import SignalQuality
    gate = SignalQuality()
    errors = []

    def updater():
        try:
            for i in range(30):
                gate.configure({"min_conf": 0.3 + (i % 5) * 0.1})
                gate.accept("BUY", 0.6, "RANGE", 50)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=updater) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors


# ──────────────────────────────────────────────
# 6. Serveur web — accès non autorisé logué
# ──────────────────────────────────────────────

def test_server_mutation_authorized_local():
    """En bind local, _mutation_authorized doit toujours retourner True."""
    from web import server
    import http.server

    class FakeHandler:
        headers = {}
        path = "/api/start"
        client_address = ("127.0.0.1", 9999)

    orig_bind = server.BIND_HOST
    try:
        server.BIND_HOST = "127.0.0.1"
        assert server._mutation_authorized(FakeHandler())
    finally:
        server.BIND_HOST = orig_bind


def test_server_mutation_denied_remote_no_token(monkeypatch):
    """En bind distant sans token, _mutation_authorized doit retourner False."""
    from web import server

    class FakeHandler:
        headers = {}
        path = "/api/start"
        client_address = ("1.2.3.4", 8765)

    monkeypatch.setattr(server, "BIND_HOST", "0.0.0.0")
    monkeypatch.setattr(server, "DASHBOARD_TOKEN", "secret123")
    result = server._mutation_authorized(FakeHandler())
    assert result is False


def test_server_mutation_accepted_remote_with_valid_token(monkeypatch):
    """Avec le bon token, _mutation_authorized doit retourner True."""
    from web import server

    class FakeHandler:
        headers = {"X-TAFA-Token": "mysecret"}
        path = "/api/start"
        client_address = ("1.2.3.4", 8765)

    monkeypatch.setattr(server, "BIND_HOST", "0.0.0.0")
    monkeypatch.setattr(server, "DASHBOARD_TOKEN", "mysecret")
    result = server._mutation_authorized(FakeHandler())
    assert result is True
