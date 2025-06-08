"""
Pipeline factory for creating appropriate document processing pipelines.

This module provides factory functions for creating pipeline instances based on
file extensions, with a registry pattern for extensibility.
"""

from pathlib import Path

from src.config import Config

from .base import BasePipeline
from .docx import DocxPipeline
from .html import HTMLPipeline
from .image import ImagePipeline
from .pdf import PDFPipeline
from .pptx import PptxPipeline

# Pipeline registry mapping extensions to pipeline classes
_PIPELINE_REGISTRY: dict[str, type[BasePipeline]] = {
    ".pdf": PDFPipeline,
    ".html": HTMLPipeline,
    ".htm": HTMLPipeline,
    ".docx": DocxPipeline,
    ".pptx": PptxPipeline,
    # Image formats
    ".png": ImagePipeline,
    ".jpg": ImagePipeline,
    ".jpeg": ImagePipeline,
    ".tiff": ImagePipeline,
    ".tif": ImagePipeline,
    ".bmp": ImagePipeline,
    ".gif": ImagePipeline,
}


def create_pipeline(file_path: Path, config: Config) -> BasePipeline:
    """
    Create appropriate pipeline for the given file.

    Args:
        file_path: Path to the file to be processed
        config: Configuration object for pipeline initialization

    Returns:
        Initialized pipeline instance for the file type

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported

    """
    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    file_extension = file_path.suffix.lower()

    if file_extension not in _PIPELINE_REGISTRY:
        supported_formats = ", ".join(sorted(_PIPELINE_REGISTRY.keys()))
        msg = (
            f"Unsupported file format: {file_extension}. "
            f"Supported formats: {supported_formats}"
        )
        raise ValueError(
            msg,
        )

    pipeline_class = _PIPELINE_REGISTRY[file_extension]
    return pipeline_class(config)


def get_supported_formats() -> list[str]:
    """
    Get list of all supported file extensions.

    Returns:
        List of supported file extensions (e.g., ['.pdf', '.html', '.htm'])

    """
    return sorted(_PIPELINE_REGISTRY.keys())


def register_pipeline(extension: str, pipeline_class: type[BasePipeline]) -> None:
    """
    Register a new pipeline for a file extension.

    Args:
        extension: File extension (e.g., '.docx')
        pipeline_class: Pipeline class that inherits from BasePipeline

    Raises:
        ValueError: If extension is invalid or pipeline_class doesn't inherit from BasePipeline

    """
    if not extension.startswith("."):
        msg = f"Extension must start with '.': {extension}"
        raise ValueError(msg)

    if not issubclass(pipeline_class, BasePipeline):
        msg = f"Pipeline class must inherit from BasePipeline: {pipeline_class}"
        raise TypeError(msg)

    _PIPELINE_REGISTRY[extension.lower()] = pipeline_class


def is_supported_format(file_path: Path) -> bool:
    """
    Check if a file format is supported.

    Args:
        file_path: Path to check

    Returns:
        True if the file format is supported, False otherwise

    """
    return file_path.suffix.lower() in _PIPELINE_REGISTRY
