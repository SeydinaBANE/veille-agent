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
| **Nouveau scan** | Lancer un scan, configurer la planification automatique |
| **Rapports** | Consulter et télécharger les rapports Markdown générés |
| **Concurrents** | Liste des concurrents suivis avec date de dernier scan |
| **Historique** | Tous les scans passés avec durée et nombre de changements détectés |

### Planification automatique

Depuis la page "Nouveau scan", active le scan automatique en choisissant un secteur, un jour et une heure. La config est persistée dans `storage/schedule.json`.

### Notifications

Quand un concurrent atteint un score ≥ 7/10, une alerte est envoyée automatiquement. Configure les canaux dans `.env` :

| Variable | Canal |
|---|---|
| `SMTP_USER` / `SMTP_PASS` / `NOTIFY_EMAIL` | Email (Gmail SMTP) |
| `SLACK_WEBHOOK_URL` | Slack |
| `DISCORD_WEBHOOK_URL` | Discord |

Les 3 sont optionnels — seuls les canaux configurés reçoivent la notification.

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
│   ├── api.py               # Backend FastAPI (routes + scheduler)
│   └── templates/
│       └── index.html       # Frontend SPA vanilla JS
├── notifier/
│   └── notify.py            # Notifications Email / Slack / Discord
├── discovery_agent/         # Identification des concurrents
├── scraper_agent/           # Scraping web
├── social_agent/            # Scraping LinkedIn & Twitter
├── diff_agent/              # Détection de changements
├── analysis_agent/          # Analyse stratégique LLM
├── report_agent/            # Génération du rapport
├── storage/
│   ├── snapshot.py          # CRUD JSON des snapshots
│   ├── snapshots/           # Données persistées par concurrent
│   └── schedule.json        # Config planification automatique
└── output/reports/          # Rapports générés
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Clé API OpenRouter (obligatoire) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | Config SMTP pour les notifications email |
| `NOTIFY_EMAIL` | Destinataire des alertes email |
| `SLACK_WEBHOOK_URL` | Webhook Slack |
| `DISCORD_WEBHOOK_URL` | Webhook Discord |

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
