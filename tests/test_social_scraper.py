from unittest.mock import MagicMock, patch

import requests

from adapters.social.scraper import PublicSocialScraper

# tenacity attache .retry au niveau du wrapper, invisible pour mypy sur la signature décorée
PublicSocialScraper._search_linkedin_duckduckgo.retry.sleep = lambda _seconds: None  # type: ignore[attr-defined]


def _json_response(data: dict) -> MagicMock:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = data
    return response


def _html_response(status_code: int, body: str) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = f"<html><body>{body}</body></html>"
    return response


def test_fetch_linkedin_posts_from_duckduckgo_related_topics() -> None:
    scraper = PublicSocialScraper()
    data = {"RelatedTopics": [{"Text": "Annonce 1"}, {"Text": "Annonce 2"}]}

    with patch("requests.get", return_value=_json_response(data)):
        posts = scraper._fetch_linkedin_posts("https://linkedin.com/company/x", "Stripe")

    assert posts == ["Annonce 1", "Annonce 2"]


def test_fetch_linkedin_posts_falls_back_to_direct_scrape_when_duckduckgo_empty() -> None:
    scraper = PublicSocialScraper()

    def fake_get(url: str, **kwargs: object) -> MagicMock:
        if "duckduckgo" in url:
            return _json_response({"RelatedTopics": []})
        return _html_response(200, "<p>" + "Un post LinkedIn suffisamment long pour être retenu ici" + "</p>")

    with patch("requests.get", side_effect=fake_get):
        posts = scraper._fetch_linkedin_posts("https://linkedin.com/company/x", "Stripe")

    assert len(posts) == 1
    assert "post LinkedIn" in posts[0]


def test_fetch_linkedin_posts_returns_error_message_on_network_failure() -> None:
    scraper = PublicSocialScraper()

    with patch("requests.get", side_effect=requests.ConnectionError("dns failure")):
        posts = scraper._fetch_linkedin_posts("https://linkedin.com/company/x", "Stripe")

    assert len(posts) == 1
    assert "LinkedIn non accessible" in posts[0]


def test_fetch_twitter_posts_returns_empty_when_no_handle() -> None:
    scraper = PublicSocialScraper()

    assert scraper._fetch_twitter_posts("") == []


def test_fetch_twitter_posts_uses_first_working_nitter_instance() -> None:
    scraper = PublicSocialScraper()
    tweet_html = '<div class="tweet-content">Premier tweet</div>'

    with patch("requests.get", return_value=_html_response(200, tweet_html)):
        posts = scraper._fetch_twitter_posts("stripe")

    assert posts == ["Premier tweet"]


def test_fetch_twitter_posts_falls_back_across_instances() -> None:
    scraper = PublicSocialScraper()
    call_urls: list[str] = []

    def fake_get(url: str, **kwargs: object) -> MagicMock:
        call_urls.append(url)
        if "nitter.poast.org" in url:
            return _html_response(500, "")
        if "nitter.privacydev.net" in url:
            return _html_response(200, '<div class="tweet-content">Tweet trouvé</div>')
        raise requests.ConnectionError("unreachable")

    with patch("requests.get", side_effect=fake_get):
        posts = scraper._fetch_twitter_posts("stripe")

    assert posts == ["Tweet trouvé"]
    assert any("nitter.poast.org" in u for u in call_urls)
    assert any("nitter.privacydev.net" in u for u in call_urls)


def test_fetch_twitter_posts_returns_fallback_when_all_instances_fail() -> None:
    scraper = PublicSocialScraper()

    with patch("requests.get", side_effect=requests.ConnectionError("unreachable")):
        posts = scraper._fetch_twitter_posts("stripe")

    assert posts == ["Twitter/@stripe non accessible via Nitter"]
