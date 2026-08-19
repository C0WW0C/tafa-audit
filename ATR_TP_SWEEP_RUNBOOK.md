# Balayage stop ATR / take-profit — TAFA Elite

Le script `scripts/sweep_atr_tp_multiframe.py` exécute toutes les combinaisons de stop ATR et de take-profit en pourcentage sur les timeframes `5m`, `15m`, `1H` et `4H`. Il utilise les datasets locaux de 2 000 bougies OKX fermées et garde le capital de 500 USDC, les frais de 8 bps par côté et la fraction de position de 15 % par défaut.

```bash
python scripts/sweep_atr_tp_multiframe.py \
  --atr-stops 1.0,1.2,1.5,2.0 \
  --take-profits 1.4,1.8,2.2 \
  --timeframes 5m,15m,1H,4H
```

Le script produit un fichier JSON et un CSV dans `reports/`. Les résultats sont regroupés **par timeframe** et ne doivent pas être additionnés. La colonne `eligible` exige au moins 10 trades et un profit factor défini ; elle ne constitue pas une validation de rentabilité.

Après sélection d’un candidat, répétez le test sur une période chronologique distincte et jamais utilisée pour choisir les paramètres. Évitez de retenir un réglage uniquement parce qu’il maximise le P&L d’un seul échantillon.

> This is research and analysis only, not personalized financial advice.
