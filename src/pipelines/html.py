"""HTML document processing pipeline."""

from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter, InputFormat

from src.config import Config
from src.utils import is_chunk_useful, merge_small_trailing_chunks

from .base import BasePipeline


class HTMLPipeline(BasePipeline):
    """Pipeline for processing HTML documents using Docling."""

    supported_extensions = [".html", ".htm"]

    def __init__(self, config: Config) -> None:
        """
        Initialize HTML pipeline with configuration.

        Args:
            config: Configuration object containing processing parameters

        """
        super().__init__(config)
        # Use default Docling settings for HTML - they're already well-optimized
        self.converter = DocumentConverter(
            format_options={
                InputFormat.HTML: None,  # Use default HTML settings
            },
        )

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

        if file_path.suffix.lower() not in self.supported_extensions:
            msg = f"Unsupported file extension: {file_path.suffix}"
            raise ValueError(msg)

        try:
            # Convert HTML document using Docling
            result = self.converter.convert(str(file_path))
            doc = result.document

            # Export to markdown for processing
            markdown_content = doc.export_to_markdown()

            # Create initial chunks using Docling's chunking
            chunks = self._create_chunks(markdown_content, file_path)

            # Apply consolidation and filtering
            chunks = merge_small_trailing_chunks(chunks, self.config)
            chunks = [chunk for chunk in chunks if is_chunk_useful(chunk, self.config)]

            return chunks

        except Exception as e:
            msg = f"Failed to process HTML file {file_path}: {e}"
            raise RuntimeError(msg) from e

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
            if len(paragraph) > 50:  # Skip very short paragraphs
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
