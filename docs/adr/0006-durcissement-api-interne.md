# ADR 0006: Durcissement API minimal pour un usage interne (pas d'authentification)

## Statut

Acceptée

## Contexte

Dans le cadre du passage en production, l'API FastAPI (`ui/api.py`) devait être évaluée pour son exposition réseau. L'utilisateur a confirmé un usage strictement interne/VPN, sans accès public. Se posait la question du niveau de durcissement à appliquer : authentification, rate limiting, CORS, validation des entrées.

## Décision

Ne pas ajouter d'authentification (jugée hors scope pour un usage interne à faible enjeu), mais appliquer les durcissements à faible coût qui restent pertinents même en réseau fermé :

- CORS restreint à une liste configurable via `ALLOWED_ORIGINS` (défaut `http://localhost:8000`) au lieu du wildcard `*` précédemment en place.
- Bornes de validation pydantic sur les entrées de scan : `max_competitors` (1-20), `sector` (1-100 caractères), `hour` (0-23) sur `ScanRequest` et `ScheduleConfig` — un dépassement renvoie `422` avant même de démarrer un scan.

Objectif : éviter qu'un scan démesuré (coûteux en appels LLM) soit déclenché par erreur — ponctuel ou planifié — sans imposer de friction d'authentification pour un usage interne.

## Conséquences

- Aucune barrière d'authentification : quiconque a accès au réseau interne/VPN peut déclencher un scan ou lire les rapports.
- Coût de développement minimal, pas de gestion de secrets d'authentification supplémentaire.
- **Si l'API devient un jour accessible publiquement ou depuis un réseau moins maîtrisé**, cette décision doit être révisée en priorité : ajouter une authentification (API key a minima) et du rate limiting avant toute exposition externe.
