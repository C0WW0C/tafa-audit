# Audit statique Ibhextif — artefacts externes TAFA

**Date d’audit :** 12 août 2026  
**Cible :** TAFA X Ultimate Elite, **paper/demo OKX uniquement**  
**Méthode :** lecture de métadonnées, calcul SHA-256, analyse syntaxique Python par AST, lecture passive d’un ZIP et inspection binaire sans désérialisation. Aucun script fourni n’a été importé, lancé ou fusionné. Aucun modèle PKL n’a été chargé.

> **Décision de sécurité.** Les fichiers fournis sont des sources candidates de connaissances et de correctifs, non des dépendances de confiance. La base TAFA Elite reste le seul socle exécutable validé. Aucun artefact externe n’est importé dans le chemin de trading, de risque ou de dashboard.

## 1. Inventaire et intégrité

| Artefact | Taille | SHA-256 | Nature constatée | Statut |
| --- | ---: | --- | --- | --- |
| `tafa_god_v2_model.pkl` | 389 822 o | `2e5d3f6209d2cef1e273bc1efb443a302e168a96d44e1240b2a81181af52bf95` | Pickle protocole 5, marqueurs `sklearn`, `HistGradientBoosting`, `numpy` | **Quarantaine** : non chargé. |
| `TAFA_PARENT_OKX_FUSION_V6_1_SELF_CROSS_GUARD.py` | 225 988 o | `bb832b2700151d0d398fda8fdbe5e2015bf4aa4c9783118b75f9592c90694f13` | Script Python, syntaxe analysable | Référence de garde seulement. |
| `TAFA_PARENT_OKX_FUSION_V6_1_CANCEL_LOOP_GUARD.py` | 216 049 o | `8fc9d733760f4775514a154da85c396ae004221b2a23b8f9553a301cc66ac17e` | Script Python, syntaxe analysable | Référence de garde seulement. |
| `TAFA_PARENT_OKX_FUSION_V6_2_BEST_FUSION_PARENT_BUS.py` | 216 533 o | `afdd6bfb1e7996073278fb902d313d33e7b70402d24cfb0562c94638aaeff735` | Script Python, syntaxe analysable | Référence de bus parental seulement. |
| `FUSION_ULTIMATE_V7.py` | 210 593 o | `81017e22a197f2c32635efe6605e8709bb1e49ffa98a791b2581ac3a6974ecb4` | Script Python, syntaxe analysable | Référence ML et stratégie seulement. |
| `tafagpt.zip` | 5 547 767 o | `fee31c09b00f3d557cc6cf4e3d980873522427e0023f47dabcdab6f833e32806` | Archive ZIP non chiffrée, 1 267 entrées | **Non intégrable telle quelle**. |

## 2. Constats critiques

| Priorité | Constat vérifié | Risque pour X Ultimate | Décision de correction |
| --- | --- | --- | --- |
| P0 | Les scripts Fusion contiennent un client REST privé OKX et les routes `/api/v5/trade/order`, `/api/v5/trade/cancel-order`, `/api/v5/trade/orders-pending` et `/api/v5/trade/fills`. Le mode `okx_demo_orders` existe. | Un import direct réintroduirait des chemins de soumission/cancellation hors des release gates Elite. | Ne pas importer le client, le routeur ou les endpoints d’ordre. Conserver uniquement le paper broker Elite. |
| P0 | L’archive `tafagpt.zip` contient `.env`, un environnement virtuel, de nombreux caches et artefacts runtime. L’analyse a relevé 1 133 entrées runtime sur 1 267. | Une fusion ou un packaging direct peut propager secrets, dépendances opaques et états périmés. | Ne jamais extraire dans le dépôt Elite ; ne conserver que le manifeste, les empreintes et des extraits relus. |
| P0 | `tafagpt/Trading/live_switch.py` active l’état live par simple méthode `enable_live()`. `security.py` accepte `ENABLE_LIVE=true` comme garde suffisante. | Garde insuffisante par rapport au verrou paper/demo d’Elite. | Ne pas porter ces modules. Toute évolution doit garder le verrou multi-conditions Elite et le refus par défaut. |
| P1 | L’audit AST trouve trois erreurs de syntaxe dans l’archive : `AI/model_training_pipeline.py:75`, `config/environment_manager.py:96` et `Trading/strategy_registry.py:96`. Les trois lignes contiennent une concaténation parasite `)a#`. | L’archive ne peut pas constituer une base de tests ou de déploiement fiable. | Corriger dans une branche isolée seulement, puis valider par compilation et tests avant toute extraction fonctionnelle. |
| P1 | Les scripts Fusion activent par défaut le WebSocket privé dans la configuration, même si la boucle le limite ensuite au mode d’ordres démo. | Surface réseau et complexité inutiles pour le profil paper Elite. | Dans Elite, garder les flux publics et l’état paper local ; les flux privés restent désactivés et non importés. |
| P1 | Le dashboard Fusion expose des paramètres d’exécution, y compris le mode, et un bouton de cancel-all démo. | Une interface locale qui change le mode est une surface de contournement. | Conserver `runtime_config` Elite avec bornes ; le mode d’exécution ne doit pas être éditable depuis le dashboard. |
| P2 | `FUSION_ULTIMATE_V7.py` entraîne RandomForest et GradientBoosting sur l’historique courant et réentraîne périodiquement. Aucun split chronologique, mesure hors-échantillon, coût ni promotion de modèle n’est visible dans cette classe. | Risque de surajustement et de promotion implicite d’un score non validé. | N’utiliser que le contrat IA Elite `filter_only` ; exiger walk-forward, données/paramètres hachés et gate de promotion avant tout score ML. |

## 3. Compatibilité sélective

Les variantes V6.1 apportent des idées de **garde anti-self-cross** et de **limitation de boucle d’annulations**. V6.2 ajoute un mécanisme de publication de décisions vers un bus parental. V7 remplace ce bus par une couche d’ensemble ML additionnelle. Ces composants ne sont pas directement compatibles : ils sont intégrés à des scripts monolithiques utilisant leur propre stockage SQLite, configuration, dashboard, clients OKX et états asynchrones.

La seule voie sûre est de réécrire des fonctions pures, une par une, après spécification. Les priorités sont :

1. écrire des tests Elite pour l’anti-self-cross et le throttle de cancel ;
2. implémenter ces règles dans un adaptateur paper ne connaissant aucun endpoint privé OKX ;
3. journaliser la décision et le motif de blocage via `trade_journal` et `status_bridge` ;
4. exécuter `pytest`, le gate M7 et le smoke test avant livraison.

## 4. Analyse du modèle `tafa_god_v2_model.pkl`

L’en-tête binaire est cohérent avec un pickle protocole 5 et les chaînes de classes indiquent une dépendance possible à scikit-learn, notamment `HistGradientBoosting`, ainsi qu’à NumPy. Cela ne permet pas d’établir la provenance d’entraînement, l’ordre des features, les versions exactes, la performance, les frais ou le protocole hors échantillon.

Un pickle est un format de sérialisation capable de demander la reconstruction d’objets Python ; il ne doit pas être chargé lorsqu’il provient d’une source externe non vérifiée. Le modèle reste donc en quarantaine. Une intégration future exige au minimum : hash vérifié contre une source de confiance, environnement isolé, inventaire de dépendances, carte de modèle, schema de features versionné, données d’entraînement traçables et rapport walk-forward indépendant. À défaut, le modèle ne doit ni influencer les signaux ni être exposé au dashboard.

## 5. Résultat de l’analyse passive `tafagpt.zip`

L’archive est non chiffrée et ne contient pas de chemin ZIP absolu ou traversant détecté dans le répertoire central. Elle contient néanmoins 1 267 entrées, dont 108 sources Python hors environnement virtuel examinées par analyse syntaxique et 1 133 artefacts runtime. La présence d’un fichier `.env` a été détectée par son nom ; son contenu n’a volontairement pas été lu ni copié.

Les modules recensés incluent gestionnaires d’API, routes d’ordre, commutateur live, IA, backtesting, SQLite, dashboard, gestion de WebSocket et stratégie. Des duplications de modules dashboard sont visibles dans la structure. Cette combinaison de sources, de runtime, de caches et de contrôles d’exécution interdit toute importation automatique dans TAFA X Ultimate.

## 6. Livrables d’audit créés

| Fichier | Rôle |
| --- | --- |
| `scripts/static_audit_received_artifacts.py` | Analyse AST, ZIP et PKL sans import, extraction ni désérialisation. |
| `reports/received_artifact_static_audit.json` | Résultat machine lisible de l’analyse passive. |
| `knowledge/source_material/external_tafa_artifact_manifest_20260812.json` | Manifest Ibhextif haché, sans contenu exécutable ni secret. |
| `EXTERNAL_TAFA_ARTIFACTS_STATIC_AUDIT.md` | Présent rapport exploitable pour la consolidation. |

## 7. Conclusion

TAFA X Ultimate Elite reste le socle validé et fonctionnel en paper/demo. Les artefacts fournis enrichissent la base de connaissances, mais aucun ne passe le seuil d’intégration directe. Les correctifs utiles doivent être **reconstruits en composants testés**, jamais copiés depuis les scripts monolithiques, l’archive runtime ou le modèle sérialisé.
