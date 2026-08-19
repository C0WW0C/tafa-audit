# Vérification locale des onglets dashboard

**Date :** 12 août 2026  
**Serveur testé :** `http://127.0.0.1:8765`

| Vérification | Constat |
| --- | --- |
| Chargement de l’interface | Le bundle Elite et le flux SSE chargent ; le statut `TAFA_X_ULTIMATE_FINAL` est visible. |
| Adresse API par défaut | La source est désormais `http://127.0.0.1:8765` lorsque le dashboard est servi depuis une autre origine. |
| Onglet « Flux & exécution » | Le clic sélectionne l’onglet et fait défiler l’interface vers la zone d’exécution. |
| Onglet « Risque & garde-fous » | Le clic sélectionne l’onglet et amène la section de protections locales paper au premier plan. |
| Onglet « Paramètres validés » | Le clic sélectionne l’onglet, déroule les champs contrôlés et rend le bouton de validation visible. |
| Contrôles mutables | Aucun clic de démarrage, arrêt ou sauvegarde de paramètres n’a été effectué durant cette vérification. |

Les routes API de lecture et de configuration validée doivent encore être couvertes par les tests serveur dédiés.

## Vérification d’assets locaux

Après compilation et synchronisation du bundle, le dashboard local ne référence plus `/manus-storage/`. Les éléments visuels sont rendus par CSS et les onglets ainsi que le flux SSE restent disponibles. La console navigateur ne contient plus d’erreur de chargement de ressource ; elle ne présente que la recommandation non bloquante d’installer React DevTools.
