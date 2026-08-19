# Time Series Momentum (TAFA)

Référence : **Moskowitz, Ooi, Pedersen (2012)** — *Time series momentum*, Journal of Financial Economics.

## Règle implémentée

Pour chaque instrument, sur **barres fermées uniquement** :

1. **Signal** = `sign(R_{t-k:t-1})`  
   - rendement cumulé des `k` dernières bougies fermées  
   - `+` → **BUY** · `−` → **SELL** (sortie / pas d’entrée)

2. **Volatilité ex ante** (EWMA des rendements au carré, §2.4 du paper)  
   - sert à **scaler la confiance** (|ret| / σ)

3. Filtres secondaires : régime, EMA, RSI, volume (ne remplacent pas le TSMOM)

## Paramètres runtime

| Clé | Défaut | Rôle |
|-----|--------|------|
| `tsmom_lookback` | 48 | Horizon k (barres) |
| `tsmom_vol_span` | 20 | EWMA vol |
| `min_conf` | 0.55 | Seuil de confiance |

## Paper vs bot

| Paper (futures, mois) | TAFA (spot paper, barres TF) |
|----------------------|------------------------------|
| Lookback 12 mois | `tsmom_lookback` barres |
| Hold 1 mois | Signal re-évalué chaque cycle |
| Size ∝ 1/σ | Confiance ∝ \|ret\|/σ (sizing via risk_manager) |
| Long & short | Long-only + exit SELL (paper spot) |

Closed-bars only — pas de look-ahead sur bougie en formation.
