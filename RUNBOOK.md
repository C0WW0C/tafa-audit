# Guide d’exécution sécurisée — TAFA X Ultimate Elite

## Démarrage local recommandé

Installez les dépendances dans un environnement Python isolé, renseignez uniquement les variables nécessaires dans votre environnement, puis exécutez :

```bash
pip install -r requirements.txt
python run_v10.py
```

Le moteur démarre en mode paper/démo lorsque les conditions strictes du mode live ne sont pas réunies. Le dashboard est démarré automatiquement et reste accessible sur :

```text
http://127.0.0.1:8765
```

La page affiche l’état bot à travers le flux `/api/stream`, et les prix de marché proviennent de la connexion WebSocket exchange configurée dans le moteur.

## Contrôle des paramètres

Le dashboard n’expose que des paramètres qui font l’objet d’une validation côté serveur. Une réponse API indique explicitement les clés `accepted`, `rejected` et `applied`. Les valeurs hors plage ou non disponibles dans le moteur actif ne doivent pas être considérées comme appliquées.

Le capital de paper trading peut être réinitialisé uniquement avant toute transaction et sans position ouverte. Après le premier trade, un changement de capital est conservé comme demande de redémarrage afin d’éviter une réécriture silencieuse de la comptabilité.

## Accès distant : désactivé par défaut

Le serveur écoute par défaut uniquement sur `127.0.0.1`. N’exposez pas le port directement sur Internet. Si un accès réseau privé est indispensable, définissez au minimum un jeton long et utilisez un reverse proxy HTTPS avec des restrictions réseau :

```bash
export TAFA_DASHBOARD_HOST=0.0.0.0
export TAFA_DASHBOARD_TOKEN="remplacez-par-un-secret-long-et-unique"
python run_v10.py
```

Saisissez alors le jeton dans le champ « Jeton de contrôle distant » du dashboard. Cette mesure ne constitue pas à elle seule une solution d’authentification multi-utilisateur.

## Procédure avant un essai contrôlé

1. Vérifiez que le dashboard affiche un flux actif, un prix marché cohérent et le mode `PAPER`.
2. Vérifiez que les paramètres affichés correspondent aux valeurs appliquées dans `/api/status`.
3. Réalisez un redémarrage contrôlé et vérifiez que l’état du PID, du circuit et du flux est cohérent.
4. Inspectez les logs `logs/tafa_v10.log` et le journal d’événements avant d’interpréter toute performance.
5. N’activez pas le live trading tant que les tests de données, d’exécution, de frais, de slippage et de reprise après panne ne sont pas complétés.

> **This is research and analysis only, not personalized financial advice.**
