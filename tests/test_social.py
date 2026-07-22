from application.social import SocialService
from domain.models import Competitor, SocialData


class FakeSocialScraper:
    def scrape(self, competitor: Competitor) -> SocialData:
        return SocialData(name=competitor.name, linkedin_posts=["post"], twitter_posts=[])


def test_collect_all_preserves_order() -> None:
    competitors = [
        Competitor(name="Stripe", website="", linkedin="", twitter="", description=""),
        Competitor(name="Adyen", website="", linkedin="", twitter="", description=""),
    ]
    service = SocialService(scraper=FakeSocialScraper())

    results = service.collect_all(competitors)

    assert [r.name for r in results] == ["Stripe", "Adyen"]
    assert results[0].linkedin_posts == ["post"]
