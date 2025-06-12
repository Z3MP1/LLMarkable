"""
Unit tests for HTML pipeline functionality.

Tests the HTML pipeline implementation following pytest best practices
with proper isolation and mocking.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config import Config
from src.exceptions import ChunkingError, ConversionError
from src.pipelines.html import HTMLPipeline


class TestHTMLPipelineInstantiation:
    """Test HTML pipeline instantiation and initialization."""

    def test_should_instantiate_successfully_when_valid_config_provided(
        self,
        test_config: Config,
    ) -> None:
        """Test that HTML pipeline instantiates with valid configuration."""
        with patch("src.pipelines.html.DocumentConverter"):
            pipeline = HTMLPipeline(test_config)

            assert pipeline.config == test_config

    def test_should_create_document_converter_for_html_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test that pipeline creates DocumentConverter for HTML processing."""
        with patch("src.pipelines.html.DocumentConverter") as mock_converter:
            HTMLPipeline(test_config)

            # Verify converter was created (HTML uses default DocumentConverter)
            mock_converter.assert_called_once()
            call_args = mock_converter.call_args
            # HTML pipeline uses default DocumentConverter without format_options
            assert call_args.args == ()
            assert "format_options" not in call_args.kwargs


class TestHTMLPipelineSupportsFile:
    """Test file format support checking."""

    def test_should_support_html_extension(self, test_config: Config) -> None:
        """Test that pipeline supports .html files."""
        with patch("src.pipelines.html.DocumentConverter"):
            pipeline = HTMLPipeline(test_config)
            html_file = Path("test.html")

            assert pipeline.supports_file(html_file) is True

    def test_should_support_htm_extension(self, test_config: Config) -> None:
        """Test that pipeline supports .htm files."""
        with patch("src.pipelines.html.DocumentConverter"):
            pipeline = HTMLPipeline(test_config)
            htm_file = Path("test.htm")

            assert pipeline.supports_file(htm_file) is True

    def test_should_not_support_other_extensions(self, test_config: Config) -> None:
        """Test that pipeline rejects unsupported file types."""
        with patch("src.pipelines.html.DocumentConverter"):
            pipeline = HTMLPipeline(test_config)
            pdf_file = Path("test.pdf")

            assert pipeline.supports_file(pdf_file) is False


class TestHTMLPipelineProcess:
    """Test HTML document processing."""

    def test_should_raise_file_not_found_when_file_missing(
        self,
        test_config: Config,
    ) -> None:
        """Test that processing raises FileNotFoundError for missing files."""
        with patch("src.pipelines.html.DocumentConverter"):
            pipeline = HTMLPipeline(test_config)
            missing_file = Path("nonexistent.html")

            with pytest.raises(FileNotFoundError, match="File not found"):
                pipeline.process(missing_file)

    def test_should_raise_value_error_when_unsupported_extension(
        self,
        test_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that processing raises ValueError for unsupported extensions."""
        with patch("src.pipelines.html.DocumentConverter"):
            pipeline = HTMLPipeline(test_config)
            # Create a file with unsupported extension
            unsupported_file = tmp_path / "test.pdf"
            unsupported_file.write_text("content")

            with pytest.raises(ValueError, match="Unsupported file extension"):
                pipeline.process(unsupported_file)

    @patch("src.pipelines.base.merge_small_trailing_chunks")
    @patch("src.pipelines.base.is_chunk_useful")
    def test_should_process_html_file_successfully(
        self,
        mock_is_useful: Mock,
        mock_merge: Mock,
        test_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test successful HTML file processing with new Docling chunking."""
        # Create test HTML file
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>Test content</p></body></html>")

        # Mock the document converter and its result
        mock_doc = Mock()

        mock_result = Mock()
        mock_result.document = mock_doc

        mock_converter = Mock()
        mock_converter.convert.return_value = mock_result

        # Mock chunker results
        mock_chunk = Mock()
        mock_chunk.text = "Test chunk content that is long enough to be considered useful"
        mock_chunk.meta = Mock()
        mock_chunk.meta.export_json_dict.return_value = {"test": "metadata"}

        # Mock utility functions
        test_chunks = [{"content": "Test chunk", "metadata": {}}]
        mock_merge.return_value = test_chunks
        mock_is_useful.return_value = True

        with (
            patch("src.pipelines.html.DocumentConverter", return_value=mock_converter),
            patch("src.pipelines.html.HybridChunker") as mock_hybrid_chunker,
        ):
            mock_hybrid_chunker.return_value.chunk.return_value = [mock_chunk]

            pipeline = HTMLPipeline(test_config)
            result = pipeline.process(html_file)

            # Verify converter was called
            mock_converter.convert.assert_called_once_with(
                str(html_file),
                max_file_size=test_config.max_file_size_bytes,
            )

            # Verify utility functions were called
            mock_merge.assert_called_once()
            mock_is_useful.assert_called()

            # Verify result
            assert isinstance(result, list)

    def test_should_raise_conversion_error_when_docling_fails(
        self,
        test_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that docling conversion failures are properly wrapped."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>Test</p></body></html>")

        # Mock converter to raise an exception
        mock_converter = Mock()
        mock_converter.convert.side_effect = Exception("Docling failed")

        with patch("src.pipelines.html.DocumentConverter", return_value=mock_converter):
            pipeline = HTMLPipeline(test_config)

            with pytest.raises(ConversionError, match="HTML parsing failed"):
                pipeline.process(html_file)

    def test_should_raise_conversion_error_when_markdown_export_fails(
        self,
        test_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that chunking failures are properly wrapped."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>Test</p></body></html>")

        # Mock converter that succeeds but chunking fails
        mock_doc = Mock()
        mock_result = Mock()
        mock_result.document = mock_doc

        mock_converter = Mock()
        mock_converter.convert.return_value = mock_result

        with (
            patch("src.pipelines.html.DocumentConverter", return_value=mock_converter),
            patch("src.pipelines.html.HybridChunker") as mock_hybrid_chunker,
        ):
            # Make HybridChunker fail
            mock_hybrid_chunker.return_value.chunk.side_effect = Exception("Chunking failed")

            with patch("src.pipelines.html.HierarchicalChunker") as mock_hierarchical_chunker:
                # Make fallback also fail
                mock_hierarchical_chunker.return_value.chunk.side_effect = Exception("Fallback failed")

                pipeline = HTMLPipeline(test_config)

                with pytest.raises(ChunkingError):
                    pipeline.process(html_file)

    def test_should_re_raise_llmarkable_errors(
        self,
        test_config: Config,
        tmp_path: Path,
    ) -> None:
        """Test that LLMarkableError exceptions are re-raised as-is."""
        html_file = tmp_path / "test.html"
        html_file.write_text("<html><body><p>Test</p></body></html>")

        # Create a specific LLMarkableError
        custom_error = ConversionError("Custom error")

        mock_converter = Mock()
        mock_converter.convert.side_effect = custom_error

        with patch("src.pipelines.html.DocumentConverter", return_value=mock_converter):
            pipeline = HTMLPipeline(test_config)

            with pytest.raises(ConversionError, match="Custom error"):
                pipeline.process(html_file)


class TestHTMLPipelineDoclingChunking:
    """Test new Docling-based chunking functionality."""

    def test_should_use_hybrid_chunker_for_document_processing(
        self,
        test_config: Config,
    ) -> None:
        """Test that pipeline uses HybridChunker for document processing."""
        mock_doc = Mock()
        mock_chunk = Mock()
        mock_chunk.text = "Test chunk content that is long enough to be useful"
        mock_chunk.meta = Mock()
        mock_chunk.meta.export_json_dict.return_value = {"test": "metadata"}

        with (
            patch("src.pipelines.html.DocumentConverter"),
            patch("src.pipelines.html.HybridChunker") as mock_hybrid_chunker,
        ):
            mock_hybrid_chunker.return_value.chunk.return_value = [mock_chunk]

            pipeline = HTMLPipeline(test_config)
            chunks = pipeline._chunk_document(mock_doc)  # noqa: SLF001

            # Verify HybridChunker was used
            mock_hybrid_chunker.return_value.chunk.assert_called_once_with(dl_doc=mock_doc)
            assert len(chunks) == 1
            assert chunks[0].text == "Test chunk content that is long enough to be useful"

    def test_should_fallback_to_hierarchical_chunker_when_hybrid_fails(
        self,
        test_config: Config,
    ) -> None:
        """Test that pipeline falls back to HierarchicalChunker when HybridChunker fails."""
        mock_doc = Mock()
        mock_chunk = Mock()
        mock_chunk.text = "Fallback chunk content"
        mock_chunk.meta = Mock()

        with (
            patch("src.pipelines.html.DocumentConverter"),
            patch("src.pipelines.html.HybridChunker") as mock_hybrid_chunker,
            patch("src.pipelines.html.HierarchicalChunker") as mock_hierarchical_chunker,
        ):
            # Make HybridChunker fail
            mock_hybrid_chunker.return_value.chunk.side_effect = Exception("Hybrid failed")
            mock_hierarchical_chunker.return_value.chunk.return_value = [mock_chunk]

            pipeline = HTMLPipeline(test_config)
            chunks = pipeline._chunk_document(mock_doc)  # noqa: SLF001

            # Verify fallback was used
            mock_hierarchical_chunker.return_value.chunk.assert_called_once_with(mock_doc)
            assert len(chunks) == 1
            assert chunks[0].text == "Fallback chunk content"
