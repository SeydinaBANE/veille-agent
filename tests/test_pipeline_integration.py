"""Test d'intégration bout-en-bout du pipeline LangGraph, sans aucun appel réseau/LLM réel.

Tous les ports (LLM, recherche, scraping web/social) sont remplacés par des doubles ;
seuls les adapters de stockage (snapshots + rapport) sont réels, pointés vers tmp_path.
Valide que main.run() câble correctement discovery → scraper → social → diff →
analysis → report de bout en bout.
"""

from pathlib import Path

from adapters.storage.report_repository import MarkdownReportRepository
from adapters.storage.snapshot_repository import JsonSnapshotRepository
from application.analysis import AnalysisService
from application.diff import DiffService
from application.discovery import DiscoveryService
from application.report import ReportService
from application.scraper import ScraperService
from application.social import SocialService
from domain.models import ChangeType, Competitor, SocialData, WebData
from main import Services, run


class FakeSearch:
    def search(self, query: str) -> str:
        return "contexte web factice"


class FakeDiscoveryLLM:
    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        return (
            '[{"name":"Stripe","website":"https://stripe.example",'
            '"linkedin":"https://linkedin.com/company/stripe",'
            '"twitter":"stripe","description":"Paiement en ligne"},'
            '{"name":"Adyen","website":"https://adyen.example",'
            '"linkedin":"https://linkedin.com/company/adyen",'
            '"twitter":"adyen","description":"Paiement en ligne aussi"}]'
        )


class FakeAnalysisLLM:
    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        return (
            '{"competitors":[{"name":"Stripe","score":8,"signal_type":"offensive",'
            '"interpretation":"nouveau concurrent detecte","recommended_action":"surveiller",'
            '"priority":"haute"},{"name":"Adyen","score":8,"signal_type":"offensive",'
            '"interpretation":"nouveau concurrent detecte","recommended_action":"surveiller",'
            '"priority":"haute"}],"summary":"Deux nouveaux concurrents identifiés."}'
        )


class FakeReportLLM:
    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        return "# Rapport de veille — test\n\n## Résumé exécutif\nTout va bien."


class FakeWebScraper:
    def scrape(self, competitor: Competitor) -> WebData:
        return WebData(
            name=competitor.name,
            website=competitor.website,
            homepage=f"Bienvenue chez {competitor.name} " * 20,
            pricing=f"Grille tarifaire {competitor.name} " * 20,
            blog_titles=["Nouvelle fonctionnalité annoncée"],
        )


class FakeSocialScraper:
    def scrape(self, competitor: Competitor) -> SocialData:
        return SocialData(name=competitor.name, linkedin_posts=[], twitter_posts=[])


def _build_fake_services(tmp_path: Path) -> Services:
    return Services(
        discovery=DiscoveryService(llm=FakeDiscoveryLLM(), search=FakeSearch()),
        scraper=ScraperService(scraper=FakeWebScraper()),
        social=SocialService(scraper=FakeSocialScraper()),
        diff=DiffService(repository=JsonSnapshotRepository(storage_dir=tmp_path / "snapshots")),
        analysis=AnalysisService(llm=FakeAnalysisLLM()),
        report=ReportService(
            llm=FakeReportLLM(),
            repository=MarkdownReportRepository(reports_dir=tmp_path / "reports"),
        ),
    )


def test_full_pipeline_first_scan_creates_baseline_and_report(tmp_path: Path) -> None:
    services = _build_fake_services(tmp_path)
    steps: list[str] = []

    final_state = run(
        "fintech SaaS (test)",
        max_competitors=2,
        on_step=steps.append,
        services=services,
    )

    assert [c.name for c in final_state["competitors"]] == ["Stripe", "Adyen"]
    assert len(final_state["web_data"]) == 2
    assert len(final_state["social_data"]) == 2

    assert len(final_state["diffs"]) == 2
    assert all(d.has_changes for d in final_state["diffs"])
    assert all(d.changes[0].change_type == ChangeType.NOUVEAU_CONCURRENT for d in final_state["diffs"])

    assert final_state["analysis"].summary == "Deux nouveaux concurrents identifiés."
    assert len(final_state["analysis"].high_priority(min_score=7)) == 2

    report_path = Path(final_state["report_path"])
    assert report_path.exists()
    assert "Rapport de veille" in report_path.read_text(encoding="utf-8")

    assert set(final_state["trace"]) == {"discovery", "scraper", "social", "diff", "analysis", "report"}
    assert len(steps) == 6


def test_second_scan_on_same_competitors_detects_no_change(tmp_path: Path) -> None:
    services = _build_fake_services(tmp_path)

    run("fintech SaaS (test)", max_competitors=2, services=services)
    second_state = run("fintech SaaS (test)", max_competitors=2, services=services)

    assert all(not d.has_changes for d in second_state["diffs"])
    assert second_state["analysis"].no_changes == ["Stripe", "Adyen"]
