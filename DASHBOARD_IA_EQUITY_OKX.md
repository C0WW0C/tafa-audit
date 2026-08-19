# Dashboard TAFA — IA configurable, equity et données OKX publiques

## Portée de la refonte

Le dashboard local a été reconstruit comme une surface de **configuration runtime et d’observabilité paper/demo**. Il expose uniquement des paramètres dont l’application a été vérifiée dans les composants actifs. Les réglages passent d’abord par une prévisualisation locale, puis par `POST /api/config`; le serveur retourne les clés acceptées, les clés appliquées et les motifs de refus éventuels.

> Le dashboard ne possède aucun contrôle de démarrage, d’arrêt, de changement de mode, d’armement, de placement, de modification ou d’annulation d’ordre.

## Paramètres réellement contrôlés

| Bloc | Réglages exposés | Application effective |
|---|---|---|
| Risque et stratégie | Capital paper, risque, stop-loss, take-profit, trailing, symbole | `risk_manager`, configuration runtime et stratégie active. |
| Signal IA / TSMOM | Activation IA, seuil de confiance, EMA, RSI, confirmations, pente, volume, lookback et volatilité TSMOM | `IntelligentStrategy.apply_config()` de l’instance en cours. |
| Experts | Activation et poids de TSMOM, EMA, RSI, momentum et volume, ainsi que vitesse d’apprentissage | `OnlineLearner`; les poids normalisés et les votes sont republiés dans l’état runtime. |
| Cerveau parent | Vitesse d’adaptation et poids du signal, régime, accord des experts, momentum et volatilité | `NeuralParentBrain.apply_config()`; le cerveau demeure un filtre soumis aux garde-fous aval. |
| Modèles de fondation | Activation, confiance minimale, contexte et délai | `FoundationModelConsensus._settings()` en mode paper uniquement. |

Si tous les experts sont désactivés, le système réactive TSMOM comme composant déterministe minimal. Cette règle est explicitement visible dans l’état de stratégie et évite une configuration silencieusement vide.

## Graphiques et provenance

La courbe d’equity lit les enregistrements `performance` persistés de la base SQLite par l’endpoint en lecture seule `GET /api/equity`. Lorsqu’aucune série n’existe encore, le dashboard affiche seulement le dernier instantané paper connu au lieu de générer des données de démonstration.

Les bougies passent par `GET /api/candles`, qui privilégie les chandeliers fermés de l’API publique OKX et indique clairement tout repli CSV local. En parallèle, le ticker du panneau utilise le canal public WebSocket `tickers` d’OKX, sans authentification. OKX documente que ses canaux publics incluent notamment les tickers et les K-lines, et recommande WebSocket pour les données de marché et la profondeur.[1]

| Élément affiché | Source | Signification |
|---|---|---|
| Chandeliers | OKX REST public, puis CSV local si nécessaire | Visualisation de bougies fermées, non une confirmation d’exécution. |
| Dernier prix | OKX WebSocket public `tickers` | Cotation live publique, sans droit de trading. |
| Equity | SQLite `performance`, sinon statut paper | Historique réellement persisté, sans points synthétiques. |
| Fraîcheur / erreur | Bridge de statut et état WebSocket | Permet de distinguer une donnée active, périmée ou repliée. |

## Validation réalisée

Les validations couvrent la préservation des détails de refus HTTP 422, les bornes des nouveaux paramètres, l’application réelle des experts et du cerveau parent, la protection d’un poids appris entre cycles, la série d’equity chronologique, les endpoints dashboard et l’absence de contrôles d’exécution dans le HTML. La suite complète de tests a été exécutée avec succès, et la syntaxe JavaScript du dashboard a été vérifiée.

## Références

[1] [OKX API Guide — WebSocket public, tickers et K-lines](https://www.okx.com/docs-v5/en/)
