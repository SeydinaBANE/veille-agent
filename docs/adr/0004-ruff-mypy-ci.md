# ADR 0004: ruff + mypy comme linter/typechecker, appliqués en CI

## Statut

Acceptée

## Contexte

Les instructions globales du projet (`CLAUDE.md`) exigent de faire tourner un linter et un typechecker avec zéro erreur avant chaque commit. Pourtant, aucun des deux n'était configuré dans ce dépôt, depuis sa création — l'exigence n'avait jamais pu être satisfaite faute d'outillage.

## Décision

Adopter `ruff` (lint) et `mypy` (typecheck) en dépendances de développement (`pyproject.toml`, groupe `dev`), avec une configuration minimale (`[tool.ruff]`, `[tool.mypy]`, longueur de ligne 120, `check_untyped_defs = true`). Corriger l'intégralité des signalements remontés par leur premier passage sur la base hexagonale (33 signalements : imports non triés, `StrEnum` au lieu de `(str, Enum)`, narrowing de type sur les blocs de réponse Anthropic, annotations manquantes...). Ajouter un workflow GitHub Actions (`.github/workflows/ci.yml`) qui exécute `ruff check`, `mypy` et `pytest` sur chaque push/PR vers `main`.

## Conséquences

- Les dérives de typage ou de style sont détectées automatiquement dès la CI, avant revue humaine.
- Quelques `# noqa: E402` restent nécessaires dans `main.py`/`ui/api.py`, où les imports suivent intentionnellement `sys.path.insert()` et `configure_logging()` — documentés inline, pas de contournement silencieux.
- `uv run ruff check .` et `uv run mypy .` doivent rester à zéro erreur avant tout commit (cf. `CLAUDE.md`).
