"""Test the token manager."""

import pytest

from src.config import Config
from src.synthesis.token_manager import TokenManager


class DummyProvider:
    """Dummy provider for testing."""

    def __init__(self) -> None:
        """Initialize the dummy provider."""
        self.calls = 0

    def get_token_count(self, text: str) -> int:
        """Get the token count for the text."""
        self.calls += 1
        return len(text.split())

@pytest.fixture
def config_openai() -> Config:
    """Create a configuration for testing with OpenAI."""
    cfg = Config()
    cfg.llm_provider = "openai"
    cfg.llm_model = "gpt-3.5-turbo"
    return cfg

@pytest.fixture
def config_ollama() -> Config:
    """Create a configuration for testing with Ollama."""
    cfg = Config()
    cfg.llm_provider = "ollama"
    cfg.llm_model = "llama3"
    return cfg

def test_count_tokens_caching(config_openai: Config) -> None:
    """Test that the token manager caches tokens."""
    provider = DummyProvider()
    tm = TokenManager(provider, config_openai)
    text = "hello world"
    assert tm.count_tokens(text) == 2
    assert tm.count_tokens(text) == 2  # Cached
    assert provider.calls == 1

def test_batch_token_count(config_openai: Config) -> None:
    """Test that the token manager batches token counts."""
    provider = DummyProvider()
    tm = TokenManager(provider, config_openai)
    texts = ["a b c", "d e"]
    counts = tm.batch_token_count(texts)
    assert counts == [3, 2]
    assert provider.calls == 2

def test_estimate_cost_openai(config_openai: Config) -> None:
    """Test that the token manager estimates the cost for OpenAI."""
    provider = DummyProvider()
    tm = TokenManager(provider, config_openai)
    tm.usage.total_tokens = 2000
    cost = tm.estimate_cost()
    assert 0.0009 < cost < 0.0011  # $0.001 for 2K tokens

def test_estimate_cost_ollama(config_ollama: Config) -> None:
    """Test that the token manager estimates the cost for Ollama."""
    provider = DummyProvider()
    tm = TokenManager(provider, config_ollama)
    tm.usage.total_tokens = 5000
    cost = tm.estimate_cost()
    assert cost == 0.0

def test_track_usage_and_get_usage(config_openai: Config) -> None:
    """Test that the token manager tracks usage and gets usage."""
    provider = DummyProvider()
    tm = TokenManager(provider, config_openai)
    tm.track_usage(100)
    usage = tm.get_usage()
    assert usage.total_tokens == 100
    assert usage.total_cost > 0.0
    assert usage.requests == 1
