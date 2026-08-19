# TAFA X Elite M7 — test paper/demo OKX

> **Avertissement.** Je suis une IA, pas un conseiller financier agréé : cette procédure est une analyse technique et ne garantit aucun résultat. Le trading comporte un risque que vous assumez. Cette release force le chemin de lancement M7 en **DEMO/PAPER** et ne doit pas être utilisée pour placer des ordres réels.

## 1. Préparer un environnement propre

Créez un environnement Python isolé, installez les dépendances et copiez le profil M7 :

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.paper-demo.example .env
```

Sous Windows sans commande `cp`, copiez manuellement `.env.paper-demo.example` vers `.env`.

Le profil impose `TAFA_MODE=DEMO`, `ENABLE_LIVE=false`, un moteur natif et l’absence de confirmation live. Conservez les identifiants API OKX privés vides pour ce test : TAFA consommera seulement les données publiques OKX.

## 2. Valider la release avant lancement

Exécutez d’abord les contrôles statiques et les tests :

```bash
python scripts/m7_release_gate.py
```

Pour lancer en plus le smoke test qui lit des données de marché publiques et contrôle le dashboard local :

```bash
python scripts/m7_release_gate.py --with-smoke
```

Le test smoke ne transmet aucun ordre réel et ne nécessite pas de clé privée. Il requiert toutefois un accès réseau à la donnée publique OKX.

## 3. Lancer TAFA M7 en paper/demo

Utilisez exclusivement le launcher M7 suivant :

```bash
python run_paper_demo.py
```

Le launcher écrase tout environnement hérité dangereux et force `TAFA_MODE=DEMO`, `ENABLE_LIVE=false` et `TAFA_PAPER_ONLY=true` avant que la configuration ne soit chargée. Le dashboard démarre automatiquement sur :

```text
http://127.0.0.1:8765
```

Le bouton **Démarrer** du dashboard utilise également `run_paper_demo.py`, pas le launcher générique. Ne rendez pas ce port public.

## 4. Vérifications à effectuer dans le dashboard

| Point | Attendu avant de poursuivre |
|---|---|
| Mode | `PAPER` ou `DEMO` ; jamais `LIVE`. |
| Source de marché | Flux OKX public connecté ou état de dégradation visible. |
| Télémétrie | Flux local actif et fraîcheur mise à jour. |
| Circuit de sécurité | Armé, sans blocage inattendu. |
| Paramètres | Toute modification est déclarée appliquée, refusée ou nécessitant un redémarrage. |
| Exécution | Les positions et P&L restent dans le portefeuille paper. |

## 5. Construire une archive de release propre

Lorsque les contrôles M7 sont validés, générez l’archive sans secrets, logs, caches ni bases runtime :

```bash
python scripts/package_m7_release.py
```

Le script produit un ZIP, un fichier SHA-256 et vérifie l’intégrité interne de l’archive.

## 6. Critères d’arrêt

Arrêtez le test et analysez les logs si le flux de marché devient périmé, si le circuit breaker se déclenche, si la réconciliation ou l’état dashboard diverge, ou si une configuration est refusée de façon inattendue. Le passage à une exécution réelle ne fait pas partie de ce runbook.

> This is research and analysis only, not personalized financial advice.
