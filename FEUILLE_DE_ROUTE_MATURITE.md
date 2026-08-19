# Feuille de route de maturité fonctionnelle — TAFA X Elite

**Objectif.** Faire évoluer TAFA d’un bot personnalisé audité, adapté au paper trading, vers une plateforme d’exécution et de supervision plus mature. Cette feuille de route vise la **parité fonctionnelle progressive** avec les capacités documentées de Freqtrade, Hummingbot et 3Commas ; elle ne vise pas à reproduire leurs produits ni à promettre un rendement financier.

> **Règle de gouvernance :** aucun passage au live trading ne doit être traité comme la conséquence automatique d’un jalon logiciel. Chaque jalon doit être validé sur données contrôlées et environnement paper/dry-run avant tout élargissement du périmètre.

## Vision cible

| Référence fonctionnelle | Capacités à atteindre dans TAFA | Résultat attendu |
|---|---|---|
| Freqtrade | Recherche reproductible, données versionnées, backtests avec frais/slippage, dry-run, API de contrôle et rapports comparables | Une stratégie TAFA peut être évaluée, reproduite et comparée sans ambiguïté de jeu de données ou de paramètres. |
| Hummingbot | Abstraction exchange, connecteurs contractuels, multi-stratégie, multi-actif, gestion de portefeuille et résilience de flux | L’ajout d’un exchange ou d’un actif ne duplique pas les règles de risque ni l’état. |
| 3Commas | Configuration exploitable, modèles de bot, webhooks, gestion centralisée, parcours utilisateur et sécurité de contrôle | Un opérateur comprend les paramètres appliqués, les positions et les limites sans toucher au code. |

## Séquence obligatoire des jalons

| Jalon | Priorité | Dépend de | Finalité | État de sortie exigé |
|---|---:|---|---|---|
| M0 — Fondations et gouvernance | P0 | — | Stabiliser l’architecture réellement exécutée | Une seule chaîne engine/risk/execution/dashboard est documentée et testée. |
| M1 — Recherche reproductible | P0 | M0 | Atteindre le socle de validation de Freqtrade | Backtest hors échantillon rejouable, données/frais/slippage versionnés. |
| M2 — Exécution paper réaliste | P0 | M0, M1 | Séparer la stratégie de l’exécution et simuler les contraintes | Dry-run avec carnet, latence, rejets et frais simulés. |
| M3 — Portefeuille multi-actif | P1 | M1, M2 | Sortir du modèle mono-position/mono-symbole | État, risque et performance isolés par symbole et agrégés au niveau portefeuille. |
| M4 — Couche connecteurs | P1 | M2, M3 | S’inspirer de l’abstraction Hummingbot | Contrat de connecteur, tests de conformité et ajout d’un second exchange sans duplication. |
| M5 — Console opérateur et automatisation | P1 | M2, M3 | Se rapprocher de l’ergonomie 3Commas sans faux contrôles | API sécurisée, templates, webhooks, permissions et dashboard multi-bot. |
| M6 — Résilience et observabilité | P0 | M2 ; enrichi par M3–M5 | Exploitation durable, reprise et diagnostic | Métriques, alertes, reprise après panne et journal d’audit testés. |
| M7 — Industrialisation | P0 avant tout déploiement élargi | M0–M6 | Rendre chaque release vérifiable | CI, scans, migrations, sauvegardes, runbooks et release candidate contrôlée. |

## Backlog priorisé

### M0 — Fondations et gouvernance

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M0.1 | Déclarer une architecture canonique dans `ARCHITECTURE.md` : launcher, engine, stratégie, risque, routeur, état et dashboard. | Diagramme et table des modules actifs/inactifs. | Aucun import runtime ne pointe vers un module absent ou une version dupliquée. |
| M0.2 | Supprimer, archiver ou marquer explicitement les shims, dashboards et moteurs obsolètes. | Rapport de nettoyage avec politique de dépréciation. | Une recherche de code ne trouve pas deux singletons de risque ou deux chemins d’exécution actifs. |
| M0.3 | Introduire des modèles typés pour `Signal`, `OrderIntent`, `OrderResult`, `Position`, `PortfolioSnapshot` et `BotStatus`. | Module de modèles et tests de sérialisation. | Le dashboard et le journal lisent le même schéma versionné. |
| M0.4 | Centraliser toutes les constantes et variables runtime dans une configuration versionnée avec schéma. | `config_schema` + migration de configuration. | Chaque paramètre est identifié comme `hot`, `restart_required` ou `unsupported`. |
| M0.5 | Mettre en place une politique de secrets. | `.env.example`, validation de démarrage et liste d’exclusions. | Aucun secret, token ou clé privée ne figure dans un ZIP, log ou réponse API. |

### M1 — Recherche reproductible et validation de stratégie

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M1.1 | Construire un catalogue de données OHLCV versionné par exchange, symbole, timeframe, fuseau, source et checksum. | Manifest de datasets et chargeur déterministe. | Une même exécution relit le même jeu de données sans téléchargement implicite. |
| M1.2 | Désactiver le warm-up synthétique en profil de validation ou le rendre visible comme état bloquant. | Politique `data_required` et test associé. | Un backtest/validation échoue explicitement si les données nécessaires manquent. |
| M1.3 | Créer un moteur de backtest event-driven commun à la stratégie et au dry-run. | Interface `MarketEvent → Signal → OrderIntent → Fill`. | Les règles d’entrée/sortie ne sont pas réimplémentées différemment selon le mode. |
| M1.4 | Intégrer frais, spread, slippage, taille minimale, précision, partial fills et délai d’exécution configurables. | Modèle de coût et scénarios unitaires. | Le rapport indique chaque hypothèse et les P&L bruts/net de coûts. |
| M1.5 | Imposer un protocole train/validation/test temporel, avec analyse walk-forward et tests de look-ahead. | Commande de validation et rapport de fuite de données. | Aucun score de sélection ne lit des prix ou labels futurs. |
| M1.6 | Générer un rapport de backtest versionné : dataset, commit, stratégie, paramètres, seeds, métriques, trades et graphiques. | `backtest_report.json` + Markdown. | Un tiers peut reproduire le résultat à partir du manifeste. |
| M1.7 | Ajouter un registre de stratégies et d’expériences. | Base SQLite ou fichiers versionnés. | Une stratégie déployée référence un identifiant d’expérience validée. |

### M2 — Exécution paper réaliste et contrôle d’ordres

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M2.1 | Introduire l’objet `OrderIntent` comme seule sortie autorisée de la stratégie. | Routeur d’ordres typé. | Une stratégie ne peut pas appeler un client exchange directement. |
| M2.2 | Créer un simulateur paper basé sur les événements et non sur un prix unique. | Moteur de fills simulés. | Le simulateur produit fill, rejet, délai et P&L cohérents avec les paramètres de marché. |
| M2.3 | Mettre en place des états d’ordre complets : `created`, `submitted`, `accepted`, `partial`, `filled`, `cancelled`, `rejected`, `expired`. | Machine à états et journal d’ordre. | Toutes les transitions invalides échouent en test. |
| M2.4 | Ajouter une idempotence de soumission et une clé de corrélation cycle/ordre. | Identifiants d’exécution et tests de reprise. | Un redémarrage ne duplique pas un ordre paper ou live. |
| M2.5 | Réconcilier périodiquement les positions, ordres et solde avec la source exchange en dry-run/live. | Service de réconciliation. | Toute divergence crée une alerte et bloque les nouveaux ordres selon une politique explicite. |
| M2.6 | Implémenter un kill switch global et par stratégie/symbole. | Commande protégée et invariants de blocage. | Après activation, aucun nouvel `OrderIntent` n’atteint le routeur. |

### M3 — Portefeuille multi-actif et risque transversal

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M3.1 | Remplacer le portefeuille mono-position par une vue portefeuille, comptes et positions par symbole. | `PortfolioService` et schéma de snapshot. | Plusieurs positions peuvent coexister sans partager des champs mutables globaux. |
| M3.2 | Mettre en place des budgets de risque par symbole, stratégie, secteur/exchange et portefeuille. | Moteur de limites hiérarchiques. | Toute intention excédant une limite reçoit un motif de rejet exploitable. |
| M3.3 | Ajouter des limites de concentration, nombre de positions, exposition nominale et corrélation. | Politique de portefeuille. | Les limites sont vérifiées avant routing et publiées au dashboard. |
| M3.4 | Agréger P&L, drawdown, frais, slippage et performance par position puis portefeuille. | Calculateur de performance. | Les totaux dashboard égalent la somme des événements enregistrés. |
| M3.5 | Introduire une watchlist réelle, avec cycle et état isolé par symbole. | Orchestrateur multi-symbole. | Ajouter/retirer un symbole ne requiert pas de changer le code de stratégie. |

### M4 — Abstraction exchange et connecteurs

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M4.1 | Définir un contrat minimal `ExchangeConnector` pour métadonnées, prix, OHLCV, ordres, annulation, positions et solde. | Interface formelle et tests de contrat. | Le moteur ne dépend plus des types spécifiques à OKX. |
| M4.2 | Encapsuler OKX derrière ce contrat sans changement fonctionnel. | Connecteur OKX testé. | Le test de conformité passe en paper/sandbox. |
| M4.3 | Ajouter un deuxième connecteur au choix, en priorité une source avec sandbox compatible. | Connecteur secondaire. | La même stratégie paper fonctionne avec les deux connecteurs via la même interface. |
| M4.4 | Normaliser symboles, précision, min-notional, fuseaux et statuts d’ordre. | Adaptateurs et catalogues de marché. | Les erreurs de format sont rejetées avant l’envoi d’un ordre. |
| M4.5 | Distinguer clairement données REST, flux WebSocket et télémétrie bot. | Gestionnaire de flux avec politiques de reconnexion. | Chaque canal possède disponibilité, âge de donnée et métrique propres. |

### M5 — Console opérateur, automatisation et expérience produit

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M5.1 | Passer d’un token simple à une authentification utilisateur, rôles et permissions de commande. | RBAC, sessions et journal d’accès. | Un lecteur ne peut pas démarrer, arrêter ou modifier une stratégie. |
| M5.2 | Créer un registre de bots, stratégies et templates de configuration. | Bibliothèque de templates versionnés. | Un template cloné conserve son origine, sa version et ses paramètres modifiés. |
| M5.3 | Ajouter une gestion multi-bot : états, versions, budgets et isolation de processus. | Orchestrateur et écran portefeuille. | L’arrêt d’un bot n’interrompt ni ne modifie un autre bot. |
| M5.4 | Intégrer des webhooks entrants et sortants authentifiés. | Schéma d’événements, signatures et essais de livraison. | Un signal reçu est validé, journalisé, idempotent et soumis aux mêmes règles de risque. |
| M5.5 | Ajouter notifications à seuil : données périmées, circuit breaker, divergence de réconciliation, limite de risque, incident de connecteur. | Centre de notifications. | Chaque alerte comporte horodatage, contexte, gravité et accusé de réception. |
| M5.6 | Ajouter un journal d’activité filtrable. | Timeline UI et API d’audit. | Une décision peut être remontée du signal à l’ordre/fill avec les paramètres effectifs. |

### M6 — Résilience, observabilité et sécurité

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M6.1 | Exporter métriques de disponibilité, délai de données, latence de cycle, rejets, fills, frais, slippage et exposition. | Endpoint de métriques et tableaux de bord opérationnels. | Les métriques différencient au moins moteur, connecteur et dashboard. |
| M6.2 | Définir une politique de reconnexion avec backoff, limites et état dégradé. | Gestionnaire de reprise WebSocket/REST. | Une perte de flux n’entraîne ni boucle serrée ni ordre aveugle. |
| M6.3 | Mettre en place snapshots transactionnels et reprise contrôlée après crash. | Journal append-only et restaurateur. | Un redémarrage rejoue l’état sans dupliquer position, ordre ni P&L. |
| M6.4 | Mettre des limites de débit, validation de schéma et protection anti-rejeu sur les endpoints de contrôle. | Middleware sécurité et tests. | Les routes de mutation refusent les requêtes expirées, non signées ou répétées. |
| M6.5 | Produire une procédure d’incident et un exercice de panne. | Runbook incident et rapport d’exercice. | Une simulation couvre au moins perte WebSocket, rejet d’ordre et divergence de solde. |

### M7 — Industrialisation et release

| ID | Tâche à accomplir | Livrable | Critère d’acceptation |
|---|---|---|---|
| M7.1 | Créer une CI avec formatage, analyse statique, tests unitaires, tests de contrat et build dashboard. | Pipeline CI. | Une pull request ne peut être fusionnée si les contrôles échouent. |
| M7.2 | Mettre en place tests de non-régression avec datasets figés et contrats exchange mockés. | Suite de tests déterministe. | Les résultats de validation sont stables entre deux exécutions. |
| M7.3 | Versionner schémas, migrations et compatibilité des configurations. | Politique semver et migrations. | Un upgrade ne corrompt pas l’état ni les configurations précédentes. |
| M7.4 | Automatiser la création de release : SBOM, checksums, archive sans secrets, notes et rollback. | Processus de packaging. | Le ZIP se vérifie, se déploie en environnement propre et se restaure. |
| M7.5 | Définir une grille de passage paper → dry-run prolongé → pilote restreint. | Comité de release et métriques de décision. | Chaque passage exige des preuves de fiabilité, pas une performance ponctuelle. |

## Ordre de démarrage recommandé

| Étape immédiate | Pourquoi elle passe avant les autres | Dépendances |
|---|---|---|
| 1. M0.1 à M0.5 | Évite de construire multi-actif ou UI sur des modules dupliqués, une configuration ambiguë ou des secrets fragiles. | Aucune |
| 2. M1.1 à M1.6 | Rend toute amélioration de stratégie mesurable et reproductible. | M0 |
| 3. M2.1 à M2.6 + M6.1 à M6.3 | Réduit le risque d’une simulation irréaliste et rend les incidents observables. | M0, M1 |
| 4. M3.1 à M3.5 | Ajoute le portefeuille réel avant la watchlist et les promesses multi-actifs. | M1, M2 |
| 5. M4.1 à M4.5 | Étend les venues seulement après avoir stabilisé l’état, le risque et les ordres. | M2, M3 |
| 6. M5.1 à M5.6 puis M7 | Ouvre une expérience produit et une exploitation multi-bot lorsque le cœur est testable. | M2–M6 |

## Indicateurs de préparation par jalon

| Domaine | Mesure de préparation | Seuil de sortie indicatif |
|---|---|---|
| Recherche | Reproductibilité de la validation | 100 % des rapports contiennent commit, dataset checksum, frais, slippage et paramètres. |
| Exécution | Couverture des transitions d’ordres | Toutes les transitions d’ordre et reprises après crash sont testées. |
| Risque | Explicabilité des refus | Chaque ordre refusé possède un code et un motif persistés. |
| Données | Intégrité de flux | L’âge de prix, les pertes de flux et les reconnexions sont mesurés par connecteur. |
| Sécurité | Surface de mutation | Toutes les mutations sont authentifiées, autorisées, auditées et limitées. |
| Produit | Véracité UI | 100 % des contrôles visibles sont appliqués, marqués restart-required ou indisponibles. |

## Ce qui ne doit pas être fait trop tôt

| Tentation | Risque | Précondition |
|---|---|---|
| Ajouter dix exchanges | Duplique les bugs et fragilise l’exécution. | Contrat connecteur + suite de conformité validés. |
| Ajouter une IA plus complexe | Masque les fuites de données et l’absence de protocole de validation. | M1 terminé. |
| Ouvrir le dashboard sur Internet | Expose des commandes de trading sans sécurité et audit suffisants. | M5.1 et M6.4 terminés, HTTPS et réseau restreint. |
| Vendre/copier des stratégies | Crée des risques de conformité, de sécurité et d’interprétation de performance. | Gouvernance, expérimentations reproductibles et validation juridique adaptée. |
| Passer au live | Un bon backtest ou une belle interface ne suffit pas. | M1, M2, M6 et M7 validés ; décision humaine distincte. |

## Références fonctionnelles

La liste est alignée sur les capacités décrites dans les documentations officielles de Freqtrade, Hummingbot et 3Commas à la date de référence du rapport de comparaison. [1] [2] [3]

> **This is research and analysis only, not personalized financial advice.**

## Références

[1]: https://www.freqtrade.io/en/stable/ "Freqtrade — documentation officielle"
[2]: https://hummingbot.org/docs/ "Hummingbot — documentation officielle"
[3]: https://3commas.io/dca-bots "3Commas DCA Bot — page officielle"
