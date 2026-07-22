"""Adapter de notification — diffuse vers plusieurs canaux (email, Slack, Discord)."""

from domain.models import CompetitorAnalysis
from domain.ports import Notifier


class CompositeNotifier:
    def __init__(self, notifiers: list[Notifier]) -> None:
        self._notifiers = notifiers

    def notify(self, sector: str, high_priority: list[CompetitorAnalysis], report_path: str) -> None:
        if not high_priority:
            return
        for notifier in self._notifiers:
            notifier.notify(sector, high_priority, report_path)
