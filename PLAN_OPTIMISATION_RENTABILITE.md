# Plan d’optimisation de la performance nette — TAFA Elite

> **Cadre.** Ce plan améliore la méthode de recherche et de paper trading ; il ne promet pas de rentabilité. Toute optimisation doit être validée sur une période hors échantillon distincte de celle utilisée pour choisir les paramètres.

## Diagnostic issu du dernier backtest

Le profil actuel applique 500 USDC de capital paper, un take-profit de 1,8 %, 8 bps de frais à l’entrée et à la sortie, ainsi qu’un objectif de session de 5 USDC nets. Les quatre séries utilisent 2 000 bougies OKX fermées, mais elles couvrent des périodes différentes : leurs performances ne doivent donc pas être agrégées.

| Timeframe | Trades | P&L net | Profit factor | Observation exploitable |
|---|---:|---:|---:|---|
| 5m | 0 | 0,00 USDC | n.d. | Aucun signal : aucune conclusion de rendement n’est possible. |
| 15m | 1 | -0,50 USDC | 0,00 | Échantillon insuffisant pour optimiser. |
| 1H | 10 | +0,04 USDC | 1,009 | Presque à l’équilibre après frais : aucune preuve d’avantage statistique. |
| 4H | 27 | -10,72 USDC | 0,577 | Configuration défavorable : les pertes moyennes (1,69 USDC) dépassent les gains moyens (1,22 USDC). |

Le seuil de 5 USDC nets n’a été atteint par aucun timeframe. Avec 15 % de 500 USDC, le notionnel maximal de départ est environ 75 USDC. À un gain brut de 1,8 % et à 8 bps de frais par côté, le gain net théorique au take-profit est environ **1,23 USDC par trade**. Atteindre 5 USDC en une seule transaction exigerait environ **304,88 USDC** de notionnel, soit près de 61 % du capital ; ce n’est pas une raison suffisante pour augmenter l’exposition.

## Optimisations prioritaires

| Priorité | Optimisation | Pourquoi | Validation requise |
|---:|---|---|---|
| P0 | Désactiver le 4H comme source d’entrée tant que sa validation hors échantillon reste négative. | Il concentre 27 trades et un profit factor de 0,577. | Trois fenêtres hors échantillon avec profit factor > 1,10 et drawdown contrôlé avant réactivation. |
| P0 | Conserver le 1H comme **piste de recherche**, pas comme stratégie validée. | C’est le moins mauvais résultat, mais +0,04 USDC est compatible avec le bruit. | Au moins trois segments hors échantillon positifs après frais et nombre de trades suffisant. |
| P0 | Mettre en œuvre une séparation chronologique entraînement/validation/test. | Optimiser sur les mêmes 2 000 bougies créerait du surajustement. | Choix des paramètres sur le train ; décision de conservation uniquement sur test jamais consulté. |
| P1 | Filtrer les entrées 1H avec le régime 4H au lieu de trader le 4H lui-même. | Une tendance de contexte peut réduire les entrées contraires, sans conclure que le 4H est rentable seul. | Comparer « 1H seul » contre « 1H + filtre 4H » sur les mêmes fenêtres hors échantillon. |
| P1 | Tester des stops ATR plus compacts : 1,0 ; 1,2 ; 1,5 au lieu de 2,0. | Les pertes 4H sont plus grandes que les gains moyens ; le stop actuel mérite un test, pas une modification aveugle. | Retenir seulement une valeur stable sur plusieurs fenêtres, après frais. |
| P1 | Tester une grille limitée de take-profit : 1,4 % ; 1,8 % ; 2,2 %. | Le TP doit être analysé avec le taux de remplissage, le profit factor et le drawdown. | Ne sélectionner aucun réglage dont le résultat se dégrade hors échantillon. |
| P1 | Ajouter un filtre de liquidité/volume et un filtre de volatilité. | Les signaux en zones peu actives ou dans un régime incompatible peuvent être peu exploitables après frais. | Mesurer le nombre de trades supprimés, P&L net, profit factor et drawdown. |
| P2 | Journaliser le slippage simulé, le spread et les rejets. | Les 8 bps de frais seuls ne modélisent pas tout le coût d’exécution. | Rapporter P&L brut, frais, slippage et P&L net séparément. |
| P2 | Utiliser une taille de position adaptative plafonnée. | La taille doit suivre le risque/drawdown, non un objectif monétaire arbitraire. | Le plafond d’exposition reste fixe et le drawdown s’améliore ou reste stable. |

## Protocole expérimental recommandé

Le protocole doit limiter l’optimisation opportuniste. Faites d’abord une expérience à une variable ; conservez les frais de 8 bps par côté et le capital paper de 500 USDC. Testez les paramètres sur une première fenêtre, puis bloquez-les avant de les évaluer sur une seconde période non consultée.

| Expérience | Valeurs testées | Mesures de sélection | Règle de rejet |
|---|---|---|---|
| Stop ATR | 1,0 ; 1,2 ; 1,5 ; 2,0 | Profit factor, drawdown, P&L net et nombre de trades | Rejeter si le résultat net ou le profit factor se dégrade hors échantillon. |
| Take-profit | 1,4 % ; 1,8 % ; 2,2 % | Taux TP, pertes moyennes, P&L net après frais | Rejeter les paramètres qui ne tiennent que sur la fenêtre de sélection. |
| Filtre régime 4H | Désactivé / tendance alignée | Rendement net 1H, trades évités, drawdown | Rejeter si le filtre réduit seulement les trades sans améliorer les mesures nettes. |
| Filtre volume | Aucun / volume supérieur à une moyenne mobile définie | Profit factor, durée et slippage | Rejeter si l’échantillon devient trop petit pour être informatif. |
| Position fraction | 10 % ; 15 % ; 20 % | Drawdown relatif, P&L net, exposition | Rejeter si l’amélioration brute vient d’une hausse de risque disproportionnée. |

## Critères de passage en paper/demo prolongé

Conserver un candidat uniquement s’il satisfait simultanément les critères suivants sur des fenêtres hors échantillon distinctes : P&L net positif après frais et slippage simulé, profit factor supérieur à 1,10, drawdown inférieur à la limite fixée avant test, absence de dépendance à un unique trade, et cohérence entre deux périodes de marché différentes. Le seuil de 5 USDC doit rester un **arrêt de session après gain réalisé**, non un signal d’entrée ni un objectif à forcer.

## Ordre de réalisation

1. Ajouter au backtester la séparation temporelle et le rapport de coûts complet.
2. Désactiver les entrées 4H actuelles et expérimenter le filtre de régime 4H appliqué aux entrées 1H.
3. Lancer la grille stop/TP à une variable, puis verrouiller les réglages retenus avant le test hors échantillon.
4. Ajouter le filtre volume/volatilité et répéter la validation.
5. Garder le profil uniquement en paper/demo tant que les critères ne sont pas atteints sur plusieurs périodes.

> **This is research and analysis only, not personalized financial advice.**
