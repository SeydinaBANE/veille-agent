from pathlib import Path

from application.report import ReportService
from domain.models import StrategicAnalysis


class FakeLLM:
    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        return "# Rapport de veille"


class FakeReportRepository:
    def __init__(self) -> None:
        self.saved: tuple[str, str] | None = None

    def save(self, sector: str, content: str) -> Path:
        self.saved = (sector, content)
        return Path(f"/fake/{sector}.md")


def test_generate_saves_llm_output() -> None:
    repository = FakeReportRepository()
    service = ReportService(llm=FakeLLM(), repository=repository)
    analysis = StrategicAnalysis(competitors=[], summary="resume", no_changes=["Stripe"])

    report_path = service.generate("fintech", analysis)

    assert report_path == "/fake/fintech.md"
    assert repository.saved is not None
    assert repository.saved[1] == "# Rapport de veille"
