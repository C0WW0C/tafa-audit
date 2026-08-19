# Correctif — résilience TLS des données publiques OKX

## Incident traité

La récupération publique des chandeliers pouvait échouer sur une fermeture prématurée de la session TLS, par exemple `SSLEOFError: UNEXPECTED_EOF_WHILE_READING`. L’ancien client abandonnait dès le premier échec réseau.

## Modification appliquée

Le client public `exchange/okx_client.py` effectue désormais jusqu’à trois tentatives au total pour les erreurs transitoires de connexion, de délai, de TLS ou pour les réponses HTTP 429/5xx. Les délais progressifs sont de 0,25 puis 0,50 seconde. Les erreurs définitives ne sont pas répétées.

La validation de certificat TLS reste activée : aucune option de contournement, tel que `verify=False`, n’est utilisée. Lorsque les tentatives échouent, le client renvoie un résultat vide contrôlé ; le service de marché conserve alors son repli existant vers les chandeliers CSV locaux.

## Validation

Deux tests de régression ont été ajoutés : l’un simule deux interruptions TLS avant une réponse réussie, l’autre vérifie le repli vers les données locales lorsque le fournisseur public ne renvoie aucune bougie. La suite complète de tests a été exécutée avec succès après le correctif.

## Périmètre de sécurité

Le changement porte uniquement sur les endpoints de données publiques. Il ne crée aucune voie d’exécution, ne modifie pas les clés ni les modes paper/demo, et ne désactive pas la vérification TLS.
