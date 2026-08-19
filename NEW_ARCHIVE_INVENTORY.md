# Inventaire initial — TAFA GOD GRID V8 et TAFA CLEAN1

## TAFA GOD GRID V8

Le pack contient 13 fichiers visibles : trois modules Python dans `bot/`, des scripts Windows `.bat`, une archive de données, une archive d’outil de backtest et quelques documents. Sa notice indique un défaut paper, mode cash, sans levier, futures ni margin ; cette déclaration reste à vérifier dans le code. Le pack ne fournit pas de suite de tests visible au premier inventaire.

## TAFA CLEAN1

L’archive contient un projet TAFA plus large avec moteur, backtesting, exchange, risque, dashboard et tests. Son volume (1 887 fichiers) est fortement gonflé par `venv/`, `__pycache__/`, logs, base SQLite et fichiers d’état runtime. Ces artefacts ne doivent pas être fusionnés dans Elite. Le document `AUDIT_FIXES.md` annonce plusieurs corrections, mais les corrections doivent être vérifiées dans les modules correspondants.

## Règle de fusion

L’intégration est limitée à des modules sources examinés, couverts par tests et compatibles avec le mode paper/demo. Les scripts `.bat`, environnements virtuels, logs, bases locales, PID, journaux et archives imbriquées sont traités comme données non fiables et restent exclus de toute fusion automatique.

## Vérifications statiques ciblées

GOD GRID construit explicitement des ordres limites spot avec `tdMode=cash`, sans réglage de levier dans ce chemin. Il contient néanmoins une fonction `private_post` qui atteint l’endpoint d’ordre OKX ; ce module ne peut pas être fusionné comme simple dashboard sans isoler ce chemin derrière les garde-fous Elite.

TAFA CLEAN force le paper par défaut et ne passe en live que si trois conditions explicites sont remplies. Il contient cependant des méthodes `place_order` et un serveur web qui lance/arrête des processus. Ses valeurs de risque par défaut (`RISK_PER_TRADE=1 %`, perte journalière 5 %, drawdown 15 %, taille d’ordre 100 USDC) doivent être comparées aux limites Elite avant toute réutilisation.
