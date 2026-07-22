"""Adapter de notification — envoie un email via SMTP."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from domain.models import CompetitorAnalysis
from domain.notification import build_message


class SmtpEmailNotifier:
    def __init__(self, host: str, port: int, user: str, password: str, to: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._to = to

    def notify(self, sector: str, high_priority: list[CompetitorAnalysis], report_path: str) -> None:
        if not all([self._user, self._password, self._to]):
            return

        message = build_message(sector, high_priority, report_path)
        subject = f"[Veille] {len(high_priority)} signal(s) prioritaire(s) — {sector}"

        try:
            msg = MIMEMultipart()
            msg["From"] = self._user
            msg["To"] = self._to
            msg["Subject"] = subject
            msg.attach(MIMEText(message, "plain", "utf-8"))
            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                server.login(self._user, self._password)
                server.send_message(msg)
            print(f"[NOTIFY] Email envoyé à {self._to}")
        except smtplib.SMTPException as e:
            print(f"[NOTIFY] Email error: {e}")
