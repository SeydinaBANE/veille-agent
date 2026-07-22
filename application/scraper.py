"""Use case — scrape le site web de chaque concurrent."""

from domain.models import Competitor, WebData
from domain.ports import WebScraper


class ScraperService:
    def __init__(self, scraper: WebScraper) -> None:
        self._scraper = scraper

    def scrape_all(self, competitors: list[Competitor]) -> list[WebData]:
        return [self._scraper.scrape(c) for c in competitors]
