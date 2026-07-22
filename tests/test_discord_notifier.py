from unittest.mock import patch

import requests

from adapters.notify.discord_notifier import DiscordWebhookNotifier
from domain.models import CompetitorAnalysis, Priority


def _analysis() -> list[CompetitorAnalysis]:
    return [
        CompetitorAnalysis(
            name="Stripe", score=9, signal_type="offensive",
            interpretation="baisse de prix", recommended_action="ajuster nos tarifs",
            priority=Priority.HAUTE,
        )
    ]


def test_notify_posts_to_webhook_when_configured() -> None:
    notifier = DiscordWebhookNotifier(webhook_url="https://discord.com/api/webhooks/xxx")

    with patch("requests.post") as mock_post:
        notifier.notify("fintech", _analysis(), "/tmp/rapport.md")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://discord.com/api/webhooks/xxx"
    assert "Stripe" in kwargs["json"]["content"]


def test_notify_is_noop_when_no_webhook_configured() -> None:
    notifier = DiscordWebhookNotifier(webhook_url="")

    with patch("requests.post") as mock_post:
        notifier.notify("fintech", _analysis(), "/tmp/rapport.md")

    mock_post.assert_not_called()


def test_notify_swallows_network_errors() -> None:
    notifier = DiscordWebhookNotifier(webhook_url="https://discord.com/api/webhooks/xxx")

    with patch("requests.post", side_effect=requests.ConnectionError("timeout")):
        notifier.notify("fintech", _analysis(), "/tmp/rapport.md")  # ne doit pas lever
