from application.notify import NotificationService
from domain.models import CompetitorAnalysis, Priority, StrategicAnalysis
from domain.notification import build_message


class RecordingNotifier:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[CompetitorAnalysis], str]] = []

    def notify(self, sector: str, high_priority: list[CompetitorAnalysis], report_path: str) -> None:
        self.calls.append((sector, high_priority, report_path))


def _analysis(scores: list[int]) -> StrategicAnalysis:
    competitors = [
        CompetitorAnalysis(
            name=f"C{i}", score=score, signal_type="offensive",
            interpretation="i", recommended_action="a", priority=Priority.HAUTE,
        )
        for i, score in enumerate(scores)
    ]
    return StrategicAnalysis(competitors=competitors, summary="resume")


def test_notify_high_priority_filters_by_score() -> None:
    notifier = RecordingNotifier()
    service = NotificationService(notifier=notifier)

    service.notify_high_priority("fintech", _analysis([9, 3, 7]), "/tmp/rapport.md")

    assert len(notifier.calls) == 1
    _, high_priority, report_path = notifier.calls[0]
    assert [c.score for c in high_priority] == [9, 7]
    assert report_path == "/tmp/rapport.md"


def test_notify_high_priority_skips_when_none_above_threshold() -> None:
    notifier = RecordingNotifier()
    service = NotificationService(notifier=notifier)

    service.notify_high_priority("fintech", _analysis([3, 5]), "/tmp/rapport.md")

    assert notifier.calls == [("fintech", [], "/tmp/rapport.md")]


def test_build_message_includes_all_competitors() -> None:
    competitors = [
        CompetitorAnalysis(
            name="Stripe", score=9, signal_type="offensive",
            interpretation="baisse de prix", recommended_action="ajuster nos tarifs",
            priority=Priority.HAUTE,
        )
    ]

    message = build_message("fintech", competitors, "/tmp/rapport.md")

    assert "Stripe" in message
    assert "9/10" in message
    assert "/tmp/rapport.md" in message
