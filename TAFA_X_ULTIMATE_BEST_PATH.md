# TAFA X Ultimate — chemin de consolidation recommandé

**Statut de release :** système de recherche **paper/demo OKX**, sans envoi d’ordre réel, sans clé privée et sans service de base de données externe activé par défaut.

> **Décision de socle.** TAFA Elite est la base de consolidation. TAFA CLEAN1 reste une source de correctifs à extraire puis tester unitairement. GOD GRID V8 est une référence d’ergonomie et de représentation des modes, non une base de code à fusionner. Cette décision maintient les protections Elite et évite de réintroduire des chemins d’ordre directs identifiés lors de l’audit statique.

## 1. Comparaison de maturité

| Axe | TAFA Elite corrigé | Freqtrade | Hummingbot | 3Commas | Écart TAFA et action sûre |
| --- | --- | --- | --- | --- | --- |
| Sécurité d’exécution | Launchers paper/demo, garde de release, tableau local durci | Le mode dry-run est explicite et les paramètres sont validés au démarrage.[1] | Les exécuteurs isolent le cycle d’une tâche de trading.[2] | La sécurité met l’accent sur clés sans droit de retrait et liste IP.[3] | Conserver le verrouillage paper ; ne jamais importer de routeur d’ordre depuis les archives auditées. |
| Persistance transactionnelle | SQLite legacy, JSONL et état JSON atomique ; suffisant pour le flux local | Objet `Trade` persistant et ordres associés, avec cycle de vie détaillé.[4] | Architecture modulaire ; le fournisseur de données est séparé des contrôleurs.[2] | Plateforme gérée, non un modèle de persistance réutilisable | Préparer un schéma relationnel `session → trade → order → risk_event` ; migration non exécutée dans cette release. |
| Données de marché | 12 datasets OKX validés ; OHLCV 5m/15m/1H/4H | Données, backtesting et frais configurables | Un unique fournisseur de marché pour bougies, carnet et transactions.[2] | Accès via intégrations d’exchange | Préparer TimescaleDB pour bougies et futures données L2 ; ne pas promettre de haute fréquence sans benchmark et donnée source adéquate. |
| IA et MLOps | Architecture IA `filter_only`, journal et protocoles walk-forward | FreqAI encadre la couche modèle | Modules séparables et contrôleurs testables | Offre gérée, logique interne non transférable | Versionner modèle, dataset, code et métriques ; le score IA n’est jamais l’autorité d’exécution. |
| Auditabilité | Journal append-only, status bridge, base Ibhextif, hashes de datasets | État de trade et d’ordre interrogeable | Événements et composants séparés | Contrôles de connexion et sécurité d’API | Ajouter les événements de risque, identifiants de session et empreintes de configuration au schéma cible. |

La comparaison ne mesure pas une rentabilité future. Elle décrit uniquement des capacités d’ingénierie et des pratiques de contrôle observables dans la documentation publique. Les backtests TAFA restent des résultats historiques dépendants de leurs données, frais et paramètres.

## 2. Architecture de données cible

La demande initiale distingue une base séries temporelles, PostgreSQL et Redis. Le chemin le plus cohérent est d’utiliser **TimescaleDB comme extension de PostgreSQL**, dans un cluster PostgreSQL administré, avec des schémas et droits séparés. TimescaleDB conserve les pilotes et le SQL PostgreSQL tout en ajoutant des tables partitionnées dans le temps, agrégats continus, compression et politiques de rétention.[5] Cette architecture évite d’introduire simultanément deux bases durables distinctes sans nécessité mesurée.

| Couche | Responsabilité | Source d’autorité | Données écrites | Règle de sûreté |
| --- | --- | --- | --- | --- |
| PostgreSQL `tafa` | Sessions, portefeuille paper, transactions, ordres simulés, événements de risque, audit | Oui | `sessions`, `trades`, `orders`, `risk_events` | Écriture transactionnelle ; mode contraint à `DEMO`. |
| TimescaleDB | Bougies et, ultérieurement, événements tick/carnet normalisés | Oui pour données de marché | `market_candles` hypertable | Horodatage UTC, fournisseur, instrument, granularité et fermeture de bougie obligatoires. |
| Redis | Cache reconstruisible de positions, limites et dernier état dashboard | **Non** | Clés de cache à TTL et flux d’interface | Jamais la seule vérité pour une position ni un événement de risque. Redis peut fonctionner sans persistance lorsqu’il est utilisé comme cache.[6] |
| Fichiers actuels | Compatibilité locale et release sans dépendance externe | Oui dans le profil local uniquement | SQLite, JSONL, JSON atomique | Défaut de la release actuelle, accès local mono-processus. |

Le dépôt contient désormais un contrat `core/storage_profile.py`. Par défaut, le profil `local` maintient SQLite, fichiers de marché et cache mémoire. Le profil `scaled` est un **contrat déclaratif** qui exige des URL PostgreSQL/TimescaleDB/Redis et refuse toute configuration qui ne reste pas strictement `DEMO` et `TAFA_PAPER_ONLY=true`. Aucune connexion distante n’est ouverte par cette couche et aucune migration n’est déclenchée implicitement.

La migration SQL préparée dans `migrations/001_tafa_postgres_timescale.sql` est idempotente et ne peut pas envoyer d’ordre. Elle crée les tables relationnelles et une hypertable de bougies, mais son exécution nécessite une revue d’exploitation, un environnement PostgreSQL dédié, des sauvegardes et un test de restauration.

## 3. Deux options de déploiement à valider avant migration externe

| Approche | Arbitrages | Coût | Complexité de mise en place |
| --- | --- | --- | --- |
| **A — release locale structurée** | Aucun service externe ; reproductible pour backtest, test et paper/demo local. Ne résout pas les écritures concurrentes à forte cadence. | Faible | Faible |
| **B — service persistant de données** | PostgreSQL avec TimescaleDB et Redis sépare durable, séries temporelles et cache ; nécessite supervision, sauvegardes, secrets, réseaux et procédures de restauration. | Infrastructure récurrente | Moyenne à élevée |

La release livrée conserve l’approche **A** et rend l’approche **B** prête à être provisionnée. Aucun déploiement externe n’a été effectué. Le choix de l’approche B doit être confirmé avant que des services persistants, des identifiants ou une automatisation soient configurés.

## 4. Latence, MLOps et sécurité : ordre de réalisation

Le moteur Python actuel convient au backtest, au dashboard et au paper/demo à la cadence actuelle. Réécrire immédiatement `exchange/` ou les coupe-circuits en Rust, C++ ou Go ferait porter un risque de régression supérieur au gain démontré. Le déclencheur de cette réécriture doit être une mesure : budget de latence, profilage, volume d’événements, contention et glissement simulé. Si la mesure le justifie, seul l’adaptateur de flux ou l’exécuteur simulé doit être isolé derrière un contrat d’événement versionné ; la décision de risque demeure déterministe et testée.

Pour MLOps, MLflow peut tracer des exécutions, versions, alias et métadonnées de modèles, en reliant une version de modèle à l’exécution et aux données qui l’ont produite.[7] La politique TAFA est plus restrictive : une dérive déclenche d’abord une alerte, un gel du modèle et une évaluation walk-forward ; aucun réentraînement ni changement de modèle automatique ne peut modifier les décisions sans validation explicite, résultat hors échantillon et journal de promotion.

La gestion des secrets ne doit pas reposer sur des fichiers versionnés. En cas de déploiement externe confirmé, un gestionnaire de secrets doit délivrer des identifiants de base temporaires et à droits minimaux. Vault documente précisément la génération et la révocation d’identifiants dynamiques, ce qui réduit leur fenêtre d’exposition.[8] Les clés d’exchange restent absentes de cette release ; si un jour elles sont autorisées par l’utilisateur, elles devront être limitées, sans droit de retrait et protégées par liste IP, conformément aux bonnes pratiques décrites par 3Commas.[3]

La conteneurisation et l’orchestration ne sont pas un prérequis pour la release paper/demo. Elles deviennent pertinentes seulement après le choix de l’approche B et lorsqu’un besoin démontré de processus 24/7, de reprise automatique, de haute disponibilité ou de charge dépasse l’environnement local.

## 5. Livrables ajoutés à cette release

| Livrable | Rôle |
| --- | --- |
| `core/storage_profile.py` | Contrat local/scaled fermé par défaut et interdit hors paper/demo. |
| `migrations/001_tafa_postgres_timescale.sql` | Schéma relationnel et séries temporelles de migration, non exécuté. |
| `tests/test_storage_profile.py` | Trois tests du défaut local, du refus hors paper/demo et du profil scaled déclaré. |
| `RESEARCH_BOT_ARCHITECTURE_COMPARISON.md` | Constats sourcés sur persistance Freqtrade et découplage Hummingbot. |
| `TAFA_X_ULTIMATE_BEST_PATH.md` | Présent document de consolidation, options d’exploitation et priorités. |

## Références

[1] [Freqtrade — Configuration, dry-run et validation](https://www.freqtrade.io/en/stable/configuration/)

[2] [Hummingbot — Architecture Strategy V2](https://hummingbot.org/strategies/v2-strategies/)

[3] [3Commas — Security et restrictions de clés API](https://3commas.io/security)

[4] [Freqtrade — Trade Object](https://www.freqtrade.io/en/stable/trade-object/)

[5] [Tiger Data — Documentation TimescaleDB](https://www.tigerdata.com/docs)

[6] [Redis — Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)

[7] [MLflow — Model Registry](https://mlflow.org/docs/latest/ml/model-registry/)

[8] [HashiCorp Vault — Static and Dynamic Secrets](https://developer.hashicorp.com/vault/tutorials/get-started/understand-static-dynamic-secrets)
