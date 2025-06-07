"""
Document conversion pipelines package.

This package contains format-specific pipeline implementations for converting
documents to LLM-friendly markdown chunks.

Available pipelines:
- BasePipeline: Abstract base class for all pipelines
- [Future: PDFPipeline, HTMLPipeline]
"""

from .base import BasePipeline

__all__ = [
    "BasePipeline",
] 