"""Use case — collecte les données sociales (LinkedIn, Twitter) de chaque concurrent."""

from domain.models import Competitor, SocialData
from domain.ports import SocialScraper


class SocialService:
    def __init__(self, scraper: SocialScraper) -> None:
        self._scraper = scraper

    def collect_all(self, competitors: list[Competitor]) -> list[SocialData]:
        return [self._scraper.scrape(c) for c in competitors]
