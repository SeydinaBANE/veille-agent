# Veille Agent

Pipeline de veille concurrentielle automatisé, orchestré avec **LangGraph**. À partir d'un secteur ou mot-clé, il identifie les concurrents, scrape leurs sites et réseaux sociaux, détecte les changements par rapport aux scans précédents, et produit un rapport Markdown stratégique.

## Architecture

```
discovery → scraper → social → diff → analysis → report
```

| Étape | Rôle | LLM |
|---|---|---|
| **Discovery** | Identifie les concurrents via DuckDuckGo + LLM | Claude Haiku |
| **Scraper** | Scrape homepage, pricing, blog de chaque site | — |
| **Social** | Récupère les posts LinkedIn & Twitter/X publics | — |
| **Diff** | Compare avec les snapshots précédents, détecte les changements | — |
| **Analysis** | Score les signaux, interprétation stratégique | Claude Opus |
| **Report** | Génère le rapport Markdown final | Claude Sonnet |

Les snapshots sont persistés dans `storage/snapshots/` entre les exécutions — le premier scan crée la baseline, les suivants produisent de vrais diffs.

## Prérequis

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- Une clé [OpenRouter](https://openrouter.ai) (accès aux modèles Anthropic)

## Installation

```bash
git clone https://github.com/SeydinaBANE/veille-agent.git
cd veille-agent
uv sync
cp .env.example .env
# Renseigner OPENROUTER_API_KEY dans .env
```

## Interface web

```bash
uv run uvicorn ui.api:app --reload --port 8000
```

Ouvre `http://localhost:8000` — 4 pages disponibles :

| Page | Rôle |
|---|---|
| **Nouveau scan** | Lancer un scan par secteur, suivre la progression en temps réel |
| **Rapports** | Consulter et lire les rapports Markdown générés |
| **Concurrents** | Liste des concurrents suivis avec date de dernier scan |
| **Historique** | Tous les scans passés avec durée et nombre de changements détectés |

## Utilisation CLI

```bash
# Secteur par défaut
uv run python main.py

# Secteur personnalisé
uv run python main.py "paiement en ligne SaaS"
uv run python main.py "CRM B2B France"
uv run python main.py "cybersécurité PME"
```

Le rapport est généré dans `output/reports/rapport_<date>_<secteur>.md`.

## Structure

```
veille-agent/
├── main.py                  # Orchestration LangGraph (StateGraph)
├── ui/
│   ├── api.py               # Backend FastAPI (7 routes)
│   └── templates/
│       └── index.html       # Frontend SPA vanilla JS
├── discovery_agent/         # Identification des concurrents
├── scraper_agent/           # Scraping web
├── social_agent/            # Scraping LinkedIn & Twitter
├── diff_agent/              # Détection de changements
├── analysis_agent/          # Analyse stratégique LLM
├── report_agent/            # Génération du rapport
├── storage/
│   ├── snapshot.py          # CRUD JSON des snapshots
│   └── snapshots/           # Données persistées par concurrent
└── output/reports/          # Rapports générés
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Clé API OpenRouter (obligatoire) |

## Exemple de rapport généré

```
# Rapport de veille — 07/05/2026

## Résumé exécutif
Stripe a modifié sa page de tarification et publié 3 nouveaux articles...

## Signaux prioritaires
| Concurrent | Score | Signal | Priorité |
|---|---|---|---|
| Stripe | 8/10 | offensive | haute |

## Recommandations
1. Analyser la nouvelle grille tarifaire Stripe...
```

## Licence

MIT
