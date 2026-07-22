"""Formatage pur du message de notification (indépendant du canal d'envoi)."""

from domain.models import CompetitorAnalysis


def build_message(sector: str, high_priority: list[CompetitorAnalysis], report_path: str) -> str:
    lines = [f"🕵️ Veille Agent — {sector}", ""]
    lines.append(f"⚠️ {len(high_priority)} signal(s) prioritaire(s) détecté(s) :")
    lines.append("")
    for c in high_priority:
        lines.append(f"• {c.name} — score {c.score}/10 ({c.signal_type})")
        lines.append(f"  {c.interpretation}")
        lines.append(f"  → {c.recommended_action}")
        lines.append("")
    if report_path:
        lines.append(f"📄 Rapport : {report_path}")
    return "\n".join(lines)
