# Correctif des ressources navigateur du dashboard

## Symptômes traités

Le navigateur pouvait signaler deux ressources locales introuvables sur le serveur TAFA en port 8765 : `/favicon.ico` et `/__manus__/debug-collector.js`. Ces réponses 404 ne bloquaient pas le moteur paper/demo, mais alourdissaient inutilement la console.

## Correctif appliqué

Le serveur `web/server.py` sert désormais un favicon SVG local, ainsi qu’un script JavaScript same-origin sans effet (« no-op ») pour le collecteur de diagnostic optionnel. Aucun accès API, état du bot, clé ou permission supplémentaire n’est accordé par ces routes.

L’avertissement navigateur relatif à la politique `unload` dépend du contexte d’intégration du navigateur. Il n’est pas émis par le moteur TAFA et ne correspond pas à une erreur de stratégie, de WebSocket OKX ou de portefeuille paper.

## Vérification

Le test `test_dashboard_static_fallbacks_avoid_browser_404s` confirme les réponses HTTP 200 et les types MIME attendus. La suite complète comporte 27 tests après ce correctif.
