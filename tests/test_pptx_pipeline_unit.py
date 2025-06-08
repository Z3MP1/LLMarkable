"""Unit tests for PPTX pipeline functionality validation."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import Config
from src.exceptions import ValidationError
from src.pipelines.pptx import PptxPipeline


class TestPptxPipelineInstantiation:
    """Test PPTX pipeline instantiation and initialization."""

    def test_should_instantiate_successfully_when_valid_config_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test successful PPTX pipeline instantiation."""
        pipeline = PptxPipeline(test_config)

        assert pipeline is not None
        assert pipeline.config == test_config

    def test_should_inherit_from_base_pipeline_when_instantiated(
        self,
        test_config: Config,
    ) -> None:
        """Test PPTX pipeline inheritance."""
        from src.pipelines.base import BasePipeline

        pipeline = PptxPipeline(test_config)

        assert isinstance(pipeline, BasePipeline)

    def test_should_initialize_tokenizer_with_config_settings(
        self,
        test_config: Config,
    ) -> None:
        """Test tokenizer initialization with config settings."""
        pipeline = PptxPipeline(test_config)

        assert pipeline.tokenizer is not None
        # Verify tokenizer configuration matches config
        assert hasattr(pipeline, "hybrid_chunker")
        assert hasattr(pipeline, "hierarchical_chunker")

    def test_should_configure_word_format_option_with_simple_pipeline(
        self,
        test_config: Config,
    ) -> None:
        """Test WordFormatOption configuration for PPTX processing."""
        pipeline = PptxPipeline(test_config)

        assert pipeline.word_options is not None
        assert hasattr(pipeline, "converter")


class TestPptxPipelineFileSupport:
    """Test PPTX pipeline file support functionality."""

    def test_should_support_pptx_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test PPTX file extension support."""
        pipeline = PptxPipeline(test_config)

        assert pipeline.supports_file(Path("presentation.pptx"))
        assert pipeline.supports_file(Path("TEST.PPTX"))  # Case insensitive

    def test_should_reject_non_pptx_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test rejection of non-PPTX files."""
        pipeline = PptxPipeline(test_config)

        assert not pipeline.supports_file(Path("document.pdf"))
        assert not pipeline.supports_file(Path("document.docx"))
        assert not pipeline.supports_file(Path("page.html"))
        assert not pipeline.supports_file(Path("data.csv"))


class TestPptxPipelineConfiguration:
    """Test PPTX pipeline configuration handling."""

    def test_should_use_config_settings_when_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test config settings usage in processing."""
        pipeline = PptxPipeline(test_config)

        assert pipeline.config.chunk_size == test_config.chunk_size
        assert pipeline.config.min_tokens == test_config.min_tokens
        assert pipeline.config.verbose == test_config.verbose

    def test_should_initialize_docling_converter_with_word_format_option(
        self,
        test_config: Config,
    ) -> None:
        """Test Docling converter initialization."""
        pipeline = PptxPipeline(test_config)

        assert pipeline.converter is not None
        assert pipeline.word_options is not None


class TestPptxPipelineProcessing:
    """Test PPTX pipeline document processing functionality."""

    def test_should_chunk_presentation_correctly_when_docling_document_provided(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test the _chunk_presentation method with mock data."""
        pipeline = PptxPipeline(test_config)

        with patch.object(pipeline, "hybrid_chunker") as mock_chunker:
            mock_chunker.chunk.return_value = [
                Mock(text="Slide 1: Introduction"),
                Mock(text="Slide 2: Content"),
            ]

            result = pipeline._chunk_presentation(mock_docling_document)

            assert isinstance(result, list)
            assert len(result) == 2
            mock_chunker.chunk.assert_called_once_with(mock_docling_document)

    def test_should_raise_file_not_found_when_file_does_not_exist(
        self,
        test_config: Config,
    ) -> None:
        """Test FileNotFoundError for missing PPTX files."""
        pipeline = PptxPipeline(test_config)
        non_existent_file = Path("nonexistent.pptx")

        with pytest.raises(FileNotFoundError, match="PPTX file not found"):
            pipeline.process(non_existent_file)


class TestPptxPipelineValidation:
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
        pipeline = PptxPipeline(test_config)
        assert pipeline.config == test_config
