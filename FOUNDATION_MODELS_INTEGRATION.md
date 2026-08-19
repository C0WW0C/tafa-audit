# TAFA — Couche de consensus Kronos-base + Chronos-2

## Objectif et principe de sécurité

Cette extension ajoute une porte de validation à deux modèles pour le **mode paper trading uniquement**. Le modèle spécialisé chandeliers `NeoQuasar/Kronos-base` produit un vote à partir de données OHLCV, puis `amazon/chronos-2` sert de validation indépendante. TAFA ne reçoit jamais de poids de modèle dans le dashboard et ne télécharge aucun modèle automatiquement.

> La couche est volontairement « fail closed » : une configuration absente, une réponse invalide, un délai dépassé, une divergence des modèles ou une confiance insuffisante renvoie **HOLD**. Elle ne peut donc pas transformer une erreur d’inférence en ordre.

## Règle de décision

Un signal paper est accepté seulement si quatre conditions sont satisfaites : la stratégie TAFA émet `BUY` ou `SELL`, Kronos-base émet le même signal, Chronos-2 émet le même signal, et la confiance la plus basse des deux modèles atteint le seuil configuré. Les contrôles existants — circuit breaker, quality gate, risk manager et Neural Parent Brain — restent applicables après ce consensus.

| Élément | Valeur par défaut | Rôle |
|---|---:|---|
| `TAFA_FOUNDATION_MODELS_ENABLED` | `false` | Active la porte de consensus en paper trading, seulement après configuration des deux endpoints. |
| `TAFA_FOUNDATION_MIN_CONFIDENCE` | `0.70` | Seuil minimal commun aux deux réponses. |
| `TAFA_FOUNDATION_CONTEXT` | `240` | Nombre maximum de chandeliers OHLCV transmis ; borné entre 60 et 512. |
| `TAFA_FOUNDATION_TIMEOUT_S` | `4` | Délai maximal par endpoint ; borné entre 0,5 et 15 secondes. |
| `TAFA_KRONOS_ENDPOINT` | vide | Endpoint privé de prédiction pour `NeoQuasar/Kronos-base`. |
| `TAFA_CHRONOS_ENDPOINT` | vide | Endpoint privé de prédiction pour `amazon/chronos-2`. |

## Contrat des endpoints

Les deux endpoints doivent être accessibles depuis l’hôte TAFA et accepter une requête HTTP `POST` JSON de la forme suivante :

```json
{
  "model": "NeoQuasar/Kronos-base",
  "symbol": "BTC-USDC",
  "timeframe": "4h",
  "candles": [
    {"open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}
  ]
}
```

La réponse doit être un JSON sans autre effet de bord :

```json
{"signal": "BUY", "confidence": 0.81}
```

Les valeurs autorisées pour `signal` sont `BUY`, `SELL` et `HOLD`. La confiance doit être normalisée entre `0` et `1`. Toute autre réponse est bloquée.

## Activation contrôlée

Commencez en copiant `.env.paper-demo.example` vers `.env`, en laissant les identifiants OKX vides et le modèle désactivé. Déployez puis validez séparément les deux services d’inférence, renseignez leurs URLs privées dans l’environnement du processus TAFA, puis activez `TAFA_FOUNDATION_MODELS_ENABLED=true`.

L’état est consultable via `/api/models/status` et via `/foundation_models.html`. Cette page indique pour chaque modèle le signal, la confiance, la latence, l’état et le motif d’un éventuel blocage. Elle n’affiche aucun endpoint ni secret.

### Serveur local prêt à l’emploi

Le projet comporte désormais un serveur local distinct dans `model_server/server.py`. Il est lié exclusivement à `127.0.0.1:8787`, avec les routes `POST /kronos/predict`, `POST /chronos/predict` et `GET /health`. Préparez les dépendances officielles une seule fois avec `scripts/setup_local_model_server.sh`, puis copiez `.env.local-model-paper.example` vers `.env`. Lancez le serveur seul avec `scripts/start_local_model_server.sh`, ou TAFA en mode papier avec `scripts/start_local_tafa_with_models.sh`.

Les deux modèles produisent de vraies prévisions à partir de chandeliers OHLCV locaux. Le serveur ne crée pas de « signal de secours » : il renvoie une erreur 503 si les poids ne sont pas chargés. Le consensus TAFA peut toujours retourner `HOLD` lorsque les modèles divergent ou qu’ils ne franchissent pas le seuil de confiance. Ce comportement est une protection, pas une défaillance de configuration.

Après le démarrage du serveur, exécutez `python3 scripts/check_local_model_consensus.py` pour confirmer que TAFA appelle les deux routes à partir de l’historique BTC-USDC 4 h fourni. Le script n’envoie aucun ordre ; il affiche uniquement l’état du consensus et les deux réponses de modèle.

Le lanceur `scripts/start_local_tafa_with_models.sh` démarre ou réutilise dans le bon ordre le serveur de modèles et le dashboard, puis lance le profil Elite paper à 500 USDC avec `TAFA_DASHBOARD_EXTERNAL=true`. Cette séquence évite la collision de port observée lorsqu’un bot tente de démarrer un second dashboard sur le port 8765.

## Validation requise avant tout élargissement

Réalisez un backtest walk-forward puis une période de paper trading avec des coûts, un spread et du slippage réalistes. Comparez le consensus à la stratégie TAFA sans modèle, en privilégiant la stabilité hors échantillon, le drawdown maximal et le rendement net plutôt que l’exactitude directionnelle seule. Cette extension ne doit pas être utilisée pour envoyer des ordres réels sans revue technique, contrôle des clés et confirmation explicite de l’opérateur.

## Références

[1] https://huggingface.co/NeoQuasar/Kronos-base — *Kronos-base, Hugging Face Model Card*  
[2] https://huggingface.co/amazon/chronos-2 — *Chronos-2, Hugging Face Model Card*
