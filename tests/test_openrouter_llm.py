from unittest.mock import MagicMock

import anthropic
import pytest
from anthropic.types import TextBlock

from adapters.llm.openrouter import OpenRouterLLMClient

# tenacity attache .retry au niveau du wrapper, invisible pour mypy sur la signature décorée
OpenRouterLLMClient.complete.retry.sleep = lambda _seconds: None  # type: ignore[attr-defined]


def _client_with_mocked_create() -> tuple[OpenRouterLLMClient, MagicMock]:
    client = OpenRouterLLMClient(api_key="test-key", model="anthropic/claude-haiku-4-5")
    mock_create = MagicMock()
    client._client.messages.create = mock_create  # type: ignore[method-assign]
    return client, mock_create


def test_complete_returns_text_block_content() -> None:
    client, mock_create = _client_with_mocked_create()
    mock_create.return_value = MagicMock(content=[TextBlock(type="text", text="  réponse du modèle  ")])

    result = client.complete(system="system prompt", prompt="user prompt", max_tokens=100)

    assert result == "réponse du modèle"
    mock_create.assert_called_once_with(
        model="anthropic/claude-haiku-4-5",
        max_tokens=100,
        system="system prompt",
        messages=[{"role": "user", "content": "user prompt"}],
    )


def test_complete_raises_on_unexpected_block_type() -> None:
    client, mock_create = _client_with_mocked_create()
    mock_create.return_value = MagicMock(content=[object()])

    with pytest.raises(ValueError, match="Réponse LLM inattendue"):
        client.complete(system="s", prompt="p", max_tokens=10)


def test_complete_retries_then_succeeds_on_transient_error() -> None:
    client, mock_create = _client_with_mocked_create()
    request = MagicMock()
    transient_error = anthropic.APIConnectionError(message="boom", request=request)
    mock_create.side_effect = [
        transient_error,
        transient_error,
        MagicMock(content=[TextBlock(type="text", text="ok après retry")]),
    ]

    result = client.complete(system="s", prompt="p", max_tokens=10)

    assert result == "ok après retry"
    assert mock_create.call_count == 3


def test_complete_reraises_after_exhausting_retries() -> None:
    client, mock_create = _client_with_mocked_create()
    request = MagicMock()
    mock_create.side_effect = anthropic.APIConnectionError(message="boom", request=request)

    with pytest.raises(anthropic.APIConnectionError):
        client.complete(system="s", prompt="p", max_tokens=10)

    assert mock_create.call_count == 3
