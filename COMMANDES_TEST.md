# Commandes de test — TAFA X Ultimate (VALIDATED_V2 + closed-bars)

À lancer depuis la racine du projet :

```bash
cd TAFA_X_ULTIMATE_FINAL
```

---


## 0. Elite Panel Control (recommandé)

```bash
cd TAFA_X_ULTIMATE_FINAL
streamlit run control_panel.py
# → http://127.0.0.1:8501
```

Start/Stop depuis le panel (`core/bot_process`). Bougies Plotly + config + ticket paper + blotter.

## 1. Smoke anti look-ahead (obligatoire)

```bash
python3 scripts/audit_closed_bars_smoke.py
```

Attendu : `PASS — closed-bars only, no tick pollution`

---

## 2. Compile des modules critiques

```bash
python3 -m py_compile \
  run_v10.py \
  core/engine.py \
  core/engine_v10.py \
  trading/intelligent_strategy.py \
  core/status_bridge.py \
  core/runtime_config.py \
  web/server.py \
  ai/ai_brain.py
```

---

## 3. Tests unitaires pytest (rapides)

```bash
# Smoke dashboard + parent brain
python3 -m pytest tests/test_runtime_dashboard.py tests/test_neural_parent_brain.py -q

# Paper / guards
python3 -m pytest tests/test_paper_execution_guard.py -q

# Foundation models (si endpoints non configurés → fail-closed OK)
python3 -m pytest tests/test_foundation_models.py -q

# Suite plus large (sans exchange live)
python3 -m pytest tests/ -q --ignore=tests/test_okx_demo_candle_fallback.py -x
```

---

## 4. Health check bot (sans démarrer le trading)

```bash
python3 health_v10.py
```

---

## 5. Démarrage paper (manuel)

Terminal A — bot :
```bash
python3 run_v10.py
```

Terminal B — dashboard seul (si besoin) :
```bash
python3 web/server.py
```

- **Desk TradingView + blotter** : http://127.0.0.1:8765/desk  
- UI Elite (React) : http://127.0.0.1:8765/

### Bougies OHLC (API)

```bash
# Avec serveur web démarré
curl -s "http://127.0.0.1:8765/api/candles?symbol=BTC-USDC&bar=15m&limit=50" | python3 -m json.tool | head -30

# Test helper direct
python3 - <<'PY'
from web.server import _candles_payload
p = _candles_payload("BTC-USDC", "15m", 30)
print(p["source"], p["count"], p["candles"][-1] if p["candles"] else None)
PY
```

TF desk : 5m · 15m · 1h · 4h · 1D — source OKX public, fallback CSV local.

---

## 6. Vérification manuelle closed-bars (Python)

```bash
python3 - <<'PY'
from trading.intelligent_strategy import IntelligentStrategy
s = IntelligentStrategy()
s.update_bar(100,101,99,100.5,10, confirmed=False)
assert len(s.closes) == 0, "forming pollue"
s.update_price(100.7)
assert len(s.closes) == 0, "tick pollue"
for i in range(5):
    s.update_bar(100+i,101+i,99+i,100.5+i,10, confirmed=True)
assert len(s.closes) == 5
print("OK", s.name, len(s.closes))
PY
```

---

## 7. Foundation models (optionnel, paper)

```bash
# Vérifier consensus local (nécessite model_server configuré)
python3 scripts/check_local_model_consensus.py

# Démarrer serveur de modèles local (si installé)
bash scripts/setup_local_model_server.sh   # une fois
bash scripts/start_local_model_server.sh
```

Variables utiles (dans `.env`) :
- `TAFA_FOUNDATION_MODELS_ENABLED=false`  (défaut fail-closed)
- `TAFA_KRONOS_ENDPOINT=` / `TAFA_CHRONOS_ENDPOINT=`

---

**Mode :** PAPER uniquement. Ne pas passer en live sans validation hors échantillon + frais + slippage.
