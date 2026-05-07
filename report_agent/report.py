"""
Report Agent — Génère le rapport Markdown hebdomadaire
Model: Claude Sonnet 4.6 (rédaction)
"""

import anthropic
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

SYSTEM_PROMPT = """Réponds toujours en français.
Tu es un rédacteur de rapports de veille concurrentielle.
Génère un rapport Markdown professionnel, clair et actionnable.

Structure du rapport :
# Rapport de veille — [date]
## Résumé exécutif (3-4 phrases)
## Signaux prioritaires (concurrents avec score >= 7)
## Changements notables (autres concurrents)
## Concurrents stables (aucun changement)
## Recommandations cette semaine (top 3 actions)

Sois concis, factuel, orienté action. Utilise des tableaux Markdown quand pertinent.
"""


def run_report(sector: str, analysis: dict, diffs: list[dict]) -> str:
    """Génère le rapport final et le sauvegarde."""

    client = anthropic.Anthropic(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api",
    )

    # Prépare le contexte
    context = f"Secteur surveillé : {sector}\n"
    context += f"Date du scan : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    context += f"Résumé analyse : {analysis.get('summary', '')}\n\n"

    if analysis.get("competitors"):
        context += "Analyse par concurrent :\n"
        for c in analysis["competitors"]:
            context += f"\n**{c['name']}** (score: {c.get('score', '?')}/10, priorité: {c.get('priority', '?')})\n"
            context += f"- Signal : {c.get('signal_type', '')}\n"
            context += f"- Interprétation : {c.get('interpretation', '')}\n"
            context += f"- Action recommandée : {c.get('recommended_action', '')}\n"

    if analysis.get("no_changes"):
        context += f"\nConcurrents sans changement : {', '.join(analysis['no_changes'])}\n"

    message = client.messages.create(
        model="anthropic/claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Génère le rapport de veille à partir de ces données :\n\n{context}"
        }]
    )

    report_content = message.content[0].text

    # Sauvegarde
    output_dir = Path(__file__).parent.parent / "output" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    sector_slug = sector.lower().replace(" ", "_")[:20]
    report_path = output_dir / f"rapport_{date_str}_{sector_slug}.md"

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"   📄 Rapport sauvegardé : {report_path}")
    return str(report_path)
