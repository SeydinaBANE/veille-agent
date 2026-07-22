from domain.models import ChangeType, CompetitorSnapshot, SocialData, WebData
from application.diff import DiffService


class FakeSnapshotRepository:
    def __init__(self) -> None:
        self._store: dict[str, CompetitorSnapshot] = {}

    def load(self, competitor_name: str) -> CompetitorSnapshot | None:
        return self._store.get(competitor_name)

    def save(self, competitor_name: str, snapshot: CompetitorSnapshot) -> None:
        self._store[competitor_name] = snapshot


def _web(name: str, homepage: str, pricing: str | None = "prix stable ici") -> WebData:
    return WebData(name=name, website="https://example.com", homepage=homepage, pricing=pricing)


def _social(name: str) -> SocialData:
    return SocialData(name=name, linkedin_posts=[], twitter_posts=[])


def test_first_scan_creates_baseline() -> None:
    service = DiffService(repository=FakeSnapshotRepository())

    diffs = service.diff_all([_web("Stripe", "bienvenue chez stripe " * 20)], [_social("Stripe")])

    assert len(diffs) == 1
    assert diffs[0].has_changes is True
    assert diffs[0].changes[0].change_type == ChangeType.NOUVEAU_CONCURRENT


def test_second_scan_detects_pricing_change() -> None:
    repository = FakeSnapshotRepository()
    service = DiffService(repository=repository)
    homepage = "bienvenue chez stripe " * 20

    service.diff_all([_web("Stripe", homepage, pricing="offre standard " * 20)], [_social("Stripe")])
    diffs = service.diff_all([_web("Stripe", homepage, pricing="nouvelle grille tarifaire " * 20)], [_social("Stripe")])

    assert diffs[0].has_changes is True
    assert any(c.change_type == ChangeType.PRIX_MODIFIE for c in diffs[0].changes)


def test_second_scan_without_changes() -> None:
    repository = FakeSnapshotRepository()
    service = DiffService(repository=repository)
    homepage = "bienvenue chez stripe " * 20
    pricing = "offre standard " * 20

    service.diff_all([_web("Stripe", homepage, pricing=pricing)], [_social("Stripe")])
    diffs = service.diff_all([_web("Stripe", homepage, pricing=pricing)], [_social("Stripe")])

    assert diffs[0].has_changes is False
