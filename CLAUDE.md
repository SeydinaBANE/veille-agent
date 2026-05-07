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

Le pipeline est un **`StateGraph` LangGraph** défini dans `main.py`. Les nœuds s'exécutent séquentiellement :

```
discovery → scraper → social → diff → analysis → report
```

L'état partagé (`VeilleState`) transmet les données entre les nœuds sous forme de TypedDict. Chaque nœud modifie l'état en place et ajoute des métriques de durée dans `state["trace"]`.

Chaque étape du pipeline vit dans son propre package :

| Package | Fichier | Rôle | LLM |
|---|---|---|---|
| `discovery_agent` | `discovery.py` | Trouve les concurrents via DuckDuckGo + LLM | Claude Haiku (rapide) |
| `scraper_agent` | `scraper.py` | Scrape la homepage, `/pricing`, `/blog` | aucun |
| `social_agent` | `social.py` | Scrape LinkedIn (via DuckDuckGo) + Twitter (via Nitter) | aucun |
| `diff_agent` | `diff.py` | Compare les nouvelles données aux snapshots stockés | aucun |
| `analysis_agent` | `analysis.py` | Score et interprète les changements stratégiques | Claude Opus |
| `report_agent` | `report.py` | Génère le rapport Markdown | Claude Sonnet |
| `storage` | `snapshot.py` | CRUD JSON des snapshots + `slugify()` | aucun |

## Détails techniques importants

- **Routage LLM** : `anthropic.Anthropic(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api")` — les noms de modèles utilisent le préfixe `anthropic/` (ex : `anthropic/claude-haiku-4-5`).
- **Logique de diff** : `diff_agent/diff.py` compare les ensembles de mots des 500 premiers caractères ; une similarité < 85 % déclenche un signal de changement. Le premier scan crée toujours une baseline (pas de diff).
- **Scraping social** : LinkedIn utilise la recherche DuckDuckGo en priorité, le scraping direct en fallback. Twitter utilise des instances Nitter publiques avec une liste de fallback.
- **Snapshots** : nommés `storage/snapshots/<slug>.json` où slug = `slugify(nom_concurrent)`. Exécuter le pipeline deux fois sur le même concurrent met à jour le snapshot — la deuxième exécution produit de vrais diffs.
- **Tous les prompts LLM sont en français** — les réponses sont attendues en français.
