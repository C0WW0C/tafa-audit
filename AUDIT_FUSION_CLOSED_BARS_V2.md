# Audit fusion — VALIDATED_V2 + closed-bars (2026-08-13)

**Base :** `TAFA_X_ULTIMATE_VALIDATED_V2`  
**Correctif appliqué :** anti look-ahead (closed-bars only)  
**Mode :** PAPER / DEMO uniquement

---

## Ordre exécuté

1. Base = VALIDATED_V2 (foundation models, tests, notes validation)
2. Patch closed-bars sur stratégie + engine + ai_brain + backtest + status_bridge
3. `py_compile` + test unitaire forming/tick
4. pytest smoke (`test_runtime_dashboard`, `test_neural_parent_brain`) → OK

---

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `trading/intelligent_strategy.py` | V7_CLOSED ; `update_bar(..., confirmed=)` ; `_forming` ; `update_price` = last_price only |
| `core/engine.py` | Warm-up closed ; `_on_ws_candle` filtre `confirm==1` ; ticks → `update_price` |
| `ai/ai_brain.py` | Propagation `confirmed` |
| `backtesting/historical.py` | `confirmed=True` sur historique |
| `core/status_bridge.py` | Warning log au lieu de `except: pass` |

---

## Vérification unitaire

```
name: TAFA_INTEL_V7_CLOSED
after forming → len(closes)=0
after tick    → len(closes)=0
after 5 closed → len(closes)=5
CLOSED-BARS FIX OK
```

---

## Architecture résultante

```
run_v10.py
  → web/server.py (SSE)
  → status_bridge
  → TAFAEngineV10
        ├─ circuit_breaker / quality_gate
        ├─ foundation models (Kronos + Chronos, paper, fail-closed)  ← V2
        ├─ TAFAEngine (OKX WS + paper)
        └─ IntelligentStrategy V7_CLOSED  ← patch
```

---

## Règles non négociables maintenant actives

1. Seules les barres `confirm==1` (ou historiques) alimentent les indicateurs.
2. Les ticks ne créent jamais d’OHLC.
3. La bougie en formation est isolée dans `_forming`.
4. Foundation models restent optionnels et fail-closed (paper).

---

## Commandes de test (détail : COMMANDES_TEST.md)

```bash
cd TAFA_X_ULTIMATE_FINAL

# 1) Smoke anti look-ahead (obligatoire)
python3 scripts/audit_closed_bars_smoke.py

# 2) Compile critique
python3 -m py_compile run_v10.py core/engine.py core/engine_v10.py \
  trading/intelligent_strategy.py core/status_bridge.py web/server.py

# 3) Pytest smoke
python3 -m pytest tests/test_runtime_dashboard.py tests/test_neural_parent_brain.py -q

# 4) Health
python3 health_v10.py
```

---

## Points restants

- Tests d’intégration cycle WS mock + paper fill
- Interdire warm-up synthétique en mode non-dev
- Stop process group (`killpg`) plus robuste
- Métriques slippage / frais

**Rester en PAPER.** Aucune garantie de performance.
