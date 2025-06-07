"""
Configuration management for the document conversion pipeline.

Simple dataclass-based configuration for Phase 1 implementation.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration settings for document conversion pipeline."""

    # Chunk size settings (token-based, following Docling best practices)
    min_tokens: int = 200  # Minimum for useful chunks
    chunk_size: int = (
        2048  # Target chunk size, also used as max_tokens for HybridChunker
    )
    chunk_overlap: int = 100  # Small overlap between chunks to preserve context

    # Input/Output directories
    input_dir: str = "input"
    output_dir: str = "output"

    # Pipeline settings
    preserve_tables: bool = True
    preserve_images: bool = False
    merge_small_trailing_chunks: bool = True  # Feature we implemented

    # Output format
    output_format: str = "markdown"
    include_metadata: bool = True

    # Logging
    log_level: str = "INFO"
    verbose: bool = False

    @classmethod
    def default(cls) -> "Config":
        """Create a configuration with default values."""
        return cls()

    def validate(self) -> bool:
        """Basic validation of configuration values."""
        if self.min_tokens <= 0:
            msg = "min_tokens must be positive"
            raise ValueError(msg)
        if self.chunk_size <= self.min_tokens:
            msg = "chunk_size must be greater than min_tokens"
            raise ValueError(msg)
        if self.chunk_overlap < 0:
            msg = "chunk_overlap must be non-negative"
            raise ValueError(msg)
        if self.chunk_overlap >= self.chunk_size:
            msg = "chunk_overlap must be less than chunk_size"
            raise ValueError(msg)
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            msg = "Invalid log_level"
            raise ValueError(msg)
        return True

    @property
    def input_path(self) -> Path:
        """Get input directory as Path object."""
        return Path(self.input_dir)

    @property
    def output_path(self) -> Path:
        """Get output directory as Path object."""
        return Path(self.output_dir)
