# Guide final de déploiement — TAFA X Ultimate Elite

**Release concernée :** TAFA X Ultimate Elite Guarded  
**Périmètre autorisé :** recherche et supervision **paper/demo OKX uniquement**  
**Interdiction de cette procédure :** aucune clé d’exchange, aucun ordre réel, aucun changement manuel vers un mode live.

> Le launcher `run_elite_final_paper.py` impose le mode `DEMO`, désactive `ENABLE_LIVE`, vide la confirmation live, fixe le portefeuille paper à 500 USDC, applique le profil multi-timeframe Elite et sélectionne le stockage local. Ne contournez pas ce launcher.

## 1. Choisir le mode d’exploitation

| Option | Cas d’usage | Atout | Limite |
| --- | --- | --- | --- |
| **Poste local** | Tests, backtests, paper/demo supervisé manuellement | Installation simple, données et dashboard restent locaux | Le processus s’arrête si la machine est arrêtée ou mise en veille. |
| **Serveur persistant dédié** | Observation continue du flux public et du dashboard | Processus maintenu sans dépendre d’un poste local | Demande une supervision système, des sauvegardes et une configuration réseau rigoureuse. |

Le déploiement initial recommandé est le **poste local**. Un serveur persistant doit rester en paper/demo jusqu’à la validation durable des logs, des arrêts, des restaurations et du contrôle d’accès dashboard.

## 2. Préconditions

Le système cible doit disposer de Python 3.12, d’un accès réseau sortant vers les données publiques OKX et d’un répertoire local inscriptible. Aucun port public ne doit être ouvert par défaut : le dashboard est conçu pour écouter sur `127.0.0.1`.

Installez la release dans un répertoire neuf, puis créez un environnement Python isolé. Les fichiers `.env*.example` sont des exemples seulement ; ne copiez aucune clé d’exchange dans la configuration paper/demo.

```bash
unzip TAFA_X_ULTIMATE_FINAL_GUARDED_PAPER_DEMO.zip -d releases
cd releases/TAFA_X_ULTIMATE_FINAL

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Vérifiez ensuite l’archive reçue avant toute installation :

```bash
sha256sum TAFA_X_ULTIMATE_FINAL_GUARDED_PAPER_DEMO.zip
# Empreinte attendue : 4da347644732490d280e2828154158544008e6c359020d1d00a7899735b91abd
```

## 3. Variables et garde de configuration

Le launcher applique lui-même les valeurs de sûreté. Une session doit produire les valeurs suivantes :

| Variable | Valeur attendue | Rôle |
| --- | --- | --- |
| `TAFA_MODE` | `DEMO` | Active le contexte de démonstration. |
| `ENABLE_LIVE` | `false` | Neutralise le chemin live. |
| `LIVE_CONFIRM` | vide | Empêche la confirmation live. |
| `TAFA_PAPER_ONLY` | `true` | Affirme la restriction paper. |
| `TAFA_PAPER_CAPITAL` | `500` | Portefeuille paper Elite. |
| `TAFA_STORAGE_PROFILE` | `local` | Conserve le stockage local validé. |

Ne définissez pas `OKX_API_KEY`, `OKX_API_SECRET` ou `OKX_API_PASSPHRASE` pour cette procédure. Les flux publics suffisent au paper/demo Elite. Le profil PostgreSQL/TimescaleDB/Redis est une cible documentée séparément, non un prérequis de cette release.

## 4. Validation pré-lancement obligatoire

Exécutez les trois vérifications ci-dessous depuis la racine de la release. Aucune étape suivante ne doit être poursuivie si l’une d’elles échoue.

```bash
python scripts/validate_ibhextif_knowledge.py
pytest -q
python scripts/m7_release_gate.py --with-smoke
```

Le résultat attendu est une base Ibhextif valide, une suite de tests verte et `M7 RELEASE GATE: PASSED`. Le smoke test démarre un cycle paper/demo court, puis l’arrête automatiquement.

## 5. Lancement paper/demo

Démarrez exclusivement avec le launcher Elite :

```bash
python run_elite_final_paper.py
```

Le moteur utilise les flux publics OKX avec repli REST si nécessaire. Le dashboard local est disponible à l’adresse suivante lorsque le processus est actif :

```text
http://127.0.0.1:8765
```

Le dashboard permet de consulter l’état, le risque, le portefeuille paper, les paramètres bornés et le statut du garde `paper_guard`. Le changement de mode d’exécution ne fait pas partie des contrôles dashboard autorisés.

## 6. Supervision opérationnelle

Pendant une session, vérifiez périodiquement que le statut indique `PAPER` ou `DEMO`, que le circuit breaker reste cohérent et que `paper_guard` journalise les éventuels achats répétitifs bloqués. Les événements sont locaux :

| Artefact | Utilité | Règle |
| --- | --- | --- |
| `data/live_status.json` | État courant du dashboard | Fichier runtime ; ne pas l’archiver ni le partager. |
| `data/journal.jsonl` | Événements paper, dont garde-fous | Contrôler avant tout diagnostic ; exclure des packages. |
| `reports/` | Résultats de backtests et validations | Associer un résultat à son dataset, ses frais et sa configuration. |
| `data/market/dataset_manifest.json` | Empreintes des datasets historiques | Vérifier avant une nouvelle campagne de backtest. |

Pour une consultation terminal simple, utilisez les scripts déjà fournis :

```bash
python scripts/monitor_prod.py
python scripts/metrics_exporter.py --host 127.0.0.1
```

Ces scripts servent à la visibilité locale. Ils ne changent ni mode d’exécution ni portefeuille.

## 7. Arrêt, reprise et retour arrière

Arrêtez le processus principal par `Ctrl+C`. Vérifiez que le WebSocket est arrêté et que le fichier PID éventuel n’est plus présent. Ne forcez pas d’arrêt du système pendant une écriture de journal ou une validation de dataset.

Pour reprendre, relancez les validations de la section 4 puis `run_elite_final_paper.py`. Les données runtime ne remplacent jamais les rapports versionnés ; une reprise démarre dans le cadre paper local.

En cas de régression, revenez à une archive connue dont l’empreinte a été validée, dans un **nouveau répertoire**. Ne remplacez pas une release fonctionnelle en place.

```bash
mkdir -p releases/rollback
unzip TAFA_X_ULTIMATE_FINAL_CONSOLIDATED_PAPER_DEMO.zip -d releases/rollback
cd releases/rollback/TAFA_X_ULTIMATE_FINAL
python scripts/m7_release_gate.py --with-smoke
```

## 8. Déploiement persistant : règles minimales

Un processus continu ne doit être envisagé qu’après plusieurs sessions locales validées. Utilisez alors un compte système dédié, un environnement virtuel isolé, un répertoire de release en lecture seule hors runtime, un répertoire `data/` à permissions minimales, des sauvegardes vérifiées et une supervision de processus avec redémarrage contrôlé.

Le dashboard reste lié à `127.0.0.1`. Si un accès distant est nécessaire, exposez-le uniquement derrière un contrôle d’accès authentifié et chiffré. N’ouvrez pas directement le port du dashboard sur Internet. La persistance avancée, les flux privés et toute infrastructure de secrets exigent une revue d’architecture distincte et restent hors de ce guide.

## 9. Critères de mise en service paper/demo

| Contrôle | Condition de passage |
| --- | --- |
| Intégrité | SHA-256 de l’archive conforme. |
| Isolation | Environnement virtuel propre et dépendances installées. |
| Sécurité | `DEMO`, `PAPER_ONLY=true`, `ENABLE_LIVE=false`, aucune clé d’exchange. |
| Validation | Ibhextif, tests et gate M7 passés. |
| Dashboard | État visible localement ; aucun port public direct. |
| Risque | Circuit breaker, quality gate et `paper_guard` visibles et cohérents. |
| Repli | Archive précédente identifiée, hachée et testée dans un autre répertoire. |

> Ce guide décrit un déploiement de recherche paper/demo. Il ne constitue pas une autorisation de trading réel ni une indication de performance future.
