# Correctif — publication de statut sous Windows

## Incident traité

Le moteur pouvait échouer lors du remplacement de `data/live_status.json` avec `WinError 5` lorsqu’un autre processus Windows détenait temporairement le fichier. Le statut en mémoire restait à jour, mais le dashboard local pouvait lire une version périmée.

## Modification appliquée

Le module `core/status_bridge.py` utilise désormais un fichier temporaire unique par écriture, synchronise son contenu sur disque, puis effectue un remplacement atomique avec au plus six tentatives et un délai progressif. Les erreurs transitoires de partage ou d’accès (`WinError 5`, `WinError 32`, `EACCES`, `EBUSY`, `EPERM`) sont reprises. Aucun remplacement non atomique n’est utilisé ; si toutes les tentatives échouent, le dernier fichier de statut valide reste intact.

Le nouveau test de régression simule deux refus d’accès consécutifs et confirme que la troisième tentative publie le statut sans laisser de fichier temporaire.

## Périmètre de sécurité

Ce correctif ne modifie ni le routage d’ordres, ni les modes d’exécution, ni la configuration de l’exchange. La suite de tests conserve les contrôles paper/demo et le verrouillage de `ENABLE_LIVE=false`.

## Validation

La suite complète a été exécutée avec succès après modification : `pytest -q`.
