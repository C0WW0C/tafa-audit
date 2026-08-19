# Correctif des interactions dashboard Elite

## Causes corrigées

Deux causes rendaient l’interface difficile à utiliser. La navigation latérale était visuelle : les boutons ne possédaient ni gestionnaire de clic ni section cible. En outre, lorsque l’interface Elite était ouverte depuis une origine différente du serveur TAFA, son adresse API par défaut reprenait cette origine au lieu de viser le serveur local en port 8765.

Une troisième anomalie reproductible concernait les zones visuelles : le bundle local référençait des chemins `/manus-storage/` propres à l’environnement WebDev. Le serveur TAFA autonome ne possède pas ces fichiers, ce qui produisait des images cassées et des requêtes 404. Les trois visuels ont été remplacés par des motifs CSS locaux, sans dépendance réseau ni stockage externe.

## Comportement rétabli

| Élément | Comportement après correctif |
| --- | --- |
| Vue d’ensemble | Sélectionne l’onglet et revient au début de la supervision. |
| Flux & exécution | Sélectionne l’onglet et amène la zone d’exécution au premier plan. |
| Risque & garde-fous | Sélectionne l’onglet et affiche la synthèse circuit, autorisation paper et garde anti-duplication. |
| Paramètres validés | Sélectionne l’onglet, déroule la section de paramètres et rend le bouton de validation accessible. |
| Adresse API | Utilise l’origine courante si le dashboard est servi en port 8765 ; sinon, vise `http(s)://<hôte>:8765` par défaut. |

Les appels continuent d’utiliser uniquement `/api/status`, `/api/stream`, `/api/config`, `/api/start` et `/api/stop` du serveur TAFA. Aucun chemin d’ordre exchange n’a été ajouté.

## Contrôles effectués

La vérification locale a confirmé le chargement du bundle Elite, la réception du flux SSE, l’absence de références `/manus-storage/` et le fonctionnement des onglets Flux, Risque et Paramètres. Les tests contrôlent également le chargement du bundle et les routes de lecture de statut, configuration, santé et résumé de performance. Le test de vérification n’a pas démarré, arrêté ou reconfiguré le bot.
