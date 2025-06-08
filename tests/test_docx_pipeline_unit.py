#!/usr/bin/env python3
"""
Unit tests for DOCX pipeline following pytest best practices.

Tests the DOCX pipeline instantiation, configuration, and core functionality
using mocks and fixtures instead of generating real DOCX files.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import Config
from src.pipelines.docx import DocxPipeline


class TestDocxPipelineInstantiation:
    """Test DOCX pipeline instantiation and basic properties."""

    def test_should_instantiate_successfully_when_valid_config_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test that DOCX pipeline can be instantiated correctly."""
        pipeline = DocxPipeline(test_config)

        assert pipeline is not None
        # DOCX pipeline uses automatic extension detection via class name
        assert pipeline.supports_file(Path("test.docx"))

    def test_should_inherit_from_base_pipeline_when_instantiated(
        self,
        test_config: Config,
    ) -> None:
        """Test that DOCX pipeline properly inherits from BasePipeline."""
        from src.pipelines.base import BasePipeline

        pipeline = DocxPipeline(test_config)
        assert isinstance(pipeline, BasePipeline)

    def test_should_initialize_tokenizer_with_config_settings(
        self,
        test_config: Config,
    ) -> None:
        """Test that tokenizer is properly initialized with config values."""
        pipeline = DocxPipeline(test_config)

        assert hasattr(pipeline, "tokenizer")
        assert pipeline.tokenizer is not None
        # BGE tokenizer has model-specific max_tokens (512)
        assert pipeline.tokenizer.max_tokens == 512

    def test_should_configure_word_format_option_with_simple_pipeline(
        self,
        test_config: Config,
    ) -> None:
        """Test that WordFormatOption is properly configured with SimplePipeline."""
        from docling.pipeline.simple_pipeline import SimplePipeline

        pipeline = DocxPipeline(test_config)

        assert hasattr(pipeline, "word_options")
        assert pipeline.word_options.pipeline_cls == SimplePipeline


class TestDocxPipelineFileSupport:
    """Test DOCX pipeline file type detection and support."""

    def test_should_support_docx_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test the supports_file method for DOCX files."""
        pipeline = DocxPipeline(test_config)

        assert pipeline.supports_file(Path("document.docx"))
        assert pipeline.supports_file(Path("test.DOCX"))  # Case insensitive
        assert pipeline.supports_file(Path("path/to/file.docx"))

    def test_should_reject_non_docx_files_when_checking_extensions(
        self,
        test_config: Config,
    ) -> None:
        """Test that non-DOCX files are properly rejected."""
        pipeline = DocxPipeline(test_config)

        assert not pipeline.supports_file(Path("document.txt"))
        assert not pipeline.supports_file(Path("document.pdf"))
        assert not pipeline.supports_file(Path("document.html"))
        assert not pipeline.supports_file(Path("document.pptx"))


class TestDocxPipelineConfiguration:
    """Test DOCX pipeline configuration handling."""

    def test_should_use_config_settings_when_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test that pipeline properly uses config settings."""
        pipeline = DocxPipeline(test_config)

        assert pipeline.config.chunk_size == test_config.chunk_size
        assert pipeline.config.min_tokens == test_config.min_tokens
        assert pipeline.config.preserve_tables is True

    def test_should_initialize_docling_converter_with_word_format_option(
        self,
        test_config: Config,
    ) -> None:
        """Test that DocumentConverter is properly initialized with WordFormatOption."""
        pipeline = DocxPipeline(test_config)

        assert hasattr(pipeline, "converter")
        assert pipeline.converter is not None


class TestDocxPipelineProcessing:
    """Test DOCX pipeline document processing functionality."""

    def test_should_chunk_document_correctly_when_docling_document_provided(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test the _chunk_document method with mock data."""
        pipeline = DocxPipeline(test_config)

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
        pipeline = DocxPipeline(test_config)

        with pytest.raises(FileNotFoundError):
            pipeline.process(Path("nonexistent.docx"))


class TestDocxPipelineValidation:
    """Test DOCX pipeline configuration validation."""

    def test_should_raise_error_when_invalid_configuration_provided(self) -> None:
        """Test that invalid configurations are handled properly."""
        from src.exceptions import ValidationError

        config = Config.default()
        config.chunk_size = 100  # Too small
        config.min_tokens = 200  # Larger than chunk_size

        with pytest.raises(ValidationError):
            # This should fail during config validation
            config.validate()

    def test_should_validate_config_on_instantiation(self) -> None:
        """Test that config validation occurs during pipeline instantiation."""
        config = Config.default()
        # Use valid settings
        config.chunk_size = 2048
        config.min_tokens = 330

        # This should succeed
        pipeline = DocxPipeline(config)
        assert pipeline is not None
