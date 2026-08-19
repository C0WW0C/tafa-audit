# Recherche publique — DeepAI et bots de trading

**Date de consultation :** 12 août 2026.  
**Périmètre :** sources publiques de `deepai.org`, sans connexion, clé API, exécution de code tiers ni envoi d’ordre.

> **Conclusion vérifiée.** Les pages officielles consultées décrivent DeepAI comme un service de génération et de conversation IA. La page « AI Trading Indicator » est présentée comme un assistant conversationnel fournissant des insights. Les documentations accessibles ne décrivent ni connecteur d’exchange, ni gestion de portefeuille, ni moteur de backtest, ni endpoint d’exécution d’ordres. Il ne faut donc pas présenter DeepAI comme un bot de trading autonome.

| Élément observé | Ce que la source décrit | Pertinence TAFA | Décision |
| --- | --- | --- | --- |
| API DeepAI | API HTTP documentées pour génération/édition d’images, super-résolution, colorisation et détourage.[1] | Hors du chemin de décision de trading | Ne pas intégrer au moteur, au risque ou au backtest. |
| AI Chat | Assistant conversationnel pouvant fournir du texte, du code ou des informations générales ; la documentation avertit qu’il peut commettre des erreurs.[1] | Peut servir, au mieux, d’assistant documentaire hors ligne d’exécution | Ne jamais lui déléguer un signal d’ordre ni une limite de risque. |
| AI Trading Indicator | Personnage de chat décrit comme une entité d’insights de trading ; l’interface expose une zone de message, sans connecteur ni contrôle d’exécution observables.[2] | Source d’analyse non déterministe | Aucune intégration d’exécution, de portefeuille ou d’API OKX. |

## Position recommandée pour TAFA X Ultimate

TAFA conserve son architecture : données OKX validées, backtests avec frais, walk-forward, qualité de données, contrôle déterministe des risques et mode paper/demo. Si un outil conversationnel était un jour évalué, son rôle serait limité à la synthèse de documentation déjà validée et journalisée. Il ne devrait recevoir aucune clé d’exchange, aucun état de position sensible ni capacité d’appeler un endpoint privé.

## Limites de la recherche

Cette conclusion couvre les pages publiques consultées. Elle n’exclut pas l’existence d’outils tiers portant un nom proche, de projets privés ou d’intégrations non publiées. Toute proposition de clonage ou d’intégration nécessitera une URL, une archive ou une documentation technique précise fournie par l’utilisateur.

## Références

[1] [DeepAI Docs](https://deepai.org/docs)

[2] [DeepAI — AI Trading Indicator](https://deepai.org/chat/a_i_trading_indicator_0)
