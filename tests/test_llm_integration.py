"""Test the LLM integration."""

from pathlib import Path
from time import perf_counter
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Config
from src.pipelines.pdf import PDFPipeline
from src.synthesis.providers.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, fail: bool = False) -> None:
        """Initialize the mock LLM provider."""
        self.fail = fail
        self.calls = 0
    async def generate(self, prompt: str, **kwargs: object) -> str:
        """Generate a response from the mock LLM."""
        self.calls += 1
        if self.fail:
            raise RuntimeError("Mock LLM failure")
        return f"refined: {prompt[:10]}..."
    def get_token_count(self, text: str) -> int:
        """Get the token count for the text."""
        return len(text.split())

@pytest.fixture(params=["light", "moderate", "aggressive"])
def config_with_synthesis(request: pytest.SubRequest) -> Config:
    """Create a configuration for testing with synthesis enabled."""
    cfg = Config()
    cfg.refine = True
    cfg.llm_provider = "mock"
    cfg.llm_model = "mock-llm"
    cfg.refinement_level = request.param
    return cfg

@patch("src.pipelines.base.ProviderFactory.get_provider")
@patch("src.pipelines.base.ContentSynthesizer")
def test_pipeline_integration_with_mock_llm(mock_synth: MagicMock, mock_get_provider: MagicMock, config_with_synthesis: Config, tmp_path: Path) -> None:
    """Test end-to-end pipeline with mock LLM provider and synthesis enabled."""
    mock_provider = MockLLMProvider()
    mock_get_provider.return_value = mock_provider
    mock_synth.return_value.refine_chunk = AsyncMock(side_effect=lambda chunk, config: f"synth-{chunk}")
    pipeline = PDFPipeline(config_with_synthesis)
    # Patch converter to avoid file I/O
    dummy_doc = MagicMock()
    pipeline.converter = MagicMock()
    pipeline.converter.convert.return_value = MagicMock(document=dummy_doc)
    pipeline._chunk_document = MagicMock(return_value=[MagicMock()])
    pipeline._process_chunks = MagicMock(return_value=[{"content": "original", "metadata": {}}])
    t0 = perf_counter()
    result = pipeline.process(tmp_path / "dummy.pdf")
    t1 = perf_counter()
    assert result[0]["content"].startswith("synth-")
    assert result[0]["metadata"]["synthesized"] is True
    assert result[0]["metadata"]["llm_provider"] == "mock"
    assert result[0]["metadata"]["llm_model"] == "mock-llm"
    assert result[0]["metadata"]["refinement_level"] == config_with_synthesis.refinement_level
    assert (t1 - t0) < 0.1  # Should run fast (mocked)

@patch("src.pipelines.base.ProviderFactory.get_provider")
@patch("src.pipelines.base.ContentSynthesizer")
def test_pipeline_integration_llm_error(mock_synth: MagicMock, mock_get_provider: MagicMock, config_with_synthesis: Config, tmp_path: Path) -> None:
    """Test pipeline handles LLM provider errors gracefully."""
    mock_provider = MockLLMProvider(fail=True)
    mock_get_provider.return_value = mock_provider
    async def fail_chunk(chunk: str, config: Config) -> str:
        """Fail to refine the chunk."""
        raise RuntimeError("LLM error")
    mock_synth.return_value.refine_chunk = AsyncMock(side_effect=fail_chunk)
    pipeline = PDFPipeline(config_with_synthesis)
    dummy_doc = MagicMock()
    pipeline.converter = MagicMock()
    pipeline.converter.convert.return_value = MagicMock(document=dummy_doc)
    pipeline._chunk_document = MagicMock(return_value=[MagicMock()])
    pipeline._process_chunks = MagicMock(return_value=[{"content": "original", "metadata": {}}])
    with pytest.raises(RuntimeError, match="LLM error"):
        pipeline.process(tmp_path / "dummy.pdf")
