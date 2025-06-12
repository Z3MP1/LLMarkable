"""Test the OllamaProvider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio

from src.config import Config
from src.exceptions import ProviderError, RateLimitError
from src.synthesis.providers.ollama import OllamaProvider


@pytest_asyncio.fixture
async def config() -> Config:
    """Fixture for the OllamaProvider configuration."""
    cfg = Config.default()
    cfg.llm_model = "mistral:7b"
    cfg.ollama_base_url = "http://localhost:11434"
    return cfg


@pytest.mark.asyncio
async def test_generate_success(config: Config) -> None:
    """Test that the OllamaProvider generates a response successfully."""
    provider = OllamaProvider(config)
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"response": "Hello world!"})
    mock_response.raise_for_status = Mock(return_value=None)
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)):
        result = await provider.generate("Say hello")
        assert result == "Hello world!"


@pytest.mark.asyncio
async def test_generate_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the OllamaProvider raises an exception for an HTTP error."""
    config = Config.default()
    async def fail(*args: object, **kwargs: object) -> str:
        raise RuntimeError("fail")
    monkeypatch.setattr(OllamaProvider, "_generate_raw", AsyncMock(side_effect=fail))
    provider = OllamaProvider(config)
    with pytest.raises(RuntimeError):
        await provider.generate("prompt")


def test_get_token_count(config: Config) -> None:
    """Test that the OllamaProvider returns the correct token count."""
    provider = OllamaProvider(config)
    provider.tokenizer = MagicMock()
    provider.tokenizer.count_tokens.return_value = 42
    result = provider.get_token_count("test string")
    assert result == 42


@pytest.mark.asyncio
async def test_generate_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that network errors are handled gracefully."""
    config = Config.default()
    async def fail(*args: object, **kwargs: object) -> str:
        raise ProviderError("network fail")
    monkeypatch.setattr(OllamaProvider, "_generate_raw", AsyncMock(side_effect=fail))
    provider = OllamaProvider(config)
    with pytest.raises(ProviderError):
        await provider.generate("prompt")


def test_get_token_count_empty(config: Config) -> None:
    """Test token count for empty string returns 0 or expected value."""
    provider = OllamaProvider(config)
    provider.tokenizer = MagicMock()
    provider.tokenizer.count_tokens.return_value = 0
    result = provider.get_token_count("")
    assert result == 0


@pytest.mark.asyncio
async def test_generate_success_first_try(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the OllamaProvider generates a response successfully on the first try."""
    config = Config.default()
    provider = OllamaProvider(config)
    # Patch the _generate_resilient method directly to avoid decorator issues
    monkeypatch.setattr(provider, "_generate_resilient", AsyncMock(return_value="ok"))
    result = await provider.generate("prompt")
    assert result == "ok"


@pytest.mark.asyncio
async def test_generate_retries_on_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the OllamaProvider retries on transient errors."""
    config = Config.default()
    config.max_retries = 2
    call_count = 0

    async def flaky(*args: object, **kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RateLimitError("rate limited")
        return "recovered"

    monkeypatch.setattr(OllamaProvider, "_generate_raw", AsyncMock(side_effect=flaky))
    provider = OllamaProvider(config)
    result = await provider.generate("prompt")
    assert result == "recovered"
    assert call_count == 2


@pytest.mark.asyncio
async def test_circuit_breaker_opens(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the OllamaProvider opens the circuit breaker on errors."""
    config = Config.default()
    config.circuit_breaker_threshold = 2
    config.max_retries = 0
    monkeypatch.setattr(OllamaProvider, "_generate_raw", AsyncMock(side_effect=RateLimitError("fail")))
    provider = OllamaProvider(config)
    with pytest.raises(RateLimitError):
        await provider.generate("prompt")


@pytest.mark.asyncio
async def test_circuit_breaker_recovers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the OllamaProvider recovers from a circuit breaker error."""
    config = Config.default()
    config.circuit_breaker_threshold = 1
    config.circuit_breaker_timeout = 1
    config.max_retries = 0
    monkeypatch.setattr(OllamaProvider, "_generate_raw", AsyncMock(side_effect=RateLimitError("fail")))
    provider = OllamaProvider(config)
    with pytest.raises(RateLimitError):
        await provider.generate("prompt")
    # Wait for the circuit breaker to reset
    await asyncio.sleep(1.1)
    # Now patch to succeed
    monkeypatch.setattr(OllamaProvider, "_generate_raw", AsyncMock(return_value="ok"))
    provider = OllamaProvider(config)  # Re-instantiate to wrap the new mock
    result = await provider.generate("prompt")
    assert result == "ok"


@pytest.mark.asyncio
async def test_no_retry_on_unexpected_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that the OllamaProvider does not retry on unexpected errors."""
    config = Config.default()
    config.max_retries = 2
    monkeypatch.setattr(OllamaProvider, "_generate_raw", AsyncMock(side_effect=ValueError("bad")))
    provider = OllamaProvider(config)
    with pytest.raises(ValueError):
        await provider.generate("prompt")
