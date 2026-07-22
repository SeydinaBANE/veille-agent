"""Ports (interfaces) que le domaine attend des adapters d'infrastructure."""

from pathlib import Path
from typing import Protocol

from domain.models import (
    Competitor,
    CompetitorAnalysis,
    CompetitorSnapshot,
    SocialData,
    WebData,
)


class LLMClient(Protocol):
    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str: ...


class SearchEngine(Protocol):
    def search(self, query: str) -> str: ...


class WebScraper(Protocol):
    def scrape(self, competitor: Competitor) -> WebData: ...


class SocialScraper(Protocol):
    def scrape(self, competitor: Competitor) -> SocialData: ...


class SnapshotRepository(Protocol):
    def load(self, competitor_name: str) -> CompetitorSnapshot | None: ...
    def save(self, competitor_name: str, snapshot: CompetitorSnapshot) -> None: ...


class ReportRepository(Protocol):
    def save(self, sector: str, content: str) -> Path: ...


class Notifier(Protocol):
    def notify(
        self, sector: str, high_priority: list[CompetitorAnalysis], report_path: str
    ) -> None: ...
