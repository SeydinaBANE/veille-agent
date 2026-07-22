"""Entités métier du domaine de veille concurrentielle."""

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class Competitor:
    name: str
    website: str
    linkedin: str
    twitter: str
    description: str


@dataclass(frozen=True)
class WebData:
    name: str
    website: str | None
    homepage: str | None
    pricing: str | None
    blog_titles: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class SocialData:
    name: str
    linkedin_posts: list[str] = field(default_factory=list)
    twitter_posts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompetitorSnapshot:
    name: str
    website: str | None
    homepage: str | None
    pricing: str | None
    blog_titles: list[str]
    linkedin_posts: list[str]
    twitter_posts: list[str]
    saved_at: str | None = None


class ChangeType(StrEnum):
    NOUVEAU_CONCURRENT = "nouveau_concurrent"
    SITE_MODIFIE = "site_modifie"
    PRIX_MODIFIE = "prix_modifie"
    NOUVEAU_CONTENU = "nouveau_contenu"
    NOUVEAU_POST_LINKEDIN = "nouveau_post_linkedin"
    NOUVEAU_POST_TWITTER = "nouveau_post_twitter"


@dataclass(frozen=True)
class ChangeSignal:
    change_type: ChangeType
    description: str


@dataclass(frozen=True)
class CompetitorDiff:
    name: str
    changes: list[ChangeSignal]
    snapshot: CompetitorSnapshot
    scanned_at: str

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0


class Priority(StrEnum):
    HAUTE = "haute"
    MOYENNE = "moyenne"
    FAIBLE = "faible"


@dataclass(frozen=True)
class CompetitorAnalysis:
    name: str
    score: int
    signal_type: str
    interpretation: str
    recommended_action: str
    priority: Priority


@dataclass(frozen=True)
class StrategicAnalysis:
    competitors: list[CompetitorAnalysis]
    summary: str
    no_changes: list[str] = field(default_factory=list)
    parse_error: bool = False

    def high_priority(self, min_score: int = 7) -> list[CompetitorAnalysis]:
        return [c for c in self.competitors if c.score >= min_score]


@dataclass(frozen=True)
class StepTrace:
    duration_s: float
    detail: str = ""
