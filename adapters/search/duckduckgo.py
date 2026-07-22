"""Adapter de recherche — implémente SearchEngine via l'API DuckDuckGo."""

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; veille-agent/1.0)"}


class DuckDuckGoSearchEngine:
    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _fetch(self, query: str) -> dict:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            headers=_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def search(self, query: str) -> str:
        try:
            data = self._fetch(query)
        except requests.RequestException as e:
            return f"Recherche web indisponible : {e}"

        results: list[str] = []
        if data.get("AbstractText"):
            results.append(data["AbstractText"])
        for topic in data.get("RelatedTopics", [])[:8]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])

        return "\n".join(results) if results else "Pas de résultats DuckDuckGo."
