"""Adapter de stockage — implémente ReportRepository via des fichiers Markdown."""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent.parent.parent / "output" / "reports"


class MarkdownReportRepository:
    def __init__(self, reports_dir: Path = REPORTS_DIR) -> None:
        self._reports_dir = reports_dir
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def save(self, sector: str, content: str) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        sector_slug = sector.lower().replace(" ", "_")[:20]
        report_path = self._reports_dir / f"rapport_{date_str}_{sector_slug}.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Rapport sauvegardé : %s", report_path)
        return report_path
