# Collecte de bougies Internet et validation — TAFA Elite

Le collecteur récupère des bougies **fermées** de l’API publique officielle OKX pour les instruments et granularités indiqués. Il ne prétend pas couvrir toutes les données du marché : la profondeur disponible, les limites de l’API et les conditions du fournisseur s’appliquent.

```bash
python scripts/fetch_okx_history.py \
  --symbols BTC-USDC,ETH-USDC,SOL-USDC \
  --timeframes 1H,4H,1D \
  --bars 2000

python scripts/validate_market_datasets.py
```

Le validateur produit `data/market/dataset_manifest.json` avec le nombre de bougies, la période couverte, l’instrument, la granularité, la source et l’empreinte SHA-256 de chaque fichier. Tout dataset dont les colonnes, les valeurs OHLCV ou la chronologie sont invalides est rejeté.

Les datasets ne doivent pas être mélangés : les résultats de backtests sont toujours séparés par instrument, timeframe et période. Les bougies Internet sont une source de recherche et ne valident pas une stratégie pour le trading réel.
