"""Adapter de recherche — implémente SearchEngine via l'API DuckDuckGo."""

import requests

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; veille-agent/1.0)"}


class DuckDuckGoSearchEngine:
    def search(self, query: str) -> str:
        try:
            response = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
                headers=_HEADERS,
                timeout=10,
            )
            data = response.json()
        except requests.RequestException as e:
            return f"Recherche web indisponible : {e}"

        results: list[str] = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:8]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])

        return "\n".join(results) if results else "Pas de résultats DuckDuckGo."
