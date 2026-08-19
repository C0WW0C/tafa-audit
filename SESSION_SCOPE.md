# Périmètre de la base Ibhextif — session TAFA

## Couverture disponible

Cette base initialise les connaissances à partir des éléments réellement accessibles dans la session de travail : le projet **TAFA X Elite**, les rapports d’audit et de release produits dans le projet, les rapports de backtest multi-timeframe et le script de balayage ATR/TP. Elle ne constitue pas une copie complète d’un historique de conversation externe, ni une ingestion de documents non présents dans le projet.

## Principes de traçabilité

Chaque connaissance doit séparer les faits observés dans un fichier, les réglages ou décisions formulés dans la session, les hypothèses de stratégie et les conclusions de backtest. Les résultats historiques ne constituent pas une validation de production et le mode réel reste hors périmètre.

## Décisions observées

| Identifiant | Décision ou contrainte | Statut |
|---|---|---|
| CONV-TAFA-001 | Maintenir le bot en paper/demo OKX ; aucun ordre réel n’est configuré. | Confirmé |
| CONV-TAFA-002 | Backtester 2 000 bougies par timeframe avec capital paper de 500 USDC. | Confirmé |
| CONV-TAFA-003 | Évaluer les réglages ATR stop / take-profit par timeframe sans agréger les P&L. | Confirmé |
| CONV-TAFA-004 | Utiliser 1,8 % comme take-profit de recherche et 5 USDC comme seuil net de session, sans garantie de gain. | Confirmé |
| CONV-TAFA-005 | Toute sélection de paramètres doit être validée sur une période chronologique hors échantillon. | Confirmé |

## Limites connues

Les séries utilisées sont des bougies historiques publiques OKX. Les coûts de 8 bps par côté sont inclus dans les backtests récents, mais le slippage, les fills réels, la latence et les endpoints privés de démonstration ne sont pas validés par ces résultats.
