from types import SimpleNamespace

from app.ai.provider import AnthropicProvider
from app.ai.schemas import AnalysisNarrative, WhyBullet


class FakeMessagesAPI:
    def __init__(self, parsed_output, input_tokens=100, output_tokens=30) -> None:
        self._parsed_output = parsed_output
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self.last_kwargs: dict | None = None

    async def parse(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(
            parsed_output=self._parsed_output,
            usage=SimpleNamespace(input_tokens=self._input_tokens, output_tokens=self._output_tokens),
        )


class FakeAnthropicClient:
    def __init__(self, parsed_output) -> None:
        self.messages = FakeMessagesAPI(parsed_output)


async def test_anthropic_provider_returns_parsed_output_and_usage() -> None:
    narrative = AnalysisNarrative(why=[WhyBullet(sign="+", text="test")])
    fake_client = FakeAnthropicClient(narrative)
    provider = AnthropicProvider(model="claude-opus-5", client=fake_client)

    result, usage = await provider.generate_structured("system", "user", AnalysisNarrative)

    assert result is narrative
    assert usage.model == "claude-opus-5"
    assert usage.input_tokens == 100
    assert usage.output_tokens == 30

    # verify the call shape sent to the SDK
    assert fake_client.messages.last_kwargs["model"] == "claude-opus-5"
    assert fake_client.messages.last_kwargs["system"] == "system"
    assert fake_client.messages.last_kwargs["output_format"] is AnalysisNarrative
    assert fake_client.messages.last_kwargs["messages"] == [{"role": "user", "content": "user"}]
