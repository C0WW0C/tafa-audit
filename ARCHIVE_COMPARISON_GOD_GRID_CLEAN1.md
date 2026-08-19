# Comparaison d’archives — GOD GRID V8, TAFA CLEAN1 et TAFA Elite

## Périmètre de l’audit

L’analyse est statique : les archives ont été extraites dans des répertoires isolés, leurs sources, documents et scripts ont été examinés sans exécuter le code importé. Les conclusions portent sur la structure, les chemins d’ordre, les garde-fous visibles et la compatibilité avec la base Elite actuelle.

| Élément | GOD GRID V8 | TAFA CLEAN1 | TAFA Elite actuel |
|---|---|---|---|
| Structure | Pack compact centré sur quelques scripts Python | Projet large avec moteur, risque, exchange, backtests et web | Base consolidée avec releases M7/Elite, datasets validés et registre Ibhextif |
| Tests visibles | Aucun test dédié identifié au premier inventaire | Tests présents, mais non exécutés car le pack est importé et non audité en profondeur | 20 tests exécutés et validés dans le projet de travail |
| Mode par défaut déclaré | Paper | Demo, paper par défaut ; live triple-gated | Paper/demo forcé par launchers dédiés |
| Chemin d’ordre | Ordre limite spot OKX Demo intégré au module dashboard | Méthodes `place_order` et chemin d’ordre manuel depuis le dashboard | Paper/demo avec séparation des release gates et du backtest |
| Données et backtests | Archive de données et outil imbriqué non inspectés | Modules de backtest existants | 12 datasets OKX validés, manifestes et walk-forward multi-datasets |
| État des artefacts | Faible volume | 1 887 fichiers, dont venv, logs, cache, DB et runtime | Artefacts source et résultats versionnés, dépendances exclues des packages propres |

## Points utiles identifiés

GOD GRID V8 apporte une représentation claire de trois modes (`paper`, `okx_demo_dryrun`, `okx_demo_orders`), des ordres limite spot cash et un affichage local dense. La méthode visible utilise `tdMode=cash` et ne montre pas de levier sur ce chemin. Sa valeur principale est donc une **référence d’interface de supervision et de séparation de modes**, pas un module à copier tel quel.

TAFA CLEAN1 présente la meilleure proximité structurelle avec Elite : moteur V10, `runtime_config`, `status_bridge`, gestionnaires de risque, journalisation, performance, backtesting et dashboard. Son fichier de configuration force le paper sauf si `TAFA_MODE=LIVE`, `ENABLE_LIVE=true` et une confirmation explicite sont présents. Les corrections listées dans `AUDIT_FIXES.md` sont des pistes de revue pertinentes, notamment sur SL/TP, reset de pertes journalières, retour de stratégie et chemins de base.

## Risques d’intégration

| Niveau | Constat | Conséquence | Décision |
|---|---|---|---|
| Élevé | GOD GRID peut atteindre directement `/api/v5/trade/order` en mode `okx_demo_orders`. | Un import de son dashboard peut réintroduire un chemin d’ordre non protégé par les release gates Elite. | Ne pas importer le routeur d’ordre ni les endpoints de changement de mode. |
| Élevé | CLEAN1 traite des fichiers de commande dashboard et appelle `engine.trader.execute` dans `run.py`. | L’ordre manuel doit être vérifié contre le mode actif à l’endroit même de l’exécution. | Ne pas importer ce mécanisme ; préserver la séparation Elite. |
| Élevé | CLEAN1 inclut un `venv`, logs, PID, DB SQLite et journaux runtime. | Risque de pollution, secrets, état périmé ou incompatibilités. | Exclure intégralement de toute fusion. |
| Moyen | Le serveur CLEAN1 manipule des processus et contient un chemin Windows `taskkill ... shell=True`. | Comportement dépendant de l’OS et surface d’administration inutile. | Ne pas reprendre ce serveur ; conserver le serveur Elite durci. |
| Moyen | Le pack GOD GRID n’expose pas de suite de tests visible. | Aucune assurance de non-régression avant intégration. | Extraire une fonction à la fois et écrire les tests Elite avant usage. |
| Faible | Les paramètres CLEAN1 diffèrent du profil Elite : capital initial 1 000, timeframe 4H, ordre 100 USDC. | Incohérence de recherche avec le profil Elite 500 USDC / datasets multi-timeframes. | Traiter ces valeurs comme paramètres externes, non comme nouveaux défauts. |

## Plan de fusion sécurisé

La fusion recommandée est sélective et s’effectue dans l’ordre suivant.

| Priorité | Composant candidat | Source | Action requise avant intégration | Statut recommandé |
|---:|---|---|---|---|
| P1 | Garde qualité, analytics et journal de trade | CLEAN1 `core/` | Lire les dépendances, écrire des tests unitaires Elite et brancher sur le status bridge existant. | À évaluer module par module |
| P1 | Correctifs SL/TP et reset journalier | CLEAN1 `risk/`, `AUDIT_FIXES.md` | Reproduire les tests de pourcentages et le test de reset UTC dans Elite. | À porter sous forme de tests d’abord |
| P2 | Rendu dashboard de modes et états | GOD GRID | Recréer uniquement les éléments UI dans Elite ; aucune copie des appels privés, clés ou endpoints d’ordre. | Inspiration visuelle seulement |
| P2 | Règles d’instrument spot | GOD GRID | Isoler en composant pur, tester tick/lot/minNotional avec données publiques OKX. | À extraire après tests |
| P3 | Cerveau IA local et outil imbriqué | GOD GRID | Nécessite audit de dépendances, licence, modèles et comportement hors ligne. | Bloqué en attente d’audit explicite |

## Décision

La base **TAFA Elite reste le socle de référence**. TAFA CLEAN1 est la source la plus exploitable pour des modules de contrôle et de qualité, après extraction et tests. GOD GRID V8 doit rester une source d’inspiration pour la présentation des modes et une éventuelle future couche d’instrumentation spot. Aucune fusion automatique n’est recommandée, et aucun code importé des archives n’a été exécuté.

> Le système reste en paper/demo. Les résultats de backtest ou les garde-fous de code ne constituent pas une validation de performance ni d’exécution réelle.
