"""Adapter de notification — envoie un message via un webhook Slack."""

import requests

from domain.models import CompetitorAnalysis
from domain.notification import build_message


class SlackWebhookNotifier:
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def notify(self, sector: str, high_priority: list[CompetitorAnalysis], report_path: str) -> None:
        if not self._webhook_url:
            return

        message = build_message(sector, high_priority, report_path)
        try:
            requests.post(self._webhook_url, json={"text": message}, timeout=10)
            print("[NOTIFY] Slack envoyé")
        except requests.RequestException as e:
            print(f"[NOTIFY] Slack error: {e}")
