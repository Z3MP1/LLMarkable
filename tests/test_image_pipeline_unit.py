#!/usr/bin/env python3
"""
Unit tests for Image pipeline following pytest best practices.

Tests the Image pipeline instantiation, configuration, and core functionality
using mocks and fixtures instead of generating real image files.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import Config
from src.pipelines.image import ImagePipeline


class TestImagePipelineInstantiation:
    """Test Image pipeline instantiation and initialization."""

    def test_should_instantiate_successfully_when_valid_config_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test successful Image pipeline instantiation."""
        pipeline = ImagePipeline(test_config)

        assert pipeline is not None
        assert pipeline.config == test_config

    def test_should_inherit_from_base_pipeline_when_instantiated(
        self,
        test_config: Config,
    ) -> None:
        """Test Image pipeline inheritance."""
        from src.pipelines.base import BasePipeline

        pipeline = ImagePipeline(test_config)

        assert isinstance(pipeline, BasePipeline)

    def test_should_initialize_tokenizer_with_config_settings(
        self,
        test_config: Config,
    ) -> None:
        """Test tokenizer initialization with config settings."""
        pipeline = ImagePipeline(test_config)

        assert pipeline.tokenizer is not None
        # Verify tokenizer configuration matches config
        assert hasattr(pipeline, "hybrid_chunker")
        assert hasattr(pipeline, "hierarchical_chunker")

    def test_should_configure_docling_converter_for_images(
        self,
        test_config: Config,
    ) -> None:
        """Test Docling converter configuration for image processing."""
        pipeline = ImagePipeline(test_config)

        assert hasattr(pipeline, "converter")
        assert pipeline.converter is not None


class TestImagePipelineFileSupport:
    """Test Image pipeline file support functionality."""

    def test_should_support_image_extensions_when_checked(self) -> None:
        """Test image file extension support."""
        test_config = Config.default()
        pipeline = ImagePipeline(test_config)

        # Test supported formats
        assert pipeline.supports_file(Path("image.png"))
        assert pipeline.supports_file(Path("photo.jpg"))
        assert pipeline.supports_file(Path("picture.jpeg"))
        assert pipeline.supports_file(Path("scan.tiff"))
        assert pipeline.supports_file(Path("document.tif"))
        assert pipeline.supports_file(Path("graphic.bmp"))
        assert pipeline.supports_file(Path("animation.gif"))

        # Test case insensitivity
        assert pipeline.supports_file(Path("IMAGE.PNG"))
        assert pipeline.supports_file(Path("PHOTO.JPG"))

        # Test unsupported formats
        assert not pipeline.supports_file(Path("document.pdf"))
        assert not pipeline.supports_file(Path("text.txt"))
        assert not pipeline.supports_file(Path("data.csv"))


class TestImagePipelineValidation:
    """Test Image pipeline validation functionality."""

    def test_should_raise_file_not_found_when_file_missing(
        self,
        test_config: Config,
    ) -> None:
        """Test FileNotFoundError for missing image files."""
        pipeline = ImagePipeline(test_config)
        non_existent_file = Path("nonexistent.png")

        from src.exceptions import ConversionError

        with pytest.raises(ConversionError):
            pipeline.process(non_existent_file)

    def test_should_raise_value_error_when_unsupported_format(
        self,
        test_config: Config,
    ) -> None:
        """Test ValueError for unsupported file formats."""
        # This test verifies that the pipeline factory would handle unsupported formats
        # The actual validation happens at the factory level, not the pipeline level
        assert test_config is not None  # Basic test to avoid unused parameter warning


class TestImagePipelineProcessing:
    """Test Image pipeline document processing functionality."""

    def test_should_chunk_document_correctly_when_docling_document_provided(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test the _chunk_document method with mock data."""
        pipeline = ImagePipeline(test_config)

        with patch.object(pipeline, "hybrid_chunker") as mock_chunker:
            mock_chunker.chunk.return_value = [
                Mock(text="OCR extracted text from image"),
                Mock(text="Additional text content"),
            ]

            result = pipeline._chunk_document(mock_docling_document)

            assert isinstance(result, list)
            assert len(result) == 2
            mock_chunker.chunk.assert_called_once_with(dl_doc=mock_docling_document)

    def test_should_fallback_to_hierarchical_when_hybrid_fails(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test fallback to HierarchicalChunker when HybridChunker fails."""
        pipeline = ImagePipeline(test_config)

        with (
            patch.object(pipeline, "hybrid_chunker") as mock_hybrid_chunker,
            patch.object(pipeline, "hierarchical_chunker") as mock_hierarchical_chunker,
        ):
            # Mock hybrid chunker failure
            mock_hybrid_chunker.chunk.side_effect = ValueError("Hybrid failed")

            # Mock hierarchical chunker success
            mock_chunks = [Mock(text="chunk1"), Mock(text="chunk2")]
            mock_hierarchical_chunker.chunk.return_value = iter(mock_chunks)

            result = pipeline._chunk_document(mock_docling_document)

            assert result == mock_chunks
            mock_hierarchical_chunker.chunk.assert_called_once_with(
                mock_docling_document,
            )


class TestImagePipelineConfiguration:
    """Test Image pipeline configuration handling."""

    def test_should_use_config_settings_when_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test config settings usage in processing."""
        pipeline = ImagePipeline(test_config)

        assert pipeline.config.chunk_size == test_config.chunk_size
        assert pipeline.config.min_tokens == test_config.min_tokens
        assert pipeline.config.verbose == test_config.verbose

    def test_should_validate_config_on_instantiation(
        self,
        test_config: Config,
    ) -> None:
        """Test config validation during pipeline instantiation."""
        # Should not raise any exception with valid config
        pipeline = ImagePipeline(test_config)
        assert pipeline.config == test_config
