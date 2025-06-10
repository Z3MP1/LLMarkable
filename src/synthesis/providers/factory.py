"""Factory for instantiating the correct LLM provider based on configuration."""

from src.config import Config

from .base import BaseLLMProvider
from .noop import NoOpProvider
from .ollama import OllamaProvider


class ProviderFactory:
    """Factory for instantiating the correct LLM provider based on configuration."""

    @staticmethod
    def get_provider(config: Config) -> BaseLLMProvider:
        """
        Return an LLM provider instance based on the configuration.

        Supports: Ollama (local), NoOpProvider (default), and stubs for OpenAI, Anthropic, Google.

        Args:
            config: The configuration object.

        Returns:
            An instance of BaseLLMProvider (or subclass).

        Raises:
            ValueError: If the provider is unknown.
            NotImplementedError: If the provider is not yet implemented.

        """
        if not config.refine:
            return NoOpProvider()
        provider = (config.llm_provider or "").lower()
        if provider == "ollama":
            return OllamaProvider(config)
        if provider == "openai":
            msg = "OpenAIProvider is not yet implemented."
            raise NotImplementedError(msg)
        if provider == "anthropic":
            msg = "AnthropicProvider is not yet implemented."
            raise NotImplementedError(msg)
        if provider == "google":
            msg = "GoogleProvider is not yet implemented."
            raise NotImplementedError(msg)
        msg = f"Unknown LLM provider: {provider}"
        raise ValueError(msg)
