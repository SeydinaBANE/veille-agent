from pathlib import Path

from adapters.storage.report_repository import MarkdownReportRepository


def test_save_writes_markdown_file(tmp_path: Path) -> None:
    repository = MarkdownReportRepository(reports_dir=tmp_path)

    report_path = repository.save("fintech SaaS", "# Rapport de veille\n\nContenu.")

    assert report_path.exists()
    assert report_path.parent == tmp_path
    assert report_path.suffix == ".md"
    assert "fintech_saas" in report_path.name
    assert report_path.read_text(encoding="utf-8") == "# Rapport de veille\n\nContenu."


def test_save_creates_reports_dir_if_missing(tmp_path: Path) -> None:
    missing_dir = tmp_path / "nested" / "reports"
    repository = MarkdownReportRepository(reports_dir=missing_dir)

    report_path = repository.save("CRM B2B", "contenu")

    assert missing_dir.exists()
    assert report_path.exists()
