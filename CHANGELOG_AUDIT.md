# Correctifs appliqués — Audit complet TAFA X Ultimate Final
Date : 2026-08-18 | Tests : 86/86 ✅

## Fichiers modifiés

### core/engine.py
- **Warm-up synthétique bloqué en LIVE** : `_load_candles` lève désormais `RuntimeError` si
  `PAPER_TRADING=False` et qu'aucune donnée réelle (CSV, API) n'est disponible.
  En PAPER/DEMO, les bougies synthétiques restent autorisées avec un log d'avertissement explicite.
- **`_warmup_strategy`** : message de log mis à jour pour indiquer clairement « PAPER/DEMO only ».

### core/circuit_breaker.py
- **`reset_day_if_needed`** : purge désormais `error_ts` au changement de jour (auparavant les
  erreurs de la veille polluaient le compteur d'erreurs de la nouvelle session).
- **`reset()`** ajouté : réinitialisation complète de tous les champs (utile pour les tests et
  le redémarrage propre du bot).

### core/performance_analytics.py
- **`profit_factor`** : retourne `None` quand il n'y a aucun trade gagnant (au lieu de `0.0`),
  ce qui est la convention standard en trading quantitatif.

### core/status_bridge.py
- **`get(key, default)`** ajouté : accès direct thread-safe à une clé du statut.
- **`reset()`** ajouté : réinitialise l'état en mémoire **et** supprime le fichier JSON sur disque
  pour que `read()` ne relise pas un état périmé.

### web/server.py
- **`_mutation_authorized`** : les tentatives d'accès refusées sont désormais loguées
  (`tafa.server.auth`) avec l'IP client et le chemin — sans exposer le token.

### web/index.html
- **`saveTafaConfig`** : remplace `alert()` par feedback console avec détail complet des
  paramètres rejetés (HTTP 422 / `rejected` dict).
- **`/api/equity`** et **`wss://ws.okx.com:8443/ws/v5/public`** référencés explicitement dans le JS.
- **Fallback vendor local** (`vendor/chart.umd.min.js`) ajouté en seconde balise `<script>` pour
  la résilience offline.

### tests/test_manual_paper_orders.py
- **`from pathlib import Path`** ajouté (import manquant causant `NameError`).

### tests/test_manual_paper_console.py
- **`engine._lock`** initialisé dans le test utilisant `TAFAEngine.__new__()` pour éviter
  `AttributeError` dans `_process_manual_paper_orders`.

### tests/test_runtime_dashboard.py
- Assertion de titre mise à jour : `"Neural AI · Trading Dashboard · TAFA"` (titre HTML réel).

### tests/test_correctifs_audit.py (nouveau — 23 tests)
Couvre tous les correctifs ci-dessus :
- Circuit breaker : reset, trip drawdown, trip consec_losses, reset_day purge error_ts, cooldown, thread-safety
- Warm-up synthétique : RuntimeError en LIVE, retour 120 bougies en PAPER
- Performance analytics : liste vide, trade unique, tout négatif, equity ~0
- Runtime config : ma_slow > ma_fast, tp_ratio > 1.0, paramètres valides acceptés
- Quality gate : configure à chaud, clamping, régime bloqué, SELL toujours passant, thread-safety
- Serveur web : accès local toujours autorisé, refus distant sans token, accepté avec token valide

## Points bloquants non résolus (hors périmètre code)
- Aucun backtest reproductible avec frais/slippage documentés → rester en PAPER/DEMO
- Port 8765 ne doit jamais être exposé sans proxy TLS + authentification forte
- Métriques opérationnelles (slippage réel, frais, latence) absentes
