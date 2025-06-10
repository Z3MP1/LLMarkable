"""OpenAI provider."""

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
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(self, prompt: str, **kwargs: object) -> str:  # noqa: ARG002
        """
        Generate a response from the OpenAI model.

        Args:
            prompt (str): The prompt string to send to the model.
            **kwargs: Additional parameters for the API (optional).

        Returns:
            str: The generated text from the model.

        """
        def _raise_no_content() -> None:
            msg = "OpenAI API returned no content in the response."
            raise RuntimeError(msg)
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content
            if content is None:
                _raise_no_content()
            assert content is not None  # type guard for ruff
            return content.strip()
        except Exception as err:
            msg = f"OpenAI API request failed: {err}"
            raise RuntimeError(msg) from err

    def get_token_count(self, text: str) -> int:
        """
        Estimate the number of tokens in the given text using OpenAI's tiktoken or similar tokenizer.

        Args:
            text (str): The input text to tokenize.

        Returns:
            int: The estimated token count.

        """
        # tiktoken is not installed; raise for now
        msg = "Token counting requires tiktoken, which is not installed."
        raise NotImplementedError(msg)
