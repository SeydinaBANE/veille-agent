"""Use case — notifie les signaux prioritaires détectés lors d'un scan."""

from domain.models import StrategicAnalysis
from domain.ports import Notifier

_HIGH_PRIORITY_MIN_SCORE = 7


class NotificationService:
    def __init__(self, notifier: Notifier) -> None:
        self._notifier = notifier

    def notify_high_priority(self, sector: str, analysis: StrategicAnalysis, report_path: str) -> None:
        high_priority = analysis.high_priority(min_score=_HIGH_PRIORITY_MIN_SCORE)
        self._notifier.notify(sector, high_priority, report_path)
