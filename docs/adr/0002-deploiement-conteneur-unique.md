# ADR 0002: Déploiement en conteneur unique, pas de scaling horizontal

## Statut

Acceptée

## Contexte

Lors de l'audit de passage en production, il fallait décider si le stockage JSON local (snapshots par concurrent dans `storage/snapshots/`, historique des scans dans `storage/scans.json`, configuration de planification dans `storage/schedule.json`) devait être remplacé par une base de données pour supporter plusieurs instances de l'application en parallèle (scaling horizontal, Kubernetes/Cloud Run/ECS...).

## Décision

L'utilisateur a confirmé une cible de déploiement en **conteneur unique** via Docker Compose, en **usage interne/VPN uniquement** (pas d'exposition publique). Le stockage JSON local est donc conservé tel quel — aucune migration vers une base de données n'a été entreprise.

## Conséquences

- Pas de dépendance à un service de base de données externe : déploiement simple, un seul `docker compose up --build`.
- Pas de problème de concurrence d'écriture entre plusieurs instances, puisqu'il n'y en a qu'une.
- Les fichiers `storage/snapshots/*.json`, `storage/scans.json` et `storage/schedule.json` doivent être persistés via des volumes montés (déjà fait dans `docker-compose.yml`) pour survivre à un redémarrage du conteneur.
- **Si le besoin de scaling horizontal ou de haute disponibilité apparaît**, cette décision doit être révisée : le stockage JSON local devra être remplacé par une base de données partagée (ou équivalent), et cette ADR marquée comme remplacée.
