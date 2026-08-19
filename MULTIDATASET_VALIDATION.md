# Validation multi-datasets Internet — TAFA Elite

## Couverture collectée

La collecte a récupéré et validé **12 datasets** de 2 000 bougies fermées provenant de l’API publique OKX : BTC-USDC, ETH-USDC et SOL-USDC pour les granularités `5m`, `15m`, `1H` et `4H`. Chaque fichier contient sa source, son instrument, sa granularité, sa chronologie et une empreinte SHA-256 dans `data/market/dataset_manifest.json`.

Cette couverture est un univers de recherche défini, non la totalité des bougies disponibles sur Internet. Les périodes diffèrent selon les timeframes ; les datasets restent donc séparés et leurs P&L ne sont jamais agrégés.

## Protocole

Pour chaque dataset, le validateur applique un split chronologique de 1 200 bougies de train et 800 bougies de test. Il compare 12 combinaisons de stop ATR (`1,0`, `1,2`, `1,5`, `2,0`) et de take-profit (`1,4 %`, `1,8 %`, `2,2 %`), sélectionne seulement un candidat positif en train, puis le teste sans changement.

| Critère de train | Seuil |
|---|---:|
| Nombre minimal de trades | 8 |
| P&L net | Strictement positif |
| Profit factor | Au moins 1,00 |

| Critère de test | Seuil |
|---|---:|
| Nombre minimal de trades | 5 |
| P&L net | Strictement positif |
| Profit factor | Au moins 1,10 |
| Drawdown maximal | Au plus 2,00 % |

## Résultats

| Instrument | 5m | 15m | 1H | 4H |
|---|---|---|---|---|
| BTC-USDC | Preuve train insuffisante | Preuve train insuffisante | Preuve train insuffisante | Preuve train insuffisante |
| ETH-USDC | Preuve train insuffisante | Preuve train insuffisante | Rejet hors échantillon | Rejet hors échantillon |
| SOL-USDC | Preuve train insuffisante | Preuve train insuffisante | Accepté pour **recherche paper** | Preuve train insuffisante |

Le candidat SOL-USDC 1H a retenu `ATR 2,0 / TP 1,8 %`. Il affiche +9,80 USDC sur le train et +0,24 USDC sur le test, avec un profit factor test de 1,10 et un drawdown test de 0,63 %. Cette acceptation est **limitée à la recherche paper** : un seul segment hors échantillon et une marge de profit limitée ne démontrent pas une robustesse suffisante pour le réel.

Les candidats ETH-USDC 1H et 4H ont été rejetés malgré des résultats train positifs, car ils deviennent négatifs hors échantillon. Ce rejet est une confirmation que le protocole évite de promouvoir un réglage uniquement adapté à son jeu de sélection.

## Limites et suite

Les bougies Internet ne modélisent pas les fills, spreads, slippage ou la latence d’exécution. La prochaine étape est d’étendre la période historique, de répéter les splits chronologiques et de mesurer le slippage simulé avant toute prolongation paper. Aucun ordre réel n’est activé par cette release.

## Références

[1] [Documentation API OKX — Historical Candlesticks](https://www.okx.com/docs-v5/en/#rest-api-market-data-get-candlesticks-history)

[2] [OKX Historical Data](https://www.okx.com/en-us/historical-data)
