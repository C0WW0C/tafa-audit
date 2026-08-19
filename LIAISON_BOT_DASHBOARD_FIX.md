# Fix liaison bot ↔ dashboard (2026-08-13)

## Problèmes corrigés

| Bug | Impact | Fix |
|-----|--------|-----|
| `status_bridge.publish` écrasait tout le JSON | Stop panel → equity/signal/paper perdus | `publish(..., merge=True)` + merge imbriqué |
| `stop_bot` publiait `{running:False}` seul | Dashboard vide après stop | merge=True |
| `paper.status` incomplet | Panel sans capital / qty / session_pnl | Champs dashboard complets |
| Pas de `strategy.get_state()` | Bloc AI vide | `get_state()` signal/conf/régime/bars |
| `status_snapshot` fragile | Running faux / pas d’âge | PID + heartbeat <45s + bridge_path |

## Chaîne validée

```
control_panel / web desk
  → status_bridge.read() ← data/live_status.json
  ← run_v10 loop: engine.status() → status_bridge.publish(st)
  ← bot_process start/stop (PID data/bot.pid)
```

## Test

```bash
python3 -c "from core.status_bridge import publish, read; publish({'running':True,'paper':{'equity':1}}); publish({'running':False}, merge=True); print(read()['paper'])"
```
