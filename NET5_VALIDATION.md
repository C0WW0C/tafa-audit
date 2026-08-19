# Validation — profil 1,8 % / 5 USDC nets

## Réglages appliqués

| Paramètre | Valeur | Effet |
|---|---:|---|
| Capital paper | 500 USDC | Capital local du profil Elite Final. |
| Take-profit de recherche | 1,8 % | Sortie de take-profit calculée à 1,8 % au-dessus de l’entrée dans le backtest. |
| Frais | 8 bps à l’entrée et 8 bps à la sortie | Les P&L de trade retirent les frais des deux côtés. |
| Seuil de session | 5 USDC nets | Une nouvelle entrée paper est bloquée seulement après que le gain net réalisé atteint ce seuil. |
| Timeframes | 5m, 15m, 1H, 4H | 2 000 bougies OKX confirmées et indépendantes par timeframe. |

## Résultat du test exécuté

| Timeframe | Équité finale | Rendement | Seuil net de 5 USDC atteint ? |
|---|---:|---:|---|
| 5m | 500,00 USDC | 0,00 % | Non |
| 15m | 499,50 USDC | -0,10 % | Non |
| 1H | 500,04 USDC | +0,01 % | Non |
| 4H | 489,28 USDC | -2,14 % | Non |

Le profil est donc correctement appliqué et la porte de release est validée, mais **aucun timeframe n’a atteint 5 USDC nets** sur l’échantillon de 2 000 bougies exécuté. Ce constat doit être conservé : modifier des paramètres jusqu’à obtenir le seuil sur le même échantillon créerait un risque de surajustement.

## Utilisation paper/demo

```bash
cp .env.elite-net5-paper.example .env
python scripts/elite_final_release_gate.py
python run_elite_final_paper.py
```

> Ce profil limite une nouvelle entrée après un gain net réalisé ; il ne garantit aucun gain et ne doit pas être interprété comme une recommandation de trading.
