# Validation walk-forward ATR/TP — TAFA Elite

Le validateur `scripts/walk_forward_atr_tp.py` sépare chronologiquement les 2 000 bougies de chaque timeframe en **1 200 bougies de train** et **800 bougies de test**. Les réglages ATR/TP sont sélectionnés exclusivement sur le train. Le test reçoit ensuite les paramètres retenus sans modification.

## Garde-fous appliqués

Un candidat de train doit réunir simultanément un P&L net positif, au moins huit trades et un profit factor d’au moins 1,00. Un candidat de test devrait ensuite afficher un P&L net positif, au moins cinq trades, un profit factor d’au moins 1,10 et un drawdown inférieur ou égal à 2 % pour être accepté en recherche paper.

## Résultat de l’exécution

| Timeframe | Résultat | Interprétation |
|---|---|---|
| 5m | `rejected_insufficient_train_evidence` | Aucun réglage ne rassemble assez de signaux. |
| 15m | `rejected_insufficient_train_evidence` | Le nombre de trades est insuffisant. |
| 1H | `rejected_insufficient_train_evidence` | Aucun réglage du train ne satisfait simultanément P&L positif, profit factor minimal et nombre de trades. |
| 4H | `rejected_insufficient_train_evidence` | Aucun réglage du train ne satisfait les critères minimaux. |

Cette absence de sélection est le comportement attendu du garde-fou : aucun réglage ne doit être promu en paper prolongé à partir des résultats actuels. Les fichiers détaillés sont `reports/walk_forward_atr_tp_2000.json` et `reports/walk_forward_atr_tp_2000.csv`.

## Suite de recherche recommandée

La prochaine amélioration doit porter sur la qualité des signaux et les données, non sur une exposition plus grande : ajouter un filtre de régime/volume, étendre la profondeur historique, puis réexécuter le même protocole immuable. Ne modifiez pas les critères de sélection pour faire accepter un candidat.

> This is research and analysis only, not personalized financial advice.
