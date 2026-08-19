# Console de marché Elite — paper/demo uniquement

## Portée

La console **Tactical Market Desk** enrichit le dashboard Elite avec un carnet public, les meilleurs prix bid/ask, le spread, un ticket de marché manuel et un ruban des exécutions manuelles. Elle sert exclusivement le portefeuille local `PaperTrading` de TAFA X Ultimate.

> Les boutons « Acheter paper » et « Vendre paper » ne transmettent aucun ordre à OKX. Ils créent une demande locale qui n’est traitée que par le moteur paper actif.

| Élément | Origine | Comportement |
| --- | --- | --- |
| Carnet 5 niveaux | WebSocket public OKX `books5`, avec fallback REST public | Affiche uniquement des données effectivement reçues ; aucun niveau n’est synthétisé. |
| Bid / ask / spread | Premier niveau du carnet public | Sert de prix d’exécution paper préférentiel pour BUY/SELL lorsque disponible. |
| Ticket manuel | Route locale `POST /api/paper/order` | Accepte seulement `BUY` ou `SELL`, sur le symbole actif, entre 5 et 250 USDC. |
| File locale | `data/manual_paper_orders/` | Écriture atomique ; le moteur consomme au plus trois demandes par cycle. |
| Exécution | `TradeManager.execute_manual_paper` | Paper-only, protections de risque, objectif de session et garde anti-duplication appliqués. |
| Ruban d’exécution | État publié par le moteur | Conserve les trente derniers résultats, dont les douze plus récents sont affichés. |

## Garde-fous

La route refuse toute utilisation si `PAPER_TRADING` n’est pas actif ou si `ENABLE_LIVE` est actif. Le montant est borné et le moteur refuse un symbole différent du symbole suivi. Une vente paper ne peut pas dépasser la position ouverte. Le ticket n’expose ni clé, ni route privée, ni sélection de compte exchange.

## Utilisation

Lancez d’abord le mode Elite paper/demo avec `python run_elite_final_paper.py`. Une fois le flux actif, ouvrez `http://127.0.0.1:8765`, saisissez un montant compris entre 5 et 250, puis utilisez le bouton paper correspondant. Le ruban indique `FILLED`, une raison de rejet contrôlé ou l’attente de traitement par le moteur.

Si le book public est temporairement indisponible, le dashboard l’indique explicitement. Aucun prix ou niveau artificiel n’est présenté comme une donnée de marché.
