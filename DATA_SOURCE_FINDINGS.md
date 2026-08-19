# Sources de bougies Internet — constat de collecte

| Source | URL / identifiant | Usage retenu | État |
|---|---|---|---|
| Documentation API OKX | https://www.okx.com/docs-v5/en/#rest-api-market-data-get-candlesticks-history | Bougies historiques publiques et confirmées via `GET /api/v5/market/history-candles`. | Retenue pour les datasets TAFA. |
| Données historiques OKX | https://www.okx.com/en-us/historical-data | Référence officielle sur les jeux de données historiques disponibles. | Source complémentaire. |
| Massive — données crypto structurées | `Massive/get_crypto_bars` | Tentative de collecte structurée conformément à la compétence d’analyse financière. | Indisponible dans cette session : l’API renvoie `failed_precondition / api not found`; aucune donnée Massive n’a été ingérée. |

Les datasets actuellement enregistrés sont exclusivement issus de l’API publique OKX et portent l’étiquette `okx-public-history`. Ils ne sont pas considérés comme exhaustifs : l’instrument, la granularité, la période et l’empreinte sont conservés dans le manifeste local.
