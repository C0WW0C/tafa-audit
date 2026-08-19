# Rapport backtests TSMOM — TAFA

**Date :** 2026-08-13  
**Stratégie :** TAFA_TSMOM_V7 (Moskowitz–Ooi–Pedersen sign + filtres)  
**Frais :** 8 bps / côté · **Position :** 20 % equity · **SL/TP ATR :** 1.5 / 3.0  
**Données :** OKX CSV ~2000 barres (BTC / ETH / SOL)

> Ce n’est **pas** une preuve de rentabilité future. Échantillons courts vs paper JFE (futures 1965–2009).

## 1. Multi-dataset (lookback=48 initial)

| Sym | TF | Trades | WR% | PnL | Ret% | MaxDD% | PF | OOS Ret% |
|-----|-----|--------|-----|-----|------|--------|-----|----------|
| BTC | 4H | 56 | 37.5 | +2.9 | +0.3 | 2.3 | 1.03 | -1.5 |
| BTC | 1H | 50 | 38.0 | -5.1 | -0.5 | 1.7 | 0.89 | +0.3 |
| BTC | 15m | 72 | 19.4 | -28.8 | -2.9 | 2.9 | 0.28 | -1.3 |
| ETH | 4H | 62 | 33.9 | -34.8 | -3.5 | 5.0 | 0.79 | -1.9 |
| ETH | 1H | 68 | 35.3 | -3.7 | -0.4 | 2.6 | 0.95 | -0.2 |
| ETH | 15m | 66 | 22.7 | -32.8 | -3.3 | 3.4 | 0.23 | -1.4 |
| SOL | 4H | 52 | 34.6 | -26.6 | -2.7 | 4.8 | 0.84 | -1.2 |
| SOL | 1H | 52 | 38.5 | +20.5 | +2.1 | 1.8 | 1.31 | -0.7 |
| SOL | 15m | 76 | 19.7 | -41.8 | -4.2 | 4.4 | 0.20 | -1.7 |

**Synthèse LB=48 :** 2/9 positifs · ret moyen **-1.7 %** · 15m très bruité.

## 2. Sensibilité lookback (BTC)

| Mode | TF | LB | Trades | WR% | Ret% | DD% | PF |
|------|-----|-----|--------|-----|------|-----|-----|
| filt | 4H | 12 | 69 | 37.7 | +0.1 | 3.6 | 1.01 |
| filt | 4H | 48 | 56 | 37.5 | +0.3 | 2.3 | 1.03 |
| **filt** | **4H** | **120** | **45** | **42.2** | **+2.3** | **1.7** | **1.33** |
| pure | 4H | 120 | 62 | 32.3 | -1.1 | 2.5 | 0.91 |
| filt | 1H | 48 | 50 | 38.0 | -0.5 | 1.7 | 0.89 |

**Meilleur setup échantillon :** filtre ON · **4H** · **lookback 120** · PF 1.33 · DD faible.

## 3. Conclusions opérationnelles

1. **TF 15m** : edge TSMOM détruit par le bruit + frais → éviter pour live paper.
2. **Filtres** (régime / RSI / EMA) > TSMOM « pure » sur cet échantillon crypto.
3. **Lookback long (96–120)** sur 4H se rapproche mieux de l’idée « 12 mois » du paper.
4. **Défaut bot mis à jour :** `tsmom_lookback = 120`.
5. OOS (trade après 70 % des barres) reste fragile → continuer paper + plus de data.

## 4. Commandes

```bash
python3 scripts/run_tsmom_backtests.py
python3 -m backtesting.run_historical --csv data/market/okx_BTC-USDC_4H_2000.csv --tf 4h
python3 scripts/audit_closed_bars_smoke.py
```

JSON détaillé : `reports/tsmom_multidataset_backtest.json`
