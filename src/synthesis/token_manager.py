"""Token manager for tracking token usage and cost."""

from dataclasses import dataclass

from src.config import Config
from src.synthesis.providers.base import BaseLLMProvider


@dataclass
class TokenUsage:
    """Track token usage and cost."""

    total_tokens: int = 0
    total_cost: float = 0.0
    requests: int = 0
    provider: str = ""
    model: str = ""


class TokenManager:
    """Manages token counting, batching, caching, and cost estimation for LLM providers."""

    def __init__(self, provider: BaseLLMProvider, config: Config) -> None:
        """Initialize the token manager."""
        self.provider = provider
        self.config = config
        self.usage = TokenUsage(provider=config.llm_provider or "", model=config.llm_model or "")
        self._cache: dict[str, int] = {}

    def count_tokens(self, text: str) -> int:
        """Count tokens for a single string, using provider's tokenizer. Caches results."""
        if text in self._cache:
            return self._cache[text]
        count = self.provider.get_token_count(text)
        self._cache[text] = count
        self.usage.total_tokens += count
        return count

    def batch_token_count(self, texts: list[str]) -> list[int]:
        """Count tokens for a batch of strings. Uses cache and provider efficiently."""
        return [self.count_tokens(t) for t in texts]

    def estimate_cost(self, tokens: int | None = None) -> float:
        """
        Estimate cost for a given number of tokens, based on provider/model.

        If tokens is None, use total usage so far.
        """
        tokens = tokens if tokens is not None else self.usage.total_tokens
        provider = (self.config.llm_provider or "").lower()
        model = (self.config.llm_model or "").lower()
        # OpenAI pricing (as of 2025-06)
        openai_prices = {
            "gpt-3.5-turbo": 0.0005 / 1000,  # $0.0005 per 1K tokens
            "gpt-4": 0.03 / 1000,            # $0.03 per 1K tokens (input)
            "gpt-4-turbo": 0.01 / 1000,      # $0.01 per 1K tokens (input)
        }
        if provider == "openai":
            for key, price in openai_prices.items():
                if key in model:
                    return tokens * price
            # Default to GPT-3.5 price if unknown
            return tokens * openai_prices["gpt-3.5-turbo"]
        if provider == "ollama":
            return 0.0  # Local, free
        # Add more providers as needed
        return 0.0

    def track_usage(self, tokens: int) -> None:
        """Track token usage and update cost."""
        self.usage.total_tokens += tokens
        self.usage.total_cost = self.estimate_cost()
        self.usage.requests += 1

    def get_usage(self) -> TokenUsage:
        """Get current usage statistics."""
        self.usage.total_cost = self.estimate_cost()
        return self.usage
