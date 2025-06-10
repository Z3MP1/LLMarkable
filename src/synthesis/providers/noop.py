"""NoOpProvider: returns input unchanged, for cases where synthesis is disabled."""

from src.config import Config
from src.synthesis.circuit_breaker import CircuitBreaker
from src.synthesis.utils import resilient_llm_call

from .base import BaseLLMProvider


class NoOpProvider(BaseLLMProvider):
    """Provider that returns the input unchanged (no synthesis)."""

    def __init__(self) -> None:
        """Initialize the NoOpProvider."""
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=1000,
            reset_timeout=1.0,
            exceptions=(Exception,),
            name="NoOpProvider",
        )
        self._generate_resilient = resilient_llm_call(self._generate_raw, Config.default(), self.circuit_breaker)

    async def generate(self, prompt: str, **kwargs: object) -> str:
        """Generate a response from the NoOpProvider."""
        return await self._generate_resilient(prompt, **kwargs)

    async def _generate_raw(self, prompt: str, **kwargs: object) -> str:  # noqa: ARG002
        """Generate a response from the NoOpProvider."""
        return prompt

    def get_token_count(self, text: str) -> int:
        """Return the token count for the given text."""
        return len(text.split())
