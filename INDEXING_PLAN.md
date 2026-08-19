# Plan d’indexation et d’interrogation Ibhextif

## État actuel

La première version est un registre local YAML/Markdown, orienté vers les fichiers produits dans ce projet. Il est volontairement simple, auditable et sans collecte automatique. Cette forme est adaptée à l’archivage des décisions et à la préparation d’une future recherche hybride.

## Découpage proposé

Chaque document doit être fragmenté par section fonctionnelle, avec une cible de 400 à 800 mots. Les chunks doivent conserver `document_id`, `ordinal`, `source_id`, `captured_at`, `trust_level`, `strategy_id`, `backtest_id`, `instrument`, `timeframe` et `freshness_status` lorsque ces champs sont applicables.

## Recherche hybride proposée

1. Filtrer les documents par instrument, timeframe, type de contenu, date de fraîcheur et niveau de confiance.
2. Exécuter une recherche lexicale sur les paramètres, identifiants et métriques.
3. Compléter par une recherche sémantique lorsque des vecteurs sont disponibles.
4. Générer une réponse uniquement à partir des chunks retournés et joindre leurs identifiants.

## Requêtes utiles

| Question | Filtres initiaux | Documents attendus |
|---|---|---|
| Quel candidat ATR/TP doit être testé hors échantillon ? | `backtest_id=BT-ATR-TP-SWEEP-001`, `timeframe=1H` | `DOC-BACKTEST-SWEEP-001`, `DOC-ATR-TP-SWEEP-001` |
| Quels sont les coûts et limites du profil net5 ? | `strategy_id=STRAT-TAFA-ELITE-BASE` | `DOC-NET5-VALIDATION-001`, `DOC-BACKTEST-NET5-001` |
| Que manque-t-il avant une évolution de maturité ? | `type=roadmap|audit` | `DOC-AUDIT-001`, `DOC-MATURITY-ROADMAP-001` |

La base ne doit jamais répondre qu’un réglage est prêt pour le réel sur la seule base d’un résultat historique.
