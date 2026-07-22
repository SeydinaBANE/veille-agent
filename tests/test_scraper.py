from application.scraper import ScraperService
from domain.models import Competitor, WebData


class FakeWebScraper:
    def scrape(self, competitor: Competitor) -> WebData:
        return WebData(
            name=competitor.name,
            website=competitor.website,
            homepage=f"homepage de {competitor.name}",
            pricing=None,
        )


def test_scrape_all_preserves_order() -> None:
    competitors = [
        Competitor(name="Stripe", website="https://stripe.com", linkedin="", twitter="", description=""),
        Competitor(name="Adyen", website="https://adyen.com", linkedin="", twitter="", description=""),
    ]
    service = ScraperService(scraper=FakeWebScraper())

    results = service.scrape_all(competitors)

    assert [r.name for r in results] == ["Stripe", "Adyen"]
    assert results[0].homepage == "homepage de Stripe"
