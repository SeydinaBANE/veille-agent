# Architecture Decision Records

Ce dossier consigne les décisions d'architecture structurantes du projet : le contexte qui les a motivées, la décision retenue, et ses conséquences (y compris les compromis acceptés). L'objectif est qu'une décision passée reste compréhensible sans avoir à reconstituer la conversation qui l'a produite.

## Index

| ADR | Titre | Statut |
|---|---|---|
| [0001](0001-architecture-hexagonale.md) | Architecture hexagonale (ports & adapters) | Acceptée |
| [0002](0002-deploiement-conteneur-unique.md) | Déploiement en conteneur unique, pas de scaling horizontal | Acceptée |
| [0003](0003-retry-backoff-tenacity.md) | Retry/backoff via tenacity sur les appels réseau et LLM transitoires | Acceptée |
| [0004](0004-ruff-mypy-ci.md) | ruff + mypy comme linter/typechecker, appliqués en CI | Acceptée |
| [0005](0005-logging-standard.md) | Logging structuré via le module `logging` standard | Acceptée |
| [0006](0006-durcissement-api-interne.md) | Durcissement API minimal pour un usage interne (pas d'authentification) | Acceptée |

## Ajouter une nouvelle ADR

Copier [`template.md`](template.md) vers `NNNN-titre-court.md` (numéro suivant, kebab-case), remplir les sections, ajouter une ligne à l'index ci-dessus.
