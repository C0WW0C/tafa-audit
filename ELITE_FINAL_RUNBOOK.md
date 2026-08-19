# TAFA Elite Final — backtest multi-timeframe et paper/demo OKX

Cette édition est conçue pour valider la stratégie avec des données publiques OKX confirmées et un portefeuille paper local de **500 USDC**. Elle ne place aucun ordre réel et ne requiert aucune clé privée.

## Préparation et données

Installez les dépendances, copiez le profil Elite Final et récupérez les données réelles fermées pour chaque timeframe :

```bash
pip install -r requirements.txt
cp .env.elite-final-paper.example .env
python scripts/fetch_okx_history.py --symbol BTC-USDC --bars 2000 --timeframes 5m,15m,1H,4H
```

Le téléchargeur utilise l’endpoint public d’historique OKX et retient uniquement les bougies confirmées. Il échoue explicitement si l’un des timeframes ne contient pas 2 000 bougies.

## Backtest

Lancez ensuite le backtester :

```bash
python scripts/run_elite_final_backtest.py --symbol BTC-USDC --capital 500 --bars 2000 --timeframes 5m,15m,1H,4H
```

Le rapport JSON est écrit dans `reports/elite_final_mtf_2000.json`. Chaque timeframe est testé indépendamment avec le même capital de 500 USDC ; les P&L ne sont pas additionnés, car les positions hypothétiques se chevauchent dans le temps.

## Paper/demo OKX

Validez la release, puis démarrez le runtime local :

```bash
python scripts/elite_final_release_gate.py --with-smoke
python run_elite_final_paper.py
```

Le dashboard local est disponible sur `http://127.0.0.1:8765`. Il démarre également le launcher Elite Final sécurisé. Vérifiez que le mode est `PAPER`/`DEMO`, que le capital paper est 500 USDC et que l’état de la source est frais.

## Limites

Un backtest décrit un résultat sous des hypothèses de données, frais et exécution ; il ne prédit pas une performance future. Cette release n’essaie pas les endpoints privés OKX, les fills de démonstration exchange, les frais réels ni le slippage de marché.

> This is research and analysis only, not personalized financial advice.
