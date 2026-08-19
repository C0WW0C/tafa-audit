# Audit comparatif et correctifs — TAFA Ultimate / TAFA X Ultimate Elite

**Périmètre.** Cet audit compare le paquet historique `TAFA_ULTIMATE` transmis initialement avec `TAFA_X_ULTIMATE_FINAL`, puis documente les corrections appliquées dans le second paquet. L’analyse porte sur l’architecture logicielle, l’intégrité de la supervision, la cohérence des paramètres et les garde-fous opérationnels. Elle ne constitue ni une validation de stratégie, ni une preuve de performance, ni un conseil d’investissement.

> **Conclusion opérationnelle.** La base à conserver est **TAFA X Ultimate**, désormais livrée dans ce paquet sous une forme plus cohérente : le moteur V10 reste le point d’exécution, les paramètres sont contrôlés, le dashboard affiche leur périmètre réel, et un flux de supervision local remplace l’illusion d’un temps réel uniquement fondé sur du polling.

## Résumé exécutif

| Domaine | TAFA Ultimate historique | TAFA X avant correction | TAFA X Elite corrigé |
|---|---|---|---|
| Structure | Plusieurs variantes, dashboards et arborescences dupliqués | Architecture V10 plus rationalisée | V10 conservé ; couche de contrôle documentée et testée |
| Risque | Gestion du risque présente mais imports/versions difficiles à suivre | Gestionnaire canonique `risk/risk_manager.py` | Paramètres de risque bornés et appliqués à chaud |
| État du bot | Polling HTTP du dashboard | Polling HTTP + WebSocket marché séparé | Flux serveur **SSE** pour l’état bot + WebSocket OKX conservé pour les données marché |
| Paramètres UI | Grand nombre de contrôles affichés | Plusieurs paramètres enregistrés sans effet moteur complet | Seuls les paramètres validés et effectivement gérés sont exposés par le dashboard Elite |
| Surface de contrôle | Serveur exposé avec CORS permissif | Démarrage/arrêt/configuration accessibles sans protection | Écoute locale par défaut ; jeton requis hors boucle locale ; charge limitée ; traces internes non exposées |
| Dashboard | Interface legacy | Interface unique mais mélange de promesses et de télémétrie | Poste de supervision « Salle des marchés éditoriale », traçabilité des sources et alertes lisibles |

## Anomalies identifiées et correctifs appliqués

| Sévérité | Constat vérifiable | Correctif appliqué | Fichiers concernés |
|---|---|---|---|
| Élevée | Le serveur de contrôle écoutait sur toutes les interfaces et envoyait `Access-Control-Allow-Origin: *`, alors que des routes pouvaient démarrer, arrêter et reconfigurer le bot. | Écoute sur `127.0.0.1` par défaut ; un jeton `TAFA_DASHBOARD_TOKEN` est obligatoire lorsque l’écoute distante est explicitement choisie. Les en-têtes permissifs et l’exposition de traces ont été retirés. | `web/server.py` |
| Élevée | Le dashboard offrait des paramètres tels que watchlist, levier ou moteurs externes, sans garantie qu’ils pilotent le moteur actif. | Validation stricte des clés et plages, avec réponse explicite `accepted` / `rejected`. Le dashboard Elite ne présente plus ces fonctions comme disponibles. | `core/runtime_config.py`, `web/server.py`, dashboard Elite |
| Élevée | Le seuil de confiance pouvait diverger entre stratégie, quality gate et Neural Parent Brain. | Le seuil `min_conf` est propagé au gate, à la stratégie active et au contrôleur parent pour éviter les décisions contradictoires. | `core/engine_v10.py`, `core/runtime_config.py`, `core/engine.py` |
| Moyenne | Une modification de capital pouvait être affichée comme appliquée alors que le portefeuille papier avait déjà son propre état. | Le capital n’est réinitialisé que sans position ni trade ; sinon la valeur est marquée comme nécessitant un redémarrage, sans modifier silencieusement la comptabilité. | `core/engine_v10.py` |
| Moyenne | L’état dashboard était obtenu essentiellement par polling, tandis que le WebSocket OKX servait à la donnée marché uniquement. | Ajout de `/api/stream`, un flux **SSE** same-origin d’état bot. Le flux est lisible par navigateur et le dashboard bascule en lecture ponctuelle si nécessaire. | `web/server.py`, dashboard Elite |
| Moyenne | Le PID pouvait signaler à tort un bot si le système avait réattribué le même PID. | Vérification de la ligne de commande du processus sous Linux avant de déclarer le bot actif. | `web/server.py` |
| Moyenne | Les routes de sélection de moteurs externes faisaient référence à une intégration absente du paquet. | Les routes retournent maintenant `501` avec un message explicite au lieu d’une intégration ambiguë. | `web/server.py` |
| Faible | Lancement direct de `run_v10.py` ne garantissait pas l’exposition du dashboard. | Le lancement V10 démarre le dashboard local en tâche de fond lorsqu’il est disponible. | `run_v10.py`, `web/server.py` |

## Comparaison : quel bot retenir ?

Le terme « meilleur bot » ne peut pas être validé uniquement par l’architecture ou les fichiers fournis. La qualité d’un bot de marché dépend de tests hors échantillon, de coûts de transaction, de slippage, de disponibilité de données, de limites d’exécution et de contrôles de risque réels. Aucun élément du présent audit ne démontre une rentabilité future.

Pour **une base de développement et de supervision**, TAFA X Elite est préférable à TAFA Ultimate historique. Il simplifie la chaîne de risque, encapsule le moteur par un circuit breaker et un quality gate, limite la dérive des paramètres et rend l’état du système plus vérifiable. Il ne doit pas être comparé à un logiciel mature de trading comme s’il s’agissait d’un classement de rendement ; il s’agit d’une comparaison d’intégrité logicielle dans le périmètre de vos deux archives.

| Critère technique | TAFA Ultimate | TAFA X Elite | Appréciation |
|---|---|---|---|
| Cohérence des versions | Plusieurs sous-projets et pages web coexistants | Base V10 centralisée, contrôle des variations renforcé | Avantage TAFA X Elite |
| Décision algorithmique | Stratégie fusion et composants variés | Stratégie + parent brain + quality gate + circuit breaker | Avantage TAFA X Elite, sous réserve de validation hors échantillon |
| Maîtrise du risque | Modules présents, surface plus dispersée | Risque canonique, bornes de configuration, statut de circuit | Avantage TAFA X Elite |
| Observabilité | État HTTP et UI historiques | Flux d’état SSE, indicateur de fraîcheur, séparation bot/marché | Avantage TAFA X Elite |
| Paramétrage | Large surface d’options mais effets partiels | Surface volontairement réduite aux contrôles validés | Avantage TAFA X Elite pour la sûreté |
| Maturité de production | Non démontrée | Non démontrée | Égalité : validation requise |

## Architecture de supervision retenue

Le moteur utilise toujours le **WebSocket OKX** pour les mises à jour de marché. Le dashboard utilise un **flux SSE** pour la télémétrie du bot : c’est une connexion unidirectionnelle persistante mieux adaptée à la diffusion d’état du bot vers un navigateur. Le tableau ci-dessous précise ce que chaque canal fait réellement.

| Canal | Direction | Usage | État dans le paquet |
|---|---|---|---|
| WebSocket OKX | Marché → bot | Prix et chandeliers publics | Conservé |
| SSE `/api/stream` | Bot → dashboard | État, risque, cycle, performance, paramètres | Ajouté |
| HTTP `/api/config` | Dashboard → bot | Application de paramètres validés | Durci |
| HTTP `/api/start`, `/api/stop` | Dashboard → bot | Cycle de vie local | Durci |

> **Important.** Le flux SSE n’est pas présenté comme un WebSocket bidirectionnel : son rôle est la télémétrie d’état. Le WebSocket marché reste la source prix du bot. Si vous souhaitez ultérieurement une console multi-utilisateur ou une diffusion d’ordres distants, une authentification complète, TLS et un vrai serveur WebSocket dédié sont indispensables.

## Points restant à traiter avant tout usage réel

| Priorité | Action recommandée | Justification |
|---|---|---|
| Bloquante | Rester en `PAPER` / `DEMO` jusqu’à validation formelle. | Le paquet ne contient pas de démonstration robuste de résultat net de frais, de slippage et de pannes d’exécution. |
| Bloquante | Ne jamais exposer le port 8765 sur Internet sans proxy TLS, authentification forte, réseau restreint et gestion des secrets. | Un jeton simple réduit une exposition mais ne remplace pas une architecture d’accès sécurisée. |
| Élevée | Désactiver le warm-up synthétique pour un environnement de production et échouer explicitement si les données historiques manquent. | `core/engine.py` peut construire des bougies synthétiques lorsque les sources de warm-up sont indisponibles ; cela est utile en développement mais doit être traçable en production. |
| Élevée | Ajouter des tests d’intégration d’ordres, d’échecs réseau, de redémarrage et de reprise d’état. | Les cinq tests actuels couvrent le contrôle de configuration, le flux d’état et le parent brain, pas un cycle d’exécution réel avec exchange. |
| Moyenne | Isoler les secrets dans des variables d’environnement et journaliser les changements d’autorisation. | Les clés exchange ne doivent jamais être stockées dans les fichiers ou logs du projet. |
| Moyenne | Mettre en place une métrique de slippage, frais réels, latence et taux de rejet. | Ces éléments conditionnent la performance opérationnelle plus que les signaux seuls. |

## Validation réalisée

| Vérification | Résultat | Limite |
|---|---|---|
| `pytest -q` sur TAFA X Elite | **5 tests réussis** | Aucun appel à un exchange réel n’a été lancé. |
| Vérification TypeScript du dashboard | **Réussie** | Le dashboard hébergé n’est pas relié à un bot local lors de cette vérification. |
| Build du dashboard React | **Réussi** | Avertissement non bloquant : bundle JavaScript principal supérieur à 500 kB. |
| Revue visuelle du dashboard | **Effectuée** | La liaison réelle doit être validée sur l’ordinateur où le bot et le serveur local sont exécutés. |

## Fichiers principaux ajoutés ou modifiés

| Fichier | Rôle |
|---|---|
| `run_v10.py` | Démarre le dashboard local avec le moteur V10 et publie le mode effectif. |
| `web/server.py` | Serveur local durci, flux d’état SSE, contrôle tokenisé hors boucle locale. |
| `core/runtime_config.py` | Schéma de paramètres, bornes et application explicite. |
| `core/engine.py` / `core/engine_v10.py` | Propagation des paramètres vers la stratégie, gate et parent brain. |
| `web/index.html`, `web/assets/` | Dashboard Elite compilé et visuels intégrés. |
| `tests/test_runtime_dashboard.py` | Régression sur paramètres et flux SSE. |

## Avertissement

Ce paquet est fourni pour le développement, l’audit et le paper trading. Les marchés peuvent entraîner des pertes ; la présence d’un dashboard, d’un modèle ou de garde-fous ne supprime pas ce risque.

> **This is research and analysis only, not personalized financial advice.**
