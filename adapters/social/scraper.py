"""Adapter social — implémente SocialScraper via scraping public LinkedIn + Nitter."""

import logging

import requests
from bs4 import BeautifulSoup

from domain.models import Competitor, SocialData

logger = logging.getLogger(__name__)

_GOOGLEBOT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}

_NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.net",
]


class PublicSocialScraper:
    def scrape(self, competitor: Competitor) -> SocialData:
        logger.info("Social scraping : %s...", competitor.name)
        return SocialData(
            name=competitor.name,
            linkedin_posts=self._fetch_linkedin_posts(competitor.linkedin, competitor.name),
            twitter_posts=self._fetch_twitter_posts(competitor.twitter),
        )

    def _fetch_linkedin_posts(self, linkedin_url: str, company_name: str) -> list[str]:
        posts: list[str] = []
        try:
            query = f'site:linkedin.com "{company_name}" post annonce 2025'
            response = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": "1"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            data = response.json()
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and topic.get("Text"):
                    posts.append(topic["Text"])

            if not posts and linkedin_url:
                resp = requests.get(linkedin_url, headers=_GOOGLEBOT_HEADERS, timeout=10)
                soup = BeautifulSoup(resp.text, "lxml")
                for el in soup.find_all(["p", "span"], limit=20):
                    text = el.get_text(strip=True)
                    if len(text) > 50:
                        posts.append(text[:300])
        except requests.RequestException as e:
            posts.append(f"LinkedIn non accessible : {e}")

        return posts[:5]

    def _fetch_twitter_posts(self, twitter_handle: str) -> list[str]:
        if not twitter_handle:
            return []

        for instance in _NITTER_INSTANCES:
            posts = self._fetch_from_nitter_instance(instance, twitter_handle)
            if posts:
                return posts

        return [f"Twitter/@{twitter_handle} non accessible via Nitter"]

    def _fetch_from_nitter_instance(self, instance: str, twitter_handle: str) -> list[str]:
        try:
            url = f"{instance}/{twitter_handle.lstrip('@')}"
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if response.status_code != 200:
                return []
            soup = BeautifulSoup(response.text, "lxml")
            tweets = soup.find_all("div", class_="tweet-content")
            return [t.get_text(strip=True)[:280] for t in tweets[:5] if t.get_text(strip=True)]
        except requests.RequestException:
            return []
