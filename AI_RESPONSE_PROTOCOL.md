# Règles de réponse IA pour la base Ibhextif

Chaque réponse issue de la base doit contenir les éléments suivants :

```yaml
answer: réponse directe fondée sur les registres
assumptions:
  - hypothèses de données, période ou frais
sources:
  - document_id: identifiant du document
    source_id: identifiant de source
    captured_at: horodatage de capture
    trust_level: niveau de confiance
limitations:
  - lacunes, conflits ou limites de validation
next_validation: action expérimentale ou documentation requise
```

Les réponses doivent distinguer explicitement : **fait observé**, **réglage configuré**, **hypothèse de stratégie**, **résultat historique** et **décision humaine requise**. Les métriques de backtest ne sont pas des prédictions et aucun ordre réel ne doit être créé, modifié ou envoyé à partir d’une réponse de la base sans confirmation explicite de l’utilisateur.
