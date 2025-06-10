"""OllamaProvider: LLM provider for local Ollama models via HTTP API."""

import httpx

from src.config import Config
from src.synthesis.circuit_breaker import CircuitBreaker
from src.synthesis.utils import resilient_llm_call
from src.utils import get_tokenizer

from .base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    """
    LLM provider for local Ollama server integration.

    This provider communicates with a locally running Ollama instance via HTTP API.
    It supports text generation and token counting for LLM-powered synthesis workflows.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the OllamaProvider with configuration.

        Args:
            config: The configuration object containing Ollama connection and model settings.

        """
        self.config = config
        self.base_url: str = config.ollama_base_url
        self.model: str = config.llm_model or "llama3.1"
        self.tokenizer = get_tokenizer(config)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            reset_timeout=float(config.circuit_breaker_timeout),
            exceptions=(RuntimeError,),
            name="OllamaProvider",
        )
        self._generate_resilient = resilient_llm_call(
            self._generate_raw,
            config,
            self.circuit_breaker,
        )

    async def generate(self, prompt: str, **kwargs: object) -> str:
        """
        Generate a response from the Ollama model.

        Args:
            prompt: The prompt string to send to the model.
            **kwargs: Additional parameters for the API (optional).

        Returns:
            The generated text from the model.

        Raises:
            httpx.HTTPError: If the request fails.

        """
        return await self._generate_resilient(prompt, **kwargs)

    async def _generate_raw(self, prompt: str, **kwargs: object) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            **{k: v for k, v in kwargs.items() if isinstance(k, str)},
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=60)
                response.raise_for_status()
                data = await response.json()
                return str(data.get("response", ""))
        except httpx.HTTPError as err:
            msg = f"Ollama API request failed: {err}"
            raise RuntimeError(msg) from err

    def get_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text using a HuggingFace tokenizer.

        Args:
            text: The input text to tokenize.

        Returns:
            The estimated token count (approximate, since Ollama does not expose a native endpoint).

        """
        token_count: int = self.tokenizer.count_tokens(text)
        return token_count
