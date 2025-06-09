"""
Base abstract class for document conversion pipelines.

Provides common interface for PDF, HTML, and other format-specific pipelines.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docling_core.transforms.chunker.base import BaseChunk

from src.config import Config

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument


class BasePipeline(ABC):
    """Abstract base class for document conversion pipelines."""

    def __init__(self, config: Config) -> None:
        """Initialize pipeline with configuration."""
        self.config = config

    @abstractmethod
    def process(self, input_path: Path) -> list[dict[str, Any]]:
        """
        Process a document file and return structured chunks with metadata.

        Args:
            input_path: Path to the input document file

        Returns:
            List of structured chunks with metadata

        Raises:
            FileAccessError: If the input file cannot be read
            ProcessingError: If document processing fails
            ChunkingError: If chunking fails

        """

    @abstractmethod
    def _chunk_document(self, docling_doc: "DoclingDocument") -> list[BaseChunk]:
        """
        Chunk a document using format-specific chunking strategy.

        Args:
            docling_doc: Docling document object (specific type varies by format)

        Returns:
            List of BaseChunk objects from the chunker

        """

    def supports_file(self, file_path: Path) -> bool:  # noqa: ARG002
        """
        Check if this pipeline supports the given file type.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file type is supported, False otherwise

        """
        # Default implementation - subclasses should override
        return False
