"""Use case — génère le rapport Markdown hebdomadaire de veille."""

from datetime import datetime

from domain.models import StrategicAnalysis
from domain.ports import LLMClient, ReportRepository

_SYSTEM_PROMPT = """Réponds toujours en français.
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


class ReportService:
    def __init__(self, llm: LLMClient, repository: ReportRepository) -> None:
        self._llm = llm
        self._repository = repository

    def generate(self, sector: str, analysis: StrategicAnalysis) -> str:
        prompt = self._build_prompt(sector, analysis)
        content = self._llm.complete(system=_SYSTEM_PROMPT, prompt=prompt, max_tokens=2000)
        report_path = self._repository.save(sector, content)
        return str(report_path)

    @staticmethod
    def _build_prompt(sector: str, analysis: StrategicAnalysis) -> str:
        context = f"Secteur surveillé : {sector}\n"
        context += f"Date du scan : {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        context += f"Résumé analyse : {analysis.summary}\n\n"

        if analysis.competitors:
            context += "Analyse par concurrent :\n"
            for c in analysis.competitors:
                context += f"\n**{c.name}** (score: {c.score}/10, priorité: {c.priority.value})\n"
                context += f"- Signal : {c.signal_type}\n"
                context += f"- Interprétation : {c.interpretation}\n"
                context += f"- Action recommandée : {c.recommended_action}\n"

        if analysis.no_changes:
            context += f"\nConcurrents sans changement : {', '.join(analysis.no_changes)}\n"

        return f"Génère le rapport de veille à partir de ces données :\n\n{context}"
