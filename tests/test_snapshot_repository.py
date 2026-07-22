from pathlib import Path

from adapters.storage.snapshot_repository import JsonSnapshotRepository, slugify
from domain.models import CompetitorSnapshot


def test_slugify_normalizes_name() -> None:
    assert slugify("Stripe / Payments Inc.") == "stripe_-_payments_inc."


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    repository = JsonSnapshotRepository(storage_dir=tmp_path)
    snapshot = CompetitorSnapshot(
        name="Stripe",
        website="https://stripe.com",
        homepage="accueil",
        pricing="tarifs",
        blog_titles=["Titre 1"],
        linkedin_posts=[],
        twitter_posts=[],
    )

    repository.save("Stripe", snapshot)
    loaded = repository.load("Stripe")

    assert loaded is not None
    assert loaded.name == "Stripe"
    assert loaded.homepage == "accueil"
    assert loaded.saved_at is not None


def test_load_missing_returns_none(tmp_path: Path) -> None:
    repository = JsonSnapshotRepository(storage_dir=tmp_path)

    assert repository.load("Inconnu") is None
