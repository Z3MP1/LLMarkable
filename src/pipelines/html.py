"""
HTML-specific document processing pipeline using Docling.

Implements HTML to markdown conversion with paragraph-based chunking.
"""

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.base import BaseChunk
from docling_core.types.doc.document import DoclingDocument
from rich.console import Console

from src.config import Config
from src.utils import get_tokenizer, is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class HTMLPipeline(BasePipeline):
    """HTML document processing pipeline with Docling integration."""

    def __init__(self, config: Config) -> None:
        """Initialize HTML pipeline with Docling configuration."""
        super().__init__(config)
        self.console = Console()

        # Get tokenizer using the new utils function
        self.tokenizer = get_tokenizer(config)

        # Initialize Docling converter with HTML options
        self.converter = DocumentConverter()

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports HTML files."""
        from .factory import supports_file_extension

        return supports_file_extension(file_path, HTMLPipeline)

    def _chunk_document(self, docling_doc: DoclingDocument) -> list[BaseChunk]:  # noqa: ARG002
        """
        Chunk HTML document using paragraph-based approach.

        Note: HTML pipeline uses a different approach than other formats.
        This method is implemented to satisfy the base class interface
        but the actual chunking is done in the process method.

        Args:
            docling_doc: Docling document object

        Returns:
            List of BaseChunk objects (empty for HTML as we use custom chunking)

        """
        # HTML pipeline uses custom paragraph-based chunking in process()
        # This method exists to satisfy the abstract base class requirement
        return []

    def process(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Process HTML file and return structured chunks.

        Args:
            file_path: Path to the HTML file to process

        Returns:
            List of chunk dictionaries with content and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is not supported

        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        if not self.supports_file(file_path):
            msg = f"Unsupported file extension: {file_path.suffix}"
            raise ValueError(msg)

        try:
            # Convert HTML document using Docling
            try:
                result = self.converter.convert(
                    str(file_path),
                    max_file_size=self.config.max_file_size_bytes,
                )
                doc = result.document
            except Exception as e:
                from src.exceptions import ConversionError

                msg = f"HTML parsing failed: {e!s}"
                raise ConversionError(
                    msg,
                    file_path=str(file_path),
                    conversion_stage="document_parsing",
                    original_error=e,
                ) from e

            # Export to markdown for processing
            try:
                markdown_content = doc.export_to_markdown()
            except Exception as e:
                from src.exceptions import ConversionError

                msg = f"HTML to Markdown conversion failed: {e!s}"
                raise ConversionError(
                    msg,
                    file_path=str(file_path),
                    conversion_stage="markdown_export",
                    original_error=e,
                ) from e

            # Create initial chunks using Docling's chunking
            chunks = self._create_chunks(markdown_content, file_path)

            # Apply consolidation and filtering
            chunks = merge_small_trailing_chunks(chunks, self.config)
            return [chunk for chunk in chunks if is_chunk_useful(chunk, self.config)]

        except Exception as e:
            # If it's already one of our custom exceptions, re-raise it
            from src.exceptions import ConversionError, LLMarkableError

            if isinstance(e, LLMarkableError):
                raise

            # Otherwise, wrap in a ConversionError
            error = ConversionError(
                f"Unexpected error processing HTML: {e!s}",
                file_path=str(file_path),
                conversion_stage="unknown",
                original_error=e,
            )
            raise error from e

    def _create_chunks(self, content: str, file_path: Path) -> list[dict[str, Any]]:
        """
        Create chunks from HTML content.

        Args:
            content: Markdown content from HTML conversion
            file_path: Original file path for metadata

        Returns:
            List of chunk dictionaries

        """
        # For HTML, we'll use simple paragraph-based chunking
        # This preserves the document structure while creating manageable chunks
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        chunks = []
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) > self.config.html_min_paragraph_length:  # Skip very short paragraphs
                chunk = {
                    "content": paragraph,
                    "metadata": {
                        "source_file": str(file_path),
                        "chunk_index": i,
                        "chunk_type": "paragraph",
                        "format": "html",
                    },
                }
                chunks.append(chunk)

        return chunks
