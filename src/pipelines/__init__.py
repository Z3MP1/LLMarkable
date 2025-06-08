"""
Document conversion pipelines package.

This package contains format-specific pipeline implementations for converting
documents to LLM-friendly markdown chunks.

Available pipelines:
- BasePipeline: Abstract base class for all pipelines
- PDFPipeline: PDF document processing pipeline
- HTMLPipeline: HTML document processing pipeline
- DocxPipeline: DOCX document processing pipeline
"""

from .base import BasePipeline
from .docx import DocxPipeline
from .factory import (
    create_pipeline,
    get_supported_formats,
    is_supported_format,
    register_pipeline,
)
from .html import HTMLPipeline
from .pdf import PDFPipeline

__all__ = [
    "BasePipeline",
    "DocxPipeline",
    "HTMLPipeline",
    "PDFPipeline",
    "create_pipeline",
    "get_supported_formats",
    "is_supported_format",
    "register_pipeline",
]
