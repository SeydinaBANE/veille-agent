"""Adapter de notification — envoie un message via un webhook Discord."""

import requests

from domain.models import CompetitorAnalysis
from domain.notification import build_message


class DiscordWebhookNotifier:
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def notify(self, sector: str, high_priority: list[CompetitorAnalysis], report_path: str) -> None:
        if not self._webhook_url:
            return

        message = build_message(sector, high_priority, report_path)
        try:
            requests.post(self._webhook_url, json={"content": message}, timeout=10)
            print("[NOTIFY] Discord envoyé")
        except requests.RequestException as e:
            print(f"[NOTIFY] Discord error: {e}")
