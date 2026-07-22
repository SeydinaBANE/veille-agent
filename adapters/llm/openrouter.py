"""Adapter LLM — implémente LLMClient via OpenRouter (SDK Anthropic)."""

import anthropic
from anthropic.types import TextBlock
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

_RETRYABLE_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class OpenRouterLLMClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key, base_url="https://openrouter.ai/api")
        self._model = model

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        block = message.content[0]
        if not isinstance(block, TextBlock):
            raise ValueError(f"Réponse LLM inattendue : bloc de type {type(block).__name__}")
        return block.text.strip()
