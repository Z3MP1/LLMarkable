"""Test the synthesis pipeline."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import Config
from src.pipelines.pdf import PDFPipeline


@pytest.fixture
def config_refine_true() -> Config:
    """Create a configuration for testing with synthesis enabled."""
    cfg = Config()
    cfg.refine = True
    cfg.llm_provider = "openai"
    cfg.llm_model = "gpt-3.5-turbo"
    cfg.refinement_level = "aggressive"
    cfg.openai_api_key = "sk-test"
    return cfg

@pytest.fixture
def config_refine_false() -> Config:
    """Create a configuration for testing with synthesis disabled."""
    cfg = Config()
    cfg.refine = False
    return cfg

@patch("src.pipelines.base.ContentSynthesizer")
@patch("src.pipelines.base.ProviderFactory.get_provider")
def test_pdf_pipeline_synthesizes_chunks(mock_get_provider: MagicMock, mock_synth: MagicMock, config_refine_true: Config, tmp_path: Path) -> None:
    """Test that the PDF pipeline synthesizes chunks."""
    mock_provider = MagicMock()
    mock_get_provider.return_value = mock_provider
    mock_synth.return_value.refine_chunk = AsyncMock(return_value="synthesized")
    pipeline = PDFPipeline(config_refine_true)
    # Patch converter to avoid file I/O
    dummy_doc = MagicMock()
    pipeline.converter = MagicMock()
    pipeline.converter.convert.return_value = MagicMock(document=dummy_doc)
    pipeline._chunk_document = MagicMock(return_value=[MagicMock()])
    pipeline._process_chunks = MagicMock(return_value=[{"content": "original", "metadata": {}}])
    result = pipeline.process(tmp_path / "dummy.pdf")
    assert result[0]["content"] == "synthesized"
    assert result[0]["metadata"]["synthesized"] is True
    assert result[0]["metadata"]["llm_provider"] == "openai"
    assert result[0]["metadata"]["llm_model"] == "gpt-3.5-turbo"
    assert result[0]["metadata"]["refinement_level"] == "aggressive"

@patch("src.pipelines.base.ContentSynthesizer")
@patch("src.pipelines.base.ProviderFactory.get_provider")
def test_pdf_pipeline_no_synthesis_when_refine_false(mock_get_provider: MagicMock, mock_synth: MagicMock, config_refine_false: Config, tmp_path: Path) -> None:
    """Test that the PDF pipeline does not synthesize chunks when refine is False."""
    pipeline = PDFPipeline(config_refine_false)
    # Patch converter to avoid file I/O
    dummy_doc = MagicMock()
    pipeline.converter = MagicMock()
    pipeline.converter.convert.return_value = MagicMock(document=dummy_doc)
    pipeline._chunk_document = MagicMock(return_value=[MagicMock()])
    pipeline._process_chunks = MagicMock(return_value=[{"content": "original", "metadata": {}}])
    result = pipeline.process(tmp_path / "dummy.pdf")
    assert result[0]["content"] == "original"
    assert "synthesized" not in result[0]["metadata"]
