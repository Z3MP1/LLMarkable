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

    def supports_file(self, file_path: Path) -> bool:
        """
        Check if this pipeline supports the given file type.

        Default implementation checks if the file extension matches the pipeline's
        primary format. Pipelines supporting multiple extensions should override this.
        """
        # Get the pipeline's primary extension from its class name
        class_name = self.__class__.__name__.lower()
        if class_name.endswith("pipeline"):
            format_name = class_name[:-8]  # Remove 'pipeline' suffix
            primary_extension = f".{format_name}"
            return file_path.suffix.lower() == primary_extension

        # Fallback: no support detection possible
        return False
