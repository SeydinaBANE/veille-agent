"""
Discovery Agent — Identifie les concurrents via DuckDuckGo + LLM
Model: Claude Haiku (rapide)
"""

import anthropic
import os
import json
import requests
import re
from dotenv import load_dotenv
load_dotenv()

SYSTEM_PROMPT = """Tu es un analyste de veille concurrentielle. 
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


def search_sector(sector: str) -> str:
    """Recherche DuckDuckGo pour trouver des acteurs du secteur."""
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": f"{sector} entreprises concurrents top 2025", "format": "json", "no_html": "1"},
            headers={"User-Agent": "Mozilla/5.0 (compatible; veille-agent/1.0)"},
            timeout=10
        )
        data = response.json()
        results = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:8]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])
        return "\n".join(results) if results else "Pas de résultats DuckDuckGo."
    except Exception as e:
        return f"Recherche web indisponible : {e}"


def run_discovery(sector: str, max_competitors: int = 5) -> list[dict]:
    print(f"   🔍 Recherche des concurrents pour : '{sector}'...")

    web_context = search_sector(sector)

    client = anthropic.Anthropic(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api",
    )

    message = client.messages.create(
        model="anthropic/claude-haiku-4-5",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""Secteur/mot-clé : {sector}

Contexte web trouvé :
{web_context}

Identifie {max_competitors} concurrents clés à surveiller dans ce secteur.
Réponds uniquement avec le JSON."""
        }]
    )

    raw = message.content[0].text.strip()

    # Nettoie le JSON si besoin
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        competitors = json.loads(raw)
        print(f"   ✅ {len(competitors)} concurrents identifiés")
        return competitors
    except json.JSONDecodeError:
        print(f"   ⚠️  Erreur parsing JSON, extraction manuelle...")
        # Fallback : extraction regex
        matches = re.findall(r'\{[^}]+\}', raw)
        result = []
        for m in matches:
            try:
                result.append(json.loads(m))
            except:
                pass
        return result if result else []
