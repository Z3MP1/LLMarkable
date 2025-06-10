"""Test the OpenAI provider."""
from unittest.mock import AsyncMock, patch

import pytest

from src.config import Config
from src.synthesis.providers.openai import OpenAIProvider


@pytest.fixture
def config() -> Config:
    """Create a default configuration for the OpenAI provider."""
    cfg = Config.default()
    cfg.openai_api_key = "sk-test"
    cfg.llm_model = "gpt-3.5-turbo"
    return cfg

@pytest.mark.asyncio
async def test_generate_success(config: Config) -> None:
    """Test that the OpenAI provider generates a response successfully."""
    provider = OpenAIProvider(config)
    mock_response = AsyncMock()
    mock_response.choices = [type("obj", (), {"message": type("obj", (), {"content": "Hello world!"})()})]
    with patch("openai.ChatCompletion.acreate", AsyncMock(return_value=mock_response)):
        result = await provider.generate("Say hello")
        assert result == "Hello world!"

@pytest.mark.asyncio
async def test_generate_api_error(config: Config) -> None:
    """Test that the OpenAI provider raises a RuntimeError when the API request fails."""
    provider = OpenAIProvider(config)
    with (
        patch("openai.ChatCompletion.acreate", AsyncMock(side_effect=Exception("fail"))),
        pytest.raises(RuntimeError),
    ):
        await provider.generate("prompt")

def test_get_token_count_not_implemented(config: Config) -> None:
    """Test that the OpenAI provider raises a NotImplementedError when token counting is not implemented."""
    provider = OpenAIProvider(config)
    with pytest.raises(NotImplementedError):
        provider.get_token_count("test string")
 