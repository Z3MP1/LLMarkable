"""
Document conversion pipelines package.

This package contains format-specific pipeline implementations for converting
documents to LLM-friendly markdown chunks.

Available pipelines:
- BasePipeline: Abstract base class for all pipelines
- PDFPipeline: PDF document processing pipeline
- HTMLPipeline: HTML document processing pipeline
"""

from .base import BasePipeline
from .html import HTMLPipeline
from .pdf import PDFPipeline

__all__ = [
    "BasePipeline",
    "HTMLPipeline",
    "PDFPipeline",
]
