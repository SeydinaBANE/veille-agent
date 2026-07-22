from application.analysis import AnalysisService
from domain.models import (
    ChangeSignal,
    ChangeType,
    CompetitorDiff,
    CompetitorSnapshot,
    Priority,
)


class FakeLLM:
    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        return self._response


def _snapshot(name: str) -> CompetitorSnapshot:
    return CompetitorSnapshot(
        name=name, website="https://x.com", homepage="h", pricing="p",
        blog_titles=[], linkedin_posts=[], twitter_posts=[],
    )


def _diff_with_change(name: str) -> CompetitorDiff:
    return CompetitorDiff(
        name=name,
        changes=[ChangeSignal(ChangeType.PRIX_MODIFIE, "prix modifié")],
        snapshot=_snapshot(name),
        scanned_at="2026-07-22T00:00:00",
    )


def _diff_without_change(name: str) -> CompetitorDiff:
    return CompetitorDiff(name=name, changes=[], snapshot=_snapshot(name), scanned_at="2026-07-22T00:00:00")


def test_analyze_returns_summary_only_when_no_changes() -> None:
    service = AnalysisService(llm=FakeLLM("ne devrait pas être appelé"))

    analysis = service.analyze([_diff_without_change("Stripe")])

    assert analysis.competitors == []
    assert analysis.no_changes == ["Stripe"]


def test_analyze_parses_llm_json() -> None:
    response = (
        '{"competitors":[{"name":"Stripe","score":8,"signal_type":"offensive",'
        '"interpretation":"...","recommended_action":"...","priority":"haute"}],'
        '"summary":"resume"}'
    )
    service = AnalysisService(llm=FakeLLM(response))

    analysis = service.analyze([_diff_with_change("Stripe"), _diff_without_change("Adyen")])

    assert analysis.summary == "resume"
    assert analysis.no_changes == ["Adyen"]
    assert analysis.competitors[0].priority == Priority.HAUTE
    assert analysis.high_priority(min_score=7) == analysis.competitors


def test_analyze_handles_invalid_json() -> None:
    service = AnalysisService(llm=FakeLLM("réponse non json"))

    analysis = service.analyze([_diff_with_change("Stripe")])

    assert analysis.parse_error is True
    assert analysis.competitors == []
