"""Provider-agnostic LLM interface (TZ section 9: "LLMProvider — интерфейс,
а не прямой вызов одного SDK"). app/ai/reasoning.py only ever talks to this
interface, so a second provider can be added later without touching it."""

from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.ai.schemas import VisionExtraction
from app.ai.vision_prompt import VISION_SYSTEM_PROMPT, VISION_USER_INSTRUCTION

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

    @abstractmethod
    async def extract_chart_info(
        self, image_bytes: bytes, media_type: str
    ) -> tuple[VisionExtraction, LLMUsage]:
        """Reads symbol/timeframe/exchange labels off a chart screenshot.
        Must never be used to read prices or indicator values (TZ section
        2.1) — that instruction lives in the system prompt, not here."""


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str, client: anthropic.AsyncAnthropic | None = None) -> None:
        self._model = model
        # Resolve SDK credentials lazily so the deterministic analysis path can
        # still start and gracefully degrade when no production LLM key exists.
        self._client = client

    def _client_or_default(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic()
        return self._client

    async def generate_structured(
        self, system_prompt: str, user_prompt: str, response_model: type[T]
    ) -> tuple[T, LLMUsage]:
        response = await self._client_or_default().messages.parse(
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

    async def extract_chart_info(
        self, image_bytes: bytes, media_type: str
    ) -> tuple[VisionExtraction, LLMUsage]:
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = await self._client_or_default().messages.parse(
            model=self._model,
            max_tokens=1024,
            system=VISION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": VISION_USER_INSTRUCTION},
                    ],
                }
            ],
            output_format=VisionExtraction,
        )
        usage = LLMUsage(
            model=self._model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return response.parsed_output, usage
