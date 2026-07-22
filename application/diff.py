"""Use case — compare les nouvelles données aux snapshots précédents."""

import logging
from datetime import datetime

from domain.models import ChangeSignal, ChangeType, CompetitorDiff, CompetitorSnapshot, SocialData, WebData
from domain.ports import SnapshotRepository

logger = logging.getLogger(__name__)

_SIMILARITY_THRESHOLD = 0.85
_SAMPLE_SIZE = 500


class DiffService:
    def __init__(self, repository: SnapshotRepository) -> None:
        self._repository = repository

    def diff_all(self, web_data: list[WebData], social_data: list[SocialData]) -> list[CompetitorDiff]:
        social_index = {s.name: s for s in social_data}
        empty_social = SocialData(name="", linkedin_posts=[], twitter_posts=[])

        diffs: list[CompetitorDiff] = []
        for web in web_data:
            social = social_index.get(web.name, empty_social)
            diff = self._diff_competitor(web, social)
            diffs.append(diff)
            status = f"{len(diff.changes)} changement(s)" if diff.has_changes else "aucun changement"
            logger.info("Diff %s : %s", web.name, status)

        return diffs

    def _diff_competitor(self, web: WebData, social: SocialData) -> CompetitorDiff:
        old = self._repository.load(web.name)

        new_snapshot = CompetitorSnapshot(
            name=web.name,
            website=web.website,
            homepage=web.homepage,
            pricing=web.pricing,
            blog_titles=web.blog_titles,
            linkedin_posts=social.linkedin_posts,
            twitter_posts=social.twitter_posts,
        )

        changes = self._detect_changes(old, new_snapshot) if old is not None else [
            ChangeSignal(
                change_type=ChangeType.NOUVEAU_CONCURRENT,
                description=f"Premier scan de {web.name} — baseline créée",
            )
        ]

        self._repository.save(web.name, new_snapshot)

        return CompetitorDiff(
            name=web.name,
            changes=changes,
            snapshot=new_snapshot,
            scanned_at=datetime.now().isoformat(),
        )

    def _detect_changes(self, old: CompetitorSnapshot, new: CompetitorSnapshot) -> list[ChangeSignal]:
        changes: list[ChangeSignal] = []

        if self._text_changed(old.homepage, new.homepage):
            changes.append(ChangeSignal(ChangeType.SITE_MODIFIE, "Page d'accueil modifiée depuis le dernier scan"))

        if self._text_changed(old.pricing, new.pricing):
            changes.append(ChangeSignal(ChangeType.PRIX_MODIFIE, "Page de tarification modifiée ⚠️"))

        new_titles = set(new.blog_titles) - set(old.blog_titles)
        if new_titles:
            changes.append(ChangeSignal(
                ChangeType.NOUVEAU_CONTENU,
                f"Nouveaux articles détectés : {', '.join(list(new_titles)[:3])}",
            ))

        new_li_posts = set(new.linkedin_posts) - set(old.linkedin_posts)
        if new_li_posts:
            changes.append(ChangeSignal(
                ChangeType.NOUVEAU_POST_LINKEDIN,
                f"{len(new_li_posts)} nouveau(x) post(s) LinkedIn",
            ))

        new_tw_posts = set(new.twitter_posts) - set(old.twitter_posts)
        if new_tw_posts:
            changes.append(ChangeSignal(
                ChangeType.NOUVEAU_POST_TWITTER,
                f"{len(new_tw_posts)} nouveau(x) tweet(s)",
            ))

        return changes

    @staticmethod
    def _text_changed(old: str | None, new: str | None) -> bool:
        if old is None and new is not None:
            return True
        if old is None or new is None:
            return False

        old_sample = old[:_SAMPLE_SIZE].lower().split()
        new_sample = new[:_SAMPLE_SIZE].lower().split()
        if not old_sample:
            return bool(new_sample)

        common = set(old_sample) & set(new_sample)
        similarity = len(common) / max(len(set(old_sample)), 1)
        return similarity < _SIMILARITY_THRESHOLD
