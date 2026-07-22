import smtplib
from unittest.mock import MagicMock, patch

from adapters.notify.email_notifier import SmtpEmailNotifier
from domain.models import CompetitorAnalysis, Priority


def _analysis() -> list[CompetitorAnalysis]:
    return [
        CompetitorAnalysis(
            name="Stripe", score=9, signal_type="offensive",
            interpretation="baisse de prix", recommended_action="ajuster nos tarifs",
            priority=Priority.HAUTE,
        )
    ]


def test_notify_sends_email_when_configured() -> None:
    notifier = SmtpEmailNotifier(host="smtp.example.com", port=587, user="me@example.com",
                                  password="secret", to="dest@example.com")
    mock_server = MagicMock()
    mock_smtp = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    with patch("smtplib.SMTP", mock_smtp):
        notifier.notify("fintech", _analysis(), "/tmp/rapport.md")

    mock_smtp.assert_called_once_with("smtp.example.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("me@example.com", "secret")
    mock_server.send_message.assert_called_once()


def test_notify_is_noop_when_not_configured() -> None:
    notifier = SmtpEmailNotifier(host="smtp.example.com", port=587, user="", password="", to="")

    with patch("smtplib.SMTP") as mock_smtp:
        notifier.notify("fintech", _analysis(), "/tmp/rapport.md")

    mock_smtp.assert_not_called()


def test_notify_logs_and_swallows_smtp_errors() -> None:
    notifier = SmtpEmailNotifier(host="smtp.example.com", port=587, user="me@example.com",
                                  password="secret", to="dest@example.com")

    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("connexion refusée")):
        notifier.notify("fintech", _analysis(), "/tmp/rapport.md")  # ne doit pas lever
