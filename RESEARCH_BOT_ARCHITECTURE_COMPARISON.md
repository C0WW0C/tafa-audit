# Recherche de référence — persistance et modularité des bots

> **Périmètre.** Cette note compile des pratiques documentées publiquement. Elle ne constitue ni un conseil d’investissement ni une validation de performance future. TAFA reste limité au mode paper/demo OKX.

## Constats vérifiés

La documentation Freqtrade présente la transaction comme un objet persistant qui relie le cycle de vie d’une position aux ordres associés. Les métadonnées recensées incluent notamment l’instrument, l’exchange, les taux et dates d’ouverture/fermeture, les frais et profits, le motif de sortie, les ordres remplis ou annulés, ainsi que les valeurs de stop. Cette granularité est une référence pertinente pour le modèle transactionnel futur de TAFA, mais ne justifie pas de réutiliser ni d’exécuter du code tiers.[1]

La documentation Hummingbot V2 sépare un fournisseur unique de données de marché, des contrôleurs de stratégie et des exécuteurs à cycle de vie fini. Cette séparation est cohérente avec un découplage TAFA entre ingestion, décision, gestion déterministe des risques et simulation d’exécution ; la couche IA prévue ne doit rester qu’un filtre ou un score explicable.[2]

| Domaine | Référence observée | Décision cible TAFA |
| --- | --- | --- |
| État de transaction | Objet transaction et ordres associés persistés | PostgreSQL transactionnel avec transaction, ordre, remplissage, position et événement d’audit distincts. |
| Données de marché | Point d’accès de données isolé des stratégies | Adaptateur de marché produisant des événements normalisés, sans accès direct du moteur IA aux sorties d’ordre. |
| Stratégie | Contrôleurs coordonnant des tâches finies | Orchestrateur paper/demo séparé de l’exécuteur simulé et du circuit breaker. |
| Risque | Cycle de vie explicitement traçable | Autorité de risque déterministe, journalisée et prioritaire sur toute suggestion IA. |

## Références

[1] [Freqtrade — Trade Object](https://www.freqtrade.io/en/stable/trade-object/)

[2] [Hummingbot — Strategy V2 Architecture](https://hummingbot.org/strategies/v2-strategies/)
