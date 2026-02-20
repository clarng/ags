"""
Sampler Library - Unified interface for OpenAI and Claude APIs.

Supports switching between providers while maintaining a consistent interface.

Usage:
    from ags.lib.sampler import Sampler

    # OpenAI (default)
    sampler = Sampler.create(provider="openai")

    # Claude
    sampler = Sampler.create(provider="claude")

    # Chat
    response = sampler.chat(
        system_prompt="You are helpful.",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(response.text)
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator

from openai import OpenAI
from anthropic import Anthropic


PROVIDERS = {"OPENAI": "openai", "CLAUDE": "claude"}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "claude": "claude-sonnet-4-20250514",
}


@dataclass
class SamplerResponse:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    stop_reason: str | None = None
    raw: Any = field(default=None, repr=False)


class BaseSampler(ABC):
    def __init__(self, model: str | None = None, max_tokens: int = 1024):
        self.model = model
        self.max_tokens = max_tokens

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> SamplerResponse:
        ...

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Generator[str, None, None]:
        ...


class OpenAISampler(BaseSampler):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ):
        super().__init__(model=model or DEFAULT_MODELS["openai"], max_tokens=max_tokens)
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def chat(self, messages, system_prompt=None, max_tokens=None, temperature=None):
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        formatted.extend(messages)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": formatted,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = self.client.chat.completions.create(**kwargs)

        return SamplerResponse(
            text=response.choices[0].message.content,
            model=response.model,
            input_tokens=getattr(response.usage, "prompt_tokens", None),
            output_tokens=getattr(response.usage, "completion_tokens", None),
            stop_reason=response.choices[0].finish_reason,
            raw=response,
        )

    def chat_stream(self, messages, system_prompt=None, max_tokens=None, temperature=None):
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        formatted.extend(messages)

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": formatted,
            "stream": True,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        stream = self.client.chat.completions.create(**kwargs)

        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices[0].delta else None
            if delta:
                yield delta


class ClaudeSampler(BaseSampler):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ):
        super().__init__(model=model or DEFAULT_MODELS["claude"], max_tokens=max_tokens)
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def chat(self, messages, system_prompt=None, max_tokens=None, temperature=None):
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = self.client.messages.create(**kwargs)

        text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        return SamplerResponse(
            text=text,
            model=response.model,
            input_tokens=getattr(response.usage, "input_tokens", None),
            output_tokens=getattr(response.usage, "output_tokens", None),
            stop_reason=response.stop_reason,
            raw=response,
        )

    def chat_stream(self, messages, system_prompt=None, max_tokens=None, temperature=None):
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if temperature is not None:
            kwargs["temperature"] = temperature

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text


class Sampler:
    """Factory for creating sampler instances."""

    @staticmethod
    def create(
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> BaseSampler:
        provider = (provider or os.environ.get("LLM_PROVIDER", "openai")).lower()

        if provider in ("openai", "gpt"):
            return OpenAISampler(api_key=api_key, model=model, max_tokens=max_tokens)
        elif provider in ("claude", "anthropic"):
            return ClaudeSampler(api_key=api_key, model=model, max_tokens=max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'claude'.")
