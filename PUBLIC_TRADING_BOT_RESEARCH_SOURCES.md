# Sources publiques — architectures de bots et intégration IA

## Freqtrade

La documentation officielle présente Freqtrade comme un bot crypto open source en Python, avec téléchargement de données, backtests, optimisation de paramètres, dry-run, interface Web/Telegram, API REST et FreqAI. La documentation de backtesting précise que les données historiques sont nécessaires, que les frais sont appliqués à l’entrée et à la sortie, et que les résultats peuvent être exportés. Elle met également en garde sur la reproductibilité des pairlists dynamiques et recommande un dry-run avant toute utilisation avec fonds. [1] [2]

## Hummingbot

La documentation officielle décrit Hummingbot comme un framework Python modulaire pour stratégies algorithmiques et market making. Sa stratégie V2 emploie des scripts et contrôleurs, avec des connecteurs normalisant l’accès aux échanges. L’écosystème comporte un dashboard, une API, un MCP et Quants Lab pour recherche/backtests. [3]

La documentation Hummingbot recommande de distinguer les workflows locaux mono-bot des workflows orientés agents, déploiement cloud et multi-bot, et indique que les connecteurs normalisent les types d’ordres entre venues. Le projet recommande de ne télécharger les composants officiels que depuis ses organisations GitHub et DockerHub officielles. [3]

## Jesse

Le site officiel de Jesse présente un framework Python à exécution locale, proposant multi-symboles/timeframes, backtests, benchmark par lots, paper trading, indicateurs et outils d’optimisation. Certaines affirmations de performance ou de précision sont des déclarations du fournisseur et ne sont pas utilisées comme preuves de rentabilité. [4]

## Implications pour TAFA X Ultimate

Les sources convergent sur une architecture en couches : données historiques versionnées, moteur de backtest qui reproduit les coûts, stratégies modulaires, gestion du risque séparée, suivi d’exécution et interface opérateur. Une couche IA doit servir prioritairement à la recherche, à l’extraction de caractéristiques, à la classification de régimes et à l’explication, tandis que les règles de risque et de validation hors échantillon restent déterministes et auditables.

Les recherches publiques sur le surajustement appuient ce choix méthodologique : une sélection de paramètres ne peut être considérée comme robuste sur le seul résultat in-sample. TAFA doit donc continuer à versionner les données, geler les paramètres avant le test chronologique, puis journaliser l’écart train/test. [5] [6]

Le document de Bailey et al. décrit le surajustement de backtest comme la sélection de variantes sur un même historique et illustre la dégradation possible du résultat hors échantillon. Le papier SSRN d’Arnott, Harvey et Markowitz souligne que les applications ML en finance font face à des contraintes de quantité de données et recommande un protocole de recherche spécifique. Le préprint arXiv de Gort et al. propose de rejeter des agents de RL estimés surajustés ; il s’agit d’une piste de recherche, pas d’une preuve que le RL est approprié pour TAFA. [5] [6] [7]

## Références

[1] [Freqtrade — documentation officielle](https://www.freqtrade.io/en/stable/)

[2] [Freqtrade — Backtesting](https://www.freqtrade.io/en/stable/backtesting/)

[3] [Hummingbot — documentation officielle](https://hummingbot.org/docs/)

[4] [Jesse — site officiel](https://jesse.trade/)

[5] [Bailey et al. — Backtest Overfitting in Financial Markets](https://www.davidhbailey.com/dhbpapers/overfit-tools-at.pdf)

[6] [SSRN — A Backtesting Protocol in the Era of Machine Learning](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3275654)

[7] [arXiv — Deep Reinforcement Learning for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting](https://arxiv.org/abs/2209.05559)
