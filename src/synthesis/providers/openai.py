"""OpenAI provider."""

import logging

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore
from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from src.config import Config
from src.synthesis.providers.base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """
    LLM provider for OpenAI API integration.

    Supports text generation and token counting for LLM-powered synthesis workflows using OpenAI models.
    """

    def __init__(self, config: Config) -> None:
        """
        Initialize the OpenAIProvider with configuration.

        Args:
            config (Config): The configuration object containing OpenAI API key and model settings.

        """
        self.config = config
        self.api_key: str | None = config.openai_api_key
        self.model: str = config.llm_model or "gpt-3.5-turbo"
        self.temperature: float = getattr(config, "temperature", 0.7)
        self.max_tokens: int = getattr(config, "max_tokens", 2048)
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.logger = logging.getLogger("OpenAIProvider")

    async def generate(self, prompt: str, **_kwargs: object) -> str:
        """
        Generate a response from the OpenAI model.

        Args:
            prompt (str): The prompt string to send to the model.
            **kwargs: Additional parameters for the API (optional).

        Returns:
            str: The generated text from the model.

        Raises:
            RuntimeError: If the API request fails or returns no content.

        """
        def _raise_no_content() -> None:
            msg = "OpenAI API returned no content in the response."
            self.logger.error(msg)
            raise RuntimeError(msg)
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                _raise_no_content()
            assert isinstance(content, str)
            msg = f"OpenAI response received, {len(content)} chars."
            self.logger.info(msg)
            return content.strip()
        except Exception as err:
            msg = f"OpenAI API request failed: {err}"
            self.logger.exception(msg)
            raise RuntimeError(msg) from err

    def get_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text using OpenAI's tiktoken tokenizer.

        Args:
            text (str): The input text to tokenize.

        Returns:
            int: The estimated token count.

        Raises:
            RuntimeError: If tiktoken is not available for the model.

        """
        if tiktoken is None:
            msg = "tiktoken is not installed. Please install tiktoken to use token counting with OpenAIProvider."
            self.logger.error(msg)
            raise RuntimeError(msg)
        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except Exception as err:
            msg = f"tiktoken encoding not found for model {self.model}: {err}"
            self.logger.exception(msg)
            raise RuntimeError(msg) from err
        return len(encoding.encode(text))

    async def validate_connection(self) -> bool:
        """
        Validate the OpenAI API key by making a lightweight request.

        Returns:
            bool: True if the API key is valid, False otherwise.

        """
        try:
            # Use a minimal prompt and max_tokens=1 for a cheap validation
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
        except Exception:
            self.logger.exception("OpenAI API key validation failed")
            return False
        else:
            self.logger.info("OpenAI API key validated successfully.")
            return True

    async def stream_generate(self, prompt: str, **_kwargs: object) -> AsyncGenerator[str, None]:
        """
        Stream a response from the OpenAI model as an async generator.

        Args:
            prompt (str): The prompt string to send to the model.
            **kwargs: Additional parameters for the API (optional).

        Yields:
            str: The next chunk of generated text from the model as it arrives.

        Raises:
            RuntimeError: If the API request fails or yields no content.

        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                # Note: extra kwargs are not passed to avoid API signature errors
            )
            async for chunk in stream:
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    yield delta
        except Exception as err:
            msg = f"OpenAI API streaming request failed: {err}"
            self.logger.exception(msg)
            raise RuntimeError(msg) from err
