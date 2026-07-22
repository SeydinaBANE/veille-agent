# ADR 0001: Architecture hexagonale (ports & adapters)

## Statut

Acceptée

## Contexte

Le pipeline était organisé en packages `*_agent` (`discovery_agent`, `scraper_agent`, `social_agent`, `diff_agent`, `analysis_agent`, `report_agent`) qui mélangeaient logique métier et détails d'infrastructure dans les mêmes fichiers : appels `requests`/`BeautifulSoup` pour le scraping, SDK `anthropic` pour les LLM, `smtplib`/webhooks pour les notifications, tout directement dans les fonctions `run_*()` appelées par les nœuds LangGraph de `main.py`.

Conséquence directe : aucun use case n'était testable sans réseau ni clé API OpenRouter, et remplacer un fournisseur (moteur de recherche, LLM, canal de notification) impliquait de modifier la logique métier elle-même.

## Décision

Réorganiser le code en trois couches :

- `domain/` — entités métier (dataclasses gelées) et ports (`Protocol`) que le domaine attend des adapters, sans aucune dépendance externe.
- `application/` — un use case par étape du pipeline (`DiscoveryService`, `ScraperService`, `SocialService`, `DiffService`, `AnalysisService`, `ReportService`, `NotificationService`), qui orchestrent les ports sans connaître leur implémentation concrète.
- `adapters/` — implémentations concrètes des ports (`adapters/llm/openrouter.py`, `adapters/search/duckduckgo.py`, `adapters/web/scraper.py`, `adapters/social/scraper.py`, `adapters/storage/*`, `adapters/notify/*`).

`main.py` et `ui/api.py` deviennent les composition roots : ils instancient les adapters concrets et les injectent dans les use cases. Le `StateGraph` LangGraph transporte désormais des entités du domaine (`Competitor`, `WebData`, `StrategicAnalysis`...) directement dans son état, plutôt que des dicts non typés.

La migration s'est faite agent par agent, avec un commit par étape et des conversions temporaires vers un format dict "legacy" pour garder l'application fonctionnelle entre chaque commit, jusqu'à un commit final de nettoyage supprimant tous les ponts.

## Conséquences

- Chaque use case est testable avec de faux ports (`FakeLLM`, `FakeSnapshotRepository`, `FakeWebScraper`...), sans réseau ni clé API — voir `tests/test_*.py` pour `application/*`.
- Remplacer un fournisseur (ex. changer de moteur de recherche, ajouter un canal de notification) ne touche qu'un adapter, jamais la logique métier.
- `tests/test_pipeline_integration.py` fait tourner le pipeline complet de bout en bout avec des doubles de ports injectés via `main.run(..., services=...)`.
- Plus de fichiers et plus d'indirection qu'une organisation par script — un compromis jugé acceptable dès que les use cases doivent être testés isolément ou que les fournisseurs externes sont susceptibles de changer.
- Si le projet grossit encore (nouveaux use cases, nouveaux adapters), suivre le même découpage plutôt que d'ajouter de la logique directement dans `main.py`/`ui/api.py`.
