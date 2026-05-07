"""
Analysis Agent — Score les changements, détecte les signaux forts
Model: Claude Opus 4.6 (raisonnement frontier)
"""

import anthropic
import os
import json
import re
from dotenv import load_dotenv
load_dotenv()

SYSTEM_PROMPT = """Réponds toujours en français.
Tu es un analyste stratégique spécialisé en veille concurrentielle.

Pour chaque concurrent, analyse les changements détectés et :
1. Score l'importance du changement (1-10)
2. Identifie le type de signal (offensive, défensive, pivot, expansion...)
3. Propose une interprétation stratégique
4. Suggère une action recommandée pour y répondre

Réponds UNIQUEMENT avec un JSON valide :
{
  "competitors": [
    {
      "name": "...",
      "score": 7,
      "signal_type": "offensive",
      "interpretation": "...",
      "recommended_action": "...",
      "priority": "haute|moyenne|faible"
    }
  ],
  "summary": "Résumé global en 2-3 phrases"
}
"""


def run_analysis(diffs: list[dict]) -> dict:
    """Analyse et score tous les changements détectés."""

    # Ne garde que les concurrents avec des changements
    with_changes = [d for d in diffs if d.get("has_changes")]
    without_changes = [d for d in diffs if not d.get("has_changes")]

    if not with_changes:
        return {
            "competitors": [],
            "summary": "Aucun changement significatif détecté cette semaine.",
            "no_changes": [d["name"] for d in without_changes]
        }

    client = anthropic.Anthropic(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api",
    )

    # Prépare le contexte pour l'analyse
    context_parts = []
    for diff in with_changes:
        name = diff["name"]
        changes = diff["changes"]
        data = diff.get("data", {})

        part = f"### {name}\n"
        part += f"Changements détectés :\n"
        for c in changes:
            part += f"- [{c['type']}] {c['description']}\n"

        if data.get("pricing"):
            part += f"\nExtrait pricing actuel :\n{data['pricing'][:400]}\n"

        if data.get("twitter_posts"):
            part += f"\nPosts Twitter récents :\n"
            for p in data["twitter_posts"][:2]:
                part += f"- {p[:200]}\n"

        context_parts.append(part)

    context = "\n\n".join(context_parts)

    message = client.messages.create(
        model="anthropic/claude-opus-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Voici les changements détectés cette semaine chez nos concurrents :

{context}

Analyse ces signaux et retourne le JSON d'analyse stratégique."""
        }]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        analysis = json.loads(raw)
        analysis["no_changes"] = [d["name"] for d in without_changes]
        return analysis
    except json.JSONDecodeError:
        return {
            "competitors": [],
            "summary": raw[:500],
            "no_changes": [d["name"] for d in without_changes],
            "parse_error": True
        }
