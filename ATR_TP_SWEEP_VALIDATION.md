# Validation du balayage ATR stop / take-profit

Le script `scripts/sweep_atr_tp_multiframe.py` a été exécuté sur 48 combinaisons, soit quatre stops ATR (`1,0`, `1,2`, `1,5`, `2,0`) et trois take-profits (`1,4 %`, `1,8 %`, `2,2 %`) pour les quatre timeframes Elite Final. Chaque exécution utilise les 2 000 bougies OKX confirmées du timeframe concerné, 500 USDC de capital paper, 15 % de fraction de position et 8 bps de frais par côté.

## Synthèse par timeframe

| Timeframe | Meilleure combinaison in-sample | P&L net | Profit factor | Drawdown max | État |
|---|---|---:|---:|---:|---|
| 5m | Aucune | 0,00 USDC | n.d. | 0,00 % | Aucun trade : non exploitable. |
| 15m | ATR 1,0 / TP 1,4 % | -0,31 USDC | 0,00 | 0,08 % | Un seul trade : non exploitable. |
| 1H | ATR 2,0 / TP 2,2 % | +1,24 USDC | 1,245 | 0,63 % | Candidat de recherche, seulement 10 trades. |
| 1H | ATR 1,2 / TP 1,8 % | +1,07 USDC | 1,212 | 0,45 % | Candidat alternatif avec drawdown inférieur et 13 trades. |
| 4H | ATR 1,0 / TP 1,8 % | -2,58 USDC | 0,851 | 1,38 % | Toutes les combinaisons sont négatives. |

Les deux réglages 1H positifs ne constituent pas une preuve de rentabilité : ils proviennent de la même période de sélection et le nombre de trades reste faible. Les résultats 5m et 15m n’atteignent pas le minimum de dix trades défini pour la colonne `eligible`. Aucun réglage 4H ne doit être retenu au vu de ce balayage.

## Prochaine validation obligatoire

1. Geler séparément les candidats `ATR 2,0 / TP 2,2 %` et `ATR 1,2 / TP 1,8 %`.
2. Les tester sur un segment chronologique hors échantillon, avec les mêmes frais et sans modifier les paramètres.
3. Comparer P&L net, profit factor, drawdown et nombre de trades ; rejeter tout candidat qui se dégrade hors échantillon.
4. Ne pas agréger les résultats entre timeframes, car les positions simulées peuvent se chevaucher.

Les fichiers détaillés produits sont `reports/atr_tp_sweep_2000.json` et `reports/atr_tp_sweep_2000.csv`.

> This is research and analysis only, not personalized financial advice.
