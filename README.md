# TAFA X Ultimate — V10 paper (Elite Panel Control)

**Mode par défaut : PAPER / DEMO.**

Architecture officielle :

```
Streamlit control_panel.py
  → core/bot_process (start/stop/pid)
  → run_v10.py ↔ status_bridge
  → TAFAEngineV10 → IntelligentStrategy V7_CLOSED + Paper + OKX
```


## Launcher simple (bot + dashboard séparés)

```bash
python3 launch_tafa.py              # bot + Elite Panel Streamlit
python3 launch_tafa.py --panel --web  # bot + panel + desk web
python3 launch_tafa.py --bot-only
```

- **Processus séparés** (`subprocess` + `start_new_session`), pas le même thread
- Bot : `TAFA_DASHBOARD_EXTERNAL=true` (ne démarre pas le web en interne)
- Panel : http://127.0.0.1:8501
- Desk  : http://127.0.0.1:8765/desk
- Ctrl+C arrête tout

## Lancer (recommandé)

```bash
cd TAFA_X_ULTIMATE_FINAL
pip install -r requirements.txt

# Terminal A — bot (optionnel si Start depuis le panel)
python3 run_v10.py

# Terminal B — Elite Panel Control
streamlit run control_panel.py
```

→ Panel : http://127.0.0.1:8501

### Elite Panel Control

| Zone | Fonction |
|------|----------|
| Start / Stop | `core/bot_process` → PID `data/bot.pid` |
| Métriques | equity, PnL, signal, cycle, DD via `status_bridge` |
| Bougies OHLC | closed bars (OKX → CSV), Plotly |
| Config | capital, risk, MA, min_conf → `runtime_config` |
| Ticket paper | `manual_paper_orders.enqueue` (5–250 USDC) |
| Blotter | journal.jsonl / trades CSV |

## Dashboards web (secondaires)

| UI | URL |
|----|-----|
| Desk TV + blotter | http://127.0.0.1:8765/desk |
| Elite React | http://127.0.0.1:8765/ |

```bash
python3 web/server.py   # si besoin sans run_v10
```

## Règles moteur

1. Closed bars only (`confirm==1` / historique)
2. Ticks → `last_price` uniquement
3. Forming isolé (`_forming`)
4. Paper first

## Tests

```bash
python3 scripts/audit_closed_bars_smoke.py
python3 -m py_compile control_panel.py core/bot_process.py core/engine.py trading/intelligent_strategy.py
python3 -m pytest tests/test_runtime_dashboard.py tests/test_neural_parent_brain.py -q
```

Voir `COMMANDES_TEST.md`.

## Avertissement

Paper / recherche uniquement. Aucune garantie de performance.
