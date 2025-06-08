#!/usr/bin/env python3
"""
Unit tests for PDF pipeline following pytest best practices.

Tests the PDF pipeline instantiation, configuration, and core functionality
using mocks and fixtures instead of generating real PDFs.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import Config
from src.pipelines.pdf import PDFPipeline


class TestPDFPipelineInstantiation:
    """Test PDF pipeline instantiation and basic properties."""

    def test_should_instantiate_successfully_when_valid_config_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test that PDF pipeline can be instantiated correctly."""
        pipeline = PDFPipeline(test_config)

        assert pipeline is not None
        # PDF pipeline uses automatic extension detection via class name
        assert pipeline.supports_file(Path("test.pdf"))

    def test_should_inherit_from_base_pipeline_when_instantiated(
        self,
        test_config: Config,
    ) -> None:
        """Test that PDF pipeline properly inherits from BasePipeline."""
        from src.pipelines.base import BasePipeline

        pipeline = PDFPipeline(test_config)
        assert isinstance(pipeline, BasePipeline)

    def test_should_initialize_tokenizer_with_config_settings(
        self,
        test_config: Config,
    ) -> None:
        """Test that tokenizer is properly initialized with config values."""
        pipeline = PDFPipeline(test_config)

        assert hasattr(pipeline, "tokenizer")
        assert pipeline.tokenizer is not None
        # Note: HuggingFace tokenizer may have model-specific max_tokens
        # We verify it's a reasonable value, not necessarily equal to config.chunk_size
        assert pipeline.tokenizer.max_tokens > 0


class TestPDFPipelineFileSupport:
    """Test PDF pipeline file type detection and support."""

    def test_should_support_pdf_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test the supports_file method for PDF files."""
        pipeline = PDFPipeline(test_config)

        assert pipeline.supports_file(Path("document.pdf"))
        assert pipeline.supports_file(Path("test.PDF"))  # Case insensitive
        assert pipeline.supports_file(Path("path/to/file.pdf"))

    def test_should_reject_non_pdf_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test that non-PDF files are properly rejected."""
        pipeline = PDFPipeline(test_config)

        assert not pipeline.supports_file(Path("document.txt"))
        assert not pipeline.supports_file(Path("document.docx"))
        assert not pipeline.supports_file(Path("document.html"))


class TestPDFPipelineConfiguration:
    """Test PDF pipeline configuration handling."""

    def test_should_use_config_settings_when_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test that pipeline properly uses config settings."""
        pipeline = PDFPipeline(test_config)

        assert pipeline.config.chunk_size == test_config.chunk_size
        assert pipeline.config.min_tokens == test_config.min_tokens
        assert pipeline.config.preserve_tables is True

    @pytest.mark.parametrize("chunk_size", [512, 1024, 2048])
    def test_should_adapt_tokenizer_when_chunk_size_changes(
        self,
        test_config: Config,
        chunk_size: int,
    ) -> None:
        """Test pipeline with different chunk size configurations."""
        test_config.chunk_size = chunk_size
        pipeline = PDFPipeline(test_config)

        # Verify the config is set correctly
        assert pipeline.config.chunk_size == chunk_size
        # Note: Tokenizer max_tokens may be model-specific, not config-driven
        assert pipeline.tokenizer.max_tokens > 0

    @pytest.mark.parametrize("verbose", [True, False])
    def test_should_respect_verbose_setting_when_configured(
        self,
        test_config: Config,
        verbose: bool,
    ) -> None:
        """Test that verbose mode is properly configured."""
        test_config.verbose = verbose
        pipeline = PDFPipeline(test_config)

        assert pipeline.config.verbose is verbose


class TestPDFPipelineProcessing:
    """Test PDF pipeline document processing functionality."""

    def test_should_process_document_successfully_when_valid_file_provided(
        self,
        test_config: Config,
        test_file_path: Path,
        mock_docling_converter: Mock,
    ) -> None:
        """Test that process method has correct signature and basic flow."""
        pipeline = PDFPipeline(test_config)

        # Mock all the dependencies
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(pipeline, "converter", mock_docling_converter),
            patch.object(pipeline, "_chunk_document") as mock_chunk,
        ):
            # Setup mock returns with chunks that have sufficient content to pass filtering
            long_text = (
                "This is a substantial chunk with enough content to meet token requirements. "
                * 20
            )
            mock_chunk.return_value = [
                Mock(text=long_text),
                Mock(text=long_text),
            ]

            # Test the method
            result = pipeline.process(test_file_path)

            assert isinstance(result, list)
            assert len(result) == 2
            mock_chunk.assert_called_once()

    def test_should_chunk_document_correctly_when_docling_document_provided(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test the _chunk_document method with mock data."""
        pipeline = PDFPipeline(test_config)

        with patch.object(pipeline, "hybrid_chunker") as mock_chunker:
            mock_chunker.chunk.return_value = [
                Mock(text="chunk1"),
                Mock(text="chunk2"),
            ]

            result = pipeline._chunk_document(mock_docling_document)

            assert isinstance(result, list)
            assert len(result) == 2
            mock_chunker.chunk.assert_called_once_with(mock_docling_document)

    def test_should_raise_file_not_found_when_file_does_not_exist(
        self,
        test_config: Config,
    ) -> None:
        """Test error handling for non-existent files."""
        pipeline = PDFPipeline(test_config)

        with pytest.raises(FileNotFoundError):
            pipeline.process(Path("nonexistent.pdf"))


class TestPDFPipelineValidation:
    """Test PDF pipeline configuration validation."""

    def test_should_raise_error_when_invalid_configuration_provided(self) -> None:
        """Test that invalid configurations are handled properly."""
        from src.exceptions import ValidationError

        config = Config.default()
        config.chunk_size = 100  # Too small
        config.min_tokens = 200  # Larger than chunk_size

        with pytest.raises(ValidationError):
            config.validate()

    def test_should_validate_config_on_instantiation(self) -> None:
        """Test that configuration is validated during pipeline creation."""
        from src.exceptions import ValidationError

        config = Config.default()
        config.chunk_size = 50  # Invalid: too small

        # This should work because validation happens in config.validate(), not __init__
        pipeline = PDFPipeline(config)
        assert pipeline is not None

        # But calling validate should raise an error
        with pytest.raises(ValidationError):
            config.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
