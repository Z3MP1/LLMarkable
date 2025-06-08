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
from src.exceptions import ChunkingError, ConversionError, ValidationError
from src.pipelines.image import ImagePipeline


class TestImagePipelineInstantiation:
    """Test Image pipeline instantiation and basic properties."""

    def test_should_instantiate_successfully_when_valid_config_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test that Image pipeline can be instantiated correctly."""
        pipeline = ImagePipeline(test_config)

        assert pipeline is not None
        # Image pipeline supports multiple extensions
        assert pipeline.supports_file(Path("test.png"))
        assert pipeline.supports_file(Path("test.jpg"))

    def test_should_inherit_from_base_pipeline_when_instantiated(
        self,
        test_config: Config,
    ) -> None:
        """Test that Image pipeline properly inherits from BasePipeline."""
        from src.pipelines.base import BasePipeline

        pipeline = ImagePipeline(test_config)
        assert isinstance(pipeline, BasePipeline)

    def test_should_initialize_tokenizer_with_config_settings(
        self,
        test_config: Config,
    ) -> None:
        """Test that tokenizer is properly initialized with config values."""
        pipeline = ImagePipeline(test_config)

        assert hasattr(pipeline, "tokenizer")
        assert pipeline.tokenizer is not None
        # BGE tokenizer has model-specific max_tokens (512)
        assert pipeline.tokenizer.max_tokens == 512

    def test_should_configure_docling_converter_for_images(
        self,
        test_config: Config,
    ) -> None:
        """Test that DocumentConverter is properly configured for image processing."""
        pipeline = ImagePipeline(test_config)

        assert hasattr(pipeline, "converter")
        assert pipeline.converter is not None


class TestImagePipelineFileSupport:
    """Test Image pipeline file type detection and support."""

    def test_should_support_image_extensions_when_checked(self) -> None:
        """Test file extension support detection."""
        config = Config.default()
        pipeline = ImagePipeline(config)

        # Test supported extensions
        supported_extensions = [
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".tif",
            ".bmp",
            ".gif",
        ]
        for ext in supported_extensions:
            test_path = Path(f"test{ext}")
            assert pipeline.supports_file(test_path)

        # Test unsupported extensions
        unsupported_extensions = [".pdf", ".docx", ".txt", ".html"]
        for ext in unsupported_extensions:
            test_path = Path(f"test{ext}")
            assert not pipeline.supports_file(test_path)


class TestImagePipelineValidation:
    """Test Image pipeline input validation."""

    def test_should_raise_file_not_found_when_file_missing(
        self,
        test_config: Config,
    ) -> None:
        """Test error handling for missing files."""
        pipeline = ImagePipeline(test_config)

        non_existent_path = Path("non_existent_image.png")

        with pytest.raises(FileNotFoundError) as context:
            pipeline.process(non_existent_path)

        assert "Image file not found" in str(context.value)

    def test_should_raise_value_error_when_unsupported_format(
        self,
        test_config: Config,
    ) -> None:
        """Test error handling for unsupported file formats."""
        pipeline = ImagePipeline(test_config)

        # Mock file existence
        with patch.object(Path, "exists", return_value=True):
            unsupported_path = Path("test.pdf")

            with pytest.raises(ValueError) as context:
                pipeline.process(unsupported_path)

            assert "Unsupported image format" in str(context.value)

    @patch("PIL.Image.open")
    def test_should_validate_image_integrity_when_pil_available(
        self,
        mock_pil_open: Mock,
        test_config: Config,
    ) -> None:
        """Test image integrity validation with PIL."""
        pipeline = ImagePipeline(test_config)

        # Mock successful image validation
        mock_img = Mock()
        mock_img.size = (1024, 768)
        mock_img.__enter__ = Mock(return_value=mock_img)
        mock_img.__exit__ = Mock(return_value=None)
        mock_pil_open.return_value = mock_img

        test_path = Path("test.png")

        # Should not raise exception for valid image
        pipeline._validate_image_integrity(test_path)

        mock_pil_open.assert_called_once_with(test_path)
        mock_img.verify.assert_called_once()

    @patch("PIL.Image.open")
    def test_should_raise_validation_error_when_corrupted_image(
        self,
        mock_pil_open: Mock,
        test_config: Config,
    ) -> None:
        """Test error handling for corrupted images."""
        pipeline = ImagePipeline(test_config)

        # Mock PIL raising exception for corrupted image
        mock_pil_open.side_effect = OSError("Cannot identify image file")

        test_path = Path("corrupted.png")

        with pytest.raises(ValidationError) as context:
            pipeline._validate_image_integrity(test_path)

        assert "Invalid or corrupted image file" in str(context.value)

    def test_should_skip_validation_when_pil_unavailable(
        self,
        test_config: Config,
    ) -> None:
        """Test graceful handling when PIL is not available."""
        pipeline = ImagePipeline(test_config)

        # Mock the PIL import inside the method to raise ImportError
        original_import = __builtins__["__import__"]

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "PIL":
                msg = "No module named 'PIL'"
                raise ImportError(msg)
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            test_path = Path("test.png")

            # Should not raise exception when PIL unavailable
            pipeline._validate_image_integrity(test_path)


class TestImagePipelineOCRProcessing:
    """Test Image pipeline OCR processing functionality."""

    @patch("src.pipelines.image.DocumentConverter")
    def test_should_convert_image_with_ocr_when_processing(
        self,
        mock_document_converter_class: Mock,
        test_config: Config,
    ) -> None:
        """Test OCR conversion of image files."""
        # Mock converter and result
        mock_converter = Mock()
        mock_document_converter_class.return_value = mock_converter

        mock_result = Mock()
        mock_doc = Mock()
        mock_doc.texts = [Mock(text="Sample OCR text")]
        mock_result.document = mock_doc
        mock_converter.convert.return_value = mock_result

        pipeline = ImagePipeline(test_config)
        # Replace the converter with our mock
        pipeline.converter = mock_converter

        test_path = Path("test.png")

        result_doc = pipeline._convert_image_with_ocr(test_path, is_large_image=False)

        assert result_doc == mock_doc
        mock_converter.convert.assert_called_once_with(test_path)

    @patch("src.pipelines.image.DocumentConverter")
    def test_should_raise_conversion_error_when_ocr_fails(
        self,
        mock_document_converter_class: Mock,
        test_config: Config,
    ) -> None:
        """Test error handling when OCR processing fails."""
        # Mock converter failure
        mock_converter = Mock()
        mock_document_converter_class.return_value = mock_converter
        mock_converter.convert.side_effect = RuntimeError("OCR processing failed")

        pipeline = ImagePipeline(test_config)
        # Replace the converter with our mock
        pipeline.converter = mock_converter

        test_path = Path("test.png")

        with pytest.raises(ConversionError) as context:
            pipeline._convert_image_with_ocr(test_path, is_large_image=False)

        assert "Image OCR processing failed" in str(context.value)

    def test_should_analyze_ocr_quality_when_processing_large_images(
        self,
        test_config: Config,
    ) -> None:
        """Test OCR quality analysis for large images."""
        pipeline = ImagePipeline(test_config)

        # Mock document with text elements
        mock_doc = Mock()
        mock_text1 = Mock(text="This is good quality text with meaningful words")
        mock_text2 = Mock(text="More quality content here")
        mock_doc.texts = [mock_text1, mock_text2]

        stats = pipeline._analyze_ocr_quality(mock_doc)

        assert stats["text_elements"] == 2
        assert stats["total_text_length"] > 0
        assert stats["estimated_confidence"] == "good"
        assert stats["has_meaningful_text"]


class TestImagePipelineChunking:
    """Test Image pipeline chunking functionality."""

    def test_should_chunk_ocr_content_with_hybrid_chunker(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test OCR content chunking with HybridChunker."""
        pipeline = ImagePipeline(test_config)

        with patch.object(pipeline, "hybrid_chunker") as mock_chunker:
            mock_chunks = [Mock(text="chunk1"), Mock(text="chunk2")]
            mock_chunker.chunk.return_value = iter(mock_chunks)

            result = pipeline._chunk_ocr_content(mock_docling_document)

            assert result == mock_chunks
            mock_chunker.chunk.assert_called_once_with(mock_docling_document)

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

            result = pipeline._chunk_ocr_content(mock_docling_document)

            assert result == mock_chunks
            mock_hierarchical_chunker.chunk.assert_called_once_with(
                mock_docling_document,
            )

    def test_should_raise_chunking_error_when_all_chunkers_fail(
        self,
        test_config: Config,
        mock_docling_document: Mock,
    ) -> None:
        """Test error handling when all chunking strategies fail."""
        pipeline = ImagePipeline(test_config)

        with (
            patch.object(pipeline, "hybrid_chunker") as mock_hybrid_chunker,
            patch.object(pipeline, "hierarchical_chunker") as mock_hierarchical_chunker,
        ):
            # Mock both chunkers failing
            mock_hybrid_chunker.chunk.side_effect = ValueError("Hybrid failed")
            mock_hierarchical_chunker.chunk.side_effect = RuntimeError(
                "Hierarchical failed",
            )

            with pytest.raises(ChunkingError) as context:
                pipeline._chunk_ocr_content(mock_docling_document)

            assert "All chunking strategies failed" in str(context.value)


class TestImagePipelineTextProcessing:
    """Test Image pipeline text processing functionality."""

    def test_should_clean_ocr_text_when_processing_chunks(
        self,
        test_config: Config,
    ) -> None:
        """Test OCR text cleaning functionality."""
        pipeline = ImagePipeline(test_config)

        # Test text with OCR artifacts
        dirty_text = (
            "This   is  text   with\n\nexcessive   whitespace  and  artifacts!!!"
        )

        cleaned = pipeline._clean_ocr_text(dirty_text)

        # Should normalize whitespace and remove artifacts
        assert "   " not in cleaned  # No triple spaces
        assert "\n\n" not in cleaned  # No double newlines
        assert len(cleaned) < len(dirty_text)

    @patch("PIL.Image.open")
    def test_should_extract_image_metadata_when_processing(
        self,
        mock_pil_open: Mock,
        test_config: Config,
    ) -> None:
        """Test image metadata extraction."""
        pipeline = ImagePipeline(test_config)

        # Mock PIL image
        mock_img = Mock()
        mock_img.width = 1024
        mock_img.height = 768
        mock_img.mode = "RGB"
        mock_img.__enter__ = Mock(return_value=mock_img)
        mock_img.__exit__ = Mock(return_value=None)
        mock_pil_open.return_value = mock_img

        test_path = Path("test.png")
        content = "Sample OCR extracted text content"

        metadata = pipeline._extract_image_metadata(test_path, content)

        assert metadata["image_format"] == "png"
        assert metadata["content_length"] == len(content)
        assert metadata["word_count"] == len(content.split())
        assert "estimated_ocr_quality" in metadata
        assert metadata["image_dimensions"]["width"] == 1024
        assert metadata["image_dimensions"]["height"] == 768

    def test_should_estimate_content_quality_accurately(
        self,
        test_config: Config,
    ) -> None:
        """Test OCR content quality estimation."""
        pipeline = ImagePipeline(test_config)

        # Test good quality content
        good_content = "This is high quality text with proper words and structure"
        assert pipeline._estimate_content_quality(good_content) == "good"

        # Test low quality content (too few words)
        low_content = "a b"
        assert pipeline._estimate_content_quality(low_content) == "low"

        # Test empty content
        empty_content = ""
        assert pipeline._estimate_content_quality(empty_content) == "empty"

        # Test content with poor character distribution
        poor_content = "123 456 789 !@# $%^ &*()"
        assert pipeline._estimate_content_quality(poor_content) == "low"


class TestImagePipelineFiltering:
    """Test Image pipeline chunk filtering functionality."""

    @patch("src.pipelines.image.is_chunk_useful")
    def test_should_filter_ocr_chunks_by_quality(
        self,
        mock_is_chunk_useful: Mock,
        test_config: Config,
    ) -> None:
        """Test OCR chunk filtering based on quality metrics."""
        pipeline = ImagePipeline(test_config)

        # Create test chunks with sufficient content for token requirements
        good_chunk = {
            "content": "This is a good quality OCR text content with sufficient words to meet token requirements for testing purposes",
            "metadata": {
                "chunk_index": 0,
                "image_specific": {
                    "estimated_ocr_quality": "good",
                    "word_count": 18,
                },
            },
        }

        empty_chunk = {
            "content": "",
            "metadata": {
                "chunk_index": 1,
                "image_specific": {
                    "estimated_ocr_quality": "empty",
                    "word_count": 0,
                },
            },
        }

        chunks = [good_chunk, empty_chunk]

        # Mock is_chunk_useful to return True for good chunk, False for empty
        # The function receives the chunk dict and config
        def mock_useful(
            chunk: dict[str, object],
            config: Config,
            tokenizer: object | None = None,
        ) -> bool:
            # Extract content from chunk dict
            content = chunk.get("content", "")
            return isinstance(content, str) and len(content.strip()) > 10

        mock_is_chunk_useful.side_effect = mock_useful

        filtered = pipeline._filter_ocr_chunks(chunks, is_large_image=False)

        # Should keep good chunk, filter empty chunk
        assert len(filtered) == 1
        assert filtered[0] == good_chunk

        # Verify is_chunk_useful was called for both chunks
        assert mock_is_chunk_useful.call_count == 2


class TestImagePipelineIntegration:
    """Test Image pipeline integration and complete processing."""

    @patch("PIL.Image.open")
    @patch("src.pipelines.image.is_chunk_useful")
    @patch("src.pipelines.image.get_tokenizer")
    @patch("src.pipelines.image.HybridChunker")
    @patch("src.pipelines.image.HierarchicalChunker")
    @patch("src.pipelines.image.merge_small_trailing_chunks")
    def test_should_process_complete_pipeline_successfully(
        self,
        mock_merge_chunks: Mock,
        mock_hierarchical_chunker: Mock,
        mock_hybrid_chunker: Mock,
        mock_get_tokenizer: Mock,
        mock_is_chunk_useful: Mock,
        mock_pil_open: Mock,
        test_config: Config,
    ) -> None:
        """Test complete image processing pipeline integration."""
        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.count_tokens.return_value = 100  # Sufficient tokens
        mock_get_tokenizer.return_value = mock_tokenizer

        # Mock chunkers
        mock_hybrid_chunker.return_value = Mock()
        mock_hierarchical_chunker.return_value = Mock()

        # Mock merge function to return chunks unchanged
        mock_merge_chunks.side_effect = lambda chunks, _config: chunks

        # Mock PIL validation
        mock_img = Mock()
        mock_img.size = (800, 600)
        mock_img.width = 800
        mock_img.height = 600
        mock_img.mode = "RGB"
        mock_img.__enter__ = Mock(return_value=mock_img)
        mock_img.__exit__ = Mock(return_value=None)
        mock_pil_open.return_value = mock_img

        # Mock chunk filtering
        def mock_useful(
            chunk: dict[str, object],
            config: Config,
            tokenizer: object | None = None,
        ) -> bool:
            # Extract content from chunk dict
            content = chunk.get("content", "")
            return isinstance(content, str) and len(content.strip()) > 10

        mock_is_chunk_useful.side_effect = mock_useful

        # Mock file system
        test_path = Path("test.png")
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
            patch.object(ImagePipeline, "_convert_image_with_ocr") as mock_convert,
            patch.object(ImagePipeline, "_chunk_ocr_content") as mock_chunk,
        ):
            mock_stat.return_value.st_size = 1024 * 1024  # 1MB

            # Mock OCR conversion
            mock_doc = Mock()
            mock_convert.return_value = mock_doc

            # Mock chunking
            mock_chunk_obj = Mock()
            mock_chunk_obj.text = "This is a sample OCR extracted text content with sufficient words to meet the minimum token requirements for testing the complete image processing pipeline functionality"
            mock_chunk_obj.meta = {}
            mock_chunk.return_value = [mock_chunk_obj]

            pipeline = ImagePipeline(test_config)
            result = pipeline.process(test_path)

            # Verify successful processing
            assert isinstance(result, list)
            assert len(result) > 0

            # Verify chunk structure
            chunk = result[0]
            assert "content" in chunk
            assert "metadata" in chunk
            assert chunk["metadata"]["file_type"] == "image"
            assert chunk["metadata"]["processing_method"] == "ocr"
