# Garde-fous d’exécution paper — TAFA X Ultimate Elite

**Portée :** uniquement le chemin local `PaperTrading` du socle Elite. Ce composant ne possède aucun client HTTP/WebSocket, aucune clé, aucun endpoint privé OKX et aucune capacité de créer, modifier ou annuler un ordre d’exchange.

## Invariants appliqués

| Règle | Comportement | Motif journalisé |
| --- | --- | --- |
| Anti-duplication d’achat | Un nouvel achat sur le même symbole est refusé pendant 15 secondes après un achat paper validé. | `duplicate_buy_cooldown` |
| Priorité de sortie | Une vente n’est jamais refusée par l’anti-duplication afin de préserver les sorties stop-loss, take-profit ou circuit breaker. | `sell_exit_priority` |
| Budget d’annulation | Le garde conserve un budget de trois annulations par symbole dans une fenêtre de cinq minutes. | `cancel_allowed` ou `cancel_budget_exhausted` |
| Traçabilité | Chaque blocage ou validation sur le chemin paper est écrit dans le journal JSONL avec symbole, côté, quantité, prix et motif. | `paper_guard_block` ou `paper_guard_pass` |

La stratégie Elite actuelle ne maintient pas d’ordres limites paper en attente ; le budget d’annulation est donc un contrat local testé, prêt à être connecté uniquement à un futur composant d’ordres limites **simulés**. Il n’appelle pas et ne doit jamais appeler une route de cancellation OKX.

## Visibilité et tests

L’état du garde est publié sous `paper_guard` dans le statut moteur destiné au dashboard. Il expose la dernière décision, les compteurs de blocage, les fenêtres actives et les limites configurées. Les tests couvrent le rejet d’un achat répété, la priorité de vente, le budget d’annulation et la journalisation d’un blocage dans `TradeManager`.

> Les garde-fous réduisent les opérations paper redondantes ; ils ne valident pas une stratégie ni une rentabilité future. Les données, frais, backtests et gates de risque existants restent nécessaires.
