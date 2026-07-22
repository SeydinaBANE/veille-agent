# CLAUDE.md

Ce fichier fournit des instructions à Claude Code (claude.ai/code) pour travailler dans ce dépôt.

## Installation

Les dépendances sont gérées avec `uv`. Installer et lancer :

```bash
uv sync                              # installe les dépendances
uv run python main.py "fintech SaaS" # lance un scan de veille
```

Copier `.env.example` vers `.env` et renseigner `OPENROUTER_API_KEY`. Tous les appels LLM passent par [OpenRouter](https://openrouter.ai) via le SDK Anthropic avec un `base_url` personnalisé.

## Lancer l'UI

```bash
uv run uvicorn ui.api:app --reload --port 8000
# → http://localhost:8000
```

L'interface expose 4 pages : **Nouveau scan**, **Rapports**, **Concurrents**, **Historique**.  
Le backend FastAPI lance le pipeline en tâche de fond et expose son état via `/api/scan/status` (polling toutes les 2s).

## Lancer le pipeline (CLI)

```bash
# Secteur par défaut
uv run python main.py

# Secteur personnalisé (les arguments CLI sont joints en une chaîne)
uv run python main.py "paiement en ligne SaaS"
uv run python main.py "CRM B2B France"
```

Les rapports sont écrits dans `output/reports/rapport_<date>_<secteur>.md`. Les snapshots (état de référence pour la détection de changements) sont stockés dans `storage/snapshots/<slug_concurrent>.json` et mis à jour à chaque exécution.

## Architecture

Le pourquoi des décisions structurantes (pas seulement le quoi) est documenté dans `docs/adr/` — s'y référer avant de remettre en cause un choix existant, et y ajouter une entrée pour toute nouvelle décision d'architecture significative (voir `docs/adr/template.md`).

Le projet suit une **architecture hexagonale (ports & adapters)** :

```
domain/       entités métier (dataclasses) + ports (Protocol) — aucune dépendance externe
application/  use cases : orchestrent les ports, aucune dépendance à une infra concrète
adapters/     implémentations concrètes des ports (LLM, scraping, stockage, notifications)
main.py       composition root : instancie les adapters, les injecte dans les use cases,
              orchestre le tout via un StateGraph LangGraph
ui/api.py     composition root du backend FastAPI (mêmes use cases, exposés en HTTP)
```

Le pipeline est un **`StateGraph` LangGraph** défini dans `main.py`. Les nœuds s'exécutent séquentiellement :

```
discovery → scraper → social → diff → analysis → report
```

L'état partagé (`VeilleState`) transmet les entités du domaine entre les nœuds sous forme de TypedDict (`list[Competitor]`, `list[WebData]`, `StrategicAnalysis`...). Chaque nœud modifie l'état en place et ajoute une `StepTrace` (durée + détail) dans `state["trace"]`. La progression est aussi remontée via le callback `on_step`, utilisé par `ui/api.py` pour le polling `/api/scan/status`.

| Couche | Fichier | Rôle | LLM |
|---|---|---|---|
| `application/discovery.py` | `DiscoveryService` | Trouve les concurrents via `SearchEngine` + `LLMClient` | Claude Haiku (rapide) |
| `application/scraper.py` | `ScraperService` | Scrape la homepage, `/pricing`, `/blog` via `WebScraper` | aucun |
| `application/social.py` | `SocialService` | Scrape LinkedIn + Twitter via `SocialScraper` | aucun |
| `application/diff.py` | `DiffService` | Compare les nouvelles données aux snapshots via `SnapshotRepository` | aucun |
| `application/analysis.py` | `AnalysisService` | Score et interprète les changements stratégiques | Claude Opus |
| `application/report.py` | `ReportService` | Génère le rapport Markdown via `ReportRepository` | Claude Sonnet |
| `application/notify.py` | `NotificationService` | Filtre les signaux prioritaires (score ≥ 7) et notifie via `Notifier` | aucun |

Adapters correspondants : `adapters/llm/openrouter.py` (LLMClient), `adapters/search/duckduckgo.py` (SearchEngine), `adapters/web/scraper.py` (WebScraper), `adapters/social/scraper.py` (SocialScraper), `adapters/storage/snapshot_repository.py` + `report_repository.py` (SnapshotRepository / ReportRepository), `adapters/notify/*` (Notifier — email SMTP, Slack, Discord, composite).

Les ports sont définis dans `domain/ports.py` (des `Protocol`, pas des classes de base) ; les entités dans `domain/models.py`.

## Qualité de code

```bash
uv run ruff check .  # lint — zéro erreur avant de committer
uv run mypy .         # typecheck — zéro erreur avant de committer
```

Un workflow GitHub Actions (`.github/workflows/ci.yml`) exécute ruff, mypy et pytest sur chaque push/PR vers `main`.

## Tests

```bash
uv run pytest
```

Deux niveaux de tests, jamais de mock sur notre propre code :

- **Use cases** (`application/*`) : testés avec de faux ports injectés directement (`FakeLLM`, `FakeSnapshotRepository`, `FakeWebScraper`...), aucun appel réseau.
- **Adapters concrets** (`adapters/*`) : testés en mockant la librairie externe qu'ils enveloppent (`requests.get`/`post`, `smtplib.SMTP`, le SDK `anthropic`) — voir `tests/test_openrouter_llm.py`, `tests/test_web_scraper.py`, `tests/test_social_scraper.py`, `tests/test_*_notifier.py`.
- `tests/test_pipeline_integration.py` fait tourner `main.run()` de bout en bout avec des doubles de ports injectés via le paramètre `services` de `run()`, sans clé API ni appel réseau.

## Détails techniques importants

- **Routage LLM** : `adapters/llm/openrouter.py` utilise `anthropic.Anthropic(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api")` — les noms de modèles utilisent le préfixe `anthropic/` (ex : `anthropic/claude-haiku-4-5`).
- **Logique de diff** : `application/diff.py` (`DiffService._text_changed`) compare les ensembles de mots des 500 premiers caractères ; une similarité < 85 % déclenche un signal de changement. Le premier scan crée toujours une baseline (pas de diff).
- **Scraping social** : LinkedIn utilise la recherche DuckDuckGo en priorité, le scraping direct en fallback. Twitter utilise des instances Nitter publiques avec une liste de fallback.
- **Snapshots** : le port `SnapshotRepository` prend directement le nom du concurrent (pas de slug) ; `adapters/storage/snapshot_repository.py` encapsule le `slugify()` et écrit dans `storage/snapshots/<slug>.json`. Exécuter le pipeline deux fois sur le même concurrent met à jour le snapshot — la deuxième exécution produit de vrais diffs.
- **Retry/backoff** : `adapters/llm/openrouter.py` et `adapters/search/duckduckgo.py` (+ la recherche LinkedIn dans `adapters/social/scraper.py`) retentent jusqu'à 3 fois avec un backoff exponentiel (`tenacity`, 1 à 8s) sur les erreurs réseau transitoires (timeout, connexion, rate limit, 5xx). Les autres échecs (site inaccessible, Nitter down) gardent leur fallback existant sans retry.
- **Logging** : `logging_config.configure_logging()` configure le root logger une seule fois (idempotent), appelé en tête de `main.py` et `ui/api.py`. Chaque module logge via `logging.getLogger(__name__)` — ne pas réintroduire de `print()`.
- **Fail-fast config** : `main.py` (`_get_services`) lève un `RuntimeError` explicite si `OPENROUTER_API_KEY` est absente, plutôt qu'un `KeyError`.
- **API web** : CORS restreint à `ALLOWED_ORIGINS` (défaut `http://localhost:8000`, pas de wildcard) ; `ScanRequest`/`ScheduleConfig` bornent `max_competitors` (1-20), `sector` (1-100 caractères) et `hour` (0-23) via des `Field` pydantic — un dépassement renvoie `422`. `GET /api/health` est sans dépendance externe (utilisé par le `HEALTHCHECK` Docker).
- **Docker** : le conteneur tourne en utilisateur non-root (`appuser`, UID 1000, voir `Dockerfile`) ; `docker-compose.yml` définit un `healthcheck` et `restart: unless-stopped`.
- **Tous les prompts LLM sont en français** — les réponses sont attendues en français.
