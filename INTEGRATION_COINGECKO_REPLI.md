# Intégration CoinGecko — cotation publique de secours

## Rôle retenu

CoinGecko est intégré comme deuxième source de **cotation de référence en USD**, après le ticker public OKX et avant Binance. Il ne remplace pas OKX pour les chandeliers, le carnet d’ordres, la microstructure ou toute action d’exécution. Cette distinction est importante : l’endpoint `simple/price` fournit un prix par identifiant d’actif, mais ne fournit pas un carnet propre à la paire OKX.

## Hiérarchie appliquée

| Priorité | Source | Usage | Conditions |
|---|---|---|---|
| 1 | OKX public | Prix du lieu de marché de référence | Ticker valide et strictement positif. |
| 2 | CoinGecko | Prix USD de secours pour actif connu | Identifiant explicite, valeur positive, horodatage amont inférieur ou égal à 120 secondes. |
| 3 | Binance | Cours public de secours secondaire | Utilisé si CoinGecko est absent, invalide ou périmé. |
| 4 | Mémoire locale | Continuité de simulation | Dernier prix ou modèle local uniquement. |

Les paires cotées en USDC sont étiquetées `coingecko_usd_proxy` lorsque CoinGecko est retenu. Le dashboard ou les journaux peuvent donc distinguer une cotation USD de référence d’un prix observé directement sur OKX. La provenance est disponible via `MarketData.quote_status()`.

## Contrôles appliqués

Le mapping statique limite CoinGecko aux actifs connus par le système : BTC, ETH, SOL, XRP et DOGE. Chaque réponse demande `include_last_updated_at=true`, puis les données dont l’horodatage dépasse 120 secondes sont rejetées. Les réponses valides sont conservées en mémoire 55 secondes afin d’éviter une sollicitation excessive de l’API publique.

CoinGecko documente que `simple/price` accepte des identifiants de monnaie, ainsi que le champ `include_last_updated_at` pour vérifier la fraîcheur ; sa documentation indique aussi une fréquence de cache de 60 secondes pour l’accès public. [1]

## Validation

Les tests vérifient que le système sélectionne CoinGecko après un ticker OKX indisponible, qu’il attribue explicitement la source `coingecko_usd_proxy`, et qu’une réponse CoinGecko âgée est rejetée avant le repli Binance. La suite complète a été exécutée avec succès après la modification.

## Références

[1] [CoinGecko API — Coin Price by IDs, Symbols, or Names](https://docs.coingecko.com/reference/simple-price)

[2] [CoinGecko API — Coins List](https://docs.coingecko.com/reference/coins-list)
