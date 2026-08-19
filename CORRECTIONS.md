# TAFA X ULTIMATE — Corrections appliquées (2026-08-14)

## Bugs corrigés — passe 1 (analyse initiale) + passe 2 (double-check)

| # | Fichier | Bug | Impact | Correction |
|---|---------|-----|--------|------------|
| 1 | `run_v10.py` | `publish()` au démarrage sans `merge=True` | Écrase equity/paper/ai/signal au restart | `merge=True` ajouté |
| 2 | `run_v10.py` | Shutdown reconstituait le dict manuellement, risque race condition | Données vides après stop | Remplacé par `publish({running:False, state:STOPPED}, merge=True)` |
| 3 | `run_v10.py` | Double publish par cycle : `engine_v10.run_cycle()` déjà publie `self.status()`, puis `run_v10` republiait le dict complet (écrasant le résultat AI enrichi) | Signal/ai du parent_brain écrasé par version non-enrichie | `run_v10` ne merge plus que `{running, state, pid}` — le dict complet reste celui de l'engine |
| 4 | `web/server.py` | `data["running"] = bot_alive` ignorait le bridge — STOPPED pendant race startup | Dashboard montre STOPPED alors que le bot démarre | `running = bot_alive OR bridge_fresh (<45s)` |
| 5 | `web/server.py` | `state=`, `stale_s=`, `health.bot_running=` utilisaient `bot_alive` mais `running` était déjà composite | Incohérence state/running affichée sur le dashboard | Uniformisé sur `data["running"]` partout |
| 6 | `web/server.py` | Timeout bridge_fresh 30s dans server vs 45s dans bot_process → fenêtre de désaccord | Streamlit panel et web dashboard pouvaient afficher des états différents | Aligné sur 45s dans les deux |
| 7 | `web/server.py` | `/api/manual-orders` lisait `manual_orders` sans fallback sur `manual_order_tape` | Liste d'ordres manuels toujours vide | Fallback `manual_order_tape` ajouté |
| 8 | `core/engine_v10.py` | `status()` : `st["ai"]` venait de `inner.status()` (signal brut), le veto `parent_brain` non reflété | Dashboard affichait signal non filtré | `st["ai"]` enrichi avec `parent_brain.last` + sync `st["last_signal"]` |
| 9 | `ai/ai_brain.py` | `_get_ml()` importait `model_manager.ModelManager` absent → ImportError silencieux chaque cycle | Spam log, vote ML (25%) toujours fallback strategy | Dégradation gracieuse documentée, `None` retourné proprement |
| 10 | `web/desk.html` | Boutons Start/Stop/Buy/Sell postaient sur routes bloquées (403) sans feedback utilisateur | Clics silencieux | Message clair : "Contrôle via streamlit run control_panel.py" |
| 11 | `core/brain_engine.py` / `core/trend_engine.py` | CRLF Windows (`\r\n`) dans les stubs | SyntaxWarning sur Linux | `sed -i 's/\r//'` appliqué |

## Chaîne publish validée (après double-check)

```
run_v10.py
  ├─ startup      → publish({running:True, pid:X, ...}, merge=True)   ← conserve equity/ai
  └─ loop/cycle   → engine_v10.run_cycle()
       └─ internally → publish_status(self.status())                  ← full dict enrichi parent_brain
     then run_v10  → publish({running:True, state:RUNNING, pid:X}, merge=True) ← lifecycle seulement
  └─ shutdown      → publish({running:False, state:STOPPED}, merge=True)
```

## Cohérence running dans server.py

```python
bot_alive    = _bot_running()                # PID OS
bridge_fresh = data["running"] AND age < 45  # heartbeat bridge
data["running"] = bot_alive OR bridge_fresh  # composite — utilisé PARTOUT (state/stale/health)
```

## Test de régression rapide

```bash
python3 -c "
from core.status_bridge import publish, read
# Simule démarrage + publish engine + publish run_v10
publish({'running':True,'paper':{'equity':1234.5},'ai':{'signal':'BUY','confidence':0.72}})
publish({'running':True,'state':'RUNNING','pid':999}, merge=True)
# Simule stop
publish({'running':False,'state':'STOPPED'}, merge=True)
r = read()
assert r['paper']['equity'] == 1234.5, 'equity perdu!'
assert r['ai']['signal'] == 'BUY', 'signal perdu!'
assert r['running'] == False, 'running incorrect!'
print('OK — paper equity:', r['paper']['equity'], '| ai signal:', r['ai']['signal'], '| running:', r['running'])
"
```
