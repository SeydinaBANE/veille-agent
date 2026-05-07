"""
Notifier — Email (SMTP), Slack webhook, Discord webhook
Déclenché après un scan si signal score >= 7
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()


def _build_message(sector: str, high_priority: list[dict], report_path: str) -> str:
    lines = [f"🕵️ Veille Agent — {sector}", ""]
    lines.append(f"⚠️ {len(high_priority)} signal(s) prioritaire(s) détecté(s) :")
    lines.append("")
    for c in high_priority:
        lines.append(f"• {c['name']} — score {c.get('score', '?')}/10 ({c.get('signal_type', '')})")
        lines.append(f"  {c.get('interpretation', '')}")
        lines.append(f"  → {c.get('recommended_action', '')}")
        lines.append("")
    if report_path:
        lines.append(f"📄 Rapport : {report_path}")
    return "\n".join(lines)


def _send_email(subject: str, body: str):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")
    to = os.getenv("NOTIFY_EMAIL", "")
    if not all([user, password, to]):
        return
    try:
        msg = MIMEMultipart()
        msg["From"] = user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        print(f"[NOTIFY] Email envoyé à {to}")
    except Exception as e:
        print(f"[NOTIFY] Email error: {e}")


def _send_slack(text: str):
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        return
    try:
        requests.post(url, json={"text": text}, timeout=10)
        print("[NOTIFY] Slack envoyé")
    except Exception as e:
        print(f"[NOTIFY] Slack error: {e}")


def _send_discord(text: str):
    url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not url:
        return
    try:
        requests.post(url, json={"content": text}, timeout=10)
        print("[NOTIFY] Discord envoyé")
    except Exception as e:
        print(f"[NOTIFY] Discord error: {e}")


def notify_changes(sector: str, high_priority: list[dict], report_path: str):
    if not high_priority:
        return
    message = _build_message(sector, high_priority, report_path)
    subject = f"[Veille] {len(high_priority)} signal(s) prioritaire(s) — {sector}"
    _send_email(subject, message)
    _send_slack(message)
    _send_discord(message)
