# Validation chronologique ATR/TP — TAFA Elite

Le script `scripts/walk_forward_atr_tp.py` sélectionne les combinaisons stop ATR / take-profit **uniquement sur les 60 % de bougies les plus anciennes**, puis les évalue sans modification sur les 40 % les plus récentes. Les résultats sont séparés par timeframe et les P&L ne sont jamais additionnés.

```bash
python scripts/walk_forward_atr_tp.py \
  --atr-stops 1.0,1.2,1.5,2.0 \
  --take-profits 1.4,1.8,2.2 \
  --timeframes 5m,15m,1H,4H
```

Un candidat n’est retenu pour la **recherche paper** que s’il réunit dans le segment test : P&L net positif, au moins cinq trades, profit factor d’au moins 1,10 et drawdown inférieur ou égal à 2 %. Ces seuils sont des garde-fous de sélection et non une preuve de performance future.

Le résultat JSON contient les trois meilleurs candidats de train, le candidat retenu et sa métrique test. Le CSV fournit une ligne synthétique par timeframe. Une stratégie ne doit pas passer au réel sur le seul fondement de ce script.
