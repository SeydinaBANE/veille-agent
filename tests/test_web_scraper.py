from unittest.mock import MagicMock, patch

import requests

from adapters.web.scraper import HttpWebScraper
from domain.models import Competitor


def _competitor(website: str = "https://example.com") -> Competitor:
    return Competitor(name="Exemple", website=website, linkedin="", twitter="", description="")


def _html_response(body: str) -> MagicMock:
    response = MagicMock()
    response.text = f"<html><body>{body}</body></html>"
    response.raise_for_status.return_value = None
    return response


def test_scrape_without_website_returns_error() -> None:
    scraper = HttpWebScraper()

    result = scraper.scrape(_competitor(website=""))

    assert result.website is None
    assert result.error == "pas d'URL"


def test_scrape_extracts_homepage_pricing_and_blog_titles() -> None:
    scraper = HttpWebScraper()
    long_pricing = "Grille tarifaire détaillée. " * 20
    blog_body = "Nous lançons une toute nouvelle fonctionnalité aujourd'hui. Suite du texte ici."

    def fake_get(url: str, **kwargs: object) -> MagicMock:
        if url == "https://example.com":
            return _html_response("Bienvenue sur notre site.")
        if url == "https://example.com/pricing":
            return _html_response(long_pricing)
        if url == "https://example.com/blog":
            return _html_response(blog_body)
        raise requests.ConnectionError("unreachable")

    with patch("requests.get", side_effect=fake_get):
        result = scraper.scrape(_competitor())

    assert result.homepage == "Bienvenue sur notre site."
    assert "Grille tarifaire" in (result.pricing or "")
    assert len(result.blog_titles) == 1
    assert "nouvelle fonctionnalité" in result.blog_titles[0]


def test_scrape_handles_full_network_failure_gracefully() -> None:
    scraper = HttpWebScraper()

    with patch("requests.get", side_effect=requests.ConnectionError("dns failure")):
        result = scraper.scrape(_competitor())

    assert result.homepage is None
    assert result.pricing is None
    assert result.blog_titles == []
