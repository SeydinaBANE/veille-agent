# ADR 0005: Logging structuré via le module `logging` standard

## Statut

Acceptée

## Contexte

Toute la sortie du pipeline (progression du scan, erreurs, résultats des notifications) passait par `print()`, dans `main.py` comme dans chaque adapter. Impossible de filtrer par niveau de gravité, de rediriger proprement les logs dans un contexte conteneurisé, ou de conserver une trace d'erreur (stack trace) en cas d'échec silencieux.

## Décision

Remplacer tous les `print()` par `logging.getLogger(__name__)` dans chaque module. Centraliser la configuration dans `logging_config.py` (`configure_logging()`), rendue idempotente (`if logging.getLogger().handlers: return`) et appelée en tête de chaque composition root (`main.py`, `ui/api.py`), qu'ils soient importés l'un par l'autre ou exécutés indépendamment. Pas de librairie tierce de logging structuré (`structlog`, `loguru`) — le module standard suffit au volume de logs de ce projet.

## Conséquences

- Niveaux de log exploitables (`INFO` pour la progression, `WARNING`/`ERROR` pour les anomalies), stack traces conservées via `logger.exception(...)` dans `run_scan_background` (ui/api.py) et les notifiers.
- Compatible nativement avec la collecte de logs Docker (stdout/stderr), sans configuration supplémentaire.
- Format actuel en texte brut (`%(asctime)s %(levelname)s %(name)s: %(message)s`), pas de sortie JSON structurée — à reconsidérer si les logs sont un jour agrégés dans un système centralisé (ELK, Datadog...).
