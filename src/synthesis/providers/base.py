"""Base abstract class for LLM provider implementations."""

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs: object) -> str:
        """Generate a response from the LLM provider given a prompt."""

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Return the token count for the given text."""
