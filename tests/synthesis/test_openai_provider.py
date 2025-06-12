"""Test the OpenAI provider."""
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Config
from src.synthesis.providers.factory import ProviderFactory
from src.synthesis.providers.openai import OpenAIProvider


@pytest.fixture
def config() -> Config:
    """Create a default configuration for the OpenAI provider."""
    cfg = Config.default()
    cfg.openai_api_key = "sk-test"
    cfg.llm_model = "gpt-3.5-turbo"
    cfg.temperature = 0.5
    cfg.max_tokens = 123
    return cfg

@pytest.mark.asyncio
async def test_generate_success(config: Config) -> None:
    """Test that the OpenAI provider generates a response successfully."""
    provider = OpenAIProvider(config)
    mock_response = MagicMock()
    mock_response.choices = [type("obj", (), {"message": type("obj", (), {"content": "Hello world!"})()})]
    with patch.object(provider.client.chat.completions, "create", AsyncMock(return_value=mock_response)):
        result = await provider.generate("Say hello")
        assert result == "Hello world!"

@pytest.mark.asyncio
async def test_generate_api_error(config: Config) -> None:
    """Test that the OpenAI provider raises a RuntimeError when the API request fails."""
    provider = OpenAIProvider(config)
    with (
        patch.object(provider.client.chat.completions, "create", AsyncMock(side_effect=Exception("fail"))),
        pytest.raises(RuntimeError),
    ):
        await provider.generate("prompt")

def test_get_token_count_with_tiktoken(monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
    """Test that the OpenAI provider counts tokens correctly with tiktoken."""
    provider = OpenAIProvider(config)
    fake_encoding = MagicMock()
    fake_encoding.encode.return_value = [1, 2, 3]
    monkeypatch.setitem(sys.modules, "tiktoken", types.SimpleNamespace(encoding_for_model=lambda model: fake_encoding))
    assert provider.get_token_count("foo bar") == 3

def test_get_token_count_without_tiktoken(monkeypatch: pytest.MonkeyPatch, config: Config) -> None:
    """Test that the OpenAI provider raises a RuntimeError when tiktoken is not installed."""
    provider = OpenAIProvider(config)
    monkeypatch.setitem(sys.modules, "tiktoken", None)
    with pytest.raises(RuntimeError):
        provider.get_token_count("foo bar")

@pytest.mark.asyncio
async def test_validate_connection_success(config: Config) -> None:
    """Test that the OpenAI provider validates the connection successfully."""
    provider = OpenAIProvider(config)
    with patch.object(provider.client.chat.completions, "create", AsyncMock(return_value=MagicMock())):
        assert await provider.validate_connection() is True

@pytest.mark.asyncio
async def test_validate_connection_failure(config: Config) -> None:
    """Test that the OpenAI provider fails to validate the connection."""
    provider = OpenAIProvider(config)
    with patch.object(provider.client.chat.completions, "create", AsyncMock(side_effect=Exception("fail"))):
        assert await provider.validate_connection() is False

def test_provider_factory_returns_openai(config: Config) -> None:
    """Test that the provider factory returns the OpenAI provider."""
    config.refine = True
    config.llm_provider = "openai"
    provider = ProviderFactory.get_provider(config)
    assert isinstance(provider, OpenAIProvider)

def test_config_options_passed(config: Config) -> None:
    """Test that the OpenAI provider passes the config options correctly."""
    provider = OpenAIProvider(config)
    assert provider.temperature == 0.5
    assert provider.max_tokens == 123
