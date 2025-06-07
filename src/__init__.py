"""
Advanced Document Conversion & Synthesis Pipeline

A modular, extensible document conversion pipeline that transforms source files
(PDF, HTML, etc.) into high-quality, LLM-friendly Markdown with format-specific
optimizations and optional AI-augmented content synthesis.
"""

__version__ = "0.1.0"
__author__ = "Converter Team"

# Import main components for easier access
from .config import Config

__all__ = ["Config", "__version__"] 