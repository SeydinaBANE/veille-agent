"""Use case — score et interprète les changements stratégiques des concurrents."""

import json
import re

from domain.models import CompetitorAnalysis, CompetitorDiff, Priority, StrategicAnalysis
from domain.ports import LLMClient

_SYSTEM_PROMPT = """Réponds toujours en français.
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


class AnalysisService:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def analyze(self, diffs: list[CompetitorDiff]) -> StrategicAnalysis:
        with_changes = [d for d in diffs if d.has_changes]
        without_changes = [d for d in diffs if not d.has_changes]
        no_changes_names = [d.name for d in without_changes]

        if not with_changes:
            return StrategicAnalysis(
                competitors=[],
                summary="Aucun changement significatif détecté cette semaine.",
                no_changes=no_changes_names,
            )

        prompt = self._build_prompt(with_changes)
        raw = self._llm.complete(system=_SYSTEM_PROMPT, prompt=prompt, max_tokens=1500)
        raw = re.sub(r"```json|```", "", raw).strip()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return StrategicAnalysis(
                competitors=[],
                summary=raw[:500],
                no_changes=no_changes_names,
                parse_error=True,
            )

        competitors = [
            CompetitorAnalysis(
                name=item.get("name", "inconnu"),
                score=item.get("score", 0),
                signal_type=item.get("signal_type", ""),
                interpretation=item.get("interpretation", ""),
                recommended_action=item.get("recommended_action", ""),
                priority=self._parse_priority(item.get("priority")),
            )
            for item in payload.get("competitors", [])
        ]

        return StrategicAnalysis(
            competitors=competitors,
            summary=payload.get("summary", ""),
            no_changes=no_changes_names,
        )

    @staticmethod
    def _parse_priority(value: str | None) -> Priority:
        try:
            return Priority(value)
        except ValueError:
            return Priority.FAIBLE

    @staticmethod
    def _build_prompt(with_changes: list[CompetitorDiff]) -> str:
        context_parts: list[str] = []
        for diff in with_changes:
            part = f"### {diff.name}\nChangements détectés :\n"
            for change in diff.changes:
                part += f"- [{change.change_type.value}] {change.description}\n"

            if diff.snapshot.pricing:
                part += f"\nExtrait pricing actuel :\n{diff.snapshot.pricing[:400]}\n"

            if diff.snapshot.twitter_posts:
                part += "\nPosts Twitter récents :\n"
                for post in diff.snapshot.twitter_posts[:2]:
                    part += f"- {post[:200]}\n"

            context_parts.append(part)

        context = "\n\n".join(context_parts)
        return f"""Voici les changements détectés cette semaine chez nos concurrents :

{context}

Analyse ces signaux et retourne le JSON d'analyse stratégique."""
