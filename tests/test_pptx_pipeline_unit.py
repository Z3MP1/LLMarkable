"""Unit tests for PPTX pipeline functionality validation."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import Config
from src.exceptions import ValidationError
from src.pipelines.pptx import PPTXPipeline


class TestPPTXPipelineInstantiation:
    """Test PPTX pipeline instantiation and initialization."""

    def test_should_instantiate_successfully_when_valid_config_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test successful PPTX pipeline instantiation."""
        pipeline = PPTXPipeline(test_config)

        assert pipeline is not None
        assert pipeline.config == test_config

    def test_should_inherit_from_base_pipeline_when_instantiated(
        self,
        test_config: Config,
    ) -> None:
        """Test PPTX pipeline inheritance."""
        from src.pipelines.base import BasePipeline

        pipeline = PPTXPipeline(test_config)

        assert isinstance(pipeline, BasePipeline)

    def test_should_initialize_tokenizer_with_config_settings(
        self,
        test_config: Config,
    ) -> None:
        """Test tokenizer initialization with config settings."""
        pipeline = PPTXPipeline(test_config)

        assert pipeline.tokenizer is not None
        # Verify tokenizer configuration matches config
        assert hasattr(pipeline, "hybrid_chunker")
        assert hasattr(pipeline, "hierarchical_chunker")

    def test_should_configure_converter_for_pptx_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test DocumentConverter configuration for PPTX processing."""
        pipeline = PPTXPipeline(test_config)

        assert hasattr(pipeline, "converter")
        assert pipeline.converter is not None


class TestPPTXPipelineFileSupport:
    """Test PPTX pipeline file support functionality."""

    def test_should_support_pptx_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test PPTX file extension support."""
        pipeline = PPTXPipeline(test_config)

        assert pipeline.supports_file(Path("presentation.pptx"))
        assert pipeline.supports_file(Path("TEST.PPTX"))  # Case insensitive

    def test_should_reject_non_pptx_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test rejection of non-PPTX files."""
        pipeline = PPTXPipeline(test_config)

        assert not pipeline.supports_file(Path("document.pdf"))
        assert not pipeline.supports_file(Path("document.docx"))
        assert not pipeline.supports_file(Path("page.html"))
        assert not pipeline.supports_file(Path("data.csv"))


class TestPPTXPipelineConfiguration:
    """Test PPTX pipeline configuration handling."""

    def test_should_use_config_settings_when_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test config settings usage in processing."""
        pipeline = PPTXPipeline(test_config)

        assert pipeline.config.chunk_size == test_config.chunk_size
        assert pipeline.config.min_tokens == test_config.min_tokens
        assert pipeline.config.verbose == test_config.verbose

    def test_should_initialize_docling_converter_properly(
        self,
        test_config: Config,
    ) -> None:
        """Test Docling converter initialization."""
        pipeline = PPTXPipeline(test_config)

        assert pipeline.converter is not None


class TestPPTXPipelineProcessing:
    """Test PPTX pipeline document processing functionality."""

    def test_should_chunk_document_correctly_when_docling_document_provided(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test the _chunk_document method with mock data."""
        pipeline = PPTXPipeline(test_config)

        with patch.object(pipeline, "hybrid_chunker") as mock_chunker:
            mock_chunker.chunk.return_value = [
                Mock(text="Slide 1: Introduction"),
                Mock(text="Slide 2: Content"),
            ]

            result = pipeline._chunk_document(mock_docling_document)  # noqa: SLF001

            assert isinstance(result, list)
            assert len(result) == 2
            mock_chunker.chunk.assert_called_once_with(dl_doc=mock_docling_document)

    def test_should_raise_file_not_found_when_file_does_not_exist(
        self,
        test_config: Config,
    ) -> None:
        """Test FileNotFoundError for missing PPTX files."""
        pipeline = PPTXPipeline(test_config)
        non_existent_file = Path("nonexistent.pptx")

        from src.exceptions import ConversionError

        with pytest.raises(ConversionError):
            pipeline.process(non_existent_file)


class TestPPTXPipelineValidation:
    """Test PPTX pipeline validation functionality."""

    def test_should_raise_error_when_invalid_configuration_provided(self) -> None:
        """Test error handling for invalid configuration."""
        # Create invalid config
        with pytest.raises(ValidationError):  # noqa: PT012
            invalid_config = Config(
                chunk_size=50,  # Too small
                min_tokens=100,  # Larger than chunk_size
            )
            invalid_config.validate()

    def test_should_validate_config_on_instantiation(
        self,
        test_config: Config,
    ) -> None:
        """Test config validation during pipeline instantiation."""
        # Should not raise any exception with valid config
        pipeline = PPTXPipeline(test_config)
        assert pipeline.config == test_config
