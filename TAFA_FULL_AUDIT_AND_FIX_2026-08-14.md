# Audit complet et correctifs — TAFA X Ultimate Control Panel

**Date :** 14 août 2026.  
**Archive auditée :** `TAFA_X_ULTIMATE_CONTROL_PANEL_CORRECTED.zip`.  
**Périmètre :** intégrité ZIP, code Python, configuration, runtime, données OHLCV, registre IBHExTIF, dashboard statique, routes API, tests de régression et hygiène de distribution.  
**Limite :** l’audit est technique et de recherche ; il ne constitue ni une validation de performance ni une recommandation financière.

## Synthèse

L’archive est cohérente pour un usage **PAPER/DEMO local**. Le profil Elite impose le mode DEMO, désactive `ENABLE_LIVE`, vide la phrase de confirmation et fixe un portefeuille PAPER local. Les contrôles d’exécution bloquent les appels de lancement, d’arrêt, de sélection de moteur et de soumission d’ordre depuis le dashboard.

Trois incohérences de dashboard et de tests ont été détectées puis corrigées. La correction la plus importante rend désormais visible dans l’interface le détail des clés runtime refusées par l’API plutôt que de présenter une erreur générique quand le serveur retourne un statut `422`. La suite de tests s’exécute désormais intégralement : **47 tests réussis** en environnement DEMO sans identifiants exchange.

| Domaine | État après audit | Commentaire |
|---|---|---|
| Intégrité d’archive | Validée | ZIP extrait sans erreur ; aucun chemin non sûr ni entrée chiffrée dans l’audit statique. |
| Syntaxe et tests | Validés | 47 tests Python et le contrôle JavaScript du dashboard réussissent. |
| Dashboard/API | Corrigé | Réponse `422` lisible, contrat de dashboard statique aligné et routes vérifiées. |
| Séparation d’exécution | Préservée | Les routes de démarrage, moteur et ordre renvoient `403`. |
| Données OHLCV | Validées | 12 datasets locaux valides ; manifeste dédié à l’audit produit. |
| Base IBHExTIF | Validée | 7 sources, 42 documents, 6 concepts, 1 stratégie et 4 backtests cohérents. |

## Inventaire et architecture observée

L’archive contient 162 modules Python, 21 fichiers de test et 12 rapports. Le moteur est organisé autour de `core`, `trading`, `risk`, `exchange`, `ai`, `backtesting` et `web`. Le serveur local `web/server.py` expose une surface d’observation, de télémétrie et de configuration runtime sur `127.0.0.1:8765` par défaut.

La configuration générique conserve une triple porte LIVE : `ENABLE_LIVE=true`, `TAFA_MODE=LIVE`, la phrase `LIVE_CONFIRM=I_UNDERSTAND_THE_RISK` et les trois identifiants OKX doivent tous être présents avant que `PAPER_TRADING` puisse devenir faux. Le profil `run_elite_final_paper.py` écrase cette possibilité en définissant DEMO, `ENABLE_LIVE=false`, `LIVE_CONFIRM=""` et un capital local de 500 USDC.

> Le chemin générique `run_v10.py` doit rester réservé à une exploitation consciente de ses variables d’environnement. Le lanceur Elite PAPER demeure le chemin approprié pour les validations non réelles.

## Constats, correctifs et preuves

| ID | Constat initial | Correctif appliqué | Vérification |
|---|---|---|---|
| DASH-01 | `postJSON()` jetait toute réponse non 2xx avant lecture du JSON. Une configuration partiellement rejetée par l’API (`422`) devenait un simple `config fail`. | Le client lit maintenant le JSON, traite `422` comme une réponse de configuration et affiche chaque clé refusée avec son motif. | Nouveau test `test_dashboard_config_feedback.py` ; suite Python réussie. |
| DASH-02 | Deux tests attendaient un ancien bundle React/module alors que le dashboard actuel est statique et charge `vendor/chart.umd.min.js`. | Les tests vérifient désormais la page Spectral Observatory et l’asset Chart.js réel, sans dépendance à un bundle obsolète. | `tests/test_runtime_dashboard.py` réussit intégralement. |
| DASH-03 | Le test de console manuelle attendait un `202` pour `/api/paper/order`, alors que le serveur et la politique de dashboard renvoient `403`. | Le test est aligné sur le contrat non exécutable : la route est refusée et aucune demande n’est mise en file. | `tests/test_manual_paper_console.py` réussit dans la suite complète. |
| API-01 | Le contrat des routes n’était pas vérifié sur un serveur de cette archive après les changements HTML. | Vérification isolée des endpoints d’état, configuration, marché, performance, observabilité, modèles, journaux et ordres manuels. | Tous les GET contrôlés répondent ; `422` pour clé hors borne, `403` pour démarrage et ordre. |
| DATA-01 | Le statut des datasets locaux n’était pas reconfirmé lors de l’audit. | Exécution du validateur déterministe avec sortie séparée `reports/audit_dataset_manifest_20260814.json`. | 12 datasets valides sur 12. |
| PKG-01 | L’archive contenait des caches Python générés pendant les validations. | Les caches `__pycache__`, `.pyc`, `.pyo` et `.pytest_cache` sont retirés avant distribution finale. | Contrôle d’intégrité ZIP final à effectuer après empaquetage. |

## Liaison dashboard et API

Le dashboard appelle les routes locales `/api/status`, `/api/config`, `/api/observability`, `/api/logs`, `/api/market/book`, `/api/performance/summary`, `/api/models/status` et `/api/manual-orders`. Le serveur renvoie des objets JSON pour ces surfaces de lecture. Les réponses de configuration utilisent `200` lorsque toutes les clés sont acceptées et `422` lorsqu’au moins une clé est hors contrat ; le dashboard expose désormais ce second cas avec le détail des refus.

Les routes `/api/bot/start`, `/api/bot/stop`, `/api/engine/select` et `/api/paper/order` restent explicitement refusées avec `403`. Cette séparation évite que la couche de navigateur puisse modifier l’état du processus ou former un ordre ; elle est cohérente avec la surface actuelle de configuration et d’observabilité.

## Configuration et contrôle de risque

Le contrat runtime accepte uniquement des paramètres bornés : capital, risque par trade, stop-loss, ratio de take-profit, trailing, moyenne mobile, RSI, confirmation, pente, volume et paramètres IA encadrés. Le runtime impose notamment un risque par trade de 0,01 % à 5 %, un levier fixé à 1 pour le moteur spot PAPER et une seule position ouverte.

Les paramètres Grid/DCA visibles dans la configuration historique ne sont pas tous des clés runtime appliquées par ce moteur. Ils ne doivent pas être présentés comme des réglages actifs tant qu’une matrice explicite « champ dashboard → clé runtime → composant moteur → preuve de prise en compte » n’est pas maintenue.

## Données et limites de validation de stratégie

Le validateur a confirmé la structure OHLCV de 12 datasets locaux. La présence de données valides ne démontre toutefois pas la robustesse d’une stratégie. Les rapports de walk-forward présents doivent être interprétés avec leurs hypothèses de période, frais, échantillonnage, faible nombre de transactions et sensibilité aux paramètres.

Les étapes recommandées avant toute conclusion de maturité sont : allonger la période historique, intégrer un modèle de glissement et de liquidité, préserver les empreintes de datasets, imposer un nombre minimal de transactions hors-échantillon et séparer les jeux de validation chronologiquement.

## Sécurité et hygiène de distribution

L’audit statique passif de l’archive originale a analysé 162 sources Python. Il n’a détecté ni entrée ZIP chiffrée ni chemin d’archive non sûr. Sept artefacts runtime étaient présents : base SQLite, journaux et caches ; les caches compilés seront retirés de l’archive finale. Les cinq fichiers `.env*` restants sont des exemples et aucun motif d’identifiant OKX non vide n’y a été trouvé.

Les journaux sont redacted côté API pour les motifs de clé et de passphrase. Aucun secret n’a été affiché ou utilisé durant les contrôles.

## Tests exécutés

| Contrôle | Résultat |
|---|---:|
| Test d’intégrité de l’archive reçue | Réussi |
| Suite Python complète en DEMO sans clés | 47 réussis |
| Contrôle JavaScript `check_spectral_dashboard.js` | Réussi |
| Compilation de `web/server.py` et `core/runtime_config.py` | Réussie |
| Contrat API local isolé | Réussi |
| Validation datasets OHLCV | 12 / 12 valides |
| Validation IBHExTIF | Réussie : 7 / 42 / 6 / 1 / 4 |

## Risques résiduels et prochaines validations

| Priorité | Risque résiduel | Action de validation |
|---|---|---|
| Élevée | Évidence de stratégie insuffisante pour inférer une robustesse économique | Walk-forward étendu avec frais, glissement, stress de marché et seuil de preuves hors-échantillon. |
| Élevée | Le lanceur générique peut devenir LIVE si toutes les portes sont satisfaites | Préserver le profil PAPER pour la recherche et auditer l’environnement avant tout lancement générique. |
| Moyenne | Risque de divergence future entre champs dashboard et clés runtime | Ajouter une matrice de liaison et un test de contrat automatique. |
| Moyenne | Journaux locaux potentiellement sensibles au contexte d’exploitation | Définir rétention, rotation et test de redaction systématique. |

## Références internes

1. `config.py` — mode, paramètres de risque et triple porte LIVE.
2. `core/runtime_config.py` — clés runtime supportées, bornes et application.
3. `web/index.html` et `web/server.py` — dashboard et routes API.
4. `tests/test_runtime_dashboard.py`, `tests/test_manual_paper_console.py`, `tests/test_dashboard_config_feedback.py` — contrats de régression.
5. `scripts/validate_market_datasets.py` et `reports/audit_dataset_manifest_20260814.json` — validation OHLCV.
6. `scripts/validate_ibhextif_knowledge.py` — intégrité du registre de connaissances.
7. `reports/audit_received_archive_static.json` — audit passif de l’archive reçue.
