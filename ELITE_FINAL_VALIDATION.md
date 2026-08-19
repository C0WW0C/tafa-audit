# Validation — TAFA Elite Final

**Périmètre vérifié :** données historiques publiques OKX confirmées, quatre timeframes (`5m`, `15m`, `1H`, `4H`), 2 000 bougies par timeframe, capital paper isolé de 500 USDC. Les exécutions de backtest sont indépendantes : les résultats ne doivent pas être additionnés.

## Résultat du backtest exécuté

| Timeframe | Bougies | Trades clôturés | Équité finale | Rendement | Drawdown maximal |
|---|---:|---:|---:|---:|---:|
| 5m | 2 000 | 0 | 500,00 USDC | 0,00 % | 0,00 % |
| 15m | 2 000 | 1 | 499,50 USDC | -0,10 % | 0,12 % |
| 1H | 2 000 | 10 | 500,67 USDC | 0,13 % | 0,66 % |
| 4H | 2 000 | 24 | 487,59 USDC | -2,48 % | 2,95 % |

Les résultats proviennent de `reports/elite_final_mtf_2000.json`, qui conserve le manifeste de données, les périodes couvertes et les hypothèses de frais. La présence de résultats négatifs ou nuls dans plusieurs fenêtres est une information importante : cette exécution ne soutient pas une affirmation de rentabilité.

## Contrôles de release

| Contrôle | Résultat |
|---|---|
| Tests automatisés | 10 tests réussis après ajout du profil Elite Final. |
| Verrou paper/demo | Le launcher Elite Final force le mode `DEMO`, désactive le live et fixe le capital local à 500 USDC. |
| Données | 2 000 bougies réelles, fermées et étiquetées `okx-public-history` pour chaque timeframe. |
| Backtest | Le script rejette tout dataset inférieur à 2 000 bougies. |
| Dashboard | La commande de démarrage locale privilégie `run_elite_final_paper.py`. |

## Limites

Ce backtest ne constitue pas une projection de performance. Il ne réalise aucun ordre, n’utilise aucune clé privée et ne valide ni les fills exchange, ni le slippage réel, ni les frais réels, ni les endpoints privés de démonstration.

> This is research and analysis only, not personalized financial advice.
