"""Provider-agnostic LLM interface (TZ section 9: "LLMProvider — интерфейс,
а не прямой вызов одного SDK"). app/ai/reasoning.py only ever talks to this
interface, so a second provider can be added later without touching it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMUsage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int


class LLMProvider(ABC):
    @abstractmethod
    async def generate_structured(
        self, system_prompt: str, user_prompt: str, response_model: type[T]
    ) -> tuple[T, LLMUsage]:
        """Returns a validated instance of `response_model` plus token usage.
        Implementations must not silently fall back to freeform text — a
        schema-invalid response should raise rather than be coerced."""


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str, client: anthropic.AsyncAnthropic | None = None) -> None:
        self._model = model
        self._client = client or anthropic.AsyncAnthropic()

    async def generate_structured(
        self, system_prompt: str, user_prompt: str, response_model: type[T]
    ) -> tuple[T, LLMUsage]:
        response = await self._client.messages.parse(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=response_model,
        )
        usage = LLMUsage(
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return response.parsed_output, usage
