# Architecture IA pour TAFA X Ultimate

## Positionnement

L’IA doit améliorer le **cycle de recherche, de filtrage et d’explication**, sans devenir un canal direct d’ordres. Cette séparation reprend les points communs observables des frameworks documentés : backtests avec données historiques et coûts, stratégies modifiables, simulation/dry-run, connecteurs séparés et outils d’analyse. [1] [2] [3]

> **Règle non négociable :** une sortie IA ne peut jamais contourner les limites de risque, les release gates, le mode paper/demo, la validation de données ou le journal d’audit.

## Architecture cible

| Couche | Responsabilité | Entrées | Sorties | Autorisation |
|---|---|---|---|---|
| Données | Capturer, valider et versionner les bougies et métadonnées | OHLCV confirmées, volumes, instrument, timeframe | Dataset versionné et manifeste | Lecture seule |
| Caractéristiques | Transformer les données en variables explicables | Dataset versionné | Indicateurs, régime, volatilité, liquidité, qualité données | Lecture seule |
| Recherche IA | Proposer une hypothèse ou classer un régime | Features, résultats de backtests, contraintes | `candidate_id`, score, explication, modèle et dataset utilisés | Aucun ordre |
| Validation | Backtest, walk-forward, coûts, métriques et contrôles d’overfit | Candidat, datasets train/test gelés | Accepté, rejeté ou à revoir | Aucun ordre |
| Risk gate | Appliquer limites hard-codées | Signal, état portefeuille, limites | `allow` ou `block` avec raison | Autorité bloquante |
| Paper executor | Simuler seulement les signaux autorisés | Signal validé et `allow` | Journal de trade paper | Paper/demo uniquement |
| Supervision | Montrer décisions, preuves et incidents | Journaux et événements | Dashboard et alertes | Lecture/arrêt seulement |

## Les quatre rôles IA utiles

### 1. Classifieur de régime

Le premier modèle doit classifier le contexte, par exemple `trend_up`, `trend_down`, `range`, `high_volatility` ou `data_degraded`. Ses features doivent être uniquement calculées à partir de bougies clôturées : rendements retardés, ATR, pente EMA, RSI, volume relatif, spread estimé et timeframe. Sa sortie ne doit pas être un ordre, mais un filtre explicite du type : « stratégie 1H autorisée uniquement si `trend_up` et volatilité dans la bande définie ».

### 2. Contrôle qualité et anomalie

Un modèle léger ou des règles statistiques peuvent détecter bougies incomplètes, gaps, volumes atypiques, prix aberrants et divergence entre WebSocket et REST. Ce rôle protège le backtest et le paper trading : si les données sont dégradées, le résultat est `block` et non une tentative de prédiction.

### 3. Scoring de candidats de recherche

L’IA peut classer des candidats de paramètres ou de stratégies après un backtest, mais elle doit lire le rapport complet : P&L net, frais, profit factor, drawdown, nombre de trades, période, nombre d’essais et résultat hors échantillon. La sélection finale doit rester déterministe : tout candidat qui ne respecte pas les seuils préenregistrés est rejeté, quel que soit le score IA.

### 4. Assistant documentaire sous contrôle

Un assistant de langage peut interroger Ibhextif et rédiger un résumé des résultats, localiser une régression, proposer une expérience ou générer une configuration candidate. Il ne reçoit jamais les clés API et ne peut appeler aucun endpoint d’ordre. Chaque recommandation devient un document de recherche, puis une exécution de backtest séparée et traçable.

## Contrat de sortie obligatoire

Chaque module IA doit produire un objet structuré, comparable et journalisable.

```json
{
  "candidate_id": "regime-v1-20260812",
  "decision": "filter_only",
  "regime": "trend_up",
  "confidence": 0.71,
  "feature_schema_version": "features-v1",
  "model_artifact_id": "sha256:...",
  "dataset_manifest_id": "sha256:...",
  "explanation": ["EMA slope positive", "ATR within allowed band"],
  "risk_override": false
}
```

Le champ `risk_override` doit toujours être `false`. Si une donnée obligatoire est absente, si la confiance est hors plage ou si le modèle ne correspond pas au schéma de features, la sortie devient `block`.

## Protocole de validation

| Étape | Exigence | Rejet automatique si |
|---|---|---|
| Dataset | Bougies confirmées, manifeste, checksum et période explicite | Gap, doublon, période inconnue ou mélange de sources non documenté |
| Train | Modèle et paramètres appris uniquement sur train | Le test est consulté pendant la sélection |
| Test | Paramètres gelés, frais et slippage déclarés | Le résultat est modifié après lecture du test |
| Walk-forward | Plusieurs splits chronologiques | Un seul split favorable est utilisé comme preuve |
| Paper | Journal de décision, P&L net, écart modèle/réalité | Les ordres paper ne correspondent pas au signal validé |
| Revue | Rapport Ibhextif avec limites et essais effectués | Absence de provenance ou explication incomplète |

Le risque de sélectionner un résultat favorable après de nombreux essais est bien documenté ; le protocole doit donc conserver le nombre de tests et exiger une validation hors échantillon. [4] [5]

## Plan de mise en œuvre

1. **Fondation de données.** Conserver les 12 datasets OKX, puis étendre les périodes sans remplacer les manifestes existants. Ajouter les colonnes de qualité et un schéma de features versionné.
2. **Baseline déterministe.** Garder le signal Elite ATR/TP et mesurer ses résultats par régime. Aucune IA tant que les métriques de base ne sont pas stables.
3. **Classifieur de régime V1.** Commencer par un modèle interprétable et une sortie `filter_only`. Le modèle n’écrit ni position, ni quantité, ni stop, ni take-profit.
4. **Quality gate V2.** Enrichir le validateur de datasets avec score de fraîcheur, gaps et cohérence inter-source.
5. **Assistant Ibhextif.** Permettre à l’IA de consulter les sources, rapports et contraintes pour suggérer des expériences ; imposer la création d’un ticket et d’un backtest séparé.
6. **Paper prolongé.** N’autoriser qu’un signal ayant passé les critères hors échantillon, avec journal intégral des raisons `allow`/`block`.

## Ce qui ne doit pas être fait

Ne pas relier un LLM, un classifieur ou un agent de reinforcement learning directement à `place_order`. Ne pas ajuster les seuils uniquement pour atteindre une cible de profit. Ne pas considérer un seul backtest positif comme preuve. Le RL est une piste de recherche nécessitant des contrôles supplémentaires contre le surajustement et n’est pas le premier composant à ajouter à TAFA. [6]

## Références

[1] [Freqtrade — documentation officielle](https://www.freqtrade.io/en/stable/)

[2] [Freqtrade — Backtesting](https://www.freqtrade.io/en/stable/backtesting/)

[3] [Hummingbot — documentation officielle](https://hummingbot.org/docs/)

[4] [Bailey et al. — Backtest Overfitting in Financial Markets](https://www.davidhbailey.com/dhbpapers/overfit-tools-at.pdf)

[5] [Arnott, Harvey et Markowitz — A Backtesting Protocol in the Era of Machine Learning](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3275654)

[6] [Gort et al. — Deep Reinforcement Learning for Cryptocurrency Trading](https://arxiv.org/abs/2209.05559)
