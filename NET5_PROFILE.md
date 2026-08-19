# Profil Elite Final — take-profit 1,8 % et objectif net de 5 USDC

Le profil `elite-net5-paper` utilise un take-profit de **1,8 %** et mesure le résultat après frais d’entrée et de sortie dans le backtester. Il fixe également une borne de session : lorsque le portefeuille paper réalise au moins **5 USDC nets**, les nouvelles entrées paper sont bloquées pour le reste de la session ; une position déjà ouverte conserve ses règles de sortie.

Cette borne ne force pas un gain : elle limite seulement l’activité après que le seuil a effectivement été réalisé. Le backtest applique les frais configurés à l’entrée et à la sortie, mais ne peut pas reproduire les fills, le spread ou le slippage réels.

Pour tester ce profil :

```bash
cp .env.elite-net5-paper.example .env
python scripts/run_elite_final_backtest.py --tp-pct 1.8 --net-target-usd 5
python run_elite_final_paper.py
```

> This is research and analysis only, not personalized financial advice.
