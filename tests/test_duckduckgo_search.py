from unittest.mock import MagicMock, patch

import requests

from adapters.search.duckduckgo import DuckDuckGoSearchEngine

# tenacity attache .retry au niveau du wrapper, invisible pour mypy sur la signature décorée
DuckDuckGoSearchEngine._fetch.retry.sleep = lambda _seconds: None  # type: ignore[attr-defined]


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    return response


def test_search_combines_abstract_and_related_topics() -> None:
    engine = DuckDuckGoSearchEngine()
    data = {
        "AbstractText": "Résumé du secteur",
        "RelatedTopics": [{"Text": "Concurrent A"}, {"Text": "Concurrent B"}, "ignoré (pas un dict)"],
    }
    with patch("requests.get", return_value=_mock_response(data)):
        result = engine.search("fintech SaaS")

    assert "Résumé du secteur" in result
    assert "Concurrent A" in result
    assert "Concurrent B" in result


def test_search_returns_fallback_when_no_results() -> None:
    engine = DuckDuckGoSearchEngine()
    with patch("requests.get", return_value=_mock_response({})):
        result = engine.search("secteur obscur")

    assert result == "Pas de résultats DuckDuckGo."


def test_search_returns_fallback_message_on_network_error() -> None:
    engine = DuckDuckGoSearchEngine()
    with patch("requests.get", side_effect=requests.ConnectionError("dns failure")):
        result = engine.search("fintech SaaS")

    assert "Recherche web indisponible" in result
