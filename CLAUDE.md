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

## Tests

```bash
uv run pytest        # tests unitaires, chaque use case testé avec des doubles de ports
```

Les tests ne mockent jamais les adapters concrets (requests, smtplib, anthropic) — ils injectent de faux ports (`FakeLLM`, `FakeSnapshotRepository`, etc.) directement dans les services `application/*`.

## Détails techniques importants

- **Routage LLM** : `adapters/llm/openrouter.py` utilise `anthropic.Anthropic(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api")` — les noms de modèles utilisent le préfixe `anthropic/` (ex : `anthropic/claude-haiku-4-5`).
- **Logique de diff** : `application/diff.py` (`DiffService._text_changed`) compare les ensembles de mots des 500 premiers caractères ; une similarité < 85 % déclenche un signal de changement. Le premier scan crée toujours une baseline (pas de diff).
- **Scraping social** : LinkedIn utilise la recherche DuckDuckGo en priorité, le scraping direct en fallback. Twitter utilise des instances Nitter publiques avec une liste de fallback.
- **Snapshots** : le port `SnapshotRepository` prend directement le nom du concurrent (pas de slug) ; `adapters/storage/snapshot_repository.py` encapsule le `slugify()` et écrit dans `storage/snapshots/<slug>.json`. Exécuter le pipeline deux fois sur le même concurrent met à jour le snapshot — la deuxième exécution produit de vrais diffs.
- **Tous les prompts LLM sont en français** — les réponses sont attendues en français.
