"""
Base abstract class for document conversion pipelines.

Provides common interface for PDF, HTML, and other format-specific pipelines.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from src.config import Config


class BasePipeline(ABC):
    """Abstract base class for document conversion pipelines."""

    def __init__(self, config: Config) -> None:
        """Initialize pipeline with configuration."""
        self.config = config

    @abstractmethod
    def process(self, input_path: Path) -> list[str]:
        """
        Process a document file and return markdown chunks.

        Args:
            input_path: Path to the input document file

        Returns:
            List of markdown text chunks

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file format is not supported

        """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions (e.g., ['.pdf', '.html'])."""

    def supports_file(self, file_path: Path) -> bool:
        """Check if this pipeline supports the given file type."""
        return file_path.suffix.lower() in self.supported_extensions
