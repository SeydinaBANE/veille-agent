"""Adapter LLM — implémente LLMClient via OpenRouter (SDK Anthropic)."""

import anthropic


class OpenRouterLLMClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key, base_url="https://openrouter.ai/api")
        self._model = model

    def complete(self, *, system: str, prompt: str, max_tokens: int) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
