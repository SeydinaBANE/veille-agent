# Veille Agent

![CI](https://github.com/SeydinaBANE/veille-agent/actions/workflows/ci.yml/badge.svg)

Pipeline de veille concurrentielle automatisé, orchestré avec **LangGraph**. À partir d'un secteur ou mot-clé, il identifie les concurrents, scrape leurs sites et réseaux sociaux, détecte les changements par rapport aux scans précédents, et produit un rapport Markdown stratégique.

## Architecture

Le pipeline suit une **architecture hexagonale (ports & adapters)** : le domaine et les use cases ne dépendent d'aucune infrastructure concrète, qui est injectée via des interfaces (`Protocol`).

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

```
domain/       entités métier (dataclasses) + ports (interfaces)
application/  use cases — un par étape du pipeline, orchestrent les ports
adapters/     implémentations concrètes (LLM, scraping, stockage, notifications)
```

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

`GET /api/health` renvoie `{"status": "ok"}` — utilisé par le `HEALTHCHECK` Docker/Compose, sans dépendance externe.

Par défaut, l'API n'accepte que les requêtes CORS depuis `http://localhost:8000` (configurable via `ALLOWED_ORIGINS`). Un scan est borné à 1-20 concurrents et un secteur de 1-100 caractères (`422` sinon), pour éviter un déclenchement démesuré et coûteux en appels LLM.

### Planification automatique

Depuis la page "Nouveau scan", active le scan automatique en choisissant un secteur, un jour et une heure. La config est persistée dans `storage/schedule.json`.

### Notifications

Quand un concurrent atteint un score ≥ 7/10, une alerte est envoyée automatiquement. Configure les canaux dans `.env` :

| Variable | Canal |
|---|---|
| `SMTP_USER` / `SMTP_PASS` / `NOTIFY_EMAIL` | Email (Gmail SMTP) |
| `SLACK_WEBHOOK_URL` | Slack |
| `DISCORD_WEBHOOK_URL` | Discord |

Les 3 sont optionnels — seuls les canaux configurés reçoivent la notification (chaque échec d'envoi est loggé mais n'interrompt jamais le scan).

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

## Déploiement Docker

```bash
docker compose up --build
```

Sert l'interface web sur `http://localhost:8000`. Le conteneur :

- tourne en utilisateur non-root (`appuser`, UID 1000) ;
- expose un `HEALTHCHECK` (`GET /api/health`, toutes les 30s) — visible via `docker compose ps` ;
- redémarre automatiquement (`restart: unless-stopped`) ;
- persiste `storage/snapshots/` et `output/reports/` via des volumes montés depuis l'hôte.

Les variables d'environnement viennent du `.env` à la racine (`env_file` dans `docker-compose.yml`). Pour construire l'image seule : `docker build -t veille-agent .`.

## Qualité de code & CI

```bash
uv run ruff check .   # lint
uv run mypy .         # typecheck
uv run pytest         # tests unitaires
```

Un workflow GitHub Actions (`.github/workflows/ci.yml`) exécute ces trois commandes sur chaque push/PR vers `main`.

## Structure

```
veille-agent/
├── main.py                          # Composition root CLI + StateGraph LangGraph
├── logging_config.py                # Configuration centralisée du logging
├── healthcheck.py                   # Script appelé par le HEALTHCHECK Docker
├── ui/
│   ├── api.py                       # Composition root FastAPI (routes + scheduler)
│   └── templates/
│       └── index.html               # Frontend SPA vanilla JS
├── domain/
│   ├── models.py                    # Entités (Competitor, WebData, StrategicAnalysis...)
│   ├── ports.py                     # Interfaces attendues des adapters (Protocol)
│   └── notification.py              # Formatage pur du message de notification
├── application/                     # Use cases — un par étape du pipeline
│   ├── discovery.py / scraper.py / social.py
│   ├── diff.py / analysis.py / report.py
│   └── notify.py
├── adapters/                        # Implémentations concrètes des ports
│   ├── llm/openrouter.py            # LLMClient via OpenRouter (retry/backoff)
│   ├── search/duckduckgo.py         # SearchEngine (retry/backoff)
│   ├── web/scraper.py               # WebScraper
│   ├── social/scraper.py            # SocialScraper (LinkedIn, Twitter/Nitter)
│   ├── storage/                     # SnapshotRepository, ReportRepository (JSON/Markdown)
│   └── notify/                      # Notifier (email SMTP, Slack, Discord, composite)
├── tests/                           # Tests unitaires + intégration
├── .github/workflows/ci.yml         # Lint (ruff) + typecheck (mypy) + tests sur push/PR
├── Dockerfile / docker-compose.yml  # Image non-root + healthcheck
├── storage/
│   ├── snapshots/                   # Données persistées par concurrent
│   └── schedule.json                # Config planification automatique
└── output/reports/                  # Rapports générés
```

## Tests

```bash
uv run pytest
```

Les use cases (`application/*`) sont testés avec des doubles de ports (`FakeLLM`, `FakeSnapshotRepository`...). Les adapters concrets (`adapters/*`) sont testés en mockant la librairie externe (`requests`, `smtplib`, SDK Anthropic) — jamais notre propre code.

## Observabilité & résilience

- **Logging** : tous les modules loggent via `logging` (configuré une fois dans `logging_config.py`, appelé depuis `main.py` et `ui/api.py`) — plus de `print()`.
- **Retry/backoff** : les appels réseau vers OpenRouter (LLM) et DuckDuckGo (recherche) retentent automatiquement jusqu'à 3 fois avec un backoff exponentiel (1 à 8s) sur les erreurs transitoires (timeout, connexion, rate limit, 5xx).
- **Fail-fast** : si `OPENROUTER_API_KEY` est absente, le pipeline échoue immédiatement avec un message explicite plutôt qu'un `KeyError`.

## Variables d'environnement

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Clé API OpenRouter (obligatoire) |
| `ALLOWED_ORIGINS` | Origines CORS autorisées pour l'API web, séparées par des virgules (défaut : `http://localhost:8000`) |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` | Config SMTP pour les notifications email |
| `NOTIFY_EMAIL` | Destinataire des alertes email |
| `SLACK_WEBHOOK_URL` | Webhook Slack |
| `DISCORD_WEBHOOK_URL` | Webhook Discord |
| `PORT` | Port d'écoute HTTP en conteneur (défaut : `8000`) |

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

[MIT](LICENSE)
