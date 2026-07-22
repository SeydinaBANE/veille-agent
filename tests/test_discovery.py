from application.discovery import DiscoveryService
from domain.ports import LLMClient, SearchEngine


class FakeSearch:
    def search(self, query: str) -> str:
        return "contexte web factice"


class FakeLLM:
    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        return self._response


def _service(response: str) -> DiscoveryService:
    llm: LLMClient = FakeLLM(response)
    search: SearchEngine = FakeSearch()
    return DiscoveryService(llm=llm, search=search)


def test_discover_parses_valid_json() -> None:
    response = (
        '[{"name":"Stripe","website":"https://stripe.com",'
        '"linkedin":"https://linkedin.com/company/stripe",'
        '"twitter":"stripe","description":"Paiement en ligne"}]'
    )
    service = _service(response)

    competitors = service.discover("fintech", max_competitors=1)

    assert len(competitors) == 1
    assert competitors[0].name == "Stripe"
    assert competitors[0].website == "https://stripe.com"


def test_discover_falls_back_on_invalid_json() -> None:
    response = 'texte non structuré {"name":"Adyen","website":"https://adyen.com"} suite'
    service = _service(response)

    competitors = service.discover("fintech", max_competitors=1)

    assert len(competitors) == 1
    assert competitors[0].name == "Adyen"
