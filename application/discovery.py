"""Use case — identifie les concurrents d'un secteur via recherche web + LLM."""

import json
import re

from domain.models import Competitor
from domain.ports import LLMClient, SearchEngine

_SYSTEM_PROMPT = """Tu es un analyste de veille concurrentielle.
À partir d'un secteur ou mot-clé, identifie les principaux concurrents à surveiller.

Pour chaque concurrent retourne :
- name : nom de l'entreprise
- website : URL du site principal (https://...)
- linkedin : URL page LinkedIn company (https://linkedin.com/company/...)
- twitter : handle Twitter sans @ (ex: stripe)
- description : 1 phrase sur ce qu'ils font

Réponds UNIQUEMENT avec un tableau JSON valide, sans markdown, sans explication.
Exemple : [{"name":"Stripe","website":"https://stripe.com","linkedin":"https://linkedin.com/company/stripe","twitter":"stripe","description":"Paiement en ligne pour développeurs"}]
"""


class DiscoveryService:
    def __init__(self, llm: LLMClient, search: SearchEngine) -> None:
        self._llm = llm
        self._search = search

    def discover(self, sector: str, max_competitors: int) -> list[Competitor]:
        web_context = self._search.search(f"{sector} entreprises concurrents top 2025")

        prompt = f"""Secteur/mot-clé : {sector}

Contexte web trouvé :
{web_context}

Identifie {max_competitors} concurrents clés à surveiller dans ce secteur.
Réponds uniquement avec le JSON."""

        raw = self._llm.complete(system=_SYSTEM_PROMPT, prompt=prompt, max_tokens=1000)
        raw = re.sub(r"```json|```", "", raw).strip()

        return self._parse_competitors(raw)

    @staticmethod
    def _parse_competitors(raw: str) -> list[Competitor]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = []
            for match in re.findall(r"\{[^}]+\}", raw):
                try:
                    payload.append(json.loads(match))
                except json.JSONDecodeError:
                    continue

        return [
            Competitor(
                name=item.get("name", "inconnu"),
                website=item.get("website", ""),
                linkedin=item.get("linkedin", ""),
                twitter=item.get("twitter", ""),
                description=item.get("description", ""),
            )
            for item in payload
        ]
