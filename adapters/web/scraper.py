"""Adapter web — implémente WebScraper via requests + BeautifulSoup."""

import logging
import re

import requests
from bs4 import BeautifulSoup

from domain.models import Competitor, WebData

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

_PRICING_PATHS = ["/pricing", "/tarifs", "/plans", "/price"]
_BLOG_PATHS = ["/blog", "/news", "/actualites", "/articles"]


class HttpWebScraper:
    def scrape(self, competitor: Competitor) -> WebData:
        website = competitor.website
        name = competitor.name

        if not website:
            return WebData(name=name, website=None, homepage=None, pricing=None, error="pas d'URL")

        logger.info("Scraping %s (%s)...", name, website)

        homepage = self._fetch_page(website)
        pricing = self._first_matching_page(website, _PRICING_PATHS, min_length=200)
        blog_titles = self._extract_blog_titles(website)

        return WebData(
            name=name,
            website=website,
            homepage=homepage,
            pricing=pricing,
            blog_titles=blog_titles,
        )

    def _fetch_page(self, url: str, timeout: int = 10) -> str | None:
        try:
            response = requests.get(url, headers=_HEADERS, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException:
            return None

        soup = BeautifulSoup(response.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return re.sub(r"\s+", " ", text)[:3000]

    def _first_matching_page(self, website: str, paths: list[str], min_length: int) -> str | None:
        for path in paths:
            content = self._fetch_page(website.rstrip("/") + path)
            if content and len(content) > min_length:
                return content
        return None

    def _extract_blog_titles(self, website: str) -> list[str]:
        for path in _BLOG_PATHS:
            blog = self._fetch_page(website.rstrip("/") + path)
            if blog:
                sample = blog[:2000]
                titles = re.findall(r"(?<!\w)([A-Z][^.!?\n]{20,80})(?=[.!?\n])", sample)
                return titles[:5]
        return []
